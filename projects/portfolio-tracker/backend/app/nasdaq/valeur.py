"""Valeur du temps passé : plancher indexé sur l'inflation et décomposition de la hausse du cours.

Détenteur unique des formules (les écrans ne font que dessiner) :
  état à t      = bénéfice dilué par action des 12 derniers mois CONNU à t (date de dépôt SEC), ramené
                  au nombre d'actions d'aujourd'hui (divisions postérieures au dépôt) et en dollars ;
  plancher à t  = moyenne de l'état à t, t-12, t-24 mois × 12 / 15 / 20 (le prix est brut, non ajusté
                  des dividendes : un cours ajusté abaisse le passé et fabrique des percées) ;
  fantôme       = meilleur état réel (moyenne 3 ans ÷ inflation) des 120 derniers mois × inflation × 15 ;
  caduc         = moyenne 3 ans ≤ 0, ou état réel < 90 % du meilleur des 10 ans ;
  décomposition = cours₁/cours₀ = inflation × bénéfices réels × multiple (état des 12 derniers mois),
                  et rendement total = cours × dividendes réinvestis ; S&P 500 dividendes réinvestis en regard.
Mesures qui ont fixé ces choix : mémoire `project_nasdaq_valeur_temps_passe` (test de percée 2009-2026).
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import time
import urllib.request
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from app.db.database import get_db_session

logger = logging.getLogger(__name__)

SEC_UA = {"User-Agent": "LM Associes nasdaq-research plm@lm-associes.com"}
MULTS = (12, 15, 20)
MID = 15
DEGRADED_BELOW = 0.9
BEST_WINDOW = 120
START = "2007-01"
PERIODS = {"3y": 36, "5y": 60, "10y": 120, "2010": None}
EPS_CHECK = (0.7, 1.4)  # écart toléré avec le bénéfice des 12 derniers mois de Yahoo (ADR, devise, tag)

state: dict = {"running": False, "error": None, "done": 0, "total": 0, "finished_at": None}


# ───────────────────────────── fonctions pures ─────────────────────────────

def _month(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m")


def eps_points(facts: dict) -> tuple[list[dict], str | None]:
    """Valeurs de BPA dilué déposées (première publication de chaque période) : trimestres, exercices, 9 mois."""
    rows = []
    unit_seen = None
    for ns, tag in (("us-gaap", "EarningsPerShareDiluted"), ("us-gaap", "EarningsPerShareBasicAndDiluted"),
                    ("ifrs-full", "DilutedEarningsLossPerShare")):
        for unit, xs in facts.get("facts", {}).get(ns, {}).get(tag, {}).get("units", {}).items():
            for x in xs:
                if "start" not in x or "end" not in x or "filed" not in x:
                    continue
                d = (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days
                k = "Q" if 80 <= d <= 100 else "Y" if 340 <= d <= 380 else "9" if 260 <= d <= 285 else None
                if k:
                    rows.append({"k": k, "start": x["start"], "end": x["end"], "filed": x["filed"],
                                 "v": float(x["val"]), "unit": unit})
                    unit_seen = unit
        if rows:
            break
    first: dict = {}
    for r in sorted(rows, key=lambda r: r["filed"]):
        first.setdefault((r["k"], r["end"]), r)
    return list(first.values()), unit_seen


def ttm_points(points: list[dict]) -> list[dict]:
    """Bénéfice des 12 derniers mois, daté du jour où il devient connu (dépôt le plus tardif des 4 trimestres).

    Le 4ᵉ trimestre se déduit : exercice − 9 mois (même date de début). Sans trimestres (émetteur
    étranger, 20-F), l'exercice tient lieu de 12 derniers mois à sa date de dépôt.
    """
    Q = {p["end"]: (p["filed"], p["v"]) for p in points if p["k"] == "Q"}
    nine = {p["start"]: p for p in points if p["k"] == "9"}
    years = [p for p in points if p["k"] == "Y"]
    for y in years:
        n = nine.get(y["start"])
        if n and y["end"] not in Q:
            Q[y["end"]] = (y["filed"], y["v"] - n["v"])
    ends = sorted(Q)
    out = []
    for i in range(3, len(ends)):
        e4 = ends[i - 3:i + 1]
        span = (pd.Timestamp(e4[-1]) - pd.Timestamp(e4[0])).days
        if not 250 <= span <= 300:
            continue
        out.append({"end": e4[-1], "avail": max(Q[e][0] for e in e4), "ttm": sum(Q[e][1] for e in e4)})
    if len(out) < 4:
        out = [{"end": y["end"], "avail": y["filed"], "ttm": y["v"]} for y in sorted(years, key=lambda y: y["end"])]
    return out


def adjust_splits(points: list[dict], splits: list[tuple[str, float]]) -> list[dict]:
    """Ramène chaque valeur DÉPOSÉE au nombre d'actions d'aujourd'hui : ÷ produit des divisions postérieures à
    SON dépôt. S'applique aux valeurs brutes, avant toute addition : quatre trimestres déposés de part et
    d'autre d'une division ne sont pas sur la même base."""
    out = []
    for p in points:
        k = 1.0
        for d, r in splits:
            if d > p["filed"] and r > 0:
                k *= r
        out.append({**p, "v": p["v"] / k})
    return out


def state_by_month(ttm: list[dict], months: list[str]) -> list[float | None]:
    """État connu à la fin de chaque mois (point-in-time : la dernière valeur DÉPOSÉE au plus tard ce mois-là)."""
    pts = sorted(ttm, key=lambda p: p["avail"])
    out, j, cur = [], 0, None
    for m in months:
        end = (pd.Period(m, "M").end_time).strftime("%Y-%m-%d")
        while j < len(pts) and pts[j]["avail"] <= end:
            cur = pts[j]["ttm"]
            j += 1
        out.append(cur)
    return out


def _a3(e: list, i: int):
    if i < 24 or e[i] is None or e[i - 12] is None or e[i - 24] is None:
        return None
    return (e[i] + e[i - 12] + e[i - 24]) / 3


def floor_series(e: list, p: list, cpi: list) -> dict:
    n = len(p)
    a3 = [_a3(e, i) for i in range(n)]
    real = [a3[i] / cpi[i] if a3[i] is not None and a3[i] > 0 and cpi[i] else None for i in range(n)]
    out = {m: [] for m in ("lo", "mid", "hi", "ghost", "ratio")}
    out["degraded"] = []
    for i in range(n):
        win = [r for r in real[max(0, i - BEST_WINDOW + 1):i + 1] if r is not None]
        best = max(win) if win else None
        ok = a3[i] is not None and a3[i] > 0
        out["lo"].append(a3[i] * MULTS[0] if ok else None)
        out["mid"].append(a3[i] * MID if ok else None)
        out["hi"].append(a3[i] * MULTS[-1] if ok else None)
        out["ghost"].append(best * cpi[i] * MID if best else None)
        out["ratio"].append(p[i] / (a3[i] * MID) if ok and p[i] else None)
        out["degraded"].append(bool(a3[i] is not None and (not ok or (best and real[i] < DEGRADED_BELOW * best))))
    return out


def start_index(months: list[str], e: list, period: str) -> tuple[int, bool]:
    n = len(months) - 1
    span = PERIODS[period]
    i0 = max(0, n - span) if span else max(0, months.index("2010-01") if "2010-01" in months else 0)
    want = i0
    while i0 < n - 12 and not (e[i0] is not None and e[i0] > 0):
        i0 += 1
    return i0, i0 != want


def decompose(d: dict, period: str) -> dict:
    """Facteurs multiplicatifs de i0 à aujourd'hui, et leurs rendements annuels."""
    m, p, tr, e, cpi, sp = d["m"], d["p"], d["tr"], d["e"], d["cpi"], d["sp"]
    i0, shifted = start_index(m, e, period)
    n = len(m) - 1
    yrs = (n - i0) / 12
    out = {"start": m[i0], "shifted": shifted, "years": round(yrs, 2), "ok": False}
    if yrs < 1 or not p[i0] or not p[n] or not tr[i0] or not tr[n]:
        out["reason"] = "historique insuffisant"
        return out
    f = {"infl": cpi[n] / cpi[i0], "sp": sp[n] / sp[i0] if sp[i0] and sp[n] else None,
         "div": (tr[n] / tr[i0]) / (p[n] / p[i0]), "price": p[n] / p[i0]}
    f["total"] = f["price"] * f["div"]
    e0, e1 = e[i0], e[n]
    if e0 is None or e1 is None or e0 <= 0 or e1 <= 0:
        out["reason"] = "perte à l'une des deux dates"
    else:
        f["real"] = (e1 / e0) / f["infl"]
        f["mult"] = (p[n] / e1) / (p[i0] / e0)
        out["pe0"], out["pe1"] = p[i0] / e0, p[n] / e1
        out["ok"] = True
        lp = math.log(f["price"])
        out["borrowed"] = max(0.0, min(1.0, math.log(f["mult"]) / lp)) if f["price"] > 1.0001 else None
    out["factor"] = {k: v for k, v in f.items() if v is not None}
    out["annual"] = {k: v ** (1 / yrs) - 1 for k, v in out["factor"].items()}
    return out


