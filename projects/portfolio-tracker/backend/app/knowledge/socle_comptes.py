"""Le SOCLE DES COMPTES — les comptes de l'émetteur reconstitués au format maison, une fois pour toutes.

POURQUOI IL EXISTE (arbitrage de l'utilisateur, 2026-10-04)
-----------------------------------------------------------
« Toutes les questions financières devraient s'intégrer à un P&L reconstitué qui s'interface avec le
schéma de valorisation. » Jusqu'ici chaque question allait chercher ses propres chiffres : une ligne
de plan, une carte d'appariement, un fait. Les correctifs #104 à #113 portaient presque tous sur la
COHÉRENCE entre questions — deux dettes nettes, deux périodes, un arrondi recopié d'une question à
l'autre. Un vrai fonds fait l'inverse : l'analyste construit d'abord le modèle des comptes (résultat,
bilan, flux, reliés et bouclés, sur cinq exercices), au format maison commun à toutes les sociétés ;
les questions d'analyse en sont des LECTURES, la valorisation en est la projection.

CE QUE CE MODULE FAIT
---------------------
Une fonction PURE, `reconstituer(faits, gabarit)` : l'inventaire `companyfacts` d'un émetteur (déjà lu,
aucun appel réseau ici) → un `SocleComptes` : des périodes (cinq exercices clos, les douze mois
glissants, le dernier bilan), une cellule par (ligne × période) avec sa provenance concept par concept,
et le résultat de chaque bouclage. Aucun modèle de langage, aucune base.

LES ÉTATS D'UNE CELLULE — jamais un zéro inventé (#25, #44)
-----------------------------------------------------------
  · `depose`          — recopié du dépôt (un concept, ou la somme des concepts d'une recette) ;
  · `par_difference`  — la ligne « autres … » d'une équation, ou un poste résolu par bouclage ;
  · `par_somme`       — un total que l'émetteur ne dépose pas, recomposé de ses composantes ;
  · `calcule`         — une définition maison (`calcul`), p. ex. le flux de trésorerie disponible ;
  · `compte_zero`     — non déposé, et le gabarit dit qu'une absence vaut zéro DANS LES ÉQUATIONS (une
                        société sans activité à l'étranger n'a pas d'effet de change). La valeur publiée
                        est None : le zéro est une hypothèse de l'équation, pas un chiffre ;
  · `non_depose`      — ni déposé, ni déductible.

LES BOUCLAGES — un écart se publie, il ne s'absorbe pas
--------------------------------------------------------
Une équation AVEC reste fait apparaître « autres … par différence » : ce que le gabarit ne nomme pas
reste visible au lieu de se perdre. Une équation SANS reste est un CONTRÔLE : quand ses deux côtés sont
connus et diffèrent au-delà de la tolérance, l'écart est publié (`Controle.statut == "ecart"`) avec son
montant. Il ne peut pas être « réglé » en fabriquant une ligne : c'est l'information qu'un analyste
veut voir en premier (les comptes ne tiennent pas, ou le gabarit lit le mauvais concept).

LES PÉRIODES — lues au dépôt, par les durées (#42, #112)
---------------------------------------------------------
Les exercices sont ceux que l'émetteur publie (`points_annuels`, détenteur unique), les douze mois
glissants l'identité « exercice clos + cumul en cours − cumul comparable » (`douze_mois_glissants`,
détenteur unique, refus nommé si un terme manque — jamais de repli sur l'exercice), le dernier bilan
le dernier instant déposé (`points_instantanes`). Aucune règle de période n'est recopiée ici.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

import yaml

from app.knowledge.appariement_feed import (
    AppariementInexecutable,
    TOLERANCE_ANCRE_J,
    douze_mois_glissants,
    points_de_l_unite_retenue,
    serie_du_concept,
)
from app.knowledge.edgar_facts import point_pour_periode

GABARIT_YAML = Path(__file__).resolve().parent / "socle_comptes.yaml"
EMETTEURS_YAML = Path(__file__).resolve().parent / "socle_comptes_emetteurs.yaml"

# Nombre d'exercices clos du socle : cinq, comme le demandent qf_1 et qf_5 (« sur cinq exercices
# consécutifs ») et comme le fait un modèle d'analyste.
NB_EXERCICES = 5

# Tolérance d'un bouclage : les montants XBRL sont déposés à l'unité (souvent au millier près) ; un
# écart sous 0,1 % du total ou sous 0,5 M$ est un arrondi de présentation, pas une incohérence.
TOLERANCE_RELATIVE = 0.001
TOLERANCE_ABSOLUE = 500_000.0

EtatCellule = Literal["depose", "par_difference", "par_somme", "calcule", "compte_zero", "non_depose"]
NaturePeriode = Literal["exercice", "douze_mois", "dernier_bilan"]


class GabaritInvalide(Exception):
    """Le gabarit maison est incohérent (ligne inconnue, reste en double, cadrages mêlés). Lève au
    chargement : un gabarit à demi lu publierait des comptes à trous qui auraient l'air complets."""


