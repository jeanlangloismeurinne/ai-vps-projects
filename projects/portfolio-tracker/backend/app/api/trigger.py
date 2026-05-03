import json
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.db.database import get_db_session
from app.agents.dust_client import DustClient, DustBudgetExceededError
from app.agents.research_agent import run_regime_1
from app.agents.portfolio_agent import run_regime_2, run_regime_3
from app.agents.sector_pulse import run_sector_pulse
from app.data_collection.m1_quantitative import collect_quantitative, collect_peers_quantitative
from app.data_collection.m2_events import collect_m2
from app.data_collection.m3_qualitative import collect_m3
from app.data_collection.assembler import assemble_data_brief
from app.notifications.slack_notifier import SlackNotifier
from app.config import settings

router = APIRouter(prefix="/trigger", tags=["trigger"])
logger = logging.getLogger(__name__)


@router.post("/regime1/{ticker}")
async def trigger_regime1(ticker: str, background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")
    background_tasks.add_task(_run_regime1, dict(pos))
    return {"status": "queued", "ticker": ticker, "regime": 1}


@router.post("/regime2/{ticker}")
async def trigger_regime2(ticker: str, background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")
    background_tasks.add_task(_run_regime2, dict(pos))
    return {"status": "queued", "ticker": ticker, "regime": 2}


@router.post("/regime3/{ticker}")
async def trigger_regime3(ticker: str, background_tasks: BackgroundTasks,
                          escalation_reason: str = "manual"):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")
    background_tasks.add_task(_run_regime3, dict(pos), escalation_reason)
    return {"status": "queued", "ticker": ticker, "regime": 3}


@router.post("/sector-pulse/{peer_ticker}")
async def trigger_sector_pulse(peer_ticker: str, main_ticker: str,
                                background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        main_pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", main_ticker
        )
        peer_row = await db.fetchrow(
            "SELECT * FROM peers WHERE peer_ticker = $1 AND position_id = $2",
            peer_ticker, str(main_pos["id"]) if main_pos else None
        )
    if not main_pos:
        raise HTTPException(404, f"Active position {main_ticker} not found")
    background_tasks.add_task(_run_sector_pulse, peer_ticker, dict(main_pos))
    return {"status": "queued", "peer_ticker": peer_ticker, "main_ticker": main_ticker}


# ── BACKGROUND TASKS ─────────────────────────────────────────────────────────

async def _run_regime1(pos: dict):
    ticker = pos["ticker"]
    notifier = SlackNotifier()
    try:
        import os
        schema_path = f"/app/sector_schemas/{pos['sector_schema']}.json"
        with open(schema_path) as f:
            sector_schema = json.load(f)

        m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
        m2 = collect_m2(ticker, pos["company_name"])
        m3 = await collect_m3(ticker, pos["company_name"], "post_earnings", {}, DustClient())
        data_brief = assemble_data_brief(ticker, m1, m2, m3, None, None, None)

        thesis = await run_regime_1(ticker, pos["company_name"], data_brief, sector_schema, DustClient())

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, data_brief_json, full_output_json)
                VALUES ($1, 1, 'manual', $2, $3)
            """, str(pos["id"]), data_brief, thesis)

        logger.info(f"Regime 1 completed for {ticker}")
    except DustBudgetExceededError as e:
        await notifier.send_error_alert(ticker, f"Budget dépassé : {e}")
    except Exception as e:
        logger.error(f"Regime 1 error for {ticker}: {e}")
        await notifier.send_error_alert(ticker, str(e))


async def _run_regime2(pos: dict):
    from app.calendar.event_router import EventRouter
    router_instance = EventRouter()
    ticker = pos["ticker"]
    try:
        async with get_db_session() as db:
            thesis = await db.fetchrow(
                "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", str(pos["id"])
            )
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1", str(pos["id"])
            )
            pulses = await db.fetch("""
                SELECT * FROM sector_pulses
                WHERE main_position_id = $1 AND accumulated = FALSE
                ORDER BY pulse_date DESC LIMIT 10
            """, str(pos["id"]))

        m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
        m2 = collect_m2(ticker, pos["company_name"])

        thesis_data = None
        if thesis:
            thesis_data = {
                "thesis_one_liner": thesis["thesis_one_liner"],
                "hypotheses": [dict(h) for h in hypotheses],
                "entry_price": float(pos["entry_price"]),
                "last_recommendation": None,
            }

        data_brief = assemble_data_brief(
            ticker=ticker, m1_data=m1, m2_data=m2, m3_data=None,
            thesis_data=thesis_data,
            sector_pulses_accumulated=[dict(p) for p in pulses],
            peers_m1_data=None,
        )

        dust = DustClient()
        review = await run_regime_2(ticker, pos["company_name"], data_brief, dust)

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, hypotheses_scores_json,
                     recommendation, data_brief_json, full_output_json, alert_level)
                VALUES ($1, 2, 'manual', $2, $3, $4, $5, $6)
            """,
                str(pos["id"]),
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
                    """, score.get("status", "neutral"), str(pos["id"]), score.get("code"))

        await SlackNotifier().send_regime2_report(ticker, review)
    except DustBudgetExceededError as e:
        await SlackNotifier().send_error_alert(ticker, f"Budget dépassé : {e}")
    except Exception as e:
        logger.error(f"Regime 2 manual error for {ticker}: {e}")
        await SlackNotifier().send_error_alert(ticker, str(e))


async def _run_regime3(pos: dict, escalation_reason: str):
    ticker = pos["ticker"]
    notifier = SlackNotifier()
    try:
        async with get_db_session() as db:
            thesis = await db.fetchrow(
                "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", str(pos["id"])
            )
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1", str(pos["id"])
            )

        m1 = collect_quantitative(ticker, settings.FMP_API_KEY)
        m2 = collect_m2(ticker, pos["company_name"])
        m3 = await collect_m3(ticker, pos["company_name"], "post_earnings", {}, DustClient())

        thesis_data = {
            "thesis_one_liner": thesis["thesis_one_liner"] if thesis else "",
            "hypotheses": [dict(h) for h in hypotheses],
            "entry_price": float(pos["entry_price"]),
        } if thesis else None

        data_brief = assemble_data_brief(
            ticker=ticker, m1_data=m1, m2_data=m2, m3_data=m3,
            thesis_data=thesis_data, sector_pulses_accumulated=None, peers_m1_data=None,
        )

        current_price = m1.get("price", {}).get("current_price")
        position_context = {
            "ticker": ticker,
            "entry_price": float(pos["entry_price"]),
            "current_price": current_price,
            "allocation_pct": float(pos["allocation_pct"]) if pos.get("allocation_pct") else None,
            "thesis_one_liner": thesis["thesis_one_liner"] if thesis else None,
        }
        deviation_trigger = {"source": escalation_reason, "triggered_at": "manual"}

        dust = DustClient()
        review = await run_regime_3(
            ticker, pos["company_name"], data_brief,
            position_context, deviation_trigger, dust
        )

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, hypotheses_scores_json,
                     recommendation, rationale, data_brief_json, full_output_json, alert_level)
                VALUES ($1, 3, $2, $3, $4, $5, $6, $7, $8)
            """,
                str(pos["id"]), escalation_reason,
                review.get("thesis_revision", {}).get("hypotheses_updated"),
                review.get("decision", {}).get("recommendation"),
                review.get("decision", {}).get("rationale"),
                data_brief, review,
                review.get("alert_level", "orange"),
            )

        await notifier.send_regime3_decision(ticker, review)
    except DustBudgetExceededError as e:
        await notifier.send_error_alert(ticker, f"Budget dépassé : {e}")
    except Exception as e:
        logger.error(f"Regime 3 error for {ticker}: {e}")
        await notifier.send_error_alert(ticker, str(e))


