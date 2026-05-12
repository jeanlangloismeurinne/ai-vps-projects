import logging
from datetime import date as _date
from app.db.database import get_db_session
from app.data_collection.data_service import DataService

logger = logging.getLogger(__name__)


def _to_date(s):
    return _date.fromisoformat(s) if s else None


class CalendarBuilder:

    async def build_for_position(self, ticker: str) -> dict:
        cal = await DataService().get_calendar(ticker)
        if not cal.get("next_earnings_date"):
            logger.info(f"No earnings date found for {ticker} — manual entry required")
            return cal

        event_date = _to_date(cal["next_earnings_date"])

        async with get_db_session() as db:
            existing = await db.fetchrow("""
                SELECT id FROM calendar_events
                WHERE ticker = $1 AND event_date = $2 AND event_type = 'earnings'
            """, ticker, event_date)

            if not existing:
                await db.execute("""
                    INSERT INTO calendar_events
                        (ticker, event_type, event_date, trigger_brief_date, trigger_review_date, source)
                    VALUES ($1, 'earnings', $2, $3, $4, $5)
                """,
                    ticker,
                    event_date,
                    _to_date(cal.get("trigger_brief_date")),
                    _to_date(cal.get("trigger_review_date")),
                    cal.get("source", "yfinance"),
                )
                logger.info(f"Calendar entry created for {ticker} on {cal['next_earnings_date']}")

        return cal

    async def refresh_all(self) -> dict:
        async with get_db_session() as db:
            positions = await db.fetch(
                "SELECT ticker FROM positions WHERE status = 'active'"
            )

        results = {}
        for row in positions:
            try:
                results[row["ticker"]] = await self.build_for_position(row["ticker"])
            except Exception as e:
                logger.error(f"Calendar refresh error for {row['ticker']}: {e}")
                results[row["ticker"]] = {"error": str(e)}

        return results
