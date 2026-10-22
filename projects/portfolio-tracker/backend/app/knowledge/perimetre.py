"""Le détenteur UNIQUE des changements de DÉCOUPAGE et de PÉRIMÈTRE (lot P1, roadmap V3
`14-lot-P1-perimetre.md`, principe fondateur n° 4).

CE QUE CE MODULE REMPLACE (§0.2 de la spec) — six endroits qui décidaient chacun, pour leur besoin
propre, de ce qu'un redécoupage ou un changement de périmètre voulait dire :
  1. `ventilation.relever` (membre « nouveau », statut `decoupage_change`, « exercice de référence »)
  2. `ventilation.rendre_ventilation` (« découpages successifs » recalculés au rendu)
  3. `modele_entreprise.structure._s2_s3b` (période de référence, signal [S3b])
  4. `modele_entreprise.faits_publies` (`parent_de` fusionné entre dépôts, `setdefault`)
  5. la consigne de l'architecte (« choisis-en un, dis lequel et pourquoi »)
  6. `appariement_feed.douze_mois_glissants` (aucun contrôle de régime/retraitement)

Un futur bug de périmètre (fusion de divisions, découpage produits→clients, cession retraitée,
même nom-contenu changé) se reproduit D'ABORD par un cas FICTIF du catalogue
(`checks/fixtures/perimetre/`), puis se corrige ICI — jamais dans un consommateur.

INTERDITS (§1) : aucune règle par libellé ni par nom de membre (un renommage se prouve par les
MONTANTS) ; aucun ticker ; aucun seuil calé sur un cas réel — la tolérance de bouclage est celle de
`socle_comptes.tolerance_bouclage`, détenteur unique, importée ici, jamais recopiée.

Pur : aucun appel réseau, aucune écriture, aucune persistance — une `Chronique` est CALCULÉE À LA
LECTURE (une valeur stockée qui dépend d'un ingrédient non stocké servirait le verdict d'avant le
correctif, `feedback_controle_au_point_de_lecture`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Literal, NamedTuple, Optional

from app.knowledge.socle_comptes import tolerance_bouclage

__all__ = [
    "ordre_des_periodes",
    "premier_niveau_de",
    "CelluleBrute",
    "Regime",
    "Transition",
    "CelluleChronique",
    "Chronique",
    "PerimetreErreur",
    "MAX_MEMBRES_PARTITION",
    "etablir_regimes",
    "typer_transitions",
    "construire_chronique",
    "verifier_invariant_agregat",
    "DOUZE_MOIS_REGIMES_INCOHERENTS",
    "points_douze_mois_coherents",
    "FilingMeta",
    "identifier_jumeau_candidat",
    "regime_a_change",
    "SignalAcquisition",
    "signal_acquisition_significative",
    "LIGNE_RACCORD_OBLIGATOIRE",
    "vue_servie",
]


# ── §2.5 — l'ordre des périodes : une seule clef, sur la date de FIN ────────────────────────────

_RE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def ordre_des_periodes(periode: str) -> tuple:
    """Clef de TRI d'un identifiant de période, sur sa date de FIN (§2.5) — détenteur unique :
    `structure._cle_tri_periode` et `ventilation._cle_periode_rendu` sont deux copies qui trient
    sur la PREMIÈRE date rencontrée, donc sur la date de DÉBUT pour un cumul (« cumul du D au F » :
    `.search` s'arrête à D). Un cumul se classe par sa fin, pas par son début — sinon un semestre
    2025 trié par son début (2025-01-27) se place AVANT un exercice clos le 2024-10-27, alors qu'il
    lui est postérieur.

    Toutes les dates ISO d'un identifiant sont candidates ; la clef retient la PLUS GRANDE (pour une
    période à une seule date, c'est elle-même ; pour « cumul du D au F », D < F donc c'est F). Un
    identifiant sans aucune date ISO (ex. un id opaque) retombe sur son texte brut, trié après toute
    date reconnue — jamais une exception : un ordre partiel reste un ordre.
    """
    dates = _RE_DATE.findall(periode or "")
    if dates:
        return (1, max(dates), periode)
    return (0, "", periode)


def premier_niveau_de(presents, parent_de: dict[str, Optional[str]]) -> frozenset[str]:
    """Les membres de PREMIER NIVEAU d'un ensemble `presents` (ceux dont le parent, dans ce MÊME
    ensemble, n'est pas lui-même présent) — détenteur unique (#46) : `ventilation.relever` (deux
    occurrences) et `modele_entreprise.structure._s2_s3b` recopiaient la même ligne
    (`{m for m in presents if parent_de.get(m) not in presents}`). Pur, O(n)."""
    presents = set(presents)
    return frozenset(m for m in presents if parent_de.get(m) not in presents)


# ── Entrées : les cellules relevées, PAR DÉPÔT (§2, en-tête) ────────────────────────────────────

@dataclass(frozen=True)
class CelluleBrute:
    """Une cellule relevée dans UN dépôt, pour UN axe. `parent` est la hiérarchie DE CE DÉPÔT (pas
    fusionnée — §0.2 point 4, la cause ①). `periode_fin`/`periode_debut` : `periode_debut is None`
    pour un instant (bilan) ; les deux sont renseignés pour un flux (exercice ou cumul)."""
    axe: str
    membre: str
    valeur: float
    periode_fin: str
    depot: str                       # identifiant du dépôt (accn) qui porte CETTE cellule
    periode_debut: Optional[str] = None
    parent: Optional[str] = None


@dataclass(frozen=True)
class Regime:
    """Un régime (§2.1) : l'ensemble des membres de PREMIER NIVEAU d'un axe, sa hiérarchie, les
    périodes couvertes et les dépôts qui le publient. `membres` = TOUS les membres vus (premier
    niveau + enfants) ; `premier_niveau` = ceux dont le parent n'appartient pas à `membres`."""
    axe: str
    premier_niveau: frozenset[str]
    membres: frozenset[str]
    parent_de: dict[str, str]
    periodes: frozenset[str]
    depots: tuple[str, ...]           # triés par ordre d'apparition (le plus récent en dernier)


_TypeTransition = Literal[
    "detail_ajoute", "renommage", "regroupement", "scission",
    "meme_nom_contenu_change", "rupture", "axe_apparu", "axe_disparu",
]


