"""Vérification du CLASSEUR DE L'ENTREPRISE — référentiel, contrat, pont, contrôles, scénarios
(lot M1, roadmap 09 §9/§12, conventions #97/#98/#140). Sans réseau, sans modèle, sans base.

  • §1 LE RÉFÉRENTIEL RÉEL se charge, contrat + pont verts ; 21 fiches, 3 patrons.
  • §2 LE CONTRAT du référentiel (`ReferentielModele`, `FicheVariable`, `FamilleDeComptes`) refuse
       chaque incohérence interne, avec son motif.
  • §3 LE CONTRAT de l'architecture (`Architecture`, `Bloc`, `PassageAgrege`, `CelluleAttendue`)
       et des objets du classeur (`Fourchette`, `Scenario`, `Deplacement`, `OrigineCalcul`).
  • §4 LE PONT [R1]-[R5] (référentiel ↔ `frameworks.yaml`/socle), [P1]-[P5] (architecture ↔
       référentiel), [C1]-[C5] (cellule ↔ architecture) — objet valide accepté, objet muté refusé
       AVEC LE BON CODE.
  • §5 LES FIXTURES RÉELLES (NVDA, RVMD, JPM — copiées du réel) : NVDA et RVMD passent le pont,
       JPM est refusé en [P1] (gabarit bancaire absent).
  • §6 `questions_sources_applicables` : rentable et pré-revenus non vides, et aucune question
       `sans_objet` du référentiel pour pré-revenus n'y figure (lue dans `frameworks.yaml`, jamais
       écrite en dur).
  • §7 LES CONTRÔLES (§4 de la spec) : chacun des six, et `part_calculee` contre l'exercice publié.
  • §8 `appliquer_scenario` : central, borne basse sur la plage, valeur dite, déplacement sans
       fourchette, déplacement qui ne touche rien, branche à probabilité.
  • §9 RÉPLICABILITÉ : le code et le référentiel livrés ne nomment ni ticker ni segment des fixtures.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402

import yaml  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.contracts.modele_entreprise_schema import (  # noqa: E402
    ARCHITECTURE_SCHEMA_VERSION, Architecture, Cellule, Deplacement, Fourchette, OrigineCalcul,
    ReferentielModele, Scenario, SCENARIO_CENTRAL,
)
from app.modele_entreprise.controles import CONTROLES, ContexteControle  # noqa: E402
from app.modele_entreprise.referentiel import (  # noqa: E402
    ArchitectureRefusee, CelluleRefusee, ReferentielRefuse, load_referentiel,
    questions_sources_applicables, valider_cellule, valider_pont_architecture,
)
from app.modele_entreprise.scenarios import ScenarioInapplicable, appliquer_scenario  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "app" / "frameworks" / "modele_entreprise.yaml"
MODULE_DIR = ROOT / "app" / "modele_entreprise"
SCHEMA_PATH = ROOT / "app" / "contracts" / "modele_entreprise_schema.py"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "modele_entreprise"

b = Bilan()
REF_BRUT = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def modifie(base: dict, **champs) -> dict:
    m = copy.deepcopy(base)
    m.update(champs)
    return m


def refus_referentiel(payload: dict) -> str:
    try:
        ReferentielModele.model_validate(payload)
    except ValidationError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001 — une panne du validateur est un FAIL nommé, pas une mort
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


def refus_objet(cls, payload: dict) -> str:
    try:
        cls.model_validate(payload)
    except ValidationError as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


# ── §1 Le référentiel réel ──────────────────────────────────────────────────────────────────────
print("§1 référentiel réel")
ref = load_referentiel()
b.check(len(ref.variables) == 22, f"le catalogue porte 22 fiches (obtenu {len(ref.variables)})")
b.check(set(ref.patrons) == {"rentable", "pre_revenus", "financiere"},
        f"3 patrons, un par archétype (obtenu {sorted(ref.patrons)})")
b.check(set(ref.famille_par_archetype) == {"rentable", "pre_revenus", "financiere"},
        "chaque archétype déclare une famille")
b.check(ref.familles_de_comptes["bancaire"].gabarit is None
        and ref.familles_de_comptes["bancaire"].motif_absence is not None,
        "la famille bancaire n'a pas encore de gabarit, et le dit")

# ── §2 Le contrat — le référentiel ──────────────────────────────────────────────────────────────
print("§2 contrat — référentiel")

v_taille = next(v for v in REF_BRUT["variables"] if v["id"] == "taille_du_marche")


def variable_test(**champs) -> dict:
    base = {**v_taille, "id": "variable_de_test", "questions_sources": ["me_5"]}
    base.update(champs)
    return base


cas_fiche_variable = [
    ("origines_admises en double", variable_test(origines_admises=["piece", "piece"]), "doublon"),
    ("questions_sources en double", variable_test(questions_sources=["me_5", "me_5"]), "doublon"),
    ("familles en double", variable_test(familles=["industrielle", "industrielle"]), "doublon"),
    ("methode_de_fourchette en double",
     variable_test(methode_de_fourchette=["fourchette_publiee", "fourchette_publiee"]), "doublon"),
    ("part_calculee sans origines == [calcul]",
     variable_test(controle="part_calculee", origines_admises=["piece"]), "part_calculee"),
    ("id avec double tiret bas", variable_test(id="bloc__variable"), "double tiret bas"),
]
b.require(cas_fiche_variable, 6, "cas de refus de `FicheVariable`")
for label, variable, motif in cas_fiche_variable:
    m = refus_referentiel(modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable]))
    b.check(motif in m, f"FicheVariable — « {label} » : motif attendu « {motif} », obtenu « {m[:200]} »")

cas_famille = [
    ("gabarit ET motif_absence tous deux présents",
     {"gabarit": "x.yaml", "motif_absence": "Motif donné alors qu'un gabarit existe déjà pour cette famille.",
      "lignes_du_business_plan": ["chiffre_affaires"]}, "jamais un mélange"),
    ("gabarit absent mais lignes non vides",
     {"gabarit": None, "motif_absence": None, "lignes_du_business_plan": ["chiffre_affaires"]}, "jamais un mélange"),
    ("gabarit présent mais lignes vides",
     {"gabarit": "x.yaml", "motif_absence": None, "lignes_du_business_plan": []}, "jamais un mélange"),
]
b.require(cas_famille, 3, "cas de refus de `FamilleDeComptes`")
for label, famille, motif in cas_famille:
    m = refus_referentiel(modifie(REF_BRUT, familles_de_comptes={**REF_BRUT["familles_de_comptes"], "test_famille": famille}))
    b.check(motif in m, f"FamilleDeComptes — « {label} » : motif attendu « {motif} », obtenu « {m[:200]} »")

cas_referentiel = [
    ("deux variables du même id",
     modifie(REF_BRUT, variables=REF_BRUT["variables"] + [REF_BRUT["variables"][0]]), "le référentiel"),
    ("famille non déclarée sur une fiche",
     modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(familles=["famille_inconnue"])]),
     "absente de `familles_de_comptes`"),
    ("contrôle non déclaré sur une fiche",
     modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(controle="controle_inconnu")]),
     "absent de `controles`"),
    ("méthode non déclarée sur une fiche",
     modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(methode_de_fourchette=["methode_inconnue"])]),
     "méthode `methode_inconnue`, absente"),
    ("famille_par_archetype vise une famille non déclarée",
     modifie(REF_BRUT, famille_par_archetype={**REF_BRUT["famille_par_archetype"], "rentable": "famille_fantome"}),
     "famille `famille_fantome`, non déclarée"),
    ("un patron ne correspond à aucun archétype",
     modifie(REF_BRUT, patrons={**REF_BRUT["patrons"], "archetype_inconnu": {"blocs": [{"role": "commun", "variables": ["couts_communs"]}]}}),
     "ne correspond à aucun archétype"),
    ("un patron retient une variable absente du catalogue",
     modifie(REF_BRUT, patrons={**REF_BRUT["patrons"], "rentable": {"blocs": [{"role": "commun", "variables": ["variable_absente_du_catalogue"]}]}}),
     "absente du catalogue"),
    ("un patron retient une variable sans sens dans sa famille",
     modifie(REF_BRUT, patrons={**REF_BRUT["patrons"], "financiere": {"blocs": [{"role": "metier", "variables": ["volume"]}]}}),
     "n'a pas de sens dans la famille"),
]
b.require(cas_referentiel, 8, "cas de refus de `ReferentielModele` (cohérence interne)")
for label, payload, motif in cas_referentiel:
    m = refus_referentiel(payload)
    b.check(motif in m, f"ReferentielModele — « {label} » : motif attendu « {motif} », obtenu « {m[:220]} »")

b.check(refus_referentiel(REF_BRUT) == "PAS DE REFUS", "le référentiel réel, non muté, est conforme au contrat")

# ── §3 Le contrat — architecture, cellule, fourchette, scénario, déplacement ────────────────────
print("§3 contrat — architecture et objets du classeur")

ARCH = {
    "schema_version": ARCHITECTURE_SCHEMA_VERSION, "ticker_id": "ticker_de_test", "version": 1,
    "archetype": "rentable", "famille": "industrielle", "version_referentiel": "1.2.0",
    "blocs": [
        {"id": "bloc_principal", "libelle": "Bloc principal", "role": "activite",
         "statut": "metier_actuel", "origine": "interne", "maille": "publie",
         "rattachement": {"type": "publie", "axe": "axe:Test", "membres": ["test:Membre"]},
         "variables": ["chiffre_affaires_du_bloc"],
         "motif": "Bloc principal publié de test, motif de longueur suffisante pour le contrat."},
        {"id": "bloc_commun", "libelle": "Bloc commun", "role": "commun",
         "statut": "metier_actuel", "origine": "interne", "maille": "estime",
         "rattachement": {"type": "agrege", "ligne": "autres_charges_exploitation"},
         "variables": ["couts_communs"],
         "motif": "Bloc commun estimé de test, motif de longueur suffisante pour le contrat.",
         "pieces": [1]},
    ],
    "variables_propres": [],
    "passage_a_l_agrege": [
        {"ligne": "chiffre_affaires", "formule": "bloc_principal__chiffre_affaires_du_bloc"},
    ],
    "cellules_attendues": [
        {"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2025"],
         "auteur": {"type": "question", "question_id": "me_2"}},
    ],
}


def arch_test(**champs) -> dict:
    return modifie(ARCH, **champs)


b.check(refus_objet(Architecture, ARCH) == "PAS DE REFUS", "l'architecture générique de test est conforme au contrat")

cas_architecture = [
    ("deux blocs du même id",
     arch_test(blocs=ARCH["blocs"] + [ARCH["blocs"][0]]), "ids de bloc"),
    ("un bloc se rattache à lui-même",
     arch_test(blocs=[{**ARCH["blocs"][0], "maille": "estime", "pieces": [1],
                       "rattachement": {"type": "parent", "bloc": "bloc_principal"}}, ARCH["blocs"][1]]),
     "se rattache à lui-même"),
    ("un bloc parent vise un bloc non déclaré",
     arch_test(blocs=[{**ARCH["blocs"][0], "maille": "estime", "pieces": [1],
                       "rattachement": {"type": "parent", "bloc": "bloc_fantome"}}, ARCH["blocs"][1]]),
     "non déclaré"),
    ("cycle de rattachement parent",
     arch_test(blocs=[
         {"id": "bloc_a", "libelle": "A", "role": "activite", "statut": "metier_actuel",
          "origine": "interne", "maille": "estime",
          "rattachement": {"type": "parent", "bloc": "bloc_b"}, "variables": ["chiffre_affaires_du_bloc"],
          "motif": "Bloc A de test, motif de longueur suffisante pour satisfaire le contrat.", "pieces": [1]},
         {"id": "bloc_b", "libelle": "B", "role": "activite", "statut": "metier_actuel",
          "origine": "interne", "maille": "estime",
          "rattachement": {"type": "parent", "bloc": "bloc_a"}, "variables": ["chiffre_affaires_du_bloc"],
          "motif": "Bloc B de test, motif de longueur suffisante pour satisfaire le contrat.", "pieces": [1]},
     ], passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_a__chiffre_affaires_du_bloc"}],
        cellules_attendues=[{"bloc": "bloc_a", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2025"],
                             "auteur": {"type": "question", "question_id": "me_2"}}]),
     "cycle de rattachement"),
    ("deux variables propres du même id",
     arch_test(variables_propres=[
         {**v_taille, "id": "propre_test", "questions_sources": [], "motif": "Variable propre déclarée deux fois pour ce test."},
         {**v_taille, "id": "propre_test", "questions_sources": [], "motif": "Deuxième déclaration de la même variable propre."},
     ]), "variables propres"),
    ("deux lignes de passage pour la même ligne",
     arch_test(passage_a_l_agrege=ARCH["passage_a_l_agrege"] + ARCH["passage_a_l_agrege"]), "lignes de passage"),
    ("formule de passage sans séparateur bloc__variable",
     arch_test(passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "chiffre_affaires_du_bloc"}]),
     "pas de la forme"),
    ("formule de passage vise un bloc non déclaré",
     arch_test(passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_fantome__chiffre_affaires_du_bloc"}]),
     "non déclaré"),
    ("formule de passage vise une variable que le bloc ne retient pas",
     arch_test(passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_principal__taille_du_marche"}]),
     "ne retient pas"),
    ("deux cellules attendues pour la même adresse",
     arch_test(cellules_attendues=ARCH["cellules_attendues"] + ARCH["cellules_attendues"]),
     "un seul auteur par cellule"),
    ("cellule attendue vise un bloc non déclaré",
     arch_test(cellules_attendues=[{"bloc": "bloc_fantome", "variable": "chiffre_affaires_du_bloc",
                                    "periodes": ["FY2025"], "auteur": {"type": "question", "question_id": "me_2"}}]),
     "non déclaré"),
    ("cellule attendue vise une variable que le bloc ne retient pas",
     arch_test(cellules_attendues=[{"bloc": "bloc_principal", "variable": "taille_du_marche",
                                    "periodes": ["FY2025"], "auteur": {"type": "question", "question_id": "me_5"}}]),
     "ne retient pas"),
]
b.require(cas_architecture, 12, "cas de refus de `Architecture` (cohérence interne)")
for label, payload, motif in cas_architecture:
    m = refus_objet(Architecture, payload)
    b.check(motif in m, f"Architecture — « {label} » : motif attendu « {motif} », obtenu « {m[:220]} »")

cas_bloc = [
    ("maille publie avec un rattachement parent",
     {**ARCH["blocs"][0], "rattachement": {"type": "parent", "bloc": "bloc_commun"}}, "incohérente"),
    ("maille estime avec un rattachement publié",
     {**ARCH["blocs"][1], "maille": "estime",
      "rattachement": {"type": "publie", "axe": "a", "membres": ["m"]}},
     "incohérente"),
]
for label, bloc, motif in cas_bloc:
    m = refus_objet(Architecture, arch_test(blocs=[bloc, ARCH["blocs"][1]]))
    b.check(motif in m, f"Bloc — « {label} » : motif attendu « {motif} », obtenu « {m[:200]} »")

# ── 1.2.0 (lot M3 bis, cause ⑤, §6) : `Bloc.origine`, `Bloc.jalon`, [S12] ───────────────────────
print("§3ter contrat — 1.2.0 origine/jalon ([S12])")
JALON_TEST = {"franchi": "preuve de concept de laboratoire", "franchi_le": "2026-03-01",
             "prochain": "autorisation d'essai clinique", "attendu_vers": "2027-06-01"}
bloc_programme = {**ARCH["blocs"][0], "statut": "en_developpement",
                  "origine": "interne", "jalon": JALON_TEST, "pieces": [1],
                  "motif": "Bloc programme de test, en développement, motif de longueur suffisante."}
m = refus_objet(Architecture, arch_test(blocs=[
    {k: v for k, v in bloc_programme.items() if k != "jalon"}, ARCH["blocs"][1]]))
b.check("si et seulement si" in m.lower(),
        f"Bloc 1.2.0 — `en_developpement` SANS jalon est refusé (obtenu « {m[:220]} »)")
m = refus_objet(Architecture, arch_test(blocs=[
    {**bloc_programme, "statut": "metier_actuel", "pieces": [1]}, ARCH["blocs"][1]]))
b.check("si et seulement si" in m.lower(),
        f"Bloc 1.2.0 — `metier_actuel` AVEC jalon est refusé (obtenu « {m[:220]} »)")
b.check(refus_objet(Architecture, arch_test(blocs=[bloc_programme, ARCH["blocs"][1]])) == "PAS DE REFUS",
        "Bloc 1.2.0 — `en_developpement` avec jalon, licence/interne : tient")
m = refus_objet(Architecture, arch_test(blocs=[
    {**bloc_programme, "origine": "acquisition"}, ARCH["blocs"][1]]))
b.check("[S12]" in m, f"[S12] — acquisition `en_developpement` refusée (obtenu « {m[:220]} »)")
b.check(refus_objet(Architecture, arch_test(blocs=[
    {**ARCH["blocs"][0], "origine": "acquisition", "statut": "extension_annoncee", "pieces": [1],
     "motif": "Acquisition annoncée de test, non conclue, motif de longueur suffisante."},
    ARCH["blocs"][1]])) == "PAS DE REFUS",
    "[S12] — acquisition `extension_annoncee` (non conclue) tient")
b.check(refus_objet(Architecture, arch_test(blocs=[
    {**bloc_programme, "origine": "licence"}, ARCH["blocs"][1]])) == "PAS DE REFUS",
    "[S12] — licence `en_developpement` tient (origine ≠ acquisition, tout statut admis)")

# ── 1.1.0 (lot M3, §2.2) : `Bloc.motif`/`Bloc.pieces` ───────────────────────────────────────────
print("§3bis contrat — 1.1.0 motif/pieces")
m = refus_objet(Architecture, arch_test(blocs=[
    {k: v for k, v in ARCH["blocs"][1].items() if k != "pieces"}, ARCH["blocs"][0]]))
b.check("au moins une pièce" in m,
        f"Bloc 1.1.0 — un bloc estimé SANS pièce est refusé (obtenu « {m[:220]} »)")
bloc_annonce_sans_pieces = {**ARCH["blocs"][0], "statut": "extension_annoncee",
                           "motif": "Bloc annoncé de test, sans pièce, motif de longueur suffisante."}
m = refus_objet(Architecture, arch_test(blocs=[bloc_annonce_sans_pieces, ARCH["blocs"][1]]))
b.check("au moins une pièce" in m,
        f"Bloc 1.1.0 — un bloc `extension_annoncee` SANS pièce est refusé (obtenu « {m[:220]} »)")
m = refus_objet(Architecture, arch_test(
    blocs=[{k: v for k, v in ARCH["blocs"][0].items() if k != "motif"}, ARCH["blocs"][1]]))
b.check("motif" in m.lower() and ("missing" in m.lower() or "field required" in m.lower()),
        f"Bloc 1.1.0 — un bloc SANS `motif` est refusé (obtenu « {m[:220]} »)")
b.check(refus_objet(Architecture, arch_test()) == "PAS DE REFUS",
        "Bloc 1.1.0 — re-contrôle : l'architecture de test (motif+pieces en place) tient")

OC_VALIDE = {"type": "calcul", "formule": "chiffre_affaires_du_bloc / taille_du_marche"}
b.check(refus_objet(Architecture, arch_test()) == "PAS DE REFUS", "re-contrôle : l'architecture de test tient")
m = refus_objet(Fourchette, {
    "bloc": "bloc_principal", "variable": "taille_du_marche", "periode_debut": "FY2025", "periode_fin": "FY2024",
    "bas": 10.0, "haut": 5.0, "methode": "dispersion_observee",
    "origine_bas": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
    "origine_haut": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]}})
b.check("bas" in m and ">" in m, f"Fourchette — bas > haut refusé (obtenu « {m[:160]} »)")
m = refus_objet(Fourchette, {
    "bloc": "bloc_principal", "variable": "taille_du_marche", "periode_debut": "sans_periode", "periode_fin": "FY2025",
    "bas": 5.0, "haut": 10.0, "methode": "dispersion_observee",
    "origine_bas": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
    "origine_haut": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]}})
b.check("même forme" in m, f"Fourchette — periode_debut/fin de formes différentes refusé (obtenu « {m[:160]} »)")
m = refus_objet(Fourchette, {
    "bloc": "bloc_principal", "variable": "taille_du_marche", "periode_debut": "FY2026", "periode_fin": "FY2024",
    "bas": 5.0, "haut": 10.0, "methode": "dispersion_observee",
    "origine_bas": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
    "origine_haut": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]}})
b.check("postérieure" in m, f"Fourchette — periode_debut postérieure à periode_fin refusé (obtenu « {m[:160]} »)")

DEP_BASE = {"bloc": "bloc_principal", "variable": "taille_du_marche", "periode_debut": "FY2025",
            "periode_fin": "FY2025", "cible": "borne_basse", "motif": "Risque de test documenté pour la fourchette."}
m = refus_objet(Deplacement, {**DEP_BASE, "valeur_dite": 12.0})
b.check("si et seulement si" in m.lower(), f"Deplacement — valeur_dite hors cible `valeur_dite` refusé (obtenu « {m[:160]} »)")
m = refus_objet(Deplacement, {**DEP_BASE, "cible": "valeur_dite", "valeur_dite": 12.0, "source_entry_refs": []})
b.check("au moins une pièce" in m, f"Deplacement — valeur_dite sans pièce refusé (obtenu « {m[:160]} »)")
b.check(refus_objet(Deplacement, DEP_BASE) == "PAS DE REFUS", "un déplacement de borne, sans pièce, est conforme")

SCE_BASE = {"nom": "scenario_test", "recit": "Récit du scénario de test, assez long pour le contrat.",
            "nature": "nomme", "deplacements": [DEP_BASE]}
cas_scenario = [
    ("central avec un déplacement", {**SCE_BASE, "nature": "central"}, "ne déplace rien"),
    ("central avec une probabilité", {**SCE_BASE, "nature": "central", "deplacements": [], "probabilite": 0.5},
     "pas de probabilité"),
    ("nomme sans déplacement", {**SCE_BASE, "deplacements": []}, "au moins un déplacement"),
    ("nomme avec une probabilité", {**SCE_BASE, "probabilite": 0.5}, "ne porte pas de probabilité"),
    ("branche sans déplacement", {**SCE_BASE, "nature": "branche", "deplacements": [], "probabilite": 0.5},
     "au moins un déplacement"),
    ("branche sans probabilité", {**SCE_BASE, "nature": "branche"}, "sa probabilité"),
]
b.require(cas_scenario, 6, "cas de refus de `Scenario`")
for label, payload, motif in cas_scenario:
    m = refus_objet(Scenario, payload)
    b.check(motif in m, f"Scenario — « {label} » : motif attendu « {motif} », obtenu « {m[:200]} »")

DEP2 = {**DEP_BASE, "periode_debut": "FY2025", "periode_fin": "FY2026"}
m = refus_objet(Scenario, {**SCE_BASE, "deplacements": [DEP_BASE, DEP2]})
b.check("se chevauchent" in m, f"Scenario — deux déplacements qui se chevauchent refusé (obtenu « {m[:200]} »)")
b.check(SCENARIO_CENTRAL.nature == "central" and SCENARIO_CENTRAL.deplacements == [],
        "SCENARIO_CENTRAL est la constante sans déplacement")

m = refus_objet(Architecture, arch_test())  # no-op sanity
b.check(m == "PAS DE REFUS", "re-contrôle final : l'architecture générique tient toujours")

m = refus_objet(OrigineCalcul, {"type": "calcul", "formule": "pour chaque exercice"})
b.check("grammaire fermée" in m, f"OrigineCalcul — formule hors grammaire refusée (obtenu « {m[:200]} »)")
b.check(refus_objet(OrigineCalcul, OC_VALIDE) == "PAS DE REFUS", "OrigineCalcul — formule valide acceptée")

m = refus_objet(Architecture, arch_test(passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "pour chaque exercice"}]))
b.check("grammaire fermée" in m, f"PassageAgrege — formule hors grammaire refusée (obtenu « {m[:200]} »)")

# ── §4 Le pont ───────────────────────────────────────────────────────────────────────────────────
print("§4 pont")

from app.modele_entreprise.referentiel import _valider_pont_referentiel  # noqa: E402


def refus_pont_referentiel(payload: dict) -> str:
    try:
        r = ReferentielModele.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        _valider_pont_referentiel(r, load_frameworks_pour_pont())
    except ReferentielRefuse as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


def load_frameworks_pour_pont():
    from app.agents.v2.frameworks import load_frameworks
    return load_frameworks()


b.check(refus_pont_referentiel(REF_BRUT) == "PAS DE REFUS", "le référentiel réel passe le pont [R1]-[R5]")

sans_pre_rev = modifie(REF_BRUT,
    famille_par_archetype={"rentable": "industrielle"},
    patrons={"rentable": REF_BRUT["patrons"]["rentable"]})
m = refus_pont_referentiel(sans_pre_rev)
b.check(m.startswith("[R1]"), f"pont référentiel — [R1] archétypes incomplets refusé (obtenu « {m[:200]} »)")

m = refus_pont_referentiel(modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(questions_sources=["qx_999"])]))
b.check(m.startswith("[R2]") and "qx_999" in m, f"pont référentiel — [R2] question source inconnue refusée (obtenu « {m[:200]} »)")

industrielle_avec_ligne_fantome = {**REF_BRUT["familles_de_comptes"]["industrielle"],
                                   "lignes_du_business_plan": REF_BRUT["familles_de_comptes"]["industrielle"]["lignes_du_business_plan"] + ["ligne_fantome"]}
m = refus_pont_referentiel(modifie(REF_BRUT, familles_de_comptes={**REF_BRUT["familles_de_comptes"], "industrielle": industrielle_avec_ligne_fantome}))
b.check(m.startswith("[R3]") and "ligne_fantome" in m, f"pont référentiel — [R3] ligne absente du gabarit refusée (obtenu « {m[:200]} »)")

m = refus_pont_referentiel(modifie(REF_BRUT, controles=REF_BRUT["controles"] + ["controle_fantome"]))
b.check(m.startswith("[R4]"), f"pont référentiel — [R4] contrôle sans fonction refusé (obtenu « {m[:200]} »)")

variables_r5 = [v if v["id"] != "capital_par_point_de_croissance" else {**v, "questions_sources": ["mo_6"]}
                for v in REF_BRUT["variables"]]
m = refus_pont_referentiel(modifie(REF_BRUT, variables=variables_r5))
b.check(m.startswith("[R5]"), f"pont référentiel — [R5] reponse_reprise sans encadré refusé (obtenu « {m[:200]} »)")

m = refus_pont_referentiel(modifie(
    REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(somme_vers_ligne="ligne_fantome")]))
b.check(m.startswith("[R6]") and "ligne_fantome" in m,
        f"pont référentiel — [R6] somme_vers_ligne hors du business plan refusé (obtenu « {m[:220]} »)")
m = refus_pont_referentiel(modifie(
    REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(somme_vers_ligne="chiffre_affaires")]))
b.check(m == "PAS DE REFUS",
        f"pont référentiel — [R6] somme_vers_ligne valide (ligne du business plan) accepté (obtenu « {m[:200]} »)")

# [R7] (1.2.0, cause ④, §5) — toute fiche a une unité de la table `unites`.
m = refus_referentiel(modifie(REF_BRUT, variables=REF_BRUT["variables"] + [variable_test(unite="unite_fantome")]))
b.check("[R7]" in m and "unite_fantome" in m,
        f"[R7] — une fiche d'unité absente de la table `unites` est refusée (obtenu « {m[:220]} »)")
b.check(len(REF_BRUT["unites"]) == 8, f"la table `unites` porte 8 entrées (obtenu {len(REF_BRUT['unites'])})")

REF_TEST = ReferentielModele.model_validate(REF_BRUT)


def arch_valide() -> Architecture:
    return Architecture.model_validate(ARCH)


def pont_architecture(payload: dict) -> str:
    try:
        arch = Architecture.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        valider_pont_architecture(arch, REF_TEST)
    except ArchitectureRefusee as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


b.check(pont_architecture(ARCH) == "PAS DE REFUS", "l'architecture générique de test passe le pont réel")

cas_pont_architecture = [
    ("archétype absent du référentiel", arch_test(archetype="archetype_fantome"), "[P1]", "absent"),
    ("famille différente de celle de l'archétype", arch_test(famille="bancaire"), "[P1]", "vise"),
    ("famille bancaire, sans gabarit", arch_test(archetype="financiere", famille="bancaire"), "[P1]", "trompeur"),
    ("version_referentiel différente du référentiel chargé", arch_test(version_referentiel="9.9.9"), "[P1]", "cite le référentiel"),
    ("variable retenue ni fiche ni propre",
     arch_test(blocs=[{**ARCH["blocs"][0], "variables": ["variable_inconnue_du_catalogue"]}, ARCH["blocs"][1]],
                passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_principal__variable_inconnue_du_catalogue"}],
                cellules_attendues=[{"bloc": "bloc_principal", "variable": "variable_inconnue_du_catalogue",
                                    "periodes": ["FY2025"], "auteur": {"type": "demande_ciblee"}}]),
     "[P2]", "ni fiche du catalogue ni variable propre"),
    ("fiche sans sens dans la famille de l'architecture",
     arch_test(blocs=[{**ARCH["blocs"][0], "variables": ["encours"]}, ARCH["blocs"][1]],
                passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_principal__encours"}],
                cellules_attendues=[{"bloc": "bloc_principal", "variable": "encours", "periodes": ["FY2025"],
                                    "auteur": {"type": "demande_ciblee"}}]),
     "[P2]", "n'a pas de sens"),
    ("ligne de passage hors du business plan de la famille",
     arch_test(passage_a_l_agrege=[{"ligne": "encours", "formule": "bloc_principal__chiffre_affaires_du_bloc"}]),
     "[P3]", "n'est pas une ligne du business plan"),
    ("cellule sans_periode pour une variable à exercice",
     arch_test(cellules_attendues=[{"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc",
                                    "periodes": ["sans_periode"], "auteur": {"type": "question", "question_id": "me_2"}}]),
     "[P4]", "n'est pas admis"),
    ("cellule à exercice pour une variable sans_periode",
     arch_test(blocs=[{**ARCH["blocs"][0], "variables": ["annee_de_lancement"]}, ARCH["blocs"][1]],
                passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "bloc_principal__annee_de_lancement"}],
                cellules_attendues=[{"bloc": "bloc_principal", "variable": "annee_de_lancement",
                                    "periodes": ["FY2025"], "auteur": {"type": "question", "question_id": "me_5"}}]),
     "[P4]", "doit porter"),
    ("cellule attribuée à une question qui n'est pas source de la variable",
     arch_test(cellules_attendues=[{"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc",
                                    "periodes": ["FY2025"], "auteur": {"type": "question", "question_id": "qf_1"}}]),
     "[P5]", "n'est pas une question source"),
]
b.require(cas_pont_architecture, 10, "cas de refus du pont [P1]-[P5]")
for label, payload, code, fragment in cas_pont_architecture:
    m = pont_architecture(payload)
    b.check(m.startswith(code) and fragment in m,
            f"pont — « {label} » : refus {code} « {fragment} » attendu, obtenu « {m[:220]} »")

CELLULE_VALIDE = {"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc", "periode": "FY2025",
                  "valeur": 100.0, "unite": "M$", "origine": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
                  "auteur": {"type": "question", "question_id": "me_2", "answer_id": 1}}
CTX_PUBLIE = ContexteControle(dernier_exercice_publie="FY2025")


def pont_cellule(payload: dict, ctx=None) -> str:
    try:
        c = Cellule.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        valider_cellule(c, REF_TEST, arch_valide(), ctx)
    except CelluleRefusee as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return "PAS DE REFUS"


b.check(pont_cellule(CELLULE_VALIDE, CTX_PUBLIE) == "PAS DE REFUS", "la cellule générique de test passe le pont réel")

cas_pont_cellule = [
    ("cellule non attendue par l'architecture",
     {**CELLULE_VALIDE, "periode": "FY2024"}, "[C1]", "aucune cellule n'est attendue"),
    ("origine hors de origines_admises de la fiche",
     {**CELLULE_VALIDE, "origine": {"type": "jugement",
                                     "taux_de_base": {"classe_de_reference": "classe de test pour ce cas", "valeur": 1.0,
                                                      "source_entry_refs": [{"entry_id": 1}]},
                                     "ecart_justifie": "Écart justifié pour ce cas de test, assez long."}},
     "[C2]", "non admise"),
    ("unité différente de celle de la fiche",
     {**CELLULE_VALIDE, "unite": "€"}, "[C3]", "attend l'unité"),
]
b.require(cas_pont_cellule, 3, "cas de refus du pont [C1]-[C3]")
for label, payload, code, fragment in cas_pont_cellule:
    m = pont_cellule(payload, CTX_PUBLIE)
    b.check(m.startswith(code) and fragment in m,
            f"pont cellule — « {label} » : refus {code} « {fragment} » attendu, obtenu « {m[:220]} »")

# [C4] le contrôle de la fiche — ici `positif_ou_nul` sur `couts_communs`.
CELLULE_COMMUN = {"bloc": "bloc_commun", "variable": "couts_communs", "periode": "FY2025", "valeur": -5.0,
                  "unite": "M$", "origine": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
                  "auteur": {"type": "demande_ciblee", "demande_id": 1}}
arch_commun = Architecture.model_validate(arch_test(cellules_attendues=[
    {"bloc": "bloc_commun", "variable": "couts_communs", "periodes": ["FY2025"], "auteur": {"type": "demande_ciblee"}}]))


def pont_cellule_commun(payload: dict, ctx=None) -> str:
    try:
        c = Cellule.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        valider_cellule(c, REF_TEST, arch_commun, ctx)
    except CelluleRefusee as e:
        return str(e)
    return "PAS DE REFUS"


m = pont_cellule_commun(CELLULE_COMMUN)
b.check(m.startswith("[C4]") and "positive ou nulle" in m, f"pont cellule — [C4] contrôle `positif_ou_nul` refusé (obtenu « {m[:200]} »)")
b.check(pont_cellule_commun({**CELLULE_COMMUN, "valeur": 5.0}) == "PAS DE REFUS",
        "pont cellule — une valeur positive passe le même contrôle")

# [C5] origine `calcul` hors des variables du même bloc.
CELLULE_CALCUL = {"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc", "periode": "FY2025",
                  "valeur": 100.0, "unite": "M$",
                  "origine": {"type": "calcul", "formule": "taille_du_marche"},
                  "auteur": {"type": "demande_ciblee", "demande_id": 1}}
arch_calcul = Architecture.model_validate(arch_test(cellules_attendues=[
    {"bloc": "bloc_principal", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2025"],
     "auteur": {"type": "demande_ciblee"}}]))


def pont_cellule_calcul(payload: dict) -> str:
    try:
        c = Cellule.model_validate(payload)
    except ValidationError as e:
        return f"REFUS DU CONTRAT (pas du pont) : {e}"
    try:
        valider_cellule(c, REF_TEST, arch_calcul)
    except CelluleRefusee as e:
        return str(e)
    return "PAS DE REFUS"


m = pont_cellule_calcul(CELLULE_CALCUL)
b.check(m.startswith("[C5]") and "hors des variables retenues" in m,
        f"pont cellule — [C5] formule hors des variables du bloc refusée (obtenu « {m[:220]} »)")

# ── §5 Les fixtures réelles (copiées du réel) ───────────────────────────────────────────────────
print("§5 fixtures réelles")
fixtures = {}
for nom in ("NVDA", "RVMD", "JPM"):
    fixtures[nom] = json.loads((FIXTURES_DIR / f"{nom}.json").read_text(encoding="utf-8"))

for nom in ("NVDA", "RVMD"):
    arch = Architecture.model_validate(fixtures[nom])
    try:
        valider_pont_architecture(arch, ref)
        passe = True
        motif = None
    except ArchitectureRefusee as e:
        passe = False
        motif = str(e)
    b.check(passe, f"fixture {nom} : passe le pont (obtenu : {motif})")

arch_jpm = Architecture.model_validate(fixtures["JPM"])
try:
    valider_pont_architecture(arch_jpm, ref)
    m_jpm = "PAS DE REFUS"
except ArchitectureRefusee as e:
    m_jpm = str(e)
b.check(m_jpm.startswith("[P1]") and "bancaire" in m_jpm.lower(),
        f"fixture JPM : refusée en [P1] avec le motif du gabarit bancaire (obtenu « {m_jpm[:200]} »)")

# ── §6 La porte de l'architecte : questions sources applicables ────────────────────────────────
print("§6 questions_sources_applicables")
from app.agents.v2.frameworks import load_frameworks  # noqa: E402

fw = load_frameworks()
sources_rentable = questions_sources_applicables(ref, fw, "rentable")
sources_pre_revenus = questions_sources_applicables(ref, fw, "pre_revenus")
b.check(len(sources_rentable) > 0, "rentable : liste non vide")
b.check(len(sources_pre_revenus) > 0, "pre_revenus : liste non vide")

# Les questions sources du catalogue qui sont, pour pre_revenus, déclarées `sans_objet` — LUES dans
# `frameworks.yaml`, jamais écrites en dur : `qf_1`/`qf_3`/`mo_6` en sont le résultat mesuré, pas
# l'énoncé du test.
toutes_questions_sources = {qid for v in ref.variables for qid in v.questions_sources}
sans_objet_pre_revenus = sorted(
    q.id for f in fw.frameworks for q in f.questions
    if q.id in toutes_questions_sources
    and "pre_revenus" in q.variables_par_archetype
    and q.variables_par_archetype["pre_revenus"].mode == "sans_objet"
)
b.check(len(sans_objet_pre_revenus) > 0,
        f"au moins une question source du catalogue est `sans_objet` pour pre_revenus (sinon ce cas ne discrimine rien) — {sans_objet_pre_revenus}")
b.check(not (set(sans_objet_pre_revenus) & set(sources_pre_revenus)),
        f"aucune question `sans_objet` pour pre_revenus ({sans_objet_pre_revenus}) ne figure dans "
        f"`questions_sources_applicables` ({sources_pre_revenus})")

# ── §7 Les contrôles ─────────────────────────────────────────────────────────────────────────────
print("§7 les contrôles")


def cellule_pour_controle(variable: str, valeur: float, unite: str = "M$", periode: str = "FY2025") -> Cellule:
    return Cellule.model_validate({
        "bloc": "bloc_de_test", "variable": variable, "periode": periode, "valeur": valeur, "unite": unite,
        "origine": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
        "auteur": {"type": "demande_ciblee", "demande_id": 1}})


ctx_vide = ContexteControle()
cas_controles = [
    ("positif — valeur positive", "positif", cellule_pour_controle("x", 1.0), ctx_vide, True),
    ("positif — valeur nulle refusée", "positif", cellule_pour_controle("x", 0.0), ctx_vide, False),
    ("positif_ou_nul — valeur nulle", "positif_ou_nul", cellule_pour_controle("x", 0.0), ctx_vide, True),
    ("positif_ou_nul — valeur négative refusée", "positif_ou_nul", cellule_pour_controle("x", -1.0), ctx_vide, False),
    ("proportion — dans [0,100]", "proportion", cellule_pour_controle("x", 50.0, unite="%"), ctx_vide, True),
    ("proportion — hors [0,100] refusée", "proportion", cellule_pour_controle("x", 150.0, unite="%"), ctx_vide, False),
    ("probabilite — dans [0,1]", "probabilite", cellule_pour_controle("x", 0.5, unite="(0-1)", periode="sans_periode"), ctx_vide, True),
    ("probabilite — hors [0,1] refusée", "probabilite", cellule_pour_controle("x", 1.5, unite="(0-1)", periode="sans_periode"), ctx_vide, False),
    ("annee — entière plausible", "annee", cellule_pour_controle("x", 2027.0, unite="année", periode="sans_periode"), ctx_vide, True),
    ("annee — non entière refusée", "annee", cellule_pour_controle("x", 2027.5, unite="année", periode="sans_periode"), ctx_vide, False),
]
b.require(cas_controles, 10, "cas des contrôles simples")
for label, nom_controle, cellule, ctx, doit_tenir in cas_controles:
    motif = CONTROLES[nom_controle](cellule, ctx)
    b.check((motif is None) == doit_tenir, f"contrôle {label} : motif obtenu « {motif} »")


def part_calculee_motif(cellule: Cellule, ctx: ContexteControle) -> str:
    """Appelle `part_calculee`, sans jamais crasher le check : une garde affaiblie par mutation
    doit produire un FAIL lisible (2ᵉ faux vert), jamais une trace Python qui tue le script avant
    son bilan (`feedback_check_degrade_en_sortant_a_zero`)."""
    try:
        motif = CONTROLES["part_calculee"](cellule, ctx)
        return "TIENT" if motif is None else motif
    except Exception as e:  # noqa: BLE001
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"


CELLULE_PART = Cellule.model_validate({
    "bloc": "bloc_de_test", "variable": "part_de_marche", "periode": "FY2025", "valeur": 20.0, "unite": "%",
    "origine": {"type": "calcul", "formule": "chiffre_affaires_du_bloc / taille_du_marche"},
    "auteur": {"type": "demande_ciblee", "demande_id": 1}})
m = part_calculee_motif(CELLULE_PART, ContexteControle(dernier_exercice_publie=None))
b.check("exercice publié inconnu" in m, f"part_calculee — sans exercice publié connu, refusé nommément (obtenu « {m} »)")
m = part_calculee_motif(CELLULE_PART, ContexteControle(dernier_exercice_publie="FY2024"))
b.check("postérieure" in m, f"part_calculee — mesurée après le dernier exercice publié, refusée (obtenu « {m} »)")
m = part_calculee_motif(CELLULE_PART, ContexteControle(dernier_exercice_publie="FY2025"))
b.check(m == "TIENT", f"part_calculee — mesurée AU dernier exercice publié, tient (obtenu « {m} »)")
m = part_calculee_motif(CELLULE_PART, ContexteControle(dernier_exercice_publie="FY2026"))
b.check(m == "TIENT", f"part_calculee — mesurée AVANT le dernier exercice publié, tient (obtenu « {m} »)")
CELLULE_PART_PAS_CALCUL = Cellule.model_validate({
    "bloc": "bloc_de_test", "variable": "part_de_marche", "periode": "FY2025", "valeur": 20.0, "unite": "%",
    "origine": {"type": "jugement", "taux_de_base": {"classe_de_reference": "classe de référence utilisée pour ce test", "valeur": 1.0,
                                                      "source_entry_refs": [{"entry_id": 1}]},
                "ecart_justifie": "Écart justifié pour ce cas de test, assez long pour le contrat."},
    "auteur": {"type": "demande_ciblee", "demande_id": 1}})
m = part_calculee_motif(CELLULE_PART_PAS_CALCUL, ContexteControle(dernier_exercice_publie="FY2025"))
b.check("doit être CALCULÉE" in m, f"part_calculee — origine autre que calcul, refusée (obtenu « {m} »)")

# ── §8 appliquer_scenario ───────────────────────────────────────────────────────────────────────
print("§8 appliquer_scenario")
CENTRALES = {
    ("bloc_a", "croissance_du_marche", "FY2024"): 0.05,
    ("bloc_a", "croissance_du_marche", "FY2025"): 0.06,
    ("bloc_a", "croissance_du_marche", "FY2026"): 0.07,
    ("bloc_a", "marge_contributive", "FY2025"): 0.30,
}
FOURCHETTE_CROISSANCE = Fourchette.model_validate({
    "bloc": "bloc_a", "variable": "croissance_du_marche", "periode_debut": "FY2024", "periode_fin": "FY2026",
    "bas": 0.0, "haut": 0.10, "methode": "dispersion_observee",
    "origine_bas": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]},
    "origine_haut": {"type": "piece", "source_entry_refs": [{"entry_id": 1}]}})

b.check(appliquer_scenario(CENTRALES, SCENARIO_CENTRAL, [FOURCHETTE_CROISSANCE]) == dict(CENTRALES),
        "central : copie identique des centrales")

DEP_BORNE_BASSE = Deplacement.model_validate({
    "bloc": "bloc_a", "variable": "croissance_du_marche", "periode_debut": "FY2025", "periode_fin": "FY2026",
    "cible": "borne_basse", "motif": "Un concurrent internalise une partie de la demande, motif testé ici."})
SC_BORNE = Scenario.model_validate({"nom": "scenario_borne", "recit": "Récit du scénario testé, assez long.",
                                    "nature": "nomme", "deplacements": [DEP_BORNE_BASSE]})
res = appliquer_scenario(CENTRALES, SC_BORNE, [FOURCHETTE_CROISSANCE])
b.check(res[("bloc_a", "croissance_du_marche", "FY2024")] == CENTRALES[("bloc_a", "croissance_du_marche", "FY2024")],
        "borne basse : la période HORS plage reste au central")
b.check(res[("bloc_a", "croissance_du_marche", "FY2025")] == 0.0 and res[("bloc_a", "croissance_du_marche", "FY2026")] == 0.0,
        "borne basse : les périodes DANS la plage prennent la borne basse")
b.check(res[("bloc_a", "marge_contributive", "FY2025")] == CENTRALES[("bloc_a", "marge_contributive", "FY2025")],
        "borne basse : une variable non visée reste au central")

DEP_VALEUR_DITE = Deplacement.model_validate({
    "bloc": "bloc_a", "variable": "marge_contributive", "periode_debut": "FY2025", "periode_fin": "FY2025",
    "cible": "valeur_dite", "valeur_dite": 0.42,
    "motif": "Un contrat de distribution renégocié relève la marge, motif testé ici.",
    "source_entry_refs": [501]})
SC_DITE = Scenario.model_validate({"nom": "scenario_dite", "recit": "Récit du scénario testé, assez long.",
                                   "nature": "nomme", "deplacements": [DEP_VALEUR_DITE]})
try:
    res = appliquer_scenario(CENTRALES, SC_DITE, [FOURCHETTE_CROISSANCE])
    b.check(res[("bloc_a", "marge_contributive", "FY2025")] == 0.42, "valeur dite : la cellule prend la valeur dite")
except Exception as e:  # noqa: BLE001
    b.check(False, f"valeur dite : la cellule prend la valeur dite — AUTRE EXCEPTION {type(e).__name__}: {e}")

DEP_SANS_FOURCHETTE = Deplacement.model_validate({
    "bloc": "bloc_a", "variable": "marge_contributive", "periode_debut": "FY2025", "periode_fin": "FY2025",
    "cible": "borne_haute", "motif": "Déplacement de test sans fourchette disponible pour marge_contributive."})
SC_SANS_FOURCHETTE = Scenario.model_validate({"nom": "scenario_sans_fourchette",
                                              "recit": "Récit du scénario testé, assez long.",
                                              "nature": "nomme", "deplacements": [DEP_SANS_FOURCHETTE]})
try:
    appliquer_scenario(CENTRALES, SC_SANS_FOURCHETTE, [FOURCHETTE_CROISSANCE])
    b.check(False, "déplacement sans fourchette couvrante : devait être refusé")
except ScenarioInapplicable as e:
    b.check("aucune fourchette" in str(e), f"déplacement sans fourchette couvrante : refusé nommément ({e})")
except Exception as e:  # noqa: BLE001 — un refus mal gardé ne doit pas tuer le script (2ᵉ faux vert)
    b.check(False, f"déplacement sans fourchette couvrante : AUTRE EXCEPTION {type(e).__name__}: {e}")

DEP_RIEN = Deplacement.model_validate({
    "bloc": "bloc_absent", "variable": "variable_absente", "periode_debut": "FY2025", "periode_fin": "FY2025",
    "cible": "borne_basse", "motif": "Déplacement de test qui ne touche aucune cellule centrale connue."})
SC_RIEN = Scenario.model_validate({"nom": "scenario_rien", "recit": "Récit du scénario testé, assez long.",
                                   "nature": "nomme", "deplacements": [DEP_RIEN]})
try:
    appliquer_scenario(CENTRALES, SC_RIEN, [FOURCHETTE_CROISSANCE])
    b.check(False, "déplacement qui ne touche rien : devait être refusé")
except ScenarioInapplicable as e:
    b.check("ne touche AUCUNE cellule" in str(e), f"déplacement qui ne touche rien : refusé nommément ({e})")
except Exception as e:  # noqa: BLE001
    b.check(False, f"déplacement qui ne touche rien : AUTRE EXCEPTION {type(e).__name__}: {e}")

SC_BRANCHE = Scenario.model_validate({"nom": "scenario_branche", "recit": "Récit de la branche testée, assez long.",
                                      "nature": "branche", "probabilite": 0.4, "deplacements": [DEP_BORNE_BASSE]})
res = appliquer_scenario(CENTRALES, SC_BRANCHE, [FOURCHETTE_CROISSANCE])
b.check(res[("bloc_a", "croissance_du_marche", "FY2025")] == 0.0, "une branche à probabilité s'applique comme un scénario nommé")

# ── §9 Réplicabilité ─────────────────────────────────────────────────────────────────────────────
print("§9 réplicabilité")
TICKERS_REGEX = ("NVDA", "RVMD", "JPM", "MSFT", "NVIDIA", "Revolution", "JPMorgan", "Microsoft")
noms_de_blocs: set[str] = set()
for nom in ("NVDA", "RVMD", "JPM"):
    for bloc in fixtures[nom]["blocs"]:
        noms_de_blocs.add(bloc["id"])
motifs_interdits = tuple(TICKERS_REGEX) + tuple(sorted(noms_de_blocs))

fichiers_a_grepper = sorted(MODULE_DIR.glob("*.py")) + [SCHEMA_PATH]
fichiers_lus = 0
for chemin in fichiers_a_grepper:
    source = chemin.read_text(encoding="utf-8")
    depouille = strip_code(source)
    fichiers_lus += 1
    for motif in motifs_interdits:
        b.check(motif not in depouille,
                f"réplicabilité — `{chemin.relative_to(ROOT)}` ne nomme pas `{motif}` (hors commentaires/docstrings)")

contenu_yaml = YAML_PATH.read_text(encoding="utf-8")
# ⚠️ PAS de dépouillement des commentaires ici, à la différence des sources Python : l'en-tête du
# référentiel n'énonce la règle de réplicabilité qu'en termes génériques, sans jamais nommer de
# ticker pour l'illustrer — contrairement à un docstring Python qui peut légitimement écrire « ne
# jamais nommer NVDA » (`feedback_grep_interdit_lit_sa_propre_enonciation`). Un ticker introduit
# dans CE fichier, même en commentaire, est donc une vraie violation, jamais une fausse alerte.
fichiers_lus += 1
for motif in motifs_interdits:
    b.check(motif not in contenu_yaml, f"réplicabilité — `{YAML_PATH.relative_to(ROOT)}` ne nomme pas `{motif}`")

b.check(fichiers_lus > 0, "réplicabilité — au moins un fichier a été lu (pas de vert sur liste vide)")

sys.exit(b.summary())
