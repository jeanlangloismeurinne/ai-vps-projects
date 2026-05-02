from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import AnalystActionCreate, AnalystActionUpdate

router = APIRouter(prefix="/api/analysts", tags=["analysts"])


@router.get("")
async def list_analyst_actions(ticker: str = None, firm: str = None, limit: int = 50):
    conditions, params, i = [], [], 1
    if ticker:
        conditions.append(f"ticker = ${i}")
        params.append(ticker)
        i += 1
    if firm:
        conditions.append(f"analyst_firm ILIKE ${i}")
        params.append(f"%{firm}%")
        i += 1
    params.append(limit)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    async with get_db_session() as db:
        rows = await db.fetch(
            f"SELECT * FROM analyst_actions {where} ORDER BY action_date DESC LIMIT ${i}",
            *params
        )
    return [_serialize(row) for row in rows]


@router.post("", status_code=201)
async def log_analyst_action(data: AnalystActionCreate):
    async with get_db_session() as db:
        row = await db.fetchrow("""
            INSERT INTO analyst_actions
                (analyst_firm, ticker, action_date, action_type,
                 from_recommendation, to_recommendation, from_target, to_target,
                 stock_price_at_action, notes)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING *
        """,
            data.analyst_firm, data.ticker, data.action_date, data.action_type,
            data.from_recommendation, data.to_recommendation,
            data.from_target, data.to_target,
            data.stock_price_at_action, data.notes,
        )
    return _serialize(row)


@router.patch("/{action_id}")
async def update_analyst_action(action_id: str, data: AnalystActionUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE analyst_actions SET {set_clause} WHERE id=$1 RETURNING *",
            action_id, *updates.values()
        )
    if not row:
        raise HTTPException(404, "Action not found")
    return _serialize(row)


@router.get("/track-records")
async def get_track_records(ticker: str = None, firm: str = None):
    conditions, params, i = [], [], 1
    if ticker:
        conditions.append(f"ticker = ${i}")
        params.append(ticker)
        i += 1
    if firm:
        conditions.append(f"analyst_firm ILIKE ${i}")
        params.append(f"%{firm}%")
        i += 1
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    async with get_db_session() as db:
        rows = await db.fetch(
            f"SELECT * FROM analyst_track_records {where} ORDER BY total_actions DESC",
            *params
        )
    return [_serialize(row) for row in rows]


def _serialize(row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d