@dataclass(frozen=True)
class Transition:
    """Une transition typée entre deux régimes consécutifs d'un axe (§2.2)."""
    axe: str
    type: _TypeTransition
    periode_recouvrement: Optional[str]
    # Les membres de l'ANCIEN régime qui composent ce mouvement, et celui/ceux du NOUVEAU qui le
    # reçoivent — vide pour axe_apparu/axe_disparu (aucun membre à relier).
    anciens: tuple[str, ...] = ()
    nouveaux: tuple[str, ...] = ()
    motif: str = ""


@dataclass(frozen=True)
class CelluleChronique:
    """Une cellule de la série comparable, dans le régime de RÉFÉRENCE (§2.3)."""
    axe: str
    membre: str
    periode: str
    valeur: float
    origine: Literal["publie", "passage", "hypothese"]
    # `origine == "passage"` : les anciens membres sommés et leur dépôt.
    passage_de: tuple[str, ...] = ()
    passage_depot: Optional[str] = None
    # `origine == "hypothese"` : la méthode, la période des parts, les anciens montants du GROUPE.
    methode: Optional[str] = None
    periode_des_parts: Optional[str] = None
    anciens_montants: Optional[dict[str, float]] = None


@dataclass
class Chronique:
    axe: str
    regime_reference: Regime
    regimes: list[Regime]
    transitions: list[Transition]
    cellules: list[CelluleChronique]
    refus: list[str] = field(default_factory=list)


class PerimetreErreur(Exception):
    """Une ERREUR du module (jamais une rupture) — l'invariant de l'agrégat (§2.3ter) ne boucle
    pas : c'est une faute de ce module, nommée, refusée, jamais absorbée en silence."""


# ── §2.1 — établir les régimes d'un axe ─────────────────────────────────────────────────────────

def etablir_regimes(cellules: list[CelluleBrute], depots_filed: dict[str, str]) -> list[Regime]:
    """Les régimes d'UN axe (toutes les `cellules` doivent porter le même `axe`). `depots_filed` :
    `{depot_id: date_de_dépôt_ISO}` — sert à ordonner les dépôts et à choisir le régime de
    référence (§2.1 : le dépôt le plus récent fait foi, #133).

    Un dépôt = un ensemble de membres de premier niveau (ceux dont le parent, DANS CE DÉPÔT, n'est
    pas lui-même présent dans ce dépôt). Deux dépôts au même ensemble de premier niveau partagent le
    MÊME régime (ses périodes et ses dépôts s'additionnent)."""
    if not cellules:
        return []
    axe = cellules[0].axe
    par_depot: dict[str, list[CelluleBrute]] = {}
    for c in cellules:
        par_depot.setdefault(c.depot, []).append(c)

    brouillons: list[tuple[frozenset[str], frozenset[str], dict[str, str], frozenset[str], str]] = []
    for depot, cs in par_depot.items():
        membres = {c.membre for c in cs}
        parent_de = {c.membre: c.parent for c in cs if c.parent is not None}
        premier_niveau = frozenset(m for m in membres if parent_de.get(m) not in membres)
        periodes = frozenset(c.periode_fin for c in cs)
        brouillons.append((premier_niveau, frozenset(membres), parent_de, periodes, depot))

    valeurs_par_depot: dict[str, dict[tuple[str, str], float]] = {
        depot: {(c.membre, c.periode_fin): c.valeur for c in cs} for depot, cs in par_depot.items()
    }

    def _compatible(depot: str, regime: Regime) -> bool:
        """Faux si `depot` porte, sur une période qu'il PARTAGE avec `regime`, une valeur
        DIFFÉRENTE (hors tolérance) pour un membre qu'ils ont en commun — §2.2
        `meme_nom_contenu_change` : même id, contenu changé, JAMAIS une continuité par le nom. Sans
        ce contrôle, deux dépôts au même premier niveau mais à des valeurs incompatibles
        fusionneraient en un seul régime, et la transition ne se verrait jamais."""
        v_depot = valeurs_par_depot[depot]
        v_regime: dict[tuple[str, str], float] = {}
        for d in regime.depots:
            v_regime.update(valeurs_par_depot[d])
        communs = set(v_depot) & set(v_regime)
        if not communs:
            return True
        tol = tolerance_bouclage(*(v_depot[k] for k in communs), *(v_regime[k] for k in communs))
        return all(abs(v_depot[k] - v_regime[k]) <= tol for k in communs)

    regimes: list[Regime] = []
    for premier_niveau, membres, parent_de, periodes, depot in sorted(
        brouillons, key=lambda b: depots_filed.get(b[4], "")
    ):
        cible = next(
            (i for i, r in enumerate(regimes)
             if r.premier_niveau == premier_niveau and _compatible(depot, r)),
            None)
        if cible is not None:
            ancien = regimes[cible]
            fusion_parent = dict(ancien.parent_de)
            fusion_parent.update(parent_de)
            regimes[cible] = Regime(
                axe=axe, premier_niveau=premier_niveau,
                membres=ancien.membres | membres, parent_de=fusion_parent,
                periodes=ancien.periodes | periodes,
                depots=ancien.depots + (depot,) if depot not in ancien.depots else ancien.depots)
        else:
            regimes.append(Regime(axe, premier_niveau, membres, dict(parent_de), periodes, (depot,)))
    # Ordre croissant par date de dépôt la plus récente du régime (le régime de référence est le
    # dernier de la liste).
    return sorted(regimes, key=lambda r: max(depots_filed.get(d, "") for d in r.depots))


# ── §2.2 — typer les transitions, BORNÉ, par les MONTANTS ───────────────────────────────────────

MAX_MEMBRES_PARTITION = 8   # au-delà : rupture nommée, jamais un calcul sans fin (§2.2)


def _trouver_partition(
    cible: float, candidats: dict[str, float], tol: float,
) -> tuple[Optional[frozenset[str]], bool]:
    """Rend `(partition, ambigu)`. `partition is None` sans ambiguïté = aucune ne boucle ; `ambigu`
    = au moins deux partitions distinctes bouclent (passage AMBIGU, §2.2). Recherche BORNÉE :
    `len(candidats) > MAX_MEMBRES_PARTITION` est refusé par l'APPELANT avant d'arriver ici."""
    noms = sorted(candidats)
    trouvees: list[frozenset[str]] = []
    for taille in range(1, len(noms) + 1):
        for combo in combinations(noms, taille):
            s = sum(candidats[m] for m in combo)
            if abs(s - cible) <= tol:
                trouvees.append(frozenset(combo))
    if not trouvees:
        return None, False
    if len(trouvees) > 1:
        return None, True
    return trouvees[0], False


