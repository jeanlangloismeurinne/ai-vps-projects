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


class PositionEdit(BaseModel):
    purchase_price_eur: Optional[float] = None  # prix saisi en € — converti en devise native
    shares: Optional[float] = None
    purchase_date: Optional[str] = None  # ISO date


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


def compute_private_irr(position: dict, private_profile: dict):
    """
    Calcule l'IRR actuel et projeté pour une position private equity.

    Retourne (irr_current_pct, irr_projected_pct) — valeurs en % arrondies à 2 décimales,
    ou None si données insuffisantes.
    """
    total_invested = float(position.get("shares", 0) or 0) * float(position.get("purchase_price", 0) or 0)
    current_ownership = float(
        position.get("current_ownership_pct") or position.get("ownership_pct_at_entry") or 0
    )

    if not current_ownership or not private_profile.get("last_valuation_m") or not total_invested:
        return None, None

    # IRR actuel (basé sur la dernière valorisation connue)
    current_value = float(private_profile["last_valuation_m"]) * current_ownership / 100
    purchase_date = position.get("purchase_date")
    if isinstance(purchase_date, str):
        from datetime import date as _date
        purchase_date = _date.fromisoformat(purchase_date)

    if not purchase_date:
        return None, None

    years_held = (date.today() - purchase_date).days / 365.25
    irr_current = None
    if total_invested > 0:
        try:
            irr_current = round(
                ((current_value / total_invested) ** (1 / max(years_held, 0.01)) - 1) * 100, 2
            )
        except Exception:
            pass

    # IRR projeté (basé sur la valorisation au prochain événement)
    irr_projected = None
    if private_profile.get("projected_valuation_next_event_m") and private_profile.get("next_event_date"):
        projected_value = float(private_profile["projected_valuation_next_event_m"]) * current_ownership / 100
        next_event = private_profile["next_event_date"]
        if isinstance(next_event, str):
            from datetime import date as _date
            next_event = _date.fromisoformat(next_event)
        years_to_event = (next_event - date.today()).days / 365.25
        total_years = years_held + max(years_to_event, 0.01)
        if total_invested > 0:
            try:
                irr_projected = round(
                    ((projected_value / total_invested) ** (1 / total_years) - 1) * 100, 2
                )
            except Exception:
                pass

    return irr_current, irr_projected


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
            SELECT pp.*, t.name AS ticker_name, t.company_type, th.one_liner AS thesis_one_liner
            FROM portfolio_positions pp
            LEFT JOIN tickers t ON t.id = pp.ticker_id
            LEFT JOIN theses th ON th.id = pp.thesis_id
            WHERE pp.status = 'open'
            """,
        )
        # Profils private pour le calcul de valorisation
        private_ticker_ids = [r["ticker_id"] for r in positions if r["company_type"] == "private"]
        private_profiles_map = {}
        if private_ticker_ids:
            pcp_rows = await db.fetch(
                "SELECT * FROM private_company_profiles WHERE ticker_id = ANY($1::text[])",
                private_ticker_ids,
            )
            for pcp in pcp_rows:
                private_profiles_map[pcp["ticker_id"]] = _serialize(pcp)

    ds = DataService()
    positions_value = 0.0
    positions_detail = []

    for pos in positions:
        ticker_id = pos["ticker_id"]
        company_type = pos["company_type"] or "public"
        pos_dict = _serialize(pos)

        if company_type == "private":
            # Valorisation basée sur last_valuation_m × ownership_pct
            private_profile = private_profiles_map.get(ticker_id, {})
            ownership = float(pos["current_ownership_pct"] or pos["ownership_pct_at_entry"] or 0)
            last_val = private_profile.get("last_valuation_m")
            if last_val and ownership:
                market_value = float(last_val) * ownership / 100 * 1_000_000  # M€ → €
            else:
                market_value = float(pos["purchase_price"]) * float(pos["shares"])
            positions_value += market_value
            positions_detail.append({
                **pos_dict,
                "current_price": None,
                "market_value": round(market_value, 2),
                "perf_pct": None,
            })
            continue

        current_price = None
        try:
            m1 = await ds.get_m1(ticker_id, settings.FMP_API_KEY)
            current_price = (m1.get("price") or {}).get("current_price")
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
            **pos_dict,
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
            SELECT pp.*, t.name AS ticker_name, t.sector, t.company_type,
                   th.status AS thesis_status,
                   th.one_liner AS thesis_one_liner
            FROM portfolio_positions pp
            LEFT JOIN tickers t ON t.id = pp.ticker_id
            LEFT JOIN theses th ON th.id = pp.thesis_id
            WHERE pp.status = 'open'
            ORDER BY pp.created_at DESC
            """
        )
        # Récupère tous les profils private en une seule requête
        private_ticker_ids = [r["ticker_id"] for r in rows if r["company_type"] == "private"]
        private_profiles_map = {}
        if private_ticker_ids:
            pcp_rows = await db.fetch(
                "SELECT * FROM private_company_profiles WHERE ticker_id = ANY($1::text[])",
                private_ticker_ids,
            )
            for pcp in pcp_rows:
                private_profiles_map[pcp["ticker_id"]] = _serialize(pcp)

    ds = DataService()
    result = []

    for pos in rows:
        ticker_id = pos["ticker_id"]
        company_type = pos["company_type"] or "public"

        pos_dict = _serialize(pos)

        if company_type == "private":
            # Société non cotée : pas de prix de marché, calcul IRR
            private_profile = private_profiles_map.get(ticker_id, {})
            irr_current, irr_projected = compute_private_irr(pos_dict, private_profile)
            result.append({
                **pos_dict,
                "current_price": None,
                "currency": "EUR",
                "market_value": None,
                "perf_pct": None,
                "perf_annualized": None,
                "irr_current_pct": irr_current,
                "irr_projected_pct": irr_projected,
                "last_valuation_m": private_profile.get("last_valuation_m"),
                "current_ownership_pct": pos_dict.get("current_ownership_pct") or pos_dict.get("ownership_pct_at_entry"),
                "next_event_date": private_profile.get("next_event_date"),
                "next_event_type": private_profile.get("next_event_type"),
            })
            continue

        current_price = None
        ticker_currency = None
        try:
            m1 = await ds.get_m1(ticker_id, settings.FMP_API_KEY)
            price_data = m1.get("price") or {}
            current_price = price_data.get("current_price")
            ticker_currency = price_data.get("currency", "EUR") or "EUR"
        except Exception:
            pass

        stored_price = float(pos["purchase_price"])
        stored_currency = pos.get("purchase_currency") or "EUR"
        shares = float(pos["shares"])

        # Convertit le prix d'achat dans la devise native si nécessaire
        purchase_price_native = stored_price
        if ticker_currency and stored_currency != ticker_currency:
            try:
                from app.api.thesis_v2 import _get_fx_rate
                purchase_date_str = pos["purchase_date"].isoformat() if pos["purchase_date"] else date.today().isoformat()
                fx = await _get_fx_rate(stored_currency, ticker_currency, purchase_date_str)
                purchase_price_native = round(stored_price * fx, 4)
            except Exception as e:
                logger.warning(f"FX conversion {stored_currency}→{ticker_currency} pour {ticker_id}: {e}")

        market_value = (float(current_price) * shares) if current_price else None

        perf_pct = None
        perf_annualized = None
        if current_price and purchase_price_native:
            perf_pct = round((float(current_price) / purchase_price_native - 1) * 100, 2)
            if pos["purchase_date"]:
                days = (date.today() - pos["purchase_date"]).days
                if days > 0:
                    years = days / 365.25
                    perf_annualized = round(
                        ((float(current_price) / purchase_price_native) ** (1 / years) - 1) * 100, 2
                    )

        result.append({
            **pos_dict,
            "purchase_price": purchase_price_native,
            "purchase_currency": ticker_currency or stored_currency,
            "current_price": current_price,
            "currency": ticker_currency,
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


@router.patch("/positions/{position_id}/edit")
async def edit_position(position_id: int, data: PositionEdit):
    """Modifie le prix d'achat (saisi en €, converti en devise native) et/ou le volume."""
    if data.purchase_price_eur is None and data.shares is None and data.purchase_date is None:
        raise HTTPException(400, "Aucun champ à mettre à jour")

    async with get_db_session() as db:
        pos = await db.fetchrow(
            "SELECT * FROM portfolio_positions WHERE id=$1 AND status='open'", position_id
        )
        if not pos:
            raise HTTPException(404, f"Position #{position_id} introuvable ou déjà clôturée")

    set_parts = ["updated_at=NOW()"]
    values = [position_id]
    i = 2

    if data.purchase_price_eur is not None:
        # Convertit le prix EUR vers la devise native du ticker
        ticker_id = pos["ticker_id"]
        purchase_date_str = (
            data.purchase_date or
            (pos["purchase_date"].isoformat() if pos["purchase_date"] else date.today().isoformat())
        )
        ticker_currency = "EUR"
        try:
            from app.data_collection.data_service import DataService
            m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
            ticker_currency = (m1.get("price") or {}).get("currency", "EUR") or "EUR"
        except Exception:
            pass

        price_native = data.purchase_price_eur
        if ticker_currency != "EUR":
            try:
                from app.api.thesis_v2 import _get_fx_rate
                fx = await _get_fx_rate("EUR", ticker_currency, purchase_date_str)
                price_native = round(data.purchase_price_eur * fx, 4)
            except Exception as e:
                logger.warning(f"FX conversion {ticker_currency} pour edit position: {e}")

        set_parts.append(f"purchase_price=${i}")
        values.append(price_native)
        i += 1
        set_parts.append(f"purchase_currency=${i}")
        values.append(ticker_currency)
        i += 1

    if data.shares is not None:
        set_parts.append(f"shares=${i}")
        values.append(data.shares)
        i += 1
    if data.purchase_date is not None:
        set_parts.append(f"purchase_date=${i}")
        values.append(date.fromisoformat(data.purchase_date))
        i += 1

    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE portfolio_positions SET {', '.join(set_parts)} WHERE id=$1 RETURNING *",
            *values,
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
