"""
Approbation humaine d'une proposition de doc système, dans `#feedback-assistant` (#1787559677496).

Ce module construit le message Block Kit et traite les clics. Il ne décide rien lui-même : la
logique transactionnelle est dans `agent_versioning`, ce qui garantit qu'il n'existe qu'un seul
chemin d'activation d'une version.
"""
import logging

from app.config import settings
from app.db import get_pool
from app.services import agent_versioning
from app.services.agent_versioning import NotAuthorized
from app.services.slack_client import post_blocks

logger = logging.getLogger(__name__)

_DIFF_MAX = 2800   # Slack tronque un bloc texte à 3000 caractères


def _truncate_diff(diff: str) -> str:
    if len(diff) <= _DIFF_MAX:
        return diff
    return diff[:_DIFF_MAX] + "\n… (diff tronqué — voir la page d'édition)"


def build_blocks(proposal_id: str, diff: str, from_version: int | None, n_instructions: int) -> list:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Proposition de révision du document système*\n"
                    f"Version de base : `v{from_version}` · {n_instructions} consigne(s) intégrée(s)"
                ),
            },
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"```{_truncate_diff(diff)}```"}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "agent_doc_approve",
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Approuver"},
                    "value": proposal_id,
                    # Un clic crée une nouvelle version active : on force une confirmation, le
                    # bouton est juste à côté de « Rejeter ».
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Approuver la révision ?"},
                        "text": {"type": "mrkdwn", "text": "Une nouvelle version du document "
                                                           "système sera créée et activée."},
                        "confirm": {"type": "plain_text", "text": "Approuver"},
                        "deny": {"type": "plain_text", "text": "Annuler"},
                    },
                },
                {
                    "type": "button",
                    "action_id": "agent_doc_reject",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Rejeter"},
                    "value": proposal_id,
                },
                {
                    "type": "button",
                    "action_id": "agent_doc_edit",
                    "text": {"type": "plain_text", "text": "Éditer"},
                    "url": f"{settings.ASSISTANT_BASE_URL}/agent/system-doc",
                    "value": proposal_id,
                },
            ],
        },
    ]


async def post_proposal(proposal_id: str) -> None:
    """Poste la proposition pour décision et mémorise le ts du message."""
    pool = await get_pool()
    prop = await pool.fetchrow(
        "SELECT diff, from_version, instruction_ids FROM agent_proposals WHERE id = $1", proposal_id
    )
    if not prop:
        logger.error("agent_approval: proposition %s introuvable", proposal_id)
        return

    ts = await post_blocks(
        channel=settings.ASSISTANT_FEEDBACK_CHANNEL_ID,
        blocks=build_blocks(
            proposal_id, prop["diff"], prop["from_version"],
            len(prop["instruction_ids"] or []),
        ),
        text="Proposition de révision du document système",
    )
    await pool.execute(
        "UPDATE agent_proposals SET slack_ts = $1, channel_id = $2 WHERE id = $3",
        ts, settings.ASSISTANT_FEEDBACK_CHANNEL_ID, proposal_id,
    )


def _unauthorized_text(user_id: str | None) -> str:
    """Message actionnable : sans allowlist configurée, personne ne peut approuver — autant dire
    tout de suite quel identifiant ajouter."""
    if not agent_versioning.approvers():
        return (
            ":lock: Aucun approbateur configuré : personne ne peut approuver de révision.\n"
            f"Ajoute `AGENT_APPROVERS={user_id}` dans les variables d'environnement Coolify "
            "d'assistant-ia, puis relance un déploiement."
        )
    return f":lock: <@{user_id}> n'est pas autorisé à décider d'une révision du document système."


async def handle_decision(action: str, proposal_id: str, user_id: str | None) -> str:
    """Applique la décision et renvoie le texte qui remplacera le message Slack."""
    try:
        if action == "approve":
            result = await agent_versioning.approve_proposal(proposal_id, user_id or "")
            prefix = ":white_check_mark:" if result.applied else ":information_source:"
        else:
            result = await agent_versioning.reject_proposal(proposal_id, user_id or "")
            prefix = ":x:" if result.applied else ":information_source:"
    except NotAuthorized:
        logger.warning("agent_approval: décision refusée — %s non autorisé", user_id)
        return _unauthorized_text(user_id)
    except Exception:
        logger.exception("agent_approval: échec du traitement de la décision")
        return ":warning: Le traitement de la décision a échoué. Le document système est inchangé."

    return f"{prefix} {result.message}\n_Décision de <@{user_id}>._"
