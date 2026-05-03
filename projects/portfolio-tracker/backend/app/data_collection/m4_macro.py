import httpx
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Scoring : Buffett 60% / CAPE 40%
TEMPERATURE_THRESHOLDS = {
    "cold":    {"buffett_max": 100, "cape_max": 20,  "cash_pct": 7.5},
    "neutral": {"buffett_max": 120, "cape_max": 25,  "cash_pct": 15.0},
    "warm":    {"buffett_max": 150, "cape_max": 35,  "cash_pct": 27.5},
    "hot":     {"buffett_max": 9999, "cape_max": 9999, "cash_pct": 42.5},
}


async def _fetch_fred_latest(series_id: str, api_key: str) -> Optional[float]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 10,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(FRED_BASE, params=params)
        r.raise_for_status()
        data = r.json()
        observations = data.get("observations", [])
        for obs in observations:
            val = obs.get("value", ".")
            if val != ".":
                return float(val)
    return None


async def get_buffett_indicator(api_key: str) -> dict:
    """Wilshire 5000 / GDP — retourne ratio en % et trend."""
    try:
        wilshire = await _fetch_fred_latest("WILL5000PRFC", api_key)
        gdp = await _fetch_fred_latest("GDP", api_key)
        if not wilshire or not gdp:
            return {"ratio_pct": None, "trend": "neutral"}
        ratio = round((wilshire / gdp) * 100, 2)
        trend = "up" if ratio > 120 else "down" if ratio < 90 else "neutral"
        return {"ratio_pct": ratio, "trend": trend, "wilshire": wilshire, "gdp": gdp}
    except Exception as e:
        logger.warning(f"Buffett indicator error: {e}")
        return {"ratio_pct": None, "trend": "neutral"}


async def get_cape_shiller(api_key: str) -> dict:
    """CAPE Shiller (Cyclically Adjusted PE) via FRED CAPE series."""
    try:
        cape = await _fetch_fred_latest("CAPE", api_key)
        if not cape:
            return {"ratio": None, "trend": "neutral"}
        trend = "up" if cape > 30 else "down" if cape < 20 else "neutral"
        return {"ratio": round(cape, 2), "trend": trend}
    except Exception as e:
        logger.warning(f"CAPE error: {e}")
        return {"ratio": None, "trend": "neutral"}


async def get_market_temperature(fred_api_key: str) -> dict:
    """Agrège Buffett + CAPE → temperature + cash_target_pct.
    Scoring: Buffett 60% / CAPE 40%.
    Niveaux: cold (<100% / <20) → neutral (100-120% / 20-25)
             → warm (120-150% / 25-35) → hot (>150% / >35)
    """
    buffett = await get_buffett_indicator(fred_api_key)
    cape = await get_cape_shiller(fred_api_key)

    buffett_ratio = buffett.get("ratio_pct")
    cape_ratio = cape.get("ratio")

    def _buffett_level(r):
        if r is None: return 1
        if r < 100: return 0
        if r < 120: return 1
        if r < 150: return 2
        return 3

    def _cape_level(r):
        if r is None: return 1
        if r < 20: return 0
        if r < 25: return 1
        if r < 35: return 2
        return 3

    bl = _buffett_level(buffett_ratio)
    cl = _cape_level(cape_ratio)
    combined = round(bl * 0.6 + cl * 0.4)
    levels = ["cold", "neutral", "warm", "hot"]
    temperature = levels[min(int(combined), 3)]
    cash_targets = {"cold": 7.5, "neutral": 15.0, "warm": 27.5, "hot": 42.5}

    return {
        "temperature": temperature,
        "cash_target_pct": cash_targets[temperature],
        "buffett_ratio_pct": buffett_ratio,
        "buffett_trend": buffett.get("trend"),
        "cape_ratio": cape_ratio,
        "cape_trend": cape.get("trend"),
        "raw_data": {"buffett": buffett, "cape": cape},
    }
