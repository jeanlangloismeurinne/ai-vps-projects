"""Job quotidien : télécharge, calcule les deux indicateurs pour tout l'univers, publie un instantané.

Idempotent : un instantané est identifié par la dernière séance US couverte (`run_date`) ; relancer
le job le même jour remplace cet instantané par le même résultat. Si les données sont absentes ou
incomplètes, aucun instantané n'est écrit : l'API continue de servir celui de la veille et signale
l'avertissement (statut `degraded` / `failed`).
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from datetime import date, datetime, timezone

import numpy as np

from app.db.database import get_db_session
from app.nasdaq.calendrier import last_closed_session
from app.nasdaq.indicators import ALERT_MONTHS, compute, from_daynum, to_daynum
from app.nasdaq.universe import Listing, dedupe_by_company, fetch_universe

logger = logging.getLogger(__name__)

CHUNK = 40  # le VPS n'a que ~1 Go libre : un lot de 200 historiques complets a fait tuer le processus (OOM)
CHUNK_TIMEOUT_S = 420
MIN_MARKET_CAP_USD = 50_000_000_000  # l'analyse ne porte que sur les entreprises au-dessus de ce seuil
MIN_PRICED_RATIO = 0.80
MIN_ON_REF_RATIO = 0.70  # les titres peu liquides n'ont pas de cours tous les jours
SUSPENDED_AFTER_DAYS = 7

_lock = asyncio.Lock()
state: dict = {"running": False, "started_at": None, "step": None, "done": 0, "total": 0}


class _Log:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, msg: str) -> None:
        line = f"{datetime.now(timezone.utc):%H:%M:%S} {msg}"
        self.lines.append(line)
        logger.info("nasdaq: %s", msg)

    def text(self) -> str:
        return "\n".join(self.lines)[-20000:]


def _download_chunk(symbols: list[str], max_day: int) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
    import yfinance as yf

    df = yf.download(symbols, period="max", auto_adjust=True, progress=False,
                     group_by="ticker", threads=True, timeout=30)
    out: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
    if df is None or df.empty:
        return out
    multi = hasattr(df.columns, "levels") and df.columns.nlevels == 2
    for s in symbols:
        try:
            sub = df[s] if multi else df
            sub = sub[["Close", "Volume"]].dropna(subset=["Close"])
        except KeyError:
            continue
        if len(sub) < 2:
            continue
        sub = sub[sub.index.values.astype("datetime64[D]").astype(np.int64) <= max_day]  # jamais de séance en cours
        if len(sub) < 2:
            continue
        days = (sub.index.values.astype("datetime64[D]").astype(np.int64))
        closes = sub["Close"].to_numpy(dtype=np.float64)
        tail = sub.tail(20)
        liq = float((tail["Close"] * tail["Volume"].fillna(0)).mean())
        out[s] = (days, closes, liq)
    return out


async def _download_all(symbols: list[str], max_day: int, log: _Log) -> dict[str, tuple[int, float]]:
    """Télécharge par petits lots, écrit chaque lot en base et ne garde en mémoire que (dernier jour, liquidité)."""
    loop = asyncio.get_running_loop()
    data: dict[str, tuple[int, float]] = {}
    state["total"] = len(symbols)

    async def run(chunk: list[str], label: str) -> None:
        t0 = time.time()
        try:
            got = await asyncio.wait_for(loop.run_in_executor(None, _download_chunk, chunk, max_day), CHUNK_TIMEOUT_S)
            await _save_prices(got)
            data.update({k: (int(v[0][-1]), v[2]) for k, v in got.items()})
            n_got = len(got)
            del got
            log(f"{label}: {n_got}/{len(chunk)} en {time.time() - t0:.0f}s")
        except asyncio.TimeoutError:
            log(f"{label}: ABANDON après {CHUNK_TIMEOUT_S}s ({len(chunk)} titres, {chunk[0]}…)")
        except Exception as e:  # noqa: BLE001 — un lot raté ne doit pas arrêter les autres
            log(f"{label}: ÉCHEC {type(e).__name__}: {str(e)[:200]}")
        state["done"] = len(data)

    for i in range(0, len(symbols), CHUNK):
        await run(symbols[i:i + CHUNK], f"lot {i // CHUNK + 1}")
    missing = [s for s in symbols if s not in data]
    if missing:
        log(f"reprise de {len(missing)} titres manquants (lots de 20)")
        for i in range(0, len(missing), 20):
            await run(missing[i:i + 20], f"reprise {i // 20 + 1}")
    return data


async def _save_prices(data: dict) -> None:
    rows = [(s, from_daynum(d[0]), from_daynum(d[-1]), d.tolist(), c.tolist())
            for s, (d, c, _l) in data.items()]
    async with get_db_session() as conn:
        for i in range(0, len(rows), 100):
            await conn.executemany(
                """INSERT INTO nasdaq_prices (ticker, first_date, last_date, day_nums, closes, updated_at)
                   VALUES ($1,$2,$3,$4,$5, now())
                   ON CONFLICT (ticker) DO UPDATE SET first_date=EXCLUDED.first_date,
                     last_date=EXCLUDED.last_date, day_nums=EXCLUDED.day_nums,
                     closes=EXCLUDED.closes, updated_at=now()""",
                rows[i:i + 100])


async def _finish_run(run_date: date, status: str, log: _Log, **kw) -> None:
    async with get_db_session() as conn:
        await conn.execute(
            """INSERT INTO nasdaq_runs (run_date, status, started_at, finished_at, n_universe, n_priced,
                                         n_shown, warning, log)
               VALUES ($1,$2,$3, now(), $4,$5,$6,$7,$8)""",
            run_date, status, state["started_at"], kw.get("n_universe"), kw.get("n_priced"),
            kw.get("n_shown"), kw.get("warning"), log.text())


async def run_daily() -> dict:
    if _lock.locked():
        return {"status": "already_running"}
    async with _lock:
        log = _Log()
        state.update(running=True, started_at=datetime.now(timezone.utc), step="univers", done=0, total=0)
        today = datetime.now(timezone.utc).date()
        try:
            return await _run(log, today)
        except Exception as e:  # noqa: BLE001
            log(f"ÉCHEC du job : {type(e).__name__}: {e}")
            logger.exception("nasdaq job")
            await _finish_run(today, "failed", log, warning=f"Le job du jour a échoué ({type(e).__name__}).")
            return {"status": "failed", "error": str(e)}
        finally:
            state.update(running=False, step=None)


async def _run(log: _Log, today: date) -> dict:
    listings = await fetch_universe()
    log(f"univers : {len(listings)} actions ordinaires (hors ETF/warrants/droits)")
    listings = [l for l in listings if l.market_cap is not None and l.market_cap >= MIN_MARKET_CAP_USD]
    log(f"retenues : {len(listings)} avec capitalisation ≥ {MIN_MARKET_CAP_USD / 1e9:.0f} Md$")
    state["step"] = "téléchargement des cours"
    by_yf = {l.yf: l for l in listings}
    expected = last_closed_session(datetime.now(timezone.utc))
    log(f"dernière séance US clôturée attendue : {expected}")
    data = await _download_all(list(by_yf), to_daynum(expected), log)
    n_universe = len(listings)

    if len(data) < MIN_PRICED_RATIO * n_universe:
        msg = (f"Données du jour incomplètes : {len(data)}/{n_universe} titres reçus. "
               "Les valeurs de la veille sont conservées.")
        log(msg)
        await _finish_run(today, "degraded", log, n_universe=n_universe, n_priced=len(data), warning=msg)
        return {"status": "degraded", "priced": len(data), "universe": n_universe}

    state["step"] = "calcul"

    kept = dedupe_by_company([by_yf[s] for s in data], {s: v[1] for s, v in data.items()})
    log(f"après dédoublonnage des doubles lignes : {len(kept)} entreprises")

    ref = Counter(data[l.yf][0] for l in kept).most_common(1)[0][0]
    ref_date = from_daynum(ref)
    fresh = [l for l in kept if ref - data[l.yf][0] <= SUSPENDED_AFTER_DAYS]
    on_ref = sum(1 for l in kept if data[l.yf][0] == ref)
    if ref_date < expected or on_ref < MIN_ON_REF_RATIO * len(kept):
        msg = (f"Données du jour absentes ou incomplètes (séance attendue : {expected:%d/%m/%Y}, "
               f"dernière séance reçue : {ref_date:%d/%m/%Y}, {on_ref}/{len(kept)} titres à jour). "
               "Les valeurs de la veille sont conservées.")
        log(msg)
        await _finish_run(ref_date, "degraded", log, n_universe=n_universe, n_priced=len(data), warning=msg)
        return {"status": "degraded", "ref_date": str(ref_date)}
    log(f"séance de référence {ref_date} : {on_ref} titres cotés ce jour, "
        f"{len(kept) - len(fresh)} suspendus/radiés (sans cours depuis > {SUSPENDED_AFTER_DAYS} j) retirés")

    async with get_db_session() as conn:
        prev_date = await conn.fetchval(
            "SELECT max(run_date) FROM nasdaq_indicators WHERE run_date < $1", ref_date)
        prev_alert = {}
        if prev_date:
            prev_alert = {r["ticker"]: r["alert"] for r in await conn.fetch(
                "SELECT ticker, alert FROM nasdaq_indicators WHERE run_date = $1", prev_date)}

    rows = []
    for i in range(0, len(fresh), 100):
        batch = fresh[i:i + 100]
        async with get_db_session() as conn:
            got = {r["ticker"]: r for r in await conn.fetch(
                "SELECT ticker, day_nums, closes FROM nasdaq_prices WHERE ticker = ANY($1::text[])",
                [l.yf for l in batch])}
        for l in batch:
            r = got.get(l.yf)
            ind = compute(np.array(r["day_nums"]), np.array(r["closes"])) if r else None
            if ind is None:
                continue
            alert = ind.is_atl or (ind.age_months is not None and ind.age_months >= ALERT_MONTHS)
            rows.append((ref_date, l.symbol, l.name, ind.price, ind.age_months, ind.is_atl, ind.is_ath,
                         ind.multiple_10y, ind.lt_10y, ind.short_history, l.market_cap, alert,
                         alert and not prev_alert.get(l.symbol, False) if prev_date else False))
    state["step"] = "publication"
    async with get_db_session() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM nasdaq_indicators WHERE run_date = $1", ref_date)
            await conn.executemany(
                """INSERT INTO nasdaq_indicators (run_date, ticker, name, price, age_months, is_atl, is_ath,
                     multiple_10y, lt_10y, short_history, market_cap, alert, alert_new)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""", rows)
    n_alert = sum(1 for r in rows if r[11])
    log(f"{len(rows)} titres publiés, {n_alert} en alerte, {sum(1 for r in rows if r[12])} nouvelles")
    await _finish_run(ref_date, "ok", log, n_universe=n_universe, n_priced=len(data), n_shown=len(rows))
    return {"status": "ok", "run_date": str(ref_date), "shown": len(rows), "alerts": n_alert}