async def _run_sector_pulse(peer_ticker: str, main_pos: dict):
    ticker = main_pos["ticker"]
    notifier = SlackNotifier()
    try:
        async with get_db_session() as db:
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1", str(main_pos["id"])
            )
            peer_row = await db.fetchrow(
                "SELECT peer_company_name FROM peers WHERE peer_ticker = $1 AND position_id = $2",
                peer_ticker, str(main_pos["id"])
            )

        peer_company = peer_row["peer_company_name"] if peer_row else peer_ticker
        peer_m2 = collect_m2(peer_ticker, peer_company)

        pulse = await run_sector_pulse(
            peer_ticker=peer_ticker,
            peer_company=peer_company,
            main_position_ticker=ticker,
            peer_m2_data=peer_m2,
            main_hypotheses=[dict(h) for h in hypotheses],
            dust_client=DustClient(),
        )

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO sector_pulses
                    (peer_ticker, main_position_id, peer_result_summary,
                     hypothesis_impacts_json, pulse_score, action, dust_cost_usd)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
                peer_ticker, str(main_pos["id"]),
                pulse.get("peer_result_summary"),
                pulse.get("hypothesis_impacts"),
                pulse.get("pulse_score", 0),
                pulse.get("action", "store"),
                pulse.get("dust_cost_usd"),
            )

        if pulse.get("action") == "escalate_to_regime3":
            await notifier.send_sector_pulse_escalation(ticker, peer_ticker, pulse)
    except Exception as e:
        logger.error(f"Sector pulse error {peer_ticker}/{ticker}: {e}")
        await notifier.send_error_alert(ticker, str(e))
