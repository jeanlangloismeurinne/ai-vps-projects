"""
Monitoring Sessions V1 — suivi des thèses via MonitoringAgentV1.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session

router = APIRouter(tags=["monitoring-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class SessionCreate(BaseModel):
    trigger_type: str
    trigger_label: str
    mode: int              # 1..5
    thesis_id: Optional[int] = None
    message: Optional[str] = None   # contexte libre si fourni directement


class ChatMessage(BaseModel):
    content: str


class SessionUpdate(BaseModel):
    status: str  # 'archived' | 'reviewed'


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_session_or_404(db, session_id: int):
    row = await db.fetchrow("SELECT * FROM monitoring_sessions WHERE id=$1", session_id)
    if not row:
        raise HTTPException(404, f"Session #{session_id} introuvable")
    return row


async def _build_monitoring_context(db, ticker_id: str, thesis_id: Optional[int], mode: int, trigger_label: str) -> str:
    """Construit le contexte texte envoyé à l'agent."""
    parts = [f"Ticker : {ticker_id}", f"Trigger : {trigger_label}", f"Mode demandé : {mode}"]

    if thesis_id:
        thesis = await db.fetchrow("SELECT * FROM theses WHERE id=$1", thesis_id)
        if thesis:
            parts.append(f"Thèse — one_liner : {thesis['one_liner'] or '(non renseigné)'}")
            if thesis["thesis_json"]:
                import json
                parts.append(f"Thèse JSON :\n```json\n{json.dumps(thesis['thesis_json'], ensure_ascii=False, indent=2)}\n```")

    # Données de marché
    try:
        from app.data_collection.data_service import DataService
        from app.config import settings
        m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
        parts.append(
            f"Données de marché : prix={m1.get('price')}, PER NTM={m1.get('forward_pe')}, "
            f"market_cap={m1.get('market_cap')}"
        )
    except Exception:
        pass

    return "\n\n".join(parts)


# ─────────────────────────── Sessions sous /tickers/{ticker_id}/monitoring ───

@router.get("/tickers/{ticker_id}/monitoring")
async def list_sessions(ticker_id: str):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM monitoring_sessions WHERE ticker_id=$1 ORDER BY created_at DESC",
            ticker_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/tickers/{ticker_id}/monitoring", status_code=201)
