"""
Tickers V1 — gestion des tickers, alertes prix, price history, métriques.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import get_db_session
from app.config import settings

router = APIRouter(prefix="/tickers", tags=["tickers-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class TickerCreate(BaseModel):
    id: str          # "CAP.PA", "TSLA"
    name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    reporting_currency: Optional[str] = None  # EUR, USD, GBP… — déduit du suffixe si absent


class TickerStatusUpdate(BaseModel):
    status: Optional[str] = None      # 'watchlist' | 'portfolio' | 'archived'
    reporting_currency: Optional[str] = None


class AlertCreate(BaseModel):
    price: float
    direction: str   # 'above' | 'below'
    label: Optional[str] = None


class AlertUpdate(BaseModel):
    active: Optional[bool] = None
    label: Optional[str] = None


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# ─────────────────────────── Helpers ─────────────────────────────────────────

_SUFFIX_CURRENCY = {
    ".PA": "EUR", ".AS": "EUR", ".MI": "EUR", ".DE": "EUR",
    ".BR": "EUR", ".LS": "EUR", ".MC": "EUR", ".AT": "EUR",
    ".CO": "EUR", ".HE": "EUR", ".OL": "EUR", ".ST": "EUR",
    ".L":  "GBP",
    ".T":  "JPY",
    ".HK": "HKD",
    ".TO": "CAD", ".V": "CAD",
    ".AX": "AUD",
    ".SS": "CNY", ".SZ": "CNY",
    ".SA": "BRL",
}

def _derive_currency(ticker_id: str) -> str:
    for suffix, currency in _SUFFIX_CURRENCY.items():
        if ticker_id.endswith(suffix):
            return currency
    return "USD"


# ─────────────────────────── Tickers CRUD ────────────────────────────────────

@router.get("")
async def list_tickers(status: Optional[str] = Query(None)):
    async with get_db_session() as db:
        if status:
            rows = await db.fetch(
                "SELECT * FROM tickers WHERE status = $1 ORDER BY added_at DESC", status
            )
        else:
            rows = await db.fetch("SELECT * FROM tickers ORDER BY added_at DESC")
    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
async def create_ticker(data: TickerCreate):
    async with get_db_session() as db:
        existing = await db.fetchrow("SELECT id FROM tickers WHERE id = $1", data.id)
        if existing:
            raise HTTPException(400, f"Ticker '{data.id}' existe déjà")
        currency = data.reporting_currency or _derive_currency(data.id)
        row = await db.fetchrow(
            """
            INSERT INTO tickers (id, name, exchange, sector, reporting_currency)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            data.id, data.name, data.exchange, data.sector, currency,
        )
    return _serialize(row)


