"""
DataService — couche d'accès aux données de marché.

Flux lecture  : Redis (TTL court) → DB (TTL long) → source externe
Flux écriture : source externe → DB (persistant) → Redis (chaud)

Deux méthodes par type de données :
  get_*()     — lecture avec cache, coût minimal pour l'utilisateur
  refresh_*() — fetch forcé depuis la source, toujours stocké en DB avec contexte
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.data_collection.data_cache import cache_get, cache_set, cache_delete
from app.db.database import get_db_session

logger = logging.getLogger(__name__)

TTL_M1 = 4 * 3600            # 4h — prix, valorisation, financials
TTL_CALENDAR = 7 * 24 * 3600  # 7j — dates earnings


class DataService:

    # ------------------------------------------------------------------ M1

    async def get_m1(self, ticker: str, fmp_api_key: str) -> dict:
        """Lecture avec cache : Redis → DB (< 4h) → yfinance."""
        key = f"pt:m1:{ticker}"

        hit = await cache_get(key)
        if hit:
            logger.debug(f"M1 Redis hit: {ticker}")
            return hit

        db_data = await self._db_m1_recent(ticker, max_age_hours=4)
        if db_data:
            await cache_set(key, db_data, TTL_M1)
            return db_data

        data = await self._fetch_m1(ticker, fmp_api_key)
        await self._db_store_m1(ticker, data, "api")
        await cache_set(key, data, TTL_M1)
        return data

    async def refresh_m1(self, ticker: str, fmp_api_key: str, context: str) -> dict:
        """Fetch forcé depuis yfinance/FMP. Toujours stocké en DB avec le contexte fourni."""
        data = await self._fetch_m1(ticker, fmp_api_key)
        await self._db_store_m1(ticker, data, context)
        await cache_set(f"pt:m1:{ticker}", data, TTL_M1)
        return data

    # ------------------------------------------------------------------ Calendar

    async def get_calendar(self, ticker: str) -> dict:
        """Lecture avec cache : Redis → DB (< 7j) → yfinance."""
        key = f"pt:calendar:{ticker}"

        hit = await cache_get(key)
        if hit:
            return hit

        db_data = await self._db_calendar_recent(ticker, max_age_days=7)
        if db_data:
            await cache_set(key, db_data, TTL_CALENDAR)
            return db_data

        data = await self._fetch_calendar(ticker)
        await self._db_store_calendar(ticker, data)
        await cache_set(key, data, TTL_CALENDAR)
        return data

    async def refresh_calendar(self, ticker: str) -> dict:
        """Fetch forcé du calendrier. Toujours stocké en DB."""
        data = await self._fetch_calendar(ticker)
        await self._db_store_calendar(ticker, data)
        await cache_set(f"pt:calendar:{ticker}", data, TTL_CALENDAR)
        return data

    # ------------------------------------------------------------------ Invalidation

    async def invalidate(self, ticker: str):
        await cache_delete(f"pt:m1:{ticker}", f"pt:calendar:{ticker}")

    # ------------------------------------------------------------------ Internals M1

    async def _fetch_m1(self, ticker: str, fmp_api_key: str) -> dict:
        from app.data_collection.m1_quantitative import collect_quantitative
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, collect_quantitative, ticker, fmp_api_key)

    async def _db_m1_recent(self, ticker: str, max_age_hours: int) -> Optional[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        async with get_db_session() as db:
            row = await db.fetchrow("""
                SELECT raw_json FROM market_snapshots
                WHERE ticker = $1 AND captured_at > $2
                ORDER BY captured_at DESC LIMIT 1
            """, ticker, cutoff)
        return row["raw_json"] if row else None

    async def _db_store_m1(self, ticker: str, data: dict, context: str):
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO market_snapshots (ticker, context, raw_json)
                VALUES ($1, $2, $3)
            """, ticker, context, data)

    # ------------------------------------------------------------------ Internals Calendar

    async def _fetch_calendar(self, ticker: str) -> dict:
        from app.data_collection.m2_events import get_earnings_calendar
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_earnings_calendar, ticker)

    async def _db_calendar_recent(self, ticker: str, max_age_days: int) -> Optional[dict]:
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        async with get_db_session() as db:
            row = await db.fetchrow("""
                SELECT next_earnings_date, trigger_brief_date, trigger_review_date, source
                FROM earnings_calendar_cache
                WHERE ticker = $1 AND fetched_at > $2
            """, ticker, cutoff)
        if not row:
            return None
        return {
            "ticker": ticker,
            "next_earnings_date": str(row["next_earnings_date"]) if row["next_earnings_date"] else None,
            "trigger_brief_date": str(row["trigger_brief_date"]) if row["trigger_brief_date"] else None,
            "trigger_review_date": str(row["trigger_review_date"]) if row["trigger_review_date"] else None,
            "source": row["source"],
        }

    async def _db_store_calendar(self, ticker: str, data: dict):
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO earnings_calendar_cache
                    (ticker, next_earnings_date, trigger_brief_date, trigger_review_date, source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (ticker) DO UPDATE SET
                    next_earnings_date  = EXCLUDED.next_earnings_date,
                    trigger_brief_date  = EXCLUDED.trigger_brief_date,
                    trigger_review_date = EXCLUDED.trigger_review_date,
                    source              = EXCLUDED.source,
                    fetched_at          = NOW()
            """, ticker,
                data.get("next_earnings_date"),
                data.get("trigger_brief_date"),
                data.get("trigger_review_date"),
                data.get("source", "yfinance"),
            )
