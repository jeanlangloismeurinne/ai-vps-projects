"""
Job hebdomadaire : déclenche la synthèse des consignes @admin une fois par semaine.

Tourne chaque minute (via APScheduler CronTrigger). La contrainte UNIQUE sur
agent_weekly_job_log(job_name, iso_week) garantit un seul déclenchement par semaine
même si le worker redémarre — patron identique à journal_notifications.

Jour et heure de déclenchement : lundi 08:00 (Europe/Paris).
"""
import logging
from datetime import datetime
import pytz

from app.services.agent_instructions import claim_weekly_job
from app.handlers.agent_synthesis_stub import run_synthesis

logger = logging.getLogger(__name__)

_paris = pytz.timezone("Europe/Paris")
_JOB_NAME = "agent_synthesis"
_TRIGGER_WEEKDAY = 0   # lundi (0 = Monday, conforme à datetime.weekday())
_TRIGGER_HOUR = 8      # à partir de 08:00 (Europe/Paris)


async def run_agent_weekly_synthesis() -> None:
    """
    Vérifie chaque minute si le job hebdomadaire doit être déclenché.

    Conditions de déclenchement :
    1. C'est lundi (weekday == 0)
    2. Il est 08:00 ou plus tard (Paris)
    3. Aucun run n'a encore eu lieu cette semaine (claim_weekly_job retourne True)
    """
    now = datetime.now(_paris)

    # Fenêtre de déclenchement : lundi, à partir de 08:00.
    # Volontairement une fenêtre et non la minute exacte « 08:00 » : si l'app est redémarrée
    # pile à cette minute (déploiement Coolify), la synthèse sauterait la semaine entière.
    # C'est `claim_weekly_job` qui garantit l'unicité, pas l'étroitesse de la fenêtre.
    if now.weekday() != _TRIGGER_WEEKDAY:
        return
    if now.hour < _TRIGGER_HOUR:
        return

    # Calcul de la semaine ISO (ex: '2026-W35')
    iso_year, iso_week, _ = now.isocalendar()
    iso_week_str = f"{iso_year}-W{iso_week:02d}"

    # Tentative de claim — ON CONFLICT DO NOTHING garantit l'idempotence
    claimed = await claim_weekly_job(_JOB_NAME, iso_week_str)
    if not claimed:
        logger.debug(
            "agent_weekly_synthesis: job déjà exécuté cette semaine (%s), ignoré",
            iso_week_str,
        )
        return

    logger.info(
        "agent_weekly_synthesis: déclenchement semaine %s → run_synthesis",
        iso_week_str,
    )
    await run_synthesis(triggered_by="weekly_job")
