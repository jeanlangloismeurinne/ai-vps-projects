"""Le PONT relationnel du classeur de l'entreprise (lot M1 — roadmap 09 §9/§11.2).

Un contrat valide un OBJET, jamais la cohérence entre deux (#37). Tout ce qui exige de connaître un
AUTRE objet — `frameworks.yaml`, le socle des comptes, le référentiel qui fonde une architecture,
l'architecture qui attend une cellule — vit ici, en Python, et lève un refus NOMMÉ, un code lettre
par règle, comme `[S]` de `agents/v2/frameworks.py` :

  · `_valider_pont_referentiel` ([R1]-[R5]) — le référentiel du classeur contre `frameworks.yaml` et
    le socle des comptes. Appelé par `load_referentiel`, qui lève plutôt que de rendre un référentiel
    partiel (même mode de panne que `FrameworkDefinitionRefused`).
  · `valider_pont_architecture` ([P1]-[P5]) — une architecture contre le référentiel qui la fonde.
    [P6] (un bloc `en_developpement`/`extension_annoncee` ne porte jamais `part_de_marche` calculée
    sur une période passée) est NOMMÉ par la spec M1 mais délibérément PAS codé : aucune cellule
    n'existe encore en M1 pour l'exercer (TODO M5, voir `ARCHITECTURE.md`).
  · `valider_cellule` ([C1]-[C5]) — une cellule contre l'architecture qui l'attend et le référentiel
    qui fonde sa fiche.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml
from pydantic import ValidationError

from app.contracts.modele_entreprise_schema import (
    Architecture, AuteurQuestion, Cellule, FicheVariable, OrigineCalcul, ReferentielModele,
)
from app.contracts.formule_grammaire import noms_de_la_formule
from app.modele_entreprise.controles import CONTROLES, ContexteControle

if TYPE_CHECKING:  # import tardif à l'exécution — pas de cycle au chargement du module
    from app.contracts.framework_definition_schema import FrameworksFile

MODELE_ENTREPRISE_YAML = Path(__file__).resolve().parents[1] / "frameworks" / "modele_entreprise.yaml"

__all__ = [
    "ReferentielRefuse", "ArchitectureRefusee", "CelluleRefusee",
    "load_referentiel", "variables_de_la_famille", "questions_sources_applicables",
    "valider_pont_architecture", "valider_cellule",
]


class ReferentielRefuse(Exception):
    """Le référentiel du classeur est formellement valide mais incohérent avec `frameworks.yaml`
    ou le socle des comptes. Lève au chargement, jamais un référentiel partiel."""


class ArchitectureRefusee(Exception):
    """Une architecture formellement valide, mais qui ne tient pas contre le référentiel du titre."""


class CelluleRefusee(Exception):
    """Une cellule formellement valide, mais que l'architecture n'attend pas, ou dont le contrôle
    échoue."""


def _valider_pont_referentiel(ref: ReferentielModele, frameworks: "FrameworksFile") -> None:
    """[R1]-[R5] — voir l'en-tête du module."""
    archetypes_fw = set(frameworks.archetypes)
    archetypes_ref = set(ref.famille_par_archetype)
    if archetypes_fw != archetypes_ref:
        raise ReferentielRefuse(
            f"[R1] `famille_par_archetype` couvre {sorted(archetypes_ref)}, `frameworks.yaml` déclare "
            f"les archétypes {sorted(archetypes_fw)} — chaque archétype a une famille, et "
            "`famille_par_archetype` n'en nomme pas d'autre")
    for patron in ref.patrons:
        if patron not in archetypes_fw:
            raise ReferentielRefuse(
                f"[R1] le patron `{patron}` n'est pas un archétype de `frameworks.yaml` "
                f"({sorted(archetypes_fw)})")

    questions_connues = {q.id for f in frameworks.frameworks for q in f.questions}
    for v in ref.variables:
        for qid in v.questions_sources:
            if qid not in questions_connues:
                raise ReferentielRefuse(
                    f"[R2] `{v.id}` cite la question source `{qid}`, absente de `frameworks.yaml`")

    from app.knowledge.socle_comptes import charger_gabarit
    lignes_gabarit = set(charger_gabarit().lignes)
    for nom_famille, famille in ref.familles_de_comptes.items():
        if famille.gabarit is None:
            continue
        for ligne in famille.lignes_du_business_plan:
            if ligne not in lignes_gabarit:
                raise ReferentielRefuse(
                    f"[R3] la famille `{nom_famille}` cite la ligne `{ligne}`, absente du gabarit du "
                    "socle des comptes")

    noms_controles = set(CONTROLES)
    if set(ref.controles) != noms_controles:
        raise ReferentielRefuse(
            f"[R4] `controles` du référentiel {sorted(ref.controles)} ne correspond pas exactement aux "
            f"fonctions déclarées dans `CONTROLES` {sorted(noms_controles)}")

    questions_par_id = {q.id: q for f in frameworks.frameworks for q in f.questions}
    for v in ref.variables:
        if "reponse_reprise" in v.origines_admises:
            porte_un_encadre = any(
                questions_par_id[qid].chiffres_cles for qid in v.questions_sources if qid in questions_par_id)
            if not porte_un_encadre:
                raise ReferentielRefuse(
                    f"[R5] `{v.id}` admet l'origine `reponse_reprise`, mais aucune de ses questions "
                    f"sources {v.questions_sources} ne déclare d'encadré de chiffres clés")

    # [R6] (lot M3, §2.3) — `somme_vers_ligne`, s'il est présent, est une ligne de
    # `lignes_du_business_plan` de CHAQUE famille de la fiche qui a un gabarit (une famille sans
    # gabarit, bancaire 1.0.0, n'a pas de lignes à viser : elle est ignorée ici, pas refusée).
    for v in ref.variables:
        if v.somme_vers_ligne is None:
            continue
        for nom_famille in v.familles:
            famille = ref.familles_de_comptes.get(nom_famille)
            if famille is None or famille.gabarit is None:
                continue
            if v.somme_vers_ligne not in famille.lignes_du_business_plan:
                raise ReferentielRefuse(
                    f"[R6] `{v.id}`.somme_vers_ligne = `{v.somme_vers_ligne}` n'est pas une ligne du "
                    f"business plan de la famille `{nom_famille}` ({famille.lignes_du_business_plan})")

    # [R7] (plan « découpage » B4g, étape 1) — chaque axe de `axes_du_premier_niveau` est un axe que le
    # fonds relève dans la ventilation publiée (`ventilation_publiee.yaml`, détenteur unique des axes).
    from app.knowledge.ventilation import charger_referentiel as charger_referentiel_ventilation
    axes_releves = {a.id for a in charger_referentiel_ventilation().axes}
    inconnus = [a for a in ref.axes_du_premier_niveau if a not in axes_releves]
    if inconnus:
        raise ReferentielRefuse(
            f"[R7] `axes_du_premier_niveau` cite {inconnus}, absent(s) des axes relevés de la ventilation "
            f"publiée {sorted(axes_releves)}")