def cumulative(d: dict, period: str) -> dict:
    """Pour l'aire empilée : log des facteurs cumulés mois par mois depuis le départ de la période."""
    m, p, tr, e, cpi, sp = d["m"], d["p"], d["tr"], d["e"], d["cpi"], d["sp"]
    i0, _ = start_index(m, e, period)
    out = {k: [] for k in ("m", "infl", "real", "mult", "div", "total", "sp")}
    e0 = e[i0] if e[i0] and e[i0] > 0 else None
    for i in range(i0, len(m)):
        out["m"].append(m[i])
        li = math.log(cpi[i] / cpi[i0])
        out["infl"].append(li)
        out["div"].append(math.log((tr[i] / tr[i0]) / (p[i] / p[i0])) if tr[i] and p[i] else None)
        out["total"].append(math.log(tr[i] / tr[i0]) if tr[i] else None)
        out["sp"].append(math.log(sp[i] / sp[i0]) if sp[i] and sp[i0] else None)
        if e0 and e[i] and e[i] > 0 and p[i]:
            out["real"].append(math.log(e[i] / e0) - li)
            out["mult"].append(math.log((p[i] / e[i]) / (p[i0] / e0)))
        else:
            out["real"].append(None)
            out["mult"].append(None)
    return out


def summary(d: dict, fwd: dict | None) -> dict:
    fl = floor_series(d["e"], d["p"], d["cpi"])
    n = len(d["m"]) - 1
    s = {"ticker": d["ticker"], "as_of": d["m"][n], "price": d["p"][n],
         "ratio": fl["ratio"][n], "degraded": fl["degraded"][n], "floor": fl["mid"][n],
         "floor_lo": fl["lo"][n], "floor_hi": fl["hi"][n],
         "eps_ttm": d["e"][n], "pe_ttm": d["p"][n] / d["e"][n] if d["e"][n] and d["e"][n] > 0 else None,
         "check": d.get("check"), "periods": {k: decompose(d, k) for k in PERIODS}}
    if fwd and fwd.get("fwd_eps"):
        pe = d["p"][n] / fwd["fwd_eps"] if fwd["fwd_eps"] > 0 else None
        s["forward"] = {**fwd, "pe": pe,
                        "pe_lo": d["p"][n] / fwd["fwd_hi"] if fwd.get("fwd_hi") and fwd["fwd_hi"] > 0 else None,
                        "pe_hi": d["p"][n] / fwd["fwd_lo"] if fwd.get("fwd_lo") and fwd["fwd_lo"] > 0 else None,
                        "ratio": pe / MID if pe else None}
    return s


