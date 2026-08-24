"""
Branches 3 et 5 du dispatcher Slack : chantier `agent-consignes`.

- handle_directive : parsing déterministe de @admin / @update (ticket #1787559677493)
- handle_conversation_turn : tour de conversation dans #assistant (ticket #1787559677494)
"""
import logging
import re

from app.services import agent_conversations, agent_doc
from app.services.agent_instructions import enqueue_instruction
from app.services.agent_tools import loop
from app.services.agent_tools.manifest import TurnState
from app.services.slack_client import post_text, update_text
from app.handlers.agent_synthesis_stub import run_synthesis
from app.config import settings

logger = logging.getLogger(__name__)

# Détection de routage uniquement — le parsing normatif appartient au ticket #1787559677493.
# `\B@` et non `\b@` : `@` n'est pas un caractère de mot, la frontière est donc « non-mot ».
# Un handle Slack réel arrive sous la forme `<@U123ABC>` et ne matche pas ces motifs.
_DIRECTIVE_RE = re.compile(r"(?<![\w<])@(admin|update)\b", re.IGNORECASE)

# Regex pour extraire le contenu après @admin (n'importe où dans le message)
# On retire le token @admin et tout ce qui précède/suit pour isoler la consigne
_ADMIN_PAYLOAD_RE = re.compile(
    r"(?<![\w<])@admin\b\s*(.*?)(?=(?<![\w<])@(?:admin|update)\b|$)",
    re.IGNORECASE | re.DOTALL,
)

# Message d'attente posté avant l'appel au modèle, puis remplacé par la réponse (#1787575776445).
# Sans lui, le fil reste muet plusieurs secondes et rien n'indique que l'agent a reçu le message.
_THINKING_TEXT = "_:hourglass_flowing_sand: je réfléchis…_"

_HELP_TEXT = (
    "*@admin* — Soumettre une consigne à l'agent\n"
    "Usage : `@admin <votre consigne>`\n"
    "Exemple : `@admin Toujours répondre en français formel`\n\n"
    "La consigne est enregistrée en attente de la prochaine synthèse (`@update`)."
)


def detect_directive(text: str) -> str | None:
    """Renvoie 'admin', 'update' ou None. Détection n'importe où dans le message (roadmap §2)."""
    match = _DIRECTIVE_RE.search(text or "")
    return match.group(1).lower() if match else None


def _extract_admin_content(text: str) -> str:
    """
    Extrait le texte de consigne après @admin.

    Parsing 100 % code — jamais un appel LLM (contrainte anti-injection §5.1).
    Le contenu retourné est stocké verbatim ; il n'est jamais interprété ici.
    Retourne une chaîne vide si aucun contenu utile n'est trouvé.
    """
    match = _ADMIN_PAYLOAD_RE.search(text or "")
    if not match:
        return ""
    return match.group(1).strip()


async def handle_directive(event: dict, keyword: str) -> None:
    """
    Traite une directive @admin ou @update détectée dans un message Slack.

    @admin <consigne> :
        - Si consigne vide → message d'aide en thread, rien en base
        - Si consigne non vide → INSERT dans agent_instruction_queue (status='pending'),
          accusé de réception en thread (numéro court = 8 premiers chars de l'UUID)

    @update :
        - Appelle le point d'accroche run_synthesis() (no-op jusqu'au ticket #1787559677495)
        - Accusé de réception en thread

    L'ack Slack 3 s et la dédup sont déjà gérés en amont (tickets #482, #492).
    Ne pas modifier slack_app.py.
    """
    channel = event.get("channel", settings.ASSISTANT_CHANNEL_ID)
    thread_ts = event.get("ts")  # on répond en thread sous le message d'origine
    user_id = event.get("user")
    text = event.get("text", "")

    if keyword == "admin":
        content = _extract_admin_content(text)
        if not content:
            # @admin sans texte utile → aide en thread, rien en base
            logger.info(
                "handle_directive: @admin sans contenu (ts=%s user=%s) → aide envoyée",
                thread_ts, user_id,
            )
            await post_text(channel=channel, text=_HELP_TEXT, thread_ts=thread_ts)
            return

        # INSERT verbatim — le contenu n'est jamais interprété ici
        instruction_id = await enqueue_instruction(
            content=content,
            user_id=user_id,
            slack_ts=thread_ts,
        )
        short_id = instruction_id[:8]  # 8 premiers chars de l'UUID — lisible dans Slack
        ack = f"Consigne enregistrée (n° {short_id}…, en attente de synthèse)."
        logger.info(
            "handle_directive: @admin consigne enregistrée id=%s user=%s ts=%s",
            instruction_id, user_id, thread_ts,
        )
        await post_text(channel=channel, text=ack, thread_ts=thread_ts)

    elif keyword == "update":
        # Déclenche la synthèse via le point d'accroche (ticket #1787559677495)
        logger.info(
            "handle_directive: @update reçu (ts=%s user=%s) → appel run_synthesis",
            thread_ts, user_id,
        )
        await run_synthesis(triggered_by="slack_update")
        await post_text(
            channel=channel,
            text="Synthèse des consignes déclenchée. Le résultat sera posté dans #feedback-assistant pour approbation.",
            thread_ts=thread_ts,
        )

    else:
        logger.warning("handle_directive: keyword inconnu '%s', ignoré", keyword)


