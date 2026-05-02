import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import json

_pool: asyncpg.Pool | None = None


async def init_pool(database_url: str):
    global _pool
    # asyncpg expects postgresql:// not postgresql+asyncpg://
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _init_connection(conn):
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    _pool = await asyncpg.create_pool(
        url,
        min_size=1,
        max_size=10,
        init=_init_connection,
    )


async def close_pool():
    if _pool:
        await _pool.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[asyncpg.Connection, None]:
    async with _pool.acquire() as conn:
        yield conn