def usable(payload: dict | None) -> bool:
    """Un bénéfice que le contrôle croisé désavoue (certificat de dépôt ≠ une action, devise) ne s'affiche pas :
    un plancher faux d'un facteur 2 ou 5 se lirait comme une propriété du titre."""
    return bool(payload) and (payload.get("check") or {}).get("ok") is not False


def assemble(ticker: str, payload: dict, macro: dict) -> dict | None:
    """Aligne la série du titre (mois, cours brut, cours ajusté, état) sur l'inflation et le S&P 500."""
    idx = {m: i for i, m in enumerate(macro["m"])}
    keep = [i for i, m in enumerate(payload["m"]) if m in idx and payload["p"][i] and payload["tr"][i]]
    if len(keep) < 36:
        return None
    pick = lambda a: [a[i] for i in keep]  # noqa: E731
    m = pick(payload["m"])
    cpi = [macro["cpi"][idx[x]] for x in m]
    sp = [macro["sp"][idx[x]] for x in m]
    if any(c is None for c in cpi):
        return None
    return {"ticker": ticker, "m": m, "p": pick(payload["p"]), "tr": pick(payload["tr"]), "e": pick(payload["e"]),
            "cpi": cpi, "sp": sp, "check": payload.get("check")}


# ───────────────────────────── collecte ─────────────────────────────

