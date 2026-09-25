import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app import alias_digest

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")

# max_instances=1 + coalesce : deux runs d'une même cadence ne se chevauchent jamais, et un
# retard ne se rattrape pas en rafale. misfire_grace_time : un cron manqué de quelques minutes
# (boucle occupée, redémarrage) part quand même — la valeur d'origine (1 s) le sautait sans bruit.
_JOB = dict(max_instances=1, coalesce=True, replace_existing=True, misfire_grace_time=600)


def start_scheduler():
    # Un seul moteur pour tous les alias (la newsletter comprise) : chaque job traite les alias
    # de SA cadence. `minute` = un e-mail de réponse par mail reçu ; matin/soir = un lot par destinataire.
    scheduler.add_job(
        alias_digest.run_frequency, CronTrigger(hour=settings.SUMMARY_HOUR, minute=settings.SUMMARY_MINUTE),
        args=["morning"], id="digest_morning", **_JOB,
    )
    scheduler.add_job(
        alias_digest.run_frequency, CronTrigger(hour=settings.EVENING_HOUR, minute=settings.EVENING_MINUTE),
        args=["evening"], id="digest_evening", **_JOB,
    )
    scheduler.add_job(
        alias_digest.run_frequency, IntervalTrigger(minutes=1),
        args=["minute"], id="digest_minute", **_JOB,
    )
    scheduler.start()
    logger.info(
        "Scheduler démarré — digests matin %02d:%02d, soir %02d:%02d, et chaque minute (Europe/Paris)",
        settings.SUMMARY_HOUR, settings.SUMMARY_MINUTE, settings.EVENING_HOUR, settings.EVENING_MINUTE,
    )


def stop_scheduler():
    scheduler.shutdown(wait=False)
