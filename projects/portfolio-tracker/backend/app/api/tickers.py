"""
Tickers V1 — gestion des tickers, alertes prix, price history, métriques.
"""
import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import get_db_session
from app.config import settings

router = APIRouter(prefix="/tickers", tags=["tickers-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class TickerCreate(BaseModel):
    id: Optional[str] = None  # "CAP.PA", "TSLA" — auto-généré PRIV-XXXXXXXX si absent et company_type=private
    name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    reporting_currency: Optional[str] = None  # EUR, USD, GBP… — déduit du suffixe si absent
    company_type: str = "public"
    # Private-specific optional fields
    stage: Optional[str] = None
    country: Optional[str] = None
    last_valuation_m: Optional[float] = None
    last_valuation_date: Optional[str] = None
    last_valuation_basis: Optional[str] = None
    arr_or_revenue_m: Optional[float] = None
    ebitda_m: Optional[float] = None
    notable_investors: Optional[List[str]] = None


class PrivateProfileUpdate(BaseModel):
    stage: Optional[str] = None
    country: Optional[str] = None
    last_valuation_m: Optional[float] = None
    last_valuation_date: Optional[str] = None
    last_valuation_basis: Optional[str] = None
    arr_or_revenue_m: Optional[float] = None
    ebitda_m: Optional[float] = None
    key_metrics_json: Optional[dict] = None
    notable_investors: Optional[List[str]] = None
    projected_valuation_next_event_m: Optional[float] = None
    next_event_date: Optional[str] = None
    next_event_type: Optional[str] = None


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
        query = """
            SELECT t.*,
                   pcp.stage, pcp.country,
                   pcp.last_valuation_m, pcp.last_valuation_date
            FROM tickers t
            LEFT JOIN private_company_profiles pcp ON pcp.ticker_id = t.id
        """
        if status:
            rows = await db.fetch(query + " WHERE t.status = $1 ORDER BY t.added_at DESC", status)
        else:
            rows = await db.fetch(query + " ORDER BY t.added_at DESC")
    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
async def create_ticker(data: TickerCreate):
    import random
    import string

    # Auto-génère un PRIV-XXXXXXXX si id absent (private companies seulement)
    if not data.id:
        if data.company_type != "private":
            raise HTTPException(400, "id requis pour les sociétés cotées")
        ticker_id = "PRIV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    else:
        ticker_id = data.id

    async with get_db_session() as db:
        existing = await db.fetchrow("SELECT id FROM tickers WHERE id = $1", ticker_id)
        if existing:
            raise HTTPException(400, f"Ticker '{ticker_id}' existe déjà")
        # Private companies default to EUR, public tickers derive from suffix
        if data.company_type == "private":
            currency = data.reporting_currency or "EUR"
        else:
            currency = data.reporting_currency or _derive_currency(ticker_id)
        row = await db.fetchrow(
            """
            INSERT INTO tickers (id, name, exchange, sector, reporting_currency, company_type)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            ticker_id, data.name, data.exchange, data.sector, currency, data.company_type,
        )
        # Si private, créer le profil dans private_company_profiles
        if data.company_type == "private":
            last_val_date = None
            if data.last_valuation_date:
                from datetime import date as _date
                try:
                    last_val_date = _date.fromisoformat(data.last_valuation_date)
                except ValueError:
                    pass
            await db.execute(
                """
                INSERT INTO private_company_profiles
                    (ticker_id, stage, country, last_valuation_m, last_valuation_date,
                     last_valuation_basis, arr_or_revenue_m, ebitda_m, notable_investors)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                ticker_id,
                data.stage,
                data.country or "FR",
                data.last_valuation_m,
                last_val_date,
                data.last_valuation_basis,
                data.arr_or_revenue_m,
                data.ebitda_m,
                data.notable_investors or [],
            )
    return _serialize(row)


@router.get("/search")
async def search_tickers(q: str = Query(..., min_length=2)):
    """Recherche de tickers par nom d'entreprise via yfinance."""
    try:
        import yfinance as yf
        search = yf.Search(q.strip(), max_results=8, news_count=0)
        results = []
        for item in (search.quotes or []):
            symbol = item.get("symbol", "")
            if not symbol:
                continue
            if item.get("quoteType") not in ("EQUITY", "ETF"):
                continue
            results.append({
                "symbol": symbol,
                "name": item.get("longname") or item.get("shortname") or symbol,
                "exchange": item.get("exchDisp") or item.get("exchange", ""),
                "sector": item.get("sectorDisp") or item.get("sector", ""),
                "type": item.get("quoteType", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"Ticker search error for '{q}': {e}")
        raise HTTPException(500, f"Erreur de recherche : {str(e)}")


@router.get("/{ticker_id}")
async def get_ticker(ticker_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow("SELECT * FROM tickers WHERE id = $1", ticker_id)
        if not row:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")
        # Fetch private profile if applicable
        private_profile = None
        if row["company_type"] == "private":
            private_profile = await db.fetchrow(
                "SELECT * FROM private_company_profiles WHERE ticker_id = $1", ticker_id
            )

    ticker_dict = _serialize(row)

    if private_profile:
        ticker_dict["private_profile"] = _serialize(private_profile)
        # Also expose key fields at top level for convenience
        ticker_dict["current_price"] = None
        ticker_dict["currency"] = None
        ticker_dict["market_cap"] = None
    else:
        # Ajoute le prix actuel via DataService (best-effort)
        try:
            from app.data_collection.data_service import DataService
            m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
            price_data = m1.get("price") or {}
            ticker_dict["current_price"] = price_data.get("current_price")
            ticker_dict["currency"] = price_data.get("currency")
            ticker_dict["market_cap"] = price_data.get("market_cap")
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


@router.patch("/{ticker_id}/private-profile")
async def update_private_profile(ticker_id: str, data: PrivateProfileUpdate):
    """Met à jour le profil d'une société non cotée (upsert)."""
    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id, company_type FROM tickers WHERE id = $1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")
        if t["company_type"] != "private":
            raise HTTPException(400, f"Ticker '{ticker_id}' n'est pas une société privée")

        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(400, "Aucun champ à mettre à jour")

        # Convert date strings to date objects
        if "last_valuation_date" in updates and isinstance(updates["last_valuation_date"], str):
            from datetime import date as _date
            try:
                updates["last_valuation_date"] = _date.fromisoformat(updates["last_valuation_date"])
            except ValueError:
                updates.pop("last_valuation_date")
        if "next_event_date" in updates and isinstance(updates["next_event_date"], str):
            from datetime import date as _date
            try:
                updates["next_event_date"] = _date.fromisoformat(updates["next_event_date"])
            except ValueError:
                updates.pop("next_event_date")

        # Upsert into private_company_profiles
        existing = await db.fetchrow(
            "SELECT ticker_id FROM private_company_profiles WHERE ticker_id = $1", ticker_id
        )
        if not existing:
            await db.execute(
                "INSERT INTO private_company_profiles (ticker_id) VALUES ($1)", ticker_id
            )

        set_parts = ["updated_at=NOW()"]
        values = [ticker_id]
        for i, (k, v) in enumerate(updates.items(), start=2):
            set_parts.append(f"{k}=${i}")
            values.append(v)

        row = await db.fetchrow(
            f"UPDATE private_company_profiles SET {', '.join(set_parts)} WHERE ticker_id=$1 RETURNING *",
            *values,
        )
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

    price_data = m1.get("price") or {}
    valuation = m1.get("valuation") or {}
    return {
        "ticker_id": ticker_id,
        "current_price": price_data.get("current_price"),
        "currency": price_data.get("currency"),
        "price_change_1d_pct": price_data.get("1d_change_pct"),
        "pe_ntm": valuation.get("pe_ntm"),
        "fcf_yield": valuation.get("fcf_yield_pct"),
        "ev_ebitda": valuation.get("ev_ebitda"),
        "net_margin": valuation.get("net_margin"),
        "roe": valuation.get("roe"),
        "debt_to_equity": valuation.get("debt_to_equity"),
        "market_cap": price_data.get("market_cap"),
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
