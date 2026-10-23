"""Publier la VENTILATION PUBLIÉE d'un émetteur au dossier — calqué sur `socle_feed.py` (lot M2).

Mêmes trois issues que le socle (jamais un silence, #25) : `publie` (version neuve), `a_jour` (même
empreinte, rien écrit), `secteur_unique`/`sans_ventilation` (statut rendu, RIEN écrit — le constat est
recalculable, #77). Une famille sans gabarit (bancaire, 1.0.0) refuse NOMMÉ à la publication, jamais à
la fonction pure (`relever` reste exécutable, voir `ventilation.py`).

Coût : l'index du dépôt + trois fichiers XBRL (gratuit, data.sec.gov), aucun modèle. User-Agent `_UA`
d'`edgar_facts`, une requête à la fois, ≥ `DELAI_S` entre appels (#73 : un blocage réseau devient un
échec nommé, jamais un silence muet).
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from typing import Any, NamedTuple, Optional

import httpx

from app.contracts.ventilation_schema import VentilationReferentiel
from app.knowledge.datation import constatee
from app.knowledge.edgar_facts import _UA
from app.knowledge.edgar_feed import EdgarFeedUnavailable, filing_url, identite_de_l_emetteur
from app.knowledge.material_events import MaterialEventsUnavailable, _submissions
from app.knowledge.perimetre import FilingMeta, identifier_jumeau_candidat, regime_a_change, vue_servie
from app.knowledge.service import ENTRIES_COURANTES, store_knowledge
from app.knowledge.socle_comptes import charger_gabarit
from app.knowledge.socle_feed import SocleIndisponible, assurer_socle
from app.knowledge.ventilation import (
    METRIC,
    Depot,
    charger_referentiel,
    empreinte,
    relever,
    rendre_ventilation,
    structure_de_ventilation,
)
from app.knowledge.ventilation_xbrl import lire_etiquettes, lire_hierarchie, lire_instance

logger = logging.getLogger(__name__)

SOURCE_TYPE = "edgar_official"
TAGS = ["financials", "edgar", METRIC]
DELAI_S = 0.25

_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/index.json"
_FICHIER = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{nom}"
_HEADERS_FICHIER = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn_nodash}/{accn}-index-headers.html"

_FORMS_10K = {"10-K", "10-K/A"}
_FORMS_10Q = {"10-Q", "10-Q/A"}


class VentilationIndisponible(Exception):
    """La ventilation ne peut pas être relevée (EDGAR injoignable, aucun 10-K déposé)."""


class VentilationPubliee(NamedTuple):
    statut: str                          # "publie" | "a_jour" | "secteur_unique" | "sans_ventilation"
    structure: Optional[dict[str, Any]]
    entry_id: Optional[int] = None
    remplace: tuple[int, ...] = ()
    motif: Optional[str] = None          # renseigné pour le refus bancaire


_SQL_COURANTS = f"""
    SELECT id, content_structured FROM knowledge_entries
     WHERE ticker_id = $1 AND {ENTRIES_COURANTES}
       AND content_structured->>'metric' = $2
     ORDER BY id DESC
"""


async def ventilation_en_vigueur(conn, ticker_id: str) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(_SQL_COURANTS, ticker_id, METRIC)
    return None if row is None else {"id": row["id"], "structure": row["content_structured"]}


async def _famille_du_titre(conn, ticker_id: str) -> tuple[Optional[str], Optional[str]]:
    """La famille de comptes du titre, lue au référentiel du classeur à partir de son archétype EN
    VIGUEUR (§2 de la spec) : `(nom_famille, nom_du_fichier_gabarit)` — `(None, None)` si le titre
    n'est pas classé (prudence, comme `read_archetype`) ; `(nom, None)` si la famille n'a pas de
    gabarit (bancaire, 1.0.0)."""
    from app.agents.v2.framework_persist import read_archetype
    from app.modele_entreprise.referentiel import load_referentiel

    classement = await read_archetype(conn, ticker_id=ticker_id)
    if classement is None:
        return None, None
    archetype, _motif = classement
    ref = load_referentiel()
    nom_famille = ref.famille_par_archetype.get(archetype)
    if nom_famille is None:
        return archetype, None
    return nom_famille, ref.familles_de_comptes[nom_famille].gabarit


# ── La lecture réseau des dépôts (gratuite) ─────────────────────────────────────────────────────

def _derniers_10k_10q(payload: dict[str, Any]) -> tuple[Optional[dict[str, str]], Optional[dict[str, str]]]:
    """Le dernier 10-K, et le dernier 10-Q s'il est postérieur (§4 de la spec). Pure."""
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    formes = recent.get("form") or []
    accns = recent.get("accessionNumber") or []
    filed = recent.get("filingDate") or []
    report = recent.get("reportDate") or []

    def _derniere(formes_visees: set[str]) -> Optional[dict[str, str]]:
        candidats = [
            {"accn": accns[i], "form": formes[i], "filed": filed[i], "report": report[i]}
            for i in range(len(formes))
            if formes[i] in formes_visees and i < len(accns) and i < len(filed)
        ]
        return max(candidats, key=lambda c: (c["report"], c["filed"])) if candidats else None

    k10 = _derniere(_FORMS_10K)
    q10 = _derniere(_FORMS_10Q)
    if k10 is not None and q10 is not None and q10["report"] <= k10["report"]:
        q10 = None
    return k10, q10