def _valeurs_sur_periode(cellules: list[CelluleBrute], periode: str) -> dict[str, float]:
    return {c.membre: c.valeur for c in cellules if c.periode_fin == periode}


def typer_transitions(
    regime_ancien: Regime, regime_nouveau: Regime, cellules: list[CelluleBrute],
) -> list[Transition]:
    """Les transitions entre deux régimes CONSÉCUTIFS du même axe (§2.2). Rend une LISTE : plusieurs
    mouvements peuvent coexister dans la même transition (un `detail_ajoute` sous un membre et un
    `regroupement` ailleurs sur le même axe, au même dépôt)."""
    axe = regime_ancien.axe
    recouvrement = sorted(regime_ancien.periodes & regime_nouveau.periodes, key=ordre_des_periodes)
    if not regime_ancien.membres:
        return [Transition(axe, "axe_disparu", None, motif="l'ancien régime ne porte aucune cellule")]
    if not regime_nouveau.membres:
        return [Transition(axe, "axe_apparu", None, motif="le nouveau régime ne porte aucune cellule")]
    if not recouvrement:
        return [Transition(
            axe, "rupture", None,
            anciens=tuple(sorted(regime_ancien.premier_niveau)),
            nouveaux=tuple(sorted(regime_nouveau.premier_niveau)),
            motif="aucune période n'est publiée dans les deux régimes : pas de recouvrement pour "
                  "prouver un passage")]
    periode = recouvrement[-1]   # la plus récente période publiée dans les DEUX régimes
    cellules_a = [c for c in cellules if c.depot in regime_ancien.depots]
    cellules_n = [c for c in cellules if c.depot in regime_nouveau.depots]
    vals_a = _valeurs_sur_periode(cellules_a, periode)
    vals_n = _valeurs_sur_periode(cellules_n, periode)
    pn_a = {m: vals_a.get(m) for m in regime_ancien.premier_niveau if m in vals_a}
    pn_n = {m: vals_n.get(m) for m in regime_nouveau.premier_niveau if m in vals_n}
    if not pn_a or not pn_n:
        return [Transition(
            axe, "rupture", periode,
            anciens=tuple(sorted(regime_ancien.premier_niveau)),
            nouveaux=tuple(sorted(regime_nouveau.premier_niveau)),
            motif=f"la période de recouvrement `{periode}` ne porte de valeur pour aucun membre de "
                  "premier niveau d'un des deux régimes")]

    tol = tolerance_bouclage(*pn_a.values(), *pn_n.values())
    transitions: list[Transition] = []

    # ── meme_nom_contenu_change : même id dans les deux régimes, valeur différente au recouvrement.
    memes_id = set(pn_a) & set(pn_n)
    mnc = {m for m in memes_id if abs(pn_a[m] - pn_n[m]) > tol}
    for m in sorted(mnc):
        transitions.append(Transition(
            axe, "meme_nom_contenu_change", periode, anciens=(m,), nouveaux=(m,),
            motif=f"« {m} » porte deux valeurs différentes au recouvrement ({pn_a[m]} puis "
                  f"{pn_n[m]}) : continuité par le nom refusée, traité comme une rupture"))

    # ── continuité triviale (même id, même valeur) : jamais un mouvement de CE niveau — ses enfants
    # nouveaux dessous sont du `detail_ajoute`, détecté séparément par `_detail_ajoute` (GLOBAL,
    # par paire de dépôts consécutifs : un parent inchangé peut rester dans le MÊME régime, §2.1,
    # donc n'apparaître dans AUCUNE paire de régimes consécutifs — c'est le cas d'un axe qui ne
    # porte QUE du détail ajouté, sans aucun autre mouvement).
    continus = memes_id - mnc

    # ── le reste : disparus / apparus à relier par renommage, puis passage (regroupement/scission).
    disparus = {m for m in regime_ancien.premier_niveau if m in pn_a} - memes_id
    apparus = {m for m in regime_nouveau.premier_niveau if m in pn_n} - memes_id
    restants_a = dict(pn_a)
    restants_n = dict(pn_n)

    # Renommage : un apparu égal à EXACTEMENT un disparu.
    for n in sorted(apparus):
        if n not in restants_n:
            continue
        candidats = [a for a in disparus if a in restants_a and abs(restants_a[a] - restants_n[n]) <= tol]
        if len(candidats) == 1:
            a = candidats[0]
            transitions.append(Transition(
                axe, "renommage", periode, anciens=(a,), nouveaux=(n,),
                motif=f"« {a} » devient « {n} » (valeur égale au recouvrement : {restants_n[n]})"))
            disparus.discard(a); restants_a.pop(a, None)
            restants_n.pop(n, None)

    apparus_restants = {m for m in apparus if m in restants_n}
    disparus_restants = {m for m in disparus if m in restants_a}

    # Regroupement : un apparu == somme d'une partition de disparus restants.
    for n in sorted(apparus_restants):
        if n not in restants_n or not disparus_restants:
            continue
        if len(disparus_restants) > MAX_MEMBRES_PARTITION:
            transitions.append(Transition(
                axe, "rupture", periode, anciens=tuple(sorted(disparus_restants)), nouveaux=(n,),
                motif=f"« {n} » : trop de membres candidats ({len(disparus_restants)} > "
                      f"{MAX_MEMBRES_PARTITION}) pour établir le passage — jamais un calcul sans fin"))
            continue
        partition, ambigu = _trouver_partition(restants_n[n], {m: restants_a[m] for m in disparus_restants}, tol)
        if ambigu:
            transitions.append(Transition(
                axe, "rupture", periode, anciens=tuple(sorted(disparus_restants)), nouveaux=(n,),
                motif=f"« {n} » : passage AMBIGU — plusieurs partitions des anciens membres bouclent "
                      f"avec {restants_n[n]}"))
        elif partition is not None:
            transitions.append(Transition(
                axe, "regroupement", periode, anciens=tuple(sorted(partition)), nouveaux=(n,),
                motif=f"« {n} » = somme de {sorted(partition)} au recouvrement ({restants_n[n]})"))
            disparus_restants -= partition

    apparus_restants = {m for m in apparus_restants if m not in {
        t.nouveaux[0] for t in transitions if t.type == "regroupement"}}

    # Scission : un disparu == somme d'une partition d'apparus restants.
    for a in sorted(disparus_restants & {m for m in disparus if m in restants_a}):
        if not apparus_restants:
            continue
        if len(apparus_restants) > MAX_MEMBRES_PARTITION:
            transitions.append(Transition(
                axe, "rupture", periode, anciens=(a,), nouveaux=tuple(sorted(apparus_restants)),
                motif=f"« {a} » : trop de membres candidats ({len(apparus_restants)} > "
                      f"{MAX_MEMBRES_PARTITION}) pour établir le passage — jamais un calcul sans fin"))
            continue
        partition, ambigu = _trouver_partition(restants_a[a], {m: restants_n[m] for m in apparus_restants}, tol)
        if ambigu:
            transitions.append(Transition(
                axe, "rupture", periode, anciens=(a,), nouveaux=tuple(sorted(apparus_restants)),
                motif=f"« {a} » : passage AMBIGU — plusieurs partitions des nouveaux membres bouclent "
                      f"avec {restants_a[a]}"))
        elif partition is not None:
            transitions.append(Transition(
                axe, "scission", periode, anciens=(a,), nouveaux=tuple(sorted(partition)),
                motif=f"« {a} » se répartit en {sorted(partition)} au recouvrement ({restants_a[a]})"))
            apparus_restants -= partition

    # Ce qui reste des deux côtés, sans mouvement trouvé : rupture nommée.
    traites_a = {m for t in transitions for m in t.anciens}
    traites_n = {m for t in transitions for m in t.nouveaux}
    reste_a = sorted(m for m in disparus if m in restants_a and m not in traites_a)
    reste_n = sorted(m for m in apparus if m in restants_n and m not in traites_n)
    if reste_a or reste_n:
        transitions.append(Transition(
            axe, "rupture", periode, anciens=tuple(reste_a), nouveaux=tuple(reste_n),
            motif=f"aucun passage établi (ni renommage, ni regroupement, ni scission) pour les "
                  f"membres disparus {reste_a} / apparus {reste_n}"))

    if not transitions:
        # Aucun mouvement du tout (régimes identiques sur le recouvrement) — rien à dire.
        return []
    return transitions


