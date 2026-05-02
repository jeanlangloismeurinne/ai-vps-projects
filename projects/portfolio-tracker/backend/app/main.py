import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.database import init_pool, close_pool
from app.config import settings
from app.api import positions, calendar, portfolio, watchlist, analysts, trigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio Tracker", version="1.0.0")
scheduler = AsyncIOScheduler(timezone="Europe/Paris")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions.router)
app.include_router(calendar.router)
app.include_router(portfolio.router)
app.include_router(watchlist.router)
app.include_router(analysts.router)
app.include_router(trigger.router)


@app.on_event("startup")
async def startup():
    await init_pool(settings.DATABASE_URL)

    scheduler.add_job(
        _daily_check,
        CronTrigger(hour=7, minute=0, timezone="Europe/Paris"),
        id="daily_check", replace_existing=True,
    )
    scheduler.add_job(
        _weekly_review,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Europe/Paris"),
        id="weekly_review", replace_existing=True,
    )
    scheduler.start()
    logger.info("Portfolio Tracker démarré")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    await close_pool()


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _daily_check():
    from app.calendar.event_router import EventRouter
    await EventRouter().process_daily_events()


async def _weekly_review():
    from app.portfolio.portfolio_view import PortfolioView
    from app.notifications.slack_notifier import SlackNotifier
    snapshot = await PortfolioView().generate_snapshot()
    await SlackNotifier().send_weekly_digest(snapshot)
