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
from app.knowledge.appariement_feed import AppariementInexecutable, douze_mois_glissants
from app.knowledge.socle_comptes import Gabarit, tolerance_bouclage
from app.knowledge.ventilation_xbrl import FaitDimensionne

REFERENTIEL_YAML = Path(__file__).resolve().parent / "ventilation_publiee.yaml"

METRIC = "ventilation_publiee"


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
    periode: str                    # id de période du socle, ou la fin ISO pour `clients`
    valeur: float
    concept: str
    accn: str
    libelle_membre: str
    parent: Optional[str] = None
    base: Optional[str] = None      # axe `clients` seulement : "{axe_qualifiant}={membre}" trié


@dataclass(frozen=True)
class Raccord:
    axe: str
    ligne: str
    periode: str
    statut: Literal["boucle", "non_ventile", "decoupage_change", "ecart", "sans_total"]
    total: Optional[float]
    somme: Optional[float]
    reste: Optional[float] = None
    niveau: Literal["total", "emboitement"] = "total"
    parent: Optional[str] = None
    # `decoupage_change` seulement : les membres de premier niveau présents à l'exercice de
    # RÉFÉRENCE mais absents de CETTE période — un redécoupage de l'axe, jamais un montant non
    # affecté (demande du coordinateur, 2026-10-21 : NVDA Data Center → {Hyperscale, AI Clouds} +
    # Edge Computing au 10-Q, Gaming/ProViz/Automotive/OEM absents du TTM).
    membres_manquants: tuple[str, ...] = ()


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


@dataclass(frozen=True)
class MembreNouveau:
    axe: str
    membre: str
    accn: str


@dataclass
class Ventilation:
    statut: Literal["ventilee", "secteur_unique", "sans_ventilation"]
    axes: tuple[str, ...]
    cellules: list[CelluleVentilation]
    raccords: list[Raccord]
    membres_nouveaux: list[MembreNouveau]
    non_rattaches: list[NonRattache]
    sous_details: list[SousDetail]
    conflits: list[str]
    refus: list[str]


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


# ── Le relevé (§4) ──────────────────────────────────────────────────────────────────────────────

