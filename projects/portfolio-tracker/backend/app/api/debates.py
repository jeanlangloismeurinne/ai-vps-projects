"""
Conviction Debates V1 — débats PASS/PROCEED entre l'utilisateur et l'OpportunityAgent.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session

router = APIRouter(prefix="/debates", tags=["debates-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class DebateCreate(BaseModel):
    thesis_id: int
    opportunity_brief_id: int
    user_conviction_note: str


class DebateMessage(BaseModel):
    content: str


class DebateClose(BaseModel):
    outcome: str           # 'pass' | 'monitor' | 'proceed'
    action: str            # 'maintain' | 'reduce' | 'close'
    conviction_override_note: Optional[str] = None
    conviction_review_date: Optional[str] = None   # ISO date
    agent_revised: bool = False
    revision_rationale: Optional[str] = None
    final_recommendation: Optional[str] = None


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_debate_or_404(db, debate_id: int):
    row = await db.fetchrow("SELECT * FROM conviction_debates WHERE id=$1", debate_id)
    if not row:
        raise HTTPException(404, f"Débat #{debate_id} introuvable")
    return row


# ─────────────────────────── Endpoints ───────────────────────────────────────

@router.post("", status_code=201)
async def create_debate(data: DebateCreate):
    """
    Crée un debate de conviction.
    Envoie automatiquement le premier message (brief PASS + conviction note de l'utilisateur).
    """
    from app.agents.opportunity_agent import OpportunityAgent, AgentNotSyncedError

    async with get_db_session() as db:
        # Vérifie que la thèse et le brief existent
        thesis = await db.fetchrow("SELECT * FROM theses WHERE id=$1", data.thesis_id)
        if not thesis:
            raise HTTPException(404, f"Thèse #{data.thesis_id} introuvable")

        brief = await db.fetchrow("SELECT * FROM opportunity_briefs WHERE id=$1", data.opportunity_brief_id)
        if not brief:
            raise HTTPException(404, f"Brief #{data.opportunity_brief_id} introuvable")

        # Crée le débat
        debate_row = await db.fetchrow(
            """
            INSERT INTO conviction_debates
                (thesis_id, opportunity_brief_id, user_conviction_note, status)
            VALUES ($1, $2, $3, 'open')
            RETURNING *
            """,
            data.thesis_id, data.opportunity_brief_id, data.user_conviction_note,
        )
        debate_id = debate_row["id"]

        # Stocke le message de l'utilisateur
        brief_summary = (
            brief["brief_json"].get("verdict", {}).get("recommendation", "PASS")
            if brief["brief_json"]
            else "PASS"
        )
        user_msg = (
            f"L'agent a conclu : {brief_summary}\n\n"
            f"Ma position : {data.user_conviction_note}"
        )
        await db.execute(
            """
            INSERT INTO opportunity_messages
                (brief_id, debate_id, role, content, mode)
            VALUES ($1, $2, 'user', $3, 'conviction_challenge')
            """,
            data.opportunity_brief_id, debate_id, user_msg,
        )

    # Premier appel agent (conviction_challenge)
    try:
        agent = OpportunityAgent()
        result = await agent.run(mode="conviction_challenge", message=user_msg)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"OpportunityAgent conviction_challenge error (debate #{debate_id}): {e}")
        raise HTTPException(502, f"Erreur agent: {e}")

    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO opportunity_messages
                (brief_id, debate_id, role, content, mode, raw_payload)
            VALUES ($1, $2, 'agent', $3, 'conviction_challenge', $4)
            RETURNING *
            """,
            data.opportunity_brief_id, debate_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "debate": _serialize(debate_row),
        "first_agent_response": result["content"],
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/{debate_id}")
async def get_debate(debate_id: int):
    async with get_db_session() as db:
        debate = await _get_debate_or_404(db, debate_id)
        messages = await db.fetch(
            """
            SELECT * FROM opportunity_messages
            WHERE debate_id=$1
            ORDER BY created_at
            """,
            debate_id,
        )
    debate_dict = _serialize(debate)
    debate_dict["messages"] = [_serialize(m) for m in messages]
    return debate_dict


@router.post("/{debate_id}/messages", status_code=201)
async def send_debate_message(debate_id: int, data: DebateMessage):
    """Envoie un message à l'agent en mode conviction_challenge."""
    from app.agents.opportunity_agent import OpportunityAgent, AgentNotSyncedError

    async with get_db_session() as db:
        debate = await _get_debate_or_404(db, debate_id)
        if debate["status"] != "open":
            raise HTTPException(409, "Ce débat est fermé")

        await db.execute(
            """
            INSERT INTO opportunity_messages
                (brief_id, debate_id, role, content, mode)
            VALUES ($1, $2, 'user', $3, 'conviction_challenge')
            """,
            debate["opportunity_brief_id"], debate_id, data.content,
        )

    try:
        agent = OpportunityAgent()
        result = await agent.run(mode="conviction_challenge", message=data.content)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Erreur agent: {e}")

    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO opportunity_messages
                (brief_id, debate_id, role, content, mode, raw_payload)
            VALUES ($1, $2, 'agent', $3, 'conviction_challenge', $4)
            RETURNING *
            """,
            debate["opportunity_brief_id"], debate_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "message": _serialize(msg_row),
        "content": result["content"],
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/{debate_id}/close")
async def close_debate(debate_id: int, data: DebateClose):
    """
    Ferme le débat selon l'outcome.

    Pour 'maintain' (PASS maintenu) :
      - debate.status = 'closed_pass'
      - thesis.conviction_override_note = note
      - thesis.conviction_review_date = date
      - thesis.status = 'active'

    Pour 'proceed' (révision PROCEED) :
      - debate.status = 'closed_proceed'
      - retourne info pour redirection Page 3 (nouvelle thèse)

    Pour 'monitor' :
      - debate.status = 'closed_monitor'
    """
    status_map = {
        "pass": "closed_pass",
        "monitor": "closed_monitor",
        "proceed": "closed_proceed",
    }
    if data.outcome not in status_map:
        raise HTTPException(400, "outcome doit être 'pass', 'monitor' ou 'proceed'")

    debate_status = status_map[data.outcome]

    async with get_db_session() as db:
        debate = await _get_debate_or_404(db, debate_id)
        if debate["status"] != "open":
            raise HTTPException(409, "Ce débat est déjà fermé")

        # Ferme le débat
        debate_row = await db.fetchrow(
            """
            UPDATE conviction_debates
            SET status=$1, final_recommendation=$2,
                agent_revised=$3, revision_rationale=$4, closed_at=NOW()
            WHERE id=$5
            RETURNING *
            """,
            debate_status,
            data.final_recommendation or data.outcome.upper(),
            data.agent_revised,
            data.revision_rationale,
            debate_id,
        )

        response = {"debate": _serialize(debate_row)}

        if data.outcome == "pass" and data.action == "maintain":
            # Met à jour la thèse pour suivi conviction
            await db.execute(
                """
                UPDATE theses
                SET conviction_override_note=$1,
                    conviction_review_date=$2,
                    status='active',
                    updated_at=NOW()
                WHERE id=$3
                """,
                data.conviction_override_note,
                data.conviction_review_date,
                debate["thesis_id"],
            )
            response["action"] = "thesis_updated_with_override"
            response["thesis_id"] = debate["thesis_id"]

        elif data.outcome == "proceed":
            # Retourne l'info pour la redirection vers Page 3 (nouvelle thèse)
            response["action"] = "redirect_to_thesis_construction"
            response["ticker_id"] = (
                (await db.fetchrow("SELECT ticker_id FROM theses WHERE id=$1", debate["thesis_id"]))
                or {}
            ).get("ticker_id")
            response["opportunity_brief_id"] = debate["opportunity_brief_id"]

        elif data.outcome == "monitor":
            response["action"] = "monitor_maintained"

    return response
