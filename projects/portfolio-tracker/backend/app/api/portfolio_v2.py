"""
Portfolio V2 — résumé, positions et mouvements de trésorerie.
"""
import logging
from typing import Optional
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session
from app.config import settings

router = APIRouter(prefix="/portfolio-v2", tags=["portfolio-v2"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class CashMovementCreate(BaseModel):
    type: str    # 'deposit' | 'withdrawal'
    amount: float
    label: Optional[str] = None


class PositionUpdate(BaseModel):
    status: str  # 'closed'
    sell_price: Optional[float] = None
    sell_date: Optional[str] = None  # ISO date


class PositionReduce(BaseModel):
    reduction_pct: float  # 0–100
    sell_price: Optional[float] = None
    sell_date: Optional[str] = None  # ISO date


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_cash_balance(db) -> float:
    """Calcule la trésorerie nette depuis cash_movements."""
    row = await db.fetchrow(
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN type IN ('deposit') THEN amount
                WHEN type IN ('withdrawal', 'buy') THEN -amount
                WHEN type = 'sell' THEN amount
                ELSE 0
            END
        ), 0) AS balance
        FROM cash_movements
        """
    )
    return float(row["balance"]) if row else 0.0


# ─────────────────────────── Endpoints ───────────────────────────────────────

@router.get("/summary")
async def portfolio_summary():
    """
    Résumé global : cash_balance, valeur des positions, total.
    """
    from app.data_collection.data_service import DataService

    async with get_db_session() as db:
        cash_balance = await _get_cash_balance(db)
        positions = await db.fetch(
            """
            SELECT pp.*, t.name AS ticker_name, th.one_liner AS thesis_one_liner
            FROM portfolio_positions pp
            LEFT JOIN tickers t ON t.id = pp.ticker_id
            LEFT JOIN theses th ON th.id = pp.thesis_id
            WHERE pp.status = 'open'
            """,
        )

    ds = DataService()
    positions_value = 0.0
    positions_detail = []

    for pos in positions:
        ticker_id = pos["ticker_id"]
        current_price = None
        try:
            m1 = await ds.get_m1(ticker_id, settings.FMP_API_KEY)
            current_price = m1.get("price")
        except Exception:
            pass

        purchase_price = float(pos["purchase_price"])
        shares = float(pos["shares"])
        market_value = (float(current_price) * shares) if current_price else (purchase_price * shares)
        positions_value += market_value

        perf_pct = None
        if current_price:
            perf_pct = round((float(current_price) / purchase_price - 1) * 100, 2)

        positions_detail.append({
            **_serialize(pos),
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "perf_pct": perf_pct,
        })

    total = cash_balance + positions_value

    return {
        "cash_balance": round(cash_balance, 2),
        "positions_value": round(positions_value, 2),
        "total": round(total, 2),
        "positions": positions_detail,
    }


@router.get("/positions")
async def list_positions():
    """Liste les positions ouvertes avec prix actuel et perf."""
    from app.data_collection.data_service import DataService
    from datetime import datetime

    async with get_db_session() as db:
        rows = await db.fetch(
            """
            SELECT pp.*, t.name AS ticker_name, t.sector, th.status AS thesis_status,
                   th.one_liner AS thesis_one_liner
            FROM portfolio_positions pp
            LEFT JOIN tickers t ON t.id = pp.ticker_id
            LEFT JOIN theses th ON th.id = pp.thesis_id
            WHERE pp.status = 'open'
            ORDER BY pp.created_at DESC
            """
        )

    ds = DataService()
    result = []

    for pos in rows:
        ticker_id = pos["ticker_id"]
        current_price = None
        try:
            m1 = await ds.get_m1(ticker_id, settings.FMP_API_KEY)
            current_price = m1.get("price")
        except Exception:
            pass

        purchase_price = float(pos["purchase_price"])
        shares = float(pos["shares"])
        market_value = (float(current_price) * shares) if current_price else None

        perf_pct = None
        perf_annualized = None
        if current_price:
            perf_pct = round((float(current_price) / purchase_price - 1) * 100, 2)
            # Perf annualisée (approximation simple)
            if pos["purchase_date"]:
                days = (date.today() - pos["purchase_date"]).days
                if days > 0:
                    years = days / 365.25
                    perf_annualized = round(
                        ((float(current_price) / purchase_price) ** (1 / years) - 1) * 100, 2
                    )

        result.append({
            **_serialize(pos),
            "current_price": current_price,
            "market_value": round(market_value, 2) if market_value else None,
            "perf_pct": perf_pct,
            "perf_annualized": perf_annualized,
        })

    return result


@router.post("/cash", status_code=201)
async def add_cash_movement(data: CashMovementCreate):
    if data.type not in ("deposit", "withdrawal"):
        raise HTTPException(400, "type doit être 'deposit' ou 'withdrawal'")
    if data.amount <= 0:
        raise HTTPException(400, "amount doit être positif")

    async with get_db_session() as db:
        row = await db.fetchrow(
            """
            INSERT INTO cash_movements (type, amount, label)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            data.type, data.amount, data.label,
        )
    return _serialize(row)


