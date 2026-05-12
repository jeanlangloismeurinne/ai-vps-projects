import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.db.database import get_db_session
from app.agents.dust_client import DustClient, DustBudgetExceededError
from app.agents.research_agent import run_regime_1
from app.agents.portfolio_agent import run_regime_2, run_regime_3
from app.agents.sector_pulse import run_sector_pulse
from app.data_collection.m1_quantitative import collect_peers_quantitative
from app.data_collection.m2_events import collect_m2
from app.data_collection.data_service import DataService
from app.data_collection.m3_qualitative import collect_m3
from app.data_collection.assembler import assemble_data_brief
from app.notifications.slack_notifier import SlackNotifier
from app.config import settings

router = APIRouter(prefix="/trigger", tags=["trigger"])
logger = logging.getLogger(__name__)


async def _get_redis():
    import redis.asyncio as aioredis
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _set_job(redis, job_id: str, data: dict):
    await redis.set(f"job:{job_id}", json.dumps(data), ex=86400)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    redis = await _get_redis()
    raw = await redis.get(f"job:{job_id}")
    await redis.aclose()
    if not raw:
        raise HTTPException(404, "job not found")
    return json.loads(raw)


@router.post("/regime0/{ticker}")
async def trigger_regime0(ticker: str, watchlist_id: str, background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", watchlist_id)
    if not item:
        raise HTTPException(404, f"Watchlist item {watchlist_id} not found")

    job_id = str(uuid.uuid4())
    redis = await _get_redis()
    await _set_job(redis, job_id, {"status": "pending", "ticker": ticker, "regime": 0})
    await redis.aclose()

    background_tasks.add_task(_run_regime0, job_id, watchlist_id, ticker)
    return {"job_id": job_id, "status": "pending", "ticker": ticker, "regime": 0}


@router.post("/regime1/{ticker}")
async def trigger_regime1(ticker: str, background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")

    job_id = str(uuid.uuid4())
    redis = await _get_redis()
    await _set_job(redis, job_id, {"status": "pending", "ticker": ticker, "regime": 1})
    await redis.aclose()

    background_tasks.add_task(_run_regime1, dict(pos), job_id)
    return {"job_id": job_id, "status": "pending", "ticker": ticker, "regime": 1}


@router.post("/regime2/{ticker}")
async def trigger_regime2(ticker: str, background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")

    job_id = str(uuid.uuid4())
    redis = await _get_redis()
    await _set_job(redis, job_id, {"status": "pending", "ticker": ticker, "regime": 2})
    await redis.aclose()

    background_tasks.add_task(_run_regime2, dict(pos), job_id)
    return {"job_id": job_id, "status": "pending", "ticker": ticker, "regime": 2}


@router.post("/regime3/{ticker}")
async def trigger_regime3(ticker: str, background_tasks: BackgroundTasks,
                          escalation_reason: str = "manual"):
    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", ticker
        )
    if not pos:
        raise HTTPException(404, f"Active position {ticker} not found")

    job_id = str(uuid.uuid4())
    redis = await _get_redis()
    await _set_job(redis, job_id, {"status": "pending", "ticker": ticker, "regime": 3})
    await redis.aclose()

    background_tasks.add_task(_run_regime3, dict(pos), escalation_reason, job_id)
    return {"job_id": job_id, "status": "pending", "ticker": ticker, "regime": 3}


@router.post("/sector-pulse/{peer_ticker}")
async def trigger_sector_pulse(peer_ticker: str, main_ticker: str,
                                background_tasks: BackgroundTasks):
    async with get_db_session() as db:
        main_pos = await db.fetchrow(
            "SELECT * FROM positions WHERE ticker = $1 AND status = 'active'", main_ticker
        )
    if not main_pos:
        raise HTTPException(404, f"Active position {main_ticker} not found")

    job_id = str(uuid.uuid4())
    redis = await _get_redis()
    await _set_job(redis, job_id, {"status": "pending", "ticker": main_ticker, "regime": "pulse"})
    await redis.aclose()

    background_tasks.add_task(_run_sector_pulse, peer_ticker, dict(main_pos), job_id)
    return {"job_id": job_id, "status": "queued", "peer_ticker": peer_ticker, "main_ticker": main_ticker}


# ── BACKGROUND TASKS ─────────────────────────────────────────────────────────

async def _update_job(job_id: str, data: dict):
    try:
        redis = await _get_redis()
        await _set_job(redis, job_id, data)
        await redis.aclose()
    except Exception as e:
        logger.warning(f"Redis update failed for job {job_id}: {e}")


async def _run_regime0(job_id: str, watchlist_id: str, ticker: str):
    from app.agents.scout_agent import _execute_scout
    try:
        redis = await _get_redis()
        await _execute_scout(job_id, watchlist_id, ticker, redis)
        await redis.aclose()
    except Exception as e:
        logger.error(f"Regime 0 error for {ticker}: {e}")
        await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 0, "detail": str(e)})


