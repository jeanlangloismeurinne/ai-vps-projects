import logging
from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import PortfolioSettingsUpdate, CashOperationCreate

router = APIRouter(prefix="/portfolio", tags=["portfolio-settings"])
logger = logging.getLogger(__name__)


@router.get("/settings")
async def get_settings():
    async with get_db_session() as db:
        row = await db.fetchrow("SELECT * FROM portfolio_settings ORDER BY updated_at DESC LIMIT 1")
    if not row:
        raise HTTPException(404, "Portfolio settings not initialized")
    return _serialize(row)


@router.patch("/settings")
async def update_settings(data: PortfolioSettingsUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE portfolio_settings SET {set_clause}, updated_at=NOW() WHERE id=(SELECT id FROM portfolio_settings LIMIT 1) RETURNING *",
            *updates.values()
        )
    if not row:
        raise HTTPException(404, "Portfolio settings not found")
    return _serialize(row)


@router.get("/cash-log")
async def get_cash_log(limit: int = 100):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM portfolio_cash_log ORDER BY operation_date DESC LIMIT $1", limit
        )
    return [_serialize(r) for r in rows]


@router.post("/cash-operation", status_code=201)
async def cash_operation(data: CashOperationCreate):
    if data.operation_type not in ("deposit", "withdrawal"):
        raise HTTPException(400, "operation_type must be deposit or withdrawal")

    async with get_db_session() as db:
        settings_row = await db.fetchrow(
            "SELECT * FROM portfolio_settings ORDER BY updated_at DESC LIMIT 1"
        )
        if not settings_row:
            raise HTTPException(404, "Portfolio settings not initialized")

        current_cash = float(settings_row["cash_balance_eur"])
        if data.operation_type == "deposit":
            new_balance = current_cash + data.amount_eur
        else:
            new_balance = current_cash - data.amount_eur

        await db.execute(
            "UPDATE portfolio_settings SET cash_balance_eur=$1, updated_at=NOW() WHERE id=$2",
            new_balance, settings_row["id"]
        )

        log_row = await db.fetchrow("""
            INSERT INTO portfolio_cash_log
                (operation_type, amount_eur, notes, balance_after)
            VALUES ($1,$2,$3,$4)
            RETURNING *
        """, data.operation_type, data.amount_eur, data.notes, new_balance)

    return _serialize(log_row)


def _serialize(row) -> dict:
    if row is None:
        return {}
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d