def _get_json(url: str):
    for k in range(3):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=SEC_UA), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * k)
        except Exception:  # noqa: BLE001 — réseau : on retente, puis on abandonne CE titre
            time.sleep(2 + 3 * k)
    return None


def _monthly_last(s: pd.Series) -> pd.Series:
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")]
    out = s.groupby(s.index.to_period("M")).last()
    out.index = out.index.strftime("%Y-%m")
    return out


def _macro_sync() -> dict:
    import yfinance as yf
    raw = urllib.request.urlopen("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", timeout=30).read().decode()
    cpi = pd.read_csv(io.StringIO(raw))
    cpi.columns = ["d", "v"]
    # l'indice d'un mois n'est publié que le mois suivant
    cpi_m = pd.Series(cpi.v.astype(float).values, index=(pd.PeriodIndex(pd.to_datetime(cpi.d), freq="M") + 1).strftime("%Y-%m"))
    sp = yf.download("^SP500TR", start=START + "-01", auto_adjust=True, progress=False)["Close"].squeeze()
    spm = _monthly_last(sp)
    months = sorted(set(spm.index) | set(cpi_m.index))
    months = [x for x in months if x >= START]
    cpi_f = cpi_m.reindex(months).ffill()
    return {"m": months, "cpi": [None if v != v else float(v) for v in cpi_f.values],
            "sp": [None if v != v else float(v) for v in spm.reindex(months).values]}


def _fx_monthly(cur: str) -> pd.Series | None:
    import yfinance as yf
    try:
        s = yf.download(f"{cur}USD=X", start=START + "-01", auto_adjust=True, progress=False)["Close"].squeeze()
        return _monthly_last(s) if len(s) else None
    except Exception:  # noqa: BLE001
        return None


def _fx_at(fx: pd.Series, month: str) -> float:
    return float(fx[fx.index <= month].iloc[-1])


def _prices_sync(symbols: list[str]) -> dict:
    """Cours bruts (divisions ajustées, dividendes NON réintégrés), cours ajustés et divisions, mois par mois."""
    import yfinance as yf
    df = yf.download(symbols, start=START + "-01", auto_adjust=False, actions=True, progress=False,
                     group_by="ticker", threads=True, timeout=30)
    out = {}
    for s in symbols:
        try:
            sub = df[s] if getattr(df.columns, "nlevels", 1) == 2 else df
        except KeyError:
            continue
        if sub is None or sub["Close"].dropna().empty:
            continue
        splits = sub["Stock Splits"].fillna(0)
        splits = [(d.strftime("%Y-%m-%d"), float(v)) for d, v in splits[splits > 0].items()]
        p, tr = _monthly_last(sub["Close"]), _monthly_last(sub["Adj Close"])
        out[s] = {"p": p, "tr": tr.reindex(p.index), "splits": splits}
    return out


def _yahoo_sync(symbol: str) -> dict:
    import yfinance as yf
    tk = yf.Ticker(symbol)
    res: dict = {}
    try:
        ee = tk.earnings_estimate
        if ee is not None and "+1y" in ee.index:
            r = ee.loc["+1y"]
            res = {"fwd_eps": float(r["avg"]), "fwd_lo": float(r["low"]), "fwd_hi": float(r["high"]),
                   "n_analysts": int(r["numberOfAnalysts"]), "growth": float(r["growth"]),
                   "currency": str(r.get("currency") or "USD")}
            if "0y" in ee.index:
                res["cur_eps"] = float(ee.loc["0y", "avg"])
    except Exception:  # noqa: BLE001
        pass
    try:
        res["trailing_eps"] = tk.info.get("trailingEps")
    except Exception:  # noqa: BLE001
        pass
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in res.items()}


async def _published() -> list[str]:
    async with get_db_session() as conn:
        rd = await conn.fetchval("SELECT max(run_date) FROM nasdaq_indicators")
        return [r["ticker"] for r in await conn.fetch(
            "SELECT ticker FROM nasdaq_indicators WHERE run_date=$1 ORDER BY market_cap DESC NULLS LAST", rd)] if rd else []


