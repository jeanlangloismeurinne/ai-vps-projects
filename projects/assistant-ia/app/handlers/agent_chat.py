"""
Branches 3 et 5 du dispatcher Slack : chantier `agent-consignes`.

- handle_directive : parsing déterministe de @admin / @update (ticket #1787559677493)
- handle_conversation_turn : tour de conversation dans #assistant (ticket #1787559677494)
"""
import logging
import re

from app.services import agent_conversations, agent_doc, deepinfra_client
from app.services.agent_instructions import enqueue_instruction
from app.services.slack_client import post_text
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
    - L'agent n'a **aucun outil** en v1. Le refus d'exécuter est porté par le doc système lui-même
      (il oriente vers `/feature`), pas par du code ici — c'est le doc qui est versionné et audité.

    Le doc actif est relu à **chaque** tour : approuver un diff change le comportement au tour
    suivant, sans redémarrage.
    """
    channel = event.get("channel", settings.ASSISTANT_CHANNEL_ID)
    slack_ts = event.get("ts")
    user_id = event.get("user")
    text = event.get("text", "")

    try:
        doc = await agent_doc.get_active_doc()
        if not doc:
            # Sans doc actif, on n'improvise pas un prompt de secours : ce serait un prompt système
            # non versionné et non audité, exactement ce que le chantier interdit.
            logger.error("agent_chat: aucun doc système actif — tour abandonné")
            await post_text(
                channel=channel,
                text="Aucun document système actif : je ne peux pas répondre tant qu'une version "
                     "n'est pas activée.",
                thread_ts=slack_ts,
            )
            return

        history = await agent_conversations.load_recent_turns(
            channel_id=channel, limit=settings.AGENT_HISTORY_TURNS
        )

        messages = [{"role": "system", "content": doc.content}]
        messages.extend(history)
        messages.append({"role": "user", "content": text})

        reply = await deepinfra_client.chat(
            messages=messages,
            model=settings.DEEPINFRA_MODEL_CHAT,
            temperature=0.3,
        )
        reply = (reply or "").strip() or "Je n'ai pas de réponse à formuler."

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

        await post_text(channel=channel, text=reply, thread_ts=slack_ts)
        logger.info(
            "agent_chat: tour traité (ts=%s user=%s doc_version=%s len_reply=%d)",
            slack_ts, user_id, doc.version, len(reply),
        )

    except Exception as exc:
        # Tâche de fond : une exception non rattrapée serait invisible côté utilisateur.
        logger.exception("agent_chat: échec du tour de conversation")
        try:
            await post_text(
                channel=channel,
                text=f"Je n'ai pas pu répondre ({type(exc).__name__}). Réessaie dans un instant.",
                thread_ts=slack_ts,
            )
        except Exception:
            logger.exception("agent_chat: impossible de signaler l'échec dans Slack")
