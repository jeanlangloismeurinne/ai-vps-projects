import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import AsyncSessionLocal
from app.scrapers import ALL_SCRAPERS

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def run_all_scrapers() -> list[dict]:
    logger.info("Lancement du scraping hebdomadaire")
    results = []
    async with AsyncSessionLocal() as db:
        for ScraperClass in ALL_SCRAPERS:
            scraper = ScraperClass(db)
            result = await scraper.run()
            results.append(result)
            logger.info(f"  {result}")
    return results


def start_scheduler():
    scheduler.add_job(
        run_all_scrapers,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="weekly_scrape",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler démarré — scraping tous les lundis à 6h (Europe/Paris)")


def stop_scheduler():
    scheduler.shutdown(wait=False)
