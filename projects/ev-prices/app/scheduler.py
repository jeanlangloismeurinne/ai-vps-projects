import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import AsyncSessionLocal
from app.scrapers import ALL_SCRAPERS
from app import progress

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def run_all_scrapers(trigger: str = "scheduled") -> list[dict]:
    logger.info("Lancement du scraping hebdomadaire")
    progress.start(ALL_SCRAPERS, trigger=trigger)
    results = []
    async with AsyncSessionLocal() as db:
        for ScraperClass in ALL_SCRAPERS:
            progress.set_running(ScraperClass.MANUFACTURER_SLUG)
            scraper = ScraperClass(db)
            result = await scraper.run()
            progress.set_done(ScraperClass.MANUFACTURER_SLUG, result)
            results.append(result)
            logger.info(f"  {result}")
    return results


def start_scheduler():
    scheduler.add_job(
        run_all_scrapers,
        CronTrigger(day_of_week="mon", hour=5, minute=0),
        id="weekly_scrape",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler démarré — scraping tous les lundis à 5h (Europe/Paris)")


def stop_scheduler():
    scheduler.shutdown(wait=False)
