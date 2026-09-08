"""Événements MATÉRIELS d'un émetteur (8-K / 6-K) — l'horloge que le corpus n'avait pas.

Pourquoi ce module existe (2026-09-05, RVMD)
--------------------------------------------
F12 a donné une horloge au **modèle** (date du jour + ancre temporelle dans le message). L'ancre
ne regardait que les dépôts **périodiques** (10-K / 10-Q), lus dans le corpus déjà écrit par
`edgar_feed`. Sur RVMD au 2026-09-04 elle annonçait « 2026-06-30 » et **rassurait** le modèle,
alors que le monde avait changé deux fois depuis :

  • 8-K du **2026-08-26** (item 8.01) — la FDA approuve RASONQUE : l'émetteur passe de
    « clinique, aucun produit approuvé » à « commercial ». Quatre entries actives tier A du
    corpus décrivent l'état antérieur — **elles ne sont pas fausses, elles sont périmées** ;
  • 8-K **rapporté le 2026-08-27, déposé le 2026-09-01** (items 1.01 + 2.03) — accord important
    et création d'une obligation financière directe, donc un bilan qui bouge après l'ancre.

Une garde peut donc être **correcte et produire quand même un faux sentiment de fraîcheur** :
c'est le mode de panne que ce module ferme.

Trois états, jamais deux confondus (famille #25 / #44)
-----------------------------------------------------
`latest_material_event()` rend un `MaterialEventLookup` dont le `status` vaut :

  • ``found``       — un événement matériel existe, daté et qualifié par ses items ;
  • ``none``        — l'émetteur n'a **publié aucun** 8-K/6-K (émetteur neuf, jeune cotation) ;
  • ``unavailable`` — EDGAR n'a pas répondu, ou le CIK est inconnu → **on ne sait pas**.

Confondre ``none`` et ``unavailable`` reproduirait exactement le défaut qu'on corrige : une panne
réseau se lirait « il ne s'est rien passé », c'est-à-dire la phrase la plus rassurante possible
produite par la pire des raisons. L'appelant doit **dire** lequel des trois il a obtenu (#25).

Date de l'ÉVÉNEMENT ≠ date du DÉPÔT
-----------------------------------
EDGAR porte les deux : `reportDate` (quand le fait s'est produit) et `filingDate` (quand il a été
publié). RVMD illustre l'écart : événement le 2026-08-27, dépôt le 2026-09-01. Le monde change à
la **date de l'événement** — c'est donc elle qui sert de seuil de péremption ; la date de dépôt est
transportée à côté pour que le délai de publication reste lisible, jamais pour l'arbitrer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import httpx

from app.config import settings
from app.knowledge.edgar_facts import _UA, cik_from_url

logger = logging.getLogger(__name__)

_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Formes qui portent un événement matériel. Les périodiques (10-K/10-Q/20-F) en sont exclues **à
# dessein** : elles sont déjà l'ancre existante, et les confondre rendrait l'extension no-op.
MATERIAL_FORMS = frozenset({"8-K", "8-K/A", "6-K", "6-K/A"})

# Items 8-K → libellé français. Un item ABSENT de cette table n'est jamais silencieux : il est
# rendu tel quel (« item 3.03 (non répertorié) »). Une table de libellés qui filtre ce qu'elle ne
# connaît pas transforme un événement inconnu en non-événement.
ITEM_LABELS: dict[str, str] = {
    "1.01": "conclusion d'un accord important",
    "1.02": "résiliation d'un accord important",
    "1.03": "mise en faillite / redressement",
    "1.05": "incident de cybersécurité important",
    "2.01": "acquisition ou cession d'actifs",
    "2.02": "résultats financiers publiés",
    "2.03": "création d'une obligation financière directe",
    "2.04": "exigibilité anticipée d'une dette",
    "2.05": "coûts d'un plan de sortie ou de cession",
    "2.06": "dépréciation d'actifs importante",
    "3.01": "avis de radiation / non-conformité de cotation",
    "3.02": "émission de titres non enregistrée",
    "3.03": "modification des droits des porteurs",
    "4.01": "changement de commissaire aux comptes",
    "4.02": "états financiers antérieurs déclarés non fiables",
    "5.01": "changement de contrôle",
    "5.02": "départ ou nomination de dirigeants",
    "5.03": "modification des statuts / exercice fiscal",
    "5.07": "résultats du vote des actionnaires",
    "7.01": "communication Regulation FD",
    "8.01": "autre événement important",
    "9.01": "états financiers et pièces jointes",
}

# Items purement formels : ils accompagnent un autre item et ne portent pas d'information de fond.
# Ils ne sont PAS retirés de l'événement — seulement écartés du calcul de « portée », pour qu'un
# 8-K « 2.02 + 9.01 » ne compte pas deux motifs de péremption là où il n'y en a qu'un.
_ITEMS_FORMELS = frozenset({"9.01"})


class MaterialEventsUnavailable(Exception):
    """EDGAR n'a pas rendu le flux des dépôts. Distinct d'« aucun événement » : l'appelant doit le
    DIRE au modèle plutôt que de laisser lire un silence rassurant (#25)."""


@dataclass(frozen=True)
class MaterialEvent:
    """Un dépôt matériel unique, tel qu'EDGAR le publie."""

    form: str
    event_date: date          # `reportDate` — quand le monde a changé
    filing_date: date         # `filingDate` — quand ça a été publié
    items: tuple[str, ...] = ()
    accession: Optional[str] = None
    url: Optional[str] = None

    @property
    def items_substantiels(self) -> tuple[str, ...]:
        return tuple(i for i in self.items if i not in _ITEMS_FORMELS)

    def libelle_items(self) -> str:
        """« 1.01 (conclusion d'un accord important), 2.03 (…) ». Vide si le formulaire n'a pas
        d'items (cas du 6-K, qui n'en porte jamais) — l'appelant le formule alors autrement."""
        return ", ".join(
            f"{i} ({ITEM_LABELS.get(i, 'non répertorié')})" for i in self.items
        )

    def resume(self) -> str:
        base = f"{self.form} du {self.event_date.isoformat()}"
        if self.filing_date != self.event_date:
            base += f" (déposé le {self.filing_date.isoformat()})"
        lib = self.libelle_items()
        return f"{base}, items {lib}" if lib else base


@dataclass(frozen=True)
class MaterialEventLookup:
    """Résultat d'une consultation du flux. `status` ∈ {found, none, unavailable} — voir module."""

    status: str
    event: Optional[MaterialEvent] = None
    cik: Optional[int] = None
    raison: Optional[str] = None          # renseigné pour `unavailable` uniquement
    recents: tuple[MaterialEvent, ...] = field(default=())

    @property
    def connu(self) -> bool:
        """True seulement si on SAIT. `none` compte comme su ; `unavailable` non."""
        return self.status in ("found", "none")


def _parse_date(v: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def _parse_items(raw: Any) -> tuple[str, ...]:
    """« 1.01,2.03 » → ('1.01', '2.03'). EDGAR sépare par virgule, parfois avec des espaces."""
    if not raw:
        return ()
    return tuple(p.strip() for p in str(raw).split(",") if p.strip())


def _filing_url(cik: int, accn: Optional[str]) -> Optional[str]:
    if not accn:
        return None
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/"
        f"{accn.replace('-', '')}/{accn}-index.htm"
    )


# Cache TTL de l'ancre, posé au SEUL point de sortie réseau (#46). Il existe pour une raison
# précise : depuis la capacité 4, la readiness est **réévaluée à chaque lecture** d'écran (#53), et
# chaque lecture demanderait sinon un aller-retour EDGAR. Un émetteur ne dépose pas deux 8-K dans
# l'heure ; en revanche un écran rafraîchi en boucle taperait EDGAR en boucle, ce que sa politique
# d'accès équitable n'autorise pas.
#
# ⚠️ Ce cache porte la RÉPONSE BRUTE, jamais l'état d'actualité. Mémoriser `perimee`/`courante`
# rendrait l'actualité persistante à l'échelle du TTL — c'est-à-dire exactement la cause n°2 du
# diagnostic #50, réintroduite par la porte de sortie. La comparaison, elle, est refaite à chaque
# lecture sur une ancre éventuellement mémorisée.
#
# ⚠️ Les échecs ne sont PAS mémorisés : une panne EDGAR doit se re-tenter à la lecture suivante,
# sinon une coupure de 30 s figerait le dossier en `indeterminable` pour une heure (#49).
_ANCRE_TTL_S = 3600.0
_ancre_cache: dict[int, tuple[float, dict[str, Any]]] = {}


def vider_cache_ancre() -> None:
    """Purge le cache d'ancres. Pour les vérifications, et pour un rafraîchissement forcé."""
    _ancre_cache.clear()


async def _submissions(cik: int) -> dict[str, Any]:
    fige = _ancre_cache.get(cik)
    if fige is not None and (time.monotonic() - fige[0]) < _ANCRE_TTL_S:
        return fige[1]

    url = _SUBMISSIONS.format(cik=cik)
    try:
        async with httpx.AsyncClient(
            timeout=settings.SEARCH_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        ) as client:
            r = await client.get(url)
    except httpx.HTTPError as e:
        raise MaterialEventsUnavailable(f"EDGAR injoignable (CIK {cik}) : {e}") from e
    if r.status_code != 200:
        raise MaterialEventsUnavailable(f"EDGAR {r.status_code} sur submissions (CIK {cik})")
    try:
        payload = r.json()
    except ValueError as e:
        raise MaterialEventsUnavailable(f"réponse EDGAR non-JSON (CIK {cik}) : {e}") from e
    _ancre_cache[cik] = (time.monotonic(), payload)
    return payload


def parse_material_events(payload: dict[str, Any], cik: int, *, limit: int = 10
                          ) -> list[MaterialEvent]:
    """Extrait les dépôts matériels de `filings.recent`, du plus récent au plus ancien.

    Le tri se fait sur la date d'**événement** : EDGAR classe par date de dépôt, et RVMD montre que
    les deux se croisent (événement du 27/08 déposé le 01/09, après un événement du 26/08 déposé le
    26/08). Trier par dépôt rendrait « le dernier événement connu » faux d'un jour dans ce cas
    précis — celui qui compte.
    """
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    formes = recent.get("form") or []
    out: list[MaterialEvent] = []
    for i, forme in enumerate(formes):
        if forme not in MATERIAL_FORMS:
            continue
        filed = _parse_date(_at(recent, "filingDate", i))
        reported = _parse_date(_at(recent, "reportDate", i))
        # Un dépôt sans date de dépôt exploitable n'est pas datable : on ne l'invente pas.
        if filed is None and reported is None:
            continue
        accn = _at(recent, "accessionNumber", i)
        out.append(
            MaterialEvent(
                form=forme,
                event_date=reported or filed,      # type: ignore[arg-type]
                filing_date=filed or reported,     # type: ignore[arg-type]
                items=_parse_items(_at(recent, "items", i)),
                accession=accn,
                url=_filing_url(cik, accn),
            )
        )
    out.sort(key=lambda e: (e.event_date, e.filing_date), reverse=True)
    return out[:limit]


def _at(recent: dict[str, Any], key: str, i: int) -> Any:
    col = recent.get(key) or []
    return col[i] if i < len(col) else None


async def latest_material_event(cik: int, *, limit: int = 10) -> MaterialEventLookup:
    """Dernier événement matériel publié par l'émetteur. Ne lève jamais : l'indisponibilité est un
    **état rendu**, pas une exception — l'appelant doit pouvoir la formuler au modèle."""
    try:
        payload = await _submissions(cik)
    except MaterialEventsUnavailable as e:
        logger.warning("material_events: flux indisponible CIK=%s (%s)", cik, e)
        return MaterialEventLookup(status="unavailable", cik=cik, raison=str(e))
    evts = parse_material_events(payload, cik, limit=limit)
    if not evts:
        return MaterialEventLookup(status="none", cik=cik, recents=())
    return MaterialEventLookup(status="found", event=evts[0], cik=cik, recents=tuple(evts))


def ancre_substantielle(lookup: MaterialEventLookup) -> MaterialEventLookup:
    """Restreint l'ancre aux dépôts qui PÈSENT — détenteur unique de « quel événement périme ».

    `latest_material_event` rend le dernier dépôt matériel, quel qu'il soit. Ce n'est pas la bonne
    ancre pour la porte de complétude : un 8-K ne portant que l'item 9.01 (« états financiers et
    pièces jointes ») est un acte purement formel, et le laisser périmer un corpus rendrait tout
    émetteur `not_ready` au premier dépôt de routine — le risque assumé nommé par la roadmap 02 §4.

    ⚠️ « Sans item » ≠ « sans substance ». EDGAR n'attribue **aucun** item aux 6-K (émetteurs
    étrangers) : ne garder que les dépôts à `items_substantiels` non vide les écarterait tous, en
    silence, et rendrait leurs corpus éternellement `courants`. Le filtre écarte donc uniquement les
    dépôts **dont tous les items déclarés sont formels** — un dépôt qui n'en déclare aucun passe.

    Fonction **pure** : elle trie ce que le flux a déjà rapporté, sans nouvel appel réseau. Les
    statuts `none` et `unavailable` traversent inchangés — ce sont des états, pas des listes à
    filtrer, et les confondre est le mode de panne central du chantier (#49).
    """
    if lookup.status != "found":
        return lookup
    gardes = tuple(e for e in lookup.recents if (not e.items) or e.items_substantiels)
    if not gardes:
        # Tous les dépôts récents sont formels : l'émetteur a bien déposé, mais rien qui périme.
        # C'est `none` (état CONNU), pas `unavailable` (panne) — la distinction porte tout #49.
        return MaterialEventLookup(status="none", cik=lookup.cik, recents=())
    return MaterialEventLookup(status="found", event=gardes[0], cik=lookup.cik, recents=gardes)


async def resolve_cik_for_ticker(conn, ticker_id: str) -> Optional[int]:
    """CIK de l'émetteur, au coût le plus bas d'abord.

    1. Relu d'une `source_url` EDGAR **déjà écrite** dans le corpus (`/data/<cik>/`, cf. #43) —
       gratuit, aucun appel réseau ;
    2. à défaut, résolu depuis `tickers.ticker_symbol` (convention #11 : jamais `tickers.id`).

    `None` = émetteur non résolvable (ticker privé, symbole absent). L'appelant traite ce cas comme
    `unavailable`, **pas** comme « aucun événement ».
    """
    row = await conn.fetchrow(
        """
        SELECT source_url
          FROM knowledge_entries
         WHERE ticker_id = $1
           AND source_type = 'edgar_official'
           AND source_url LIKE '%/data/%'
         ORDER BY source_date DESC NULLS LAST, id DESC
         LIMIT 1
        """,
        ticker_id,
    )
    cik = cik_from_url(row["source_url"]) if row else None
    if cik:
        return cik

    symbole = await conn.fetchval("SELECT ticker_symbol FROM tickers WHERE id = $1", ticker_id)
    if not symbole:
        return None
    # Import tardif : `edgar_feed` importe ce module en aval, l'importer en tête créerait un cycle.
    from app.knowledge.edgar_feed import resolve_cik

    try:
        return await resolve_cik(str(symbole))
    except Exception as e:  # noqa: BLE001 — résolution best-effort, l'appelant dira « inconnu »
        logger.warning("material_events: CIK non résolu pour %s (%s)", ticker_id, e)
        return None


async def material_anchor_for_ticker(conn, ticker_id: Optional[str]) -> MaterialEventLookup:
    """Ancre matérielle d'un ticker, prête à être formulée au modèle."""
    if not ticker_id:
        return MaterialEventLookup(status="unavailable", raison="aucun ticker_id fourni")
    cik = await resolve_cik_for_ticker(conn, ticker_id)
    if cik is None:
        return MaterialEventLookup(
            status="unavailable",
            raison=f"CIK non résolu pour {ticker_id} (émetteur non déposant SEC ?)",
        )
    return await latest_material_event(cik)
