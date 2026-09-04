"""
Récupération ciblée d'une line-item XBRL depuis EDGAR (data.sec.gov `companyconcept`).

Motif (00-REPRISE, étape `financials`) : la dimension MVDD `financials` exige un tier plancher **A**.
Or seul un fait EDGAR (`edgar_official`, tier A) peut fonder un champ à ce plancher — le quant
(yfinance/FMP, tier B+) ne le peut pas. Le seed NVDA porte déjà la plupart des postes (CA, résultat
net, cash-flow opérationnel, capitaux propres, dette, trésorerie…) mais **PAS le capex**, nécessaire à
`fcf_conversion_pct` (FCF = OCF − capex) et `intensite_capex_pct` (capex / CA). Plutôt que de fabriquer
ce chiffre ou d'aller le chercher au quant (ce qui casserait le tier A), on le **mesure à la source** :
l'API XBRL `companyconcept` d'EDGAR, qui rend l'historique d'un concept us-gaap pour un émetteur.

Discipline (conventions #24/#25/#28) :
  • Le concept est nommé explicitement (`PaymentsToAcquirePropertyPlantAndEquipment`) — pas d'inférence
    de source par un modèle ; la provenance est EDGAR, donc tier A à l'écriture.
  • Un échec réseau/absence lève `EdgarUnavailable` : l'appelant NE fabrique PAS le capex et laisse les
    champs qui en dépendent **non fondés** (un trou honnête vaut mieux qu'un chiffre inventé, #25).
  • Le CIK n'est pas deviné : il est **dérivé de l'URL EDGAR d'une entry déjà en base** (`/data/<cik>/`),
    donc de la provenance réelle du dépôt seedé — aucune table de correspondance à maintenir.

Aucune dépendance nouvelle : `httpx` (déjà utilisé par websearch) + stdlib.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# SEC impose un User-Agent identifiant (sinon 403) — cf. sec.gov/os/accessing-edgar-data.
_UA = "portfolio-tracker/2.0 (research contact plm@lm-associes.com)"
_COMPANYCONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{tag}.json"
# formes annuelles acceptées (un 10-K, éventuellement amendé). Les 10-Q sont trimestriels → écartés.
_ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}
_CIK_RE = re.compile(r"/data/(\d+)[/-]")


class EdgarUnavailable(Exception):
    """EDGAR n'a pas rendu le concept demandé (réseau, 403, concept absent). Distinct d'un zéro :
    l'appelant doit le remonter et laisser le champ non fondé, jamais fabriquer la valeur (#25)."""


def cik_from_url(url: Optional[str]) -> Optional[int]:
    """Extrait le CIK d'une URL EDGAR (`.../data/1045810/000104581026000021/...`). None si absent."""
    if not url:
        return None
    m = _CIK_RE.search(url)
    return int(m.group(1)) if m else None


def _parse_annual_points(payload: dict[str, Any], *, unit: str) -> list[dict[str, Any]]:
    """Extrait les points ANNUELS (un par exercice) de la réponse companyconcept.

    Dédoublonne par date de fin (`end`) : à `end` égal on préfère le 10-K originel au 10-K/A le plus
    récemment déposé (la valeur ré-affirmée dans un amendement reste la même ; on veut un seul point
    déterministe). Ne renvoie que les dépôts annuels (`_ANNUAL_FORMS`) marqués `fp='FY'`.
    """
    units = (payload.get("units") or {}).get(unit) or []
    by_end: dict[str, dict[str, Any]] = {}
    for it in units:
        if it.get("form") not in _ANNUAL_FORMS or it.get("fp") != "FY":
            continue
        end = it.get("end")
        val = it.get("val")
        if end is None or val is None:
            continue
        point = {
            "end": end,
            "val": float(val),
            "start": it.get("start"),
            "fy": it.get("fy"),
            "form": it.get("form"),
            "accn": it.get("accn"),
            "filed": it.get("filed"),
        }
        prev = by_end.get(end)
        # à end égal : garder le 10-K non amendé, sinon le déposé le plus tôt (déterministe)
        if prev is None or (prev["form"].endswith("/A") and not point["form"].endswith("/A")):
            by_end[end] = point
    return sorted(by_end.values(), key=lambda p: p["end"])


def _parse_instant_points(payload: dict[str, Any], *, unit: str) -> list[dict[str, Any]]:
    """Extrait les points INSTANTANÉS (postes de bilan) de la réponse companyconcept.

    Différence essentielle avec `_parse_annual_points` : **aucun filtre sur la forme du dépôt**. Un
    poste de bilan n'appartient pas à un exercice, il date d'un instant ; le restreindre aux 10-K
    rendait le socle aveugle à tout trimestre depuis le dernier annuel. Mesuré sur RVMD au
    2026-09-04 : bilan retenu au 2025-12-31 (trésorerie 383,7 M$, capitaux propres 1 631,3 M$,
    dette absente) alors que le 10-Q du 2026-06-30, public et déposé, porte 815,4 M$, 2 606,2 M$
    et **487,4 M$ d'obligations convertibles**. Rien ne signalait l'écart : le fait restait tier A,
    exact, et faux de fraîcheur.

    Un point instantané se reconnaît à l'ABSENCE de `start` (pas de durée). On ne se fie jamais à
    `fp` : EDGAR le rend incohérent sur les comparatifs (RVMD tague `fp=Q2` un point au 2026-03-31).
    À `end` égal, on préfère le dépôt annuel non amendé — le 10-K fait foi sur sa propre clôture,
    le comparatif d'un 10-Q ultérieur ne fait que la recopier.
    """
    units = (payload.get("units") or {}).get(unit) or []
    by_end: dict[str, dict[str, Any]] = {}
    for it in units:
        if it.get("start") is not None:      # flux : a une durée, ce n'est pas un poste de bilan
            continue
        end, val = it.get("end"), it.get("val")
        if end is None or val is None:
            continue
        point = {
            "end": end,
            "val": float(val),
            "start": None,
            "fy": it.get("fy"),
            "form": it.get("form"),
            "accn": it.get("accn"),
            "filed": it.get("filed"),
        }
        prev = by_end.get(end)
        if prev is None or _instant_rank(point) < _instant_rank(prev):
            by_end[end] = point
    return sorted(by_end.values(), key=lambda p: p["end"])