@lru_cache(maxsize=1)
def load_referentiel(chemin: Optional[str] = None) -> ReferentielModele:
    """Charge et VALIDE le référentiel du classeur. Lève plutôt que de rendre un référentiel
    partiel — un référentiel à demi chargé laisserait l'architecte composer sur des fiches
    manquantes sans que rien ne le dise."""
    p = Path(chemin) if chemin else MODELE_ENTREPRISE_YAML
    if not p.exists():
        raise ReferentielRefuse(f"référentiel introuvable : {p}")
    brut = yaml.safe_load(p.read_text(encoding="utf-8"))
    try:
        ref = ReferentielModele.model_validate(brut)
    except ValidationError as exc:
        raise ReferentielRefuse(f"référentiel invalide ({p}) : {exc}") from exc
    from app.agents.v2.frameworks import load_frameworks
    _valider_pont_referentiel(ref, load_frameworks())
    return ref


def variables_de_la_famille(ref: ReferentielModele, famille: str) -> list[FicheVariable]:
    """Les fiches qui ont un sens dans cette famille — ce que l'architecte (M3) recevra."""
    return [v for v in ref.variables if famille in v.familles]


def questions_sources_applicables(ref: ReferentielModele, frameworks: "FrameworksFile",
                                  archetype: str) -> list[str]:
    """L'union des questions sources des variables de la famille de l'archétype, MOINS les
    questions `sans_objet` pour cet archétype — l'entrée de la porte de l'architecte (M3)."""
    famille = ref.famille_par_archetype[archetype]
    questions: set[str] = set()
    for v in ref.variables:
        if famille in v.familles:
            questions |= set(v.questions_sources)
    sans_objet = {
        q.id for f in frameworks.frameworks for q in f.questions
        if archetype in q.variables_par_archetype and q.variables_par_archetype[archetype].mode == "sans_objet"
    }
    return sorted(questions - sans_objet)