# ── §2.3 / §2.3 bis — la chronique : séries comparables, publié / passage / hypothèse ──────────

def _resoudre_valeur(
    transitions: list[Transition], cellules: list[CelluleBrute], membre: str, periode: str,
    *, profondeur: int = 0,
) -> Optional[float]:
    """La valeur de `membre` à `periode`, par CHAÎNE de passages vérifiés (plusieurs
    renommages/regroupements/scissions consécutifs, §2.3) — pas seulement le hop immédiat : une
    chaîne V1→V2→V3 doit pouvoir reconstituer V3 à une période où seul V1 a publié. Bornée (une
    chaîne traverse au plus les régimes de l'axe, toujours finis — le garde-fou n'est jamais
    censé être atteint, mais une récursion sans borne serait le blocage muet que #73 interdit)."""
    if profondeur > 2 * MAX_MEMBRES_PARTITION:
        return None
    direct = next((c.valeur for c in cellules if c.membre == membre and c.periode_fin == periode), None)
    if direct is not None:
        if any(membre in t.anciens and t.type in ("meme_nom_contenu_change", "rupture") for t in transitions):
            return None   # perturbé : cette valeur directe n'est PAS une continuité fiable
        return direct
    for t in transitions:
        if membre not in t.nouveaux:
            continue
        if t.type in ("renommage", "regroupement"):
            valeurs = [_resoudre_valeur(transitions, cellules, a, periode, profondeur=profondeur + 1)
                       for a in t.anciens]
            if all(v is not None for v in valeurs):
                return sum(valeurs)
        elif t.type == "scission" and t.periode_recouvrement is not None:
            v_ancien = _resoudre_valeur(
                transitions, cellules, t.anciens[0], periode, profondeur=profondeur + 1)
            if v_ancien is None:
                continue
            parts = _valeurs_sur_periode(
                [c for c in cellules if c.periode_fin == t.periode_recouvrement], t.periode_recouvrement)
            total_parts = sum(parts.get(n, 0.0) for n in t.nouveaux)
            if total_parts == 0:
                continue
            return v_ancien * (parts.get(membre, 0.0) / total_parts)
    return None


def _passage_direct(
    transitions: list[Transition], membre_ref: str, vals_periode: dict[str, float], cellules: list[CelluleBrute],
    periode: str,
) -> Optional[tuple[tuple[str, ...], float]]:
    """Rend `(anciens, valeur)` par un passage VÉRIFIÉ (§2.3) : l'IDENTITÉ (le membre existait déjà
    sous le même nom, continu), ou le(s) ancien(s) de la transition qui mène à `membre_ref`
    (`renommage`/`regroupement`/`scission`) — leur valeur étant elle-même résolue PAR CHAÎNE
    (`_resoudre_valeur`), pas seulement au hop immédiat. `None` si aucun passage vérifié ne mène à
    ce membre.

    L'identité n'est PAS enregistrée comme une `Transition` (`typer_transitions` ne décrit que les
    MOUVEMENTS) : un membre inchangé n'en a besoin que pour reconstituer son historique, ici."""
    valeur = _resoudre_valeur(transitions, cellules, membre_ref, periode)
    if valeur is None:
        return None
    perturbe = any(
        membre_ref in t.anciens and t.type in ("meme_nom_contenu_change", "rupture")
        for t in transitions)
    if not perturbe and membre_ref in vals_periode:
        return (membre_ref,), valeur
    for t in transitions:
        if membre_ref in t.nouveaux and t.type in ("renommage", "regroupement", "scission"):
            return t.anciens, valeur
    return None


