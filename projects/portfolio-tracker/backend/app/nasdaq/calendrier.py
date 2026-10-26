"""Dernière séance NYSE/Nasdaq clôturée (jours fériés US inclus)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil.easter import easter

ET = ZoneInfo("America/New_York")
CLOSE_PLUS = time(16, 15)  # clôture 16h00 + marge pour que les cours finaux soient publiés


def _nth_weekday(y: int, m: int, wd: int, n: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(wd - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_monday(y: int, m: int) -> date:
    d = date(y, m + 1, 1) - timedelta(days=1)
    return d - timedelta(days=d.weekday())


def _observed(d: date) -> date | None:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def holidays(y: int) -> set[date]:
    h = {
        _nth_weekday(y, 1, 0, 3), _nth_weekday(y, 2, 0, 3), easter(y) - timedelta(days=2),
        _last_monday(y, 5), _nth_weekday(y, 9, 0, 1), _nth_weekday(y, 11, 3, 4),
    }
    for m, d in ((6, 19), (7, 4), (12, 25)):
        h.add(_observed(date(y, m, d)))
    ny = date(y, 1, 1)
    if ny.weekday() != 5:  # 1er janvier un samedi : la Bourse reste ouverte le vendredi 31/12
        h.add(_observed(ny))
    return h


def is_session(d: date) -> bool:
    return d.weekday() < 5 and d not in holidays(d.year)


def last_closed_session(now_utc: datetime) -> date:
    now = now_utc.astimezone(ET)
    d = now.date()
    if not (is_session(d) and now.time() >= CLOSE_PLUS):
        d -= timedelta(days=1)
    while not is_session(d):
        d -= timedelta(days=1)
    return d
