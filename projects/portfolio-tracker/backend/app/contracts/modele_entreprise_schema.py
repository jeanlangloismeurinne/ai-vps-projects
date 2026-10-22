"""Contrat du CLASSEUR DE L'ENTREPRISE — catalogue, architecture, cellule, fourchette, scénario,
déplacement (roadmap 09 §9/§12, lot M1, conventions #97/#98/#140).

CE QUE FERAIT UN VRAI FONDS, ET CE QUE M1 LIVRE
------------------------------------------------
Le directeur de la recherche tient UNE fiche par hypothèse maison (`FicheVariable`) et des feuilles
de départ par type d'entreprise (`Patron`) ; l'architecte, dédié à chaque titre (M3), compose
l'`Architecture` à partir de ces fiches — les blocs, les variables qu'il retient par bloc, la règle
de passage au format agrégé des comptes, et la liste des cellules à remplir. Le comité signe cette
architecture (M3, migration 062) ; l'analyste et le collecteur écrivent ensuite des `Cellule`
(M4/M5). Les scénarios se bâtissent sur un inventaire de variables à fourchette (`Fourchette`,
`Scenario`, `Deplacement`) — ce fichier en FIXE LA FORME dès M1, seul le scénario central est
peuplé (09 §12.2) ; le moteur de génération de scénarios et le calcul des fourchettes arrivent en
M6.

CE QUE CE FICHIER VÉRIFIE, ET CE QU'IL NE PEUT PAS VÉRIFIER (#37)
------------------------------------------------------------------
Ici : la cohérence INTERNE de chaque objet (identifiants uniques, vocabulaires fermés, formes
mutuellement exclusives — « publié » porte un rattachement publié, pas un autre). Là-bas
(`app/modele_entreprise/referentiel.py`, `_valider_pont_referentiel` / `valider_pont_architecture` /
`valider_cellule`) : ce qui demande de connaître un AUTRE objet — le référentiel contre
`frameworks.yaml` et le socle des comptes, une architecture contre le référentiel qui la fonde, une
cellule contre l'architecture qui l'attend. Un contrat valide un objet, jamais la cohérence entre
deux.

La SIGNATURE de l'architecture n'est pas ici : c'est un acte au procès-verbal (M3, migration 062),
pas une propriété de l'architecture proposée — même geste que `modele_valorisation_schema.py` /
`signature_modele_schema.py`.

Cible : pydantic v2 (container). Module PUR.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, Field, model_validator

from .analysis_v2_schemas import Strict
from .formule_grammaire import FormuleInexecutable, analyser_formule, noms_de_la_formule
from .modele_valorisation_schema import OrigineJugement, OriginePiece, OrigineReprise

__all__ = [
    "ARCHITECTURE_SCHEMA_VERSION",
    "annee_de_periode",
    # référentiel
    "FicheVariable", "FamilleDeComptes", "BlocDePatron", "Patron", "ReferentielModele", "UniteDimension",
    # origines d'une cellule
    "OrigineCalcul", "OrigineCellule",
    # architecture
    "VariablePropre", "RattachementPublie", "RattachementParent", "RattachementAgrege", "Rattachement",
    "Jalon", "BlocPropose", "Bloc", "PassageAgrege", "AuteurQuestion", "AuteurDemande", "AuteurCellule",
    "CelluleAttendue", "AxeUsage", "ManqueDuDossier", "Architecture",
    # cellule écrite
    "AuteurQuestionEcrite", "AuteurDemandeEcrite", "AuteurCelluleEcrite", "Cellule",
    # fourchette, scénario, déplacement
    "Fourchette", "Deplacement", "Scenario", "SCENARIO_CENTRAL",
]

# 1.2.0 — lot M3 bis (roadmap V3 `13-lot-M3bis-structure.md`, principe fondateur n° 4) : traite les
# CAUSES des erreurs des architectures à blanc du 2026-10-22, pas leurs symptômes.
#   ① `RattachementPublie.membres` (liste, regroupement) remplace `membre` (un seul) ; `Bloc.maille`
#     n'est plus un champ du modèle (`BlocPropose`, ce que l'agent produit) — le CODE la pose
#     (`publie` si `RattachementPublie`, `estime` sinon, `app/modele_entreprise/faits_publies.py`) ;
#     `ArchitecteSortie.autres_axes` (place pour le second découpage publié, hors de l'arbre).
#   ② (rendu, `ventilation.py` — aucun champ de contrat)
#   ③ `Bloc`/`Architecture.manques_du_dossier` (ce que le dossier ne permet pas de découper).
#   ④ `ReferentielModele.unites` (table des dimensions physiques, `dimensions.py`, [S11]).
#   ⑤ `Bloc.origine` (interne/acquisition/licence/partenariat), `Bloc.jalon` (requis SSI
#     `statut == "en_developpement"`) — [S12] (ici, invariant d'un seul objet, #37).
# 0 ligne en base à cette date (migration 061 appliquée, aucune architecture encore proposée) :
# aucune reprise à écrire.
ARCHITECTURE_SCHEMA_VERSION = "architecture-1.2.0"

def _sans_double_tiret_bas(v: str) -> str:
    # Un id ne contient JAMAIS `__` (double tiret bas) : c'est le séparateur réservé des formules
    # de passage à l'agrégé (`bloc__variable`, §2.3). Sans cette règle, `partition("__")` ne
    # saurait plus distinguer le bloc de la variable dans un nom composé. Le moteur regex de
    # pydantic v2 (Rust) n'admet pas le lookahead : la règle se porte donc en `AfterValidator`,
    # pas dans le `pattern`.
    if "__" in v:
        raise ValueError(f"l'identifiant `{v}` contient `__` (double tiret bas), réservé au "
                         "séparateur `bloc__variable` d'une formule de passage")
    return v


Identifiant = Annotated[
    str, Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=60), AfterValidator(_sans_double_tiret_bas)]
QuestionId = Annotated[str, Field(pattern=r"^[a-z]{2}_[0-9]+$")]
# `FY2025`, ou `sans_periode` pour une variable qui n'a pas de période (§2.3/§2.4).
PeriodeCellule = Annotated[str, Field(pattern=r"^(FY[0-9]{4}|sans_periode)$")]


def annee_de_periode(periode: str) -> Optional[int]:
    """L'année d'une période `FY####`, ou `None` pour `sans_periode`. DÉTENTEUR UNIQUE (#46) de
    l'ordre des périodes du classeur : `Fourchette._ordonnee`, `Scenario` (chevauchement de deux
    déplacements) et `app/modele_entreprise/scenarios.appliquer_scenario` l'appellent tous, pour
    que « ce que le contrat ordonne » et « ce que le moteur applique » ne puissent pas diverger."""
    return int(periode[2:]) if periode.startswith("FY") else None


def _sans_doublon(valeurs: list[str], ou: str) -> None:
    if len(set(valeurs)) != len(valeurs):
        raise ValueError(f"{ou} : doublon dans {valeurs}")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2.1 — LE RÉFÉRENTIEL
# ═══════════════════════════════════════════════════════════════════════════════════════════════

ORIGINES_CELLULE = ("piece", "reponse_reprise", "jugement", "calcul")
ROLES_BLOC = ("activite", "programme", "metier", "commun")
# 1.2.0 (cause ⑤, §6) — la MATURITÉ (`statut`) et l'ORIGINE d'un bloc sont deux champs disjoints :
# une acquisition conclue est `metier_actuel`, jamais `en_developpement` ([S12] ci-dessous).
ORIGINES_BLOC = ("interne", "acquisition", "licence", "partenariat")


class UniteDimension(Strict):
    """Une unité du catalogue (1.2.0, cause ④, §5) : sa dimension PHYSIQUE (exposants de montant,
    de quantité, de temps) et son échelle par rapport à l'unité de base ($ pour un montant, une
    unité pour une quantité, une année pour un temps). DÉTENTEUR UNIQUE : la table
    `ReferentielModele.unites`, lue par `app/modele_entreprise/dimensions.py` — jamais recopiée."""
    montant: int = 0
    quantite: int = 0
    temps: int = 0
    echelle: Annotated[float, Field(gt=0)]


class FicheVariable(Strict):
    """Une hypothèse maison du catalogue : définition, unité, période, d'où peut venir le chiffre,
    comment on le contrôle, comment on en borne l'incertitude, à quelle(s) question(s) elle se
    raccorde et dans quelle(s) famille(s) de comptes elle a un sens."""
    id: Identifiant
    libelle: Annotated[str, Field(min_length=10)]
    definition: Annotated[str, Field(min_length=40)]
    unite: Annotated[str, Field(min_length=1)]
    periode: Literal["exercice", "instant", "sans_periode"]
    origines_admises: Annotated[
        list[Literal["piece", "reponse_reprise", "jugement", "calcul"]], Field(min_length=1)]
    controle: Optional[str] = None
    questions_sources: list[QuestionId] = Field(default_factory=list)
    familles: Annotated[list[str], Field(min_length=1)]
    methode_de_fourchette: Annotated[list[str], Field(min_length=1)]
    # 1.1.0 (lot M3, §2.1) : « le chiffre d'affaires des blocs de premier niveau s'additionne en
    # cette ligne de l'agrégé » — c'est la donnée que lit [S7] (`modele_entreprise/structure.py`).
    # Détenteur unique (#46) : le code ne nomme jamais `chiffre_affaires_du_bloc`/`chiffre_affaires`.
    somme_vers_ligne: Optional[Identifiant] = None

    @model_validator(mode="after")
    def _sans_doublons_et_calcul_coherent(self) -> "FicheVariable":
        _sans_doublon(list(self.origines_admises), f"`{self.id}`.origines_admises")
        _sans_doublon(list(self.questions_sources), f"`{self.id}`.questions_sources")
        _sans_doublon(list(self.familles), f"`{self.id}`.familles")
        _sans_doublon(list(self.methode_de_fourchette), f"`{self.id}`.methode_de_fourchette")
        if self.controle == "part_calculee" and list(self.origines_admises) != ["calcul"]:
            raise ValueError(
                f"`{self.id}` : le contrôle `part_calculee` exige `origines_admises == [\"calcul\"]`, "
                f"reçu {self.origines_admises}")
        return self


class FamilleDeComptes(Strict):
    """Le format agrégé d'une famille de comptes (industrielle, bancaire, 09 §12.1) — ou pourquoi
    il n'existe pas encore (`motif_absence`). `gabarit` null, `motif_absence` présent et
    `lignes_du_business_plan` vide sont les TROIS faces du même fait : une famille sans format
    agrégé n'a ni fichier de gabarit, ni lignes, et le dit."""
    gabarit: Optional[str] = None
    motif_absence: Optional[Annotated[str, Field(min_length=20)]] = None
    lignes_du_business_plan: list[Identifiant] = Field(default_factory=list)

    @model_validator(mode="after")
    def _equivalence_gabarit_motif_lignes(self) -> "FamilleDeComptes":
        sans_gabarit = self.gabarit is None
        a_motif = self.motif_absence is not None
        lignes_vides = not self.lignes_du_business_plan
        if not (sans_gabarit == a_motif == lignes_vides):
            raise ValueError(
                "une famille de comptes sans gabarit porte un motif d'absence ET des lignes vides, "
                f"jamais un mélange (gabarit absent={sans_gabarit}, motif présent={a_motif}, "
                f"lignes vides={lignes_vides})")
        return self


