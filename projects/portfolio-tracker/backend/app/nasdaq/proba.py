"""Probabilité estimée que le cours dépasse son plus haut historique dans les 12 mois (252 séances).

Règle d'or : à l'instant t, on n'utilise que ce qui était connu à t.
  · les variables ne regardent que les séances ≤ t ;
  · le modèle de l'année Y est appris sur des observations dont les 12 mois de résultat étaient
    ÉCOULÉS au 1er janvier de Y (jamais une observation dont le résultat dépend de l'après-t).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone

import numpy as np

from app.nasdaq.indicators import clean_series, to_daynum

log = logging.getLogger("nasdaq.proba")

H = 252          # horizon : séances
STEP = 21        # une observation par mois
MIN_I = 252      # un an d'historique minimum
DPM = 30.4375
NAMES = ["dd", "tsath", "mom126", "mom252", "vol", "hist"]
LABELS = {
    "dd": "Distance au plus haut (cours ÷ plus haut)",
    "tsath": "Temps écoulé depuis le dernier plus haut",
    "mom126": "Évolution du cours sur 6 mois",
    "mom252": "Évolution du cours sur 12 mois",
    "vol": "Volatilité sur 12 mois",
    "hist": "Ancienneté de la cotation",
}
def get_db_session():
    from app.db.database import get_db_session as g  # import tardif : le calcul pur se teste sans base
    return g()


MIN_TRAIN, MIN_CLASS = 2000, 200

state = {"running": False, "step": "", "done": 0, "total": 0, "error": None}
_models_cache: dict = {"v": None, "models": None}


def features(day: np.ndarray, c: np.ndarray, cm: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Variables en chacun des indices `idx` (≥ MIN_I) — ne lisent que les séances ≤ idx."""
    m = len(c)
    lastath = np.maximum.accumulate(np.where(c >= cm, np.arange(m), 0))
    lr = np.diff(np.log(c), prepend=np.log(c[0]))
    cl = np.concatenate([[0.0], np.cumsum(lr)])
    cl2 = np.concatenate([[0.0], np.cumsum(lr * lr)])
    mu = (cl[idx + 1] - cl[idx + 1 - 252]) / 252
    var = (cl2[idx + 1] - cl2[idx + 1 - 252]) / 252 - mu * mu
    return np.column_stack([
        np.log(c[idx] / cm[idx]),
        np.log1p((day[idx] - day[lastath[idx]]) / DPM),
        np.log1p(np.maximum(c[idx] / c[idx - 126] - 1, -0.95)),
        np.log1p(np.maximum(c[idx] / c[idx - 252] - 1, -0.95)),
        np.sqrt(np.maximum(var, 0) * 252),
        np.log(np.maximum(day[idx] - day[0], 365) / 365.25),
    ])


