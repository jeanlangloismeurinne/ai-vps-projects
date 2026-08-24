"""Outil `create_reminder` — premier outil à effet de bord (#1787579840505).

## Frontière modèle / code (roadmap §2.3 — non négociable)

| Le modèle fait | Le code fait |
|---|---|
| Extraire un titre et une date **décomposée** (mode + composants) | Résoudre en `TIMESTAMPTZ` depuis un `now` qu'il fournit lui-même |
| Rien d'autre | Choisir le board, la colonne, valider les bornes, écrire, confirmer, journaliser |

La surface d'attaque se réduit donc à **un titre et quelques entiers validés**. Le pire cas d'une
injection réussie est un rappel parasite, visible dans le fil et supprimable en un clic.

## Pourquoi une date décomposée plutôt qu'une date ISO

Demander une date ISO au modèle reviendrait à lui faire résoudre « demain » — donc à lui faire
deviner `now`, ce que le ticket interdit explicitement. Demander une expression libre (« mardi
prochain ») imposerait un analyseur de langue en Python : soit une dépendance au comportement
difficile à auditer, soit un analyseur maison fragile.

La décomposition est la troisième voie : le modèle fait ce qu'il sait faire — traduire une
formulation en `mode` + composants, sans connaître la date du jour — et le code fait de
l'arithmétique de calendrier, testable et lisible. Un mode inconnu est refusé, il n'existe pas de
chemin par défaut silencieux.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.services import kanban as kanban_svc
from app.services.agent_time import TZ, format_local, now_local
from app.services.agent_tools.base import PreparedCall, ToolContext, ToolError, ToolResult, ToolSpec
from app.services.agent_tools.manifest import Effect, RateLimit, ToolManifest

logger = logging.getLogger(__name__)

# Constantes de code, jamais des arguments du modèle : c'est ce qui garantit qu'un contenu
# injecté ne peut pas rediriger un rappel vers un autre board (roadmap §2.3).
REMINDER_COLUMN = "Rappels"
DEFAULT_BOARD_NAME = "Personnel"
DEFAULT_TIME = "09:00"

TITLE_MAX = 200
# Un rappel dans plus de deux ans n'est jamais une intention réelle — c'est une erreur de
# résolution. Refusé explicitement plutôt que corrigé en silence.
HORIZON_MAX = timedelta(days=730)
# Tolérance sur le passé : le temps qui passe entre la résolution et l'écriture ne doit pas
# transformer « dans 1 minute » en refus.
PAST_TOLERANCE = timedelta(minutes=2)

_JOURS = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Ce qu'il faut rappeler, en quelques mots, à la première personne "
                           "de l'utilisateur. Ex. « appeler le garage ».",
        },
        "date_mode": {
            "type": "string",
            "enum": ["in_minutes", "offset_days", "weekday", "absolute"],
            "description": (
                "Comment la date a été formulée. "
                "`in_minutes` : « dans 20 minutes », « dans 2 heures » (convertir en minutes). "
                "`offset_days` : « aujourd'hui » (0), « demain » (1), « après-demain » (2), "
                "« dans 3 jours » (3). "
                "`weekday` : « mardi », « lundi prochain » — la prochaine occurrence de ce jour. "
                "`absolute` : une date explicite (« le 12 septembre »). "
                "Tu ne connais pas la date d'aujourd'hui : ne la calcule jamais toi-même."
            ),
        },
        "in_minutes": {"type": "integer", "description": "Si date_mode = in_minutes."},
        "offset_days": {"type": "integer", "description": "Si date_mode = offset_days. 0 = aujourd'hui."},
        "weekday": {
            "type": "string",
            "enum": list(_JOURS),
            "description": "Si date_mode = weekday.",
        },
        "date": {"type": "string", "description": "Si date_mode = absolute, au format AAAA-MM-JJ."},
        "time": {
            "type": "string",
            "description": f"Heure locale HH:MM. Omise si date_mode = in_minutes. "
                           f"Défaut {DEFAULT_TIME} si l'utilisateur n'a pas précisé d'heure.",
        },
    },
    "required": ["title", "date_mode"],
    "additionalProperties": False,
}

MANIFEST = ToolManifest(
    name="create_reminder",
    description=(
        "Programme un rappel pour l'utilisateur : il recevra un message Slack à l'heure dite. "
        "À utiliser dès qu'il demande d'être rappelé, prévenu ou relancé à un moment donné."
    ),
    schema=SCHEMA,
    effect=Effect.WRITE,
    taints_context=False,       # n'introduit aucun contenu extérieur dans le contexte
    reversible=True,            # bouton « annuler » → suppression de la carte
    scope="données kanban de l'utilisateur",
    visibility=True,            # la confirmation apparaît dans le fil, immédiatement
    # 3 par tour : « crée-moi trois rappels » doit fonctionner. 20 par jour : plafond de dégâts
    # d'une boucle qui s'emballerait, sans gêner un usage réel (roadmap §3.5).
    rate_limit=RateLimit(per_turn=3, per_day=20),
    egress=None,
)


def _parse_time(raw: str | None) -> tuple[int, int]:
    if not raw:
        h, m = DEFAULT_TIME.split(":")
        return int(h), int(m)
    try:
        h_s, _, m_s = str(raw).partition(":")
        h, m = int(h_s), int(m_s or 0)
    except ValueError:
        raise ToolError(f"heure illisible : {raw!r} (format attendu HH:MM)")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ToolError(f"heure hors bornes : {raw!r}")
    return h, m


def resolve_due_at(args: dict, now: datetime) -> datetime:
    """Résout les composants du modèle en un datetime aware, dans le fuseau de l'utilisateur.

    `now` est **passé en argument** : c'est ce qui rend cette fonction testable sans horloge, et
    ce qui garantit que le modèle ne fournit jamais la référence temporelle.
    """
    mode = args.get("date_mode")

    if mode == "in_minutes":
        minutes = args.get("in_minutes")
        if not isinstance(minutes, int) or minutes <= 0:
            raise ToolError("`in_minutes` doit être un entier positif")
        return now + timedelta(minutes=minutes)

    h, m = _parse_time(args.get("time"))

    if mode == "offset_days":
        days = args.get("offset_days")
        if not isinstance(days, int) or days < 0:
            raise ToolError("`offset_days` doit être un entier positif ou nul")
        target = (now + timedelta(days=days)).replace(hour=h, minute=m, second=0, microsecond=0)

    elif mode == "weekday":
        wanted = _JOURS.get(str(args.get("weekday") or "").lower())
        if wanted is None:
            raise ToolError(f"jour de la semaine inconnu : {args.get('weekday')!r}")
        delta = (wanted - now.weekday()) % 7
        candidate = (now + timedelta(days=delta)).replace(hour=h, minute=m, second=0, microsecond=0)
        # « mardi » un mardi à 15h alors qu'il est 18h désigne le mardi suivant, pas une heure
        # déjà passée : la prochaine occurrence est toujours dans le futur.
        if candidate <= now:
            candidate += timedelta(days=7)
        target = candidate

    elif mode == "absolute":
        raw = str(args.get("date") or "")
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            raise ToolError(f"date illisible : {raw!r} (format attendu AAAA-MM-JJ)")
        target = d.replace(hour=h, minute=m, tzinfo=TZ)

    else:
        raise ToolError(f"`date_mode` inconnu : {mode!r}")

    return target


async def _resolve(args: dict, ctx: ToolContext) -> PreparedCall:
    title = str(args.get("title") or "").strip()
    if not title:
        raise ToolError("titre vide : précise ce qu'il faut rappeler")
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX].rstrip() + "…"

    now = now_local()
    due_at = resolve_due_at(args, now)

    # Bornes vérifiées **après** résolution, sur la valeur réelle. Une date passée ou aberrante
    # est refusée avec un message clair, jamais corrigée en silence : c'est en la voyant refusée
    # que l'utilisateur comprend que sa formulation était ambiguë.
    if due_at < now - PAST_TOLERANCE:
        raise ToolError(
            f"la date résolue est dans le passé ({format_local(due_at)}). "
            f"Demande à l'utilisateur de préciser le jour et l'heure."
        )
    if due_at > now + HORIZON_MAX:
        raise ToolError(
            f"la date résolue est trop lointaine ({format_local(due_at)}) — "
            f"probablement une erreur d'interprétation."
        )

    return PreparedCall(
        resolved={"title": title, "due_at": due_at.isoformat()},
        summary=f"*{title}* — {format_local(due_at)}",
    )


async def _target_column() -> str:
    """Colonne de destination : `Rappels` sur le board par défaut, créée à la volée.

    Le board par défaut est créé s'il n'en existe aucun — sinon un premier rappel échouerait sur
    une base neuve, ce qui n'est pas une erreur que l'utilisateur peut comprendre depuis Slack.
    """
    board = await kanban_svc.get_default_board()
    if not board:
        boards = await kanban_svc.list_boards()
        board = boards[0] if boards else await kanban_svc.create_board(
            DEFAULT_BOARD_NAME, is_default=True
        )
    col = await kanban_svc.ensure_column(str(board["id"]), REMINDER_COLUMN)
    return str(col["id"])


def build_posterior_blocks(card_id: str, title: str, due_at: datetime) -> list[dict]:
    """Confirmation *a posteriori* : le rappel existe déjà, on montre quoi et quand.

    Régime réservé au contexte propre (roadmap §3.3) : la portée est d'un message, l'erreur est
    visible immédiatement, et l'annulation tient en un clic — profil de risque sans commune
    mesure avec un diff de doc système, qui reste lui en approbation *préalable*.
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":alarm_clock: Rappel programmé : *{title}*\n{format_local(due_at)}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "agent_reminder_edit",
                    "text": {"type": "plain_text", "text": "Éditer"},
                    "value": card_id,
                },
                {
                    "type": "button",
                    "action_id": "agent_reminder_cancel",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Annuler"},
                    "value": card_id,
                },
            ],
        },
    ]