async def handle_conversation_turn(event: dict) -> None:
    """
    Un tour de conversation dans `#assistant` (ticket #1787559677494).

    Modèle de sécurité (roadmap §5.1, non négociable) :
    - Le prompt système vient **exclusivement** de `agent_system_doc WHERE active`. Rien d'autre
      n'est concaténé dedans.
    - Le message de l'utilisateur et l'historique partent en rôles `user`/`assistant`, jamais en
      rôle `system` : ce sont des **données**, pas des instructions.
    - Les outils viennent **exclusivement** de `agent_tools.registry`, jamais du doc système
      (roadmap agent-outillage §3.1). Le doc peut dire *quand* utiliser un outil ; il ne peut pas
      en faire exister un.

    Le doc actif est relu à **chaque** tour : approuver un diff change le comportement au tour
    suivant, sans redémarrage.

    Depuis le chantier `agent-outillage`, ce tour n'est plus un simple aller-retour : il passe par
    une boucle bornée qui peut exécuter des outils (`agent_tools.loop`). Ce qui protège n'est plus
    l'absence d'outil, mais la frontière modèle / code de chaque outil et le régime de confirmation
    dérivé de son manifeste.
    """
    channel = event.get("channel", settings.ASSISTANT_CHANNEL_ID)
    slack_ts = event.get("ts")
    user_id = event.get("user")
    text = event.get("text", "")

    # Accusé de réception immédiat (#1787575776445). Posté avant tout appel réseau : c'est le
    # seul signe visible que le message a été reçu pendant les secondes d'attente du modèle.
    # Best-effort — si Slack refuse ce message, le tour se déroule quand même et la réponse
    # est postée normalement : un indicateur d'attente ne doit jamais faire perdre une réponse.
    thinking_ts: str | None = None
    try:
        thinking_ts = await post_text(channel=channel, text=_THINKING_TEXT, thread_ts=slack_ts)
    except Exception:
        logger.warning("agent_chat: indicateur d'attente non posté, on continue", exc_info=True)

    async def respond(message: str) -> None:
        """Remplace l'indicateur d'attente par `message`, ou poste si l'indicateur manque."""
        if thinking_ts:
            try:
                await update_text(channel=channel, ts=thinking_ts, text=message)
                return
            except Exception:
                # L'édition a échoué (message supprimé, droits…) : on retombe sur un post normal
                # plutôt que de laisser l'utilisateur sur « je réfléchis… » indéfiniment.
                logger.warning("agent_chat: chat.update échoué, repli sur post", exc_info=True)
        await post_text(channel=channel, text=message, thread_ts=slack_ts)

    try:
        doc = await agent_doc.get_active_doc()
        if not doc:
            # Sans doc actif, on n'improvise pas un prompt de secours : ce serait un prompt système
            # non versionné et non audité, exactement ce que le chantier interdit.
            logger.error("agent_chat: aucun doc système actif — tour abandonné")
            await respond(
                "Aucun document système actif : je ne peux pas répondre tant qu'une version "
                "n'est pas activée."
            )
            return

        history = await agent_conversations.load_recent_turns(
            channel_id=channel, limit=settings.AGENT_HISTORY_TURNS
        )

        messages = [{"role": "system", "content": doc.content}]
        messages.extend(history)
        messages.append({"role": "user", "content": text})

        turn = TurnState(
            channel_id=channel,
            user_id=user_id,
            slack_ts=slack_ts,
            thread_ts=slack_ts,
            doc_version=doc.version,
        )
        outcome = await loop.run_turn(messages, turn)
        reply = outcome.text.strip() or "Je n'ai pas de réponse à formuler."

        # Les deux tours ne sont enregistrés qu'après une réponse obtenue : un appel en échec ne
        # doit pas laisser un tour `user` orphelin qui polluerait l'historique du tour suivant.
        await agent_conversations.save_turn(
            role="user", content=text, channel_id=channel,
            user_id=user_id, slack_ts=slack_ts, thread_ts=slack_ts,
        )
        await agent_conversations.save_turn(
            role="assistant", content=reply, channel_id=channel,
            thread_ts=slack_ts,
        )

        await respond(reply)
        logger.info(
            "agent_chat: tour traité (ts=%s user=%s doc_version=%s len_reply=%d "
            "iterations=%d outils=%d taint=%s exhausted=%s)",
            slack_ts, user_id, doc.version, len(reply),
            outcome.iterations, outcome.tool_calls_made, turn.taint_sources, outcome.exhausted,
        )

    except Exception as exc:
        # Tâche de fond : une exception non rattrapée serait invisible côté utilisateur.
        logger.exception("agent_chat: échec du tour de conversation")
        try:
            # Passe aussi par `respond` : sinon l'indicateur « je réfléchis… » resterait affiché
            # pour toujours à côté du message d'erreur.
            await respond(
                f"Je n'ai pas pu répondre ({type(exc).__name__}). Réessaie dans un instant."
            )
        except Exception:
            logger.exception("agent_chat: impossible de signaler l'échec dans Slack")
