from typing import List
from collections import defaultdict


class ConcentrationChecker:
    def __init__(self, max_sector_pct: float = 20.0, max_single_position_pct: float = 15.0):
        self.max_sector_pct = max_sector_pct
        self.max_single_position_pct = max_single_position_pct

    def check(self, positions: list) -> list:
        flags = []
        active = [p for p in positions if p.get("status") == "active" and p.get("allocation_pct")]

        total_alloc = sum(p["allocation_pct"] for p in active)
        if total_alloc == 0:
            return flags

        sector_totals = defaultdict(float)
        for p in active:
            sector_totals[p["sector_schema"]] += p["allocation_pct"]

        for sector, total in sector_totals.items():
            if total > self.max_sector_pct:
                flags.append({
                    "type": "sector_concentration",
                    "sector": sector,
                    "total_pct": total,
                    "threshold_pct": self.max_sector_pct,
                })

        for p in active:
            if p["allocation_pct"] > self.max_single_position_pct:
                flags.append({
                    "type": "single_position",
                    "ticker": p["ticker"],
                    "total_pct": p["allocation_pct"],
                    "threshold_pct": self.max_single_position_pct,
                })

        return flags