_FORMS_JUMEAU = _FORMS_10K | _FORMS_10Q


def _tous_filings(payload: dict[str, Any]) -> tuple[FilingMeta, ...]:
    """Tous les 10-K/10-Q du flux `submissions`, pour la recherche du JUMEAU (§5, étape 2) — pure,
    bornée (le flux est déjà fini)."""
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    formes = recent.get("form") or []
    accns = recent.get("accessionNumber") or []
    filed = recent.get("filingDate") or []
    report = recent.get("reportDate") or []
    return tuple(
        FilingMeta(accn=accns[i], form=formes[i], filed=filed[i], report=report[i])
        for i in range(len(formes))
        if formes[i] in _FORMS_JUMEAU and i < len(accns) and i < len(filed) and i < len(report)
    )


def _premier_niveau_par_axe(depot: Depot, referentiel: VentilationReferentiel) -> dict[str, frozenset[str]]:
    """Les membres de premier niveau d'UN dépôt, par axe à raccord `total` — approximation GRATUITE
    (sans le retrait des qualificateurs neutres de `ventilation._classer`) qui sert UNIQUEMENT à
    décider si le JUMEAU vaut la peine d'être lu (§5) : un faux positif coûte une lecture gratuite
    de plus, un faux négatif ne casse rien (le jumeau reste simplement absent, comme avant ce lot)."""
    axes_total = {a.axe for a in referentiel.axes if a.raccord == "total"}
    membres_par_axe: dict[str, set[str]] = {a: set() for a in axes_total}
    for f in depot.faits:
        for a, m in f.membres:
            if a in axes_total:
                membres_par_axe[a].add(m)
    return {
        a: frozenset(m for m in ms if depot.hierarchie.get(m) not in ms)
        for a, ms in membres_par_axe.items()
    }


async def _get(client: httpx.AsyncClient, url: str) -> bytes:
    await asyncio.sleep(DELAI_S)
    r = await client.get(url)
    r.raise_for_status()
    return r.content


def _choisir(noms: list[str], *, suffixe: str, repli_xsd: bool) -> Optional[str]:
    for n in noms:
        if n.endswith(suffixe):
            return n
    if repli_xsd:
        for n in noms:
            if n.endswith(".xsd"):
                return n
    return None


async def _lire_depot(client: httpx.AsyncClient, cik: int, accn: str, form: str, filed: str) -> Depot:
    nodash = accn.replace("-", "")
    try:
        index = _as_json(await _get(client, _INDEX.format(cik=cik, accn_nodash=nodash)))
        noms = [it["name"] for it in index["directory"]["item"]]
        nom_inst = _choisir(noms, suffixe="_htm.xml", repli_xsd=False)
        if nom_inst is None:
            raise VentilationIndisponible(f"dépôt {accn} : pas d'instance XBRL (`_htm.xml`) à l'index")
        nom_lab = _choisir(noms, suffixe="_lab.xml", repli_xsd=True)
        nom_def = _choisir(noms, suffixe="_def.xml", repli_xsd=True)
        inst = await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_inst))
        lab = await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_lab)) if nom_lab else b""
        defx = (await _get(client, _FICHIER.format(cik=cik, accn_nodash=nodash, nom=nom_def))
               if nom_def and nom_def != nom_lab else (lab if nom_lab and nom_lab.endswith(".xsd") else b""))
    except httpx.HTTPError as e:
        raise VentilationIndisponible(f"EDGAR injoignable pour le dépôt {accn} : {e}") from e

    faits = tuple(lire_instance(inst))
    etiquettes = lire_etiquettes(lab) if lab else {}
    hierarchie, conflits = lire_hierarchie(defx) if defx else ({}, ())
    return Depot(accn=accn, form=form, filed=filed, faits=faits, etiquettes=etiquettes,
                hierarchie=hierarchie, conflits=conflits)