async def create_and_run_session(ticker_id: str, data: SessionCreate):
    """
    Crée une session de monitoring et la lance immédiatement via MonitoringAgentV1.
    Vérifie la sync de l'agent avant toute chose.
    """
    from app.agents.monitoring_agent_v1 import MonitoringAgentV1, AgentNotSyncedError

    if data.mode not in range(1, 6):
        raise HTTPException(400, "mode doit être entre 1 et 5")

    # Vérifie sync avant création
    try:
        agent = MonitoringAgentV1()
        # _check_sync lève AgentNotSyncedError si non synced
        from app.db.database import get_db_session as _gds
        async with _gds() as db:
            sync_row = await db.fetchrow(
                "SELECT synced, dust_agent_id FROM agent_prompts WHERE agent_name='monitoring-agent'"
            )
        if sync_row and not sync_row["synced"]:
            # Crée la session en status bloqué
            async with _gds() as db:
                session_row = await db.fetchrow(
                    """
                    INSERT INTO monitoring_sessions
                        (ticker_id, thesis_id, trigger_type, trigger_label, mode, status)
                    VALUES ($1,$2,$3,$4,$5,'blocked_sync')
                    RETURNING *
                    """,
                    ticker_id, data.thesis_id, data.trigger_type, data.trigger_label, data.mode,
                )
            return {
                "session": _serialize(session_row),
                "error": "Agent monitoring-agent non synchronisé. Sync requis avant exécution.",
                "status": "blocked_sync",
            }
    except Exception:
        pass

    # Crée la session en status 'running'
    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")

        context_message = data.message
        if not context_message:
            context_message = await _build_monitoring_context(
                db, ticker_id, data.thesis_id, data.mode, data.trigger_label
            )

        session_row = await db.fetchrow(
            """
            INSERT INTO monitoring_sessions
                (ticker_id, thesis_id, trigger_type, trigger_label, mode, status)
            VALUES ($1,$2,$3,$4,$5,'running')
            RETURNING *
            """,
            ticker_id, data.thesis_id, data.trigger_type, data.trigger_label, data.mode,
        )
    session_id = session_row["id"]

    try:
        result = await agent.run(mode=data.mode, message=context_message)
    except AgentNotSyncedError as e:
        async with get_db_session() as db:
            await db.execute(
                "UPDATE monitoring_sessions SET status='blocked_sync' WHERE id=$1", session_id
            )
        raise HTTPException(503, str(e))
    except Exception as e:
        async with get_db_session() as db:
            await db.execute(
                "UPDATE monitoring_sessions SET status='completed', result_json=$2 WHERE id=$1",
                session_id, {"error": str(e)},
            )
        logger.error(f"MonitoringAgent error (session #{session_id}): {e}")
        raise HTTPException(502, f"Erreur agent: {e}")

    # Parse le JSON de résultat
    parsed = agent.extract_json(result["content"])
    alert_level = None
    routing_suggestion = None
    if parsed:
        alert_level = parsed.get("alert_level") or parsed.get("flag")
        routing_suggestion = parsed.get("routing_suggestion") or parsed.get("action")

    # Met à jour la session
    async with get_db_session() as db:
        updated_row = await db.fetchrow(
            """
            UPDATE monitoring_sessions
            SET status='completed', result_json=$2, alert_level=$3,
                routing_suggestion=$4, model_used=$5, completed_at=NOW()
            WHERE id=$1
            RETURNING *
            """,
            session_id,
            parsed or {"raw": result["content"]},
            alert_level,
            routing_suggestion,
            result.get("model"),
        )
        # Stocke les messages
        await db.execute(
            "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, context_message,
        )
        await db.execute(
            """
            INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
            VALUES ($1, 'agent', $2, $3)
            """,
            session_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    # Notification Slack si alerte
    if alert_level in ("REVIEW_REQUIRED", "CRITICAL"):
        try:
            from app.notifications.slack_webhook import SlackWebhook
            await SlackWebhook().send_monitoring_alert(
                ticker=ticker_id,
                alert_level=alert_level,
                mode=data.mode,
                label=data.trigger_label,
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Slack monitoring alert failed: {e}")

    return {
        "session": _serialize(updated_row),
        "alert_level": alert_level,
        "routing_suggestion": routing_suggestion,
        "tokens_input": result.get("tokens_input"),
        "tokens_output": result.get("tokens_output"),
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/tickers/{ticker_id}/monitoring/{session_id}")
async def get_session(ticker_id: str, session_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM monitoring_sessions WHERE id=$1 AND ticker_id=$2",
            session_id, ticker_id,
        )
    if not row:
        raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")
    return _serialize(row)


@router.patch("/tickers/{ticker_id}/monitoring/{session_id}")
async def update_session(ticker_id: str, session_id: int, data: SessionUpdate):
    """Met à jour le statut d'une session (ex: 'archived')."""
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM monitoring_sessions WHERE id=$1 AND ticker_id=$2",
            session_id, ticker_id,
        )
        if not row:
            raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")
        updated = await db.fetchrow(
            "UPDATE monitoring_sessions SET status=$1, updated_at=NOW() WHERE id=$2 RETURNING *",
            data.status, session_id,
        )
    return _serialize(updated)


@router.post("/tickers/{ticker_id}/monitoring/{session_id}/chat", status_code=201)
async def chat_in_session(ticker_id: str, session_id: int, data: ChatMessage):
    """Envoie un message supplémentaire dans une session existante (mode freeform)."""
    from app.agents.monitoring_agent_v1 import MonitoringAgentV1, AgentNotSyncedError

    async with get_db_session() as db:
        session = await _get_session_or_404(db, session_id)
        if session["ticker_id"] != ticker_id:
            raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")

        await db.execute(
            "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, data.content,
        )

    try:
        agent = MonitoringAgentV1()
        result = await agent.run(mode=session["mode"], message=data.content)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Erreur agent: {e}")

    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
            VALUES ($1, 'agent', $2, $3)
            RETURNING *
            """,
            session_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "message": _serialize(msg_row),
        "content": result["content"],
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/monitoring/{session_id}/messages")
async def get_session_messages(session_id: int):
    async with get_db_session() as db:
        await _get_session_or_404(db, session_id)
        rows = await db.fetch(
            "SELECT * FROM monitoring_messages WHERE session_id=$1 ORDER BY created_at",
            session_id,
        )
    return [_serialize(r) for r in rows]