# ── Le gabarit ──────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Terme:
    ligne: str
    signe: int            # +1 / -1


@dataclass(frozen=True)
class Ligne:
    id: str
    libelle: str
    etat: str
    cadrage: str                                   # "flux" | "instant"
    recettes: tuple[tuple[str, ...], ...] = ()
    absent_vaut_zero: bool = False
    calcul: tuple[Terme, ...] = ()
    recettes_par_emetteur: bool = False


@dataclass(frozen=True)
class Equation:
    etat: str
    total: str
    composantes: tuple[Terme, ...]
    reste: Optional[Terme] = None

    def libelle(self) -> str:
        droite = " ".join(f"{'+' if t.signe > 0 else '−'} {t.ligne}" for t in self.composantes)
        if self.reste:
            droite += f" {'+' if self.reste.signe > 0 else '−'} {self.reste.ligne}"
        return f"{self.total} = {droite.lstrip('+ ')}"


@dataclass(frozen=True)
class Gabarit:
    version: str
    etats: tuple[tuple[str, str, str], ...]        # (id, libellé, cadrage)
    lignes: dict[str, Ligne]
    equations: tuple[Equation, ...]

    def lignes_de(self, etat: str) -> list[Ligne]:
        return [l for l in self.lignes.values() if l.etat == etat]


def _terme(brut: str, connues: set[str], ou: str) -> Terme:
    s = str(brut).strip()
    if not s or s[0] not in "+-":
        raise GabaritInvalide(f"{ou} : terme « {s} » sans signe explicite (+ ou -)")
    nom = s[1:].strip()
    if nom not in connues:
        raise GabaritInvalide(f"{ou} : la ligne « {nom} » n'existe pas dans le gabarit")
    return Terme(nom, +1 if s[0] == "+" else -1)


