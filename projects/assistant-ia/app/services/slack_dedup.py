"""
Garde d'idempotence sur les événements Slack.

Slack redélivre un événement tant qu'il n'a pas reçu de 200 sous 3 s. Les branches du dispatcher
qui écrivent en base doivent donc réclamer l'événement avant tout effet de bord.
"""
import logging

from app.db import get_pool

logger = logging.getLogger(__name__)


def event_key(event: dict) -> str:
    """Clé stable d'un message Slack. `client_msg_id` est l'identifiant natif ; il est absent de
    certains messages (intégrations, messages édités), d'où le repli sur channel+ts."""
    client_msg_id = event.get("client_msg_id")
    if client_msg_id:
        return client_msg_id
    return f"{event.get('channel', '')}:{event.get('ts', '')}"


async def claim_event(event: dict) -> bool:
    """Réclame l'événement. Renvoie True si c'est la première fois qu'on le voit (l'appelant peut
    agir), False s'il a déjà été traité (redélivrance → ne rien faire).

    En cas d'erreur base, renvoie True : mieux vaut un doublon éventuel qu'une note utilisateur
    perdue en silence.
    """
    key = event_key(event)
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO slack_event_dedup (event_key, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (event_key) DO NOTHING
            RETURNING event_key
            """,
            key,
            event.get("channel"),
        )
    except Exception:
        logger.exception(f"claim_event: échec de la garde d'idempotence (key={key}) — on laisse passer")
        return True

    if row is None:
        logger.info(f"claim_event: événement déjà traité, ignoré (key={key})")
        return False
    return True