async def refresh(tickers: list[str] | None = None) -> dict:
    """Recalcule tout pour les titres publiés : comptes SEC, cours bruts, PER à terme (photo du jour)."""
    if state["running"]:
        return {"status": "already_running"}
    state.update(running=True, error=None, done=0)
    loop = asyncio.get_running_loop()
    try:
        tickers = tickers or await _published()
        state["total"] = len(tickers)
        macro = await loop.run_in_executor(None, _macro_sync)
        async with get_db_session() as conn:
            await conn.execute(
                """INSERT INTO nasdaq_macro (series, payload, updated_at) VALUES ('valeur', $1, now())
                   ON CONFLICT (series) DO UPDATE SET payload=EXCLUDED.payload, updated_at=now()""", macro)
        ciks = await loop.run_in_executor(None, _get_json, "https://www.sec.gov/files/company_tickers.json")
        cik = {v["ticker"].upper(): v["cik_str"] for v in (ciks or {}).values()}
        from app.nasdaq.universe import yf_symbol
        fx_cache: dict = {}
        n_ok = 0
        for i in range(0, len(tickers), 20):
            chunk = tickers[i:i + 20]
            yfs = {t: yf_symbol(t) for t in chunk}
            prices = await loop.run_in_executor(None, _prices_sync, list(yfs.values()))
            for t in chunk:
                note = None
                payload = None
                try:
                    pr = prices.get(yfs[t])
                    c = cik.get(t.upper().replace(".", "-"))
                    facts = await loop.run_in_executor(None, _get_json, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c:010d}.json") if c else None
                    await asyncio.sleep(0.12)
                    yh = await loop.run_in_executor(None, _yahoo_sync, yfs[t])
                    ycur = yh.get("currency") or "USD"
                    if yh.get("fwd_eps") is not None and ycur != "USD":
                        if ycur not in fx_cache:
                            fx_cache[ycur] = await loop.run_in_executor(None, _fx_monthly, ycur)
                        fxy = fx_cache[ycur]
                        if fxy is not None and len(fxy):
                            rate = float(fxy.iloc[-1])
                            for k in ("fwd_eps", "fwd_lo", "fwd_hi", "cur_eps"):
                                if yh.get(k) is not None:
                                    yh[k] = yh[k] * rate
                            yh["currency"] = "USD"
                    if not pr:
                        note = "cours bruts indisponibles"
                    elif not facts:
                        note = "pas de comptes à la SEC"
                    else:
                        pts, unit = eps_points(facts)
                        ttm = ttm_points(adjust_splits(pts, pr["splits"]))
                        cur = (unit or "USD/shares").split("/")[0]
                        if not ttm:
                            note = "pas de bénéfice par action dans les comptes SEC"
                        else:
                            if cur != "USD":
                                if cur not in fx_cache:
                                    fx_cache[cur] = await loop.run_in_executor(None, _fx_monthly, cur)
                                fx = fx_cache[cur]
                                if fx is None:
                                    note = f"bénéfices en {cur}, change indisponible"
                                    ttm = []
                                else:
                                    ttm = [{**q, "ttm": q["ttm"] * _fx_at(fx, _month(q["end"]))} for q in ttm
                                           if _month(q["end"]) >= fx.index[0]]
                            months = list(pr["p"].index)
                            e = state_by_month(ttm, months)
                            ours = e[-1]
                            ref = yh.get("trailing_eps")
                            ok = bool(ours and ref and ref > 0 and ours > 0 and EPS_CHECK[0] <= ours / ref <= EPS_CHECK[1]) \
                                or bool(ours is not None and ref is not None and ours <= 0 and ref <= 0)
                            payload = {"m": months, "p": [float(x) for x in pr["p"].values],
                                       "tr": [None if x != x else float(x) for x in pr["tr"].values], "e": e,
                                       "check": {"ours": ours, "yahoo": ref, "ok": ok, "currency": cur}}
                            if not ok:
                                note = "bénéfice des 12 derniers mois incohérent avec Yahoo (certificat de dépôt, devise ou élément exceptionnel)"
                    async with get_db_session() as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """INSERT INTO nasdaq_valeur_series (ticker, payload, note, updated_at) VALUES ($1,$2,$3, now())
                                   ON CONFLICT (ticker) DO UPDATE SET payload=EXCLUDED.payload, note=EXCLUDED.note, updated_at=now()""",
                                t, payload, note)
                            if yh.get("fwd_eps") is not None:
                                last = await conn.fetchval("SELECT max(as_of) FROM nasdaq_forward WHERE ticker=$1", t)
                                today = date.today()
                                if last is None or (today - last).days >= 6:
                                    await conn.execute(
                                        """INSERT INTO nasdaq_forward (ticker, as_of, price, fwd_eps, fwd_lo, fwd_hi, n_analysts, cur_eps, growth, currency)
                                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT (ticker, as_of) DO NOTHING""",
                                        t, today, float(pr["p"].iloc[-1]) if pr else None, yh["fwd_eps"], yh.get("fwd_lo"),
                                        yh.get("fwd_hi"), yh.get("n_analysts"), yh.get("cur_eps"), yh.get("growth"), yh.get("currency"))
                    n_ok += payload is not None
                except Exception as ex:  # noqa: BLE001 — un titre raté n'arrête pas les autres
                    logger.exception("valeur %s", t)
                    note = f"échec {type(ex).__name__}"
                state["done"] += 1
            del prices
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        return {"status": "ok", "tickers": len(tickers), "with_data": n_ok}
    except Exception as ex:  # noqa: BLE001
        state["error"] = f"{type(ex).__name__}: {ex}"
        logger.exception("valeur.refresh")
        return {"status": "failed", "error": state["error"]}
    finally:
        state["running"] = False


