from datetime import datetime
from typing import Optional


def assemble_data_brief(ticker: str, m1_data: dict, m2_data: dict,
                        m3_data: Optional[dict], thesis_data: Optional[dict],
                        sector_pulses_accumulated: Optional[list],
                        peers_m1_data: Optional[dict]) -> dict:

    brief = {
        "ticker": ticker,
        "brief_date": datetime.utcnow().isoformat(),
        "quantitative": {
            "price": m1_data.get("price", {}),
            "valuation": m1_data.get("valuation", {}),
            "financials_3y": m1_data.get("financials_3y", {}),
            "dividend": m1_data.get("dividend", {}),
            "eps_estimates": m1_data.get("eps_estimates", {}),
        },
        "events": {
            "earnings_calendar": m2_data.get("earnings_calendar", {}),
            "recent_ir_news": m2_data.get("ir_feed", [])[:5],
            "material_news": [n for n in m2_data.get("news", [])
                              if n.get("materiality_score", 0) >= 2][:8],
        },
    }

    if m3_data:
        brief["qualitative"] = m3_data

    if peers_m1_data:
        brief["peers_snapshot"] = {
            t: {"pe_ntm": d.get("valuation", {}).get("pe_ntm"),
                "fcf_yield_pct": d.get("valuation", {}).get("fcf_yield_pct"),
                "ytd_change_pct": d.get("price", {}).get("ytd_change_pct")}
            for t, d in peers_m1_data.items() if "error" not in d
        }

    if sector_pulses_accumulated:
        brief["accumulated_sector_pulses"] = sector_pulses_accumulated
        scores = [p.get("pulse_score", 0) for p in sector_pulses_accumulated
                  if p.get("pulse_score")]
        brief["sector_momentum_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0

    if thesis_data:
        cp = m1_data.get("price", {}).get("current_price")
        ep = thesis_data.get("entry_price")
        brief["active_thesis"] = {
            "thesis_one_liner": thesis_data.get("thesis_one_liner"),
            "hypotheses": thesis_data.get("hypotheses", []),
            "last_recommendation": thesis_data.get("last_recommendation"),
            "entry_price": ep,
            "current_return_pct": round((cp / ep - 1) * 100, 2) if ep and cp else None,
        }

    return brief