def relever(
    depots: list[Depot], gabarit: Gabarit, referentiel: VentilationReferentiel, socle: dict[str, Any],
) -> Ventilation:
    """Le relevé pur, raccordé au socle EN VIGUEUR. Ne lève jamais : les constats
    (`ventilee`/`secteur_unique`/`sans_ventilation`) sont rendus, pas des échecs."""
    if not depots:
        return Ventilation("sans_ventilation", (), [], [], [], [], [], [], ["aucun dépôt fourni"])

    concepts_ligne = _concepts_vers_ligne(gabarit)
    periodes_socle = socle.get("periodes") or []
    fin_vers_fy = {p["fin"]: p["id"] for p in periodes_socle if p["cadrage"] == "flux" and p["nature"] == "exercice"}
    # Un « cumul depuis le début de l'exercice » commence le lendemain d'une clôture d'exercice
    # connue (l'exercice en cours, ou l'exercice comparable). Un cumul TRIMESTRIEL isolé (ex. le
    # seul T2) ne commence PAS là — il est écarté de la capture « membres nouveaux » (§4.3bis,
    # demande du coordinateur 2026-10-21 : NVDA publie aussi un cumul T2 seul, qui n'est pas « le
    # cumul de l'exercice en cours »).
    debuts_cumul_valides = {str(date.fromisoformat(fy) + timedelta(days=1)) for fy in fin_vers_fy}
    fin_vers_b = {p["fin"]: p["id"] for p in periodes_socle if p["cadrage"] == "instant"}
    periode_ttm = next((p for p in periodes_socle if p.get("nature") == "douze_mois"), None)
    cel_socle = socle.get("cellules") or {}
    id_vers_periode = {p["id"]: p for p in periodes_socle}

    k10 = next((d for d in depots if d.form.startswith("10-K")), depots[0])
    membres_k10: dict[str, set[str]] = {}
    membres_par_axe: dict[str, set[str]] = {a.id: set() for a in referentiel.axes}
    etiquette: dict[str, str] = {}
    parent_de: dict[str, str] = {}
    conflits: list[str] = []
    # Fenêtre (début, fin) de chaque période « cumul du … au … » (§4.3bis — membres nouveaux,
    # demande du coordinateur 2026-10-21) : un cumul du 10-Q n'a pas d'id dans le socle.
    cumul_fenetres: dict[str, tuple[str, str]] = {}
    # Les faits SANS AUCUNE dimension — seule source de « total » pour un raccord sur un cumul,
    # le socle n'en ayant pas (§4.3bis : « un raccord sur le cumul est permis s'il existe un total
    # du même cumul dans les faits sans dimension du 10-Q »).
    faits_sans_dim: dict[tuple[str, str, str], float] = {}
    for depot in depots:
        for f in depot.faits:
            if not f.membres and f.debut and f.fin:
                faits_sans_dim.setdefault((f.concept, f.debut, f.fin), f.valeur)

    cellules: dict[tuple, CelluleVentilation] = {}
    non_rattaches: list[NonRattache] = []
    sous_details: list[SousDetail] = []
    membres_nouveaux: list[MembreNouveau] = []

    for depot in depots:
        for m, p in depot.hierarchie.items():
            parent_de.setdefault(m, p)
        for m, lib in depot.etiquettes.items():
            etiquette.setdefault(m, lib)

    for depot in depots:
        est_k10 = depot is k10
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
                if est_k10:
                    membres_k10.setdefault(axe_def.id, set()).add(membre)
                elif membre not in membres_k10.get(axe_def.id, set()):
                    if not any(m.axe == axe_def.id and m.membre == membre for m in membres_nouveaux):
                        membres_nouveaux.append(MembreNouveau(axe_def.id, membre, depot.accn))
                    # Un membre nouveau PORTE sa valeur (§4.3bis, demande du coordinateur) : c'est
                    # l'information la plus précieuse du dépôt (NVDA publie désormais elle-même le
                    # poids de ses grands hébergeurs). Axe `raccord: aucun` (clients) : la MÊME
                    # forme de cellule `__proportion__` que les membres déjà connus. Axe `raccord:
                    # total` : une période « cumul du … au … », jamais mêlée aux exercices ni au
                    # TTM — et seulement un cumul DEPUIS LE DÉBUT DE L'EXERCICE (`debuts_cumul_
                    # valides`), jamais un cumul trimestriel isolé (NVDA publie aussi le T2 seul).
                    if axe_def.raccord == "aucun":
                        if fait.concept in axe_def.concepts:
                            base_txt = ",".join(f"{a}={m}" for a, m in sorted(base.items()))
                            pid = fait.fin or fait.instant or ""
                            cle = (axe_def.id, "__proportion__", membre, pid, base_txt)
                            cellules[cle] = CelluleVentilation(
                                axe_def.id, "__proportion__", membre, pid, fait.valeur, fait.concept,
                                depot.accn, etiquette.get(membre, membre), parent_de.get(membre), base_txt)
                    elif axe_def.raccord == "total" and fait.debut in debuts_cumul_valides and fait.fin:
                        ligne_nouv = _ligne_du_concept(fait.concept, concepts_ligne)
                        if ligne_nouv is not None:
                            pid_cumul = f"cumul du {fait.debut} au {fait.fin}"
                            cumul_fenetres[pid_cumul] = (fait.debut, fait.fin)
                            cle_cumul = (axe_def.id, ligne_nouv, membre, pid_cumul)
                            if cle_cumul not in cellules:
                                cellules[cle_cumul] = CelluleVentilation(
                                    axe_def.id, ligne_nouv, membre, pid_cumul, fait.valeur, fait.concept,
                                    depot.accn, etiquette.get(membre, membre), parent_de.get(membre))
                    continue

                if axe_def.raccord == "aucun":
                    if fait.concept not in axe_def.concepts:
                        non_rattaches.append(NonRattache(axe_def.id, membre, fait.fin or fait.instant or "", fait.concept, fait.valeur, depot.accn))
                        continue
                    base_txt = ",".join(f"{a}={m}" for a, m in sorted(base.items()))
                    pid = fait.fin or fait.instant or ""
                    cle = (axe_def.id, "__proportion__", membre, pid, base_txt)
                    cellules[cle] = CelluleVentilation(
                        axe_def.id, "__proportion__", membre, pid, fait.valeur, fait.concept, depot.accn,
                        etiquette.get(membre, membre), parent_de.get(membre), base_txt)
                    continue

                ligne = _ligne_du_concept(fait.concept, concepts_ligne)
                if ligne is None:
                    non_rattaches.append(NonRattache(axe_def.id, membre, fait.fin or fait.instant or "", fait.concept, fait.valeur, depot.accn))
                    continue

                pid = None
                if fait.instant is not None:
                    pid = fin_vers_b.get(fait.instant)
                elif fait.fin is not None and fait.debut is not None:
                    pid = fin_vers_fy.get(fait.fin)
                if pid is None:
                    continue   # cumul non annuel isolé : traité par le passage « douze mois » ci-dessous
                cle = (axe_def.id, ligne, membre, pid)
                if cle not in cellules:
                    cellules[cle] = CelluleVentilation(
                        axe_def.id, ligne, membre, pid, fait.valeur, fait.concept, depot.accn,
                        etiquette.get(membre, membre), parent_de.get(membre))

    # ── Rattraper la valeur du PARENT d'un membre nouveau, À LA MÊME FENÊTRE (§4.3bis) ─────────────
    # Sans elle, l'emboîtement ne peut jamais se juger : Data Center (préexistant) n'a sinon aucune
    # cellule au cumul du 10-Q pour s'opposer à ses enfants nouveaux (Hyperscale, AI Clouds…).
    for cle, c in list(cellules.items()):
        if len(cle) != 4 or not cle[3].startswith("cumul du "):
            continue
        axe_id, ligne, membre, pid_cumul = cle
        parent = parent_de.get(membre)
        if parent is None or (axe_id, ligne, parent, pid_cumul) in cellules:
            continue
        axe_def = next(a for a in referentiel.axes if a.id == axe_id)
        debut, fin = cumul_fenetres[pid_cumul]
        for depot in depots:
            trouve = None
            for f in depot.faits:
                if f.concept != c.concept or f.debut != debut or f.fin != fin:
                    continue
                res = _classer(f.membres, axe_def, referentiel)
                if res is not None and res[0] == parent:
                    trouve = f
                    break
            if trouve is not None:
                cellules[(axe_id, ligne, parent, pid_cumul)] = CelluleVentilation(
                    axe_id, ligne, parent, pid_cumul, trouve.valeur, trouve.concept, depot.accn,
                    etiquette.get(parent, parent), parent_de.get(parent))
                break

    # ── Douze mois glissants (§4.2) : l'identité comptable de `appariement_feed`, détenteur unique ──
    if periode_ttm is not None and len(depots) > 1:
        points: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for depot in depots:
            for fait in depot.faits:
                if fait.instant is not None or fait.fin is None:
                    continue
                for axe_def in referentiel.axes:
                    if axe_def.raccord != "total":
                        continue
                    res = _classer(fait.membres, axe_def, referentiel)
                    if res is None:
                        continue
                    membre, _base = res
                    if membre not in membres_k10.get(axe_def.id, set()):
                        continue   # membre nouveau au 10-Q : pas de douze mois (§4.2)
                    ligne = _ligne_du_concept(fait.concept, concepts_ligne)
                    if ligne is None:
                        continue
                    points.setdefault((axe_def.id, ligne, membre), []).append({
                        "start": fait.debut, "end": fait.fin, "val": fait.valeur,
                        "form": depot.form, "accn": depot.accn, "filed": depot.filed,
                    })
        fin_ttm = date.fromisoformat(periode_ttm["fin"])
        for (axe_id, ligne, membre), pts in points.items():
            try:
                valeur, _compo = douze_mois_glissants(pts, fin_ttm, f"{axe_id}:{ligne}:{membre}")
            except AppariementInexecutable:
                continue
            accn_plus_recent = max((p["accn"] for p in pts if p.get("accn")), default="")
            cle = (axe_id, ligne, membre, periode_ttm["id"])
            cellules[cle] = CelluleVentilation(
                axe_id, ligne, membre, periode_ttm["id"], valeur, "(douze mois glissants)",
                accn_plus_recent, etiquette.get(membre, membre), parent_de.get(membre))

    # Conflits de hiérarchie : seulement pour les membres RÉELLEMENT en usage (une cellule, ou un
    # membre nouveau) — un conflit sur une ligne de bilan ou un pays fiscal que personne ne lit
    # est du bruit, jamais rendu (demande du coordinateur, 2026-10-21).
    membres_en_usage = {c.membre for c in cellules.values()} | {m.membre for m in membres_nouveaux}
    conflits = [
        c for d in depots for c in d.conflits
        if (m := re.match(r"« ([^»]+) »", c)) and m.group(1) in membres_en_usage
    ]

    # ── Le raccord (§4.4) ───────────────────────────────────────────────────────────────────────
    raccords: list[Raccord] = []
    groupes: dict[tuple[str, str, str], set[str]] = {}
    for c in cellules.values():
        if c.ligne == "__proportion__":
            continue
        groupes.setdefault((c.axe, c.ligne, c.periode), set()).add(c.membre)

    def _premier_niveau_de(axe_id: str, ligne: str, periode: str) -> set[str]:
        presents_p = groupes.get((axe_id, ligne, periode), set())
        return {m for m in presents_p if parent_de.get(m) not in presents_p}

    def _reference(axe_id: str, ligne: str) -> Optional[str]:
        """Le dernier exercice CLOS présent pour cet axe+ligne — la publication la plus récente
        fait foi (#133), jamais un repli arbitraire. `None` si aucun exercice n'est présent."""
        candidats = [pid for (a, l, pid) in groupes if a == axe_id and l == ligne
                    and pid in id_vers_periode and id_vers_periode[pid].get("nature") == "exercice"]
        return max(candidats, key=lambda pid: id_vers_periode[pid]["fin"]) if candidats else None

    for (axe_id, ligne, periode), presents in groupes.items():
        axe_def = next(a for a in referentiel.axes if a.id == axe_id)
        if axe_def.raccord != "total":
            continue
        premier_niveau = {m for m in presents if parent_de.get(m) not in presents}
        valeurs = {m: cellules[(axe_id, ligne, m, periode)].valeur for m in presents}
        somme = sum(valeurs[m] for m in premier_niveau)

        total: Optional[float] = None
        est_cumul = periode in cumul_fenetres
        if est_cumul:
            debut, fin = cumul_fenetres[periode]
            concept_use = next((cellules[(axe_id, ligne, m, periode)].concept for m in presents), None)
            total = faits_sans_dim.get((concept_use, debut, fin)) if concept_use else None
        else:
            c_socle = cel_socle.get(f"{ligne}|{periode}")
            if c_socle is not None and c_socle.get("v") is not None:
                total = float(c_socle["v"])

        if total is None:
            raccords.append(Raccord(axe_id, ligne, periode, "sans_total", None, somme))
        else:
            reste = total - somme
            statut: Literal["boucle", "non_ventile", "decoupage_change"] = (
                "boucle" if abs(reste) <= tolerance_bouclage(total, somme) else "non_ventile")
            manquants: tuple[str, ...] = ()
            if statut != "boucle" and not est_cumul:
                ref_pid = _reference(axe_id, ligne)
                if ref_pid is not None and ref_pid != periode:
                    manquants = tuple(sorted(_premier_niveau_de(axe_id, ligne, ref_pid) - presents))
                    if manquants:
                        statut = "decoupage_change"
            raccords.append(Raccord(axe_id, ligne, periode, statut, total, somme, reste,
                                    membres_manquants=manquants))

        # Emboîtement : chaque parent présent avec au moins un enfant présent.
        for parent in presents:
            enfants = {m for m in presents if parent_de.get(m) == parent}
            if not enfants:
                continue
            somme_enfants = sum(valeurs[m] for m in enfants)
            ecart = valeurs[parent] - somme_enfants
            statut_e = "boucle" if abs(ecart) <= tolerance_bouclage(valeurs[parent], somme_enfants) else "ecart"
            raccords.append(Raccord(axe_id, ligne, periode, statut_e, valeurs[parent], somme_enfants, ecart,
                                    niveau="emboitement", parent=parent))

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

    return Ventilation(
        statut, axes_ventiles, list(cellules.values()), raccords, membres_nouveaux, non_rattaches,
        sous_details, conflits, [])


