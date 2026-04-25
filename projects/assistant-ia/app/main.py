import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from pathlib import Path

from app.routes import webhooks, journal, kanban, slack_commands
from app.db import get_pool, close_pool, run_migrations
from app.jobs.journal_prompt import send_daily_prompt, send_reminder
from app.jobs.task_reminder import check_due_cards

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

_paris = pytz.timezone("Europe/Paris")
_scheduler = AsyncIOScheduler(timezone=pytz.UTC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()

    _scheduler.add_job(send_daily_prompt, CronTrigger(hour=19, minute=0, timezone=_paris))
    _scheduler.add_job(send_reminder, CronTrigger(hour=22, minute=0, timezone=_paris))
    _scheduler.add_job(check_due_cards, CronTrigger(minute="*"))
    _scheduler.start()
    logger.info("Scheduler started")

    yield

    _scheduler.shutdown()
    await close_pool()


app = FastAPI(title="assistant-ia", docs_url=None, redoc_url=None, lifespan=lifespan)

_public = Path(__file__).parent.parent / "public"
if _public.exists():
    app.mount("/public", StaticFiles(directory=str(_public)), name="public")

app.include_router(webhooks.router)
app.include_router(journal.router)
app.include_router(kanban.router)
app.include_router(slack_commands.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
