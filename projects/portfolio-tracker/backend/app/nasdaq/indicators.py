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

    On part de la veille : si elle est au-dessus de P, on remonte jusqu'à la dernière clôture ≤ P ;
    si elle est en dessous, jusqu'à la dernière clôture ≥ P. Veille égale à P : D = veille.
    """
    n = len(closes)
    if n < 2:
        return 0, False, True
    p = closes[-1]
    prev = closes[:-1]
    side = prev[-1] - p
    if side == 0:
        idx = n - 2
    elif side > 0:
        hits = np.flatnonzero(prev <= p)
        if hits.size == 0:
            return None, True, False
        idx = int(hits[-1])
    else:
        hits = np.flatnonzero(prev >= p)
        if hits.size == 0:
            return 0, False, True
        idx = int(hits[-1])
    return int(day_nums[-1] - day_nums[idx]), False, False


def compute(day_nums: np.ndarray, closes: np.ndarray) -> Indicators | None:
    day_nums, closes = clean_series(day_nums, closes)
    if len(closes) < 2:
        return None
    price = float(closes[-1])
    days, atl, ath = age_in_days(day_nums, closes)
    age = None if days is None else int(round(days / DAYS_PER_MONTH))

    today = from_daynum(day_nums[-1])
    try:
        target = today.replace(year=today.year - 10)
    except ValueError:  # 29 février
        target = today.replace(year=today.year - 10, day=28)
    tn = to_daynum(target)
    i = bisect.bisect_right(day_nums.tolist(), tn) - 1
    lt10 = i < 0
    base = float(closes[0] if lt10 else closes[i])
    multiple = price / base if base > 0 else None
    short = int(day_nums[-1] - day_nums[0]) < SHORT_HISTORY_DAYS
    return Indicators(price, age, atl, ath, multiple, lt10, short)