async def _get_agent_version(agent_id: str) -> int | None:
    import httpx
    DUST_API_BASE = "https://dust.tt/api/v1"
    headers = {"Authorization": f"Bearer {settings.DUST_API_KEY}"}
    url = f"{DUST_API_BASE}/w/{settings.DUST_WORKSPACE_ID}/assistant/agent_configurations/{agent_id}?variant=light"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json().get("agentConfiguration", {}).get("version")
    except Exception:
        pass
    return None


async def _run_regime1(pos: dict, job_id: str = None):
    ticker = pos["ticker"]
    notifier = SlackNotifier()
    try:
        if job_id:
            await _update_job(job_id, {"status": "running", "ticker": ticker, "regime": 1})

        # Versionning agents
        v_research = await _get_agent_version(settings.DUST_RESEARCH_AGENT_ID)
        v_portfolio = await _get_agent_version(settings.DUST_PORTFOLIO_AGENT_ID)

        schema_path = f"/app/sector_schemas/{pos['sector_schema']}.json"
        with open(schema_path) as f:
            sector_schema = json.load(f)

        try:
            m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime1")
        except Exception as e:
            logger.warning(f"M1 error for {ticker}: {e}")
            m1 = {"ticker": ticker, "error": str(e)}

        try:
            m2 = collect_m2(ticker, pos["company_name"])
        except Exception as e:
            logger.warning(f"M2 error for {ticker}: {e}")
            m2 = {}

        try:
            m3 = await collect_m3(ticker, pos["company_name"], "post_earnings", {}, DustClient())
        except Exception as e:
            logger.warning(f"M3 error for {ticker}: {e}")
            m3 = {}

        data_brief = assemble_data_brief(ticker, m1, m2, m3, None, None, None)

        thesis = await run_regime_1(ticker, pos["company_name"], data_brief, sector_schema, DustClient())

        async with get_db_session() as db:
            # Vérifier version précédente pour alerte
            prev = await db.fetchrow(
                "SELECT agent_version_research FROM theses WHERE position_id=$1 AND is_current=TRUE",
                str(pos["id"])
            )
            if prev and prev["agent_version_research"] and v_research and prev["agent_version_research"] != v_research:
                await notifier.send_error_alert(ticker,
                    f"⚠ Prompt research-agent mis à jour (v{prev['agent_version_research']}→v{v_research}) depuis le dernier run {ticker}")

            # Mettre à jour thèse avec conversation_id et versions
            conv_id = thesis.get("dust_conversation_id")
            await db.execute("""
                UPDATE theses SET
                    dust_conversation_id = COALESCE($1, dust_conversation_id),
                    agent_version_research = $2,
                    agent_version_portfolio = $3
                WHERE position_id = $4 AND is_current = TRUE
            """, conv_id, v_research, v_portfolio, str(pos["id"]))

            # Extraire et stocker schema_json dans positions si disponible
            schema_json = thesis.get("schema_json") or thesis.get("fundamental_analysis")
            if schema_json:
                await db.execute(
                    "UPDATE positions SET schema_json=$1 WHERE id=$2",
                    schema_json, str(pos["id"])
                )

            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, data_brief_json, full_output_json,
                     dust_conversation_id, agent_version_research, agent_version_portfolio)
                VALUES ($1, 1, 'manual', $2, $3, $4, $5, $6)
            """, str(pos["id"]), data_brief, thesis, conv_id, v_research, v_portfolio)

        if job_id:
            await _update_job(job_id, {"status": "done", "ticker": ticker, "regime": 1})
        logger.info(f"Regime 1 completed for {ticker}")
    except DustBudgetExceededError as e:
        await notifier.send_error_alert(ticker, f"Budget dépassé : {e}")
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 1, "detail": "budget_exceeded"})
    except Exception as e:
        import traceback
        logger.error(f"Regime 1 error for {ticker}: {e}\n{traceback.format_exc()}")
        await notifier.send_error_alert(ticker, str(e))
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 1, "detail": str(e)})


async def _run_regime2(pos: dict, job_id: str = None):
    from app.calendar.event_router import EventRouter
    ticker = pos["ticker"]
    try:
        if job_id:
            await _update_job(job_id, {"status": "running", "ticker": ticker, "regime": 2})

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

        m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime2")
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

        v_research = await _get_agent_version(settings.DUST_RESEARCH_AGENT_ID)
        v_portfolio = await _get_agent_version(settings.DUST_PORTFOLIO_AGENT_ID)

        dust = DustClient()
        review = await run_regime_2(ticker, pos["company_name"], data_brief, dust)
        conv_id = review.get("dust_conversation_id")

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, hypotheses_scores_json,
                     recommendation, data_brief_json, full_output_json, alert_level,
                     dust_conversation_id, agent_version_research, agent_version_portfolio)
                VALUES ($1, 2, 'manual', $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                str(pos["id"]),
                review.get("hypotheses_scores"),
                review.get("recommendation"),
                data_brief, review,
                review.get("alert_level", "green"),
                conv_id, v_research, v_portfolio,
            )

            if review.get("hypotheses_scores"):
                for score in review["hypotheses_scores"]:
                    await db.execute("""
                        UPDATE hypotheses SET current_status = $1, last_updated = NOW()
                        WHERE position_id = $2 AND code = $3
                    """, score.get("status", "neutral"), str(pos["id"]), score.get("code"))

        await SlackNotifier().send_regime2_report(ticker, review)
        if job_id:
            await _update_job(job_id, {"status": "done", "ticker": ticker, "regime": 2})
    except DustBudgetExceededError as e:
        await SlackNotifier().send_error_alert(ticker, f"Budget dépassé : {e}")
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 2, "detail": "budget_exceeded"})
    except Exception as e:
        logger.error(f"Regime 2 manual error for {ticker}: {e}")
        await SlackNotifier().send_error_alert(ticker, str(e))
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 2, "detail": str(e)})


async def _run_regime3(pos: dict, escalation_reason: str, job_id: str = None):
    ticker = pos["ticker"]
    notifier = SlackNotifier()
    try:
        if job_id:
            await _update_job(job_id, {"status": "running", "ticker": ticker, "regime": 3})

        async with get_db_session() as db:
            thesis = await db.fetchrow(
                "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", str(pos["id"])
            )
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1", str(pos["id"])
            )

        m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime3")
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

        v_research = await _get_agent_version(settings.DUST_RESEARCH_AGENT_ID)
        v_portfolio = await _get_agent_version(settings.DUST_PORTFOLIO_AGENT_ID)

        dust = DustClient()
        review = await run_regime_3(
            ticker, pos["company_name"], data_brief,
            position_context, deviation_trigger, dust
        )
        conv_id = review.get("dust_conversation_id")

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO reviews
                    (position_id, regime, triggered_by, hypotheses_scores_json,
                     recommendation, rationale, data_brief_json, full_output_json, alert_level,
                     dust_conversation_id, agent_version_research, agent_version_portfolio)
                VALUES ($1, 3, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                str(pos["id"]), escalation_reason,
                review.get("thesis_revision", {}).get("hypotheses_updated"),
                review.get("decision", {}).get("recommendation"),
                review.get("decision", {}).get("rationale"),
                data_brief, review,
                review.get("alert_level", "orange"),
                conv_id, v_research, v_portfolio,
            )

        await notifier.send_regime3_decision(ticker, review)
        if job_id:
            await _update_job(job_id, {"status": "done", "ticker": ticker, "regime": 3})
    except DustBudgetExceededError as e:
        await notifier.send_error_alert(ticker, f"Budget dépassé : {e}")
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 3, "detail": "budget_exceeded"})
    except Exception as e:
        logger.error(f"Regime 3 error for {ticker}: {e}")
        await notifier.send_error_alert(ticker, str(e))
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "regime": 3, "detail": str(e)})


async def _run_sector_pulse(peer_ticker: str, main_pos: dict, job_id: str = None):
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
        if job_id:
            await _update_job(job_id, {"status": "done", "ticker": ticker, "regime": "pulse"})
    except Exception as e:
        logger.error(f"Sector pulse error {peer_ticker}/{ticker}: {e}")
        await notifier.send_error_alert(ticker, str(e))
        if job_id:
            await _update_job(job_id, {"status": "error", "ticker": ticker, "detail": str(e)})
