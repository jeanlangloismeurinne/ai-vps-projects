import logging
from datetime import date
from app.services import journal as journal_svc
from app.services.slack_client import post_text
from app.config import settings

logger = logging.getLogger(__name__)


async def send_daily_prompt():
    today = date.today()
    existing = await journal_svc.get_today_prompt(today)
    if existing:
        logger.info("Journal prompt already sent today, skipping")
        return
    ts = await post_text(
        channel=settings.SLACK_CHANNEL_JOURNAL,
        text="💡 *Quel est ton apprentissage du jour ?*",
    )
    await journal_svc.store_prompt(ts, today)
    logger.info(f"Journal prompt sent for {today}, ts={ts}")


async def send_reminder():
    today = date.today()
    if await journal_svc.has_entry_today(today):
        return
    prompt = await journal_svc.get_today_prompt(today)
    if not prompt:
        return
    await post_text(
        channel=settings.SLACK_CHANNEL_JOURNAL,
        text="⏰ Tu n'as pas encore répondu. Quel est ton apprentissage du jour ?",
        thread_ts=prompt["slack_ts"],
    )
    logger.info("Journal reminder sent")
