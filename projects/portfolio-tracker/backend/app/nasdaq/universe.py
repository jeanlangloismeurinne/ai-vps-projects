"""Univers : actions ordinaires du NASDAQ, une ligne par entreprise."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
SCREENER_URL = "https://api.nasdaq.com/api/screener/stocks"
_UA = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-tracker)"}

_NOT_COMMON = re.compile(
    r"\b(warrants?|rights?|units?|notes?|debentures?|preferred|subordinated|"
    r"preference|trust certificates?|contingent value|etf|fund)\b|"
    r"(?<!american )depositary shares|\(adw\)", re.I)
_CLASS_TAIL = re.compile(
    r"(\s+-\s.*$|\s+(class|series)\s+[a-z0-9]\b.*$|\s+(common|ordinary|capital)\s+(stock|shares?).*$|"
    r"\s+american depositary.*$|\s+depositary.*$|\s+common units.*$)", re.I)


@dataclass
class Listing:
    symbol: str      # symbole Nasdaq
    yf: str          # symbole yfinance
    name: str
    market_cap: float | None
    last_sale: float | None


def yf_symbol(sym: str) -> str:
    return sym.strip().replace(".", "-").replace("/", "-").replace(" ", "-")


def company_key(name: str) -> str:
    n = _CLASS_TAIL.sub("", name)
    return re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()


def _money(s: str | None) -> float | None:
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


async def fetch_universe() -> list[Listing]:
    async with httpx.AsyncClient(timeout=60, headers=_UA, follow_redirects=True) as c:
        r1 = await c.get(LISTED_URL)
        r1.raise_for_status()
        r2 = await c.get(SCREENER_URL, params={"tableonly": "true", "limit": "10000", "exchange": "NASDAQ"})
        r2.raise_for_status()
    rows = r2.json()["data"]["table"]["rows"]
    screener = {r["symbol"].strip(): r for r in rows}

    out: list[Listing] = []
    for line in r1.text.splitlines()[1:]:
        f = line.split("|")
        if len(f) < 8 or f[0].startswith("File Creation"):
            continue
        sym, name, _cat, test, _fin, _lot, etf, nextshares = f[:8]
        if test == "Y" or etf == "Y" or nextshares == "Y":
            continue
        if _NOT_COMMON.search(name):
            continue
        s = screener.get(sym)
        out.append(Listing(sym, yf_symbol(sym), name.strip(),
                           _money(s["marketCap"]) if s else None,
                           _money(s["lastsale"]) if s else None))
    return out


def dedupe_by_company(listings: list[Listing], liquidity: dict[str, float]) -> list[Listing]:
    """Doubles lignes (GOOG/GOOGL) : on garde la plus liquide (volume en dollars)."""
    best: dict[str, Listing] = {}
    for l in listings:
        k = company_key(l.name)
        cur = best.get(k)
        if cur is None or liquidity.get(l.yf, 0.0) > liquidity.get(cur.yf, 0.0):
            best[k] = l
    return list(best.values())
