from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import CalendarEventCreate
from app.calendar.calendar_builder import CalendarBuilder

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
async def list_events(upcoming_only: bool = False, ticker: str = None, limit: int = 50):
    conditions = []
    params = []
    i = 1
    if upcoming_only:
        conditions.append(f"event_date >= CURRENT_DATE")
    if ticker:
        conditions.append(f"ticker = ${i}")
        params.append(ticker)
        i += 1
    params.append(limit)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    async with get_db_session() as db:
        rows = await db.fetch(
            f"SELECT * FROM calendar_events {where} ORDER BY event_date ASC LIMIT ${i}",
            *params
        )
    return [_serialize(row) for row in rows]


@router.post("", status_code=201)
async def create_event(data: CalendarEventCreate):
    async with get_db_session() as db:
        row = await db.fetchrow("""
            INSERT INTO calendar_events
                (ticker, event_type, event_date, trigger_brief_date,
                 trigger_review_date, priority, source, notes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING *
        """,
            data.ticker, data.event_type, data.event_date,
            data.trigger_brief_date, data.trigger_review_date,
            data.priority, data.source, data.notes,
        )
    return _serialize(row)


@router.post("/refresh")
async def refresh_calendar():
    results = await CalendarBuilder().refresh_all()
    return {"results": results}


@router.patch("/{event_id}/processed")
async def mark_processed(event_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "UPDATE calendar_events SET processed=TRUE WHERE id=$1 RETURNING *", event_id
        )
    if not row:
        raise HTTPException(404, "Event not found")
    return _serialize(row)


def _serialize(row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d