def _as_json(payload: bytes) -> dict[str, Any]:
    import json
    return json.loads(payload)


async def lire_depots(cik: int, *, referentiel: Optional[VentilationReferentiel] = None) -> list[Depot]:
    """Les dépôts à relever : le dernier 10-K, le dernier 10-Q s'il est postérieur (§4), et le
    dépôt JUMEAU quand le périmètre a redécoupé (§5, étape 2 du lot P1) — celui qui a publié, dans
    l'ANCIEN découpage, la période que le 10-Q reprend en comparatif. Lit le flux `submissions` par
    le lecteur EXISTANT (`material_events._submissions`, détenteur unique, cache au seul point de
    sortie réseau) — on n'en écrit pas un second.

    Le jumeau n'est lu QUE si `referentiel` est fourni ET qu'un axe à raccord `total` a changé de
    premier niveau entre le 10-K et le 10-Q (`perimetre.regime_a_change`) — jamais pour tout
    émetteur à chaque appel (§5 : gratuit, mais pas pour rien). `referentiel=None` (défaut) :
    comportement INCHANGÉ (deux dépôts au plus), pour tout appelant qui n'a pas encore de
    référentiel sous la main."""
    try:
        payload = await _submissions(cik)
    except MaterialEventsUnavailable as e:
        raise VentilationIndisponible(f"flux `submissions` injoignable (CIK {cik}) : {e}") from e
    k10, q10 = _derniers_10k_10q(payload)
    if k10 is None:
        raise VentilationIndisponible(f"aucun 10-K déposé par le CIK {cik} — pas de ventilation à relever")
    async with httpx.AsyncClient(timeout=90.0, follow_redirects=True,
                                 headers={"User-Agent": _UA, "Accept": "*/*"}) as client:
        k10_depot = await _lire_depot(client, cik, k10["accn"], k10["form"], k10["filed"])
        depots = [k10_depot]
        if q10 is not None:
            q10_depot = await _lire_depot(client, cik, q10["accn"], q10["form"], q10["filed"])
            depots.append(q10_depot)
            if referentiel is not None:
                pn_ancien = _premier_niveau_par_axe(k10_depot, referentiel)
                pn_recent = _premier_niveau_par_axe(q10_depot, referentiel)
                if regime_a_change(pn_ancien, pn_recent):
                    filings = _tous_filings(payload)
                    recent_meta = FilingMeta(q10["accn"], q10["form"], q10["filed"], q10["report"])
                    ancien_meta = FilingMeta(k10["accn"], k10["form"], k10["filed"], k10["report"])
                    jumeau = identifier_jumeau_candidat(filings, recent_meta, ancien_meta)
                    if jumeau is not None:
                        depots.append(await _lire_depot(client, cik, jumeau.accn, jumeau.form, jumeau.filed))
    return depots


# ── La publication (base, #35 transaction explicite) ────────────────────────────────────────────

async def assurer_ventilation(conn, ticker_id: str) -> VentilationPubliee:
    """Relève et publie la ventilation si elle a changé. ÉCRIT (une transaction) — sauf les trois
    constats (`a_jour`/`secteur_unique`/`sans_ventilation`), qui n'écrivent jamais."""
    try:
        ident = await identite_de_l_emetteur(conn, ticker_id)
    except EdgarFeedUnavailable as e:
        raise VentilationIndisponible(f"identité de l'émetteur {ticker_id} injoignable : {e}") from e
    try:
        famille = await _famille_du_titre(conn, ticker_id)
    except Exception as e:  # référentiel du classeur absent/invalide : refus nommé, pas une panne nue
        raise VentilationIndisponible(f"famille de {ticker_id} indéterminable : {e}") from e
    try:
        depots = await lire_depots(ident.cik, referentiel=charger_referentiel())
    except VentilationIndisponible:
        raise
    except httpx.HTTPError as e:
        raise VentilationIndisponible(f"ventilation de {ticker_id} non relevable : {e}") from e
    try:
        socle_publie = await assurer_socle(conn, ticker_id)
    except SocleIndisponible as e:
        raise VentilationIndisponible(f"socle des comptes indisponible pour {ticker_id} : {e}") from e
    return await publier_ventilation(
        conn, ticker_id, cik=ident.cik, raison_sociale=ident.raison_sociale, famille=famille,
        depots=depots, socle=socle_publie.structure)