class BlocDePatron(Strict):
    role: Literal["activite", "programme", "metier", "commun"]
    variables: Annotated[list[Identifiant], Field(min_length=1)]


class Patron(Strict):
    blocs: Annotated[list[BlocDePatron], Field(min_length=1)]


class ReferentielModele(Strict):
    """Le fichier `frameworks/modele_entreprise.yaml` entier."""
    version: Annotated[str, Field(min_length=1)]
    # 1.1.0 (lot M3, §2.1) — l'INTERRUPTEUR de la signature de l'architecture (principe fondateur
    # n° 3) : REQUIS, sans défaut — un référentiel qui ne tranche pas explicitement ce point
    # laisserait `servir_architecture` deviner. Lu à la LECTURE, jamais recopié (#53).
    signature_de_l_architecture: bool
    # 1.1.0 (arbitrage de l'utilisateur, 2026-10-22) — l'INTERRUPTEUR de la phase de test de la
    # porte : REQUIS, sans défaut. `false` (cible) : une réponse renvoyée par le contrôle FERME la
    # porte — l'architecte ne construit que sur des réponses justes. `true` (phase de test) :
    # elle OUVRE la porte, marquée « refusée par le contrôle ». Lu à la LECTURE
    # (`porte_de_l_architecte`), jamais recopié (#53).
    porte_admet_reponses_refusees: bool
    familles_de_comptes: dict[Identifiant, FamilleDeComptes]
    famille_par_archetype: dict[str, str]
    controles: Annotated[list[Identifiant], Field(min_length=1)]
    methodes_de_fourchette: Annotated[list[Identifiant], Field(min_length=1)]
    variables: Annotated[list[FicheVariable], Field(min_length=1)]
    patrons: dict[str, Patron]
    # 1.2.0 (cause ④, §5) — la table des UNITÉS, DÉTENTEUR UNIQUE de leur dimension physique et de
    # leur échelle. REQUISE, sans défaut : un référentiel qui ne la porte pas laisserait
    # `dimensions.py` deviner l'unité d'une fiche.
    unites: Annotated[dict[str, UniteDimension], Field(min_length=1)]

    @model_validator(mode="after")
    def _coherence_interne(self) -> "ReferentielModele":
        ids = [v.id for v in self.variables]
        _sans_doublon(ids, "le référentiel")
        par_id = {v.id: v for v in self.variables}

        for v in self.variables:
            for f in v.familles:
                if f not in self.familles_de_comptes:
                    raise ValueError(f"`{v.id}` déclare la famille `{f}`, absente de `familles_de_comptes`")
            if v.controle is not None and v.controle not in self.controles:
                raise ValueError(f"`{v.id}` déclare le contrôle `{v.controle}`, absent de `controles`")
            for m in v.methode_de_fourchette:
                if m not in self.methodes_de_fourchette:
                    raise ValueError(f"`{v.id}` déclare la méthode `{m}`, absente de `methodes_de_fourchette`")
            # [R7] (cause ④, §5) — toute fiche a une unité de la table `unites`.
            if v.unite not in self.unites:
                raise ValueError(
                    f"[R7] `{v.id}` déclare l'unité `{v.unite}`, absente de la table `unites` "
                    f"({sorted(self.unites)})")

        for archetype, famille in self.famille_par_archetype.items():
            if famille not in self.familles_de_comptes:
                raise ValueError(f"l'archétype `{archetype}` vise la famille `{famille}`, non déclarée")

        for nom_patron, patron in self.patrons.items():
            if nom_patron not in self.famille_par_archetype:
                raise ValueError(
                    f"le patron `{nom_patron}` ne correspond à aucun archétype de `famille_par_archetype`")
            famille_archetype = self.famille_par_archetype[nom_patron]
            for bloc in patron.blocs:
                for vid in bloc.variables:
                    fiche = par_id.get(vid)
                    if fiche is None:
                        raise ValueError(
                            f"le patron `{nom_patron}` (bloc `{bloc.role}`) retient `{vid}`, absente du catalogue")
                    if famille_archetype not in fiche.familles:
                        raise ValueError(
                            f"le patron `{nom_patron}` retient `{vid}`, qui n'a pas de sens dans la famille "
                            f"`{famille_archetype}` (familles de la fiche : {fiche.familles})")
        return self


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2.2 — LES ORIGINES D'UNE CELLULE
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class OrigineCalcul(Strict):
    """Une cellule CALCULÉE à partir d'autres cellules du même bloc et de la même période —
    4ᵉ origine, propre au classeur. `formule` est validée par la grammaire fermée existante
    (`formule_grammaire.analyser_formule`, #46 : détenteur unique, pas recopiée) ; les noms qu'elle
    référence sont des ids de VARIABLE (le pont vérifie qu'ils sont retenus par le même bloc, [C5])."""
    type: Literal["calcul"]
    formule: str

    @model_validator(mode="after")
    def _formule_valide(self) -> "OrigineCalcul":
        try:
            analyser_formule(self.formule)
        except FormuleInexecutable as e:
            raise ValueError(f"`formule` hors de la grammaire fermée — {e}") from e
        return self