def _detail_ajoute(
    axe: str, cellules: list[CelluleBrute], depots_filed: dict[str, str],
) -> list[Transition]:
    """`detail_ajoute` (§2.2), détecté GLOBALEMENT par paire de dépôts CONSÉCUTIFS (triés par date
    de dépôt), indépendamment des régimes : un parent dont la valeur est inchangée (à la tolérance
    de bouclage) sur une période publiée par les deux dépôts, et qui gagne des enfants nouveaux.
    Détection indépendante de `etablir_regimes` parce qu'un axe qui ne porte QUE du détail ajouté
    (aucun autre mouvement) ne change pas de premier niveau — ses deux dépôts fusionnent dans le
    MÊME régime (§2.1), et une transition ENTRE régimes ne le verrait donc jamais."""
    par_depot: dict[str, list[CelluleBrute]] = {}
    for c in cellules:
        par_depot.setdefault(c.depot, []).append(c)
    depots_tries = sorted(par_depot, key=lambda d: depots_filed.get(d, ""))
    transitions: list[Transition] = []
    vus: set[tuple[str, tuple[str, ...]]] = set()
    for d_ancien, d_nouveau in zip(depots_tries[:-1], depots_tries[1:]):
        cells_a, cells_n = par_depot[d_ancien], par_depot[d_nouveau]
        membres_a = {c.membre for c in cells_a}
        membres_n = {c.membre for c in cells_n}
        parent_n = {c.membre: c.parent for c in cells_n if c.parent is not None}
        periodes_communes = sorted(
            {c.periode_fin for c in cells_a} & {c.periode_fin for c in cells_n}, key=ordre_des_periodes)
        for periode in periodes_communes:
            vals_a = _valeurs_sur_periode(cells_a, periode)
            vals_n = _valeurs_sur_periode(cells_n, periode)
            communs = sorted(set(vals_a) & set(vals_n))
            if not communs:
                continue
            tol = tolerance_bouclage(*vals_a.values(), *vals_n.values())
            for m in communs:
                if abs(vals_a[m] - vals_n[m]) > tol:
                    continue
                enfants_nouveaux = tuple(sorted(
                    e for e in membres_n if parent_n.get(e) == m and e not in membres_a))
                cle = (m, enfants_nouveaux)
                if enfants_nouveaux and cle not in vus:
                    vus.add(cle)
                    transitions.append(Transition(
                        axe, "detail_ajoute", periode, anciens=(m,), nouveaux=enfants_nouveaux,
                        motif=f"« {m} » inchangé ({vals_a[m]}) ; enfants nouveaux détaillés dessous : "
                              f"{list(enfants_nouveaux)}"))
    return transitions


def construire_chronique(
    axe: str, cellules: list[CelluleBrute], depots_filed: dict[str, str],
) -> Chronique:
    """La chronique d'UN axe : régimes, transitions typées, et la série comparable dans le régime de
    RÉFÉRENCE (§2.3), avec passage vérifié ou répartition par hypothèse (§2.3 bis)."""
    regimes = etablir_regimes(cellules, depots_filed)
    if not regimes:
        return Chronique(axe, Regime(axe, frozenset(), frozenset(), {}, frozenset(), ()), [], [], [])
    regime_ref = regimes[-1]
    transitions: list[Transition] = _detail_ajoute(axe, cellules, depots_filed)
    for ancien, nouveau in zip(regimes[:-1], regimes[1:]):
        transitions.extend(typer_transitions(ancien, nouveau, cellules))

    toutes_periodes = sorted({c.periode_fin for c in cellules}, key=ordre_des_periodes)
    cellules_chronique: list[CelluleChronique] = []
    refus: list[str] = []

    for periode in toutes_periodes:
        vals_periode = _valeurs_sur_periode(cellules, periode)
        periode_dans_ref = periode in regime_ref.periodes
        for membre in sorted(regime_ref.premier_niveau):
            if membre in vals_periode and periode_dans_ref:
                cellules_chronique.append(
                    CelluleChronique(axe, membre, periode, vals_periode[membre], "publie"))
                continue
            if periode_dans_ref:
                continue   # période du régime de référence mais membre non publié cette période-là

            trouve_passage = _passage_direct(transitions, membre, vals_periode, cellules, periode)
            if trouve_passage is not None:
                anciens, valeur_passage = trouve_passage
                depot_source = next(
                    (c.depot for c in cellules if c.periode_fin == periode and c.membre in anciens), None)
                cellules_chronique.append(CelluleChronique(
                    axe, membre, periode, valeur_passage, "passage",
                    passage_de=anciens, passage_depot=depot_source))
                continue

            # §2.3 bis — répartition par hypothèse. Le GROUPE = la plus petite partie de l'axe qui
            # se raccorde : les anciens membres de la transition la plus proche qui touche `membre`,
            # sinon l'axe entier (aucun recouvrement).
            groupe_ancien, groupe_nouveau, methode_motif = _groupe_hypothese(transitions, membre, regime_ref)
            if groupe_ancien is None or not all(a in vals_periode for a in groupe_ancien):
                continue   # ce membre n'a simplement rien à cette période-là : pas d'historique à inventer
            premiere_periode_nouveau = _premiere_periode_du_regime(regime_ref, cellules)
            parts = _parts_au_prorata(groupe_nouveau, premiere_periode_nouveau, cellules)
            if membre not in parts or sum(parts.values()) <= 0:
                refus.append(
                    f"[{axe}] « {membre} » à `{periode}` : aucune part calculable au prorata à "
                    f"`{premiere_periode_nouveau}` — répartition par hypothèse impossible")
                continue
            montant_groupe = sum(vals_periode[a] for a in groupe_ancien)
            valeur = montant_groupe * (parts[membre] / sum(parts.values()))
            cellules_chronique.append(CelluleChronique(
                axe, membre, periode, valeur, "hypothese",
                methode="prorata des parts du groupe à la première période du nouveau découpage (v1)",
                periode_des_parts=premiere_periode_nouveau,
                anciens_montants={a: vals_periode[a] for a in groupe_ancien}))

    return Chronique(axe, regime_ref, regimes, transitions, cellules_chronique, refus)


