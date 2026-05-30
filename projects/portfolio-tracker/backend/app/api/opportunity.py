"""
Opportunity Briefs V1 — analyse d'opportunités avec l'OpportunityAgent.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session

router = APIRouter(tags=["opportunity-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class BriefCreate(BaseModel):
    source: str = "manual"  # 'manual' | 'watchlist_threshold' | 'monitoring_reroute'


class BriefUpdate(BaseModel):
    brief_json: Optional[dict] = None
    status: Optional[str] = None
    conviction_score: Optional[int] = None
    recommendation: Optional[str] = None
    screening_bypassed: Optional[bool] = None


class ChatMessage(BaseModel):
    role: str = "user"
    content: str
    mode: str = "freeform"  # 'freeform' | 'json_generation' | 'conviction_challenge'


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_brief_or_404(db, brief_id: int):
    row = await db.fetchrow("SELECT * FROM opportunity_briefs WHERE id=$1", brief_id)
    if not row:
        raise HTTPException(404, f"Brief #{brief_id} introuvable")
    return row


# ─────────────────────────── Briefs sous /tickers/{ticker_id} ────────────────

@router.get("/tickers/{ticker_id}/opportunities")
async def list_briefs(ticker_id: str):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM opportunity_briefs WHERE ticker_id=$1 ORDER BY created_at DESC",
            ticker_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/tickers/{ticker_id}/opportunities", status_code=201)
async def create_brief(ticker_id: str, data: BriefCreate):
    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")
        row = await db.fetchrow(
            "INSERT INTO opportunity_briefs (ticker_id, source) VALUES ($1,$2) RETURNING *",
            ticker_id, data.source,
        )
    return _serialize(row)


@router.get("/tickers/{ticker_id}/opportunities/{brief_id}")
async def get_brief(ticker_id: str, brief_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM opportunity_briefs WHERE id=$1 AND ticker_id=$2",
            brief_id, ticker_id,
        )
    if not row:
        raise HTTPException(404, f"Brief #{brief_id} introuvable pour ticker '{ticker_id}'")
    return _serialize(row)


@router.patch("/tickers/{ticker_id}/opportunities/{brief_id}")
async def update_brief(ticker_id: str, brief_id: int, data: BriefUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    updates["updated_at"] = "NOW()"
    # Construction dynamique sans NOW() dans les paramètres positionnels
    set_parts = []
    values = []
    idx = 3
    for k, v in updates.items():
        if k == "updated_at":
            set_parts.append("updated_at=NOW()")
        else:
            set_parts.append(f"{k}=${idx}")
            values.append(v)
            idx += 1
    set_clause = ", ".join(set_parts)
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE opportunity_briefs SET {set_clause} WHERE id=$1 AND ticker_id=$2 RETURNING *",
            brief_id, ticker_id, *values,
        )
    if not row:
        raise HTTPException(404, f"Brief #{brief_id} introuvable pour ticker '{ticker_id}'")
    return _serialize(row)


# ─────────────────────────── Chat / Refresh JSON sous /opportunities/{id} ────

@router.post("/opportunities/{brief_id}/chat", status_code=201)
async def chat_with_brief(brief_id: int, data: ChatMessage):
    from app.agents.opportunity_agent import OpportunityAgent, AgentNotSyncedError

    async with get_db_session() as db:
        brief = await _get_brief_or_404(db, brief_id)

        # Stocke le message utilisateur
        await db.execute(
            """
            INSERT INTO opportunity_messages (brief_id, role, content, mode)
            VALUES ($1, $2, $3, $4)
            """,
            brief_id, "user", data.content, data.mode,
        )

    if data.mode not in ("freeform", "conviction_challenge"):
        raise HTTPException(400, "Ce endpoint accepte uniquement mode='freeform' ou 'conviction_challenge'")

    try:
        agent = OpportunityAgent()
        result = await agent.run(mode=data.mode, message=data.content)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        import httpx as _httpx
        if isinstance(e, _httpx.HTTPStatusError):
            status = e.response.status_code
            error_msg = f"Service Dust indisponible ({status}) — réessaie dans quelques secondes"
        elif isinstance(e, (_httpx.TimeoutException, TimeoutError)):
            error_msg = "L'agent Dust n'a pas répondu dans le délai imparti — réessaie"
        else:
            error_msg = str(e)
        logger.error(f"OpportunityAgent error (brief #{brief_id}): {e}")
        async with get_db_session() as db:
            await db.execute(
                """INSERT INTO opportunity_messages (brief_id, role, content, mode)
                   VALUES ($1, 'error', $2, $3)""",
                brief_id, error_msg, data.mode,
            )
        raise HTTPException(502, f"Erreur agent: {error_msg}")

    # Stocke la réponse de l'agent
    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO opportunity_messages (brief_id, role, content, mode, raw_payload)
            VALUES ($1, 'agent', $2, $3, $4)
            RETURNING *
            """,
            brief_id, result["content"], data.mode,
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


@router.post("/opportunities/{brief_id}/refresh-json")
async def refresh_brief_json(brief_id: int):
    """
    Récupère l'historique complet du brief, appelle l'agent en mode json_generation,
    parse le JSON retourné et met à jour opportunity_briefs.
    """
    from app.agents.opportunity_agent import OpportunityAgent, AgentNotSyncedError

    async with get_db_session() as db:
        brief = await _get_brief_or_404(db, brief_id)
        messages = await db.fetch(
            "SELECT role, content FROM opportunity_messages WHERE brief_id=$1 ORDER BY created_at",
            brief_id,
        )

    # Construit le message d'historique
    history_parts = []
    for msg in messages:
        history_parts.append(f"[{msg['role'].upper()}]\n{msg['content']}")
    history_text = "\n\n---\n\n".join(history_parts) if history_parts else "(aucun échange précédent)"
    full_message = (
        f"Ticker : {brief['ticker_id']}\n\n"
        f"Historique de la conversation :\n\n{history_text}"
    )

    try:
        agent = OpportunityAgent()
        result = await agent.run(mode="json_generation", message=full_message)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"OpportunityAgent json_generation error (brief #{brief_id}): {e}")
        raise HTTPException(502, f"Erreur agent: {e}")

    parsed = agent.extract_json(result["content"])
    if not parsed:
        raise HTTPException(422, "L'agent n'a pas retourné un JSON valide")

    # Mise à jour du brief
    conviction_score = parsed.get("verdict", {}).get("conviction_score") or parsed.get("conviction_score")
    recommendation = (
        parsed.get("verdict", {}).get("recommendation")
        or parsed.get("recommendation")
    )

    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            UPDATE opportunity_briefs
            SET brief_json=$1, conviction_score=$2, recommendation=$3, updated_at=NOW()
            WHERE id=$4
            RETURNING *
            """,
            parsed, conviction_score, recommendation, brief_id,
        )
        # Stocke le message json_generation
        await db.execute(
            """
            INSERT INTO opportunity_messages (brief_id, role, content, mode, raw_payload)
            VALUES ($1, 'agent', $2, 'json_generation', $3)
            """,
            brief_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "brief": _serialize(row),
        "parsed_json": parsed,
        "conviction_score": conviction_score,
        "recommendation": recommendation,
        "tokens_input": result.get("tokens_input"),
        "tokens_output": result.get("tokens_output"),
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/opportunities/{brief_id}/messages")
async def get_brief_messages(brief_id: int):
    async with get_db_session() as db:
        await _get_brief_or_404(db, brief_id)
        rows = await db.fetch(
            "SELECT * FROM opportunity_messages WHERE brief_id=$1 ORDER BY created_at",
            brief_id,
        )
    return [_serialize(r) for r in rows]