# Réutilise `Origine` de `modele_valorisation_schema.py` (#46, détenteur unique) : une cellule
# admet les mêmes trois origines qu'une hypothèse de valorisation (pièce, réponse reprise, jugement
# ancré), plus `calcul`.
OrigineCellule = Annotated[
    Union[OriginePiece, OrigineReprise, OrigineJugement, OrigineCalcul], Field(discriminator="type")]


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2.3 — L'ARCHITECTURE (sortie de l'agent architecte, M3 ; M1 EN FIXE LA FORME)
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class VariablePropre(FicheVariable):
    """Une variable déclarée par l'architecte HORS catalogue, marquée « propre au titre » pour le
    comité — même fiche complète qu'une variable du catalogue, plus le motif de son ajout."""
    motif: Annotated[str, Field(min_length=30)]


class RattachementPublie(Strict):
    """Le bloc EST un ou plusieurs faits XBRL dimensionnés — axe et membre(s) en clair (le pont
    contre la ventilation au socle vérifie l'existence de chaque adresse, [S1]).

    1.2.0 (cause ①, §2) — `membres` (liste) remplace `membre` (un seul) : PLUSIEURS membres publiés
    du MÊME axe, de MÊMES parents, peuvent former UN bloc de REGROUPEMENT (ex. de forme : les
    membres sous le seuil de matérialité réunis en un seul bloc publié) — le regroupement reste un
    bloc PUBLIÉ, pas un estimé ([S1] vérifie que `len(membres) > 1` implique le même parent)."""
    type: Literal["publie"]
    axe: Annotated[str, Field(min_length=1)]
    membres: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]

    @model_validator(mode="after")
    def _sans_doublon_membres(self) -> "RattachementPublie":
        _sans_doublon(self.membres, f"le rattachement publié de l'axe `{self.axe}`")
        return self