def charger_gabarit(chemin: Path = GABARIT_YAML) -> Gabarit:
    """Lit et VALIDE le gabarit. Lève `GabaritInvalide` sur toute incohérence relationnelle."""
    brut = yaml.safe_load(Path(chemin).read_text(encoding="utf-8")) or {}
    etats: list[tuple[str, str, str]] = []
    lignes: dict[str, Ligne] = {}
    for e in brut.get("etats") or []:
        cadrage = e.get("cadrage")
        if cadrage not in ("flux", "instant"):
            raise GabaritInvalide(f"état {e.get('id')} : cadrage « {cadrage} » hors de flux/instant")
        etats.append((e["id"], e["libelle"], cadrage))
        for l in e.get("lignes") or []:
            if l["id"] in lignes:
                raise GabaritInvalide(f"ligne « {l['id']} » déclarée deux fois")
            recettes = tuple(tuple(r) for r in (l.get("recettes") or []))
            if any(not r for r in recettes):
                raise GabaritInvalide(f"ligne « {l['id']} » : recette vide")
            par_emetteur = bool(l.get("recettes_par_emetteur"))
            if par_emetteur and recettes:
                raise GabaritInvalide(f"ligne « {l['id']} » : une ligne à recettes PAR ÉMETTEUR n'a pas de "
                                      "recette commune — sinon le concept vaudrait pour tous")
            lignes[l["id"]] = Ligne(l["id"], l["libelle"], e["id"], cadrage, recettes,
                                    bool(l.get("absent_vaut_zero")), (), par_emetteur)
    connues = set(lignes)
    # Les calculs se lisent en second : ils peuvent nommer une ligne d'un autre état.
    for e in brut.get("etats") or []:
        for l in e.get("lignes") or []:
            if l.get("calcul"):
                termes = tuple(_terme(t, connues, f"calcul de {l['id']}") for t in l["calcul"])
                lignes[l["id"]] = Ligne(**{**lignes[l["id"]].__dict__, "calcul": termes})
    equations: list[Equation] = []
    restes_vus: dict[str, str] = {}
    for e in brut.get("etats") or []:
        for q in e.get("equations") or []:
            ou = f"équation de {q.get('total')} ({e['id']})"
            if q.get("total") not in connues:
                raise GabaritInvalide(f"{ou} : total inconnu")
            comp = tuple(_terme(t, connues, ou) for t in q.get("composantes") or [])
            reste = _terme(q["reste"], connues, ou) if q.get("reste") else None
            if reste:
                if reste.ligne in restes_vus:
                    raise GabaritInvalide(f"{ou} : « {reste.ligne} » est déjà le reste de "
                                          f"{restes_vus[reste.ligne]}")
                if lignes[reste.ligne].recettes or lignes[reste.ligne].calcul:
                    raise GabaritInvalide(f"{ou} : un reste se calcule par différence, il ne se "
                                          f"dépose pas — « {reste.ligne} » porte des recettes")
                restes_vus[reste.ligne] = q["total"]
            cadrages = {lignes[t.ligne].cadrage for t in comp + ((reste,) if reste else ())}
            cadrages.add(lignes[q["total"]].cadrage)
            if len(cadrages) != 1:
                raise GabaritInvalide(f"{ou} : mêle un flux et un instant — {sorted(cadrages)}")
            equations.append(Equation(e["id"], q["total"], comp, reste))
    orphelines = [l.id for l in lignes.values()
                  if not l.recettes and not l.calcul and not l.recettes_par_emetteur
                  and l.id not in restes_vus]
    if orphelines:
        raise GabaritInvalide(f"lignes sans recette, sans calcul et qui ne sont le reste d'aucune "
                              f"équation (toujours vides) : {orphelines}")
    return Gabarit(str(brut.get("version")), tuple(etats), lignes, tuple(equations))


@dataclass(frozen=True)
class Reclassement:
    """Un reclassement d'analyste PROPRE À UN ÉMETTEUR : la ligne maison qu'il alimente, les concepts
    déposés qui la composent (sommés, comme une recette), son motif et sa pièce."""
    ligne: str
    concepts: tuple[str, ...]
    motif: str
    piece: str


def charger_reclassements(cik: Optional[int], gabarit: Gabarit,
                          chemin: Path = EMETTEURS_YAML) -> tuple[Reclassement, ...]:
    """Les reclassements de CET émetteur (clé : CIK), validés contre le gabarit. Aucun = `()`."""
    brut = yaml.safe_load(Path(chemin).read_text(encoding="utf-8")) or {}
    out: list[Reclassement] = []
    for r in ((brut.get("emetteurs") or {}).get(str(cik)) or []) if cik is not None else []:
        ligne = gabarit.lignes.get(r.get("ligne"))
        if ligne is None or not ligne.recettes_par_emetteur:
            raise GabaritInvalide(f"reclassement de l'émetteur {cik} vers « {r.get('ligne')} » : ce n'est pas "
                                  "une ligne à recettes par émetteur du gabarit")
        motif, piece = str(r.get("motif") or "").strip(), str(r.get("piece") or "").strip()
        if len(motif) < 40 or not piece.startswith("http"):
            raise GabaritInvalide(f"reclassement de l'émetteur {cik} vers « {ligne.id} » sans motif écrit ni "
                                  "pièce : un reclassement d'analyste se justifie, il ne se déclare pas")
        concepts = tuple(r.get("concepts") or ())
        if not concepts:
            raise GabaritInvalide(f"reclassement de l'émetteur {cik} vers « {ligne.id} » sans concept")
        out.append(Reclassement(ligne.id, concepts, motif, piece))
    if len({r.ligne for r in out}) != len(out):
        raise GabaritInvalide(f"émetteur {cik} : deux reclassements vers la même ligne")
    return tuple(out)


