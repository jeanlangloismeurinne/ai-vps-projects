"""Les deux indicateurs de la spec (fonctions pures, sans E/S)."""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

DAYS_PER_MONTH = 30.4375
ALERT_MONTHS = 12
SHORT_HISTORY_DAYS = 365
_EPOCH = date(1970, 1, 1)


def to_daynum(d: date) -> int:
    return (d - _EPOCH).days


def from_daynum(n: int) -> date:
    return _EPOCH + timedelta(days=int(n))


def clean_series(day_nums: np.ndarray, closes: np.ndarray, spike: float = 5.0):
    """Écarte les jours manquants, nuls et les pointes isolées (aberrations) ; l'ordre est conservé."""
    day_nums = np.asarray(day_nums, dtype=np.int64)
    closes = np.asarray(closes, dtype=np.float64)
    ok = np.isfinite(closes) & (closes > 0)
    day_nums, closes = day_nums[ok], closes[ok]
    if len(closes) >= 3:
        prev, cur, nxt = closes[:-2], closes[1:-1], closes[2:]
        up = (cur / prev > spike) & (cur / nxt > spike)
        down = (prev / cur > spike) & (nxt / cur > spike)
        bad = np.zeros(len(closes), dtype=bool)
        bad[1:-1] = up | down
        day_nums, closes = day_nums[~bad], closes[~bad]
    return day_nums, closes


@dataclass
class Indicators:
    price: float
    age_months: int | None
    is_atl: bool
    is_ath: bool
    multiple_10y: float | None
    lt_10y: bool
    short_history: bool


def age_in_days(day_nums: np.ndarray, closes: np.ndarray) -> tuple[int | None, bool, bool]:
    """(âge en jours, plus bas historique, plus haut historique) du dernier cours.

    Âge = temps écoulé depuis la PREMIÈRE date de l'histoire où le cours a touché le niveau P
    d'aujourd'hui (première clôture de l'autre côté de P, ou égale à P, par rapport au début de série).
    """
    n = len(closes)
    if n < 2:
        return 0, False, True
    p = closes[-1]
    prev = closes[:-1]
    first = prev[0]
    if first == p:
        idx = 0
    elif first < p:
        hits = np.flatnonzero(prev >= p)
        if hits.size == 0:
            return 0, False, True
        idx = int(hits[0])
    else:
        hits = np.flatnonzero(prev <= p)
        if hits.size == 0:
            return None, True, False
        idx = int(hits[0])
    return int(day_nums[-1] - day_nums[idx]), False, False


def compute(day_nums: np.ndarray, closes: np.ndarray) -> Indicators | None:
    day_nums, closes = clean_series(day_nums, closes)
    if len(closes) < 2:
        return None
    price = float(closes[-1])
    days, atl, ath = age_in_days(day_nums, closes)
    age = None if days is None else int(round(days / DAYS_PER_MONTH))

    multiple, lt10 = multiple_at(day_nums.tolist(), closes, len(closes) - 1)
    short = int(day_nums[-1] - day_nums[0]) < SHORT_HISTORY_DAYS
    return Indicators(price, age, atl, ath, multiple, lt10, short)


def multiple_at(days: list[int], closes: np.ndarray, i: int) -> tuple[float | None, bool]:
    """(multiple 10 ans, historique < 10 ans) à la séance d'indice i ; sans cours à -10 ans, base = première clôture."""
    today = from_daynum(days[i])
    try:
        target = today.replace(year=today.year - 10)
    except ValueError:  # 29 février
        target = today.replace(year=today.year - 10, day=28)
    j = bisect.bisect_right(days, to_daynum(target), 0, i + 1) - 1
    lt10 = j < 0
    base = float(closes[0] if lt10 else closes[j])
    return (float(closes[i]) / base if base > 0 else None), lt10


def series_tail(day_nums: np.ndarray, closes: np.ndarray, k: int) -> dict | None:
    """Les k dernières séances, chacune avec l'ancienneté et le multiple qu'elle aurait eus CE JOUR-LÀ.

    Même définition qu'`age_in_days`, vectorisée : la première date où le cours a touché le niveau de la séance t
    se lit par recherche dichotomique sur le maximum (ou minimum) cumulé. `a` = âge en jours (pour un plus bas
    historique : jours depuis le début de l'histoire) ; `l` = 1 si plus bas historique.
    """
    day_nums, closes = clean_series(day_nums, closes)
    n = len(closes)
    if n < 2:
        return None
    cmax = np.maximum.accumulate(closes)
    cmin = np.minimum.accumulate(closes)
    t = np.arange(max(1, n - k), n)
    p = closes[t]
    first = closes[0]
    idx_up = np.searchsorted(cmax, p, side="left")
    idx_dn = np.searchsorted(-cmin, -p, side="left")
    idx = np.where(p > first, idx_up, np.where(p < first, idx_dn, 0))
    ath = (p > first) & (idx >= t)
    atl = (p < first) & (idx >= t)
    ages = np.where(ath, 0, np.where(atl, day_nums[t] - day_nums[0], day_nums[t] - day_nums[np.minimum(idx, t)]))
    days = day_nums.tolist()
    mult = [multiple_at(days, closes, int(i))[0] for i in t]
    return {
        "d": day_nums[t].tolist(),
        "p": [round(float(x), 2) for x in p],
        "a": ages.astype(int).tolist(),
        "l": atl.astype(int).tolist(),
        "m": [None if m is None else round(m, 3) for m in mult],
    }
