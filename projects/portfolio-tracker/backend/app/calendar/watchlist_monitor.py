import logging
from app.db.database import get_db_session
from app.data_collection.m1_quantitative import collect_quantitative
from app.notifications.slack_notifier import SlackNotifier
from app.config import settings

logger = logging.getLogger(__name__)


class WatchlistMonitor:

    async def check_prices(self):
        async with get_db_session() as db:
            items = await db.fetch("SELECT * FROM watchlist WHERE status = 'watching'")

        notifier = SlackNotifier()
        for row in items:
            item = dict(row)
            ticker = item["ticker"]
            try:
                m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
                current_price = m1.get("price", {}).get("current_price")
                if not current_price:
                    continue

                entry_target = item.get("entry_price_target")
                gap = round((float(current_price) / float(entry_target) - 1) * 100, 2) if entry_target else None

                trigger_price = item.get("trigger_alert_price")
                alert_triggered = trigger_price and float(current_price) <= float(trigger_price)

                # Calcul readiness score
                from app.db.database import get_db_session as _gs
                async with _gs() as db2:
                    market_row = await db2.fetchrow(
                        "SELECT temperature FROM market_indicators ORDER BY fetched_at DESC LIMIT 1"
                    )
                    score, _ = _compute_readiness(item, market_row)

                    if alert_triggered and not item.get("alert_triggered_at"):
                        await db2.execute("""
                            UPDATE watchlist
                            SET current_price=$1, gap_to_entry=$2, readiness_score=$3,
                                last_checked=NOW(), alert_triggered_at=NOW(), alert_acknowledged=FALSE
                            WHERE id=$4
                        """, current_price, gap, score, item["id"])
                    else:
                        await db2.execute("""
                            UPDATE watchlist
                            SET current_price=$1, gap_to_entry=$2, readiness_score=$3,
                                last_checked=NOW()
                            WHERE id=$4
                        """, current_price, gap, score, item["id"])

                if alert_triggered and not item.get("alert_triggered_at"):
                    await notifier.send_watchlist_alert(ticker, float(current_price), float(trigger_price))
                    logger.info(f"Watchlist alert sent for {ticker} at {current_price}")

            except Exception as e:
                logger.warning(f"Watchlist check error for {ticker}: {e}")


def _compute_readiness(item: dict, market_row=None) -> tuple:
    score = 0
    breakdown = {}

    gap = item.get("gap_to_entry")
    if gap is not None:
        gap_val = float(gap)
        gap_pts = 40 if gap_val <= 2 else 30 if gap_val <= 5 else 20 if gap_val <= 10 else 0
    else:
        gap_pts = 0
    score += gap_pts
    breakdown["gap_to_entry"] = gap_pts

    cash_pts = 30 if item.get("cash_ready") else 0
    score += cash_pts
    breakdown["cash_ready"] = cash_pts

    brief = item.get("scout_brief") or ""
    brief_pts = 20 if len(brief) > 100 else 0
    score += brief_pts
    breakdown["scout_brief"] = brief_pts

    temp = market_row["temperature"] if market_row else None
    temp_pts = 10 if temp in ("cold", "neutral") else 0
    score += temp_pts
    breakdown["market_temperature"] = temp_pts

    return score, breakdown