class RattachementParent(Strict):
    """Le bloc est un découpage ESTIMÉ, plus fin que la publication, à l'intérieur d'un autre bloc
    déclaré (09 §4 : le cas « grands hébergeurs » à l'intérieur d'un segment publié)."""
    type: Literal["parent"]
    bloc: Identifiant


class RattachementAgrege(Strict):
    """Le bloc est entièrement ESTIMÉ et se raccorde directement à une ligne des comptes
    reconstitués (09 §4 : le cas d'un émetteur qui ne publie rien à la maille du bloc, et dont
    tous les blocs sont estimés)."""
    type: Literal["agrege"]
    ligne: Identifiant


Rattachement = Annotated[
    Union[RattachementPublie, RattachementParent, RattachementAgrege], Field(discriminator="type")]


class Jalon(Strict):
    """Requis SSI `Bloc.statut == \"en_developpement\"`, interdit sinon (1.2.0, cause ⑤, §6).
    `prochain` est le jalon que mesure la fiche `probabilite_de_succes` — DÉTENTEUR UNIQUE de son
    énoncé, jamais recopié ailleurs."""
    franchi: Annotated[str, Field(min_length=10)]
    franchi_le: date
    prochain: Annotated[str, Field(min_length=10)]
    attendu_vers: Optional[date] = None


