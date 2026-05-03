from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import WatchlistCreate, WatchlistUpdate

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("")
async def list_watchlist():
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM watchlist ORDER BY identified_date DESC"
        )
    return [_serialize(row) for row in rows]


@router.post("", status_code=201)
async def add_to_watchlist(data: WatchlistCreate):
    async with get_db_session() as db:
        existing = await db.fetchrow("SELECT id FROM watchlist WHERE ticker = $1", data.ticker)
        if existing:
            raise HTTPException(400, f"{data.ticker} already on watchlist")
        row = await db.fetchrow("""
            INSERT INTO watchlist
                (ticker, company_name, sector_schema, rationale,
                 entry_price_target, trigger_alert_price)
            VALUES ($1,$2,$3,$4,$5,$6)
            RETURNING *
        """,
            data.ticker, data.company_name, data.sector_schema, data.rationale,
            data.entry_price_target, data.trigger_alert_price,
        )
    return _serialize(row)


@router.patch("/{item_id}")
async def update_watchlist_item(item_id: str, data: WatchlistUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE watchlist SET {set_clause} WHERE id=$1 RETURNING *",
            item_id, *updates.values()
        )
    if not row:
        raise HTTPException(404, "Watchlist item not found")
    return _serialize(row)


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(item_id: str):
    async with get_db_session() as db:
        result = await db.execute("DELETE FROM watchlist WHERE id=$1", item_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Watchlist item not found")


@router.post("/{item_id}/promote")
async def promote_to_position(item_id: str):
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id=$1", item_id)
        if not item:
            raise HTTPException(404, "Watchlist item not found")
        if not item["entry_price_target"]:
            raise HTTPException(400, "entry_price_target required to promote")
        await db.execute(
            "UPDATE watchlist SET status='promoted' WHERE id=$1", item_id
        )
    return {
        "message": "Ready to create position",
        "suggested_payload": {
            "ticker": item["ticker"],
            "company_name": item["company_name"],
            "sector_schema": item["sector_schema"],
            "entry_price": float(item["entry_price_target"]),
        }
    }


def _serialize(row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d
