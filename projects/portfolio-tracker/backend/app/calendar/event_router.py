import logging
from datetime import date, datetime
from app.db.database import get_db_session
from app.agents.dust_client import DustClient
from app.agents.portfolio_agent import run_regime_2, run_pre_event_brief
from app.agents.sector_pulse import run_sector_pulse
from app.data_collection.m1_quantitative import collect_quantitative, collect_peers_quantitative
from app.data_collection.m2_events import collect_m2
from app.data_collection.assembler import assemble_data_brief
from app.notifications.slack_notifier import SlackNotifier
from app.config import settings
from app.calendar.watchlist_monitor import WatchlistMonitor

logger = logging.getLogger(__name__)


class EventRouter:

    async def process_daily_events(self):
        today = date.today()
        logger.info(f"Processing daily events for {today}")

        await self._process_pre_event_briefs(today)
        await self._process_regime2_reviews(today)
        await self._process_sector_pulses(today)
        await WatchlistMonitor().check_prices()

    async def _process_pre_event_briefs(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch("""
                SELECT ce.*, p.company_name, p.id as position_id
                FROM calendar_events ce
                JOIN positions p ON p.ticker = ce.ticker
                WHERE ce.trigger_brief_date = $1
                AND ce.brief_processed = FALSE
                AND p.status = 'active'
            """, today)

        if not events:
            return

        dust = DustClient()
        notifier = SlackNotifier()

        for event in events:
            event = dict(event)
            ticker = event["ticker"]
            try:
                async with get_db_session() as db:
                    hypotheses = await db.fetch(
                        "SELECT * FROM hypotheses WHERE position_id = $1 AND current_status != 'invalidated'",
                        event["position_id"]
                    )

                brief = await run_pre_event_brief(
                    ticker=ticker,
                    company_name=event["company_name"],
                    hypotheses=[dict(h) for h in hypotheses],
                    event_type=event["event_type"],
                    guidance_published={},
                    dust_client=dust,
                )
                await notifier.send_pre_event_brief(ticker, brief, event)

                async with get_db_session() as db:
                    await db.execute(
                        "UPDATE calendar_events SET brief_processed = TRUE WHERE id = $1",
                        event["id"]
                    )
            except Exception as e:
                logger.error(f"Pre-event brief error for {ticker}: {e}")
                await notifier.send_error_alert(ticker, str(e))

    async def _process_regime2_reviews(self, today: date):
        async with get_db_session() as db:
            events = await db.fetch("""
                SELECT ce.*, p.company_name, p.id as position_id, p.entry_price
                FROM calendar_events ce
                JOIN positions p ON p.ticker = ce.ticker
                WHERE ce.trigger_review_date = $1
                AND ce.processed = FALSE
                AND p.status = 'active'
            """, today)

        if not events:
            return

        dust = DustClient()
        notifier = SlackNotifier()

        for event in events:
            event = dict(event)
            ticker = event["ticker"]
            try:
                await self._run_regime2_for_position(
                    ticker=ticker,
                    position_id=str(event["position_id"]),
                    company_name=event["company_name"],
                    entry_price=float(event["entry_price"]),
                    triggered_by=f"calendar:{event['event_type']}",
                    dust=dust,
                    notifier=notifier,
                )

                async with get_db_session() as db:
                    await db.execute(
                        "UPDATE calendar_events SET processed = TRUE WHERE id = $1",
                        event["id"]
                    )
            except Exception as e:
                logger.error(f"Regime 2 error for {ticker}: {e}")
                await notifier.send_error_alert(ticker, str(e))

    async def _run_regime2_for_position(self, ticker: str, position_id: str,
                                         company_name: str, entry_price: float,
                                         triggered_by: str, dust: DustClient,
                                         notifier: SlackNotifier):
        async with get_db_session() as db:
            thesis = await db.fetchrow(
                "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", position_id
            )
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1", position_id
            )
            pulses = await db.fetch("""
                SELECT * FROM sector_pulses
                WHERE main_position_id = $1 AND accumulated = FALSE
                ORDER BY pulse_date DESC LIMIT 10
            """, position_id)

        m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
        m2 = collect_m2(ticker, company_name)

        thesis_data = None
        if thesis:
            thesis_data = {
                "thesis_one_liner": thesis["thesis_one_liner"],
                "hypotheses": [dict(h) for h in hypotheses],
                "entry_price": entry_price,
                "last_recommendation": None,
            }

        data_brief = assemble_data_brief(
            ticker=ticker,
            m1_data=m1,
            m2_data=m2,
            m3_data=None,
            thesis_data=thesis_data,
            sector_pulses_accumulated=[dict(p) for p in pulses],
            peers_m1_data=None,
        )

        review = await run_regime_2(ticker, company_name, data_brief, dust)

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, hypotheses_scores_json,
                     recommendation, data_brief_json, full_output_json, alert_level)
                VALUES ($1, 2, $2, $3, $4, $5, $6, $7)
            """,
                position_id, triggered_by,
                review.get("hypotheses_scores"),
                review.get("recommendation"),
                data_brief, review,
                review.get("alert_level", "green"),
            )

            if review.get("hypotheses_scores"):
                for score in review["hypotheses_scores"]:
                    await db.execute("""
                        UPDATE hypotheses SET current_status = $1, last_updated = NOW()
                        WHERE position_id = $2 AND code = $3
                    """, score.get("status", "neutral"), position_id, score.get("code"))

            await db.execute("""
                UPDATE sector_pulses SET accumulated = TRUE
                WHERE main_position_id = $1 AND accumulated = FALSE
            """, position_id)

        await notifier.send_regime2_report(ticker, review)

        if review.get("flag") == "REVIEW_REQUIRED":
            logger.info(f"Regime 2 escalation for {ticker}: {review.get('escalation_reason')}")

    async def _process_sector_pulses(self, today: date):
        async with get_db_session() as db:
            peer_events = await db.fetch("""
                SELECT ce.ticker as peer_ticker, ce.event_type,
                    p.ticker as main_ticker, p.id as position_id, p.company_name
                FROM calendar_events ce
                JOIN peers pr ON pr.peer_ticker = ce.ticker
                JOIN positions p ON p.id = pr.position_id
                WHERE ce.trigger_review_date = $1
                AND ce.processed = FALSE
                AND p.status = 'active'
            """, today)

        if not peer_events:
            return

        dust = DustClient()
        notifier = SlackNotifier()

        for event in peer_events:
            event = dict(event)
            peer_ticker = event["peer_ticker"]
            main_ticker = event["main_ticker"]
            try:
                async with get_db_session() as db:
                    hypotheses = await db.fetch(
                        "SELECT * FROM hypotheses WHERE position_id = $1", event["position_id"]
                    )
                    peer_row = await db.fetchrow(
                        "SELECT peer_company_name FROM peers WHERE peer_ticker = $1 AND position_id = $2",
                        peer_ticker, event["position_id"]
                    )

                peer_company = peer_row["peer_company_name"] if peer_row else peer_ticker
                peer_m2 = collect_m2(peer_ticker, peer_company)

                pulse = await run_sector_pulse(
                    peer_ticker=peer_ticker,
                    peer_company=peer_company,
                    main_position_ticker=main_ticker,
                    peer_m2_data=peer_m2,
                    main_hypotheses=[dict(h) for h in hypotheses],
                    dust_client=dust,
                )

                async with get_db_session() as db:
                    await db.execute("""
                        INSERT INTO sector_pulses
                            (peer_ticker, main_position_id, peer_result_summary,
                             hypothesis_impacts_json, pulse_score, action, dust_cost_usd)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        peer_ticker, event["position_id"],
                        pulse.get("peer_result_summary"),
                        pulse.get("hypothesis_impacts"),
                        pulse.get("pulse_score", 0),
                        pulse.get("action", "store"),
                        pulse.get("dust_cost_usd"),
                    )

                if pulse.get("action") == "escalate_to_regime3":
                    await notifier.send_sector_pulse_escalation(main_ticker, peer_ticker, pulse)

            except Exception as e:
                logger.error(f"Sector pulse error for {peer_ticker}/{main_ticker}: {e}")
