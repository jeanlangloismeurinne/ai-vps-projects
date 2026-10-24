"""Le RELEVÉ et le RACCORD de la ventilation publiée — fonction PURE (lot M2, roadmap V3 11).

Prend les dépôts déjà LUS (instance + étiquettes + hiérarchie, `ventilation_xbrl.py`) et le socle des
comptes EN VIGUEUR (`socle_comptes.structure_du_socle`), et rend une `Ventilation` : une cellule par
(axe × ligne du gabarit × membre × période), raccordée au total publié quand l'axe le permet. Aucun
appel réseau ni modèle ici — c'est la même séparation que `socle_comptes.reconstituer` (#115).

LA FAMILLE DE L'ÉMETTEUR NE GOUVERNE PAS `relever`. Une famille sans gabarit (bancaire, 1.0.0) bloque
la PUBLICATION (`ventilation_feed.publier_ventilation`), jamais la fonction pure : `relever` reçoit
TOUJOURS le gabarit industriel (seul gabarit qui existe en 1.0.0) pour reconnaître les concepts dont
l'émetteur se sert — JPM dépose `NetIncomeLoss`/`Assets`/`IncomeTaxExpenseBenefit` par métier, qui SONT
des recettes à un seul concept du gabarit industriel, même si JPM n'est pas une industrielle. Les
concepts propres au secteur bancaire (`RevenuesNetOfInterestExpense`, `NoninterestExpense`,
`ProvisionForLoanLeaseAndOtherLosses`…) n'appartiennent à aucune recette → `non_rattaches`, visibles,
jamais perdus ni devinés (mesuré, §écarts de ce lot : JPM n'étiquette que TROIS métiers sur
`StatementBusinessSegmentsAxis` — CCB/CIB/AWM ; le quatrième, « Corporate », est tagué SEUL sur
`srt:ConsolidationItemsAxis = us-gaap:CorporateNonSegmentMember`, SANS membre de
`StatementBusinessSegmentsAxis` : il n'entre donc jamais dans l'axe `secteurs` du référentiel 1.0.0 —
écart à la lettre de la spec, qui annonçait quatre métiers relevés).

LE CLASSEMENT D'UN FAIT (§4.1 de la spec). Après retrait des qualificateurs neutres déclarés au
référentiel, un fait appartient à l'axe A si son contexte porte EXACTEMENT un membre de A et aucun
autre axe — sauf, pour un axe `raccord: aucun` (ex. `clients`), les `qualificateurs` qu'il déclare, qui
deviennent la BASE du fait (ex. : la part d'un client sur le secteur Compute & Networking). Un fait qui
porte un axe de PLUS, non déclaré qualificateur, est un SOUS-DÉTAIL (JPM : provision du segment CCB ×
portefeuille Apple Card) — compté, jamais relevé comme une cellule d'axe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

from app.contracts.ventilation_schema import AxeVentilation, VentilationReferentiel
from app.knowledge.perimetre import (
    CONCEPT_DOUZE_MOIS, FORME_STRUCTURE, SignalAcquisition, ordre_des_periodes, premier_niveau_de,
    signal_acquisition_significative,
)
from app.knowledge.socle_comptes import Gabarit, tolerance_bouclage
from app.knowledge.ventilation_xbrl import FaitDimensionne

REFERENTIEL_YAML = Path(__file__).resolve().parent / "ventilation_publiee.yaml"

METRIC = "ventilation_publiee"
# `CONCEPT_DOUZE_MOIS` (le concept d'une cellule CALCULÉE, jamais lue au dépôt) est importé du détenteur
# `perimetre` : les douze mois se calculent désormais dans la VUE SERVIE, sur la série du découpage
# de référence (lot P1 §8 point 3), jamais dans le relevé.


class ReferentielVentilationInvalide(Exception):
    """Le référentiel de ventilation est formellement invalide — lève plutôt que de publier un
    référentiel partiel (même geste que `GabaritInvalide`)."""


@lru_cache(maxsize=1)
def charger_referentiel(chemin: Path = REFERENTIEL_YAML) -> VentilationReferentiel:
    """Charge et VALIDE le référentiel de ventilation (contrat pydantic strict, #46)."""
    brut = yaml.safe_load(Path(chemin).read_text(encoding="utf-8")) or {}
    try:
        return VentilationReferentiel.model_validate(brut)
    except Exception as e:  # ValidationError pydantic, mais on ne nomme pas la dépendance ici
        raise ReferentielVentilationInvalide(f"référentiel de ventilation invalide ({chemin}) : {e}") from e


# ── Les dépôts, tels que lus par l'appelant (`ventilation_feed.py` / l'outil / les fixtures) ──────

@dataclass(frozen=True)
class Depot:
    accn: str
    form: str
    filed: str
    faits: tuple[FaitDimensionne, ...]
    etiquettes: dict[str, str] = field(default_factory=dict)
    hierarchie: dict[str, str] = field(default_factory=dict)
    # Les conflits de hiérarchie DÉJÀ rendus par `ventilation_xbrl.lire_hierarchie` (son 2ᵉ membre
    # de tuple) — jamais tus : `relever` les reporte tels quels dans `Ventilation.conflits`.
    conflits: tuple[str, ...] = ()


# ── Les issues du relevé ────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CelluleVentilation:
    axe: str
    ligne: str                      # nom de la ligne du gabarit, ou "__proportion__" (axe `clients`)
    membre: str
    periode: str                    # id de période du socle, « cumul du D au F », ou la fin ISO (`clients`)
    valeur: float
    concept: str
    accn: str
    libelle_membre: str
    parent: Optional[str] = None
    base: Optional[str] = None      # axe `clients` seulement : "{axe_qualifiant}={membre}" trié
    # Un FLUX porte ses dates (les douze mois de la vue servie reconnaissent un terme par sa DURÉE,
    # #42/#112, jamais par son identifiant) ; `None` pour un instant ou une proportion.
    debut: Optional[str] = None
    fin: Optional[str] = None


@dataclass(frozen=True)
class TotalCumul:
    """Le total consolidé (fait SANS dimension) d'un cumul depuis le début de l'exercice, lu dans le
    dépôt qui le publie — le socle ne porte pas de cumul, le raccord de la vue en a besoin."""
    ligne: str
    periode: str
    valeur: float
    accn: str


@dataclass(frozen=True)
class NonRattache:
    axe: str
    membre: str
    periode: str
    concept: str
    valeur: float
    accn: str


@dataclass(frozen=True)
class SousDetail:
    concept: str
    membres: tuple[tuple[str, str], ...]
    periode: str
    valeur: float
    accn: str


@dataclass
class Ventilation:
    """Le RELEVÉ BRUT, par dépôt (lot P1 §8 point 1) — aucune décision de périmètre : ni membre
    « nouveau », ni « découpage changé », ni douze mois, ni raccord. Tout cela se calcule à la
    lecture, dans `perimetre.vue_servie`, seul point d'entrée des lecteurs (§8 point 2)."""
    statut: Literal["ventilee", "secteur_unique", "sans_ventilation"]
    axes: tuple[str, ...]
    cellules: list[CelluleVentilation]
    totaux_cumul: list[TotalCumul]
    non_rattaches: list[NonRattache]
    sous_details: list[SousDetail]
    conflits: list[str]
    refus: list[str]
    # §4 bis (lot P1) — le SIGNAL d'acquisition significative (jamais la croissance hors
    # acquisitions, module ad hoc ultérieur), produit par `perimetre.signal_acquisition_significative`
    # à partir des faits XBRL de regroupement d'entreprises DÉJÀ LUS avec les dépôts.
    signaux_acquisition: list[SignalAcquisition] = field(default_factory=list)


# ── Le classement d'un fait (§4.1) ─────────────────────────────────────────────────────────────

def _concepts_vers_ligne(gabarit: Gabarit) -> dict[str, str]:
    """concept → id de ligne, pour les RECETTES À UN SEUL CONCEPT du gabarit (détenteur unique des
    concepts, #46 — un concept lu par deux lignes de recettes à un terme n'a pas de ligne unique,
    il va en `non_rattaches` plutôt que d'être deviné)."""
    vus: dict[str, set[str]] = {}
    for ligne in gabarit.lignes.values():
        for recette in ligne.recettes:
            if len(recette) == 1:
                vus.setdefault(recette[0], set()).add(ligne.id)
    return {c: next(iter(ls)) for c, ls in vus.items() if len(ls) == 1}


def _classer(
    membres: tuple[tuple[str, str], ...], axe_def: AxeVentilation, referentiel: VentilationReferentiel,
) -> Optional[tuple[str, dict[str, str]]]:
    """Si le fait relève de CET axe, rend `(membre, base)` — `base` = les qualificateurs admis
    rencontrés (vide hors `clients`). `None` si l'axe n'est pas touché, OU si un axe en trop
    (non déclaré qualificateur) disqualifie le fait — l'appelant en fait un sous-détail."""
    neutres = {(q.axe, q.membre) for q in referentiel.qualificateurs_neutres}
    restants = [(a, m) for (a, m) in membres if (a, m) not in neutres]
    de_cet_axe = [(a, m) for (a, m) in restants if a == axe_def.axe]
    autres = [(a, m) for (a, m) in restants if a != axe_def.axe]
    if len(de_cet_axe) != 1:
        return None
    if autres:
        admis = set(axe_def.qualificateurs)
        hors = [(a, m) for a, m in autres if a not in admis]
        if hors:
            return None
    return de_cet_axe[0][1], {a: m for a, m in autres}


def _touche_un_axe(membres: tuple[tuple[str, str], ...], referentiel: VentilationReferentiel) -> bool:
    axes_connus = {a.axe for a in referentiel.axes}
    return any(a in axes_connus for a, _ in membres)


_PREFIXE_GABARIT = "us-gaap:"


def _ligne_du_concept(concept: str, concepts_ligne: dict[str, str]) -> Optional[str]:
    """Le gabarit (`socle_comptes.yaml`) nomme ses recettes SANS préfixe de taxonomie (toujours
    `us-gaap:`, la seule que `fetch_company_facts`/le socle lisent) ; `FaitDimensionne.concept` est
    résolu AVEC son préfixe (#3 de `ventilation_xbrl`). On ôte le préfixe `us-gaap:` avant de
    chercher — un concept d'une autre taxonomie (`srt:`, `dei:`…) n'appartient à aucune recette."""
    if not concept.startswith(_PREFIXE_GABARIT):
        return None
    return concepts_ligne.get(concept[len(_PREFIXE_GABARIT):])


# ── §4 bis — les faits XBRL de regroupement d'entreprises, DÉJÀ LUS avec les dépôts ───────────────

# Concepts us-gaap STANDARD de regroupement d'entreprises (aucun nom propre à un émetteur, #46) :
# la contrepartie totale transférée, et — quand l'émetteur la publie — le chiffre d'affaires de
# l'entité acquise (réel depuis la date d'acquisition, ou pro forma).
_CONCEPT_CONTREPARTIE_REGROUPEMENT = "us-gaap:BusinessCombinationConsiderationTransferred1"
_CONCEPTS_CA_ACQUIS = (
    "us-gaap:BusinessCombinationsRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedRevenueOfAcquiree1",
    "us-gaap:BusinessAcquisitionProFormaRevenue",
)


def faits_regroupement_de_depots(depots: list[Depot]) -> tuple[dict[str, Any], ...]:
    """Les faits XBRL de regroupement d'entreprises, groupés PAR ACQUISITION (le membre déclaré sur
    `us-gaap:BusinessAcquisitionAxis`, quel qu'il soit — jamais un nom propre lu en dur ; `()` si
    l'émetteur ne tague aucune acquisition cette période-ci). Pure, aucun appel réseau : les dépôts
    sont DÉJÀ lus (`ventilation_feed.lire_depots`). Alimente
    `perimetre.signal_acquisition_significative`, jamais un calcul de croissance (§4 bis)."""
    par_acquisition: dict[tuple, dict[str, Any]] = {}
    for depot in depots:
        for f in depot.faits:
            if f.concept == _CONCEPT_CONTREPARTIE_REGROUPEMENT:
                cle = f.membres
                entree = par_acquisition.setdefault(
                    cle, {"date": None, "contrepartie": None, "chiffre_affaires_acquis": None})
                entree["contrepartie"] = f.valeur
                if entree["date"] is None:
                    entree["date"] = f.instant or f.fin
            elif f.concept in _CONCEPTS_CA_ACQUIS:
                cle = f.membres
                entree = par_acquisition.setdefault(
                    cle, {"date": None, "contrepartie": None, "chiffre_affaires_acquis": None})
                if entree["chiffre_affaires_acquis"] is None:
                    entree["chiffre_affaires_acquis"] = f.valeur
                if entree["date"] is None:
                    entree["date"] = f.instant or f.fin
    return tuple(e for e in par_acquisition.values() if e["contrepartie"] is not None)


# ── Le relevé (§4) ──────────────────────────────────────────────────────────────────────────────

def relever(
    depots: list[Depot], gabarit: Gabarit, referentiel: VentilationReferentiel, socle: dict[str, Any],
) -> Ventilation:
    """Le relevé pur, DÉPÔT PAR DÉPÔT. Ne lève jamais : les constats
    (`ventilee`/`secteur_unique`/`sans_ventilation`) sont rendus, pas des échecs.

    Ce que relève chaque dépôt, pour chaque membre d'un axe (aucun membre n'est privilégié — un
    membre « connu du 10-K » n'a plus de statut, lot P1 §8 point 3) : ses exercices clos (période
    d'exercice du socle), ses instants (période de bilan du socle) et ses CUMULS depuis le début
    d'un exercice connu (« cumul du D au F ») ; jamais un cumul trimestriel isolé (il ne commence
    pas au lendemain d'une clôture). Les comparatifs d'un dépôt (le semestre de l'an passé republié
    dans le nouveau découpage) sont relevés au même titre que ses périodes propres : c'est le
    recouvrement qui permet de PROUVER un passage."""
    if not depots:
        return Ventilation("sans_ventilation", (), [], [], [], [], [], ["aucun dépôt fourni"])

    concepts_ligne = _concepts_vers_ligne(gabarit)
    periodes_socle = socle.get("periodes") or []
    fin_vers_fy = {p["fin"]: p["id"] for p in periodes_socle if p["cadrage"] == "flux" and p["nature"] == "exercice"}
    # Un « cumul depuis le début de l'exercice » commence le lendemain d'une clôture d'exercice
    # connue. Un cumul TRIMESTRIEL isolé (ex. le seul T2) ne commence PAS là : il n'est pas relevé.
    debuts_cumul_valides = {str(date.fromisoformat(fy) + timedelta(days=1)) for fy in fin_vers_fy}
    fin_vers_b = {p["fin"]: p["id"] for p in periodes_socle if p["cadrage"] == "instant"}
    cel_socle = socle.get("cellules") or {}

    membres_par_axe: dict[str, set[str]] = {a.id: set() for a in referentiel.axes}
    etiquette: dict[str, str] = {}
    # La hiérarchie est celle DU DÉPÔT qui porte la cellule (lot P1 §8 point 1) — jamais fusionnée.
    parent_de_par_depot: dict[str, dict[str, str]] = {d.accn: dict(d.hierarchie) for d in depots}

    cellules: dict[tuple, CelluleVentilation] = {}
    non_rattaches: list[NonRattache] = []
    sous_details: list[SousDetail] = []
    # (accn, ligne, période) → concept des cellules relevées, pour lire le total du même cumul.
    concepts_cumul: dict[tuple[str, str, str], tuple[str, str, str]] = {}

    for depot in depots:
        for m, lib in depot.etiquettes.items():
            etiquette.setdefault(m, lib)

    for depot in depots:
        parents = parent_de_par_depot[depot.accn]
        for fait in depot.faits:
            if not _touche_un_axe(fait.membres, referentiel):
                continue
            for axe_def in referentiel.axes:
                res = _classer(fait.membres, axe_def, referentiel)
                if res is None:
                    if any(a == axe_def.axe for a, _ in fait.membres):
                        periode_sd = fait.fin or fait.instant or ""
                        sous_details.append(SousDetail(fait.concept, fait.membres, periode_sd, fait.valeur, depot.accn))
                    continue
                membre, base = res
                membres_par_axe[axe_def.id].add(membre)
                etiquette.setdefault(membre, membre.split(":", 1)[-1])

                if axe_def.raccord == "aucun":
                    if fait.concept not in axe_def.concepts:
                        non_rattaches.append(NonRattache(axe_def.id, membre, fait.fin or fait.instant or "", fait.concept, fait.valeur, depot.accn))
                        continue
                    base_txt = ",".join(f"{a}={m}" for a, m in sorted(base.items()))
                    pid = fait.fin or fait.instant or ""
                    # Identité PAR DÉPÔT : l'accn fait partie de la clef — deux dépôts ne se fusionnent
                    # jamais ; au sein d'un même dépôt, le dernier fait rencontré gagne (comportement
                    # d'origine).
                    cle = (axe_def.id, "__proportion__", membre, pid, base_txt, depot.accn)
                    cellules[cle] = CelluleVentilation(
                        axe_def.id, "__proportion__", membre, pid, fait.valeur, fait.concept, depot.accn,
                        etiquette.get(membre, membre), parents.get(membre), base_txt)
                    continue

                ligne = _ligne_du_concept(fait.concept, concepts_ligne)
                if ligne is None:
                    non_rattaches.append(NonRattache(axe_def.id, membre, fait.fin or fait.instant or "", fait.concept, fait.valeur, depot.accn))
                    continue

                debut = fin = None
                if fait.instant is not None:
                    pid = fin_vers_b.get(fait.instant)
                elif fait.fin is not None and fait.debut is not None:
                    debut, fin = fait.debut, fait.fin
                    pid = fin_vers_fy.get(fait.fin)
                    if pid is None and fait.debut in debuts_cumul_valides:
                        pid = f"cumul du {fait.debut} au {fait.fin}"
                        concepts_cumul.setdefault((depot.accn, ligne, pid), (fait.concept, fait.debut, fait.fin))
                else:
                    pid = None
                if pid is None:
                    continue   # cumul trimestriel isolé, ou période hors du socle
                cle = (axe_def.id, ligne, membre, pid, depot.accn)
                if cle not in cellules:
                    cellules[cle] = CelluleVentilation(
                        axe_def.id, ligne, membre, pid, fait.valeur, fait.concept, depot.accn,
                        etiquette.get(membre, membre), parents.get(membre), debut=debut, fin=fin)

    # Le total consolidé de chaque cumul relevé, lu dans les faits SANS DIMENSION du même dépôt
    # (§4.3bis : le socle n'en a pas). Même concept que les cellules du cumul.
    totaux_cumul: list[TotalCumul] = []
    for depot in depots:
        sans_dim = {(f.concept, f.debut, f.fin): f.valeur for f in depot.faits
                    if not f.membres and f.debut and f.fin}
        for (accn, ligne, pid), cle_total in sorted(concepts_cumul.items()):
            if accn == depot.accn and cle_total in sans_dim:
                totaux_cumul.append(TotalCumul(ligne, pid, sans_dim[cle_total], accn))

    # Conflits de hiérarchie : seulement pour les membres RÉELLEMENT en usage — un conflit sur une
    # ligne de bilan ou un pays fiscal que personne ne lit est du bruit, jamais rendu.
    membres_en_usage = {c.membre for c in cellules.values()}
    conflits = [
        c for d in depots for c in d.conflits
        if (m := re.match(r"« ([^»]+) »", c)) and m.group(1) in membres_en_usage
    ]

    # ── Le statut (§4.5) ────────────────────────────────────────────────────────────────────────
    axes_ventiles = tuple(sorted(a_id for a_id, ms in membres_par_axe.items() if len(ms) >= 2))
    if axes_ventiles:
        statut: Literal["ventilee", "secteur_unique", "sans_ventilation"] = "ventilee"
    else:
        secteurs_membres = membres_par_axe.get("secteurs", set())
        if not secteurs_membres or secteurs_membres <= set(referentiel.membres_secteur_unique):
            statut = "secteur_unique"
        else:
            statut = "sans_ventilation"

    # ── §4 bis — le signal d'acquisition significative ──────────────────────────────────────────
    dernier_exercice_fin = max(fin_vers_fy, default=None)
    dernier_exercice_id = fin_vers_fy.get(dernier_exercice_fin) if dernier_exercice_fin else None
    ca_exercice = ((cel_socle.get(f"chiffre_affaires|{dernier_exercice_id}") or {}).get("v")
                  if dernier_exercice_id else None)
    signaux_acquisition = signal_acquisition_significative(
        faits_regroupement_de_depots(depots), chiffre_affaires_exercice=ca_exercice,
        seuil=referentiel.seuil_acquisition_significative)

    return Ventilation(
        statut, axes_ventiles, list(cellules.values()), totaux_cumul, non_rattaches,
        sous_details, conflits, [], signaux_acquisition)


# ── La forme PERSISTÉE, et sa lecture ───────────────────────────────────────────────────────────

def structure_de_ventilation(
    v: Ventilation, *, version_referentiel: str, version_gabarit: str, depots: tuple[Depot, ...],
) -> dict[str, Any]:
    """Le `content_structured` de la pièce : le RELEVÉ BRUT, par dépôt. Pur. `metric =
    "ventilation_publiee"`, `poste_kind = "stock"` (une ventilation courante par émetteur, comme le
    socle, #43). Ses lecteurs passent TOUS par `perimetre.vue_servie` (`forme` = `FORME_STRUCTURE`)."""
    return {
        "metric": METRIC,
        "poste_kind": "stock",
        "forme": FORME_STRUCTURE,
        "statut": v.statut,
        "axes": list(v.axes),
        "version_referentiel": version_referentiel,
        "version_gabarit": version_gabarit,
        "depots": [{"accn": d.accn, "form": d.form, "filed": d.filed} for d in depots],
        "cellules": [
            {"axe": c.axe, "ligne": c.ligne, "membre": c.membre, "periode": c.periode, "v": c.valeur,
             "concept": c.concept, "accn": c.accn, "libelle": c.libelle_membre,
             **({"parent": c.parent} if c.parent else {}), **({"base": c.base} if c.base else {}),
             **({"debut": c.debut, "fin": c.fin} if c.debut and c.fin else {})}
            for c in sorted(v.cellules, key=lambda c: (c.axe, c.ligne, c.membre, c.periode, c.accn))
        ],
        "totaux_cumul": [
            {"ligne": t.ligne, "periode": t.periode, "v": t.valeur, "accn": t.accn}
            for t in sorted(v.totaux_cumul, key=lambda t: (t.ligne, t.periode, t.accn))
        ],
        "non_rattaches": [n.__dict__ for n in v.non_rattaches],
        "sous_details": [
            {"concept": s.concept, "membres": [list(m) for m in s.membres], "periode": s.periode,
             "valeur": s.valeur, "accn": s.accn}
            for s in v.sous_details
        ],
        "conflits": list(v.conflits),
        "refus": list(v.refus),
        "signaux_acquisition": [
            {"date": s.date, "montant": s.montant, "base": s.base, "part_estimee": s.part_estimee}
            for s in v.signaux_acquisition
        ],
    }


def empreinte(structure: dict[str, Any]) -> tuple:
    """Ce qui fait qu'une ventilation publiée est la MÊME qu'une autre — deux relevés identiques
    rendent la même empreinte, une cellule changée une autre (idempotence, [V11]). La FORME en fait
    partie : une pièce d'avant le lot P1 se republie."""
    return (
        structure.get("forme"),
        structure.get("version_referentiel"), structure.get("version_gabarit"), structure.get("statut"),
        tuple(sorted(d.get("accn") for d in structure.get("depots") or [])),
        tuple(sorted(
            (c["axe"], c["ligne"], c["membre"], c["periode"], c.get("accn") or "", c["v"])
            for c in structure.get("cellules") or [])),
    )


# Les grandeurs de référence d'une part de concentration (membres STANDARD de
# `us-gaap:ConcentrationRiskByBenchmarkAxis`) et leur tournure dans le rendu.
GRANDEURS_DE_CONCENTRATION = {
    "us-gaap:SalesRevenueNetMember": "du chiffre d'affaires",
    "us-gaap:RevenueFromContractWithCustomerMember": "du chiffre d'affaires",
    "us-gaap:RevenueBenchmarkMember": "du chiffre d'affaires",
    "us-gaap:AccountsReceivableMember": "des créances clients",
}


def _membre_lisible(membre: Optional[str]) -> str:
    """Un membre sans étiquette lue : son nom local, « Member » ôté, mots séparés."""
    nom = (membre or "").split(":", 1)[-1]
    nom = re.sub(r"(Segment)?Member$", "", nom)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nom) or (membre or "")


