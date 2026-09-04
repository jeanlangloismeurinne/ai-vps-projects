"""
Alimentation du SOCLE EDGAR : les postes comptables bruts d'un émetteur → entries `fact_financial`
tier A, mesurées à la source (API XBRL `companyconcept` de data.sec.gov).

Motif (trouvé le 2026-08-30 en préparant le second ticker) : `financials_feed` DÉRIVE ses 4 ratios
de faits `fact_financial` EDGAR **déjà en base**, et `edgar_facts.cik_from_url()` déduit le CIK de
l'URL EDGAR **d'une entry déjà en base**. Or ces faits de base n'existaient que pour NVDA, par un
**seed écrit à la main** (`db/seeds/nvda_v2_knowledge_seed.sql`) — aucun chemin de code ne les
produisait. Conséquence mesurée : pour tout autre ticker, `extract_edgar_facts()` rend un dict vide,
les 4 ratios restent non fondés, la dimension `financials` (bloc structuré, plancher **tier A**) ne
peut pas passer, donc la readiness ne peut jamais atteindre `ready` et la chaîne d'analyse est
inatteignable (`_load_ready_context()` lève `NotReadyError`). Ce module ferme ce trou.

Discipline (conventions #24/#25/#28) :
  • **Aucun chiffre n'est fabriqué ni emprunté au quant.** Chaque poste est un point XBRL mesuré chez
    EDGAR, avec son concept, son accession et sa forme dans `content_structured` → provenance EDGAR,
    donc `edgar_official` / tier A à l'écriture. C'est la seule source qui satisfait le plancher A.
  • Un poste introuvable reste **absent** (jamais zéro, jamais estimé) : il est reporté dans
    `unfounded` et les ratios qui en dépendent resteront non fondés en aval (#25).
  • Le CIK n'est plus deviné ni dérivé d'une entry pré-existante : il est **résolu depuis le symbole**
    via le registre officiel `company_tickers.json` de la SEC. C'est ce qui rend le feed amorçable
    sur un ticker au corpus vide — l'amorçage était précisément ce qui manquait.
  • L'`source_url` écrite pointe le dépôt réel (`/Archives/edgar/data/<cik>/<accn>/…-index.htm`),
    reconstruite depuis l'accession du point retenu. Elle porte donc `/data/<cik>/`, ce qui **recâble
    au passage `cik_from_url()`** pour les consommateurs en aval (capex de `financials_feed`).

⚠️ **Le tag XBRL ne se choisit pas par convention, il se choisit par FRAÎCHEUR** (mesuré contre
l'API réelle le 2026-08-30). Un concept peut répondre HTTP 200 avec un historique **périmé de
15 ans** — le 00-REPRISE ne notait le cas que pour le capex de NVDA, c'est en fait la règle générale :

    MSFT  `Revenues`                                    → dernier point 2010-06-30  ⚠️
    MSFT  `RevenueFromContractWithCustomerExcluding…`    → dernier point 2026-06-30  ✅
    NVDA  `PaymentsToAcquirePropertyPlantAndEquipment`   → dernier point 2012-01-29  ⚠️
    NVDA  `PaymentsToAcquireProductiveAssets`            → dernier point 2026-01-25  ✅

Chaque poste porte donc une LISTE de concepts candidats, et un candidat n'est retenu que s'il a un
point **près de la date d'ancrage** (`_pick_for_period`, tolérance 20 j). Prendre « le premier tag
qui répond » donnerait un CA de 2010 présenté comme le CA courant — un faux tier A, le pire mode de
panne pour ce projet.

Aucune dépendance nouvelle : `httpx` (déjà utilisé) + stdlib.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from datetime import date
from typing import Any, Optional

import httpx

from app.config import settings
from app.db.database import get_db_session
from app.knowledge.edgar_facts import (
    EdgarUnavailable, _UA, fetch_concept_annual, fetch_concept_instant, _pick_for_period,
)
from app.knowledge.service import store_knowledge

logger = logging.getLogger(__name__)

_SOURCE_TYPE = "edgar_official"
_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
# Dépôt EDGAR d'où provient le point retenu (porte `/data/<cik>/` → `cik_from_url` la relit).
_FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{accn}-index.htm"

# Un exercice annuel dure ~365 j. Filet contre un point `fp=FY` qui serait en fait un trimestre :
# le prendre pour un flux annuel donnerait un CA ~4× trop faible, sans aucun signal d'erreur.
_ANNUAL_MIN_DAYS, _ANNUAL_MAX_DAYS = 300, 400

# Devises tentées dans l'ordre (un 20-F peut publier hors USD).
_UNITS = ("USD", "EUR", "GBP", "DKK", "SEK", "CHF")


class EdgarFeedUnavailable(Exception):
    """Le socle EDGAR n'est pas constructible (ticker sans symbole, CIK introuvable, EDGAR muet).
    Distinct d'une couverture partielle : l'appelant DOIT le remonter (#25)."""


@dataclass
class Poste:
    """Un poste comptable : son nom interne (`metric`, lu par `financials_feed._SIMPLE_METRICS`),
    ses concepts XBRL candidats **par ordre de préférence à fraîcheur égale**, et ses tags."""
    metric: str
    concepts: list[str]
    tags: list[str]
    label: str
    flow: bool                      # True = flux (a une durée à valider) · False = poste de bilan
    composite_with: Optional[str] = None   # 2ᵉ concept d'un poste composite (cash_and_lt_debt)
    composite_concepts: list[str] = dc_field(default_factory=list)


# L'ordre des concepts n'arbitre qu'à fraîcheur ÉGALE (la fraîcheur prime — cf. docstring).
# `RevenueFromContractWithCustomerExcludingAssessedTax` d'abord : c'est le concept ASC 606, en
# vigueur depuis 2018 ; `Revenues` est l'ancien, encore utilisé par certains émetteurs.
POSTES: list[Poste] = [
    Poste("stockholders_equity",
          ["StockholdersEquity",
           "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
          ["financials", "balance_sheet", "edgar"], "Capitaux propres", flow=False),
    Poste("revenue",
          ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
           "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
          ["financials", "revenue", "edgar"], "Chiffre d'affaires", flow=True),
    Poste("net_income",
          ["NetIncomeLoss", "ProfitLoss"],
          ["financials", "profitability", "edgar"], "Résultat net", flow=True),
    Poste("gross_profit",
          ["GrossProfit"],
          ["financials", "margins", "edgar"], "Marge brute", flow=True),
    Poste("operating_cash_flow",
          ["NetCashProvidedByUsedInOperatingActivities",
           "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
          ["financials", "cash_flow", "edgar"], "Cash-flow opérationnel", flow=True),
    Poste("total_assets",
          ["Assets"],
          ["financials", "balance_sheet", "edgar"], "Total actif", flow=False),
    Poste("capital_expenditure",
          ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
          ["financials", "capex", "edgar"], "Capex", flow=True),
    Poste("cash_and_lt_debt",
          ["CashAndCashEquivalentsAtCarryingValue"],
          ["financials", "balance_sheet", "leverage", "edgar"], "Trésorerie et dette long terme",
          flow=False,
          composite_with="long_term_debt",
          # ⚠️ Cette liste décrit une FAMILLE de financements, pas un concept canonique. Elle ne
          # portait que le prêt à terme — le mode de financement des sociétés matures. Un émetteur
          # en développement se finance en OBLIGATIONS CONVERTIBLES : RVMD dépose
          # `ConvertibleLongTermNotesPayable` (487,4 M$ au 2026-06-30) et AUCUN des deux premiers.
          # Le manque ne se voyait pas comme une erreur, seulement comme un poste non fondé — et
          # « inférer zéro » aurait publié « aucune dette, trésorerie nette » sur 487 M$ de dette,
          # en inversant le signe de la dette nette. C'est #30 transposé : le concept se choisit sur
          # ce que l'émetteur DÉPOSE, jamais sur ce que sa catégorie est censée déposer.
          composite_concepts=["LongTermDebtNoncurrent", "LongTermDebt",
                              "ConvertibleLongTermNotesPayable", "ConvertibleDebtNoncurrent",
                              "ConvertibleNotesPayableNoncurrent"]),
]

# Le poste qui fixe la date d'ancrage : tous les autres sont pris au MÊME exercice (jamais mélangés).
_ANCHOR_METRIC = "stockholders_equity"


# ─────────────────────────────── partie PURE (testable hors ligne) ───────────────────────────────

def is_annual_flow(point: dict[str, Any]) -> bool:
    """Un point de flux couvre-t-il bien un exercice ? Un `fp=FY` déposé en 10-K peut porter un
    trimestre ; le retenir comme flux annuel diviserait le CA par ~4 **sans erreur visible**."""
    start, end = point.get("start"), point.get("end")
    if not start or not end:
        return False
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    except (TypeError, ValueError):
        return False
    return _ANNUAL_MIN_DAYS <= days <= _ANNUAL_MAX_DAYS


def select_concept(
    points_by_concept: dict[str, list[dict[str, Any]]], period_end: Optional[date], *, flow: bool
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Choisit le concept XBRL dont l'historique atteint réellement `period_end`, et le point retenu.

    C'est ICI que se joue la correction du piège documenté en tête : un concept périmé (dernier point
    2010) n'a aucun point près de l'ancrage → `_pick_for_period` rend None → on passe au suivant.
    À fraîcheur égale, l'ordre de `Poste.concepts` tranche. Pur : aucune IO.
    """
    for concept in points_by_concept:
        point = _pick_for_period(points_by_concept[concept] or [], period_end)
        if point is None:
            continue
        if flow and not is_annual_flow(point):
            continue
        return concept, point
    return None, None


def filing_url(cik: int, accn: Optional[str]) -> Optional[str]:
    """URL du dépôt d'où sort le point. Porte `/data/<cik>/` → relisible par `cik_from_url()`."""
    if not accn:
        return None
    return _FILING_URL.format(cik=cik, accn_nodash=accn.replace("-", ""), accn=accn)


def _md(v: Optional[float]) -> str:
    if v is None:
        return "n/d"
    return f"{v/1e9:.2f}".replace(".", ",") + " Md"


def fiscal_label(point: dict[str, Any]) -> Optional[str]:
    """`FY2026`. Préfère le `fy` déclaré par EDGAR, sinon l'année de la date de clôture."""
    fy = point.get("fy")
    if isinstance(fy, int):
        return f"FY{fy}"
    end = point.get("end")
    if isinstance(end, str) and len(end) >= 4:
        return f"FY{end[:4]}"
    return None


@dataclass
class EdgarEntrySpec:
    metric: str
    title: str
    content: str
    content_structured: dict[str, Any]
    tags: list[str]
    source_url: Optional[str]
    period_end: date
    fiscal_period: Optional[str]


def build_edgar_entries(
    ticker_id: str, symbol: str, cik: int, resolved: dict[str, dict[str, Any]],
    *, fiscal_end: Optional[date] = None,
) -> tuple[list[EdgarEntrySpec], list[dict[str, str]]]:
    """`resolved` (metric → {concept, point, unit, …}) → specs d'entries. Pur, sans IO ni DB.

    Un poste absent de `resolved` n'est PAS inventé : il ressort dans `unfounded` avec son motif.
    Le format de `content_structured` reproduit celui du seed NVDA — c'est le contrat de lecture de
    `financials_feed.extract_edgar_facts()` (clés `metric`, `value`, `currency`, `period`,
    `period_end`, et `cash`/`long_term_debt` pour le poste composite).
    """
    specs: list[EdgarEntrySpec] = []
    unfounded: list[dict[str, str]] = []

    for poste in POSTES:
        got = resolved.get(poste.metric)
        if got is None:
            unfounded.append({"metric": poste.metric, "reason": "aucun concept XBRL exploitable"})
            continue
        point, concept, unit = got["point"], got["concept"], got["unit"]
        period_end = date.fromisoformat(point["end"])
        # Un flux porte un libellé d'exercice (`FY2025`) ; un poste de bilan porte une DATE, parce
        # qu'il n'appartient à aucun exercice. Le libellé n'est jamais tiré de `fp`, incohérent sur
        # les comparatifs de 10-Q (RVMD tague `fp=Q2` un point au 2026-03-31).
        period = fiscal_label(point) if poste.flow else f"AU {point['end']}"
        # `datation` nomme ce que la date VEUT dire ; sans lui, un consommateur devrait deviner la
        # nature du poste depuis une liste de `metric` en dur — exactement le genre de convention
        # tacite que #30 proscrit.
        datation = "exercice clos le" if poste.flow else "bilan au"
        url = filing_url(cik, point.get("accn"))

        structured: dict[str, Any] = {
            "metric": poste.metric,
            "currency": unit,
            "period": period,
            "period_end": point["end"],
            "poste_kind": "flow" if poste.flow else "stock",
            "xbrl_tag": f"us-gaap:{concept}",
            "accn": point.get("accn"),
            "form": point.get("form"),
        }
        # Un bilan plus récent que la clôture annuelle est le cas NORMAL dès qu'un 10-Q est déposé.
        # On l'écrit dans le fait pour que l'écart soit lisible en aval au lieu d'être supposé nul.
        if not poste.flow and fiscal_end is not None:
            structured["fiscal_end"] = fiscal_end.isoformat()
            structured["jours_apres_cloture"] = (period_end - fiscal_end).days

        if poste.composite_with:
            second = got.get("second")
            structured["cash"] = point["val"]
            if second is None:
                # Le second concept manque. On ne perd PAS le premier pour autant : la trésorerie
                # est déposée, sourcée, tier A — la jeter parce que son co-poste manque faisait
                # tomber `levier` ET `roic_pct` d'un émetteur dont le ROIC (−90,7 % chez RVMD) est
                # précisément le fait central. Mais on n'écrit pas zéro non plus : `long_term_debt`
                # reste None et le texte dit « non déterminée », pas « nulle ». Confondre les deux
                # inverse le signe de la dette nette (#32 : un trou de la table n'est pas un trou
                # du monde ; et son inverse — un trou du monde n'est pas un zéro).
                structured[poste.composite_with] = None
                structured["long_term_debt_status"] = "aucun_concept_depose"
                unfounded.append({
                    "metric": poste.metric,
                    "reason": (f"{poste.composite_with} : aucun des concepts candidats n'est déposé "
                               f"— trésorerie publiée seule, dette NON DÉTERMINÉE (pas nulle)"),
                })
                content = (
                    f"{poste.label} de {ticker_id} ({symbol}) — {datation} {point['end']} : "
                    f"trésorerie {_md(point['val'])}{unit}. Dette long terme **non déterminée** : "
                    f"aucun des concepts XBRL candidats n'est déposé par cet émetteur. "
                    f"⚠️ Absence de dépôt ≠ absence de dette — ne pas lire ce poste comme une "
                    f"position sans dette, et ne pas en dériver de dette nette. "
                    f"Source : {point.get('form', '10-K')} EDGAR, concept XBRL us-gaap:{concept} "
                    f"(accession {point.get('accn')})."
                )
            else:
                structured[poste.composite_with] = second["point"]["val"]
                structured["xbrl_tag_2"] = f"us-gaap:{second['concept']}"
                content = (
                    f"{poste.label} de {ticker_id} ({symbol}) — {datation} {point['end']} : "
                    f"trésorerie {_md(point['val'])}{unit}, dette long terme "
                    f"{_md(second['point']['val'])}{unit}. Source : {point.get('form', '10-K')} EDGAR, "
                    f"concepts XBRL us-gaap:{concept} et us-gaap:{second['concept']} "
                    f"(accession {point.get('accn')})."
                )
        else:
            structured["value"] = point["val"]
            content = (
                f"{poste.label} de {ticker_id} ({symbol}) — {datation} {point['end']} : "
                f"{_md(point['val'])}{unit}. Source : {point.get('form', '10-K')} EDGAR, concept "
                f"XBRL us-gaap:{concept} (accession {point.get('accn')})."
            )

        specs.append(EdgarEntrySpec(
            metric=poste.metric,
            title=f"{poste.label} {period or point['end']} ({symbol})",
            content=content, content_structured=structured, tags=list(poste.tags),
            source_url=url, period_end=period_end, fiscal_period=period,
        ))

    return specs, unfounded


# ─────────────────────────────────────── couche IO ───────────────────────────────────────────────

_cik_cache: dict[str, int] = {}


async def resolve_cik(symbol: str) -> int:
    """Symbole boursier → CIK, via le registre officiel `company_tickers.json` de la SEC.

    C'est la brique d'AMORÇAGE : sans elle, le CIK ne pouvait venir que de l'URL d'une entry EDGAR
    déjà en base, ce qui rendait le socle inamorçable sur un corpus vide (le seed NVDA masquait le
    problème). Mémoïsé par processus — le registre est un fichier de ~800 Ko qui bouge peu.
    """
    key = symbol.upper()
    if key in _cik_cache:
        return _cik_cache[key]
    try:
        async with httpx.AsyncClient(
            timeout=settings.SEARCH_TIMEOUT_S, follow_redirects=True,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        ) as client:
            r = await client.get(_COMPANY_TICKERS)
    except httpx.HTTPError as e:
        raise EdgarFeedUnavailable(f"registre SEC injoignable : {e}") from e
    if r.status_code != 200:
        raise EdgarFeedUnavailable(f"registre SEC HTTP {r.status_code}")
    try:
        payload = r.json()
    except ValueError as e:
        raise EdgarFeedUnavailable(f"registre SEC non-JSON : {e}") from e

    for rec in (payload or {}).values():
        t = (rec or {}).get("ticker")
        cik = (rec or {}).get("cik_str")
        if t and cik is not None:
            _cik_cache[str(t).upper()] = int(cik)
    if key not in _cik_cache:
        raise EdgarFeedUnavailable(
            f"symbole {symbol} absent du registre SEC — émetteur non déposant EDGAR "
            f"(place hors US ?) ; fonder `financials` depuis des documents uploadés"
        )
    return _cik_cache[key]


async def _points_for(
    cik: int, concepts: list[str], *, flow: bool
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Historique de chaque concept candidat. Un concept absent (404) est simplement ignoré :
    c'est le cas NOMINAL (les émetteurs ne déclarent pas tous les mêmes concepts).

    `flow=True` → points annuels (10-K/20-F, `fp=FY`) : un flux appartient à un exercice.
    `flow=False` → points instantanés, toutes formes : un poste de BILAN date d'un instant, et le
    dernier instant publié vaut mieux que la dernière clôture annuelle (cf. `_parse_instant_points`).
    """
    fetch = fetch_concept_annual if flow else fetch_concept_instant
    out: dict[str, list[dict[str, Any]]] = {}
    unit_used = _UNITS[0]
    for concept in concepts:
        for unit in _UNITS:
            try:
                out[concept] = await fetch(cik, concept, unit=unit)
                unit_used = unit
                break
            except EdgarUnavailable:
                continue
    return out, unit_used


async def collect_postes(cik: int) -> tuple[dict[str, dict[str, Any]], Optional[date], Optional[date]]:
    """Récupère tous les postes chez EDGAR sur DEUX ancres, une par nature de poste.

    Il n'y a pas une date, il y en a deux, et les confondre est un défaut de sens :
      • **ancre de flux** (`fiscal_end`) — la dernière clôture ANNUELLE. Un chiffre d'affaires, un
        résultat, un cash-flow appartiennent à un exercice ; les prendre à deux exercices
        différents fabriquerait des ratios faux tout en restant « tier A ».
      • **ancre de bilan** (`balance_end`) — le dernier INSTANT publié, 10-Q compris. Un poste de
        bilan ne « couvre » pas une période, il date d'un jour ; le figer sur la clôture annuelle
        rendait le socle aveugle à tout trimestre depuis le dernier 10-K. Sur RVMD au 2026-09-04,
        c'était un bilan de 8 mois : trésorerie ×2,1, capitaux propres ×1,6 et 487,4 M$ de dette
        convertible entièrement invisibles, sur une position réellement détenue.

    Les deux ancres sont dérivées des capitaux propres (`_ANCHOR_METRIC`), présent sous les deux
    formes. Chaque poste s'aligne sur SON ancre à ±20 j, ou reste absent (#25). Quand l'émetteur n'a
    déposé aucun trimestre depuis son 10-K, `balance_end == fiscal_end` et le comportement est
    exactement l'ancien.
    """
    anchor_poste = next(p for p in POSTES if p.metric == _ANCHOR_METRIC)

    annual_points, _ = await _points_for(cik, anchor_poste.concepts, flow=True)
    _, annual_point = select_concept(annual_points, None, flow=False)
    if annual_point is None:
        raise EdgarFeedUnavailable(
            f"CIK {cik} : aucun point annuel pour {'/'.join(anchor_poste.concepts)} — "
            f"pas d'ancrage d'exercice, socle EDGAR non constructible"
        )
    fiscal_end = date.fromisoformat(annual_point["end"])

    instant_points, anchor_unit = await _points_for(cik, anchor_poste.concepts, flow=False)
    concept, point = select_concept(instant_points, None, flow=False)
    if point is None:                       # aucun instantané : on retombe sur la clôture annuelle
        concept, point, anchor_unit = _concept_of(annual_points, annual_point), annual_point, "USD"
    balance_end = date.fromisoformat(point["end"])

    resolved: dict[str, dict[str, Any]] = {
        _ANCHOR_METRIC: {"concept": concept, "point": point, "unit": anchor_unit}
    }

    for poste in POSTES:
        if poste.metric == _ANCHOR_METRIC:
            continue
        target = fiscal_end if poste.flow else balance_end
        points, unit = await _points_for(cik, poste.concepts, flow=poste.flow)
        concept, point = select_concept(points, target, flow=poste.flow)
        if point is None:
            continue
        got: dict[str, Any] = {"concept": concept, "point": point, "unit": unit}
        if poste.composite_with:
            # La 2ᵉ jambe d'un composite de bilan suit l'ancre de BILAN, comme la 1ʳᵉ : c'est
            # exactement là que se jouait la dette convertible de RVMD, déposée en 10-Q seulement.
            pts2, unit2 = await _points_for(cik, poste.composite_concepts, flow=False)
            c2, p2 = select_concept(pts2, balance_end, flow=False)
            if p2 is not None:
                got["second"] = {"concept": c2, "point": p2, "unit": unit2}
        resolved[poste.metric] = got

    return resolved, fiscal_end, balance_end


def _concept_of(
    points_by_concept: dict[str, list[dict[str, Any]]], point: dict[str, Any]
) -> Optional[str]:
    """Retrouve le concept dont provient un point retenu (repli sans instantané)."""
    for concept, pts in points_by_concept.items():
        if any(p is point for p in pts):
            return concept
    return None


async def _current_fact_ids(
    conn, ticker_id: str, metric: str, period_end: str, *, flow: bool
) -> list[int]:
    """Ids des entrées COURANTES que ce fait remplace — TOUTES, pas la plus récente.

    Apparie sur `metric` + la datation du `content_structured`, pas sur les tags : cela rend le feed
    idempotent **y compris face au seed NVDA écrit à la main**, dont les tags diffèrent de ceux
    produits ici. Re-mesurer un poste remplace donc le fait seedé par le fait mesuré, au lieu d'en
    créer un doublon que `extract_edgar_facts` trancherait par ordre d'itération.

    ⚠️ **La clé d'identité dépend du type de poste, exactement comme l'ancre (F4).** Un FLUX est
    identifié par `(metric, period_end)` : le CA de FY2024 et celui de FY2025 sont deux faits
    légitimes qui coexistent. Un poste de BILAN, lui, est identifié par `metric` SEUL — il n'y a
    qu'un bilan courant, et un instant plus ancien est *périmé*, pas *historique*. Apparier un
    stock sur l'égalité des dates faisait qu'un changement d'ancre **ajoutait** la vérité sans
    retirer le périmé : mesuré sur RVMD au déploiement de F4, les capitaux propres au 2025-12-31
    (1,63 MdUSD) et au 2026-06-30 (2,61 MdUSD) sont restés tous deux `superseded_by IS NULL`.
    `extract_edgar_facts` s'en sortait (il prend le point le plus récent), mais le corpus narratif
    lu par les agents portait deux réponses contradictoires à la même question.

    Un instant **strictement plus récent** déjà en base n'est jamais supersedé par un plus ancien
    (`<= $4`) : si EDGAR reculait, ce serait une régression silencieuse, pas une mise à jour.
    """
    scope = (
        "AND content_structured->>'period_end' = $4"
        if flow
        else "AND content_structured->>'period_end' <= $4"
    )
    rows = await conn.fetch(
        f"""
        SELECT id FROM knowledge_entries
        WHERE ticker_id = $1 AND superseded_by IS NULL AND is_deleted = FALSE
          AND entry_type = 'fact_financial' AND source_type = $2
          AND content_structured->>'metric' = $3
          {scope}
        ORDER BY id DESC
        """,
        ticker_id, _SOURCE_TYPE, metric, period_end,
    )
    return [r["id"] for r in rows]


async def run_edgar_feed(
    ticker_id: str, *, persist: bool = True
) -> dict[str, Any]:
    """Amorce (ou rafraîchit) le socle EDGAR d'un ticker : 8 postes comptables → entries tier A.

    `persist=False` = dry-run — la base est append-only, on regarde avant d'écrire. À lancer AVANT
    `financials-refresh`, qui dérive ses ratios de ces faits.
    """
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT ticker_symbol, company_type FROM tickers WHERE id = $1", ticker_id
        )
    if row is None:
        raise EdgarFeedUnavailable(f"ticker inconnu : {ticker_id}")
    if (row["company_type"] or "") == "private" or not row["ticker_symbol"]:
        raise EdgarFeedUnavailable(
            f"{ticker_id} : pas de symbole de marché (privé/PUB-/PRIV-) — aucun dépôt EDGAR"
        )
    symbol = row["ticker_symbol"]

    cik = await resolve_cik(symbol)
    resolved, fiscal_end, balance_end = await collect_postes(cik)
    specs, unfounded = build_edgar_entries(
        ticker_id, symbol, cik, resolved, fiscal_end=fiscal_end
    )

    created: list[dict[str, Any]] = []
    if persist:
        async with get_db_session() as conn:
            async with conn.transaction():
                for spec in specs:
                    prevs = await _current_fact_ids(
                        conn, ticker_id, spec.metric, spec.content_structured["period_end"],
                        flow=spec.content_structured.get("poste_kind") == "flow",
                    )
                    stored = await store_knowledge(
                        conn, ticker_id=ticker_id, entry_type="fact_financial",
                        content=spec.content, source_type=_SOURCE_TYPE, title=spec.title,
                        content_structured=spec.content_structured, tags=spec.tags, lang="fr",
                        source_url=spec.source_url, source_date=spec.period_end,
                        fiscal_period=spec.fiscal_period,
                        supersedes_entry_id=prevs[0] if prevs else None,
                        # PAS de `covers` : ce sont les INTRANTS des ratios, pas les champs MVDD
                        # eux-mêmes (cf. migration 029, qui laisse les faits EDGAR bruts non tagués).
                    )
                    # `store_knowledge` ne referme que la lignée de version (prevs[0]). Les autres
                    # entrées courantes du même poste — celles laissées orphelines par un changement
                    # d'ancre — sont retirées ici : les oublier, c'est laisser le corpus répondre
                    # deux choses différentes à la même question.
                    if len(prevs) > 1:
                        await conn.execute(
                            "UPDATE knowledge_entries SET superseded_by = $1 WHERE id = ANY($2::int[])",
                            stored["id"], prevs[1:],
                        )
                    created.append(
                        dict(stored) | {"metric": spec.metric, "supersedes": prevs}
                    )
        logger.info(
            "edgar_feed %s (%s, CIK %d) → %d poste(s) · flux %s, bilan %s (+%d j) · non fondés: %s",
            ticker_id, symbol, cik, len(created), fiscal_end, balance_end,
            (balance_end - fiscal_end).days,
            ", ".join(u["metric"] for u in unfounded) or "aucun",
        )

    return {
        "ticker_id": ticker_id, "symbol": symbol, "cik": cik,
        # `period_end` conservé (ancre de FLUX) : c'est le contrat de lecture existant. `balance_end`
        # est la nouveauté — la date du bilan retenu, qui n'est plus supposée égale à la clôture.
        "period_end": fiscal_end.isoformat(), "balance_end": balance_end.isoformat(),
        "jours_apres_cloture": (balance_end - fiscal_end).days,
        "persisted": persist,
        "postes": [
            {
                "metric": s.metric, "xbrl_tag": s.content_structured["xbrl_tag"],
                "kind": s.content_structured.get("poste_kind"),
                "value": s.content_structured.get("value"),
                "cash": s.content_structured.get("cash"),
                "long_term_debt": s.content_structured.get("long_term_debt"),
                "currency": s.content_structured["currency"],
                "period": s.fiscal_period, "source_url": s.source_url,
            }
            for s in specs
        ],
        "unfounded": unfounded,
        "created": [{"id": c["id"], "metric": c["metric"], "supersedes": c["supersedes"]}
                    for c in created],
    }