class BlocPropose(Strict):
    """Ce que le MODÈLE produit pour un bloc (1.2.0, cause ①, §2) — SANS `maille` : la maille
    (`publie` si `rattachement` est `RattachementPublie`, `estime` sinon) n'est plus déclarée, le
    CODE la pose en même temps que l'en-tête (`app/modele_entreprise/faits_publies.py`,
    `poser_maille`) — ni `Bloc.maille` demandée au modèle, ni son emboîtement entre blocs publiés
    (DÉRIVÉ de la hiérarchie de la ventilation, jamais déclaré pour un `RattachementPublie`)."""
    id: Identifiant
    libelle: Annotated[str, Field(min_length=1)]
    role: Literal["activite", "programme", "metier", "commun"]
    statut: Literal["metier_actuel", "extension_annoncee", "en_developpement"]
    # 1.2.0 (cause ⑤, §6) — l'ORIGINE, distincte de la MATURITÉ (`statut`) : une acquisition est un
    # fait acquis (conclue) ou en négociation (annoncée), jamais « en développement ».
    origine: Literal["interne", "acquisition", "licence", "partenariat"]
    jalon: Optional[Jalon] = None
    rattachement: Rattachement
    variables: Annotated[list[Identifiant], Field(min_length=1)]
    # pourquoi ce bloc existe, à cette maille, sous ce statut : ce que le comité lit en signant
    # l'architecture (§6).
    motif: Annotated[str, Field(min_length=20)]
    # Les pièces du dossier qui le fondent (ids de `knowledge_entries`, §3.3) — [S6] vérifie que
    # chacune est dans `Matiere.pieces_citables`.
    pieces: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _jalon_ssi_en_developpement(self) -> "BlocPropose":
        a_jalon = self.jalon is not None
        if a_jalon != (self.statut == "en_developpement"):
            raise ValueError(
                f"`{self.id}` : `jalon` est REQUIS si et seulement si `statut == "
                f"\"en_developpement\"` (reçu statut=`{self.statut}`, jalon {'présent' if a_jalon else 'absent'})")
        return self

    @model_validator(mode="after")
    def _s12_acquisition_jamais_en_developpement(self) -> "BlocPropose":
        # [S12] (1.2.0, cause ⑤, §6) — invariant d'UN SEUL objet (#37) : une acquisition est soit
        # conclue et consolidée (`metier_actuel`), soit annoncée et non conclue
        # (`extension_annoncee`) — jamais « en développement », qui désignerait un programme de
        # recherche interne. `licence`/`partenariat` admettent n'importe quel statut.
        if self.origine == "acquisition" and self.statut not in ("metier_actuel", "extension_annoncee"):
            raise ValueError(
                f"[S12] `{self.id}` : origine `acquisition` exige `statut` ∈ "
                f"{{metier_actuel, extension_annoncee}}, reçu `{self.statut}` — une acquisition "
                "conclue ou annoncée n'est jamais « en développement »")
        return self


