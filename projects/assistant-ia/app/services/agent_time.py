"""Fuseau horaire de l'utilisateur — un seul endroit (#1787579840500 b).

Le scheduler tourne en UTC (`app/main.py`) et la base stocke des `TIMESTAMPTZ`. Rien n'imposait
jusqu'ici le fuseau *de l'utilisateur* : « demain 9h » était ambigu et serait tombé à 11h en heure
d'été. Ce module est le seul endroit qui connaît `AGENT_TIMEZONE`, pour que résolution et
affichage ne puissent pas diverger.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings

# Repli sur UTC plutôt qu'une exception au démarrage : un fuseau mal orthographié ne doit pas
# empêcher l'app de démarrer, mais doit se voir dans les dates affichées.
try:
    TZ = ZoneInfo(settings.AGENT_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):  # pragma: no cover — dépend de la conf
    TZ = ZoneInfo("UTC")


def now_local() -> datetime:
    """`now` dans le fuseau de l'utilisateur, aware. Toujours fourni par le code, jamais deviné
    par le modèle (roadmap agent-outillage §2.3)."""
    return datetime.now(TZ)


def to_local(dt: datetime) -> datetime:
    """Convertit un datetime dans le fuseau utilisateur. Un datetime naïf est réputé UTC —
    c'est ce que produit asyncpg pour une colonne sans fuseau et ce que fait le scheduler."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)


_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def format_local(dt: datetime) -> str:
    """Date lisible en français, dans le fuseau utilisateur : « mardi 26 août à 09:00 ».

    C'est cette chaîne que voit l'utilisateur dans la confirmation d'un rappel. Afficher la date
    *résolue* est la partie qui compte : c'est ce qui rend une mauvaise interprétation
    (« mardi » = lequel ?) immédiatement visible (roadmap §3.2).
    """
    d = to_local(dt)
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} à {d:%H:%M}"