# ── La forme PERSISTÉE, et sa lecture ───────────────────────────────────────────────────────────

def structure_de_ventilation(
    v: Ventilation, *, version_referentiel: str, version_gabarit: str, depots: tuple[Depot, ...],
) -> dict[str, Any]:
    """Le `content_structured` de la pièce. Pur. `metric = "ventilation_publiee"`, `poste_kind =
    "stock"` (une ventilation courante par émetteur, comme le socle, #43)."""
    return {
        "metric": METRIC,
        "poste_kind": "stock",
        "statut": v.statut,
        "axes": list(v.axes),
        "version_referentiel": version_referentiel,
        "version_gabarit": version_gabarit,
        "depots": [{"accn": d.accn, "form": d.form, "filed": d.filed} for d in depots],
        "cellules": [
            {"axe": c.axe, "ligne": c.ligne, "membre": c.membre, "periode": c.periode, "v": c.valeur,
             "concept": c.concept, "accn": c.accn, "libelle": c.libelle_membre,
             **({"parent": c.parent} if c.parent else {}), **({"base": c.base} if c.base else {})}
            for c in sorted(v.cellules, key=lambda c: (c.axe, c.ligne, c.membre, c.periode))
        ],
        "raccords": [
            {"axe": r.axe, "ligne": r.ligne, "periode": r.periode, "statut": r.statut, "total": r.total,
             "somme": r.somme, "reste": r.reste, "niveau": r.niveau,
             **({"parent": r.parent} if r.parent else {}),
             **({"membres_manquants": list(r.membres_manquants)} if r.membres_manquants else {})}
            for r in sorted(v.raccords, key=lambda r: (r.axe, r.ligne, r.periode, r.niveau, r.parent or ""))
        ],
        "membres_nouveaux": [m.__dict__ for m in v.membres_nouveaux],
        "non_rattaches": [n.__dict__ for n in v.non_rattaches],
        "sous_details": [
            {"concept": s.concept, "membres": [list(m) for m in s.membres], "periode": s.periode,
             "valeur": s.valeur, "accn": s.accn}
            for s in v.sous_details
        ],
        "conflits": list(v.conflits),
        "refus": list(v.refus),
    }


