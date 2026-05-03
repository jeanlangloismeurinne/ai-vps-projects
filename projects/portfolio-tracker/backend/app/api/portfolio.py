from fastapi import APIRouter
from app.portfolio.portfolio_view import PortfolioView
from app.db.database import get_db_session

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio():
    return await PortfolioView().generate_snapshot()


@router.get("/snapshots")
async def list_snapshots(limit: int = 10):
    async with get_db_session() as db:
        rows = await db.fetch("""
            SELECT id, snapshot_date, portfolio_metrics_json, concentration_flags_json
            FROM portfolio_snapshots
            ORDER BY snapshot_date DESC LIMIT $1
        """, limit)
    return [_serialize(row) for row in rows]


def _serialize(row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d