class Bloc(BlocPropose):
    """L'architecture POSÉE (après l'en-tête, §4.1 point 4) : `maille` est AJOUTÉE par le code
    (`faits_publies.poser_maille`), jamais déclarée par le modèle (`BlocPropose` ne la porte pas)."""
    maille: Literal["publie", "estime"]

    @model_validator(mode="after")
    def _maille_correspond_au_rattachement(self) -> "Bloc":
        est_publie = isinstance(self.rattachement, RattachementPublie)
        if (self.maille == "publie") != est_publie:
            raise ValueError(
                f"`{self.id}` : maille `{self.maille}` incohérente avec un rattachement "
                f"`{self.rattachement.type}` — `publie` va avec `publie`, rien d'autre")
        return self

    @model_validator(mode="after")
    def _pieces_si_estime_ou_annonce(self) -> "Bloc":
        # Un découpage ESTIMÉ, ou une activité qui n'est pas `metier_actuel` (annoncée, en
        # développement), n'est qu'une opinion sans au moins une pièce qui la fonde (§2.2).
        if (self.maille == "estime" or self.statut != "metier_actuel") and not self.pieces:
            raise ValueError(
                f"`{self.id}` : maille `{self.maille}`, statut `{self.statut}` — un découpage estimé "
                "ou une activité qui n'est pas `metier_actuel` doit citer au moins une pièce "
                "(`pieces`), sinon ce n'est qu'une opinion")
        return self


class PassageAgrege(Strict):
    """La règle de passage du détail à l'agrégé : une ligne des comptes reconstitués de la famille
    = une formule sur des noms `bloc__variable` (double tiret bas, §2.3 — jamais dans un id)."""
    ligne: Identifiant
    formule: str

    @model_validator(mode="after")
    def _formule_valide(self) -> "PassageAgrege":
        try:
            analyser_formule(self.formule)
        except FormuleInexecutable as e:
            raise ValueError(f"`formule` hors de la grammaire fermée — {e}") from e
        return self


class AuteurQuestion(Strict):
    type: Literal["question"]
    question_id: QuestionId


class AuteurDemande(Strict):
    type: Literal["demande_ciblee"]


AuteurCellule = Annotated[Union[AuteurQuestion, AuteurDemande], Field(discriminator="type")]


class CelluleAttendue(Strict):
    bloc: Identifiant
    variable: Identifiant
    periodes: Annotated[list[PeriodeCellule], Field(min_length=1)]
    auteur: AuteurCellule


class AxeUsage(Strict):
    """1.2.0 (cause ①, §2) — pour CHAQUE axe de la ventilation qui ne porte AUCUN bloc publié, ce
    que l'architecte en fait (raccord des marges, contrôle de concentration, information pour un
    bloc…) : la case qui manquait pour le second découpage publié d'un émetteur (#69 : le rendu
    d'un inventaire est un producteur — un axe SANS bloc et SANS usage est un oubli, [S10])."""
    axe: Annotated[str, Field(min_length=1)]
    usage: Annotated[str, Field(min_length=20)]


class ManqueDuDossier(Strict):
    """1.2.0 (cause ③, §4.4) — ce que le dossier ne permet PAS de découper (programmes non nommés,
    dépense non affectée…), écrit plutôt que regroupé en silence : un signal pour le comité."""
    sujet: Annotated[str, Field(min_length=20)]
    blocs: list[Identifiant] = Field(default_factory=list)
    consequence: Annotated[str, Field(min_length=20)]


