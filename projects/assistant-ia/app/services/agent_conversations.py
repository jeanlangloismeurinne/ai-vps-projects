"""
Historique des tours de conversation de l'agent (`agent_conversations`).

Le contenu stocké ici est de la **donnée** : il est relu et renvoyé au modèle comme historique de
conversation, jamais concaténé au prompt système. Un utilisateur ne peut donc pas modifier les
consignes de l'agent en écrivant dans le fil (roadmap §5.1).
"""
import logging

from app.db import get_pool

logger = logging.getLogger(__name__)


async def save_turn(
    *,
    role: str,
    content: str,
    channel_id: str | None,
    user_id: str | None = None,
    slack_ts: str | None = None,
    thread_ts: str | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO agent_conversations
            (role, content, channel_id, user_id, slack_ts, thread_ts)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        role, content, channel_id, user_id, slack_ts, thread_ts,
    )


async def load_recent_turns(channel_id: str, limit: int) -> list[dict]:
    """Les `limit` derniers tours du channel, du plus ancien au plus récent.

    Fenêtre bornée : un historique illimité finirait par dépasser la fenêtre de contexte du modèle
    et par coûter cher à chaque tour. On prend les N derniers puis on réinverse — trier ASC avec
    LIMIT donnerait les N *premiers* tours, c'est-à-dire l'inverse de ce qu'on veut.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT role, content
        FROM agent_conversations
        WHERE channel_id = $1
        ORDER BY created_at DESC, id DESC
        LIMIT $2
        """,
        channel_id, limit,
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