# ── Le socle reconstitué ────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Periode:
    id: str                       # "FY2025", "TTM2026-06-30", "B2026-06-30"
    nature: NaturePeriode
    cadrage: str                  # "flux" | "instant"
    fin: str                      # ISO
    libelle: str


@dataclass
class Cellule:
    ligne: str
    periode: str
    etat: EtatCellule
    valeur: Optional[float] = None
    # Provenance : les lectures déposées qui la composent (concept, accn, form, filed, start, end, val,
    # et pour les douze mois les trois composantes) ; ou, pour une cellule déduite, l'équation.
    lectures: list[dict[str, Any]] = field(default_factory=list)
    equation: Optional[str] = None
    # Postes non déposés que cette ligne « par différence » absorbe (ils comptent dans le reste).
    absorbe: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Controle:
    equation: str
    periode: str
    statut: Literal["ok", "ecart"]
    gauche: float
    droite: float

    @property
    def ecart(self) -> float:
        return self.gauche - self.droite


@dataclass
class SocleComptes:
    version_gabarit: str
    periodes: list[Periode]
    cellules: dict[tuple[str, str], Cellule]
    controles: list[Controle]
    refus: list[str]                       # ce qui n'a pas pu être reconstitué, nommé
    dernier_depot: Optional[dict[str, Any]] = None   # {accn, form, filed} le plus récent lu
    reclassements: tuple[Reclassement, ...] = ()

    def valeur(self, ligne: str, periode: str) -> Optional[float]:
        c = self.cellules.get((ligne, periode))
        return c.valeur if c else None

    def ecarts(self) -> list[Controle]:
        return [c for c in self.controles if c.statut == "ecart"]


def _iso(d: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(d))
    except (TypeError, ValueError):
        return None


def _series_flux(faits: dict[str, list[dict[str, Any]]], concepts: Iterable[str]) -> list[str]:
    """Les fins d'exercice ANNUELLES publiées par le premier concept de la liste qui en porte."""
    for c in concepts:
        if c not in faits:
            continue
        try:
            serie, _, cadrage = serie_du_concept(faits[c], c)
        except AppariementInexecutable:
            continue
        if cadrage == "flux" and serie:
            return [p["end"] for p in serie]
    return []


def _derniere_fin_de_flux(faits: dict[str, list[dict[str, Any]]], concept: str) -> Optional[str]:
    if concept not in faits:
        return None
    try:
        _, pts = points_de_l_unite_retenue(faits[concept], concept)
    except AppariementInexecutable:
        return None
    fins = [str(p["end"]) for p in pts if p.get("start")]
    return max(fins) if fins else None


def _dernier_instant(faits: dict[str, list[dict[str, Any]]], concept: str) -> Optional[str]:
    if concept not in faits:
        return None
    try:
        serie, _, cadrage = serie_du_concept(faits[concept], concept)
    except AppariementInexecutable:
        return None
    return serie[-1]["end"] if cadrage == "instant" and serie else None


def periodes_du_socle(faits: dict[str, list[dict[str, Any]]], gabarit: Gabarit
                      ) -> tuple[list[Periode], list[str]]:
    """Les colonnes du socle, lues au dépôt. Pure. Rend (périodes, refus nommés).

    Les exercices s'ancrent sur le RÉSULTAT NET (toute société qui dépose publie son résultat ; le
    chiffre d'affaires manque chez une pré-revenus), le dernier bilan sur le TOTAL DE L'ACTIF.
    """
    refus: list[str] = []
    ancre_flux = [c for r in gabarit.lignes["resultat_net"].recettes for c in r]
    fins = _series_flux(faits, ancre_flux)[-NB_EXERCICES:]
    if not fins:
        return [], ["aucun exercice annuel du résultat net n'est déposé : pas de socle sans exercice"]
    periodes = [Periode(f"FY{f}", "exercice", "flux", f, f"Exercice clos le {f}") for f in fins]
    derniere = _derniere_fin_de_flux(faits, ancre_flux[0])
    if derniere and derniere > fins[-1]:
        periodes.append(Periode(f"TTM{derniere}", "douze_mois", "flux", derniere,
                                f"Douze mois au {derniere}"))
    periodes += [Periode(f"B{f}", "exercice", "instant", f, f"Bilan au {f}") for f in fins]
    ancre_bilan = [c for r in gabarit.lignes["total_actif"].recettes for c in r][0]
    dernier = _dernier_instant(faits, ancre_bilan)
    if dernier is None:
        refus.append("le total de l'actif n'est déposé à aucun instant : pas de dernier bilan")
    elif dernier > fins[-1]:
        periodes.append(Periode(f"B{dernier}", "dernier_bilan", "instant", dernier,
                                f"Dernier bilan au {dernier}"))
    return periodes, refus


