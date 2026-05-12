import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def init_redis(url: str):
    global _redis
    _redis = aioredis.from_url(url, decode_responses=True)
    logger.info("Redis connecté")


async def close_redis():
    if _redis:
        await _redis.aclose()


async def cache_get(key: str) -> Optional[Any]:
    if not _redis:
        return None
    try:
        raw = await _redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Redis get [{key}]: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int):
    if not _redis:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Redis set [{key}]: {e}")


async def cache_delete(*keys: str):
    if not _redis or not keys:
        return
    try:
        await _redis.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis delete {keys}: {e}")
