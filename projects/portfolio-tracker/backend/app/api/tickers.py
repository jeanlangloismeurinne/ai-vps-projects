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
    id: Optional[str] = None  # laissé vide → auto-généré PUB-XXXXXXXX (cotées) ou PRIV-XXXXXXXX (privées)
    name: str
    ticker_symbol: Optional[str] = None  # symbole yfinance ex. "CAP.PA" — peut être fourni plus tard
    exchange: Optional[str] = None
    sector: Optional[str] = None
    reporting_currency: Optional[str] = None  # EUR, USD, GBP… — déduit du suffixe du ticker_symbol si absent
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


class TickerUpdate(BaseModel):
    name: Optional[str] = None
    ticker_symbol: Optional[str] = None  # symbole yfinance — renseigné à l'étape d'opportunité
    exchange: Optional[str] = None
    sector: Optional[str] = None
    status: Optional[str] = None      # 'watchlist' | 'portfolio' | 'archived'
    reporting_currency: Optional[str] = None


# Alias pour compatibilité
TickerStatusUpdate = TickerUpdate


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

    if not data.id:
        prefix = "PRIV-" if data.company_type == "private" else "PUB-"
        ticker_id = prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    else:
        ticker_id = data.id

    # Le ticker_symbol est le symbole yfinance : si fourni, on l'utilise ; sinon on l'infère de l'id
    # (seulement si l'id n'est pas auto-généré, i.e. ressemble à un vrai symbole boursier)
    ticker_symbol = data.ticker_symbol
    if ticker_symbol is None and not ticker_id.startswith(("PUB-", "PRIV-")):
        ticker_symbol = ticker_id

    async with get_db_session() as db:
        existing = await db.fetchrow("SELECT id FROM tickers WHERE id = $1", ticker_id)
        if existing:
            raise HTTPException(400, f"Ticker '{ticker_id}' existe déjà")
        if data.company_type == "private":
            currency = data.reporting_currency or "EUR"
        else:
            # Dérive la devise du ticker_symbol s'il est connu, sinon EUR par défaut
            currency = data.reporting_currency or (
                _derive_currency(ticker_symbol) if ticker_symbol else "EUR"
            )
        row = await db.fetchrow(
            """
            INSERT INTO tickers (id, name, ticker_symbol, exchange, sector, reporting_currency, company_type)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            ticker_id, data.name, ticker_symbol, data.exchange, data.sector, currency, data.company_type,
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


@router.get("/fx-rate")
async def get_fx_rate(from_currency: str = Query(...), to_currency: str = Query(...)):
    """Taux de change live via yfinance (cours du jour)."""
    if from_currency == to_currency:
        return {"from": from_currency, "to": to_currency, "rate": 1.0}
    try:
        import asyncio
        import yfinance as yf
        from datetime import date as _date, timedelta

        fx_ticker = f"{from_currency}{to_currency}=X"

        def _fetch():
            today = _date.today()
            for offset in range(7):
                start = today - timedelta(days=offset)
                end = start + timedelta(days=2)
                hist = yf.Ticker(fx_ticker).history(start=start.isoformat(), end=end.isoformat())
                if not hist.empty:
                    return float(hist["Close"].iloc[-1])
            raise ValueError(f"Taux {fx_ticker} introuvable")

        loop = asyncio.get_event_loop()
        rate = await loop.run_in_executor(None, _fetch)
        return {"from": from_currency, "to": to_currency, "rate": round(rate, 6)}
    except Exception as e:
        raise HTTPException(502, f"Taux de change introuvable : {e}")


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
    symbol_for_data = row.get("ticker_symbol") or None

    if private_profile:
        ticker_dict["private_profile"] = _serialize(private_profile)
        ticker_dict["current_price"] = None
        ticker_dict["currency"] = None
        ticker_dict["market_cap"] = None
    elif symbol_for_data:
        # Ajoute le prix actuel via DataService (best-effort)
        try:
            from app.data_collection.data_service import DataService
            m1 = await DataService().get_m1(symbol_for_data, settings.FMP_API_KEY)
            price_data = m1.get("price") or {}
            ticker_dict["current_price"] = price_data.get("current_price")
            ticker_dict["currency"] = price_data.get("currency")
            ticker_dict["market_cap"] = price_data.get("market_cap")
        except Exception as e:
            logger.warning(f"Impossible de récupérer le prix pour {symbol_for_data}: {e}")
            ticker_dict["current_price"] = None
    else:
        ticker_dict["current_price"] = None
        ticker_dict["currency"] = None
        ticker_dict["market_cap"] = None

    return ticker_dict


@router.patch("/{ticker_id}")
async def update_ticker(ticker_id: str, data: TickerUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Aucun champ à mettre à jour")

    allowed = {"name", "ticker_symbol", "exchange", "sector", "status", "reporting_currency"}
    updates = {k: v for k, v in updates.items() if k in allowed}

    # Si ticker_symbol fourni et reporting_currency absent, dériver la devise
    if "ticker_symbol" in updates and "reporting_currency" not in updates:
        async with get_db_session() as db:
            row = await db.fetchrow("SELECT reporting_currency FROM tickers WHERE id=$1", ticker_id)
            if row and not row["reporting_currency"]:
                updates["reporting_currency"] = _derive_currency(updates["ticker_symbol"])

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

    # Résoudre le symbole yfinance depuis ticker_symbol si disponible
    async with get_db_session() as db:
        row = await db.fetchrow("SELECT ticker_symbol FROM tickers WHERE id=$1", ticker_id)
    yf_symbol = (row["ticker_symbol"] if row else None) or None
    if not yf_symbol:
        return {"ticker_id": ticker_id, "period": period, "data": []}

    loop = asyncio.get_event_loop()

    def _fetch():
        ticker = yf.Ticker(yf_symbol)
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
    async with get_db_session() as db:
        row = await db.fetchrow("SELECT ticker_symbol FROM tickers WHERE id=$1", ticker_id)
    yf_symbol = (row["ticker_symbol"] if row else None) or None
    if not yf_symbol:
        return {"ticker_id": ticker_id, "current_price": None, "currency": None}

    try:
        from app.data_collection.data_service import DataService
        m1 = await DataService().get_m1(yf_symbol, settings.FMP_API_KEY)
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