def _lecture(concept: str, p: dict[str, Any]) -> dict[str, Any]:
    return {"concept": concept, "val": float(p["val"]), "start": p.get("start"), "end": p.get("end"),
            "form": p.get("form"), "accn": p.get("accn"), "filed": p.get("filed")}


def lire_concept(faits: dict[str, list[dict[str, Any]]], concept: str, periode: Periode
                 ) -> Optional[tuple[float, list[dict[str, Any]]]]:
    """La valeur d'UN concept pour UNE période, et ses lectures. None si non déposé. Pure.

    Chaque cadrage passe par son détenteur unique : exercice → `serie_du_concept` + tolérance
    d'ancre ; douze mois → `douze_mois_glissants` (un terme manquant = None, jamais l'exercice) ;
    instant → `serie_du_concept` côté instant. Un concept de flux n'est jamais lu en instant ni
    l'inverse : le cadrage du concept doit être celui de la ligne.
    """
    bruts = faits.get(concept)
    if not bruts:
        return None
    try:
        serie, _, cadrage = serie_du_concept(bruts, concept)
    except AppariementInexecutable:
        return None
    if cadrage != periode.cadrage:
        return None
    fin = _iso(periode.fin)
    if periode.nature == "douze_mois":
        try:
            _, pts = points_de_l_unite_retenue(bruts, concept)
            val, composantes = douze_mois_glissants(pts, fin, concept)
        except AppariementInexecutable:
            return None
        return val, [{"concept": concept, **c} for c in composantes]
    p = point_pour_periode(serie, fin, tol_days=TOLERANCE_ANCRE_J)
    if p is None:
        return None
    return float(p["val"]), [_lecture(concept, p)]


def _lire_ligne(faits, ligne: Ligne, periode: Periode) -> Optional[Cellule]:
    for recette in ligne.recettes:
        lus = [lire_concept(faits, c, periode) for c in recette]
        if all(l is not None for l in lus):
            return Cellule(ligne.id, periode.id, "depose", sum(v for v, _ in lus),
                           [x for _, lect in lus for x in lect])
    return None


def _tolerance(*montants: float) -> float:
    return max(TOLERANCE_ABSOLUE, TOLERANCE_RELATIVE * max((abs(m) for m in montants), default=0.0))