def _fiche_ou_propre(arch: Architecture, ref: ReferentielModele, variable_id: str) -> Optional[FicheVariable]:
    par_id = {v.id: v for v in ref.variables}
    par_propre = {v.id: v for v in arch.variables_propres}
    return par_id.get(variable_id) or par_propre.get(variable_id)


def valider_pont_architecture(arch: Architecture, ref: ReferentielModele,
                              periodes_projetees: Optional[tuple[str, ...]] = None) -> None:
    """[P1]-[P5] — voir l'en-tête du module. [P6] délibérément absent (TODO M5).

    `periodes_projetees` (lot M3 ter, §5) : les périodes PROJETÉES du classeur de
    CE titre, pour que le message de renvoi [P4] les NOMME plutôt que de dire seulement « refusé » —
    une valeur reprise d'un encadré (chiffre unique) s'applique à CHAQUE exercice projeté, et c'est
    cette liste que le modèle doit écrire. Optionnel : les appelants qui n'ont pas la matière sous
    la main (checks, `registre.py`) gardent le message sans la liste, jamais une erreur."""
    famille_attendue = ref.famille_par_archetype.get(arch.archetype)
    if famille_attendue is None:
        raise ArchitectureRefusee(
            f"[P1] l'archétype `{arch.archetype}` est absent de `famille_par_archetype` du référentiel")
    if arch.famille != famille_attendue:
        raise ArchitectureRefusee(
            f"[P1] l'architecture est en famille `{arch.famille}`, l'archétype `{arch.archetype}` vise "
            f"`{famille_attendue}`")
    famille = ref.familles_de_comptes[arch.famille]
    if famille.gabarit is None:
        raise ArchitectureRefusee(f"[P1] {famille.motif_absence}")
    if arch.version_referentiel != ref.version:
        raise ArchitectureRefusee(
            f"[P1] l'architecture cite le référentiel `{arch.version_referentiel}`, le référentiel "
            f"chargé est en `{ref.version}`")

    # [R7] (lot M3 bis, cause ④, §5) — toute VARIABLE PROPRE a une unité de la table `unites` du
    # référentiel (le catalogue, lui, est déjà vérifié à son propre chargement, #37 : un contrat
    # valide un objet, jamais la cohérence entre deux — l'architecture et le référentiel SONT deux
    # objets, donc ici, au pont).
    for vp in arch.variables_propres:
        if vp.unite not in ref.unites:
            raise ArchitectureRefusee(
                f"[R7] la variable propre `{vp.id}` déclare l'unité `{vp.unite}`, absente de la "
                f"table `unites` du référentiel ({sorted(ref.unites)})")

    par_bloc = {b.id: b for b in arch.blocs}
    for bloc in arch.blocs:
        for vid in bloc.variables:
            fiche = _fiche_ou_propre(arch, ref, vid)
            if fiche is None:
                raise ArchitectureRefusee(
                    f"[P2] le bloc `{bloc.id}` retient `{vid}`, ni fiche du catalogue ni variable propre "
                    "déclarée par cette architecture")
            est_fiche_catalogue = vid in {v.id for v in ref.variables}
            est_variable_propre = vid in {v.id for v in arch.variables_propres}
            if est_fiche_catalogue and est_variable_propre:
                raise ArchitectureRefusee(
                    f"[P2] `{vid}` est déclarée à la fois fiche du catalogue et variable propre")
            if est_fiche_catalogue and arch.famille not in fiche.familles:
                raise ArchitectureRefusee(
                    f"[P2] la fiche `{vid}` n'a pas de sens dans la famille `{arch.famille}` "
                    f"(familles : {fiche.familles})")

    for p in arch.passage_a_l_agrege:
        if p.ligne not in famille.lignes_du_business_plan:
            raise ArchitectureRefusee(
                f"[P3] `{p.ligne}` n'est pas une ligne du business plan de la famille `{arch.famille}` "
                f"({famille.lignes_du_business_plan})")

    for c in arch.cellules_attendues:
        fiche = _fiche_ou_propre(arch, ref, c.variable)
        if fiche is None:
            raise ArchitectureRefusee(
                f"[P4] la cellule attendue `{c.variable}` n'est ni une fiche du catalogue ni une "
                "variable propre de cette architecture")
        if fiche.periode == "sans_periode":
            if c.periodes != ["sans_periode"]:
                raise ArchitectureRefusee(
                    f"[P4] `{c.variable}` est `sans_periode` (référentiel) : la cellule attendue doit "
                    f"porter `periodes == [\"sans_periode\"]`, reçu {c.periodes}")
        elif "sans_periode" in c.periodes:
            attendu = (f" ; périodes attendues : {list(periodes_projetees)}" if periodes_projetees else "")
            raise ArchitectureRefusee(
                f"[P4] `{c.variable}` porte une période (`{fiche.periode}`, référentiel) : "
                "`sans_periode` n'est pas admis pour ses cellules — une valeur reprise d'un encadré "
                f"(chiffre unique) s'applique à CHAQUE exercice projeté{attendu}")
        if isinstance(c.auteur, AuteurQuestion) and c.auteur.question_id not in fiche.questions_sources:
            raise ArchitectureRefusee(
                f"[P5] la cellule de `{c.variable}` est attribuée à la question `{c.auteur.question_id}`, "
                f"qui n'est pas une question source de cette variable ({fiche.questions_sources}) — ce "
                "doit être une demande ciblée")


