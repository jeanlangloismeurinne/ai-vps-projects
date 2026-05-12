import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.database import init_pool, close_pool
from app.config import settings
from app.api import positions, calendar, portfolio, watchlist, analysts, trigger, feedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio Tracker", version="1.0.0")
scheduler = AsyncIOScheduler(timezone="Europe/Paris")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions.router)
app.include_router(calendar.router)
app.include_router(portfolio.router)
app.include_router(watchlist.router)
app.include_router(analysts.router)
app.include_router(trigger.router)
app.include_router(feedback.router)

from app.api import market, dust_runs, portfolio_settings as portfolio_settings_api
app.include_router(market.router)
app.include_router(dust_runs.router)
app.include_router(portfolio_settings_api.router)


@app.on_event("startup")
async def startup():
    await init_pool(settings.DATABASE_URL)

    scheduler.add_job(
        _daily_check,
        CronTrigger(hour=7, minute=0, timezone="Europe/Paris"),
        id="daily_check", replace_existing=True,
    )
    scheduler.add_job(
        _weekly_review,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Europe/Paris"),
        id="weekly_review", replace_existing=True,
    )
    scheduler.add_job(
        _refresh_watchlist_prices,
        CronTrigger(hour=7, minute=30, timezone="Europe/Paris"),
        id="watchlist_price_refresh", replace_existing=True,
    )
    scheduler.add_job(
        _refresh_market_temperature,
        CronTrigger(day_of_week="mon", hour=8, minute=15, timezone="Europe/Paris"),
        id="market_temperature_refresh", replace_existing=True,
    )
    scheduler.add_job(
        _refresh_all_calendars,
        CronTrigger(day_of_week="mon", hour=8, minute=30, timezone="Europe/Paris"),
        id="weekly_calendar_refresh", replace_existing=True,
    )
    scheduler.add_job(
        _refresh_watchlist_peer_calendars,
        CronTrigger(day_of_week="fri", hour=18, minute=0, timezone="Europe/Paris"),
        id="weekly_watchlist_peer_calendar_refresh", replace_existing=True,
    )
    scheduler.start()
    logger.info("Portfolio Tracker démarré")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    await close_pool()


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _daily_check():
    from app.calendar.event_router import EventRouter
    await EventRouter().process_daily_events()


async def _weekly_review():
    from app.portfolio.portfolio_view import PortfolioView
    from app.notifications.slack_notifier import SlackNotifier
    snapshot = await PortfolioView().generate_snapshot()
    await SlackNotifier().send_weekly_digest(snapshot)


async def _refresh_watchlist_prices():
    from app.calendar.watchlist_monitor import WatchlistMonitor
    await WatchlistMonitor().check_prices()


async def _refresh_market_temperature():
    from app.data_collection.m4_macro import get_market_temperature
    from app.db.database import get_db_session
    from app.config import settings
    try:
        data = await get_market_temperature(settings.FRED_API_KEY)
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO market_indicators
                    (buffett_ratio, buffett_trend, cape_ratio, cape_trend,
                     temperature, cash_target_pct, raw_data_json)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
                data.get("buffett_ratio_pct"), data.get("buffett_trend"),
                data.get("cape_ratio"), data.get("cape_trend"),
                data.get("temperature"), data.get("cash_target_pct"),
                data.get("raw_data"),
            )
    except Exception as e:
        logger.error(f"Market temperature refresh error: {e}")


async def _refresh_all_calendars():
    from app.calendar.calendar_builder import CalendarBuilder
    try:
        await CalendarBuilder().refresh_all()
    except Exception as e:
        logger.error(f"Calendar refresh_all error: {e}")


async def _refresh_watchlist_peer_calendars():
    import json
    from app.db.database import get_db_session
    async with get_db_session() as db:
        items = await db.fetch(
            "SELECT ticker, schema_json_draft FROM watchlist WHERE status IN ('watching', 'validated')"
        )
    for item in items:
        try:
            draft = item["schema_json_draft"] or {}
            peers = draft.get("peers", [])
            if isinstance(peers, list):
                for peer in peers[:5]:
                    peer_ticker = peer if isinstance(peer, str) else peer.get("ticker", "")
                    if peer_ticker:
                        import yfinance as yf
                        from app.db.database import get_db_session as _gs
                        try:
                            t = yf.Ticker(peer_ticker)
                            cal = t.calendar
                            if cal is not None and not cal.empty:
                                earnings_date = cal.columns[0] if hasattr(cal, 'columns') else None
                                if earnings_date:
                                    async with _gs() as db2:
                                        await db2.execute("""
                                            INSERT INTO calendar_events
                                                (ticker, event_type, event_date, source, notes)
                                            VALUES ($1,'earnings',$2,'yfinance','watchlist_peer')
                                            ON CONFLICT DO NOTHING
                                        """, peer_ticker, earnings_date)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Watchlist peer calendar error for {item['ticker']}: {e}")