def _resoudre(gabarit: Gabarit, periode: Periode, cellules: dict[str, Cellule]) -> list[Controle]:
    """Résout les équations d'UNE période jusqu'au point fixe, puis publie les contrôles. Mute
    `cellules`. Une équation se résout quand il lui reste UNE inconnue ; une équation sans inconnue
    est un contrôle."""
    eqs = [e for e in gabarit.equations if gabarit.lignes[e.total].cadrage == periode.cadrage]

    def connue(nom: str) -> Optional[float]:
        c = cellules.get(nom)
        if c is None:
            return None
        if c.etat == "compte_zero":
            return 0.0
        return c.valeur

    progres = True
    while progres:
        progres = False
        for eq in eqs:
            # total − Σ sᵢ·xᵢ − s_r·reste = 0 : chaque terme porte son coefficient dans cette forme.
            termes = [(eq.total, +1)] + [(t.ligne, -t.signe) for t in eq.composantes]
            if eq.reste:
                termes.append((eq.reste.ligne, -eq.reste.signe))
            inconnues = [i for i, (nom, _) in enumerate(termes) if connue(nom) is None]
            if len(inconnues) != 1:
                continue
            i = inconnues[0]
            nom_x, coef_x = termes[i]
            valeur = -sum(coef * connue(nom) for j, (nom, coef) in enumerate(termes) if j != i) / coef_x
            etat: EtatCellule = "par_somme" if i == 0 else "par_difference"
            x = Terme(nom_x, 1)
            absorbe = []
            if eq.reste is not None and x.ligne == eq.reste.ligne:
                absorbe = [t.ligne for t in eq.composantes
                           if cellules.get(t.ligne) is not None and cellules[t.ligne].etat == "compte_zero"]
            cellules[x.ligne] = Cellule(x.ligne, periode.id, etat, valeur, [], eq.libelle(), absorbe)
            progres = True

    controles: list[Controle] = []
    for eq in eqs:
        valeurs = {t.ligne: connue(t.ligne) for t in (Terme(eq.total, 1),) + eq.composantes
                   + ((eq.reste,) if eq.reste else ())}
        if any(v is None for v in valeurs.values()):
            continue
        # Une équation qui vient de déduire une de ses lignes est vraie par construction : ce n'est
        # pas un contrôle. Seule une équation dont TOUTES les lignes viennent d'ailleurs en est un.
        if any(cellules[l].equation == eq.libelle() for l in valeurs if l in cellules):
            continue
        gauche = valeurs[eq.total]
        droite = sum(t.signe * valeurs[t.ligne] for t in eq.composantes)
        if eq.reste:
            droite += eq.reste.signe * valeurs[eq.reste.ligne]
        statut = "ok" if abs(gauche - droite) <= _tolerance(gauche, droite) else "ecart"
        controles.append(Controle(eq.libelle(), periode.id, statut, gauche, droite))
    return controles


def reconstituer(faits: dict[str, list[dict[str, Any]]], gabarit: Optional[Gabarit] = None,
                 *, reclassements: tuple[Reclassement, ...] = ()) -> SocleComptes:
    """Les comptes de l'émetteur au format maison, à partir de l'inventaire `companyfacts`. Pure.

    `reclassements` : ceux de CET émetteur (`charger_reclassements`) — ils donnent leur recette aux
    lignes `recettes_par_emetteur`, qui sinon restent comptées zéro."""
    gabarit = gabarit or charger_gabarit()
    propres = {r.ligne: r for r in reclassements}
    periodes, refus = periodes_du_socle(faits, gabarit)
    cellules: dict[tuple[str, str], Cellule] = {}
    controles: list[Controle] = []
    for periode in periodes:
        locales: dict[str, Cellule] = {}
        for ligne in gabarit.lignes.values():
            if ligne.cadrage != periode.cadrage or not (ligne.recettes or ligne.recettes_par_emetteur):
                continue
            if ligne.id in propres:
                ligne = Ligne(**{**ligne.__dict__, "recettes": (propres[ligne.id].concepts,)})
            c = _lire_ligne(faits, ligne, periode)
            if c is not None:
                locales[ligne.id] = c
            elif ligne.absent_vaut_zero:
                locales[ligne.id] = Cellule(ligne.id, periode.id, "compte_zero")
        controles += _resoudre(gabarit, periode, locales)
        for ligne in gabarit.lignes.values():
            if ligne.cadrage != periode.cadrage or not ligne.calcul:
                continue
            vals = [locales.get(t.ligne) for t in ligne.calcul]
            if all(v is not None and (v.valeur is not None or v.etat == "compte_zero") for v in vals):
                valeur = sum(t.signe * (v.valeur or 0.0) for t, v in zip(ligne.calcul, vals))
                formule = " ".join(f"{'+' if t.signe > 0 else '−'} {t.ligne}" for t in ligne.calcul)
                locales[ligne.id] = Cellule(ligne.id, periode.id, "calcule", valeur, [],
                                            f"{ligne.id} = {formule.lstrip('+ ')}")
        for ligne in gabarit.lignes.values():
            if ligne.cadrage != periode.cadrage:
                continue
            cellules[(ligne.id, periode.id)] = locales.get(
                ligne.id, Cellule(ligne.id, periode.id, "non_depose"))
    depots = [l for c in cellules.values() for l in c.lectures if l.get("accn")]
    dernier = max(depots, key=lambda l: (str(l.get("filed") or ""), str(l.get("accn")))) if depots else None
    return SocleComptes(
        gabarit.version, periodes, cellules, controles, refus,
        {k: dernier[k] for k in ("accn", "form", "filed")} if dernier else None,
        tuple(reclassements))