async def _execute(resolved: dict, ctx: ToolContext) -> ToolResult:
    """Écrit la carte. Reçoit le payload **résolu** — jamais les arguments bruts du modèle.

    Cette fonction est appelée soit directement (contexte propre), soit depuis le clic
    « Confirmer » (contexte tainté) : dans les deux cas avec le payload figé à la résolution,
    donc avec exactement la date qui a été affichée à l'utilisateur.
    """
    title = resolved["title"]
    due_at = datetime.fromisoformat(resolved["due_at"])

    column_id = await _target_column()
    card = await kanban_svc.create_card(column_id, title, description=None, due_date=due_at)
    card_id = str(card["id"])

    logger.info("create_reminder: carte %s créée — %r à %s", card_id, title, due_at.isoformat())

    return ToolResult(
        payload={
            "status": "créé",
            "card_id": card_id,
            "title": title,
            "due_at_local": format_local(due_at),
            "note": "Le rappel est programmé et confirmé à l'utilisateur dans le fil, "
                    "avec un bouton pour l'annuler ou l'éditer. Ne répète pas la date, "
                    "contente-toi d'un acquittement bref.",
        },
        slack_blocks=build_posterior_blocks(card_id, title, due_at),
        slack_text=f"Rappel programmé : {title} — {format_local(due_at)}",
    )


SPEC = ToolSpec(manifest=MANIFEST, execute=_execute, resolve=_resolve)
