"""
Theses V1 — construction et validation de thèses d'investissement.
"""
import json as _json
import logging
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db.database import get_db_session
from app.config import settings

router = APIRouter(tags=["thesis-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class ThesisCreate(BaseModel):
    opportunity_id: Optional[int] = None


class ThesisUpdate(BaseModel):
    thesis_json: Optional[dict] = None
    one_liner: Optional[str] = None
    needs_revision: Optional[bool] = None
    conviction_override_note: Optional[str] = None
    conviction_review_date: Optional[str] = None
    decision_delay_used: Optional[bool] = None
    reevaluation_date: Optional[str] = None


class ChatMessage(BaseModel):
    role: str = "user"
    content: str
    mode: str = "freeform"  # 'freeform' | 'json_generation'


class CalendarEventInput(BaseModel):
    event_type: str
    label: str
    scheduled_date: str  # ISO date
    peer_ticker: Optional[str] = None
    monitoring_mode: int = 2
    source: str = "thesis_agent"
    pending_validation: bool = False


class ValidateThesisBody(BaseModel):
    shares: float
    purchase_price: float
    purchase_date: str  # ISO date
    calendar_events: Optional[List[CalendarEventInput]] = None


class ImportLegacyBody(BaseModel):
    brief_json: dict
    conviction_score: int
    recommendation: str  # PROCEED | MONITOR | PASS
    thesis_json: dict
    one_liner: Optional[str] = None
    shares: float
    purchase_price: float
    purchase_date: str  # ISO date
    calendar_events: Optional[List[CalendarEventInput]] = None


# ─────────────────────────── Helpers ─────────────────────────────────────────

import math as _math

_TICKER_MAP = {
    "amazon": "AMZN", "aws": "AMZN",
    "google": "GOOGL", "alphabet": "GOOGL", "gcp": "GOOGL",
    "apple": "AAPL",
    "meta": "META", "facebook": "META",
    "nvidia": "NVDA",
    "salesforce": "CRM",
    "oracle": "ORCL",
    "ibm": "IBM",
    "servicenow": "NOW",
    "sap": "SAP",
    "workday": "WDAY",
}

def _guess_ticker(name: str) -> str:
    first = name.split()[0].lower().rstrip(",()")
    return _TICKER_MAP.get(first, name.split()[0][:8].upper())


def _normalize_thesis_json(parsed: dict) -> dict:
    """
    Fusionne les clés plates attendues par ThesisEditorV2 dans le JSON agent (step_1..step_7).
    Préserve tout l'output original de l'agent.
    """
    out = dict(parsed)

    # ── Metadata (conviction, recommandation, résumé) ──────────────────────────
    meta = parsed.get("thesis_metadata", {})
    if isinstance(meta, dict):
        if meta.get("investment_thesis_summary"):
            out["one_liner"] = meta["investment_thesis_summary"]
        if meta.get("analyst_conviction_score") is not None:
            out["conviction_score"] = meta["analyst_conviction_score"]
        if meta.get("analyst_conviction_rationale"):
            out["conviction_rationale"] = meta["analyst_conviction_rationale"]
        if meta.get("investment_recommendation"):
            out["recommendation"] = meta["investment_recommendation"]
        if meta.get("thesis_horizon_years"):
            out["thesis_horizon_years"] = meta["thesis_horizon_years"]
        if meta.get("ideal_investor_profile"):
            out["ideal_investor_profile"] = meta["ideal_investor_profile"]

    # ── Scénarios ──────────────────────────────────────────────────────────────
    raw_step4 = parsed.get("step_4_scenarios_5yr", {})
    scenarios_list = (
        raw_step4.get("scenarios", []) if isinstance(raw_step4, dict)
        else (raw_step4 if isinstance(raw_step4, list) else [])
    )
    base_price = raw_step4.get("base_price", 0) if isinstance(raw_step4, dict) else 0

    if isinstance(raw_step4, dict) and raw_step4.get("probability_weighted_target"):
        out["probability_weighted_target"] = raw_step4["probability_weighted_target"]

    scenarios = {}
    for s in scenarios_list:
        name = (s.get("scenario_name") or "").lower()
        if not name:
            continue
        midpoint = (s.get("price_target_5yr") or {}).get("midpoint", 0)
        prob = s.get("probability_pct", 0)
        desc = s.get("hypothesis_directrice") or s.get("description", "")
        cagr = ""
        if base_price and midpoint:
            try:
                cagr = round((_math.pow(midpoint / base_price, 0.2) - 1) * 100, 1)
            except Exception:
                pass
        scenarios[name] = {"probability": prob, "cagr": cagr, "description": desc}
    if scenarios:
        out["scenarios"] = scenarios

    # ── Hypothèses (avec KPI + seuils d'alerte) ────────────────────────────────
    raw_step5 = parsed.get("step_5_falsifiable_hypotheses", [])
    hyps_list = raw_step5 if isinstance(raw_step5, list) else []
    if hyps_list:
        out["hypotheses"] = [
            {
                "id": f"H{h.get('hypothesis_id', i + 1)}",
                "text": h.get("statement", ""),
                "status": "unverified",
                "weight": h.get("criticality_level", ""),
                "kpi_metric": (h.get("kpi_tracking") or {}).get("metric_name", ""),
                "kpi_target": (h.get("kpi_tracking") or {}).get("baseline_target", ""),
                "kpi_unit": (h.get("kpi_tracking") or {}).get("unit", ""),
                "alert_threshold": h.get("alert_threshold", {}),
                "invalidation_threshold": h.get("invalidation_threshold", {}),
            }
            for i, h in enumerate(hyps_list)
        ]

    # ── Seuils de cours ────────────────────────────────────────────────────────
    def _get_scenario(name_upper):
        return next((s for s in scenarios_list if (s.get("scenario_name") or "").upper() == name_upper), {})

    price_thresholds = {}
    bear_pt = (_get_scenario("BEAR").get("price_target_5yr") or {})
    central_pt = (_get_scenario("CENTRAL").get("price_target_5yr") or {})
    bull_pt = (_get_scenario("BULL").get("price_target_5yr") or {})
    if bear_pt:
        price_thresholds["stop_loss"] = bear_pt.get("low") or bear_pt.get("midpoint")
    if central_pt:
        price_thresholds["fair_value"] = central_pt.get("midpoint")
    if bull_pt:
        price_thresholds["target_price"] = bull_pt.get("midpoint")
    if price_thresholds:
        out["price_thresholds"] = price_thresholds

    # ── Analyse fondamentale résumée ───────────────────────────────────────────
    raw_step1 = parsed.get("step_1_fundamental_analysis", {})
    if isinstance(raw_step1, dict):
        fa = {}
        if raw_step1.get("verdict"):
            fa["verdict"] = raw_step1["verdict"]
        moat = raw_step1.get("moat_assessment", {})
        if isinstance(moat, dict):
            if moat.get("status"):
                fa["moat_status"] = moat["status"]
            if moat.get("components"):
                fa["moat_components"] = [
                    {
                        "type": c.get("moat_type", ""),
                        "strength": c.get("strength", ""),
                        "durability": c.get("durability", ""),
                    }
                    for c in moat["components"] if isinstance(c, dict)
                ]
        pricing = raw_step1.get("pricing_power", {})
        if isinstance(pricing, dict):
            if pricing.get("status"):
                fa["pricing_power_status"] = pricing["status"]
            if pricing.get("sustainability"):
                fa["pricing_power_sustainability"] = pricing["sustainability"]
        capalloc = raw_step1.get("capital_allocation", {})
        if isinstance(capalloc, dict) and capalloc:
            fa["capital_allocation"] = capalloc
        if fa:
            out["fundamental_analysis"] = fa

    # ── Pairs comparables ──────────────────────────────────────────────────────
    raw_step2 = parsed.get("step_2_competitive_analysis", {})
    competitors = raw_step2.get("key_competitors_analysis", []) if isinstance(raw_step2, dict) else []
    tiers = ["T1", "T2", "T3"]
    if competitors:
        out["pairs"] = [
            {
                "ticker": _guess_ticker(c.get("competitor", "")),
                "tier": tiers[min(i, 2)],
                "note": c.get("competitive_position") or c.get("competitor", ""),
            }
            for i, c in enumerate(competitors)
        ]

    # ── Bear Steel Man ─────────────────────────────────────────────────────────
    raw_step7 = parsed.get("step_7_devil_advocate_risks", [])
    risks = raw_step7 if isinstance(raw_step7, list) else raw_step7.get("bear_steel_man", []) if isinstance(raw_step7, dict) else []
    if risks:
        parts = []
        for r in risks[:4]:
            if isinstance(r, dict):
                cat = r.get("risk_category", "")
                desc = r.get("description", "")
                parts.append(f"{cat} : {desc}" if cat else desc)
            elif isinstance(r, str):
                parts.append(r)
        out["bear_steel_man"] = "\n\n".join(parts)

    # ── Track Record Analystes ─────────────────────────────────────────────────
    raw_step6 = parsed.get("step_6_analyst_track_record", {})
    if isinstance(raw_step6, dict):
        consensus = raw_step6.get("consensus_current", {})
        hist = raw_step6.get("historical_reliability", {})
        count = consensus.get("analyst_count", "")
        target_med = consensus.get("price_target_median", "")
        target_low = consensus.get("price_target_low", "")
        target_high = consensus.get("price_target_high", "")
        eps_beat = hist.get("eps_beat_ratio_pct", "")
        rev_beat = hist.get("revenue_beat_ratio_pct", "")
        buy_pct = consensus.get("recommendation_buy_pct", "")
        label = f"Consensus ({count} analystes)" if count else "Consensus Wall Street"
        accuracy_parts = [p for p in [
            f"EPS beat {eps_beat}%" if eps_beat else "",
            f"Rev beat {rev_beat}%" if rev_beat else "",
            f"PT ${target_low}-${target_high} (médian ${target_med})" if target_med else "",
            f"Buy {buy_pct}%" if buy_pct else "",
        ] if p]
        out["track_record_analysts"] = [{"analyst": label, "accuracy": " | ".join(accuracy_parts)}]

    return out


def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_thesis_or_404(db, thesis_id: int):
    row = await db.fetchrow("SELECT * FROM theses WHERE id=$1", thesis_id)
    if not row:
        raise HTTPException(404, f"Thèse #{thesis_id} introuvable")
    return row


# ─────────────────────────── Theses sous /tickers/{ticker_id} ────────────────

@router.get("/tickers/{ticker_id}/theses")
async def list_theses(ticker_id: str):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM theses WHERE ticker_id=$1 ORDER BY created_at DESC",
            ticker_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/tickers/{ticker_id}/theses", status_code=201)
async def create_thesis(ticker_id: str, data: ThesisCreate):
    """
    Crée une thèse en draft.
    Si opportunity_id fourni, charge le brief et construit le handoff JSON.
    """
    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")

        handoff_json = None
        if data.opportunity_id:
            brief_row = await db.fetchrow(
                "SELECT * FROM opportunity_briefs WHERE id=$1 AND ticker_id=$2",
                data.opportunity_id, ticker_id,
            )
            if not brief_row:
                raise HTTPException(404, f"Brief #{data.opportunity_id} introuvable pour ticker '{ticker_id}'")
            brief_dict = _serialize(brief_row)
            ticker_row = await db.fetchrow(
                "SELECT name, reporting_currency FROM tickers WHERE id=$1", ticker_id
            )
            handoff_json = {
                "opportunity_brief": brief_dict.get("brief_json") or {},
                "conviction_score": brief_dict.get("conviction_score"),
                "recommendation": brief_dict.get("recommendation"),
                "ticker_id": ticker_id,
                "ticker_name": ticker_row["name"] if ticker_row else ticker_id,
                "reporting_currency": ticker_row["reporting_currency"] if ticker_row else "USD",
                "source": brief_dict.get("source"),
            }

        row = await db.fetchrow(
            """
            INSERT INTO theses (ticker_id, opportunity_id, status, thesis_json)
            VALUES ($1, $2, 'draft', $3)
            RETURNING *
            """,
            ticker_id, data.opportunity_id, handoff_json,
        )
    return _serialize(row)


@router.get("/tickers/{ticker_id}/theses/{thesis_id}")
async def get_thesis(ticker_id: str, thesis_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM theses WHERE id=$1 AND ticker_id=$2",
            thesis_id, ticker_id,
        )
        if not row:
            raise HTTPException(404, f"Thèse #{thesis_id} introuvable pour ticker '{ticker_id}'")
        messages = await db.fetch(
            "SELECT * FROM thesis_messages WHERE thesis_id=$1 ORDER BY created_at",
            thesis_id,
        )
    thesis_dict = _serialize(row)
    thesis_dict["messages"] = [_serialize(m) for m in messages]
    # Expose calendar_events_suggested at top level (stored inside thesis_json by the agent)
    if isinstance(thesis_dict.get("thesis_json"), dict):
        cal = thesis_dict["thesis_json"].get("calendar_events_suggested", [])
        if cal:
            thesis_dict["calendar_events_suggested"] = cal
    return thesis_dict


@router.patch("/tickers/{ticker_id}/theses/{thesis_id}")
async def update_thesis(ticker_id: str, thesis_id: int, data: ThesisUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    set_parts = ["updated_at=NOW()"]
    values = []
    idx = 3
    for k, v in updates.items():
        set_parts.append(f"{k}=${idx}")
        values.append(v)
        idx += 1
    set_clause = ", ".join(set_parts)
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE theses SET {set_clause} WHERE id=$1 AND ticker_id=$2 RETURNING *",
            thesis_id, ticker_id, *values,
        )
    if not row:
        raise HTTPException(404, f"Thèse #{thesis_id} introuvable pour ticker '{ticker_id}'")
    return _serialize(row)


# ─────────────────────────── Chat / Refresh / Validate sous /theses/{id} ─────

def _format_handoff(handoff: dict) -> str:
    import json
    brief = handoff.get("opportunity_brief") or {}
    lines = [
        "=== HANDOFF OPPORTUNITY → THESIS ===",
        f"Ticker        : {handoff.get('ticker_id')} — {handoff.get('ticker_name', '')}",
        f"Devise rapport: {handoff.get('reporting_currency', 'USD')}",
        f"Conviction    : {handoff.get('conviction_score', 'n/a')}/10",
        f"Recommandation: {handoff.get('recommendation', 'n/a')}",
        "",
        "=== BRIEF D'OPPORTUNITÉ VALIDÉ ===",
        json.dumps(brief, ensure_ascii=False, indent=2),
        "=====================================",
    ]
    return "\n".join(lines)


@router.post("/theses/{thesis_id}/chat", status_code=201)
async def chat_with_thesis(thesis_id: int, data: ChatMessage):
    from app.agents.thesis_agent import ThesisAgent, AgentNotSyncedError

    async with get_db_session() as db:
        thesis = await _get_thesis_or_404(db, thesis_id)
        prior_count = await db.fetchval(
            "SELECT COUNT(*) FROM thesis_messages WHERE thesis_id=$1", thesis_id
        )
        await db.execute(
            """
            INSERT INTO thesis_messages (thesis_id, role, content, mode)
            VALUES ($1, $2, $3, $4)
            """,
            thesis_id, "user", data.content, data.mode,
        )

    if data.mode not in ("freeform", "json_generation"):
        raise HTTPException(400, "mode doit être 'freeform' ou 'json_generation'")

    # Premier message freeform : préfixer avec le handoff pour que l'agent ait tout le contexte
    agent_message = data.content
    if data.mode == "freeform" and prior_count == 0 and thesis["thesis_json"]:
        handoff_block = _format_handoff(thesis["thesis_json"])
        agent_message = f"{handoff_block}\n\n{data.content}"

    try:
        agent = ThesisAgent()
        result = await agent.run(mode=data.mode, message=agent_message)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ThesisAgent error (thesis #{thesis_id}): {error_msg}")
        async with get_db_session() as db:
            await db.execute(
                """INSERT INTO thesis_messages (thesis_id, role, content, mode)
                   VALUES ($1, 'error', $2, $3)""",
                thesis_id, error_msg, data.mode,
            )
        raise HTTPException(502, f"Erreur agent: {error_msg}")

    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO thesis_messages (thesis_id, role, content, mode, raw_payload)
            VALUES ($1, 'agent', $2, $3, $4)
            RETURNING *
            """,
            thesis_id, result["content"], data.mode,
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd"), "conversation_id": result.get("conversation_id")},
        )

    return {
        "message": _serialize(msg_row),
        "content": result["content"],
        "tokens_input": result.get("tokens_input"),
        "tokens_output": result.get("tokens_output"),
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/theses/{thesis_id}/chat/stream")
async def chat_with_thesis_stream(thesis_id: int, data: ChatMessage):
    """
    Variante streaming de /chat — renvoie les tokens Dust en SSE au fur et à mesure.
    Rollback : basculer NEXT_PUBLIC_DUST_STREAMING=false dans Coolify → frontend repasse sur /chat.
    """
    from app.agents.thesis_agent import ThesisAgent, AgentNotSyncedError

    async with get_db_session() as db:
        thesis = await _get_thesis_or_404(db, thesis_id)
        prior_count = await db.fetchval(
            "SELECT COUNT(*) FROM thesis_messages WHERE thesis_id=$1", thesis_id
        )
        await db.execute(
            "INSERT INTO thesis_messages (thesis_id, role, content, mode) VALUES ($1, $2, $3, $4)",
            thesis_id, "user", data.content, data.mode,
        )

    agent_message = data.content
    if data.mode == "freeform" and prior_count == 0 and thesis["thesis_json"]:
        handoff_block = _format_handoff(thesis["thesis_json"])
        agent_message = f"{handoff_block}\n\n{data.content}"

    async def event_stream():
        try:
            agent = ThesisAgent()
            async for event in agent.run_streaming(mode=data.mode, message=agent_message):
                yield f"data: {_json.dumps(event)}\n\n"
                if event["type"] == "done":
                    async with get_db_session() as db:
                        await db.execute(
                            """INSERT INTO thesis_messages (thesis_id, role, content, mode, raw_payload)
                               VALUES ($1, 'agent', $2, $3, $4)""",
                            thesis_id, event["content"], data.mode,
                            {"tokens_input": event.get("tokens_input"),
                             "tokens_output": event.get("tokens_output"),
                             "cost_usd": event.get("cost_usd"),
                             "conversation_id": event.get("conversation_id")},
                        )
        except AgentNotSyncedError as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"ThesisAgent streaming error (thesis #{thesis_id}): {error_msg}")
            yield f"data: {_json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            try:
                async with get_db_session() as db:
                    await db.execute(
                        "INSERT INTO thesis_messages (thesis_id, role, content, mode) VALUES ($1, 'error', $2, $3)",
                        thesis_id, error_msg, data.mode,
                    )
            except Exception:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/theses/{thesis_id}/refresh-json")
async def refresh_thesis_json(thesis_id: int):
    """
    Récupère l'historique complet, appelle l'agent en mode json_generation,
    met à jour thesis_json et extrait calendar_events_suggested.
    """
    from app.agents.thesis_agent import ThesisAgent, AgentNotSyncedError

    async with get_db_session() as db:
        thesis = await _get_thesis_or_404(db, thesis_id)
        messages = await db.fetch(
            "SELECT role, content FROM thesis_messages WHERE thesis_id=$1 ORDER BY created_at",
            thesis_id,
        )

    history_parts = []
    for msg in messages:
        history_parts.append(f"[{msg['role'].upper()}]\n{msg['content']}")
    history_text = "\n\n---\n\n".join(history_parts) if history_parts else "(aucun échange précédent)"
    full_message = (
        f"Ticker : {thesis['ticker_id']}\n\n"
        f"Historique de la conversation :\n\n{history_text}"
    )

    try:
        agent = ThesisAgent()
        result = await agent.run(mode="json_generation", message=full_message)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"ThesisAgent json_generation error (thesis #{thesis_id}): {e}")
        raise HTTPException(502, f"Erreur agent: {e}")

    parsed = agent.extract_json(result["content"])
    if not parsed:
        raise HTTPException(422, "L'agent n'a pas retourné un JSON valide")
    parsed = _normalize_thesis_json(parsed)

    calendar_events_suggested = parsed.get("calendar_events_suggested", [])
    one_liner = parsed.get("one_liner") or parsed.get("thesis_one_liner")

    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            UPDATE theses
            SET thesis_json=$1, one_liner=COALESCE($2, one_liner), updated_at=NOW()
            WHERE id=$3
            RETURNING *
            """,
            parsed, one_liner, thesis_id,
        )
        await db.execute(
            """
            INSERT INTO thesis_messages (thesis_id, role, content, mode, raw_payload)
            VALUES ($1, 'agent', $2, 'json_generation', $3)
            """,
            thesis_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "thesis": _serialize(row),
        "parsed_json": parsed,
        "calendar_events_suggested": calendar_events_suggested,
        "tokens_input": result.get("tokens_input"),
        "tokens_output": result.get("tokens_output"),
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/theses/{thesis_id}/refresh-json/stream")
async def refresh_thesis_json_stream(thesis_id: int):
    """
    Variante streaming de /refresh-json — yielde les tokens Dust en SSE.
    Event final : type='done_refresh' avec parsed_json + calendar_events_suggested.
    Rollback : basculer NEXT_PUBLIC_DUST_STREAMING=false → frontend repasse sur /refresh-json.
    """
    from app.agents.thesis_agent import ThesisAgent, AgentNotSyncedError

    async with get_db_session() as db:
        thesis = await _get_thesis_or_404(db, thesis_id)
        messages = await db.fetch(
            "SELECT role, content FROM thesis_messages WHERE thesis_id=$1 ORDER BY created_at",
            thesis_id,
        )

    history_parts = []
    for msg in messages:
        history_parts.append(f"[{msg['role'].upper()}]\n{msg['content']}")
    history_text = "\n\n---\n\n".join(history_parts) if history_parts else "(aucun échange précédent)"
    full_message = (
        f"Ticker : {thesis['ticker_id']}\n\n"
        f"Historique de la conversation :\n\n{history_text}"
    )

    async def event_stream():
        try:
            agent = ThesisAgent()
            async for event in agent.run_streaming(mode="json_generation", message=full_message):
                if event["type"] == "done":
                    content = event.get("content", "")
                    parsed = agent.extract_json(content)
                    if not parsed:
                        yield f"data: {_json.dumps({'type': 'error', 'message': 'L\'agent n\'a pas retourné un JSON valide'})}\n\n"
                        return
                    parsed = _normalize_thesis_json(parsed)
                    calendar_events_suggested = parsed.get("calendar_events_suggested", [])
                    one_liner = parsed.get("one_liner") or parsed.get("thesis_one_liner")
                    async with get_db_session() as db:
                        row = await db.fetchrow(
                            """UPDATE theses SET thesis_json=$1, one_liner=COALESCE($2, one_liner), updated_at=NOW()
                               WHERE id=$3 RETURNING *""",
                            parsed, one_liner, thesis_id,
                        )
                        await db.execute(
                            """INSERT INTO thesis_messages (thesis_id, role, content, mode, raw_payload)
                               VALUES ($1, 'agent', $2, 'json_generation', $3)""",
                            thesis_id, content,
                            {"tokens_input": event.get("tokens_input"),
                             "tokens_output": event.get("tokens_output"),
                             "cost_usd": event.get("cost_usd")},
                        )
                    yield f"data: {_json.dumps({'type': 'done_refresh', 'parsed_json': parsed, 'calendar_events_suggested': calendar_events_suggested, 'thesis': _serialize(row)})}\n\n"
                else:
                    yield f"data: {_json.dumps(event)}\n\n"
        except AgentNotSyncedError as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"ThesisAgent refresh streaming error (thesis #{thesis_id}): {error_msg}")
            yield f"data: {_json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/theses/{thesis_id}/validate")
async def validate_thesis(thesis_id: int, data: ValidateThesisBody):
    """
    Valide la thèse :
    - thesis.status = 'active'
    - tickers.status = 'portfolio'
    - Crée portfolio_positions
    - Crée cash_movements (buy)
    - Persiste les calendar_events
    - Notification Slack
    """
    from datetime import date as _date

    async with get_db_session() as db:
        thesis = await _get_thesis_or_404(db, thesis_id)
        ticker_id = thesis["ticker_id"]

        # Active la thèse
        await db.execute(
            "UPDATE theses SET status='active', validated_at=NOW(), updated_at=NOW() WHERE id=$1",
            thesis_id,
        )

        # Met le ticker en portfolio
        await db.execute(
            "UPDATE tickers SET status='portfolio', updated_at=NOW() WHERE id=$1",
            ticker_id,
        )

        # Crée la position
        purchase_date_obj = _date.fromisoformat(data.purchase_date)
        position_row = await db.fetchrow(
            """
            INSERT INTO portfolio_positions
                (ticker_id, shares, purchase_price, purchase_date, thesis_id, status)
            VALUES ($1, $2, $3, $4, $5, 'open')
            RETURNING *
            """,
            ticker_id, data.shares, data.purchase_price, purchase_date_obj, thesis_id,
        )

        # Mouvement de trésorerie (buy)
        total_amount = data.shares * data.purchase_price
        await db.execute(
            """
            INSERT INTO cash_movements (type, amount, label, ticker_id)
            VALUES ('buy', $1, $2, $3)
            """,
            total_amount,
            f"Achat {ticker_id} — {data.shares} titres @ {data.purchase_price}",
            ticker_id,
        )

        # Persiste les calendar_events suggérés
        events_created = []
        if data.calendar_events:
            for ev in data.calendar_events:
                ev_date = _date.fromisoformat(ev.scheduled_date)
                ev_row = await db.fetchrow(
                    """
                    INSERT INTO calendar_events
                        (thesis_id, ticker_id, event_type, label, scheduled_date,
                         peer_ticker, monitoring_mode, source, pending_validation)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    RETURNING *
                    """,
                    thesis_id, ticker_id, ev.event_type, ev.label, ev_date,
                    ev.peer_ticker, ev.monitoring_mode, ev.source, ev.pending_validation,
                )
                events_created.append(_serialize(ev_row))

    # Notification Slack
    try:
        from app.notifications.slack_webhook import SlackWebhook
        await SlackWebhook().send_thesis_validated(
            ticker=ticker_id,
            one_liner=thesis["one_liner"] or "",
            shares=data.shares,
            price=data.purchase_price,
        )
    except Exception as e:
        logger.warning(f"Slack notification failed: {e}")

    return {
        "thesis_id": thesis_id,
        "status": "active",
        "position": _serialize(position_row),
        "calendar_events_created": events_created,
    }


@router.post("/tickers/{ticker_id}/import-legacy", status_code=201)
async def import_legacy_position(ticker_id: str, data: ImportLegacyBody):
    """
    Onboarding d'une position legacy (achetée avant le process V1).
    Crée brief + thèse + position + calendrier en une seule opération atomique.
    """
    from datetime import date as _date

    thesis_json = _normalize_thesis_json(data.thesis_json)
    one_liner = data.one_liner or thesis_json.get("one_liner") or thesis_json.get("thesis_one_liner")

    # Calendar : données explicites ou extraites du thesis_json
    calendar_events_input = data.calendar_events or []
    if not calendar_events_input:
        for ev in thesis_json.get("calendar_events_suggested", []):
            if not ev.get("scheduled_date"):
                continue
            calendar_events_input.append(CalendarEventInput(
                event_type=ev.get("event_type", "conviction_review"),
                label=ev.get("label", ""),
                scheduled_date=ev["scheduled_date"],
                peer_ticker=ev.get("peer_ticker"),
                monitoring_mode=ev.get("monitoring_mode", 2),
                source="manual",
                pending_validation=False,
            ))

    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable — crée-le d'abord via POST /tickers")

        brief_row = await db.fetchrow(
            """
            INSERT INTO opportunity_briefs
                (ticker_id, source, brief_json, conviction_score, recommendation, status)
            VALUES ($1, 'legacy_import', $2, $3, $4, 'validated')
            RETURNING *
            """,
            ticker_id, data.brief_json, data.conviction_score, data.recommendation,
        )
        brief_id = brief_row["id"]

        thesis_row = await db.fetchrow(
            """
            INSERT INTO theses
                (ticker_id, opportunity_id, status, thesis_json, one_liner, validated_at)
            VALUES ($1, $2, 'active', $3, $4, NOW())
            RETURNING *
            """,
            ticker_id, brief_id, thesis_json, one_liner,
        )
        thesis_id = thesis_row["id"]

        await db.execute(
            "UPDATE tickers SET status='portfolio', updated_at=NOW() WHERE id=$1",
            ticker_id,
        )

        purchase_date_obj = _date.fromisoformat(data.purchase_date)
        position_row = await db.fetchrow(
            """
            INSERT INTO portfolio_positions
                (ticker_id, shares, purchase_price, purchase_date, thesis_id, status)
            VALUES ($1, $2, $3, $4, $5, 'open')
            RETURNING *
            """,
            ticker_id, data.shares, data.purchase_price, purchase_date_obj, thesis_id,
        )

        await db.execute(
            """
            INSERT INTO cash_movements (type, amount, label, ticker_id)
            VALUES ('buy', $1, $2, $3)
            """,
            data.shares * data.purchase_price,
            f"Achat legacy {ticker_id} — {data.shares} titres @ {data.purchase_price}",
            ticker_id,
        )

        events_created = []
        for ev in calendar_events_input:
            if not ev.scheduled_date:
                continue
            try:
                ev_date = _date.fromisoformat(ev.scheduled_date)
            except ValueError:
                continue
            ev_row = await db.fetchrow(
                """
                INSERT INTO calendar_events
                    (thesis_id, ticker_id, event_type, label, scheduled_date,
                     peer_ticker, monitoring_mode, source, pending_validation)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                RETURNING *
                """,
                thesis_id, ticker_id, ev.event_type, ev.label, ev_date,
                ev.peer_ticker, ev.monitoring_mode, ev.source, ev.pending_validation,
            )
            events_created.append(_serialize(ev_row))

    try:
        from app.notifications.slack_webhook import SlackWebhook
        await SlackWebhook().send_thesis_validated(
            ticker=ticker_id,
            one_liner=one_liner or "",
            shares=data.shares,
            price=data.purchase_price,
        )
    except Exception as e:
        logger.warning(f"Slack notification failed: {e}")

    return {
        "thesis_id": thesis_id,
        "brief_id": brief_id,
        "status": "active",
        "position": _serialize(position_row),
        "calendar_events_created": events_created,
    }


@router.get("/theses/{thesis_id}/messages")
async def get_thesis_messages(thesis_id: int):
    async with get_db_session() as db:
        await _get_thesis_or_404(db, thesis_id)
        rows = await db.fetch(
            "SELECT * FROM thesis_messages WHERE thesis_id=$1 ORDER BY created_at",
            thesis_id,
        )
    return [_serialize(r) for r in rows]