# ───────────────────────────── lecture ─────────────────────────────

async def load(tickers: list[str] | None = None) -> tuple[dict, dict, dict, dict]:
    async with get_db_session() as conn:
        macro = await conn.fetchval("SELECT payload FROM nasdaq_macro WHERE series='valeur'")
        rows = await conn.fetch(
            "SELECT ticker, payload, note FROM nasdaq_valeur_series" + (" WHERE ticker = ANY($1::text[])" if tickers else ""),
            *([tickers] if tickers else []))
        fw = await conn.fetch(
            """SELECT DISTINCT ON (ticker) ticker, as_of, fwd_eps, fwd_lo, fwd_hi, n_analysts, growth, currency
               FROM nasdaq_forward ORDER BY ticker, as_of DESC""")
    if isinstance(macro, str):
        macro = json.loads(macro)
    series = {r["ticker"]: (json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"]) for r in rows}
    notes = {r["ticker"]: r["note"] for r in rows}
    fwd = {r["ticker"]: {**dict(r), "as_of": r["as_of"].isoformat()} for r in fw}
    return macro or {}, series, notes, fwd


def _fwd_usd(f: dict | None) -> dict | None:
    if not f or (f.get("currency") or "USD") != "USD":
        return None
    return f


async def read_summary(period: str = "10y") -> list[dict]:
    macro, series, notes, fwd = await load()
    if not macro:
        return []
    out = []
    for t, payload in series.items():
        item = {"ticker": t, "note": notes.get(t)}
        d = assemble(t, payload, macro) if usable(payload) else None
        if d:
            s = summary(d, _fwd_usd(fwd.get(t)))
            s["period"] = s.pop("periods")[period]
            item.update(s)
        out.append(item)
    return out


async def read_one(ticker: str, period: str = "10y") -> dict | None:
    macro, series, notes, fwd = await load([ticker])
    payload = series.get(ticker)
    if payload is None and ticker not in notes:
        return None
    item = {"ticker": ticker, "note": notes.get(ticker)}
    d = assemble(ticker, payload, macro) if usable(payload) and macro else None
    if not d:
        return item
    s = summary(d, _fwd_usd(fwd.get(ticker)))
    s["period"] = s.pop("periods")[period]
    fl = floor_series(d["e"], d["p"], d["cpi"])
    item.update(s)
    item["series"] = {"m": d["m"], "p": d["p"], **fl}
    item["cumul"] = cumulative(d, period)
    async with get_db_session() as conn:
        item["forward_history"] = [
            {"as_of": r["as_of"].isoformat(), "pe": (r["price"] / r["fwd_eps"]) if r["price"] and r["fwd_eps"] and r["fwd_eps"] > 0 else None,
             "n": r["n_analysts"]}
            for r in await conn.fetch("SELECT as_of, price, fwd_eps, n_analysts FROM nasdaq_forward WHERE ticker=$1 ORDER BY as_of", ticker)]
    return item