def _groupe_hypothese(
    transitions: list[Transition], membre: str, regime_ref: Regime,
) -> tuple[Optional[tuple[str, ...]], tuple[str, ...], str]:
    """Le GROUPE concerné par une répartition par hypothèse pour `membre` (§2.3 bis) : les anciens
    membres touchés par une transition RUPTURE/MEME_NOM_CONTENU_CHANGE qui le cite (ou le passage
    AMBIGU, lui aussi typé `rupture`). `detail_ajoute` est EXCLU délibérément : ses enfants nouveaux
    « n'ont d'histoire que là où ils sont publiés » (§2.2) — aucune hypothèse ne leur en invente une.
    Sans recouvrement AU TOUT (la `Transition` « aucune période … » porte alors tous les anciens
    premier-niveau et tous les nouveaux), le groupe est naturellement l'axe entier."""
    for t in transitions:
        if membre in t.nouveaux and t.anciens and t.type in ("rupture", "meme_nom_contenu_change"):
            return t.anciens, t.nouveaux, f"transition {t.type}"
    return None, tuple(sorted(regime_ref.premier_niveau)), "aucune transition ne cite ce membre"


def _premiere_periode_du_regime(regime: Regime, cellules: list[CelluleBrute]) -> Optional[str]:
    periodes = sorted(
        {c.periode_fin for c in cellules if c.membre in regime.premier_niveau and c.periode_fin in regime.periodes},
        key=ordre_des_periodes)
    return periodes[0] if periodes else None


def _parts_au_prorata(
    membres: tuple[str, ...], periode: Optional[str], cellules: list[CelluleBrute],
) -> dict[str, float]:
    if periode is None:
        return {}
    vals = _valeurs_sur_periode(cellules, periode)
    return {m: vals[m] for m in membres if m in vals}


# ── §2.3 ter — l'invariant de l'agrégat ─────────────────────────────────────────────────────────

def verifier_invariant_agregat(
    chronique: Chronique, ligne_du_socle: dict[str, float],
) -> list[str]:
    """Pour chaque période à raccord, Σ des membres de premier niveau de la série RECONSTITUÉE
    (publiés + passages + hypothèses) == la ligne du socle, à la tolérance de bouclage — sinon une
    ERREUR DU MODULE (§2.3 ter), jamais une rupture : la structure d'un compte de résultat ne change
    pas d'une année à l'autre. Rend la liste des motifs (vide = invariant tenu partout)."""
    par_periode: dict[str, float] = {}
    for c in chronique.cellules:
        if c.membre in chronique.regime_reference.premier_niveau:
            par_periode[c.periode] = par_periode.get(c.periode, 0.0) + c.valeur
    motifs: list[str] = []
    for periode, somme in par_periode.items():
        if periode not in ligne_du_socle:
            continue
        total = ligne_du_socle[periode]
        tol = tolerance_bouclage(total, somme)
        if abs(total - somme) > tol:
            motifs.append(
                f"[{chronique.axe}] invariant de l'agrégat rompu à `{periode}` : Σ premier niveau "
                f"reconstituée = {somme}, ligne du socle = {total} (écart {total - somme}, "
                f"tolérance {tol}) — ERREUR du module, jamais une rupture présentée comme normale")
    return motifs


# ── §8 (addendum) point 2 — la vue SERVIE, calculée à la lecture ───────────────────────────────

# La LIGNE dont la somme des membres de premier niveau DOIT se raccorder au total consolidé, pour
# TOUT émetteur (ASC 280 / IFRS 8 : la ventilation du CHIFFRE D'AFFAIRES par secteur, activité ou
# zone géographique est tenue de reconcilier à la vente consolidée — ce n'est vrai d'AUCUNE autre
# ligne : un résultat ou un actif sectoriel laisse couramment un reste « corporate »/non affecté,
# sans que ce soit un défaut de périmètre, cf. [V4] NVDA resultat_exploitation). La garde (iv) ne
# porte donc QUE sur cette ligne — l'étendre à une ligne qui n'a jamais eu vocation à boucler
# fabriquerait un faux refus, pas une garde (`feedback_garde_structure_pas_sens`). Ce n'est PAS un
# seuil calé sur un émetteur : c'est une règle du gabarit (`socle_comptes.yaml`), valable pour tout
# émetteur qui ventile son chiffre d'affaires.
LIGNE_RACCORD_OBLIGATOIRE = "chiffre_affaires"


def _depot_le_plus_recent(cles: list[tuple], depots_filed: dict[str, str]) -> tuple:
    """Parmi des cellules candidates pour LA MÊME adresse logique (axe,ligne,membre,période[,base]),
    celle du dépôt déposé le plus RÉCEMMENT (#133) — jamais le premier dépôt rencontré. Pure,
    déterministe (l'accn départage une égalité de date de dépôt)."""
    return max(cles, key=lambda c: (depots_filed.get(c[-1], ""), c[-1]))