def empreinte(structure: dict[str, Any]) -> tuple:
    """Ce qui fait qu'une ventilation publiée est la MÊME qu'une autre — deux relevés identiques
    rendent la même empreinte, une cellule changée une autre (idempotence, [V11])."""
    return (
        structure.get("version_referentiel"), structure.get("version_gabarit"), structure.get("statut"),
        tuple(sorted(d.get("accn") for d in structure.get("depots") or [])),
        tuple(sorted(
            (c["axe"], c["ligne"], c["membre"], c["periode"], c["v"]) for c in structure.get("cellules") or [])),
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


def rendre_ventilation(structure: dict[str, Any], *, raison_sociale: str) -> str:
    """Le texte que lit l'analyste : un tableau par axe, l'emboîtement indenté, la concentration des
    clients en phrases. Tamponné `mesure` (#110) — aucun des mots qui annoncent une dérivation
    (`derive_nature`) n'apparaît ici : un reste de raccord est dit « non ventilé », jamais
    « calculé » ni « par différence »."""
    out = [
        f"Ventilation publiée de {raison_sociale} relevée dans l'instance XBRL des dépôts "
        f"(référentiel {structure.get('version_referentiel')}, gabarit {structure.get('version_gabarit')}). "
        f"Statut : {structure.get('statut')}.",
    ]
    for d in structure.get("depots") or []:
        out.append(f"  Dépôt lu : {d.get('form')} ({d.get('accn')}), déposé le {d.get('filed')}.")

    cellules = structure.get("cellules") or []
    libelle_par_membre = {c["membre"]: c["libelle"] for c in cellules}
    parent_par_membre = {c["membre"]: c["parent"] for c in cellules if c.get("parent")}
    nouveaux_set = {(m["axe"], m["membre"]) for m in (structure.get("membres_nouveaux") or [])}
    raccords = {(r["axe"], r["ligne"], r["periode"]): r for r in (structure.get("raccords") or [])
                if r["niveau"] == "total"}
    axes = sorted({c["axe"] for c in cellules})
    for axe in axes:
        out.append("")
        out.append(f"— Axe « {axe} » —")
        lignes = sorted({(c["ligne"], c["periode"]) for c in cellules if c["axe"] == axe and c["ligne"] != "__proportion__"})
        for ligne, periode in lignes:
            membres_ici = {c["membre"]: c for c in cellules
                           if c["axe"] == axe and c["ligne"] == ligne and c["periode"] == periode}
            presents = set(membres_ici)
            premier_niveau = sorted(m for m in presents if membres_ici[m].get("parent") not in presents)
            out.append(f"  {ligne} — {periode} :")

            def _imprimer(m: str, profondeur: int) -> None:
                c = membres_ici[m]
                prefixe = "    " + "  " * profondeur + ("↳ " if profondeur else "")
                marque = " (NOUVEAU)" if (axe, m) in nouveaux_set else ""
                valeur_fmt = f"{c['v'] / 1e6:,.1f}".replace(",", " ")
                out.append(f"{prefixe}{c['libelle']}{marque} : {valeur_fmt} M$")
                for e in sorted(x for x in presents if membres_ici[x].get("parent") == m):
                    _imprimer(e, profondeur + 1)

            for m in premier_niveau:
                _imprimer(m, 0)

            r = raccords.get((axe, ligne, periode))
            if r is not None:
                # La ligne de raccord porte UNIQUEMENT sur le premier niveau (#4.4) — jamais la
                # somme qu'un lecteur ferait en additionnant aussi les enfants affichés dessous.
                if r["statut"] == "boucle":
                    total_fmt = f"{r['total'] / 1e6:,.1f}".replace(",", " ")
                    out.append(f"    (premier niveau boucle avec le total publié : {total_fmt} M$)")
                elif r["statut"] == "sans_total":
                    out.append("    (pas de total publié pour cette période — raccord non établi)")
                elif r["statut"] == "decoupage_change":
                    manq = ", ".join(libelle_par_membre.get(x, x) for x in (r.get("membres_manquants") or []))
                    reste_fmt = f"{r['reste'] / 1e6:,.1f}".replace(",", " ")
                    out.append(f"    DÉCOUPAGE CHANGÉ — absent(s) depuis l'exercice de référence : {manq} "
                               f"(reste au total : {reste_fmt} M$)")
                else:
                    out.append(f"    non ventilé (reste au total publié) : {r['reste'] / 1e6:,.1f} M$".replace(",", " "))
        # Clients : phrases dédiées — la base est le membre du qualificateur SECTEUR s'il y en a un
        # (`StatementBusinessSegmentsAxis`, toujours le dernier par tri alphabétique des axes dans
        # `base`, #46 : détenteur unique du tri côté `relever`), sinon « l'ensemble consolidé ».
        # La GRANDEUR rapportée est le membre de `ConcentrationRiskByBenchmarkAxis` : une part des
        # créances clients n'est pas une part des ventes (NVDA 10-Q : « A/R Customer A » = 22 % des
        # créances). Une grandeur inconnue ou absente est nommée telle quelle, jamais supposée être
        # le chiffre d'affaires.
        clients = [c for c in cellules if c["axe"] == axe and c["ligne"] == "__proportion__"]
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

    if structure.get("non_rattaches"):
        out.append("")
        out.append(f"Faits sur un axe retenu sans recette du gabarit (non rattachés) : {len(structure['non_rattaches'])}.")
    if structure.get("sous_details"):
        out.append(f"Sous-détails (un axe de plus que la publication) : {len(structure['sous_details'])}.")

    # Membres nouveaux : le libellé, le PARENT, et les valeurs relevées au 10-Q — c'est
    # l'information la plus précieuse du dépôt (demande du coordinateur, 2026-10-21), jamais un
    # simple décompte.
    if nouveaux_set:
        out.append("")
        out.append("Membres nouveaux (apparus depuis le dernier 10-K), relevés au 10-Q :")
        for axe_id, membre in sorted(nouveaux_set):
            cs = sorted((c for c in cellules if c["axe"] == axe_id and c["membre"] == membre),
                       key=lambda c: c["periode"])
            lib = cs[0]["libelle"] if cs else libelle_par_membre.get(membre, membre)
            # Le parent n'est nommé QUE s'il a lui-même une cellule (donc un libellé LU, pas le nom
            # brut d'un domaine XBRL sans traduction) — Edge Computing est un premier niveau, pas
            # un enfant de Data Center, et ne porte donc aucune mention.
            parent = parent_par_membre.get(membre)
            parent_lib = libelle_par_membre.get(parent) if parent and parent in libelle_par_membre else None
            out.append(f"  {axe_id} / {lib}" + (f" (enfant de {parent_lib})" if parent_lib else "") + " :")
            if not cs:
                out.append("    (aucune valeur retenue — hors axe à raccord, ou cumul non identifiable)")
            for c in cs:
                if c["ligne"] == "__proportion__":
                    out.append(f"    {c['periode']} : {c['v'] * 100:.0f} %")
                else:
                    out.append(f"    {c['periode']} : {c['v'] / 1e6:,.1f} M$".replace(",", " "))
    return "\n".join(out)
