import asyncpg
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def run_migrations():
    pool = await get_pool()
    sql = (Path(__file__).parent.parent / "migrations" / "001_initial.sql").read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Migrations applied")