def _m(v: Optional[float]) -> str:
    return "?" if v is None else f"{v / 1e6:,.1f}".replace(",", " ")


_PHRASE_TRANSITION = {
    "detail_ajoute": "« {anciens} » est inchangé ; il est désormais détaillé en {nouveaux}",
    "renommage": "« {anciens} » est devenu « {nouveaux} » (même montant sur la période commune)",
    "regroupement": "« {nouveaux} » = {anciens} (addition vérifiée sur la période commune)",
    "scission": "« {anciens} » se répartit désormais en {nouveaux} (vérifié sur la période commune) ; "
                "l'historique des nouvelles parties commence à leur première publication",
    "meme_nom_contenu_change": "« {anciens} » garde son nom mais change de contenu (montants "
                               "différents sur la période commune) : NON COMPARABLE avant la republication",
    "rupture": "{anciens} → {nouveaux} : aucun passage vérifiable par les montants — NON COMPARABLE, "
               "rien n'est reconstitué",
    "axe_apparu": "axe apparu", "axe_disparu": "axe disparu",
}


def rendre_ventilation(vue: dict[str, Any], *, raison_sociale: str,
                       avec_identifiants: bool = False) -> str:
    """Le texte que lit l'analyste (et l'architecte) : la VUE SERVIE (`perimetre.vue_servie`), jamais
    le relevé brut — un relevé brut porte plusieurs découpages et plusieurs dépôts pour la même
    période ; le rendre tel quel laisserait le lecteur additionner deux découpages (lot P1 §8 point
    2). Tamponné `mesure` (#110) : aucun des mots qui annoncent une dérivation (`derive_nature`)
    n'apparaît ici — un chiffre reconstitué est dit « addition vérifiée », un reste « non ventilé ».

    Par axe : les découpages successifs et leur passage, en phrases ; puis l'historique dans le
    découpage de RÉFÉRENCE (le plus récent publié), chaque chiffre reconstitué marqué ; les périodes
    incomplètes et le point de départ manquant, nommés ; enfin l'ancien découpage tel que publié.

    `avec_identifiants=True` (lot M3, §3.2) : chaque membre est suivi de son adresse
    `[axe=<id d'axe du référentiel> membre=<qname XBRL>]` — un modèle ne peut citer un membre XBRL
    qu'on lui montre."""
    if not vue.get("vue"):
        raise ValueError("rendre_ventilation lit la VUE SERVIE (`perimetre.vue_servie`), jamais le "
                         "relevé brut par dépôt")
    out = [
        f"Ventilation publiée de {raison_sociale} relevée dans l'instance XBRL des dépôts "
        f"(référentiel {vue.get('version_referentiel')}, gabarit {vue.get('version_gabarit')}). "
        f"Statut : {vue.get('statut')}.",
    ]
    depots = {d.get("accn"): d for d in vue.get("depots") or []}
    for d in vue.get("depots") or []:
        out.append(f"  Dépôt lu : {d.get('form')} ({d.get('accn')}), déposé le {d.get('filed')}.")

    def _depot_lisible(accn: Optional[str]) -> str:
        d = depots.get(accn) or {}
        return f"{d.get('form', '?')} du {d.get('filed', '?')}"

    cellules = vue.get("cellules") or []
    anterieures = vue.get("cellules_anterieures") or []
    libelle_par_membre = {c["membre"]: c.get("libelle") or c["membre"] for c in anterieures + cellules}
    nouveaux_set = {(m["axe"], m["membre"]) for m in (vue.get("membres_nouveaux") or [])}
    raccords = {(r["axe"], r["ligne"], r["periode"]): r for r in (vue.get("raccords") or [])
                if r["niveau"] == "total"}
    chroniques = {(c["axe"], c["ligne"]): c for c in vue.get("chroniques") or []}
    axes = sorted({c["axe"] for c in cellules} | {c["axe"] for c in anterieures})

    def _libs(membres) -> str:
        return ", ".join(libelle_par_membre.get(m, m) for m in membres)

    if avec_identifiants and axes:
        # Cause ② (lot M3 bis, §3) : le rendu DIT ce qu'est un axe — deux axes se croisent, ils ne
        # s'emboîtent pas entre eux ; chacun répartit le MÊME chiffre d'affaires total (#69).
        out.append("")
        out.append(
            "Chaque axe répartit le MÊME chiffre d'affaires total de l'émetteur selon un critère "
            "différent. Deux axes se CROISENT : un membre d'un axe n'est JAMAIS contenu dans un "
            "membre d'un autre axe. L'emboîtement n'existe qu'À L'INTÉRIEUR d'un axe (marqué ↳ "
            "ci-dessous). Chaque axe est rendu dans son découpage le PLUS RÉCENT ; un chiffre "
            "« addition vérifiée » est la somme exacte d'anciens membres publiés ; un découpage "
            "antérieur est montré à part, tel que publié, et ne s'additionne jamais avec le récent.")
        for axe in axes:
            sommes_axe = {k: r for k, r in raccords.items() if k[0] == axe and k[1] == "chiffre_affaires"}
            if sommes_axe:
                out.append(f"  Axe « {axe} » — Σ des membres de premier niveau vs. chiffre d'affaires des comptes :")
                for (_, _, periode), r in sorted(sommes_axe.items(), key=lambda kv: ordre_des_periodes(kv[0][2])):
                    total_fmt = f"{_m(r.get('total'))} M$" if r.get("total") is not None else "inconnu"
                    out.append(f"    {periode} : Σ = {_m(r.get('somme'))} M$ ; chiffre d'affaires des comptes = {total_fmt}")

    for axe in axes:
        out.append("")
        out.append(f"— Axe « {axe} » —")
        chron_ca = chroniques.get((axe, "chiffre_affaires")) or next(
            (c for (a, _l), c in sorted(chroniques.items()) if a == axe), None)
        if chron_ca is not None and len(chron_ca["regimes"]) > 1:
            out.append("  Découpages successifs publiés (le plus récent fait foi) :")
            for r in chron_ca["regimes"]:
                out.append(f"    · {_libs(r['premier_niveau'])} — publié par "
                           f"{', '.join(_depot_lisible(a) for a in r['depots'])}")
            out.append("  Passage de l'un à l'autre (établi par les montants, sur une période publiée dans les deux) :")
            for t in chron_ca["transitions"]:
                gabarit_phrase = _PHRASE_TRANSITION.get(t["type"], t["type"])
                out.append("    · " + gabarit_phrase.format(
                    anciens=_libs(t["anciens"]), nouveaux=_libs(t["nouveaux"]))
                    + (f" [période commune : {t['periode_recouvrement']}]" if t.get("periode_recouvrement") else ""))
            if chron_ca.get("comparable_depuis"):
                out.append(f"  Série comparable dans le découpage le plus récent depuis : {chron_ca['comparable_depuis']}.")

        lignes = sorted({(c["ligne"], c["periode"]) for c in cellules if c["axe"] == axe and c["ligne"] != "__proportion__"},
                        key=lambda lp: (lp[0], ordre_des_periodes(lp[1])))
        for ligne, periode in lignes:
            membres_ici = {c["membre"]: c for c in cellules
                           if c["axe"] == axe and c["ligne"] == ligne and c["periode"] == periode}
            parent_de_ici = {m: c.get("parent") for m, c in membres_ici.items()}
            premier_niveau = sorted(premier_niveau_de(membres_ici, parent_de_ici))
            calcule = any(c.get("concept") == CONCEPT_DOUZE_MOIS for c in membres_ici.values())
            out.append(f"  {ligne} — {periode}" + (" (douze mois calculés : exercice + cumul − cumul comparable)" if calcule else "") + " :")

            def _imprimer(m: str, profondeur: int) -> None:
                c = membres_ici[m]
                prefixe = "    " + "  " * profondeur + ("↳ " if profondeur else "")
                marque = " (NOUVEAU)" if (axe, m) in nouveaux_set else ""
                adresse = f" [axe={axe} membre={m}]" if avec_identifiants else ""
                origine = ""
                if c.get("origine") == "passage":
                    origine = (f" — addition vérifiée : {_libs(c['passage_de'])}" if c.get("passage_de")
                               else " — dont terme(s) par addition vérifiée")
                out.append(f"{prefixe}{c.get('libelle') or m}{marque}{adresse} : {_m(c['v'])} M${origine}")
                for e in sorted(x for x in membres_ici if membres_ici[x].get("parent") == m):
                    _imprimer(e, profondeur + 1)

            for m in premier_niveau:
                _imprimer(m, 0)

            r = raccords.get((axe, ligne, periode))
            if r is not None:
                # La ligne de raccord porte UNIQUEMENT sur le premier niveau (#4.4).
                if r["statut"] == "boucle":
                    out.append(f"    (premier niveau boucle avec le total publié : {_m(r['total'])} M$)")
                elif r["statut"] == "sans_total":
                    out.append("    (pas de total publié pour cette période — raccord non établi)")
                else:
                    out.append(f"    non ventilé (reste au total publié) : {_m(r['reste'])} M$")

        for (a, ligne), ch in sorted(chroniques.items()):
            if a != axe:
                continue
            for inc in ch.get("periodes_incompletes") or []:
                out.append(f"  {ligne} — {inc['periode']} : série incomplète, sans valeur pour "
                           f"{_libs(inc['manquants'])} — la somme n'est pas jugée contre le total")
            if ch.get("douze_mois_non_etablis"):
                out.append(f"  {ligne} — douze mois non établis pour "
                           f"{_libs([d['membre'] for d in ch['douze_mois_non_etablis']])} "
                           f"(un terme n'est pas publié dans le découpage le plus récent)")
            if ch.get("point_de_depart_manquant"):
                out.append(f"  {ligne} — POINT DE DÉPART MANQUANT au dernier exercice ({ch.get('dernier_exercice')}) "
                           f"pour {_libs(ch['point_de_depart_manquant'])}")

        ant = [c for c in anterieures if c["axe"] == axe]
        if ant:
            out.append("  Découpage antérieur, tel que publié (pour information — ne s'additionne pas avec le découpage le plus récent) :")
            for ligne, periode in sorted({(c["ligne"], c["periode"]) for c in ant},
                                         key=lambda lp: (lp[0], ordre_des_periodes(lp[1]))):
                ici = {c["membre"]: c for c in ant if c["ligne"] == ligne and c["periode"] == periode}
                parents_ici = {m: c.get("parent") for m, c in ici.items()}
                morceaux: list[str] = []

                def _morceau(m: str, profondeur: int) -> None:
                    if profondeur > len(ici):   # hiérarchie cyclique : borne, jamais une récursion sans fin
                        return
                    c = ici[m]
                    adresse = f" [axe={axe} membre={m}]" if avec_identifiants else ""
                    morceaux.append(f"{'↳ ' * profondeur}{c.get('libelle') or m}{adresse} {_m(c['v'])}")
                    for e in sorted((x for x in ici if parents_ici.get(x) == m),
                                    key=lambda x: ici[x].get("libelle") or x):
                        _morceau(e, profondeur + 1)

                for m in sorted(premier_niveau_de(ici, parents_ici), key=lambda x: ici[x].get("libelle") or x):
                    _morceau(m, 0)
                ici = list(ici.values())
                out.append(f"    {ligne} — {periode} ({_depot_lisible(ici[0]['accn'])}) : " + " ; ".join(morceaux) + " M$")

        # Clients : phrases dédiées — la base est le membre du qualificateur SECTEUR s'il y en a un,
        # sinon « l'ensemble consolidé ». La GRANDEUR rapportée est le membre de
        # `ConcentrationRiskByBenchmarkAxis` : une part des créances clients n'est pas une part des
        # ventes. Une grandeur inconnue ou absente est nommée telle quelle.
        clients = sorted((c for c in cellules if c["axe"] == axe and c["ligne"] == "__proportion__"),
                         key=lambda c: (c["periode"], c.get("libelle") or ""))
        for c in clients:
            paires = [p.split("=", 1) for p in (c.get("base") or "").split(",") if "=" in p]
            segment = next((m for a, m in paires if a.endswith("StatementBusinessSegmentsAxis")), None)
            base_lib = (libelle_par_membre.get(segment) or _membre_lisible(segment)) if segment \
                else "l'ensemble consolidé"
            reference = next((m for a, m in paires if a.endswith("ConcentrationRiskByBenchmarkAxis")), None)
            grandeur = GRANDEURS_DE_CONCENTRATION.get(reference) if reference else None
            if grandeur is None:
                grandeur = (f"de la grandeur « {_membre_lisible(reference)} »" if reference
                            else "d'une grandeur non déclarée au dépôt")
            out.append(
                f"  Le client « {c['libelle']} » représente {c['v'] * 100:.0f} % {grandeur} "
                f"de {base_lib}, période au {c['periode']}.")

    if vue.get("non_rattaches"):
        out.append("")
        out.append(f"Faits sur un axe retenu sans recette du gabarit (non rattachés) : {len(vue['non_rattaches'])}.")
    if vue.get("sous_details"):
        out.append(f"Sous-détails (un axe de plus que la publication) : {len(vue['sous_details'])}.")

    # Membres nouveaux : apparus avec le découpage le plus récent — le libellé et le PARENT ; leurs
    # valeurs sont dans les tableaux ci-dessus (marquées « NOUVEAU »).
    if nouveaux_set:
        out.append("")
        out.append("Membres apparus avec le découpage le plus récent :")
        parent_par_membre = {c["membre"]: c.get("parent") for c in cellules if c.get("parent")}
        for axe_id, membre in sorted(nouveaux_set):
            parent = parent_par_membre.get(membre)
            parent_lib = libelle_par_membre.get(parent) if parent and parent in libelle_par_membre else None
            out.append(f"  {axe_id} / {libelle_par_membre.get(membre, membre)}"
                       + (f" (enfant de {parent_lib})" if parent_lib else ""))

    if vue.get("refus"):
        out.append("")
        out.append("Refus nommés (erreurs du relevé, jamais tues) :")
        for r in vue["refus"]:
            out.append(f"  {r}")

    # §4 bis — le signal d'acquisition significative (jamais la croissance hors acquisitions).
    signaux = vue.get("signaux_acquisition") or []
    if signaux:
        out.append("")
        out.append("Signal d'acquisition significative (faits XBRL de regroupement d'entreprises) :")
        for s_ in signaux:
            base_txt = ("du chiffre d'affaires acquis publié" if s_["base"] == "chiffre_affaires_acquis"
                       else "de la contrepartie rapportée à la capitalisation")
            out.append(
                f"  croissance qui inclut une acquisition : {s_['date'] or 'date inconnue'}, "
                f"{_m(s_['montant'])} M$ de contrepartie, part estimée {s_['part_estimee'] * 100:.1f} % {base_txt}")
    return "\n".join(out)
