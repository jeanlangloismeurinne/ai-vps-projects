"""Suivi NASDAQ (spec du 2026-10-26) — indépendant du reste du portfolio-tracker.

  GET  /nasdaq/snapshot        dernier instantané publié + avertissement éventuel
  GET  /nasdaq/status          job en cours, derniers passages (journal)
  POST /nasdaq/run             lance le job maintenant (en tâche de fond)
  GET  /nasdaq/history/{t}     historique quotidien des deux indicateurs d'un titre
  GET  /nasdaq/series/{t}      idem pour un titre sur 1y / 5y / max (fiche)
  GET  /nasdaq/watchlist       titres suivis (cartes de l'accueil) ; PUT/DELETE /watchlist/{t}
  GET  /nasdaq/search?q=       recherche parmi les titres publiés
  GET  /nasdaq/proba/{t}       courbe de probabilité de nouveau plus haut à 12 mois (point par point, passé seul)
  GET  /nasdaq/proba-calib     qualité du modèle mesurée hors échantillon
  GET  /nasdaq/series          ancienneté et multiple de chaque titre aux ~260 dernières séances (reconstitués des cours)
"""
from __future__ import annotations

import asyncio
from datetime import date

import numpy as np

from fastapi import APIRouter, HTTPException, Response

from app.db.database import get_db_session
from app.nasdaq import job, proba
from app.nasdaq.indicators import series_tail, to_daynum
from app.nasdaq.universe import yf_symbol

router = APIRouter(prefix="/nasdaq", tags=["nasdaq"])

# Catégories de multiple 10 ans pour la liste d'alertes (borne basse incluse), de la plus haute à la plus basse.
CATEGORIES = [
    {"key": "x10", "label": "Croissance forte (≥ 10×)", "min": 10.0},
    {"key": "x5", "label": "Croissance (5× à 10×)", "min": 5.0},
    {"key": "x2", "label": "Progression (2× à 5×)", "min": 2.0},
    {"key": "x1", "label": "Stable (1× à 2×)", "min": 1.0},
    {"key": "lt1", "label": "Destruction de valeur (< 1×)", "min": 0.0},
]
STALE_DAYS = 5

SERIES_SESSIONS = 260  # ~1 an de séances : couvre les sauts 5 j / 20 j et les traînées jusqu'à 3 mois

_tasks: set[asyncio.Task] = set()
_series_cache: dict = {}


@router.get("/snapshot")
async def snapshot() -> dict:
    async with get_db_session() as conn:
        last_ok = await conn.fetchrow(
            "SELECT id, run_date, finished_at FROM nasdaq_runs WHERE status='ok' ORDER BY run_date DESC, id DESC LIMIT 1")
        if not last_ok:
            return {"run_date": None, "rows": [], "categories": CATEGORIES, "warning": "Aucun calcul n'a encore été publié."}
        rows = await conn.fetch(
            """SELECT ticker, name, price, age_months, is_atl, is_ath, multiple_10y, lt_10y, short_history,
                      market_cap, alert, alert_new FROM nasdaq_indicators WHERE run_date = $1""",
            last_ok["run_date"])
        newer = await conn.fetchrow(
            "SELECT status, warning, finished_at FROM nasdaq_runs WHERE id > $1 AND status <> 'ok' ORDER BY id DESC LIMIT 1",
            last_ok["id"])
    warning = newer["warning"] if newer else None
    if (date.today() - last_ok["run_date"]).days > STALE_DAYS and not warning:
        warning = f"Dernières données du {last_ok['run_date']:%d/%m/%Y} : le calcul n'a pas été rafraîchi récemment."
    return {
        "run_date": last_ok["run_date"].isoformat(),
        "generated_at": last_ok["finished_at"].isoformat() if last_ok["finished_at"] else None,
        "warning": warning,
        "categories": CATEGORIES,
        "rows": [dict(r) for r in rows],
    }