def vue_servie(structure: dict[str, Any], socle: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """La vue SERVIE (lot P1, §8 addendum, point 2 — tranche A) : calculée À LA LECTURE à partir de
    la structure PERSISTÉE par `ventilation.relever` (cellules PAR DÉPÔT, point 1 — identité
    `(axe, ligne, membre, période, accn)`, sans aucune fusion) et du socle EN VIGUEUR. Rend une
    structure de MÊME FORME, où :

      · `cellules` est DÉDUPLIQUÉE à UNE cellule par adresse logique (axe, ligne, membre, période,
        base) : quand plusieurs dépôts publient la MÊME adresse, celui déposé le plus RÉCEMMENT
        fait foi (#133) — jamais le premier dépôt rencontré. C'est la cause mesurée de `c551003` :
        le jumeau avait fait prendre une version d'ORIGINE à la place d'une version RETRAITÉE sur
        un chemin qui ne passait pas encore par ici (`appariement_feed._choisir_terme`, déjà
        corrigé) — cette déduplication ferme le MÊME trou pour tout lecteur qui passe par la vue ;
      · `refus` porte, EN PLUS des refus déjà portés par `structure`, la garde (iv) : pour chaque
        axe à raccord, sur la ligne `LIGNE_RACCORD_OBLIGATOIRE`, la somme des membres de premier
        niveau de la série reconstituée égale la ligne du socle à `tolerance_bouclage` À CHAQUE
        période connue du socle — sinon une ERREUR du module, refus NOMMÉ
        (`verifier_invariant_agregat`, §2.3 ter), jamais une rupture tue.

    Dans CETTE tranche (A), `cellules` reste la valeur telle que DISPOSÉE par un dépôt (la
    reconstruction par passage/hypothèse, elle, n'est pas branchée au rendu — tranche B) : pour un
    axe à un seul régime, la déduplication ne change RIEN (une seule adresse logique, un seul
    dépôt l'alimentant déjà) — la vue reproduit le comportement actuel à l'identique. Elle ne
    change le texte affiché que là où une fusion silencieuse cachait auparavant un second dépôt
    (jamais un nouveau rendu de régime)."""
    cellules_brutes = structure.get("cellules") or []
    depots_meta = structure.get("depots") or []
    depots_filed = {d["accn"]: d.get("filed") or "" for d in depots_meta}

    # ── Déduplication : une adresse logique, une cellule ────────────────────────────────────────
    par_adresse: dict[tuple, list[dict]] = {}
    for c in cellules_brutes:
        adresse = (c["axe"], c["ligne"], c["membre"], c["periode"], c.get("base"))
        par_adresse.setdefault(adresse, []).append(c)
    cellules_vue: list[dict] = []
    for adresse, candidats in par_adresse.items():
        if len(candidats) == 1:
            cellules_vue.append(candidats[0])
            continue
        cles = [(*adresse, c["accn"]) for c in candidats]
        accn_retenu = _depot_le_plus_recent(cles, depots_filed)[-1]
        retenue = next(c for c in candidats if c["accn"] == accn_retenu)
        cellules_vue.append(retenue)

    # ── Garde (iv) : l'invariant de l'agrégat, sur la ligne qui DOIT boucler ────────────────────
    cel_socle = (socle or {}).get("cellules") or {}
    refus_nouveaux: list[str] = []
    par_axe: dict[str, list[dict]] = {}
    for c in cellules_vue:
        if c["ligne"] == LIGNE_RACCORD_OBLIGATOIRE:
            par_axe.setdefault(c["axe"], []).append(c)
    for axe, cs in par_axe.items():
        brutes = [
            CelluleBrute(
                axe=axe, membre=c["membre"], valeur=float(c["v"]), periode_fin=c["periode"],
                depot=c["accn"], parent=c.get("parent"))
            for c in cs
        ]
        chronique = construire_chronique(axe, brutes, depots_filed)
        ligne_du_socle_brut = {
            periode.split("|", 1)[1]: float(cel["v"])
            for periode, cel in cel_socle.items()
            if periode.startswith(f"{LIGNE_RACCORD_OBLIGATOIRE}|") and cel.get("v") is not None
        }
        # Une période n'entre dans la garde que si la série RECONSTITUÉE y est COMPLÈTE (tous les
        # membres de premier niveau du régime de référence y ont une valeur). Un membre du régime
        # de référence sans aucune valeur à cette période (ex. un membre NOUVEAU dont les douze
        # mois glissants ne sont pas encore établis, §4.2) est une incomplétude DÉJÀ nommée par le
        # raccord `decoupage_change`/`non_ventile` existant — ce n'est pas la faute de ce module, et
        # la garde (iv) ne doit porter que sur ce qu'elle peut vraiment juger, sous peine de refuser
        # une série que personne n'a prétendu complète (`feedback_garde_structure_pas_sens`).
        membres_par_periode: dict[str, set[str]] = {}
        for cc in chronique.cellules:
            if cc.membre in chronique.regime_reference.premier_niveau:
                membres_par_periode.setdefault(cc.periode, set()).add(cc.membre)
        periodes_completes = {
            p for p, ms in membres_par_periode.items() if ms >= chronique.regime_reference.premier_niveau}
        ligne_du_socle = {p: v for p, v in ligne_du_socle_brut.items() if p in periodes_completes}
        refus_nouveaux.extend(verifier_invariant_agregat(chronique, ligne_du_socle))

    return {
        **structure,
        "cellules": cellules_vue,
        "refus": list(structure.get("refus") or []) + refus_nouveaux,
    }


# ── §2.4 — les douze mois glissants : même régime, ou retraitement cohérent ─────────────────────

DOUZE_MOIS_REGIMES_INCOHERENTS = (
    "douze mois non établis : les termes relèvent de deux découpages sans passage vérifié")


def points_douze_mois_coherents(
    *, regime_exercice: Optional[frozenset[str]] = None,
    regime_cumul: Optional[frozenset[str]] = None,
    regime_comparable: Optional[frozenset[str]] = None,
    transitions: tuple[Transition, ...] = (),
    retraitements: Optional[dict[str, tuple[dict, ...]]] = None,
) -> tuple[bool, Optional[str]]:
    """Le prédicat du détenteur (§2.4), reçu par `appariement_feed.douze_mois_glissants` — JAMAIS
    recopié. Deux contrôles indépendants, l'un ou l'autre peut s'appliquer selon ce que l'appelant
    fournit :

    1. RÉGIME (ventilation par axe) : les trois termes (exercice clos, cumul en cours, cumul
       comparable) doivent appartenir au MÊME régime (même ensemble de membres de premier niveau),
       ou être raccordés entre eux par un passage VÉRIFIÉ (une transition de type `detail_ajoute`,
       `renommage` ou `regroupement`/`scission` — jamais `rupture` ni `meme_nom_contenu_change`).
       `None` pour un des trois arguments de régime = ce contrôle ne s'applique pas (appel socle).

    2. RETRAITEMENT (socle, un concept us-gaap) : `retraitements` = `{role: (point_version_1,
       point_version_2, …)}` pour les rôles qui portent PLUSIEURS valeurs selon le dépôt. Si un rôle
       a plusieurs valeurs, LES TROIS rôles doivent pouvoir être pris dans leur version la plus
       RÉCEMMENT DÉPOSÉE (celle qui existe pour chacun) — sinon refus nommé : jamais un mélange
       silencieux d'une version retraitée et d'une version d'origine.

    Rend `(True, None)` si cohérent, `(False, motif)` sinon — JAMAIS une exception : c'est à
    l'appelant de transformer `False` en refus nommé (même esprit que `Ventilation`, qui rend des
    constats, pas des échecs)."""
    if regime_exercice is not None and regime_cumul is not None and regime_comparable is not None:
        if not (regime_exercice == regime_cumul == regime_comparable):
            passage_ok = any(
                t.type in ("detail_ajoute", "renommage", "regroupement", "scission")
                for t in transitions)
            if not passage_ok:
                return False, (
                    f"{DOUZE_MOIS_REGIMES_INCOHERENTS} (exercice={sorted(regime_exercice)}, "
                    f"cumul={sorted(regime_cumul)}, comparable={sorted(regime_comparable)})")

    if retraitements:
        multiples = {r: pts for r, pts in retraitements.items() if len({p.get("val") for p in pts}) > 1}
        if multiples:
            for role, pts in multiples.items():
                plus_recent = max(pts, key=lambda p: str(p.get("filed") or ""))
                autres_memes_filed = [p for p in pts if str(p.get("filed")) == str(plus_recent.get("filed"))]
                if len(autres_memes_filed) > 1 and len({p.get("val") for p in autres_memes_filed}) > 1:
                    return False, (
                        f"retraitement ambigu sur le rôle « {role} » : plusieurs valeurs déposées à "
                        "la même date, aucune ne fait foi sans jugement humain")
            return True, None   # la version la plus récente de chaque rôle est prise (appelant : `_preferer`)
    return True, None


# ── §5 — identifier le dépôt JUMEAU (étape 2) ───────────────────────────────────────────────────

class FilingMeta(NamedTuple):
    """Ce que la lecture du flux `submissions` donne pour un dépôt — assez pour en relire les
    fichiers XBRL (`ventilation_feed._lire_depot`), rien de plus."""
    accn: str
    form: str
    filed: str
    report: str          # `reportDate` — la fin de la période couverte


def identifier_jumeau_candidat(
    filings: tuple[FilingMeta, ...], recent: FilingMeta, ancien: FilingMeta,
) -> Optional[FilingMeta]:
    """Le dépôt JUMEAU (§0/§5) : celui qui a publié, dans l'ANCIEN découpage, la période que `recent`
    reprend comme comparatif. Pur, BORNÉ (parcourt `filings`, une liste finie déjà lue) — identifié
    par la DATE, jamais par un nom de dépôt : le comparatif d'un dépôt dont la période couvre environ
    un an avant `recent.report` (±20 j, la même tolérance que `appariement_feed.TOLERANCE_ANCRE_J`),
    déposé AVANT `ancien` (donc dans l'ancien régime) — sinon `None` (pas de jumeau à lire).
    """
    from datetime import date
    try:
        cible = date.fromisoformat(recent.report).replace(year=date.fromisoformat(recent.report).year - 1)
    except ValueError:
        return None
    candidats = [
        f for f in filings
        if f.filed < ancien.filed and f.accn not in (recent.accn, ancien.accn)
    ]
    meilleur: Optional[FilingMeta] = None
    meilleur_ecart = None
    for f in candidats:
        try:
            ecart = abs((date.fromisoformat(f.report) - cible).days)
        except ValueError:
            continue
        if ecart <= 20 and (meilleur_ecart is None or ecart < meilleur_ecart):
            meilleur, meilleur_ecart = f, ecart
    return meilleur


def regime_a_change(
    premier_niveau_ancien: dict[str, frozenset[str]], premier_niveau_recent: dict[str, frozenset[str]],
) -> bool:
    """`True` si, pour AU MOINS UN axe, l'ensemble des membres de premier niveau a changé entre
    l'ancien dépôt (10-K) et le dépôt récent (10-Q) — le signal qui décide si le jumeau vaut la
    peine d'être lu (§5 : gratuit, mais pas pour tout émetteur à chaque appel). Pur ; les deux
    dictionnaires sont `{axe_id: frozenset(membres de premier niveau)}`, déjà réduits à l'axe."""
    axes = set(premier_niveau_ancien) | set(premier_niveau_recent)
    return any(premier_niveau_ancien.get(a) != premier_niveau_recent.get(a) for a in axes)


# ── §4 bis — le signal d'acquisition significative ──────────────────────────────────────────────

SEUIL_ACQUISITION_SIGNIFICATIVE_DEFAUT = 0.05   # 5 %, paramètre du fonds (référentiel de ventilation)


class SignalAcquisition(NamedTuple):
    date: str
    montant: float
    base: Literal["chiffre_affaires_acquis", "contrepartie_sur_capitalisation"]
    part_estimee: float


def signal_acquisition_significative(
    faits_regroupement: tuple[dict, ...], *,
    chiffre_affaires_exercice: Optional[float] = None,
    capitalisation: Optional[float] = None,
    seuil: float = SEUIL_ACQUISITION_SIGNIFICATIVE_DEFAUT,
) -> list[SignalAcquisition]:
    """Le SIGNAL (§4 bis), jamais le calcul de la croissance hors acquisitions (module ad hoc après
    le premier comité, arbitrage Q2). `faits_regroupement` : les faits XBRL de regroupement
    d'entreprises déjà lus (`BusinessCombinationConsiderationTransferred1`,
    `BusinessCombinationsRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedRevenueOfAcquiree1`
    ou pro forma quand déposé), chacun `{"date": iso, "contrepartie": float,
    "chiffre_affaires_acquis": Optional[float]}`. Seuil : 5 % du CA de l'exercice si le chiffre
    d'affaires acquis est publié, sinon 5 % de la contrepartie rapportée à la capitalisation — à dire
    au comité (§4 bis), jamais absorbé en silence.

    Rend la liste des acquisitions AU-DESSUS du seuil (éventuellement vide) — jamais une exception :
    une acquisition sous le seuil n'est pas un refus, c'est une mesure qui ne déclenche rien."""
    signaux: list[SignalAcquisition] = []
    for f in faits_regroupement:
        contrepartie = f.get("contrepartie")
        if contrepartie is None:
            continue
        ca_acquis = f.get("chiffre_affaires_acquis")
        if ca_acquis is not None and chiffre_affaires_exercice:
            part = ca_acquis / chiffre_affaires_exercice
            base: Literal["chiffre_affaires_acquis", "contrepartie_sur_capitalisation"] = "chiffre_affaires_acquis"
        elif capitalisation:
            part = contrepartie / capitalisation
            base = "contrepartie_sur_capitalisation"
        else:
            continue   # ni chiffre d'affaires acquis ni capitalisation : rien à comparer au seuil
        if part >= seuil:
            signaux.append(SignalAcquisition(
                date=f.get("date") or "", montant=contrepartie, base=base, part_estimee=part))
    return signaux