async def publier_ventilation(
    conn, ticker_id: str, *, cik: int, raison_sociale: str, famille: Optional[tuple[str, Optional[str]]],
    depots: list[Depot], socle: dict[str, Any], embed: bool = True,
) -> VentilationPubliee:
    """La moitié BASE : des dépôts déjà lus + le socle en vigueur → la pièce publiée, ou le constat
    rendu. Séparée pour s'éprouver sur des fixtures copiées du réel, sans réseau (§5 de la spec)."""
    gabarit = charger_gabarit()
    referentiel = charger_referentiel()
    nom_famille, gabarit_famille = famille if famille is not None else (None, None)
    if gabarit_famille is None:
        v = relever(depots, gabarit, referentiel, socle)   # la fonction pure RESTE exécutable
        if nom_famille is None:
            motif = (f"{ticker_id} n'est pas classé (aucun archétype en vigueur) : la famille de "
                     "comptes est indéterminable, donc aucune ventilation publiée")
        else:
            motif = (f"famille « {nom_famille} » : gabarit à écrire (M2 bis) — aucune ventilation "
                     "publiée, un zéro trompeur ne doit pas entrer au dossier")
        return VentilationPubliee(
            "refus_famille", structure_de_ventilation(
                v, version_referentiel=referentiel.version, version_gabarit=gabarit.version,
                depots=tuple(depots)),
            motif=motif)

    v = relever(depots, gabarit, referentiel, socle)
    structure = structure_de_ventilation(
        v, version_referentiel=referentiel.version, version_gabarit=gabarit.version, depots=tuple(depots))

    if v.statut != "ventilee":
        return VentilationPubliee(v.statut, structure)

    courants = await conn.fetch(_SQL_COURANTS, ticker_id, METRIC)
    if courants and empreinte(courants[0]["content_structured"] or {}) == empreinte(structure):
        return VentilationPubliee("a_jour", courants[0]["content_structured"], courants[0]["id"])

    depot_recent = max(depots, key=lambda d: (d.filed, d.accn))
    fins = [c.periode for c in v.cellules if re.match(r"^\d{4}-\d{2}-\d{2}$", c.periode or "")]
    fin_du_fait = max(fins) if fins else depot_recent.filed
    titre = (f"Ventilation publiée — {raison_sociale} — {len(v.axes)} axe(s) relevé(s) "
             f"(dernier dépôt {depot_recent.form} du {depot_recent.filed})")
    async with conn.transaction():
        stored = await store_knowledge(
            conn, ticker_id=ticker_id, entry_type="fact_financial",
            content=rendre_ventilation(vue_servie(structure, socle), raison_sociale=raison_sociale),
            source_type=SOURCE_TYPE,
            title=titre, content_structured=structure, tags=TAGS, lang="fr",
            source_url=filing_url(cik, depot_recent.accn),
            datation=constatee(date_du_fait=date.fromisoformat(fin_du_fait), date_du_document=date.fromisoformat(depot_recent.filed)),
            fiscal_period=f"AU {fin_du_fait}", supersedes_entry_id=courants[0]["id"] if courants else None,
            embed=embed)
        autres = [r["id"] for r in courants[1:]]
        if autres:
            await conn.execute(
                "UPDATE knowledge_entries SET superseded_by = $1 WHERE id = ANY($2::int[])",
                stored["id"], autres)
    logger.info("ventilation publiée %s publiée (#%s), remplace %s", ticker_id, stored["id"],
               [r["id"] for r in courants])
    return VentilationPubliee("publie", structure, stored["id"], tuple(r["id"] for r in courants))
