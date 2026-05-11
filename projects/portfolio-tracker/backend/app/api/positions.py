import logging
from fastapi import APIRouter, HTTPException
from app.db.database import get_db_session
from app.db.models import PositionCreate, PositionUpdate, ThesisCreate, PeerCreate

router = APIRouter(prefix="/positions", tags=["positions"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_positions():
    async with get_db_session() as db:
        rows = await db.fetch("""
            SELECT p.*,
                r.recommendation, r.alert_level, r.review_date,
                t.thesis_one_liner,
                COUNT(h.id) FILTER (WHERE h.current_status = 'alert') as alert_count,
                COUNT(h.id) FILTER (WHERE h.current_status = 'invalidated') as invalidated_count
            FROM positions p
            LEFT JOIN LATERAL (
                SELECT recommendation, alert_level, review_date FROM reviews
                WHERE position_id = p.id ORDER BY review_date DESC LIMIT 1
            ) r ON TRUE
            LEFT JOIN theses t ON t.position_id = p.id AND t.is_current = TRUE
            LEFT JOIN hypotheses h ON h.position_id = p.id
            GROUP BY p.id, r.recommendation, r.alert_level, r.review_date, t.thesis_one_liner
            ORDER BY p.allocation_pct DESC NULLS LAST
        """)
    return [_serialize(row) for row in rows]


@router.post("", status_code=201)
async def create_position(data: PositionCreate):
    async with get_db_session() as db:
        existing = await db.fetchrow("SELECT id FROM positions WHERE ticker = $1", data.ticker)
        if existing:
            raise HTTPException(400, f"Position {data.ticker} already exists")
        row = await db.fetchrow("""
            INSERT INTO positions
                (ticker, company_name, sector_schema, exchange, entry_date,
                 entry_price, entry_price_currency, allocation_pct, quantity, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING *
        """,
            data.ticker, data.company_name, data.sector_schema, data.exchange,
            data.entry_date, data.entry_price, data.entry_price_currency,
            data.allocation_pct, data.quantity, data.status,
        )

        # Log cash operation si portfolio_settings existe
        try:
            from app.api.portfolio_settings import _log_position_cash
            await _log_position_cash(db, str(row["id"]), float(data.entry_price), data.quantity, "position_open")
        except Exception:
            pass

    return _serialize(row)


@router.get("/{position_id}")
async def get_position(position_id: str):
    from app.portfolio.portfolio_view import PortfolioView
    detail = await PortfolioView().get_position_detail(position_id)
    if not detail:
        raise HTTPException(404, "Position not found")
    return _serialize_detail(detail)


@router.patch("/{position_id}")
async def update_position(position_id: str, data: PositionUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    async with get_db_session() as db:
        row = await db.fetchrow(
            f"UPDATE positions SET {set_clause}, updated_at=NOW() WHERE id=$1 RETURNING *",
            position_id, *updates.values()
        )
    if not row:
        raise HTTPException(404, "Position not found")
    return _serialize(row)


@router.post("/{position_id}/thesis", status_code=201)
async def create_thesis(position_id: str, data: ThesisCreate):
    async with get_db_session() as db:
        pos = await db.fetchrow("SELECT id FROM positions WHERE id = $1", position_id)
        if not pos:
            raise HTTPException(404, "Position not found")

        await db.execute(
            "UPDATE theses SET is_current = FALSE WHERE position_id = $1 AND is_current = TRUE",
            position_id
        )

        version_row = await db.fetchrow(
            "SELECT COALESCE(MAX(version), 0) + 1 as next_version FROM theses WHERE position_id = $1",
            position_id
        )

        thesis = await db.fetchrow("""
            INSERT INTO theses
                (position_id, version, thesis_one_liner, bear_steel_man,
                 scenarios_json, price_thresholds_json, entry_context_json, is_current)
            VALUES ($1,$2,$3,$4,$5,$6,$7,TRUE)
            RETURNING *
        """,
            position_id, version_row["next_version"],
            data.thesis_one_liner, data.bear_steel_man,
            data.scenarios,
            data.price_thresholds,
            data.entry_context,
        )

        for h in data.hypotheses:
            await db.execute("""
                INSERT INTO hypotheses
                    (thesis_id, position_id, code, label, description, criticality,
                     verification_horizon, kpi_to_watch, confirmation_threshold, alert_threshold)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
                thesis["id"], position_id,
                h.code, h.label, h.description, h.criticality,
                h.verification_horizon, h.kpi_to_watch,
                h.confirmation_threshold, h.alert_threshold,
            )

        if data.peers:
            for p in data.peers:
                await db.execute("""
                    INSERT INTO peers
                        (position_id, peer_ticker, peer_company_name, tier_level,
                         rationale, hypotheses_watched, metrics_to_extract)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    ON CONFLICT DO NOTHING
                """,
                    position_id,
                    p.get("ticker") or p.get("peer_ticker"),
                    p.get("peer_company_name"),
                    p.get("tier_level", 3),
                    p.get("rationale"),
                    p.get("hypotheses_watched"),
                    p.get("metrics_to_extract"),
                )

    return {"id": str(thesis["id"]), "version": thesis["version"], "position_id": position_id}


@router.get("/{position_id}/thesis")
async def get_current_thesis(position_id: str):
    async with get_db_session() as db:
        thesis = await db.fetchrow(
            "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", position_id
        )
        if not thesis:
            raise HTTPException(404, "No active thesis found")
        hypotheses = await db.fetch(
            "SELECT * FROM hypotheses WHERE position_id = $1 ORDER BY code", position_id
        )
    return {**_serialize(thesis), "hypotheses": [_serialize(h) for h in hypotheses]}


@router.get("/{position_id}/reviews")
async def get_reviews(position_id: str, limit: int = 20):
    async with get_db_session() as db:
        rows = await db.fetch("""
            SELECT * FROM reviews WHERE position_id = $1
            ORDER BY review_date DESC LIMIT $2
        """, position_id, limit)
    return [_serialize(row) for row in rows]


@router.post("/{position_id}/peers", status_code=201)
async def add_peer(position_id: str, data: PeerCreate):
    async with get_db_session() as db:
        row = await db.fetchrow("""
            INSERT INTO peers
                (position_id, peer_ticker, peer_company_name, tier_level,
                 rationale, hypotheses_watched, metrics_to_extract)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            RETURNING *
        """,
            position_id, data.peer_ticker, data.peer_company_name, data.tier_level,
            data.rationale, data.hypotheses_watched, data.metrics_to_extract,
        )
    return _serialize(row)


@router.patch("/{position_id}/monitoring/{run_id}/acknowledge")
async def acknowledge_review(position_id: str, run_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "UPDATE reviews SET acknowledged=TRUE WHERE id=$1 AND position_id=$2 RETURNING id",
            run_id, position_id
        )
    if not row:
        raise HTTPException(404, "Review not found")
    return {"acknowledged": True}


@router.post("/{position_id}/thesis-chat")
async def position_thesis_chat(position_id: str, data: dict):
    from app.agents import thesis_chat
    message = data.get("message", "")
    if not message:
        raise HTTPException(400, "message required")

    async with get_db_session() as db:
        thesis = await db.fetchrow(
            "SELECT * FROM theses WHERE position_id=$1 AND is_current=TRUE", position_id
        )

        # Fallback: use the latest regime 1 review's conversation_id if no thesis yet
        conv_id = thesis["dust_conversation_id"] if thesis else None
        if not conv_id:
            review_row = await db.fetchrow(
                """SELECT dust_conversation_id FROM reviews
                   WHERE position_id=$1 AND dust_conversation_id IS NOT NULL
                   ORDER BY review_date DESC LIMIT 1""",
                position_id
            )
            if review_row:
                conv_id = review_row["dust_conversation_id"]

        if not conv_id and not thesis:
            raise HTTPException(404, "No active thesis or regime 1 run found")

        try:
            if conv_id:
                result = await thesis_chat.continue_chat(conv_id, message)
                result["conversation_id"] = conv_id
            else:
                result = await thesis_chat.start_thesis_chat(
                    position_id, str(thesis["id"]), message, db
                )
        except ValueError as e:
            if "rate_limit" in str(e):
                raise HTTPException(503, "Agent temporairement indisponible, réessayez dans 30 secondes")
            if "dust_error" in str(e):
                from app.notifications.slack_notifier import SlackNotifier
                await SlackNotifier().send_error_alert(position_id, f"Erreur agent Dust sur thesis-chat/{position_id}")
                raise HTTPException(502, "Erreur agent Dust")
            raise HTTPException(500, str(e))

    return result


@router.get("/{position_id}/thesis-chat")
async def get_position_thesis_chat(position_id: str):
    from app.agents.thesis_chat import get_chat_history
    async with get_db_session() as db:
        thesis = await db.fetchrow(
            "SELECT dust_conversation_id FROM theses WHERE position_id=$1 AND is_current=TRUE",
            position_id
        )
        conv_id = thesis["dust_conversation_id"] if thesis else None
        if not conv_id:
            review_row = await db.fetchrow(
                """SELECT dust_conversation_id FROM reviews
                   WHERE position_id=$1 AND dust_conversation_id IS NOT NULL
                   ORDER BY review_date DESC LIMIT 1""",
                position_id
            )
            if review_row:
                conv_id = review_row["dust_conversation_id"]

    if not conv_id:
        return {"turns": [], "conversation_id": None}
    turns = await get_chat_history(conv_id)
    return {"turns": turns, "conversation_id": conv_id}


@router.post("/{position_id}/validate-thesis")
async def validate_position_thesis(position_id: str):
    import json as _json
    async with get_db_session() as db:
        # Try direct update first (thesis row exists)
        row = await db.fetchrow("""
            UPDATE theses SET validated_at=NOW()
            WHERE position_id=$1 AND is_current=TRUE
            RETURNING validated_at
        """, position_id)
        if row:
            return {"validated": True, "validated_at": row["validated_at"].isoformat()}

        # No thesis row — create one from latest regime 1 review
        review = await db.fetchrow("""
            SELECT full_output_json, dust_conversation_id FROM reviews
            WHERE position_id=$1
            ORDER BY review_date DESC LIMIT 1
        """, position_id)
        if not review:
            raise HTTPException(404, "No active thesis or regime 1 run found")

        out = review["full_output_json"] or {}
        if isinstance(out, str):
            out = _json.loads(out)

        thesis_one_liner = out.get("thesis_one_liner") or "Analyse Régime 1 — à compléter"
        bear_steel_man   = out.get("bear_steel_man")   or "À compléter après analyse contradictoire"
        scenarios_json   = out.get("scenarios_json")   or {}
        price_thresholds = out.get("price_thresholds_json") or {}
        conv_id          = review["dust_conversation_id"]

        new_row = await db.fetchrow("""
            INSERT INTO theses
              (position_id, version, thesis_one_liner, bear_steel_man,
               scenarios_json, price_thresholds_json,
               dust_conversation_id, is_current, validated_at)
            VALUES ($1, 1, $2, $3, $4, $5, $6, TRUE, NOW())
            RETURNING id, validated_at
        """, position_id, thesis_one_liner, bear_steel_man,
             scenarios_json, price_thresholds, conv_id)

    return {"validated": True, "validated_at": new_row["validated_at"].isoformat()}


def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif hasattr(v, '__class__') and v.__class__.__name__ == 'UUID':
            d[k] = str(v)
    return d


def _serialize_detail(detail: dict) -> dict:
    return {
        "position": _serialize(detail["position"]),
        "thesis": _serialize(detail["thesis"]),
        "hypotheses": [_serialize(h) for h in detail["hypotheses"]],
        "reviews": [_serialize(r) for r in detail["reviews"]],
        "peers": [_serialize(p) for p in detail["peers"]],
        "sector_pulses": [_serialize(p) for p in detail["sector_pulses"]],
    }
