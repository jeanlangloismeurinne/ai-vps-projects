"""
Calendar V2 — gestion des événements calendrier V1.
"""
import logging
from typing import Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import get_db_session

router = APIRouter(prefix="/calendar-v2", tags=["calendar-v2"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class EventCreate(BaseModel):
    thesis_id: Optional[int] = None
    ticker_id: str
    event_type: str
    label: str
    scheduled_date: str   # ISO date
    peer_ticker: Optional[str] = None
    monitoring_mode: int = 2
    source: str = "manual"
    pending_validation: bool = False


class EventUpdate(BaseModel):
    label: Optional[str] = None
    scheduled_date: Optional[str] = None
    monitoring_mode: Optional[int] = None
    pending_validation: Optional[bool] = None


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# ─────────────────────────── Endpoints ───────────────────────────────────────

@router.get("")
async def list_events(
    ticker_id: Optional[str] = Query(None),
    thesis_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None),
    include_triggered: bool = Query(False),
):
    conditions = []
    params = []
    idx = 1

    if not include_triggered:
        conditions.append(f"triggered = FALSE")

    if ticker_id:
        conditions.append(f"ce.ticker_id = ${idx}")
        params.append(ticker_id)
        idx += 1

    if thesis_id:
        conditions.append(f"ce.thesis_id = ${idx}")
        params.append(thesis_id)
        idx += 1

    if from_date:
        conditions.append(f"scheduled_date >= ${idx}")
        params.append(date.fromisoformat(from_date))
        idx += 1
    else:
        conditions.append(f"scheduled_date >= ${idx}")
        params.append(date.today())
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT ce.*, t.name AS ticker_name, t.status AS ticker_status,
               t.company_type AS ticker_company_type,
               th.one_liner AS thesis_one_liner
        FROM calendar_events ce
        LEFT JOIN tickers t ON t.id = ce.ticker_id
        LEFT JOIN theses th ON th.id = ce.thesis_id
        {where}
        ORDER BY ce.scheduled_date ASC
    """

    async with get_db_session() as db:
        rows = await db.fetch(query, *params)

    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
async def create_event(data: EventCreate):
    ev_date = date.fromisoformat(data.scheduled_date)

    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", data.ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{data.ticker_id}' introuvable")

        row = await db.fetchrow(
            """
            INSERT INTO calendar_events
                (thesis_id, ticker_id, event_type, label, scheduled_date,
                 peer_ticker, monitoring_mode, source, pending_validation)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING *
            """,
            data.thesis_id, data.ticker_id, data.event_type, data.label, ev_date,
            data.peer_ticker, data.monitoring_mode, data.source, data.pending_validation,
        )
    return _serialize(row)


@router.patch("/{event_id}")
async def update_event(event_id: int, data: EventUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")

    set_parts = []
    values = []
    idx = 2
    for k, v in updates.items():
        if k == "scheduled_date":
            set_parts.append(f"scheduled_date=${idx}")
            values.append(date.fromisoformat(v))
        else:
            set_parts.append(f"{k}=${idx}")
            values.append(v)
        idx += 1
    set_clause = ", ".join(set_parts)

    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE calendar_events SET {set_clause} WHERE id=$1 RETURNING *",
            event_id, *values,
        )
    if not row:
        raise HTTPException(404, f"Événement #{event_id} introuvable")
    return _serialize(row)


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "DELETE FROM calendar_events WHERE id=$1 RETURNING id", event_id
        )
    if not row:
        raise HTTPException(404, f"Événement #{event_id} introuvable")


@router.get("/{event_id}/sessions")
async def list_event_sessions(event_id: int):
    """Sessions monitoring liées à cet événement calendrier."""
    async with get_db_session() as db:
        rows = await db.fetch(
            """
            SELECT ms.*, t.name AS ticker_name
            FROM monitoring_sessions ms
            LEFT JOIN tickers t ON t.id = ms.ticker_id
            WHERE ms.calendar_event_id = $1
            ORDER BY ms.created_at ASC
            """,
            event_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/{event_id}/validate")
async def validate_event(event_id: int):
    """Valide un événement pending_validation=TRUE (ex : suggéré par l'agent)."""
    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            UPDATE calendar_events
            SET pending_validation=FALSE, source='manual'
            WHERE id=$1
            RETURNING *
            """,
            event_id,
        )
    if not row:
        raise HTTPException(404, f"Événement #{event_id} introuvable")
    return _serialize(row)