@router.get("/status")
async def status() -> dict:
    async with get_db_session() as conn:
        runs = await conn.fetch(
            """SELECT id, run_date, status, started_at, finished_at, n_universe, n_priced, n_shown, warning, log
               FROM nasdaq_runs ORDER BY id DESC LIMIT 10""")
    return {"running": job.state["running"], "step": job.state["step"],
            "done": job.state["done"], "total": job.state["total"],
            "started_at": job.state["started_at"], "runs": [dict(r) for r in runs]}


@router.post("/run", status_code=202)
async def run_now() -> dict:
    if job.state["running"]:
        raise HTTPException(status_code=409, detail="Un calcul est déjà en cours.")
    t = asyncio.create_task(job.run_daily())
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return {"started": True}


@router.get("/history/{ticker}")
async def history(ticker: str) -> list[dict]:
    async with get_db_session() as conn:
        rows = await conn.fetch(
            """SELECT run_date, price, age_months, is_atl, multiple_10y, market_cap, alert
               FROM nasdaq_indicators WHERE ticker = $1 ORDER BY run_date""", ticker.upper())
    if not rows:
        raise HTTPException(status_code=404, detail=f"Titre `{ticker}` absent du suivi.")
    return [dict(r) for r in rows]


@router.get("/series")
async def series() -> dict:
    """Dérivée des mêmes cours que l'instantané : jamais périmée, recalculée une fois par instantané publié."""
    async with get_db_session() as conn:
        run_date = await conn.fetchval(
            "SELECT run_date FROM nasdaq_runs WHERE status='ok' ORDER BY run_date DESC, id DESC LIMIT 1")
        if not run_date:
            return {"run_date": None, "series": {}}
        if _series_cache.get("run_date") == run_date:
            return _series_cache["payload"]
        tickers = [r["ticker"] for r in await conn.fetch(
            "SELECT ticker FROM nasdaq_indicators WHERE run_date = $1", run_date)]
        prices = await conn.fetch(
            "SELECT ticker, day_nums, closes FROM nasdaq_prices WHERE ticker = ANY($1::text[])",
            [yf_symbol(t) for t in tickers])
    by_yf = {yf_symbol(t): t for t in tickers}
    cut = to_daynum(run_date)
    out: dict[str, dict] = {}
    for r in prices:
        d = np.array(r["day_nums"], dtype=np.int64)
        c = np.array(r["closes"], dtype=np.float64)
        keep = d <= cut
        s = series_tail(d[keep], c[keep], SERIES_SESSIONS)
        if s:
            out[by_yf[r["ticker"]]] = s
    payload = {"run_date": run_date.isoformat(), "series": out}
    _series_cache.update(run_date=run_date, payload=payload)
    return payload


RANGES = {"1y": 260, "5y": 1300, "max": 10**6}


@router.get("/series/{ticker}")
async def series_one(ticker: str, range: str = "1y") -> dict:
    """Fiche d'un titre : cours et ancienneté sur 1 an, 5 ans ou tout l'historique (sans multiple, inutile ici)."""
    if range not in RANGES:
        raise HTTPException(status_code=422, detail="range ∈ 1y, 5y, max")
    async with get_db_session() as conn:
        run_date = await conn.fetchval(
            "SELECT run_date FROM nasdaq_runs WHERE status='ok' ORDER BY run_date DESC, id DESC LIMIT 1")
        row = await conn.fetchrow("SELECT day_nums, closes FROM nasdaq_prices WHERE ticker = $1",
                                  yf_symbol(ticker.upper())) if run_date else None
    if not row:
        raise HTTPException(status_code=404, detail=f"Titre `{ticker}` absent du suivi.")
    d = np.array(row["day_nums"], dtype=np.int64)
    c = np.array(row["closes"], dtype=np.float64)
    keep = d <= to_daynum(run_date)
    s = series_tail(d[keep], c[keep], RANGES[range], with_mult=False)
    if not s:
        raise HTTPException(status_code=404, detail=f"Historique insuffisant pour `{ticker}`.")
    return s


