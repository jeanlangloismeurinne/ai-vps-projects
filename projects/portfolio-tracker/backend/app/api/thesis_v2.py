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


# ─────────────────────────── Helpers ─────────────────────────────────────────

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


@router.get("/theses/{thesis_id}/messages")
async def get_thesis_messages(thesis_id: int):
    async with get_db_session() as db:
        await _get_thesis_or_404(db, thesis_id)
        rows = await db.fetch(
            "SELECT * FROM thesis_messages WHERE thesis_id=$1 ORDER BY created_at",
            thesis_id,
        )
    return [_serialize(r) for r in rows]