# ── La forme PERSISTÉE et sa lecture (détenteurs uniques, purs) ─────────────────────────────────────
#
# Le socle s'écrit en base comme UNE pièce du dossier (une `knowledge_entry`, `metric = socle_comptes`) :
# le modèle des comptes de l'entreprise, versionné (A1) à chaque nouveau dépôt. Sa forme structurée est
# ce que relit le CODE (l'encadré des chiffres clés, le pont qui le vérifie) ; son texte est ce que lit
# l'ANALYSTE. Les deux sortent d'ici, d'un seul socle — jamais deux rendus d'un même chiffre.

METRIC = "socle_comptes"

# Les périodes qu'un chiffre de l'encadré peut demander au socle — vocabulaire FERMÉ.
PERIODES_DE_CHIFFRE = ("dernier_bilan", "douze_mois", "dernier_exercice")


def structure_du_socle(socle: SocleComptes) -> dict[str, Any]:
    """Le socle en JSON (le `content_structured` de la pièce). Pur."""
    fins = [p.fin for p in socle.periodes]
    return {
        "metric": METRIC,
        "poste_kind": "stock",                       # un seul socle courant par émetteur (#43)
        "period_end": max(fins) if fins else None,
        "version_gabarit": socle.version_gabarit,
        "dernier_depot": socle.dernier_depot,
        "periodes": [p.__dict__ for p in socle.periodes],
        "cellules": {
            f"{c.ligne}|{c.periode}": {
                "v": c.valeur, "e": c.etat,
                **({"c": sorted({l["concept"] for l in c.lectures})} if c.lectures else {}),
                **({"eq": c.equation} if c.equation else {}),
                **({"absorbe": c.absorbe} if c.absorbe else {}),
            }
            for c in socle.cellules.values()
        },
        "controles": [{"equation": c.equation, "periode": c.periode, "statut": c.statut,
                       "ecart": c.ecart} for c in socle.controles],
        "reclassements": [r.__dict__ for r in socle.reclassements],
        "refus": list(socle.refus),
    }


def empreinte(structure: dict[str, Any]) -> tuple:
    """Ce qui fait qu'un socle publié est le MÊME qu'un autre : gabarit, dernier dépôt, cellules,
    reclassements. Deux passages sur le même dépôt ne créent pas de version (idempotence)."""
    cel = structure.get("cellules") or {}
    return (structure.get("version_gabarit"), (structure.get("dernier_depot") or {}).get("accn"),
            tuple(sorted((k, v.get("v"), v.get("e")) for k, v in cel.items())),
            tuple(sorted(r.get("ligne", "") + "|" + ",".join(r.get("concepts", ()))
                         for r in structure.get("reclassements") or [])))


def periode_demandee(structure: dict[str, Any], periode: str) -> Optional[dict[str, Any]]:
    """La colonne du socle qu'une période de chiffre désigne. Pur. None si le socle n'en a pas.

    · `dernier_bilan`    — l'instant le plus récent ;
    · `douze_mois`       — les douze mois glissants, et, quand le dernier dépôt est un rapport annuel,
                           l'exercice qu'il clôt (les douze derniers mois SONT l'exercice, #112) ;
    · `dernier_exercice` — l'exercice clos le plus récent.
    """
    if periode not in PERIODES_DE_CHIFFRE:
        raise ValueError(f"période de chiffre « {periode} » hors de {PERIODES_DE_CHIFFRE}")
    ps = structure.get("periodes") or []
    instants = [p for p in ps if p["cadrage"] == "instant"]
    flux = [p for p in ps if p["cadrage"] == "flux"]
    if periode == "dernier_bilan":
        return max(instants, key=lambda p: p["fin"]) if instants else None
    exercices = [p for p in flux if p["nature"] == "exercice"]
    if periode == "douze_mois":
        glissants = [p for p in flux if p["nature"] == "douze_mois"]
        if glissants:
            return max(glissants, key=lambda p: p["fin"])
    return max(exercices, key=lambda p: p["fin"]) if exercices else None