def _tk(ticker: str) -> str:
    return ticker.upper().strip()


async def _published(conn, tickers: list[str]) -> dict[str, str]:
    rows = await conn.fetch(
        """SELECT DISTINCT ON (ticker) ticker, name FROM nasdaq_indicators
           WHERE ticker = ANY($1::text[]) ORDER BY ticker, run_date DESC""", tickers)
    return {r["ticker"]: r["name"] for r in rows}


@router.get("/watchlist")
async def watchlist() -> dict:
    async with get_db_session() as conn:
        tickers = [r["ticker"] for r in await conn.fetch("SELECT ticker FROM nasdaq_watchlist ORDER BY added_at")]
    return {"tickers": tickers}


@router.put("/watchlist/{ticker}", status_code=204, response_class=Response)
async def watchlist_add(ticker: str) -> None:
    t = _tk(ticker)
    async with get_db_session() as conn:
        if t not in await _published(conn, [t]):
            raise HTTPException(status_code=404, detail=f"Titre `{ticker}` absent du suivi.")
        await conn.execute("INSERT INTO nasdaq_watchlist (ticker) VALUES ($1) ON CONFLICT DO NOTHING", t)


@router.delete("/watchlist/{ticker}", status_code=204, response_class=Response)
async def watchlist_del(ticker: str) -> None:
    async with get_db_session() as conn:
        await conn.execute("DELETE FROM nasdaq_watchlist WHERE ticker = $1", _tk(ticker))


@router.get("/search")
async def search(q: str = "", limit: int = 8) -> list[dict]:
    q = q.strip()
    if not q:
        return []
    async with get_db_session() as conn:
        run_date = await conn.fetchval(
            "SELECT run_date FROM nasdaq_runs WHERE status='ok' ORDER BY run_date DESC, id DESC LIMIT 1")
        if not run_date:
            return []
        rows = await conn.fetch(
            """SELECT ticker, name, market_cap FROM nasdaq_indicators
               WHERE run_date = $1 AND (ticker ILIKE $2 OR name ILIKE $3)
               ORDER BY (ticker ILIKE $2) DESC, market_cap DESC NULLS LAST LIMIT $4""",
            run_date, q + "%", "%" + q + "%", min(max(limit, 1), 20))
    return [dict(r) for r in rows]


@router.get("/proba-calib")
async def proba_calib() -> dict:
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT payload FROM nasdaq_proba_calib WHERE id = 1")
    return {"calib": row["payload"] if row else None, "fitting": proba.state["running"], "error": proba.state["error"]}


@router.get("/proba/{ticker}")
async def proba_one(ticker: str, years: int = 5) -> dict:
    """p = probabilité estimée à chaque date (modèle appris AVANT cette année) ; o = 1 atteint / 0 manqué / null en cours."""
    if not 1 <= years <= 40:
        raise HTTPException(status_code=422, detail="years ∈ 1..40")
    models = await proba.load_models()
    if not models:
        raise HTTPException(status_code=503, detail="Modèle de probabilité pas encore appris.")
    async with get_db_session() as conn:
        run_date = await conn.fetchval(
            "SELECT run_date FROM nasdaq_runs WHERE status='ok' ORDER BY run_date DESC, id DESC LIMIT 1")
        row = await conn.fetchrow("SELECT day_nums, closes FROM nasdaq_prices WHERE ticker = $1",
                                  yf_symbol(_tk(ticker))) if run_date else None
    if not row:
        raise HTTPException(status_code=404, detail=f"Titre `{ticker}` absent du suivi.")
    d = np.array(row["day_nums"], dtype=np.int64)
    c = np.array(row["closes"], dtype=np.float64)
    keep = d <= to_daynum(run_date)
    out = proba.curve(d[keep], c[keep], models, years=years)
    if not out:
        raise HTTPException(status_code=404, detail=f"Historique insuffisant pour `{ticker}`.")
    return out