class Architecture(Strict):
    """Ce que l'architecte propose (M3/M3 bis) ; M1 n'en fixe que la FORME."""
    schema_version: Literal["architecture-1.2.0"] = ARCHITECTURE_SCHEMA_VERSION
    ticker_id: Annotated[str, Field(min_length=1)]
    version: Annotated[int, Field(ge=1)]
    archetype: Annotated[str, Field(min_length=1)]
    famille: Annotated[str, Field(min_length=1)]
    version_referentiel: Annotated[str, Field(min_length=1)]
    blocs: Annotated[list[Bloc], Field(min_length=1)]
    variables_propres: list[VariablePropre] = Field(default_factory=list)
    passage_a_l_agrege: Annotated[list[PassageAgrege], Field(min_length=1)]
    cellules_attendues: Annotated[list[CelluleAttendue], Field(min_length=1)]
    # 1.2.0 (cause ①, §2) — place pour le second découpage publié, hors de l'arbre ([S10]).
    autres_axes: list[AxeUsage] = Field(default_factory=list)
    # 1.2.0 (cause ③, §4.4) — ce que le dossier ne permet pas de découper.
    manques_du_dossier: list[ManqueDuDossier] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherence_interne(self) -> "Architecture":
        ids_blocs = [b.id for b in self.blocs]
        _sans_doublon(ids_blocs, "l'architecture (ids de bloc)")
        par_bloc = {b.id: b for b in self.blocs}

        for b in self.blocs:
            if isinstance(b.rattachement, RattachementParent):
                if b.rattachement.bloc == b.id:
                    raise ValueError(f"`{b.id}` se rattache à lui-même")
                if b.rattachement.bloc not in par_bloc:
                    raise ValueError(f"`{b.id}` vise le bloc parent `{b.rattachement.bloc}`, non déclaré")
        for b in self.blocs:
            # Parcours BORNÉ par construction (`range(len(blocs) + 1)`), jamais un `while` dont la
            # seule garantie de terminaison serait `cur.id in vus` : si cette garde venait à être
            # affaiblie (ou mutée, cf. `negatif_modele_entreprise.sh`), un `while` boucherait le
            # validateur à l'infini sur un cycle réel — un déni de service, pas un refus nommé.
            vus: set[str] = set()
            cur: Optional[Bloc] = b
            for _ in range(len(self.blocs) + 1):
                if cur is None or not isinstance(cur.rattachement, RattachementParent):
                    break
                if cur.id in vus:
                    raise ValueError(f"cycle de rattachement parent détecté en passant par `{cur.id}`")
                vus.add(cur.id)
                cur = par_bloc.get(cur.rattachement.bloc)

        ids_vp = [v.id for v in self.variables_propres]
        _sans_doublon(ids_vp, "l'architecture (variables propres)")

        axes_autres = [a.axe for a in self.autres_axes]
        _sans_doublon(axes_autres, "l'architecture (autres_axes)")

        lignes_passage = [p.ligne for p in self.passage_a_l_agrege]
        _sans_doublon(lignes_passage, "l'architecture (lignes de passage à l'agrégé)")
        for p in self.passage_a_l_agrege:
            for nom in noms_de_la_formule(p.formule):
                if "__" not in nom:
                    raise ValueError(
                        f"la formule de passage `{p.ligne}` référence `{nom}`, pas de la forme "
                        "`bloc__variable`")
                bloc_id, _, var_id = nom.partition("__")
                bloc = par_bloc.get(bloc_id)
                if bloc is None:
                    raise ValueError(
                        f"la formule de passage `{p.ligne}` référence le bloc `{bloc_id}`, non déclaré")
                if var_id not in bloc.variables:
                    raise ValueError(
                        f"la formule de passage `{p.ligne}` référence `{bloc_id}__{var_id}`, mais le bloc "
                        f"`{bloc_id}` ne retient pas `{var_id}`")

        vues: set[tuple[str, str, str]] = set()
        for c in self.cellules_attendues:
            for periode in c.periodes:
                cle = (c.bloc, c.variable, periode)
                if cle in vues:
                    raise ValueError(
                        f"deux cellules attendues pour (`{c.bloc}`, `{c.variable}`, `{periode}`) — "
                        "un seul auteur par cellule (#99 généralisé)")
                vues.add(cle)
            bloc = par_bloc.get(c.bloc)
            if bloc is None:
                raise ValueError(f"une cellule attendue vise le bloc `{c.bloc}`, non déclaré")
            if c.variable not in bloc.variables:
                raise ValueError(
                    f"une cellule attendue vise `{c.variable}`, que le bloc `{c.bloc}` ne retient pas")
        return self


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2.4 — LA CELLULE (rien de stocké en M1 : vue recalculée à la lecture, 09 §9)
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class AuteurQuestionEcrite(Strict):
    type: Literal["question"]
    question_id: QuestionId
    answer_id: int


class AuteurDemandeEcrite(Strict):
    type: Literal["demande_ciblee"]
    demande_id: int


AuteurCelluleEcrite = Annotated[
    Union[AuteurQuestionEcrite, AuteurDemandeEcrite], Field(discriminator="type")]


