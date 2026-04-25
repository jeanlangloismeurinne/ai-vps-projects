import asyncpg
import logging
from datetime import date
from app.db import get_pool

logger = logging.getLogger(__name__)


async def store_prompt(slack_ts: str, prompt_date: date) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO journal_prompts (slack_ts, prompt_date) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        slack_ts, prompt_date,
    )


async def get_today_prompt(today: date) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM journal_prompts WHERE prompt_date = $1", today
    )


async def store_entry(content: str, slack_ts: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO journal_entries (content, slack_ts) VALUES ($1, $2) ON CONFLICT (slack_ts) DO NOTHING",
        content, slack_ts,
    )
    logger.info(f"Journal entry stored: ts={slack_ts}")


async def has_entry_today(today: date) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT 1 FROM journal_entries WHERE created_at::date = $1", today
    )
    return row is not None


async def get_all_entries() -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT id, content, slack_ts, created_at FROM journal_entries ORDER BY created_at DESC"
    )


async def is_journal_thread(thread_ts: str) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT 1 FROM journal_prompts WHERE slack_ts = $1", thread_ts
    )
    return row is not None
