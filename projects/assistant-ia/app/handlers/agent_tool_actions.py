"""Les clics qui bordent les outils de l'agent (#1787579840505).

Deux familles, correspondant aux deux régimes de la roadmap §3.2 :

- **Avant écriture** (`agent_tool_confirm` / `agent_tool_cancel`) — contexte tainté. Rien n'a été
  écrit ; la ligne `agent_tool_calls` en `confirmation_requise` porte le payload résolu et fait
  office d'objet en attente. Le clic l'exécute ou l'enterre.
- **Après écriture** (`agent_reminder_cancel` / `agent_reminder_edit`) — contexte propre. La carte
  existe ; l'utilisateur la supprime ou la corrige.

Ce module ne décide d'aucun régime : `policy()` l'a déjà fait. Il exécute une décision humaine.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.services import kanban as kanban_svc
from app.services.agent_time import TZ, format_local, to_local
from app.services.agent_tools import audit, registry
from app.services.agent_tools.base import ToolContext, ToolError
from app.services.agent_tools.create_reminder import build_posterior_blocks
from app.services.agent_tools.manifest import TurnState

logger = logging.getLogger(__name__)

# Au-delà, une confirmation en attente n'est plus exécutable. Sans cette borne, un bouton oublié
# dans un vieux fil resterait armé indéfiniment, et une date résolue il y a trois jours serait
# écrite telle quelle.
CONFIRM_TTL = timedelta(hours=1)

EDIT_MODAL = "agent_reminder_edit_modal"


def _plain(text: str) -> list[dict]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]


# ── Confirmation préalable ───────────────────────────────────────────────────

async def confirm_pending(call_id: str, user_id: str | None) -> tuple[str, list[dict]]:
    """Exécute une action suspendue. Renvoie (texte, blocs) remplaçant le message de confirmation."""
    row = await audit.get_pending(call_id)
    if not row:
        # Déjà tranchée, expirée, ou jamais enregistrée. Aucun effet, et on le dit.
        return ":information_source: Cette demande a déjà été traitée.", []

    created = row["created_at"]
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > CONFIRM_TTL:
        await audit.settle(call_id, verdict="refused", user_confirmed=False,
                           verdict_reason="confirmation expirée")
        return ":hourglass: Demande expirée — rien n'a été écrit. Redemande-le-moi si besoin.", []

    spec = registry.get(row["tool_name"])
    if spec is None:
        await audit.settle(call_id, verdict="refused", user_confirmed=False,
                           verdict_reason="outil devenu indisponible")
        return f":warning: L'outil `{row['tool_name']}` n'est plus disponible — rien n'a été écrit.", []

    resolved = row["resolved_payload"]
    if isinstance(resolved, str):
        resolved = json.loads(resolved)
    taints = row["taint_sources"]
    if isinstance(taints, str):
        taints = json.loads(taints)

    # Le payload exécuté est celui qui a été **affiché**, relu depuis la base : pas une
    # re-résolution. « demain 9h » confirmé après minuit ne doit pas glisser d'un jour.
    turn = TurnState(
        channel_id=row["channel_id"] or "",
        user_id=row["user_id"],
        slack_ts=row["slack_ts"],
        thread_ts=row["thread_ts"],
        doc_version=row["doc_version"],
        taint_sources=list(taints or []),
    )

    try:
        result = await spec.execute(resolved, ToolContext(turn=turn))
    except ToolError as exc:
        await audit.settle(call_id, verdict="refused", user_confirmed=True, verdict_reason=str(exc))
        return f":warning: L'action a échoué : {exc}", []
    except Exception:
        logger.exception("agent_tool_actions: exécution confirmée en échec (%s)", call_id)
        await audit.settle(call_id, verdict="refused", user_confirmed=True,
                           verdict_reason="erreur interne à l'exécution")
        return ":warning: L'action a échoué. Rien n'a été écrit.", []

    await audit.settle(call_id, verdict="ok", user_confirmed=True, result=result.payload)
    logger.info("agent_tool_actions: %s confirmé par %s (call=%s)", row["tool_name"], user_id, call_id)

    text = f":white_check_mark: Confirmé par <@{user_id}> — {result.slack_text or row['tool_name']}"
    # On garde les blocs de l'outil (donc « Éditer » / « Annuler » pour un rappel) : une action
    # confirmée doit rester aussi corrigeable qu'une action créée en contexte propre.
    blocks = (result.slack_blocks or []) + [
        {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
    ]
    return text, blocks


async def cancel_pending(call_id: str, user_id: str | None) -> tuple[str, list[dict]]:
    """Enterre une action suspendue. Rien n'a jamais été écrit — il n'y a rien à défaire."""
    settled = await audit.settle(
        call_id, verdict="refused", user_confirmed=False,
        verdict_reason=f"annulé par l'utilisateur {user_id}",
    )
    if not settled:
        return ":information_source: Cette demande a déjà été traitée.", []
    return ":x: Annulé — rien n'a été écrit.", []


# ── Rappel déjà créé ─────────────────────────────────────────────────────────

async def cancel_reminder(card_id: str, user_id: str | None) -> tuple[str, list[dict]]:
    card = await kanban_svc.get_card(card_id)
    if not card:
        return ":information_source: Ce rappel n'existe plus.", []
    deleted = await kanban_svc.delete_card(card_id)
    if not deleted:
        return ":warning: Suppression impossible — le rappel est toujours actif.", []
    logger.info("agent_tool_actions: rappel %s supprimé par %s", card_id, user_id)
    return f":wastebasket: Rappel annulé : *{card['title']}*", []


def edit_modal_view(card, message_ts: str, channel_id: str) -> dict:
    """Modale d'édition d'un rappel : titre, date, heure.

    Datepicker et timepicker plutôt qu'un champ libre : la correction d'une date mal interprétée
    ne doit pas repasser par une interprétation.
    """
    due = to_local(card["due_date"]) if card["due_date"] else None
    date_el: dict = {"type": "datepicker", "action_id": "date"}
    time_el: dict = {"type": "timepicker", "action_id": "time"}
    if due:
        date_el["initial_date"] = due.strftime("%Y-%m-%d")
        time_el["initial_time"] = due.strftime("%H:%M")

    return {
        "type": "modal",
        "callback_id": EDIT_MODAL,
        "private_metadata": json.dumps({
            "card_id": str(card["id"]), "ts": message_ts, "channel": channel_id,
        }),
        "title": {"type": "plain_text", "text": "Modifier le rappel"},
        "submit": {"type": "plain_text", "text": "Enregistrer"},
        "close": {"type": "plain_text", "text": "Fermer"},
        "blocks": [
            {
                "type": "input", "block_id": "title",
                "label": {"type": "plain_text", "text": "Rappel"},
                "element": {
                    "type": "plain_text_input", "action_id": "title",
                    "initial_value": card["title"],
                },
            },
            {
                "type": "input", "block_id": "date",
                "label": {"type": "plain_text", "text": "Date"},
                "element": date_el,
            },
            {
                "type": "input", "block_id": "time",
                "label": {"type": "plain_text", "text": "Heure"},
                "element": time_el,
            },
        ],
    }


async def apply_edit(card_id: str, title: str, date_str: str, time_str: str) -> tuple[str, list[dict]]:
    """Applique l'édition. `reminder_sent_at` est remis à NULL : reprogrammer une date, c'est
    demander à être notifié de nouveau — sinon un rappel déjà parti ne repartirait jamais."""
    h, _, m = time_str.partition(":")
    due = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=int(h), minute=int(m or 0), tzinfo=TZ
    )
    card = await kanban_svc.update_card(
        card_id, title=title.strip(), due_date=due, reminder_sent_at=None
    )
    if not card:
        return ":warning: Ce rappel n'existe plus.", []
    logger.info("agent_tool_actions: rappel %s modifié → %r %s", card_id, title, due.isoformat())
    return (
        f"Rappel mis à jour : {card['title']} — {format_local(due)}",
        build_posterior_blocks(card_id, card["title"], due),
    )
