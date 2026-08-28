import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app import digest

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


def start_scheduler():
    scheduler.add_job(
        digest.run_daily_digest,
        CronTrigger(hour=settings.SUMMARY_HOUR, minute=settings.SUMMARY_MINUTE),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler démarré — digest quotidien à %02d:%02d (Europe/Paris)",
        settings.SUMMARY_HOUR, settings.SUMMARY_MINUTE,
    )


def stop_scheduler():
    scheduler.shutdown(wait=False)