def _instant_rank(point: dict[str, Any]) -> tuple[int, str]:
    """Ordre de préférence à `end` égal : annuel non amendé, puis annuel amendé, puis le reste ;
    à égalité, le dépôt le plus ancien (déterministe, et c'est l'affirmation d'origine)."""
    form = point.get("form") or ""
    rank = 0 if form in _ANNUAL_FORMS and not form.endswith("/A") else (
        1 if form in _ANNUAL_FORMS else 2
    )
    return rank, str(point.get("filed") or "")


async def fetch_concept_instant(
    cik: int, tag: str, *, unit: str = "USD"
) -> list[dict[str, Any]]:
    """Historique INSTANTANÉ d'un concept de bilan. Lève `EdgarUnavailable` si indisponible.

    Même contrat d'erreur que `fetch_concept_annual` : une absence se remonte, elle ne se comble pas.
    """
    payload = await _companyconcept(cik, tag)
    points = _parse_instant_points(payload, unit=unit)
    if not points:
        raise EdgarUnavailable(
            f"aucun point instantané ({unit}) pour {tag} (CIK {cik})"
        )
    return points


def _pick_for_period(points: list[dict[str, Any]], period_end: Optional[date], *, tol_days: int = 20
                     ) -> Optional[dict[str, Any]]:
    """Point annuel dont la date de fin colle au `period_end` visé (tolérance : l'exercice fiscal ne
    tombe pas au jour près d'une année sur l'autre). À défaut de `period_end`, le plus récent."""
    if not points:
        return None
    if period_end is None:
        return points[-1]
    best, best_gap = None, None
    for p in points:
        try:
            gap = abs((date.fromisoformat(p["end"]) - period_end).days)
        except (TypeError, ValueError):
            continue
        if gap <= tol_days and (best_gap is None or gap < best_gap):
            best, best_gap = p, gap
    return best


async def _companyconcept(cik: int, tag: str) -> dict[str, Any]:
    """Réponse brute de `companyconcept` pour un concept us-gaap. Un échec lève `EdgarUnavailable`
    — jamais un dict vide, qui se lirait comme « l'émetteur ne déclare rien » (#25)."""
    url = _COMPANYCONCEPT.format(cik=cik, tag=tag)
    try:
        async with httpx.AsyncClient(
            timeout=settings.SEARCH_TIMEOUT_S, follow_redirects=True,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        ) as client:
            r = await client.get(url)
    except httpx.HTTPError as e:
        raise EdgarUnavailable(f"EDGAR injoignable pour {tag} (CIK {cik}) : {e}") from e
    if r.status_code == 404:
        raise EdgarUnavailable(f"concept {tag} absent pour CIK {cik} (404) — l'émetteur ne le déclare pas")
    if r.status_code != 200:
        raise EdgarUnavailable(f"EDGAR {r.status_code} pour {tag} (CIK {cik})")
    try:
        return r.json()
    except ValueError as e:
        raise EdgarUnavailable(f"réponse EDGAR non-JSON pour {tag} (CIK {cik}) : {e}") from e


async def fetch_concept_annual(
    cik: int, tag: str, *, unit: str = "USD"
) -> list[dict[str, Any]]:
    """Historique ANNUEL d'un concept us-gaap pour un émetteur. Lève `EdgarUnavailable` si indisponible.

    Retour : liste de points `{end, val, start, fy, form, accn, filed}` triés par `end` croissant.
    """
    payload = await _companyconcept(cik, tag)
    points = _parse_annual_points(payload, unit=unit)
    if not points:
        raise EdgarUnavailable(
            f"aucun point annuel ({'/'.join(sorted(_ANNUAL_FORMS))}, fp=FY, {unit}) pour {tag} (CIK {cik})"
        )
    return points


async def fetch_annual_value(
    cik: int, tag: str, *, period_end: Optional[date], unit: str = "USD"
) -> dict[str, Any]:
    """Valeur annuelle d'un concept pour l'exercice se terminant ~`period_end`. Lève si introuvable.

    Renvoie le point retenu (`{end, val, ...}`) — l'appelant en fait un fait EDGAR tier A."""
    points = await fetch_concept_annual(cik, tag, unit=unit)
    point = _pick_for_period(points, period_end)
    if point is None:
        ends = ", ".join(p["end"] for p in points[-4:])
        raise EdgarUnavailable(
            f"{tag} (CIK {cik}) : aucun exercice ne finit près de {period_end} (dispo : {ends})"
        )
    return point
