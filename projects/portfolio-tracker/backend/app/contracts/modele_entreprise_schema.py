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

from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, Field, model_validator

from .analysis_v2_schemas import Strict
from .formule_grammaire import FormuleInexecutable, analyser_formule, noms_de_la_formule
from .modele_valorisation_schema import OrigineJugement, OriginePiece, OrigineReprise

__all__ = [
    "ARCHITECTURE_SCHEMA_VERSION",
    "annee_de_periode",
    # référentiel
    "FicheVariable", "FamilleDeComptes", "BlocDePatron", "Patron", "ReferentielModele",
    # origines d'une cellule
    "OrigineCalcul", "OrigineCellule",
    # architecture
    "VariablePropre", "RattachementPublie", "RattachementParent", "RattachementAgrege", "Rattachement",
    "Bloc", "PassageAgrege", "AuteurQuestion", "AuteurDemande", "AuteurCellule", "CelluleAttendue",
    "Architecture",
    # cellule écrite
    "AuteurQuestionEcrite", "AuteurDemandeEcrite", "AuteurCelluleEcrite", "Cellule",
    # fourchette, scénario, déplacement
    "Fourchette", "Deplacement", "Scenario", "SCENARIO_CENTRAL",
]

# 1.0.0 — première version du contrat (lot M1).
ARCHITECTURE_SCHEMA_VERSION = "architecture-1.0.0"

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
    familles_de_comptes: dict[Identifiant, FamilleDeComptes]
    famille_par_archetype: dict[str, str]
    controles: Annotated[list[Identifiant], Field(min_length=1)]
    methodes_de_fourchette: Annotated[list[Identifiant], Field(min_length=1)]
    variables: Annotated[list[FicheVariable], Field(min_length=1)]
    patrons: dict[str, Patron]

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
    """Le bloc EST un fait XBRL dimensionné — axe et membre en clair (M0 ; le pont contre la
    ventilation au socle arrive avec M2/M3)."""
    type: Literal["publie"]
    axe: Annotated[str, Field(min_length=1)]
    membre: Annotated[str, Field(min_length=1)]


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


class Bloc(Strict):
    id: Identifiant
    libelle: Annotated[str, Field(min_length=1)]
    role: Literal["activite", "programme", "metier", "commun"]
    statut: Literal["metier_actuel", "extension_annoncee", "en_developpement"]
    maille: Literal["publie", "estime"]
    rattachement: Rattachement
    variables: Annotated[list[Identifiant], Field(min_length=1)]

    @model_validator(mode="after")
    def _maille_correspond_au_rattachement(self) -> "Bloc":
        est_publie = isinstance(self.rattachement, RattachementPublie)
        if (self.maille == "publie") != est_publie:
            raise ValueError(
                f"`{self.id}` : maille `{self.maille}` incohérente avec un rattachement "
                f"`{self.rattachement.type}` — `publie` va avec `publie`, rien d'autre")
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


class Architecture(Strict):
    """Ce que l'architecte propose (M3) ; M1 n'en fixe que la FORME."""
    schema_version: Literal["architecture-1.0.0"] = ARCHITECTURE_SCHEMA_VERSION
    ticker_id: Annotated[str, Field(min_length=1)]
    version: Annotated[int, Field(ge=1)]
    archetype: Annotated[str, Field(min_length=1)]
    famille: Annotated[str, Field(min_length=1)]
    version_referentiel: Annotated[str, Field(min_length=1)]
    blocs: Annotated[list[Bloc], Field(min_length=1)]
    variables_propres: list[VariablePropre] = Field(default_factory=list)
    passage_a_l_agrege: Annotated[list[PassageAgrege], Field(min_length=1)]
    cellules_attendues: Annotated[list[CelluleAttendue], Field(min_length=1)]

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
