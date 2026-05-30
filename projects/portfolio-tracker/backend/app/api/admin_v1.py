"""
Admin V1 — gestion des agent_prompts, statut système, calendrier et logs.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class AgentPromptUpdate(BaseModel):
    prompt_text: Optional[str] = None
    dust_agent_id: Optional[str] = None
    dust_agent_url: Optional[str] = None


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# ─────────────────────────── Agent Prompts ───────────────────────────────────

@router.get("/agents")
async def list_agents():
    async with get_db_session() as db:
        rows = await db.fetch("SELECT * FROM agent_prompts ORDER BY agent_name")
    return [_serialize(r) for r in rows]


@router.patch("/agents/{agent_name}")
async def update_agent(agent_name: str, data: AgentPromptUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    # Quand on modifie le prompt, on marque synced=FALSE
    updates["synced"] = False
    updates["updated_at"] = "now"

    set_parts = ["updated_at=NOW()", "synced=FALSE"]
    values = []
    idx = 2
    for k, v in data.model_dump().items():
        if v is not None:
            set_parts.append(f"{k}=${idx}")
            values.append(v)
            idx += 1
    set_clause = ", ".join(set_parts)

    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE agent_prompts SET {set_clause} WHERE agent_name=$1 RETURNING *",
            agent_name, *values,
        )
    if not row:
        raise HTTPException(404, f"Agent '{agent_name}' introuvable")
    return _serialize(row)


@router.post("/agents/{agent_name}/sync")
async def sync_agent(agent_name: str):
    """Marque l'agent comme synchronisé (synced=TRUE) et incrémente la version."""
    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            UPDATE agent_prompts
            SET synced=TRUE, last_synced_at=NOW(), version=version+1, updated_at=NOW()
            WHERE agent_name=$1
            RETURNING *
            """,
            agent_name,
        )
    if not row:
        raise HTTPException(404, f"Agent '{agent_name}' introuvable")
    return _serialize(row)


# ─────────────────────────── Status système ──────────────────────────────────

@router.get("/status")
async def system_status():
    """Ping Dust, Slack webhook et market data."""
    import httpx

    status = {}

    # Dust
    dust_ok = False
    if settings.DUST_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://dust.tt/api/v1/w/{settings.DUST_WORKSPACE_ID}/members",
                    headers={"Authorization": f"Bearer {settings.DUST_API_KEY}"},
                )
                dust_ok = r.status_code == 200
        except Exception:
            pass
    status["dust"] = "ok" if dust_ok else ("unconfigured" if not settings.DUST_API_KEY else "error")

    # Slack webhook
    slack_ok = False
    if settings.SLACK_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json={"text": "ping"},
                )
                slack_ok = r.status_code == 200
        except Exception:
            pass
    status["slack_webhook"] = "ok" if slack_ok else ("unconfigured" if not settings.SLACK_WEBHOOK_URL else "error")

    # FMP / market data
    fmp_ok = False
    if settings.FMP_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={settings.FMP_API_KEY}"
                )
                fmp_ok = r.status_code == 200
        except Exception:
            pass
    status["fmp"] = "ok" if fmp_ok else "error"

    # DB agents sync status
    async with get_db_session() as db:
        agents = await db.fetch("SELECT agent_name, synced FROM agent_prompts")
    status["agents_sync"] = {r["agent_name"]: r["synced"] for r in agents}

    return status


# ─────────────────────────── Calendar ────────────────────────────────────────

@router.get("/calendar")
async def admin_calendar(from_date: Optional[str] = None):
    """Tous les calendar_events V1 à venir avec join tickers + theses."""
    from datetime import date
    if from_date:
        date_filter = date.fromisoformat(from_date)
    else:
        date_filter = date.today()

    async with get_db_session() as db:
        rows = await db.fetch(
            """
            SELECT
                ce.*,
                t.name   AS ticker_name,
                t.status AS ticker_status,
                th.one_liner AS thesis_one_liner
            FROM calendar_events ce
            LEFT JOIN tickers t ON t.id = ce.ticker_id
            LEFT JOIN theses th ON th.id = ce.thesis_id
            WHERE ce.scheduled_date >= $1
            ORDER BY ce.scheduled_date ASC
            """,
            date_filter,
        )
    return [_serialize(r) for r in rows]


# ─────────────────────────── Logs ────────────────────────────────────────────

@router.get("/logs")
async def admin_logs(limit: int = 50):
    """Monitoring sessions récentes + celles en erreur."""
    async with get_db_session() as db:
        recent = await db.fetch(
            """
            SELECT ms.*, t.name AS ticker_name
            FROM monitoring_sessions ms
            LEFT JOIN tickers t ON t.id = ms.ticker_id
            ORDER BY ms.created_at DESC
            LIMIT $1
            """,
            limit,
        )
        errors = await db.fetch(
            """
            SELECT ms.*, t.name AS ticker_name
            FROM monitoring_sessions ms
            LEFT JOIN tickers t ON t.id = ms.ticker_id
            WHERE ms.status IN ('blocked_sync')
               OR ms.result_json::text LIKE '%error%'
            ORDER BY ms.created_at DESC
            LIMIT 20
            """,
        )

    return {
        "recent_sessions": [_serialize(r) for r in recent],
        "errors": [_serialize(r) for r in errors],
    }