def valider_cellule(cellule: Cellule, ref: ReferentielModele, arch: Architecture,
                    ctx: Optional[ContexteControle] = None) -> None:
    """[C1]-[C5] — voir l'en-tête du module."""
    attendues = {(c.bloc, c.variable, p) for c in arch.cellules_attendues for p in c.periodes}
    if (cellule.bloc, cellule.variable, cellule.periode) not in attendues:
        raise CelluleRefusee(
            f"[C1] aucune cellule n'est attendue pour (`{cellule.bloc}`, `{cellule.variable}`, "
            f"`{cellule.periode}`)")
    fiche = _fiche_ou_propre(arch, ref, cellule.variable)
    if fiche is None:
        raise CelluleRefusee(
            f"[C1] `{cellule.variable}` n'est ni une fiche du catalogue ni une variable propre de "
            "cette architecture")
    if cellule.origine.type not in fiche.origines_admises:
        raise CelluleRefusee(
            f"[C2] origine `{cellule.origine.type}` non admise pour `{cellule.variable}` (admises : "
            f"{fiche.origines_admises})")
    if cellule.unite != fiche.unite:
        raise CelluleRefusee(
            f"[C3] `{cellule.variable}` attend l'unité `{fiche.unite}`, reçu `{cellule.unite}`")
    if fiche.controle is not None:
        motif = CONTROLES[fiche.controle](cellule, ctx or ContexteControle())
        if motif is not None:
            raise CelluleRefusee(f"[C4] {motif}")
    if isinstance(cellule.origine, OrigineCalcul):
        bloc = next((b for b in arch.blocs if b.id == cellule.bloc), None)
        if bloc is None:
            raise CelluleRefusee(f"[C5] le bloc `{cellule.bloc}` est absent de l'architecture")
        hors = sorted(set(noms_de_la_formule(cellule.origine.formule)) - set(bloc.variables))
        if hors:
            raise CelluleRefusee(
                f"[C5] la formule de `{cellule.variable}` référence {hors}, hors des variables retenues "
                f"par le bloc `{cellule.bloc}` ({bloc.variables})")