class Cellule(Strict):
    bloc: Identifiant
    variable: Identifiant
    periode: PeriodeCellule
    valeur: float
    unite: Annotated[str, Field(min_length=1)]
    origine: OrigineCellule
    auteur: AuteurCelluleEcrite


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2.5 — FOURCHETTE, SCÉNARIO, DÉPLACEMENT (tables dès M1, central seul peuplé en v1, 09 §12.2)
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class Fourchette(Strict):
    bloc: Identifiant
    variable: Identifiant
    periode_debut: PeriodeCellule
    periode_fin: PeriodeCellule
    bas: float
    haut: float
    methode: Identifiant
    origine_bas: OrigineCellule
    origine_haut: OrigineCellule

    @model_validator(mode="after")
    def _ordonnee(self) -> "Fourchette":
        if self.bas > self.haut:
            raise ValueError(f"fourchette de `{self.variable}` : bas ({self.bas}) > haut ({self.haut})")
        ad, af = annee_de_periode(self.periode_debut), annee_de_periode(self.periode_fin)
        if (ad is None) != (af is None):
            raise ValueError(
                f"fourchette de `{self.variable}` : periode_debut (`{self.periode_debut}`) et periode_fin "
                f"(`{self.periode_fin}`) ne sont pas de la même forme")
        if ad is not None and af is not None and ad > af:
            raise ValueError(
                f"fourchette de `{self.variable}` : periode_debut (`{self.periode_debut}`) postérieure à "
                f"periode_fin (`{self.periode_fin}`)")
        return self


class Deplacement(Strict):
    bloc: Identifiant
    variable: Identifiant
    periode_debut: PeriodeCellule
    periode_fin: PeriodeCellule
    cible: Literal["borne_basse", "borne_haute", "valeur_dite"]
    valeur_dite: Optional[float] = None
    motif: Annotated[str, Field(min_length=20)]
    source_entry_refs: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valeur_dite_coherente(self) -> "Deplacement":
        if (self.valeur_dite is not None) != (self.cible == "valeur_dite"):
            raise ValueError("`valeur_dite` est présente SI ET SEULEMENT SI `cible == \"valeur_dite\"`")
        if self.cible == "valeur_dite" and not self.source_entry_refs:
            raise ValueError("une `valeur_dite` exige au moins une pièce (`source_entry_refs`)")
        return self


def _chevauchent(d1: Deplacement, d2: Deplacement) -> bool:
    a1, a2 = annee_de_periode(d1.periode_debut), annee_de_periode(d1.periode_fin)
    b1, b2 = annee_de_periode(d2.periode_debut), annee_de_periode(d2.periode_fin)
    if a1 is None or b1 is None:
        return (d1.periode_debut == d1.periode_fin == d2.periode_debut == d2.periode_fin == "sans_periode")
    return a1 <= b2 and b1 <= a2  # type: ignore[operator]


class Scenario(Strict):
    nom: Identifiant
    recit: Annotated[str, Field(min_length=20)]
    nature: Literal["central", "nomme", "branche"]
    probabilite: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = None
    deplacements: list[Deplacement] = Field(default_factory=list)

    @model_validator(mode="after")
    def _forme_par_nature(self) -> "Scenario":
        if self.nature == "central":
            if self.deplacements:
                raise ValueError("un scénario `central` ne déplace rien")
            if self.probabilite is not None:
                raise ValueError("un scénario `central` ne porte pas de probabilité")
        elif self.nature == "nomme":
            if not self.deplacements:
                raise ValueError("un scénario `nomme` porte au moins un déplacement")
            if self.probabilite is not None:
                raise ValueError("un scénario `nomme` ne porte pas de probabilité")
        else:  # branche
            if not self.deplacements:
                raise ValueError("une `branche` porte au moins un déplacement")
            if self.probabilite is None:
                raise ValueError("une `branche` porte sa probabilité, entre 0 et 1")

        for i, d1 in enumerate(self.deplacements):
            for d2 in self.deplacements[i + 1:]:
                if d1.bloc == d2.bloc and d1.variable == d2.variable and _chevauchent(d1, d2):
                    raise ValueError(
                        f"deux déplacements de `{self.nom}` visent (`{d1.bloc}`, `{d1.variable}`) sur des "
                        "périodes qui se chevauchent")
        return self


# Le central n'est PAS une ligne en base (09 §2.5) : il ne pourrait que diverger de sa définition.
# C'est cette constante que toute évaluation applique par défaut (`app/modele_entreprise/scenarios.py`).
SCENARIO_CENTRAL = Scenario(
    nom="central",
    recit="Le scénario central : les cellules telles qu'elles tiennent aujourd'hui, sans aucun déplacement.",
    nature="central",
    deplacements=[],
)