@router.patch("/positions/{position_id}")
async def close_position(position_id: int, data: PositionUpdate):
    """Clôture une position (status='closed') et enregistre le mouvement cash."""
    if data.status != "closed":
        raise HTTPException(400, "status doit être 'closed'")

    sell_date_obj = None
    if data.sell_date:
        sell_date_obj = date.fromisoformat(data.sell_date)

    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM portfolio_positions WHERE id=$1 AND status='open'", position_id
        )
        if not pos:
            raise HTTPException(404, f"Position #{position_id} introuvable ou déjà clôturée")

        row = await db.fetchrow(
            """
            UPDATE portfolio_positions
            SET status='closed', sell_price=$1, sell_date=$2, updated_at=NOW()
            WHERE id=$3
            RETURNING *
            """,
            data.sell_price, sell_date_obj, position_id,
        )

        if data.sell_price:
            total_proceeds = float(pos["shares"]) * data.sell_price
            await db.execute(
                """
                INSERT INTO cash_movements (type, amount, label, ticker_id)
                VALUES ('sell', $1, $2, $3)
                """,
                total_proceeds,
                f"Vente {pos['ticker_id']} — {pos['shares']} titres @ {data.sell_price}",
                pos["ticker_id"],
            )

    return _serialize(row)


@router.post("/positions/{position_id}/reduce")
async def reduce_position(position_id: int, data: PositionReduce):
    """Réduit une position d'un pourcentage donné et enregistre le mouvement cash."""
    if not (0 < data.reduction_pct <= 100):
        raise HTTPException(400, "reduction_pct doit être entre 0 et 100")

    sell_date_obj = None
    if data.sell_date:
        sell_date_obj = date.fromisoformat(data.sell_date)

    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM portfolio_positions WHERE id=$1 AND status='open'", position_id
        )
        if not pos:
            raise HTTPException(404, f"Position #{position_id} introuvable ou déjà clôturée")

        current_shares = float(pos["shares"])
        shares_to_sell = round(current_shares * data.reduction_pct / 100, 6)
        remaining_shares = round(current_shares - shares_to_sell, 6)

        if remaining_shares <= 0:
            new_status = "closed"
        else:
            new_status = "open"

        row = await db.fetchrow(
            """
            UPDATE portfolio_positions
            SET shares=$1, status=$2, sell_price=$3, sell_date=$4, updated_at=NOW()
            WHERE id=$5
            RETURNING *
            """,
            remaining_shares, new_status, data.sell_price, sell_date_obj, position_id,
        )

        if data.sell_price:
            proceeds = shares_to_sell * data.sell_price
            await db.execute(
                """
                INSERT INTO cash_movements (type, amount, label, ticker_id)
                VALUES ('sell', $1, $2, $3)
                """,
                proceeds,
                f"Vente partielle {pos['ticker_id']} — {shares_to_sell} titres ({data.reduction_pct}%) @ {data.sell_price}",
                pos["ticker_id"],
            )

    return _serialize(row)


@router.get("/pending-allocation")
async def pending_allocation():
    """Thèses actives ou draft sans position ouverte allouée."""
    async with get_db_session() as db:
        rows = await db.fetch(
            """
            SELECT th.id, th.ticker_id, th.status, th.one_liner, th.thesis_json,
                   th.created_at, th.updated_at,
                   t.name AS ticker_name, t.sector
            FROM theses th
            LEFT JOIN tickers t ON t.id = th.ticker_id
            LEFT JOIN portfolio_positions pp ON pp.thesis_id = th.id AND pp.status = 'open'
            WHERE th.status IN ('draft', 'active')
              AND pp.id IS NULL
            ORDER BY th.updated_at DESC
            """
        )
    return [_serialize(r) for r in rows]


@router.get("/cash/history")
async def cash_history(limit: int = 10):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM cash_movements ORDER BY created_at DESC LIMIT $1",
            limit,
        )
    return [_serialize(r) for r in rows]
