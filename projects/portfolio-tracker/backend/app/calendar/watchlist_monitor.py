import logging
from app.db.database import get_db_session
from app.data_collection.m1_quantitative import collect_quantitative
from app.notifications.slack_notifier import SlackNotifier
from app.config import settings

logger = logging.getLogger(__name__)


class WatchlistMonitor:

    async def check_prices(self):
        async with get_db_session() as db:
            items = await db.fetch("""
                SELECT * FROM watchlist WHERE status = 'watching'
            """)

        notifier = SlackNotifier()
        for row in items:
            item = dict(row)
            ticker = item["ticker"]
            try:
                m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
                current_price = m1.get("price", {}).get("current_price")
                if not current_price:
                    continue

                gap_to_entry = None
                entry_target = item.get("entry_price_target")
                if entry_target:
                    gap_to_entry = round((current_price / float(entry_target) - 1) * 100, 2)

                async with get_db_session() as db:
                    await db.execute("""
                        UPDATE watchlist
                        SET current_price = $1, gap_to_entry = $2, last_checked = NOW()
                        WHERE id = $3
                    """, current_price, gap_to_entry, item["id"])

                trigger_price = item.get("trigger_alert_price")
                if trigger_price and current_price <= float(trigger_price):
                    await notifier.send_watchlist_alert(ticker, current_price, float(trigger_price))
                    logger.info(f"Watchlist alert sent for {ticker} at {current_price}")

            except Exception as e:
                logger.warning(f"Watchlist check error for {ticker}: {e}")
