import logging
from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import WatchlistCreate, WatchlistUpdate, WatchlistValidateThesis, WatchlistChatMessage
from app.config import settings

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = logging.getLogger(__name__)


# ── LECTURE ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_watchlist():
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM watchlist ORDER BY identified_date DESC"
        )
    return [_serialize(row) for row in rows]


@router.get("/alerts")
async def get_alerts():
    """Retourne les items avec alerte non acquittée."""
    async with get_db_session() as db:
        rows = await db.fetch("""
            SELECT * FROM watchlist
            WHERE alert_triggered_at IS NOT NULL AND alert_acknowledged = FALSE
            ORDER BY alert_triggered_at DESC
        """)
    return [_serialize(row) for row in rows]


@router.get("/{item_id}/readiness")
async def get_readiness(item_id: str):
    """Calcule le readiness score (0-100)."""
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", item_id)
        if not item:
            raise HTTPException(404, "Watchlist item not found")
        market_row = await db.fetchrow(
            "SELECT temperature FROM market_indicators ORDER BY fetched_at DESC LIMIT 1"
        )

    item_dict = dict(item)
    score, breakdown = _compute_readiness(item_dict, market_row)

    async with get_db_session() as db:
        await db.execute(
            "UPDATE watchlist SET readiness_score = $1 WHERE id = $2", score, item_id
        )

    return {"item_id": item_id, "readiness_score": score, "breakdown": breakdown}


@router.get("/{item_id}/full")
async def get_full(item_id: str):
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", item_id)
    if not item:
        raise HTTPException(404, "Watchlist item not found")
    return _serialize(item)


@router.get("/{item_id}/chat")
async def get_chat(item_id: str):
    from app.agents.thesis_chat import get_chat_history
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT dust_conversation_id FROM watchlist WHERE id = $1", item_id)
    if not item:
        raise HTTPException(404, "Watchlist item not found")
    if not item["dust_conversation_id"]:
        return {"turns": [], "conversation_id": None}
    turns = await get_chat_history(item["dust_conversation_id"])
    return {"turns": turns, "conversation_id": item["dust_conversation_id"]}


# ── ÉCRITURE ──────────────────────────────────────────────────────────────────

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


@router.post("/refresh-prices")
async def refresh_prices():
    """Fetch prix live pour tous les items status='watching', recalcule gap_to_entry."""
    from app.data_collection.m1_quantitative import collect_quantitative
    async with get_db_session() as db:
        items = await db.fetch("SELECT * FROM watchlist WHERE status = 'watching'")

    updated = 0
    for row in items:
        item = dict(row)
        try:
            m1 = collect_quantitative(item["ticker"], settings.FMP_API_KEY)
            current_price = m1.get("price", {}).get("current_price")
            if not current_price:
                continue

            entry_target = item.get("entry_price_target")
            gap = round((float(current_price) / float(entry_target) - 1) * 100, 2) if entry_target else None

            async with get_db_session() as db:
                await db.execute("""
                    UPDATE watchlist
                    SET current_price=$1, gap_to_entry=$2, last_checked=NOW()
                    WHERE id=$3
                """, current_price, gap, item["id"])
            updated += 1
        except Exception as e:
            logger.warning(f"Price refresh error for {item['ticker']}: {e}")

    return {"updated": updated}


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


@router.patch("/{item_id}/acknowledge-alert")
async def acknowledge_alert(item_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "UPDATE watchlist SET alert_acknowledged=TRUE WHERE id=$1 RETURNING id",
            item_id
        )
    if not row:
        raise HTTPException(404, "Watchlist item not found")
    return {"acknowledged": True}


@router.post("/{item_id}/chat")
async def post_chat(item_id: str, data: WatchlistChatMessage):
    from app.agents import thesis_chat
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", item_id)
        if not item:
            raise HTTPException(404, "Watchlist item not found")

        item_dict = dict(item)
        try:
            if item_dict.get("dust_conversation_id"):
                result = await thesis_chat.continue_chat(item_dict["dust_conversation_id"], data.message)
                result["conversation_id"] = item_dict["dust_conversation_id"]
            else:
                result = await thesis_chat.start_watchlist_chat(item_id, data.message, db)
        except ValueError as e:
            if "rate_limit" in str(e):
                raise HTTPException(503, "Agent temporairement indisponible, réessayez dans 30 secondes")
            if "dust_error" in str(e):
                from app.notifications.slack_notifier import SlackNotifier
                await SlackNotifier().send_error_alert(item_dict.get("ticker", item_id), f"Erreur agent Dust sur chat watchlist/{item_id}")
                raise HTTPException(502, "Erreur agent Dust")
            raise HTTPException(500, str(e))

    return result


@router.post("/{item_id}/validate-thesis")
async def validate_thesis(item_id: str, data: WatchlistValidateThesis):
    async with get_db_session() as db:
        item = await db.fetchrow("SELECT * FROM watchlist WHERE id = $1", item_id)
        if not item:
            raise HTTPException(404, "Watchlist item not found")

        item_dict = dict(item)
        validated_thesis = {
            "schema_json_draft": item_dict.get("schema_json_draft"),
            "scout_brief": item_dict.get("scout_brief"),
            "peer_snapshot_json": item_dict.get("peer_snapshot_json"),
            "entry_price_target": data.entry_price_target or item_dict.get("entry_price_target"),
            "conviction_signal": item_dict.get("conviction_signal"),
        }

        await db.execute("""
            UPDATE watchlist SET
                validated_thesis_json = $1,
                validated_at = NOW(),
                thesis_status = 'validated',
                entry_price_target = COALESCE($2, entry_price_target),
                trigger_alert_price = COALESCE($3, trigger_alert_price)
            WHERE id = $4
        """,
            validated_thesis,
            data.entry_price_target,
            data.trigger_alert_price,
            item_id,
        )

        updated = await db.fetchrow("SELECT validated_at FROM watchlist WHERE id = $1", item_id)

    return {
        "validated": True,
        "validated_at": updated["validated_at"].isoformat() if updated else None,
        "decision": data.decision,
        "open_promote_drawer": data.decision == "invest_now",
    }


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
            "UPDATE watchlist SET status='invested' WHERE id=$1", item_id
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


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _compute_readiness(item: dict, market_row=None) -> tuple:
    score = 0
    breakdown = {}

    # 40 pts : gap_to_entry
    gap = item.get("gap_to_entry")
    if gap is not None:
        gap_val = float(gap)
        if gap_val <= 2:
            gap_pts = 40
        elif gap_val <= 5:
            gap_pts = 30
        elif gap_val <= 10:
            gap_pts = 20
        else:
            gap_pts = 0
    else:
        gap_pts = 0
    score += gap_pts
    breakdown["gap_to_entry"] = {"pts": gap_pts, "gap_pct": gap}

    # 30 pts : cash_ready
    cash_pts = 30 if item.get("cash_ready") else 0
    score += cash_pts
    breakdown["cash_ready"] = {"pts": cash_pts}

    # 20 pts : scout_brief
    brief = item.get("scout_brief") or ""
    brief_pts = 20 if len(brief) > 100 else 0
    score += brief_pts
    breakdown["scout_brief"] = {"pts": brief_pts}

    # 10 pts : température marché
    temp = market_row["temperature"] if market_row else None
    temp_pts = 10 if temp in ("cold", "neutral") else 0
    score += temp_pts
    breakdown["market_temperature"] = {"pts": temp_pts, "temperature": temp}

    return score, breakdown


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
