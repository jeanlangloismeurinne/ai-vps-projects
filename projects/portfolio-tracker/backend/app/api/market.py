import logging
from datetime import datetime, timedelta
from fastapi import APIRouter
from app.db.database import get_db_session
from app.config import settings

router = APIRouter(prefix="/market", tags=["market"])
logger = logging.getLogger(__name__)


@router.get("/temperature")
async def get_temperature():
    """Retourne le dernier enregistrement market_indicators (refresh si > 24h)."""
    from app.data_collection.m4_macro import get_market_temperature

    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM market_indicators ORDER BY fetched_at DESC LIMIT 1"
        )

    if row:
        age = datetime.utcnow() - row["fetched_at"].replace(tzinfo=None)
        if age < timedelta(hours=24):
            return _serialize(row)

    # Refresh
    try:
        data = await get_market_temperature(settings.FRED_API_KEY)
        async with get_db_session() as db:
            row = await db.fetchrow("""
                INSERT INTO market_indicators
                    (buffett_ratio, buffett_trend, cape_ratio, cape_trend,
                     temperature, cash_target_pct, raw_data_json)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                RETURNING *
            """,
                data.get("buffett_ratio_pct"),
                data.get("buffett_trend"),
                data.get("cape_ratio"),
                data.get("cape_trend"),
                data.get("temperature"),
                data.get("cash_target_pct"),
                data.get("raw_data"),
            )
        return _serialize(row)
    except Exception as e:
        logger.error(f"Market temperature error: {e}")
        return {"temperature": "neutral", "cash_target_pct": 15.0, "error": str(e)}


@router.get("/temperature/history")
async def get_temperature_history(limit: int = 52):
    """Historique des enregistrements pour les graphiques (52 semaines max)."""
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM market_indicators ORDER BY fetched_at DESC LIMIT $1", limit
        )
    return [_serialize(r) for r in rows]


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