def valeur_du_socle(structure: dict[str, Any], formule: str, periode: str
                    ) -> tuple[Optional[float], str]:
    """Un chiffre LU dans le socle : (valeur, période ou motif d'absence). Pur. DÉTENTEUR UNIQUE, lu par
    l'encadré de l'analyste et par le pont qui le vérifie (#46).

    `formule` est une formule de `formule_grammaire` sur des LIGNES du gabarit. Une ligne `compte_zero`
    vaut zéro (le gabarit dit que son absence vaut zéro) ; une ligne non déposée rend le chiffre NON
    ÉTABLI en la nommant — jamais un zéro (#25)."""
    from app.contracts.formule_grammaire import FormuleInexecutable, evaluer_formule, noms_de_la_formule
    col = periode_demandee(structure, periode)
    if col is None:
        return None, f"non établi : le socle des comptes n'a pas de période « {periode} »"
    cel = structure.get("cellules") or {}
    valeurs: dict[tuple[str, int], float] = {}
    manquantes = []
    for nom in sorted(noms_de_la_formule(formule)):
        c = cel.get(f"{nom}|{col['id']}")
        if c is None or (c.get("v") is None and c.get("e") != "compte_zero"):
            manquantes.append(nom)
            continue
        valeurs[(nom, 0)] = 0.0 if c.get("e") == "compte_zero" else float(c["v"])
    if manquantes:
        return None, (f"non établi : {', '.join(manquantes)} non déposé(s) au {col['libelle'].lower()} "
                      "dans le socle des comptes")
    try:
        v = evaluer_formule(formule, valeurs)
    except FormuleInexecutable as e:
        return None, f"non calculable : {e}"
    return v, f"{col['libelle']} — socle des comptes : {formule}"


def rendre_socle(structure: dict[str, Any], gabarit: Gabarit, *, raison_sociale: str) -> str:
    """Le texte que lit l'ANALYSTE : les trois états en millions de dollars, exacts au dixième (un
    arrondi au milliard se recopie — #113, « 1,22 Md$ » pour 1 223,03 M$). Pur."""
    ps = structure.get("periodes") or []
    cel = structure.get("cellules") or {}
    depot = structure.get("dernier_depot") or {}
    out = [f"Comptes de {raison_sociale} reconstitués au format maison depuis les dépôts SEC "
           f"(gabarit {structure.get('version_gabarit')}, dernier dépôt lu : {depot.get('form')} déposé "
           f"le {depot.get('filed')}). Montants en millions de dollars, tels que déposés (une charge est "
           "positive). Une ligne « solde du bouclage » est l'écart déterministe entre un total déposé et "
           "les lignes nommées au-dessus. « n.d. » : ligne non déposée par l'émetteur."]
    for r in structure.get("reclassements") or []:
        out.append(f"Reclassement d'analyste — {gabarit.lignes[r['ligne']].libelle} : "
                   f"{', '.join(r['concepts'])}. {r['motif']} (pièce : {r['piece']})")
    for etat_id, libelle, cadrage in gabarit.etats:
        cols = [p for p in ps if p["cadrage"] == cadrage]
        if not cols:
            continue
        out.append("")
        out.append(f"{libelle} — " + " | ".join(p["libelle"] for p in cols))
        for l in gabarit.lignes_de(etat_id):
            vals = []
            for p in cols:
                c = cel.get(f"{l.id}|{p['id']}") or {}
                v = c.get("v")
                vals.append("n.d." if v is None else f"{v / 1e6:,.1f}".replace(",", " "))
            out.append(f"  {l.libelle} : " + " | ".join(vals))
    ecarts = [c for c in structure.get("controles") or [] if c["statut"] == "ecart"]
    out.append("")
    out.append(f"Bouclages : {len(structure.get('controles') or [])} contrôles, "
               + ("aucun écart." if not ecarts else f"{len(ecarts)} écart(s) : " + " ; ".join(
                   f"{c['periode']} {c['equation']} (écart {c['ecart'] / 1e6:,.1f} M$)" for c in ecarts)))
    return "\n".join(out)
