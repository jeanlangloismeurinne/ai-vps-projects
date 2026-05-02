import logging
from datetime import datetime
from app.db.database import get_db_session
from app.portfolio.concentration_checker import ConcentrationChecker
from app.data_collection.m1_quantitative import collect_quantitative
from app.config import settings

logger = logging.getLogger(__name__)


class PortfolioView:

    async def generate_snapshot(self) -> dict:
        async with get_db_session() as db:
            positions = await db.fetch("""
                SELECT p.*,
                    r.recommendation, r.alert_level, r.review_date,
                    t.thesis_one_liner
                FROM positions p
                LEFT JOIN LATERAL (
                    SELECT recommendation, alert_level, review_date
                    FROM reviews WHERE position_id = p.id
                    ORDER BY review_date DESC LIMIT 1
                ) r ON TRUE
                LEFT JOIN theses t ON t.position_id = p.id AND t.is_current = TRUE
                WHERE p.status = 'active'
                ORDER BY p.allocation_pct DESC NULLS LAST
            """)

        pos_list = []
        for row in positions:
            p = dict(row)
            try:
                m1 = collect_quantitative(p["ticker"], settings.FMP_API_KEY)
                current_price = m1.get("price", {}).get("current_price")
                entry_price = float(p["entry_price"]) if p["entry_price"] else None
                unrealized_pnl_pct = None
                if current_price and entry_price:
                    unrealized_pnl_pct = round((current_price / entry_price - 1) * 100, 2)

                pos_list.append({
                    "id": str(p["id"]),
                    "ticker": p["ticker"],
                    "company_name": p["company_name"],
                    "sector_schema": p["sector_schema"],
                    "allocation_pct": float(p["allocation_pct"]) if p["allocation_pct"] else None,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                    "recommendation": p["recommendation"],
                    "alert_level": p["alert_level"],
                    "last_review_date": p["review_date"].isoformat() if p["review_date"] else None,
                    "thesis_one_liner": p["thesis_one_liner"],
                })
            except Exception as e:
                logger.warning(f"Snapshot error for {p['ticker']}: {e}")
                pos_list.append({
                    "id": str(p["id"]),
                    "ticker": p["ticker"],
                    "company_name": p["company_name"],
                    "sector_schema": p["sector_schema"],
                    "allocation_pct": float(p["allocation_pct"]) if p["allocation_pct"] else None,
                    "entry_price": float(p["entry_price"]) if p["entry_price"] else None,
                    "current_price": None,
                    "unrealized_pnl_pct": None,
                    "recommendation": p["recommendation"],
                    "alert_level": p["alert_level"],
                    "last_review_date": p["review_date"].isoformat() if p["review_date"] else None,
                    "thesis_one_liner": p["thesis_one_liner"],
                })

        checker = ConcentrationChecker(max_sector_pct=settings.MAX_SECTOR_CONCENTRATION_PCT)
        concentration_flags = checker.check([dict(row) for row in positions])

        snapshot = {
            "snapshot_date": datetime.utcnow().isoformat(),
            "positions": pos_list,
            "concentration_flags": concentration_flags,
            "portfolio_metrics": {
                "total_positions": len(pos_list),
                "total_allocation_pct": sum(
                    p["allocation_pct"] for p in pos_list if p["allocation_pct"]
                ),
            },
        }

        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO portfolio_snapshots (positions_json, concentration_flags_json, portfolio_metrics_json)
                VALUES ($1, $2, $3)
            """, pos_list, concentration_flags, snapshot["portfolio_metrics"])

        return snapshot

    async def get_position_detail(self, position_id: str) -> dict:
        async with get_db_session() as db:
            pos = await db.fetchrow("SELECT * FROM positions WHERE id = $1", position_id)
            if not pos:
                return None

            thesis = await db.fetchrow(
                "SELECT * FROM theses WHERE position_id = $1 AND is_current = TRUE", position_id
            )
            hypotheses = await db.fetch(
                "SELECT * FROM hypotheses WHERE position_id = $1 ORDER BY code", position_id
            )
            reviews = await db.fetch(
                "SELECT * FROM reviews WHERE position_id = $1 ORDER BY review_date DESC LIMIT 10",
                position_id
            )
            peers = await db.fetch(
                "SELECT * FROM peers WHERE position_id = $1 ORDER BY tier_level", position_id
            )
            pulses = await db.fetch("""
                SELECT * FROM sector_pulses WHERE main_position_id = $1
                ORDER BY pulse_date DESC LIMIT 20
            """, position_id)

        return {
            "position": dict(pos),
            "thesis": dict(thesis) if thesis else None,
            "hypotheses": [dict(h) for h in hypotheses],
            "reviews": [dict(r) for r in reviews],
            "peers": [dict(p) for p in peers],
            "sector_pulses": [dict(p) for p in pulses],
        }