def outcomes(cm: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """1 = nouveau plus haut dans les 252 séances suivantes ; 0 = non (fenêtre complète) ; -1 = pas encore écoulée."""
    m = len(cm)
    j = np.searchsorted(cm, cm[idx], side="right")   # première séance dont le plus haut cumulé dépasse celui de t
    hit = (j < m) & (j <= idx + H)
    return np.where(hit, 1, np.where(idx + H <= m - 1, 0, -1)).astype(int)


def prep(day_nums, closes):
    day, c = clean_series(day_nums, closes)
    if len(c) <= MIN_I + 1:
        return None
    return day, c, np.maximum.accumulate(c)


def training_samples(day_nums, closes):
    """(jour de l'observation, jour où son résultat est connu, variables, résultat) — fenêtres complètes seulement."""
    p = prep(day_nums, closes)
    if p is None:
        return None
    day, c, cm = p
    m = len(c)
    idx = np.arange(MIN_I, m - H, STEP)
    if len(idx) == 0:
        return None
    return day[idx], day[idx + H], features(day, c, cm, idx), outcomes(cm, idx)


def fit_logit(X: np.ndarray, y: np.ndarray, lam: float = 1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    R = lam * np.eye(Z.shape[1]); R[0, 0] = 0
    for _ in range(40):
        p = 1 / (1 + np.exp(-np.clip(Z @ w, -30, 30)))
        step = np.linalg.solve((Z * (p * (1 - p))[:, None]).T @ Z + R, Z.T @ (p - y) + R @ w)
        w -= step
        if np.abs(step).max() < 1e-9:
            break
    return mu, sd, w


def predict(model, X: np.ndarray) -> np.ndarray:
    mu, sd, w = model
    return 1 / (1 + np.exp(-np.clip(w[0] + ((X - mu) / sd) @ w[1:], -30, 30)))


def _year_of(day: np.ndarray) -> np.ndarray:
    return day.astype("datetime64[D]").astype("datetime64[Y]").astype(int) + 1970


def pick_models(models: dict, years: np.ndarray):
    """Pour chaque année de point, le modèle de fit_year le plus grand ≤ année (None si aucun)."""
    ys = sorted(models)
    out = []
    for y in years:
        ok = [k for k in ys if k <= y]
        out.append(ok[-1] if ok else None)
    return out


def curve(day_nums, closes, models: dict, years: float | None = 5, step: int = STEP) -> dict | None:
    """Courbe mensuelle ancrée sur la dernière séance. p = probabilité à la date ; o = 1 atteint / 0 manqué / None en cours."""
    pr = prep(day_nums, closes)
    if pr is None or not models:
        return None
    day, c, cm = pr
    m = len(c)
    idx = np.arange(m - 1, MIN_I - 1, -step)[::-1]
    if years is not None:
        idx = idx[day[idx] >= day[-1] - years * 365.25]
    if len(idx) == 0:
        return None
    X = features(day, c, cm, idx)
    use = pick_models(models, _year_of(day[idx]))
    p = np.full(len(idx), np.nan)
    for k in set(u for u in use if u is not None):
        sel = np.array([u == k for u in use])
        p[sel] = predict(models[k], X[sel])
    o = outcomes(cm, idx)
    keep = ~np.isnan(p)
    if not keep.any():
        return None
    return {
        "d": day[idx][keep].tolist(),
        "p": [round(float(v), 3) for v in p[keep]],
        "o": [None if v < 0 else int(v) for v in o[keep]],
        "dd": [round(float(v), 3) for v in np.exp(X[keep, 0])],
        "model_year": [u for u, kk in zip(use, keep) if kk][-1],
    }


async def load_models() -> dict:
    async with get_db_session() as conn:
        rows = await conn.fetch("SELECT fit_year, mu, sd, coef, fitted_at FROM nasdaq_proba_model ORDER BY fit_year")
    ver = tuple((r["fit_year"], r["fitted_at"]) for r in rows)
    if _models_cache["v"] == ver and _models_cache["models"] is not None:
        return _models_cache["models"]
    models = {r["fit_year"]: (np.array(r["mu"]), np.array(r["sd"]), np.array(r["coef"])) for r in rows}
    _models_cache.update(v=ver, models=models)
    return models


def _auc(y: np.ndarray, s: np.ndarray) -> float:
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(1, len(s) + 1)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def evaluate(day, day_end, X, y, models: dict) -> dict:
    """Qualité hors échantillon : chaque observation est notée par le modèle de SON année (appris avant elle)."""
    yr = _year_of(day)
    p = np.full(len(y), np.nan)
    use = pick_models(models, yr)
    for k in set(u for u in use if u is not None):
        sel = np.array([u == k for u in use])
        p[sel] = predict(models[k], X[sel])
    ok = ~np.isnan(p)
    p, yy, yr = p[ok], y[ok], yr[ok]
    buckets = []
    for lo in np.arange(0, 1, 0.1):
        m = (p >= lo) & (p < lo + 0.1 + (1e-9 if lo > 0.85 else 0))
        if m.sum() >= 30:
            buckets.append({"lo": round(float(lo), 1), "n": int(m.sum()), "pred": round(float(p[m].mean()), 3), "real": round(float(yy[m].mean()), 3)})
    thresholds = []
    for s in np.arange(0.1, 0.91, 0.1):
        m = p >= s
        if m.sum() >= 30:
            thresholds.append({"s": round(float(s), 1), "n": int(m.sum()), "hit": round(float(yy[m].mean()), 3), "share": round(float(m.mean()), 3)})
    years = [{"y": int(a), "n": int((yr == a).sum()), "pred": round(float(p[yr == a].mean()), 3), "real": round(float(yy[yr == a].mean()), 3)}
             for a in sorted(set(yr.tolist())) if (yr == a).sum() >= 100]
    return {"n": int(len(p)), "base_rate": round(float(yy.mean()), 3), "auc": round(_auc(yy, p), 3),
            "buckets": buckets, "thresholds": thresholds, "years": years}


async def fit_all() -> dict:
    """Relit tous les cours, apprend un modèle par année, mesure la qualité hors échantillon, persiste."""
    state.update(running=True, step="lecture des cours", done=0, total=0, error=None)
    try:
        async with get_db_session() as conn:
            tk = [r[0] for r in await conn.fetch("SELECT ticker FROM nasdaq_prices")]
        state["total"] = len(tk)
        parts = []
        for k, t in enumerate(tk):
            async with get_db_session() as conn:
                r = await conn.fetchrow("SELECT day_nums, closes FROM nasdaq_prices WHERE ticker=$1", t)
            s = training_samples(np.array(r["day_nums"], dtype=np.int64), np.array(r["closes"], dtype=np.float64))
            if s:
                parts.append(s)
            state["done"] = k + 1
            if k % 25 == 0:
                await asyncio.sleep(0)
        day = np.concatenate([p[0] for p in parts]); day_end = np.concatenate([p[1] for p in parts])
        X = np.concatenate([p[2] for p in parts]); y = np.concatenate([p[3] for p in parts])
        state["step"] = "apprentissage"
        models, meta = {}, {}
        for Y in range(int(_year_of(np.array([day.min()]))[0]) + 1, date.today().year + 1):
            cutoff = to_daynum(date(Y, 1, 1))
            tr = day_end <= cutoff
            n_pos = int(y[tr].sum()); n = int(tr.sum())
            if n < MIN_TRAIN or n_pos < MIN_CLASS or n - n_pos < MIN_CLASS:
                continue
            assert (day_end[tr] <= cutoff).all()
            models[Y] = fit_logit(X[tr], y[tr].astype(float))
            meta[Y] = (cutoff, n, n_pos)
        if not models:
            raise RuntimeError("Pas assez d'observations pour apprendre un modèle.")
        state["step"] = "évaluation"
        ev = evaluate(day, day_end, X, y, models)
        last = max(models)
        mu, sd, w = models[last]
        ev["model_year"] = last
        ev["first_year"] = min(models)
        ev["n_models"] = len(models)
        ev["coefficients"] = [{"name": nm, "label": LABELS[nm], "coef": round(float(c), 3)} for nm, c in zip(NAMES, w[1:])]
        ev["intercept"] = round(float(w[0]), 3)
        ev["n_tickers"] = len(parts)
        ev["computed_at"] = datetime.now(timezone.utc).isoformat()
        async with get_db_session() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM nasdaq_proba_model")
                for Y, (mu_, sd_, w_) in models.items():
                    cutoff, n, n_pos = meta[Y]
                    await conn.execute(
                        "INSERT INTO nasdaq_proba_model (fit_year, cutoff_day, n_train, n_pos, mu, sd, coef) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                        Y, cutoff, n, n_pos, mu_.tolist(), sd_.tolist(), w_.tolist())
                await conn.execute(
                    """INSERT INTO nasdaq_proba_calib (id, computed_at, payload) VALUES (1, now(), $1)
                       ON CONFLICT (id) DO UPDATE SET computed_at = now(), payload = EXCLUDED.payload""", ev)
        _models_cache.update(v=None, models=None)
        log.info("nasdaq.proba : %d modèles (%s→%s), AUC hors échantillon %.3f", len(models), min(models), last, ev["auc"])
        return ev
    except Exception as e:  # noqa: BLE001
        state["error"] = f"{type(e).__name__}: {e}"
        log.exception("nasdaq.proba : échec de l'apprentissage")
        raise
    finally:
        state.update(running=False, step="")


async def ensure_models() -> None:
    """Réapprend si aucun modèle n'existe pour l'année en cours (au plus une fois par an)."""
    if state["running"]:
        return
    async with get_db_session() as conn:
        have = await conn.fetchval("SELECT max(fit_year) FROM nasdaq_proba_model")
    if have is None or have < date.today().year:
        await fit_all()
