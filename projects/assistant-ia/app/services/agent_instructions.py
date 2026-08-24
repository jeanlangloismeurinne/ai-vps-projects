"""
Service d'accès à agent_instruction_queue et agent_weekly_job_log.

Responsabilités :
- Enregistrer une nouvelle consigne @admin (INSERT verbatim, status='pending')
- Vérifier et enregistrer le déclenchement du job hebdomadaire (patron ON CONFLICT DO NOTHING)
"""
import logging
from app.db import get_pool

logger = logging.getLogger(__name__)


async def enqueue_instruction(content: str, user_id: str | None, slack_ts: str | None) -> str:
    """
    Insère une consigne dans agent_instruction_queue (status='pending').

    Le contenu est stocké verbatim — jamais interprété ici.
    Retourne l'id UUID de la ligne créée.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO agent_instruction_queue (content, user_id, slack_ts, status)
        VALUES ($1, $2, $3, 'pending')
        RETURNING id
        """,
        content, user_id, slack_ts,
    )
    return str(row["id"])


async def claim_weekly_job(job_name: str, iso_week: str) -> bool:
    """
    Tente d'enregistrer le déclenchement du job pour la semaine iso_week.

    Retourne True si ce run est le premier de la semaine (claim réussi),
    False si un run existe déjà (ON CONFLICT DO NOTHING).

    Patron identique à journal_notifications : UNIQUE (job_name, iso_week) + ON CONFLICT DO NOTHING.
    """
    pool = await get_pool()
    result = await pool.execute(
        """
        INSERT INTO agent_weekly_job_log (job_name, iso_week)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        job_name, iso_week,
    )
    # asyncpg renvoie "INSERT 0 1" si insertion réussie, "INSERT 0 0" si conflit
    return result == "INSERT 0 1"