@router.get("/{ticker_id}")
async def get_ticker(ticker_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow("SELECT * FROM tickers WHERE id = $1", ticker_id)
    if not row:
        raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")

    ticker_dict = _serialize(row)

    # Ajoute le prix actuel via DataService (best-effort)
    try:
        from app.data_collection.data_service import DataService
        m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
        ticker_dict["current_price"] = m1.get("price")
        ticker_dict["currency"] = m1.get("currency")
        ticker_dict["market_cap"] = m1.get("market_cap")
    except Exception as e:
        logger.warning(f"Impossible de récupérer le prix pour {ticker_id}: {e}")
        ticker_dict["current_price"] = None

    return ticker_dict


@router.patch("/{ticker_id}")
async def update_ticker_status(ticker_id: str, data: TickerStatusUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    set_parts = ["updated_at=NOW()"]
    values = [ticker_id]
    for i, (k, v) in enumerate(updates.items(), start=2):
        set_parts.append(f"{k}=${i}")
        values.append(v)
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE tickers SET {', '.join(set_parts)} WHERE id=$1 RETURNING *",
            *values,
        )
    if not row:
        raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")
    return _serialize(row)


@router.delete("/{ticker_id}", status_code=204)
async def archive_ticker(ticker_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "UPDATE tickers SET status='archived', updated_at=NOW() WHERE id=$1 RETURNING id",
            ticker_id,
        )
    if not row:
        raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")


# ─────────────────────────── Price History ───────────────────────────────────

@router.get("/{ticker_id}/price-history")
async def get_price_history(
    ticker_id: str,
    period: str = Query("1y", description="1y / 5y / max"),
):
    import yfinance as yf

    loop = asyncio.get_event_loop()

    def _fetch():
        ticker = yf.Ticker(ticker_id)
        hist = ticker.history(period=period.lower())
        if hist.empty:
            return []
        hist = hist.reset_index()
        records = []
        for _, row in hist.iterrows():
            records.append({
                "date": row["Date"].date().isoformat() if hasattr(row["Date"], "date") else str(row["Date"])[:10],
                "open": float(row["Open"]) if row["Open"] else None,
                "high": float(row["High"]) if row["High"] else None,
                "low": float(row["Low"]) if row["Low"] else None,
                "close": float(row["Close"]) if row["Close"] else None,
                "volume": int(row["Volume"]) if row["Volume"] else None,
            })
        return records

    try:
        records = await loop.run_in_executor(None, _fetch)
    except Exception as e:
        raise HTTPException(502, f"Erreur yfinance: {e}")

    return {"ticker_id": ticker_id, "period": period, "data": records}


# ─────────────────────────── Metrics ─────────────────────────────────────────

@router.get("/{ticker_id}/metrics")
async def get_ticker_metrics(ticker_id: str):
    try:
        from app.data_collection.data_service import DataService
        m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
    except Exception as e:
        raise HTTPException(502, f"Erreur DataService: {e}")

    return {
        "ticker_id": ticker_id,
        "price": m1.get("price"),
        "currency": m1.get("currency"),
        "pe_ntm": m1.get("pe_ntm") or m1.get("forward_pe"),
        "fcf_yield": m1.get("fcf_yield"),
        "ev_ebitda": m1.get("ev_ebitda"),
        "revenue_growth_yoy": m1.get("revenue_growth_yoy"),
        "net_margin": m1.get("net_margin"),
        "roe": m1.get("roe"),
        "debt_to_equity": m1.get("debt_to_equity"),
        "market_cap": m1.get("market_cap"),
        "raw": m1,
    }


# ─────────────────────────── Price Alerts ────────────────────────────────────

@router.get("/{ticker_id}/alerts")
async def list_alerts(ticker_id: str):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM price_alerts WHERE ticker_id=$1 AND active=TRUE ORDER BY created_at DESC",
            ticker_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/{ticker_id}/alerts", status_code=201)
async def create_alert(ticker_id: str, data: AlertCreate):
    if data.direction not in ("above", "below"):
        raise HTTPException(400, "direction doit être 'above' ou 'below'")
    async with get_db_session() as db:
        # Vérifie que le ticker existe
        t = await db.fetchrow("SELECT id FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")
        row = await db.fetchrow(
            """
            INSERT INTO price_alerts (ticker_id, price, direction, label)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            ticker_id, data.price, data.direction, data.label,
        )
    return _serialize(row)


@router.delete("/{ticker_id}/alerts/{alert_id}", status_code=204)
async def delete_alert(ticker_id: str, alert_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "DELETE FROM price_alerts WHERE id=$1 AND ticker_id=$2 RETURNING id",
            alert_id, ticker_id,
        )
    if not row:
        raise HTTPException(404, "Alerte introuvable")


@router.patch("/{ticker_id}/alerts/{alert_id}")
async def update_alert(ticker_id: str, alert_id: int, data: AlertUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")
    set_clause = ", ".join(f"{k}=${i+3}" for i, k in enumerate(updates))
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE price_alerts SET {set_clause} WHERE id=$1 AND ticker_id=$2 RETURNING *",
            alert_id, ticker_id, *updates.values(),
        )
    if not row:
        raise HTTPException(404, "Alerte introuvable")
    return _serialize(row)
