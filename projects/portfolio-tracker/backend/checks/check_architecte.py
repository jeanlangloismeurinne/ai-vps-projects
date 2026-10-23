"""Vérification de l'AGENT ARCHITECTE — sa porte, les périodes, la matière, l'exemple du prompt,
les contrôles de structure [S1]-[S9], le renvoi, le service de signature (lot M3, roadmap V3
`12-lot-M3-architecte.md`). Sans réseau, sans modèle, sans base.

  • §1 LA PORTE — une ligne du tableau §3.1 = un cas (via `porte._diagnostic`, la plomberie de
       lecture `manque_pour_question` étant remplacée par un double contrôlé) ; l'interrupteur
       `porte_admet_reponses_refusees` ; émetteur non classé.
  • §2 LES PÉRIODES — NVDA (fins fin janvier), une fin au 1ᵉʳ janvier, une collision.
  • §3 LA MATIÈRE — déterminisme du rendu (deux rendus identiques), adresses `[axe=… membre=…]`.
  • §4 L'EXEMPLE DU PROMPT (#121) — valide contre `ArchitecteSortie`, puis — en-tête posé — contre
       `Architecture`, [P1]-[P5] et [S1]-[S9] sur une matière fictive écrite ici.
  • §5 L'EN-TÊTE — un `ticker_id` dans la sortie du modèle est refusé par `Strict`.
  • §6 [S1]-[S9] — pour chaque règle, un cas réel (NVDA, ventilation copiée du réel) ou fictif qui
       passe, et un cas muté qui la fait refuser par SON code.
  • §7 LE RENVOI — un faux agent qui rend une sortie refusée puis une valide → acceptée, coût cumulé ;
       deux refus → `ArchitectureRefusee` avec les motifs ; porte fermée → aucun appel.
  • §8 LE SERVICE — en attente / remplacée / signée / signée à revoir / interrupteur `false`.
  • §9 RÉPLICABILITÉ — grep des tickers/segments des fixtures dans le code et le prompt livrés, sur
       le texte dépouillé des commentaires/docstrings, asserté en positif sur un fichier qui en
       contient.

Cible : pydantic v2 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402

import app.agents.v2.parcours as parcours_mod  # noqa: E402
import app.modele_entreprise.porte as porte_mod  # noqa: E402
from app.contracts.architecture_signature_schema import DemandeDecisionArchitecture  # noqa: E402
from app.contracts.modele_entreprise_schema import Architecture, BlocPropose, InventaireProgramme  # noqa: E402
from app.contracts.parcours_schema import Manque  # noqa: E402
from app.knowledge import perimetre as pe  # noqa: E402
from app.knowledge import ventilation as vt  # noqa: E402
from app.knowledge import ventilation_xbrl as vx  # noqa: E402
from app.knowledge.socle_comptes import (  # noqa: E402
    charger_gabarit, charger_reclassements, reconstituer, structure_du_socle,
)
from app.modele_entreprise.architecte import (  # noqa: E402
    ArchitecteSortie, ArchitectureRefusee, PorteFermee, _EXEMPLE_ARCHITECTURE, _poser_entete,
    juger_architecture,
)
from app.modele_entreprise.matiere import Matiere  # noqa: E402
import app.modele_entreprise.matiere as matiere_mod  # noqa: E402
from app.modele_entreprise.periodes import PeriodesInvalides, periode_du_classeur, periodes_du_classeur  # noqa: E402
from app.modele_entreprise.porte import EtatQuestionSource, Porte, porte_de_l_architecte  # noqa: E402
from app.modele_entreprise.referentiel import ArchitectureRefusee as PontRefusee  # noqa: E402
from app.modele_entreprise.referentiel import load_referentiel, valider_pont_architecture  # noqa: E402
from app.modele_entreprise.signature import servir_architecture  # noqa: E402
from app.modele_entreprise.structure import valider_structure  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = ROOT / "app" / "modele_entreprise"
FIX = Path(__file__).resolve().parent / "fixtures" / "ventilation"
SOCLE_FIX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"

b = Bilan()
REF = load_referentiel()

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# §1 LA PORTE
# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§1 la porte")


def _etat(*, archetype="rentable", reponses=(), dispenses=None, comite=None) -> SimpleNamespace:
    return SimpleNamespace(archetype=archetype, dispenses=dispenses or {}, comite=comite or {},
                           reponses=list(reponses), fichier=None)


def _m(nature, cause, explication, answer_id=None, attente=None) -> Manque:
    kw = dict(framework_id="fw", libelle_framework="FW", question_id="q1", enonce="?",
              nature=nature, cause=cause, explication=explication, answer_id=answer_id)
    if nature == "pas_encore_observable":
        from app.contracts.readiness_report_schema import AttenteObservation
        kw["attente"] = attente or AttenteObservation(
            cause="x", fait_declencheur="x", depuis="2026-01-01", piece_du_fait=1,
            historique_requis="x", revoir_le=date(2099, 1, 1))
    if cause in ("recherche_epuisee", "source_indisponible", "sans_source_possible"):
        from app.contracts.parcours_schema import IngredientManquant
        kw["ingredients"] = [IngredientManquant(
            ingredient_id="ing_test", cause=cause, constate_le=datetime(2026, 10, 1, tzinfo=timezone.utc),
            motif="motif de test pour prouver la cause")]
    return Manque.model_validate(kw)


F = SimpleNamespace(id="fw")
Q = SimpleNamespace(id="q1")


def _diag(applicable, manque, *, ref=REF) -> EtatQuestionSource:
    """Appelle `_diagnostic` avec `manque_pour_question` remplacé par un double contrôlé ; ne
    laisse JAMAIS une exception inattendue tuer le script avant son bilan
    (`feedback_check_degrade_en_sortant_a_zero`, 2ᵉ faux vert) — une garde affaiblie par mutation
    doit produire un FAIL lisible."""
    porte_mod.manque_pour_question = lambda etat, f, q: (applicable, manque)
    try:
        return porte_mod._diagnostic(_etat(), F, Q, ref)
    except Exception as e:  # noqa: BLE001
        return EtatQuestionSource("q1", "fw", False, f"AUTRE EXCEPTION {type(e).__name__}: {e}")
    finally:
        porte_mod.manque_pour_question = parcours_mod.manque_pour_question


cas_porte = [
    ("applicables inconnu (émetteur non classé)", None, None, False, "émetteur non classé"),
    ("sans_reponse, toute cause", True, _m("sans_reponse", "pas_encore_cherchee", "x"), False,
     "aucune réponse instruite"),
    ("rouverte_comite", True, _m("rouverte_comite", "renvoi_comite", "x"), False, "remis à zéro"),
    ("non_fondee, source_indisponible", True, _m("non_fondee", "source_indisponible", "panne"),
     False, "échec technique"),
    ("non_fondee, cause != source_indisponible", True,
     _m("non_fondee", "recherche_epuisee", "non publié", answer_id=5), True, "non fondable"),
    ("perimee", True, _m("perimee", "fait_nouveau_publie", "un fait", answer_id=7), True,
     "réponse #7"),
    ("pas_encore_observable", True, _m("pas_encore_observable", "pas_encore_observable", "x",
                                       answer_id=9), True, "réponse #9"),
]
b.require(cas_porte, 7, "cas de la porte, lignes du tableau §3.1")
for label, applicable, manque, attendu_ouvre, fragment in cas_porte:
    eq = _diag(applicable, manque)
    b.check(eq.ouvre == attendu_ouvre and fragment in eq.raison,
            f"porte — « {label} » : ouvre={attendu_ouvre} attendu, fragment « {fragment} » — "
            f"obtenu ouvre={eq.ouvre} raison « {eq.raison[:140]} »")

# `manque is None` : les TROIS sous-cas (tient / acceptée / dispensée) — duck-typing (pas de vrais
# objets PositionComite/FrameworkAnswerServie, juste les attributs lus par `_diagnostic`).
porte_mod.manque_pour_question = lambda etat, f, q: (True, None)
try:
    eq = porte_mod._diagnostic(_etat(dispenses={"fw": frozenset({"q1"})}), F, Q, REF)
    b.check(eq.ouvre and "dispensée" in eq.raison, f"porte — dispensée : {eq.raison}")

    pos = SimpleNamespace(acceptation=SimpleNamespace(etat="en_vigueur"))
    eq = porte_mod._diagnostic(_etat(comite={("fw", "q1"): pos}), F, Q, REF)
    b.check(eq.ouvre and "acceptée" in eq.raison, f"porte — acceptée : {eq.raison}")

    old_rt = parcours_mod.reponse_tient
    parcours_mod.reponse_tient = lambda r: True
    try:
        rep = SimpleNamespace(answer_id=42, servie=SimpleNamespace(framework_id="fw", question_id="q1"))
        eq = porte_mod._diagnostic(_etat(reponses=[rep]), F, Q, REF)
        b.check(eq.ouvre and "réponse #42" in eq.raison, f"porte — tient : {eq.raison}")
    finally:
        parcours_mod.reponse_tient = old_rt
finally:
    porte_mod.manque_pour_question = parcours_mod.manque_pour_question

# L'interrupteur `porte_admet_reponses_refusees` — arbitrage du 2026-10-22.
REF_ORDRE0 = REF.model_copy(update={"porte_admet_reponses_refusees": False})
m_renvoyee = _m("renvoyee", "controle_ko", "le contrôle a refusé", answer_id=3)
eq_test = _diag(True, m_renvoyee, ref=REF)
b.check(eq_test.ouvre and "refusée par le contrôle" in eq_test.raison,
        f"interrupteur — phase de test (true) : renvoyée OUVRE, marquée : {eq_test.raison}")
eq_cible = _diag(True, m_renvoyee, ref=REF_ORDRE0)
b.check(not eq_cible.ouvre and "à corriger avant de dessiner" in eq_cible.raison,
        f"interrupteur — cible (false) : renvoyée FERME : {eq_cible.raison}")
b.check(REF.porte_admet_reponses_refusees is True,
        "le référentiel réel est en phase de test (`porte_admet_reponses_refusees: true`)")

# `porte_de_l_architecte` — émetteur non classé au niveau de la porte entière.
porte_vide = porte_de_l_architecte(SimpleNamespace(archetype=None), REF)
b.check(not porte_vide.ouverte and porte_vide.questions == () and porte_vide.archetype is None,
        "porte — émetteur non classé : porte fermée, aucune question, raison au niveau porte")

print("§2 les périodes")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
b.check(periode_du_classeur(date(2026, 1, 25)) == "FY2026",
        "périodes — une clôture fin janvier (NVDA) appartient à l'année qui s'achève")
b.check(periode_du_classeur(date(2026, 1, 1)) == "FY2025",
        "périodes — une clôture au 1ᵉʳ janvier recule sur l'année précédente")
b.check(periode_du_classeur(date(2026, 6, 30)) == "FY2026",
        "périodes — une clôture en milieu d'année n'est jamais affectée par le recul de 7 jours")

SOCLE_NVDA_PERIODES = {
    "periodes": [
        {"id": "FY2024-01-28", "fin": "2024-01-28", "cadrage": "flux", "nature": "exercice"},
        {"id": "FY2025-01-26", "fin": "2025-01-26", "cadrage": "flux", "nature": "exercice"},
        {"id": "FY2026-01-25", "fin": "2026-01-25", "cadrage": "flux", "nature": "exercice"},
    ]
}
pdc = periodes_du_classeur(SOCLE_NVDA_PERIODES, 10)
b.check(pdc.historiques == ("FY2024", "FY2025", "FY2026"), f"périodes NVDA historiques : {pdc.historiques}")
b.check(pdc.projetees == tuple(f"FY{2026+i}" for i in range(1, 11)),
        f"périodes NVDA projetées (horizon 10) : {pdc.projetees}")

SOCLE_COLLISION = {"periodes": [
    {"id": "a", "fin": "2025-12-28", "cadrage": "flux", "nature": "exercice"},
    {"id": "b", "fin": "2026-01-02", "cadrage": "flux", "nature": "exercice"},
]}
try:
    periodes_du_classeur(SOCLE_COLLISION, 5)
    b.check(False, "périodes — collision de deux exercices sur le même FY#### : devait lever")
except PeriodesInvalides as e:
    b.check("retombent sur" in str(e), f"périodes — collision refusée nommément : {e}")

print("§3 la matière")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
from app.modele_entreprise.matiere import rendre_matiere  # noqa: E402

VENT_NVDA_FICTIVE = {
    "statut": "ventilee", "axes": ["activites"],
    "cellules": [
        {"axe": "activites", "ligne": "chiffre_affaires", "membre": "fictif:ProduitAMember",
         "periode": "FY2025", "v": 100.0, "concept": "x", "accn": "a", "libelle": "Produit A"},
        {"axe": "activites", "ligne": "chiffre_affaires", "membre": "fictif:ProduitBMember",
         "periode": "FY2025", "v": 50.0, "concept": "x", "accn": "a", "libelle": "Produit B"},
    ],
    "raccords": [], "membres_nouveaux": [], "non_rattaches": [], "sous_details": [], "conflits": [],
    "refus": [],
}


def matiere_fictive(**over) -> Matiere:
    base = dict(
        ticker_id="FICTIF", raison_sociale="Fictive SA", cik=1, date_du_jour=date(2026, 10, 22),
        derniere_cloture=date(2025, 12, 31), derniere_cloture_annuelle=date(2025, 12, 31),
        archetype="rentable", classement_motif="motif de test", classement_date=date(2025, 1, 1),
        classement_declencheur=None, famille="industrielle",
        periodes_historiques=("FY2024", "FY2025"), periodes_projetees=("FY2026", "FY2027"),
        lignes_business_plan=("chiffre_affaires (Chiffre d'affaires)",), fiches_texte="  · x",
        patron_texte="  · y", socle_texte="comptes", socle_piece_id=100, socle_structure={},
        ventilation_texte="vent", ventilation_piece_id=200, ventilation_structure=VENT_NVDA_FICTIVE,
        questions_texte=("— Question me_2 — ouvre",), notes_flash_texte="(aucune)",
        pieces_citables=frozenset({100, 101, 102, 103}), pieces_citables_texte="  · #100 — (sans titre)",
        me_7_verbatim=None, me_7_nombre_de_programmes=None)
    base.update(over)
    return Matiere(**base)


M1, M2 = matiere_fictive(), matiere_fictive()
b.check(rendre_matiere(M1) == rendre_matiere(M2), "matière — rendu déterministe (deux rendus identiques)")
txt = rendre_matiere(M1)
b.check("Fictive SA" in txt and "CIK 1" in txt, "matière — raison sociale et CIK présents")
b.check("2026-10-22" in txt, "matière — date du jour présente")
b.check("[axe=activites membre=fictif:ProduitAMember]" not in txt,
        "matière — PAS d'adresse ici (ventilation_texte est un champ de texte déjà rendu séparément, "
        "sans identifiants dans cette fixture)")

M_secteur_unique = matiere_fictive(ventilation_structure=None,
                                   ventilation_texte="L'émetteur ne publie qu'un secteur : tous les "
                                   "blocs seront estimés et se raccordent à une ligne des comptes "
                                   "(statut `secteur_unique`).")
b.check("tous les blocs seront estimés" in rendre_matiere(M_secteur_unique),
        "matière — secteur_unique : la phrase du constat, aucune adresse")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§4 l'exemple du prompt (#121)")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
sortie = ArchitecteSortie.model_validate(_EXEMPLE_ARCHITECTURE)
b.check(len(sortie.blocs) == 7, f"exemple — 7 blocs, dont une plateforme (obtenu {len(sortie.blocs)})")
arch_exemple = _poser_entete(sortie, ticker_id="FICTIF", version=1, archetype="rentable",
                             famille="industrielle", version_referentiel=REF.version)
b.check(len(arch_exemple.inventaire_des_programmes) == 1 and
       arch_exemple.inventaire_des_programmes[0].programme == "Programme X",
       f"exemple — inventaire des programmes porte `Programme X` : {arch_exemple.inventaire_des_programmes}")
matiere_exemple = matiere_fictive(
    pieces_citables=frozenset({100, 101, 102, 103}),
    me_7_verbatim="L'entreprise mentionne le Programme X et un portefeuille de recherche amont "
                 "non nommé individuellement.")
tient, motif, signaux = juger_architecture(arch_exemple, REF, matiere_exemple)
b.check(tient, f"exemple — valide contre le contrat, [P1]-[P5] et [S1]-[S15] (motif : {motif})")
b.check(any("[S15]" in s and "non chiffré" in s for s in signaux),
        f"exemple — [S15] signale l'inventaire non chiffré (`me_7_nombre_de_programmes` absent de "
        f"la matière fictive) : {signaux}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§5 l'en-tête")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
try:
    ArchitecteSortie.model_validate({**_EXEMPLE_ARCHITECTURE, "ticker_id": "NVDA"})
    b.check(False, "en-tête — un `ticker_id` dans la sortie du modèle devait être refusé (Strict)")
except Exception as e:  # noqa: BLE001
    b.check("ticker_id" in str(e) or "extra" in str(e).lower(),
            f"en-tête — `ticker_id` venu du modèle refusé par `Strict` : {e}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§6 [S1]-[S9]")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
GAB = charger_gabarit()
REF_VENT = vt.charger_referentiel()


def charger_depot(ticker: str, accn: str) -> vt.Depot:
    manifeste = json.loads((FIX / f"{ticker}_{accn}.json").read_text(encoding="utf-8"))
    inst = gzip.decompress((FIX / f"{ticker}_{accn}_inst.xml.gz").read_bytes())
    lab = gzip.decompress((FIX / f"{ticker}_{accn}_lab.xml.gz").read_bytes())
    defx = gzip.decompress((FIX / f"{ticker}_{accn}_def.xml.gz").read_bytes())
    faits = tuple(vx.lire_instance(inst))
    etiquettes = vx.lire_etiquettes(lab)
    hierarchie, conflits = vx.lire_hierarchie(defx)
    return vt.Depot(accn=accn, form=manifeste["form"], filed=manifeste["filed"], faits=faits,
                    etiquettes=etiquettes, hierarchie=hierarchie, conflits=conflits)


def socle_de(ticker: str):
    d = json.loads((SOCLE_FIX / f"{ticker}.json").read_text(encoding="utf-8"))
    return d["cik"], structure_du_socle(reconstituer(d["faits"], GAB, reclassements=charger_reclassements(d["cik"], GAB)))


_, SOCLE_STRUCT_NVDA = socle_de("NVDA")
# Les TROIS dépôts que `ventilation_feed.lire_depots` lit en production quand le premier niveau change
# (10-K, 10-Q récent, 10-Q jumeau) ; l'architecte lit la VUE SERVIE (lot P1 §8), jamais le relevé brut.
DEPOTS_NVDA = [charger_depot("NVDA", "0001045810-26-000021"), charger_depot("NVDA", "0001045810-26-000075"),
               charger_depot("NVDA", "0001045810-25-000209")]
V_NVDA = vt.relever(DEPOTS_NVDA, GAB, REF_VENT, SOCLE_STRUCT_NVDA)
STRUCT_NVDA = pe.vue_servie(vt.structure_de_ventilation(V_NVDA, version_referentiel=REF_VENT.version,
                                                        version_gabarit=GAB.version, depots=tuple(DEPOTS_NVDA)),
                            SOCLE_STRUCT_NVDA)

MATIERE_NVDA = matiere_fictive(
    ticker_id="NVDA", raison_sociale="NVIDIA Corp", cik=1045810,
    periodes_historiques=("FY2024", "FY2025", "FY2026"),
    periodes_projetees=tuple(f"FY{2026+i}" for i in range(1, 11)),
    ventilation_structure=STRUCT_NVDA, socle_structure=SOCLE_STRUCT_NVDA,
    socle_piece_id=1, ventilation_piece_id=2,
    pieces_citables=frozenset({1, 2}))

SEGS_10K = [("data_center", "nvda:DataCenterMember"), ("gaming", "nvda:GamingMember"),
           ("proviz", "nvda:ProfessionalVisualizationMember"), ("automotive", "nvda:AutomotiveMember"),
           ("oem", "nvda:OEMAndOtherMember")]


def _bloc_publie(bid, membre, **over):
    base = {"id": bid, "libelle": bid, "role": "activite", "statut": "metier_actuel",
           "origine": "interne", "maille": "publie",
           "rattachement": {"type": "publie", "axe": "activites", "membres": [membre]},
           "variables": ["chiffre_affaires_du_bloc"],
           "motif": f"Segment publié {bid} du 10-K, motif de longueur suffisante pour le contrat."}
    base.update(over)
    return base


def arch_nvda_10k(**over_cellules) -> Architecture:
    blocs = [_bloc_publie(bid, m) for bid, m in SEGS_10K]
    formule = " + ".join(f"{bid}__chiffre_affaires_du_bloc" for bid, _ in SEGS_10K)
    cellules = [{"bloc": bid, "variable": "chiffre_affaires_du_bloc",
                "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}}
               for bid, _ in SEGS_10K]
    d = {"schema_version": "architecture-1.3.0", "ticker_id": "NVDA", "version": 1, "archetype": "rentable",
        "famille": "industrielle", "version_referentiel": REF.version, "blocs": blocs,
        "variables_propres": [], "passage_a_l_agrege": [{"ligne": "chiffre_affaires", "formule": formule}],
        "cellules_attendues": cellules,
        # [S10] (1.2.0, cause ①) — la ventilation réelle de NVDA porte aussi `clients`, `geographie`,
        # `secteurs` : premier niveau sur `activites` seul, les autres axes sont déclarés en usage.
        "autres_axes": [
            {"axe": "clients", "usage": "Information de concentration client, hors de l'arbre."},
            {"axe": "geographie", "usage": "Information de répartition géographique, hors de l'arbre."},
            {"axe": "secteurs", "usage": "Second découpage publié (segments) ; raccord des marges, hors de l'arbre."},
        ]}
    d.update(over_cellules)
    return Architecture.model_validate(d)


def valide_ou_motif(arch: Architecture, matiere=MATIERE_NVDA) -> str:
    try:
        signaux = valider_structure(arch, REF, matiere)
        return f"OK signaux={signaux}"
    except Exception as e:  # noqa: BLE001
        return str(e)


ARCH_10K = arch_nvda_10k()
r = valide_ou_motif(ARCH_10K)
b.check(r.startswith("OK") and "[S3b]" in r,
        f"[S1]-[S9] — architecture NVDA plausible au découpage du 10-K (antérieur), signal [S3b] attendu : {r[:300]}")

# Garde (iii), lot P1 : une architecture sur le découpage LE PLUS RÉCENT (Data Center + Edge Computing)
# trouve ses exercices — Edge Computing FY2026 existe par addition vérifiée — et ne lève aucun [S3b].
SEGS_10Q = [("data_center", "nvda:DataCenterMember"), ("edge", "nvda:EdgeComputingMember")]
ARCH_10Q = arch_nvda_10k(
    blocs=[_bloc_publie(bid, m) for bid, m in SEGS_10Q],
    passage_a_l_agrege=[{"ligne": "chiffre_affaires",
                        "formule": "data_center__chiffre_affaires_du_bloc + edge__chiffre_affaires_du_bloc"}],
    cellules_attendues=[{"bloc": bid, "variable": "chiffre_affaires_du_bloc",
                         "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}}
                        for bid, _ in SEGS_10Q])
r = valide_ou_motif(ARCH_10Q)
b.check(r.startswith("OK") and "[S3b]" not in r and "[S2]" not in r,
        f"[S2]/[S3b] — architecture sur le découpage le plus récent : exercices trouvés (addition vérifiée), "
        f"aucun signal : {r[:300]}")
ARCH_10Q_SANS_EDGE = arch_nvda_10k(
    blocs=[_bloc_publie("data_center", "nvda:DataCenterMember")],
    passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "data_center__chiffre_affaires_du_bloc"}],
    cellules_attendues=[{"bloc": "data_center", "variable": "chiffre_affaires_du_bloc",
                         "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}}])
r = valide_ou_motif(ARCH_10Q_SANS_EDGE)
b.check(r.startswith("[S2]") and "FY2026-01-25" in r and "EdgeComputing" in r,
        f"[S2] — période de référence = l'EXERCICE FY2026 du découpage récent (pas un cumul) ; Edge Computing "
        f"non couvert est nommé : {r[:300]}")

# [S1] : un membre inventé.
ARCH_S1 = arch_nvda_10k(blocs=[_bloc_publie("data_center", "nvda:InventeMember")] +
                        [_bloc_publie(bid, m) for bid, m in SEGS_10K[1:]])
r = valide_ou_motif(ARCH_S1)
b.check(r.startswith("[S1]"), f"[S1] — membre inventé refusé : {r[:200]}")

# [S1] — REGROUPEMENT (1.2.0, cause ①) : plusieurs membres publiés d'un bloc, de parents
# DIFFÉRENTS dans la hiérarchie relevée — `nvda:HyperscaleMember` (enfant de Data Center au 10-Q)
# et `nvda:GamingMember` (premier niveau, aucun parent) n'ont pas le même parent.
ARCH_REGROUP_KO = arch_nvda_10k(blocs=[
    _bloc_publie("regroupe", "nvda:HyperscaleMember", rattachement={
        "type": "publie", "axe": "activites", "membres": ["nvda:HyperscaleMember", "nvda:GamingMember"]})],
    passage_a_l_agrege=[{"ligne": "chiffre_affaires", "formule": "regroupe__chiffre_affaires_du_bloc"}],
    cellules_attendues=[{"bloc": "regroupe", "variable": "chiffre_affaires_du_bloc",
                        "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}}],
    autres_axes=[{"axe": "clients", "usage": "usage de test suffisamment long"}, {"axe": "geographie", "usage": "usage de test suffisamment long"},
                {"axe": "secteurs", "usage": "usage de test suffisamment long"}])
r = valide_ou_motif(ARCH_REGROUP_KO)
b.check(r.startswith("[S1]") and "parents différents" in r,
        f"[S1] — regroupement de membres à parents différents refusé : {r[:300]}")

# [S1] — REGROUPEMENT valide : deux membres de premier niveau (même parent, `None`).
_RESTE_BLOC = {"id": "reste", "libelle": "Reste", "role": "activite", "statut": "metier_actuel",
              "origine": "interne", "maille": "estime",
              "rattachement": {"type": "agrege", "ligne": "chiffre_affaires"},
              "variables": ["chiffre_affaires_du_bloc"], "pieces": [1],
              "motif": "Reste non couvert par le regroupement, motif de longueur suffisante."}
ARCH_REGROUP_OK = arch_nvda_10k(blocs=[
    _bloc_publie("regroupe", "nvda:DataCenterMember", rattachement={
        "type": "publie", "axe": "activites", "membres": ["nvda:DataCenterMember", "nvda:GamingMember"]}),
    _RESTE_BLOC],
    passage_a_l_agrege=[{"ligne": "chiffre_affaires",
                        "formule": "regroupe__chiffre_affaires_du_bloc + reste__chiffre_affaires_du_bloc"}],
    cellules_attendues=[
        {"bloc": "regroupe", "variable": "chiffre_affaires_du_bloc",
         "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}},
        {"bloc": "reste", "variable": "chiffre_affaires_du_bloc",
         "periodes": list(MATIERE_NVDA.periodes_projetees), "auteur": {"type": "demande_ciblee"}}],
    autres_axes=[{"axe": "clients", "usage": "usage de test suffisamment long"}, {"axe": "geographie", "usage": "usage de test suffisamment long"},
                {"axe": "secteurs", "usage": "usage de test suffisamment long"}])
r = valide_ou_motif(ARCH_REGROUP_OK)
b.check(r.startswith("OK"),
        f"[S1] — regroupement de deux membres de premier niveau (même parent `None`) tient : {r[:300]}")

# [S2] : découpage mixte (Data Center + Gaming + Edge Computing, 10-K + 10-Q mêlés).
ARCH_S2 = arch_nvda_10k(blocs=[_bloc_publie("data_center", "nvda:DataCenterMember"),
                               _bloc_publie("gaming", "nvda:GamingMember"),
                               _bloc_publie("edge", "nvda:EdgeComputingMember")],
                        passage_a_l_agrege=[{"ligne": "chiffre_affaires",
                                            "formule": "data_center__chiffre_affaires_du_bloc + "
                                                       "gaming__chiffre_affaires_du_bloc + "
                                                       "edge__chiffre_affaires_du_bloc"}],
                        cellules_attendues=[
                            {"bloc": bid, "variable": "chiffre_affaires_du_bloc",
                             "periodes": list(MATIERE_NVDA.periodes_projetees),
                             "auteur": {"type": "demande_ciblee"}}
                            for bid in ("data_center", "gaming", "edge")])
r = valide_ou_motif(ARCH_S2)
b.check(r.startswith("[S2]") and "découpage mixte" in r, f"[S2] — découpage mixte refusé : {r[:250]}")

# Double compte Data Center / Compute — depuis le lot M3 bis (cause ①), l'emboîtement entre deux
# blocs PUBLIÉS est DÉRIVÉ (`faits_publies.est_premier_niveau_publie`) : Compute (membre descendant
# de Data Center dans la hiérarchie relevée) est automatiquement classé HORS premier niveau, donc
# écarté de la somme [S7] attendue — c'est [S7] qui nomme le double compte (« en trop »), plus [S3]
# (qui ne porte plus que sur l'AXE, §5 de la spec M3 bis : voir le docstring de `_s3`).
ARCH_S3 = arch_nvda_10k(blocs=[_bloc_publie("data_center", "nvda:DataCenterMember"),
                               _bloc_publie("compute", "nvda:ComputeMember"),
                               _bloc_publie("gaming", "nvda:GamingMember"),
                               _bloc_publie("proviz", "nvda:ProfessionalVisualizationMember"),
                               _bloc_publie("automotive", "nvda:AutomotiveMember"),
                               _bloc_publie("oem", "nvda:OEMAndOtherMember")],
                        passage_a_l_agrege=[{"ligne": "chiffre_affaires",
                                            "formule": " + ".join(
                                                f"{b}__chiffre_affaires_du_bloc" for b in
                                                ("data_center", "compute", "gaming", "proviz",
                                                 "automotive", "oem"))}],
                        cellules_attendues=[
                            {"bloc": bid, "variable": "chiffre_affaires_du_bloc",
                             "periodes": list(MATIERE_NVDA.periodes_projetees),
                             "auteur": {"type": "demande_ciblee"}}
                            for bid in ("data_center", "compute", "gaming", "proviz", "automotive", "oem")])
r = valide_ou_motif(ARCH_S3)
b.check(r.startswith("[S7]") and "compute" in r and "en trop" in r,
        f"[S7] — Data Center et Compute côte à côte : Compute (dérivé hors premier niveau, "
        f"descendant de Data Center) est « en trop » dans la formule de passage : {r[:300]}")

# [S3] (sous-cas 2) : les blocs publiés de premier niveau sont sur PLUSIEURS axes.
VENT_DEUX_AXES = {
    **VENT_NVDA_FICTIVE,
    "axes": ["activites", "geographie"],
    "cellules": VENT_NVDA_FICTIVE["cellules"] + [
        {"axe": "geographie", "ligne": "chiffre_affaires", "membre": "fictif:USMember",
         "periode": "FY2025", "v": 80.0, "concept": "x", "accn": "a", "libelle": "US"},
    ],
}
MATIERE_DEUX_AXES = matiere_fictive(ventilation_structure=VENT_DEUX_AXES)
ARCH_DEUX_AXES = Architecture.model_validate({
    "schema_version": "architecture-1.3.0", "ticker_id": "FICTIF", "version": 1, "archetype": "rentable",
    "famille": "industrielle", "version_referentiel": REF.version,
    "blocs": [
        {"id": "produit_a", "libelle": "Produit A", "role": "activite", "statut": "metier_actuel",
         "origine": "interne", "maille": "publie",
         "rattachement": {"type": "publie", "axe": "activites", "membres": ["fictif:ProduitAMember"]},
         "variables": ["chiffre_affaires_du_bloc"], "motif": "Bloc sur l'axe activites, motif suffisant."},
        {"id": "us", "libelle": "US", "role": "activite", "statut": "metier_actuel",
         "origine": "interne", "maille": "publie",
         "rattachement": {"type": "publie", "axe": "geographie", "membres": ["fictif:USMember"]},
         "variables": ["chiffre_affaires_du_bloc"], "motif": "Bloc sur l'axe geographie, motif suffisant."},
    ],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "chiffre_affaires",
                            "formule": "produit_a__chiffre_affaires_du_bloc + us__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [
        {"bloc": "produit_a", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
        {"bloc": "us", "variable": "chiffre_affaires_du_bloc", "periodes": ["FY2026", "FY2027"],
         "auteur": {"type": "demande_ciblee"}},
    ],
})
r = valide_ou_motif(ARCH_DEUX_AXES, MATIERE_DEUX_AXES)
b.check(r.startswith("[S3]") and "plusieurs axes" in r,
        f"[S3] — un seul axe au premier niveau, plusieurs axes refusés : {r[:250]}")

# [S3b] : signal déjà observé sur `ARCH_10K` ci-dessus — revérifié ici explicitement.
# Lot P1 (§3) : [S3b] = « l'architecture suit un découpage autre que celui de référence » — le
# texte change (l'ancien disait « la période de référence n'est pas la plus récente publiée », ce
# qui se déclenchait aussi pour un exercice face à un cumul du MÊME découpage).
b.check("découpage ANTÉRIEUR" in valide_ou_motif(ARCH_10K),
        "[S3b] — signal : l'architecture suit le découpage du 10-K, antérieur au découpage de référence (10-Q)")

# [S4] : un bloc parent rattaché à un bloc COMMUN.
arch_s4_dict = ARCH_10K.model_dump(mode="json")
arch_s4_dict["blocs"] = arch_s4_dict["blocs"] + [
    {"id": "commun", "libelle": "Commun", "role": "commun", "statut": "metier_actuel",
     "origine": "interne", "maille": "estime",
     "rattachement": {"type": "agrege", "ligne": "autres_charges_exploitation"},
     "variables": ["couts_communs"], "motif": "Bloc commun de test, motif suffisant.", "pieces": [1]},
    {"id": "sous_commun", "libelle": "Sous-commun", "role": "activite", "statut": "metier_actuel",
     "origine": "interne", "maille": "estime", "rattachement": {"type": "parent", "bloc": "commun"},
     "variables": ["couts_communs"], "motif": "Bloc rattaché à un commun, motif suffisant.", "pieces": [1]},
]
ARCH_S4 = Architecture.model_validate(arch_s4_dict)
r = valide_ou_motif(ARCH_S4)
b.check(r.startswith("[S4]"), f"[S4] — bloc parent rattaché à un bloc commun refusé : {r[:250]}")

# [S5] : RVMD toute estimée (secteur_unique) — un bloc `publie` serait refusé.
MATIERE_RVMD = matiere_fictive(ticker_id="RVMD", raison_sociale="Revolution Medicines, Inc.",
                               cik=1628171, ventilation_structure=None,
                               periodes_historiques=("FY2021", "FY2022", "FY2023", "FY2024", "FY2025"),
                               periodes_projetees=tuple(f"FY{2025+i}" for i in range(1, 11)),
                               pieces_citables=frozenset({1, 2}),
                               me_7_verbatim="`me_7` décrit le Programme en développement X, en phase "
                                            "préclinique, nombre_de_programmes = 1.")
ARCH_RVMD = Architecture.model_validate({
    "schema_version": "architecture-1.3.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
    "famille": "industrielle", "version_referentiel": REF.version,
    "blocs": [
        {"id": "produit", "libelle": "Produit commercialisé", "role": "activite", "statut": "metier_actuel",
         "origine": "interne", "maille": "estime",
         "rattachement": {"type": "agrege", "ligne": "chiffre_affaires"},
         "variables": ["chiffre_affaires_du_bloc"], "motif": "RVMD n'a aucune ventilation publiée : "
         "le produit commercialisé est estimé, rattaché au chiffre d'affaires.", "pieces": [1]},
        {"id": "programme_x", "libelle": "Programme en développement X", "role": "programme",
         "statut": "en_developpement", "origine": "interne", "maille": "estime",
         "jalon": {"franchi": "preuve de concept préclinique", "franchi_le": "2026-01-15",
                   "prochain": "autorisation d'essai clinique de phase 1", "attendu_vers": "2027-01-15"},
         "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
         "variables": ["probabilite_de_succes"], "motif": "Programme en développement, ancré sur une "
         "classe de référence documentée en pièce.", "pieces": [1],
         "programmes": ["Programme en développement X"]},
    ],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "chiffre_affaires", "formule": "produit__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [
        {"bloc": "produit", "variable": "chiffre_affaires_du_bloc",
         "periodes": list(MATIERE_RVMD.periodes_projetees), "auteur": {"type": "demande_ciblee"}},
    ],
    "inventaire_des_programmes": [
        {"programme": "Programme en développement X", "traitement": "bloc", "bloc": "programme_x",
         "motif": "Nommé individuellement par `me_7`, en phase préclinique, sa propre ligne."},
    ],
})
r = valide_ou_motif(ARCH_RVMD, MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S5] — RVMD toute estimée (secteur_unique + programmes) tient : {r[:250]}")
ARCH_RVMD_PUBLIE_dict = ARCH_RVMD.model_dump(mode="json")
ARCH_RVMD_PUBLIE_dict["blocs"][0] = {**ARCH_RVMD_PUBLIE_dict["blocs"][0], "maille": "publie",
                                     "rattachement": {"type": "publie", "axe": "activites", "membres": ["x:M"]}}
ARCH_RVMD_PUBLIE = Architecture.model_validate(ARCH_RVMD_PUBLIE_dict)
r = valide_ou_motif(ARCH_RVMD_PUBLIE, MATIERE_RVMD)
b.check("[S5]" in r, f"[S5] — un bloc `publie` sur `secteur_unique` est refusé (avec [S1]/[S2] en "
                     f"cascade, puisqu'aucune ventilation n'existe pour en fonder l'adresse) : {r[:300]}")

# [S6] : une pièce hors du dossier.
ARCH_S6_dict = ARCH_RVMD.model_dump(mode="json")
ARCH_S6_dict["blocs"][0]["pieces"] = [999999]
r = valide_ou_motif(Architecture.model_validate(ARCH_S6_dict), MATIERE_RVMD)
b.check(r.startswith("[S6]"), f"[S6] — pièce hors du dossier refusée : {r[:250]}")

# [S4] (sous-cas 2) : un bloc `agrege` vise une ligne HORS du business plan de la famille.
ARCH_S4B_dict = ARCH_RVMD.model_dump(mode="json")
ARCH_S4B_dict["blocs"][0]["rattachement"] = {"type": "agrege", "ligne": "ligne_hors_business_plan"}
r = valide_ou_motif(Architecture.model_validate(ARCH_S4B_dict), MATIERE_RVMD)
b.check(r.startswith("[S4]"), f"[S4] — bloc agrege hors du business plan refusé : {r[:250]}")

# [S9] (sous-cas 1) : une cellule attendue hors des périodes du classeur.
ARCH_S9B_dict = ARCH_10K.model_dump(mode="json")
ARCH_S9B_dict["cellules_attendues"][0]["periodes"] = ["FY9999"]
r = valide_ou_motif(Architecture.model_validate(ARCH_S9B_dict))
b.check(r.startswith("[S9]") and "FY9999" in r, f"[S9] — période hors du classeur refusée : {r[:250]}")

# [S7] : un bloc de chiffre d'affaires OUBLIÉ dans la formule de passage.
ARCH_S7_dict = ARCH_10K.model_dump(mode="json")
ARCH_S7_dict["passage_a_l_agrege"] = [{"ligne": "chiffre_affaires", "formule": " + ".join(
    f"{bid}__chiffre_affaires_du_bloc" for bid, _ in SEGS_10K[:-1])}]  # oem oublié
r = valide_ou_motif(Architecture.model_validate(ARCH_S7_dict))
b.check(r.startswith("[S7]") and "oem" in r, f"[S7] — bloc oublié dans l'agrégé refusé : {r[:250]}")

# [S7] (sous-cas 2) : AUCUNE formule de passage ne porte la ligne `chiffre_affaires`.
ARCH_S7B_dict = ARCH_10K.model_dump(mode="json")
ARCH_S7B_dict["passage_a_l_agrege"] = [
    {"ligne": "autres_charges_exploitation", "formule": "data_center__chiffre_affaires_du_bloc"}]
r = valide_ou_motif(Architecture.model_validate(ARCH_S7B_dict))
b.check(r.startswith("[S7]") and "aucune formule" in r,
        f"[S7] — aucune formule ne porte la ligne chiffre_affaires, refusé : {r[:250]}")

# [S8] : une extension annoncée comptée dans UNE formule de passage — sur une ligne DIFFÉRENTE de
# `chiffre_affaires` (une variable sans `somme_vers_ligne`), pour isoler [S8] de [S7] (qui refuserait
# de toute façon toute formule `chiffre_affaires` citant un bloc `extension_annoncee`, §5 : le
# vocabulaire « bloc de chiffre d'affaires » exclut ce statut par construction).
ARCH_S8_dict = ARCH_10K.model_dump(mode="json")
ARCH_S8_dict["blocs"].append({
    "id": "extension_x", "libelle": "Extension annoncée", "role": "activite", "statut": "extension_annoncee",
    "origine": "interne", "maille": "estime",
    "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
    "variables": ["taille_du_marche"], "motif": "Extension annoncée de test, motif suffisant.",
    "pieces": [1]})
ARCH_S8_dict["passage_a_l_agrege"].append(
    {"ligne": "recherche_developpement", "formule": "extension_x__taille_du_marche"})
r = valide_ou_motif(Architecture.model_validate(ARCH_S8_dict))
b.check(r.startswith("[S8]"), f"[S8] — extension annoncée comptée dans une formule de passage refusée : {r[:250]}")

# [S9] : une cellule attendue qui ne couvre pas toutes les périodes projetées.
ARCH_S9_dict = ARCH_10K.model_dump(mode="json")
ARCH_S9_dict["cellules_attendues"][0]["periodes"] = ARCH_S9_dict["cellules_attendues"][0]["periodes"][:-1]
r = valide_ou_motif(Architecture.model_validate(ARCH_S9_dict))
b.check(r.startswith("[S9]"), f"[S9] — période projetée non couverte refusée : {r[:250]}")

# ── [S10] (1.2.0, cause ①) : un axe de la ventilation sans bloc publié ET sans `autres_axes`. ───
ARCH_S10_dict = ARCH_10K.model_dump(mode="json")
ARCH_S10_dict["autres_axes"] = [a for a in ARCH_S10_dict["autres_axes"] if a["axe"] != "secteurs"]
r = valide_ou_motif(Architecture.model_validate(ARCH_S10_dict))
b.check(r.startswith("[S10]") and "secteurs" in r,
        f"[S10] — axe `secteurs` sans bloc publié ET sans usage déclaré, refusé : {r[:250]}")
b.check(ARCH_10K.autres_axes and valide_ou_motif(ARCH_10K).startswith("OK"),
        "[S10] — ARCH_10K (tous les autres axes déclarés en `autres_axes`) tient")

# ── [S11] (1.2.0, cause ④) : les formules de passage sont TYPÉES (dimension, échelle, période). ─
# Blocs fictifs isolés (RattachementAgrege sur une ligne sans `somme_vers_ligne`, pour que [S7] ne
# s'en mêle pas — seules les variables PORTANT `somme_vers_ligne` entrent dans son vocabulaire).
_BLOC_A = {"id": "a", "libelle": "A", "role": "commun", "statut": "metier_actuel", "origine": "interne",
          "maille": "estime", "rattachement": {"type": "agrege", "ligne": "autres_charges_exploitation"},
          "variables": ["taille_du_marche", "part_de_marche", "volume", "prix_moyen"],
          "motif": "Bloc fictif de test [S11], motif de longueur suffisante pour le contrat.", "pieces": [1]}


def arch_s11(formule: str, ligne: str = "autres_charges_exploitation") -> Architecture:
    return Architecture.model_validate({
        "schema_version": "architecture-1.3.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
        "famille": "industrielle", "version_referentiel": REF.version, "blocs": [_BLOC_A],
        "variables_propres": [], "passage_a_l_agrege": [{"ligne": ligne, "formule": formule}],
        "cellules_attendues": [
            {"bloc": "a", "variable": v, "periodes": ["sans_periode"] if v == "part_de_marche" else
             list(MATIERE_RVMD.periodes_projetees), "auteur": {"type": "demande_ciblee"}}
            for v in ("taille_du_marche", "volume", "prix_moyen")] + [
            {"bloc": "a", "variable": "part_de_marche", "periodes": list(MATIERE_RVMD.periodes_projetees),
             "auteur": {"type": "demande_ciblee"}}],
    })


r = valide_ou_motif(arch_s11("a__taille_du_marche + a__part_de_marche"), MATIERE_RVMD)
b.check("[S11]" in r, f"[S11] — somme M$ + % refusée (dimension/échelle incohérente) : {r[:300]}")

r = valide_ou_motif(arch_s11("a__volume * a__prix_moyen"), MATIERE_RVMD)
b.check("[S11]" in r and "échelle" in r,
        f"[S11] — produit volume × prix_moyen SANS `/ 1000000` refusé (échelle 1 ≠ 10⁶) : {r[:300]}")

r = valide_ou_motif(arch_s11("a__volume * a__prix_moyen / 1000000"), MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S11] — produit volume × prix_moyen AVEC `/ 1000000` tient : {r[:300]}")

# Un littéral qui n'est PAS un rapport d'échelles de la table est un COEFFICIENT, neutre (une
# décote, une moitié) ; un littéral qui l'est (`/ 100`, `/ 1000000`) est une conversion d'unité.
r = valide_ou_motif(arch_s11("a__taille_du_marche * 0.9 + a__taille_du_marche / 2"), MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S11] — coefficients `* 0.9` et `/ 2` sur des M$ : même échelle, tient : {r[:300]}")

r = valide_ou_motif(arch_s11("a__taille_du_marche * a__part_de_marche / 100"), MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S11] — M$ × % ramené par `/ 100` (conversion de la table) tient : {r[:300]}")

r = valide_ou_motif(arch_s11("a__taille_du_marche * a__part_de_marche"), MATIERE_RVMD)
b.check("[S11]" in r, f"[S11] — M$ × % SANS `/ 100` refusé (échelle 10⁴ ≠ 10⁶) : {r[:300]}")

r = valide_ou_motif(arch_s11("a__taille_du_marche"), MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S11] — une seule variable M$ sur une ligne `flux` tient (facteur "
                           f"`exercice` présent) : {r[:300]}")

r = valide_ou_motif(arch_s11("a__taille_du_marche", ligne="capital_employe"), MATIERE_RVMD)
b.check("[S11]" in r, f"[S11] — une variable `exercice` (taille_du_marche) sur une ligne `instant` "
                     f"(`capital_employe`) refusée : {r[:300]}")

# Stock (`cout_restant_de_developpement`, M$, `sans_periode`) dans une ligne ANNUELLE — le cas
# nommé par la spec (§5, cause ④) : « …__cout_restant_de_developpement dans une ligne annuelle ».
_BLOC_B = {**_BLOC_A, "id": "b", "variables": ["cout_restant_de_developpement"]}


def arch_s11_b(formule: str, ligne: str) -> Architecture:
    return Architecture.model_validate({
        "schema_version": "architecture-1.3.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
        "famille": "industrielle", "version_referentiel": REF.version, "blocs": [_BLOC_B],
        "variables_propres": [], "passage_a_l_agrege": [{"ligne": ligne, "formule": formule}],
        "cellules_attendues": [{"bloc": "b", "variable": "cout_restant_de_developpement",
                               "periodes": ["sans_periode"], "auteur": {"type": "demande_ciblee"}}],
    })


r = valide_ou_motif(arch_s11_b("b__cout_restant_de_developpement", "recherche_developpement"), MATIERE_RVMD)
b.check("[S11]" in r and "période" in r.lower(),
        f"[S11] — stock `sans_periode` dans une ligne `flux` annuelle refusé : {r[:300]}")

# Un facteur `sans_periode` est NEUTRE dans un produit : multiplié par une variable `exercice`
# (`taille_du_marche`), le terme a bien un facteur `exercice` — tient.
_BLOC_C = {**_BLOC_A, "id": "c", "variables": ["cout_restant_de_developpement", "taille_du_marche"]}
arch_c = Architecture.model_validate({
    "schema_version": "architecture-1.3.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
    "famille": "industrielle", "version_referentiel": REF.version, "blocs": [_BLOC_C],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "recherche_developpement",
                           "formule": "c__taille_du_marche"}],
    "cellules_attendues": [
        {"bloc": "c", "variable": "taille_du_marche", "periodes": list(MATIERE_RVMD.periodes_projetees),
         "auteur": {"type": "demande_ciblee"}},
        {"bloc": "c", "variable": "cout_restant_de_developpement", "periodes": ["sans_periode"],
         "auteur": {"type": "demande_ciblee"}}],
})
r = valide_ou_motif(arch_c, MATIERE_RVMD)
b.check(r.startswith("OK"), f"[S11] — une seule variable `exercice` sur une ligne `flux` tient : {r[:300]}")

# ── Les 4 architectures à blanc du 2026-10-22, REJOUÉES sous 1.2.0 (§7 de la spec M3 bis) ───────
# Converties au plus proche (`membre`→`membres`, `origine` posée, `jalon` ajouté si manquant) dans
# `checks/fixtures/architecte/2026-10-22/*_converti.json` — chacune refusée par la règle de SA
# cause. `nvda_1_corrige.json` : la MÊME architecture, l'axe `activites` déclaré en `autres_axes`
# et les blocs de marché retirés de l'arbre — elle, passe.
print("§6bis les 4 architectures du 2026-10-22, rejouées sous 1.2.0")
FIX_ARCH = Path(__file__).resolve().parent / "fixtures" / "architecte" / "2026-10-22"
MATIERE_NVDA_COMPLETE = matiere_fictive(
    ticker_id="NVDA", raison_sociale="NVIDIA Corp", cik=1045810,
    periodes_historiques=("FY2022", "FY2023", "FY2024", "FY2025", "FY2026"),
    periodes_projetees=tuple(f"FY{2026+i}" for i in range(1, 11)),
    ventilation_structure=STRUCT_NVDA, socle_structure=SOCLE_STRUCT_NVDA,
    socle_piece_id=1, ventilation_piece_id=2, pieces_citables=frozenset(range(800, 1100)),
    # `me_7` (fixture M3 bis, conversion 1.2.0→1.3.0) mentionne l'acquisition de Hugging Face,
    # nommée par le bloc `en_developpement_hugging_face` de ces fixtures ([S14]).
    me_7_verbatim="`me_7` (test) décrit le projet Hugging Face integration, en développement.")


def rejoue_fixture(nom: str, matiere) -> str:
    raw = json.loads((FIX_ARCH / nom).read_text(encoding="utf-8"))
    try:
        arch = Architecture.model_validate(raw)
    except Exception as e:  # noqa: BLE001 — un refus de CONTRAT, pas de structure
        return f"REFUS DU CONTRAT : {e}"
    return valide_ou_motif(arch, matiere)

r = rejoue_fixture("nvda_1_converti.json", MATIERE_NVDA_COMPLETE)
b.check("[S10]" in r and "activites" in r,
        f"nvda_1 convertie 1.2.0 — refusée par [S10] (axe `activites` sans bloc publié ET sans "
        f"usage déclaré) : {r[:300]}")

r = rejoue_fixture("nvda_1_corrige.json", MATIERE_NVDA_COMPLETE)
b.check(r.startswith("OK"),
        f"nvda_1 CORRIGÉE (axe `activites` en `autres_axes`, marchés retirés de l'arbre) — tient : {r[:300]}")

r = rejoue_fixture("nvda_2_converti.json", MATIERE_NVDA_COMPLETE)
b.check("[S10]" in r,
        f"nvda_2 convertie 1.2.0 — refusée par [S10] (mêmes axes oubliés que nvda_1) : {r[:300]}")

# nvda_2, variante : Networking et Data Center cités PAR ADRESSE (publié), comme le passage 2 les
# aurait montrés frères — exactement le double-axe nommé par la spec (§7).
r = rejoue_fixture("nvda_2_s3.json", MATIERE_NVDA_COMPLETE)
b.check("[S3]" in r and "plusieurs axes" in r,
        f"nvda_2 (Networking/Data Center cités par adresse, publiés) — refusée par [S3], plusieurs "
        f"axes au premier niveau (`secteurs` et `activites`) : {r[:300]}")

r = rejoue_fixture("rvmd_1_converti.json", MATIERE_RVMD)
b.check(r.startswith("OK") or "[S11]" in r,
        f"rvmd_1 convertie 1.2.0 (jalon ajouté par la conversion) — contrat tient, structure jugée "
        f"par [S11] le cas échéant : {r[:300]}")

# RVMD — la conversion a ajouté le `jalon` requis par le contrat (cause ⑤), ce qui laisse la
# formule de passage `recherche_developpement = programmes_precliniques__cout_restant_de_
# developpement` seule en cause : un STOCK (`sans_periode`) dans une ligne ANNUELLE — exactement
# la cause ④ mesurée le 2026-10-22.
raw_rvmd1 = json.loads((FIX_ARCH / "rvmd_1_converti.json").read_text(encoding="utf-8"))
arch_rvmd1 = Architecture.model_validate(raw_rvmd1)
formule_rd = next(p.formule for p in arch_rvmd1.passage_a_l_agrege if p.ligne == "recherche_developpement")
b.check("cout_restant_de_developpement" in formule_rd,
        f"rvmd_1 — la formule de passage `recherche_developpement` lit bien le stock sans période "
        f"(cause ④ mesurée le 2026-10-22) : {formule_rd}")
r = valide_ou_motif(arch_rvmd1, MATIERE_RVMD)
b.check("[S11]" in r,
        f"rvmd_1 convertie 1.2.0 — [S11] refuse le stock `cout_restant_de_developpement` "
        f"(sans_periode) dans la ligne annuelle `recherche_developpement` : {r[:300]}")

r = rejoue_fixture("rvmd_2_converti.json", MATIERE_RVMD)
b.check("[S11]" in r, f"rvmd_2 convertie 1.2.0 — même cause ④ que rvmd_1, refusée par [S11] : {r[:300]}")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§7 le renvoi")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
import asyncio  # noqa: E402

from app.modele_entreprise import architecte as arc_mod  # noqa: E402


class FauxCompletion:
    def __init__(self, content):
        self.content = content
        self.model = "faux-modele"
        self.tokens_in = 10
        self.tokens_out = 10
        self.cost_usd = 0.001


class FauxProvider:
    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = 0

    async def complete(self, messages, **kw):
        self.appels += 1
        contenu = self.reponses.pop(0)
        return FauxCompletion(contenu)


def faux_agent(reponses):
    from app.agents.providers import ResolvedAgent
    return ResolvedAgent(agent_name="faux", flow_version="v2", provider=FauxProvider(reponses),
                         model="faux-modele", system_prompt="x")


# Schema-VALIDE (passe `ArchitecteSortie`), mais refusée par le PONT/[S1] (membre inventé, absent de
# la ventilation de `matiere_fictive()`) — c'est CE refus que le renvoi de l'architecte doit rejouer,
# pas une réparation de JSON malformé (celle-ci est déjà le rôle interne de `run_json_agent`).
_EXEMPLE_AVEC_MEMBRE_INVENTE = json.loads(json.dumps(_EXEMPLE_ARCHITECTURE))
_EXEMPLE_AVEC_MEMBRE_INVENTE["blocs"][0]["rattachement"]["membres"] = ["fictif:MembreInventeMember"]
SORTIE_INVALIDE = json.dumps(_EXEMPLE_AVEC_MEMBRE_INVENTE)
SORTIE_VALIDE = json.dumps(_EXEMPLE_ARCHITECTURE)


async def _proposer_sans_db(reponses, *, hors_porte=True):
    """Exerce `proposer_architecture_du_titre` jusqu'à l'appel modèle SANS base ni réseau : on
    monkeypatch `charger_etat_dossier`/`charger_matiere`/`prochaine_version` pour isoler la
    plomberie du renvoi (#7), seule ciblée ici — la lecture réelle est éprouvée par ailleurs
    (step 0/2 de la mesure, `checks/check_architecture_persist.py`)."""
    agent = faux_agent(reponses)

    class FauxEtat:
        archetype = "rentable"

    async def _fake_etat_dossier(conn, ticker_id):
        return FauxEtat()

    async def _fake_matiere(conn, ticker_id, *, publier):
        # `_EXEMPLE_ARCHITECTURE` nomme « Programme X » ([S14]) — la matière factice doit le
        # porter dans son verbatim de `me_7` pour que la sortie VALIDE de ce test le reste.
        return matiere_fictive(me_7_verbatim="`me_7` (test du renvoi) décrit le Programme X.")

    async def _fake_prochaine_version(conn, ticker_id):
        return 1

    class _FakeConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _FakeSession:
        def __call__(self):
            return _FakeConn()

    old_porte = arc_mod.porte_de_l_architecte
    arc_mod.porte_de_l_architecte = lambda etat, ref: Porte(ouverte=True, archetype="rentable", questions=())
    old_charger_matiere = arc_mod.charger_matiere
    arc_mod.charger_matiere = _fake_matiere
    old_prochaine = arc_mod.prochaine_version
    arc_mod.prochaine_version = _fake_prochaine_version
    import app.agents.v2.parcours as pmod
    old_ced = pmod.charger_etat_dossier
    pmod.charger_etat_dossier = _fake_etat_dossier
    import app.db.database as dbmod
    old_sess = dbmod.get_db_session
    dbmod.get_db_session = _FakeSession()
    try:
        return await arc_mod.proposer_architecture_du_titre("FICTIF", agent=agent, hors_porte=hors_porte), agent
    finally:
        arc_mod.porte_de_l_architecte = old_porte
        arc_mod.charger_matiere = old_charger_matiere
        arc_mod.prochaine_version = old_prochaine
        pmod.charger_etat_dossier = old_ced
        dbmod.get_db_session = old_sess


resultat, agent = asyncio.run(_proposer_sans_db([SORTIE_INVALIDE, SORTIE_VALIDE]))
b.check(resultat.architecture is not None and agent.provider.appels == 2,
        f"renvoi — sortie refusée puis valide → acceptée après 2 appels (obtenu {agent.provider.appels})")
b.check(resultat.run.cost_usd > 0 and resultat.run.attempts >= 2,
        f"renvoi — coût cumulé sur les deux appels (cost={resultat.run.cost_usd}, attempts={resultat.run.attempts})")

try:
    asyncio.run(_proposer_sans_db([SORTIE_INVALIDE, SORTIE_INVALIDE]))
    b.check(False, "renvoi — deux refus successifs : devait lever `ArchitectureRefusee`")
except ArchitectureRefusee as e:
    b.check(e.attempts >= 2, f"renvoi — deux refus → `ArchitectureRefusee` avec motifs et coût cumulé : {e}")


async def _porte_fermee():
    agent = faux_agent([SORTIE_VALIDE])

    class FauxEtatFerme:
        archetype = "rentable"

    async def _fake_etat_dossier(conn, ticker_id):
        return FauxEtatFerme()

    class _FakeConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class _FakeSession:
        def __call__(self):
            return _FakeConn()

    old_porte = arc_mod.porte_de_l_architecte
    arc_mod.porte_de_l_architecte = lambda etat, ref: Porte(
        ouverte=False, archetype="rentable",
        questions=(EtatQuestionSource("q1", "fw", False, "aucune réponse instruite"),))
    import app.agents.v2.parcours as pmod
    old_ced = pmod.charger_etat_dossier
    pmod.charger_etat_dossier = _fake_etat_dossier
    import app.db.database as dbmod
    old_sess = dbmod.get_db_session
    dbmod.get_db_session = _FakeSession()
    try:
        await arc_mod.proposer_architecture_du_titre("FICTIF", agent=agent, hors_porte=False)
    finally:
        arc_mod.porte_de_l_architecte = old_porte
        pmod.charger_etat_dossier = old_ced
        dbmod.get_db_session = old_sess
    return agent


try:
    agent_ferme = asyncio.run(_porte_fermee())
    b.check(False, "porte fermée — devait lever `PorteFermee` avant tout appel")
except PorteFermee:
    b.check(True, "porte fermée — `PorteFermee` levée AVANT toute dépense")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§8 le service de signature")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
from app.contracts.architecture_signature_schema import DecisionArchitecture, VersionArchitecture  # noqa: E402

V1 = VersionArchitecture(id=1, ticker_id="T", version=1, auteur="architecte (test)",
                         propose_le=datetime.now(timezone.utc), architecture=ARCH_10K.model_copy(
                             update={"ticker_id": "T"}))
V2 = VersionArchitecture(id=2, ticker_id="T", version=2, auteur="architecte (test)",
                         propose_le=datetime.now(timezone.utc), architecture=ARCH_10K.model_copy(
                             update={"ticker_id": "T", "version": 2}))


def juger_tient(_a):
    return True, "", ()


def juger_ne_tient_pas(_a):
    return False, "motif de refus", ()


s = servir_architecture("T", [], [], juger=juger_tient, interrupteur=True)
b.check(s.etat == "aucune_proposee", "service — rien proposé : `aucune_proposee`")

s = servir_architecture("T", [V1], [], juger=juger_tient, interrupteur=True)
b.check(s.etat == "en_attente_de_signature" and s.en_attente.signable,
        "service — en attente de signature")

s = servir_architecture("T", [V1, V2], [], juger=juger_tient, interrupteur=True)
b.check(s.en_attente.version.version == 2, "service — v1 REMPLACÉE par v2, v2 en attente")

D1 = DecisionArchitecture(id=1, architecture_id=1, ticker_id="T", version=1, action="signer",
                          auteur="comité", motif="motif test", signaux=[],
                          decide_le=datetime.now(timezone.utc))
s = servir_architecture("T", [V1], [D1], juger=juger_tient, interrupteur=True)
b.check(s.etat == "signee" and s.signee.etat == "tient", "service — signée, tient")

s = servir_architecture("T", [V1], [D1], juger=juger_ne_tient_pas, interrupteur=True)
b.check(s.signee.etat == "a_revoir" and s.en_vigueur.version is None,
        f"service — signée mais ne tient plus (à revoir), rien en vigueur : {s.en_vigueur.motif}")

s = servir_architecture("T", [V1], [], juger=juger_tient, interrupteur=False)
b.check(s.en_vigueur.version is not None and s.en_vigueur.version.version == 1,
        "service — interrupteur `false` : la dernière proposée qui tient, SANS signature, en vigueur")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§9 réplicabilité")
# ═══════════════════════════════════════════════════════════════════════════════════════════════
TICKERS_REGEX = ("NVDA", "RVMD", "NVIDIA", "Revolution Medicines")
fichiers_a_grepper = sorted(MODULE_DIR.glob("*.py"))
fichiers_lus = 0
for chemin in fichiers_a_grepper:
    source = chemin.read_text(encoding="utf-8")
    depouille = strip_code(source)
    fichiers_lus += 1
    for motif in TICKERS_REGEX:
        b.check(motif not in depouille,
                f"réplicabilité — `{chemin.relative_to(ROOT)}` ne nomme pas `{motif}` (hors "
                "commentaires/docstrings)")
b.check(fichiers_lus > 0, "réplicabilité — au moins un fichier a été lu (pas de vert sur liste vide)")

# Test NÉGATIF du grep lui-même (#feedback_grep_interdit_lit_sa_propre_enonciation) : un fichier qui
# EN CONTIENT UN (hors commentaire) doit faire rougir la même assertion si on la rejoue sur lui.
_source_test = "x = 'NVDA'\n"
_depouille_test = strip_code(_source_test)
b.check("NVDA" in _depouille_test,
        "réplicabilité — le dépouillement laisse bien passer un ticker en code réel (sanity du grep)")

# ═══════════════════════════════════════════════════════════════════════════════════════════════
print("§10 lot M3 ter — [S13]-[S15], §3 (jamais de plantage), §2 (pièces citables), §5 ([P4]), §6 "
     "(péremption)")
# ═══════════════════════════════════════════════════════════════════════════════════════════════

# ── [S13] (contrat, invariant d'UN SEUL objet — #37, même précédent que [S12]) ───────────────────


def _bloc_dev(**over) -> dict:
    base = {"id": "p", "libelle": "Programme", "role": "programme", "statut": "en_developpement",
           "origine": "interne",
           "jalon": {"franchi": "preuve de concept", "franchi_le": "2026-01-01",
                     "prochain": "jalon suivant", "attendu_vers": "2027-01-01"},
           "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
           "variables": ["probabilite_de_succes"], "motif": "Motif de test [S13], assez long.",
           "pieces": [1], "programmes": ["Molécule Test"]}
    base.update(over)
    return base


BlocPropose.model_validate(_bloc_dev())
b.check(True, "[S13] — bloc `en_developpement` non plateforme, UN programme nommé : tient")

try:
    BlocPropose.model_validate(_bloc_dev(programmes=["Molécule A", "Molécule B"]))
    b.check(False, "[S13] — deux programmes sur un bloc non plateforme devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("[S13]" in str(e), f"[S13] — deux programmes refusés : {e}")

try:
    BlocPropose.model_validate(_bloc_dev(programmes=[]))
    b.check(False, "[S13] — zéro programme sur un bloc `en_developpement` non plateforme devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("[S13]" in str(e), f"[S13] — zéro programme refusé : {e}")

BlocPropose.model_validate(_bloc_dev(programmes=[], plateforme=True, nombre_de_programmes_non_nommes=3))
b.check(True, "[S13] — bloc `plateforme` (programmes vide, nombre_de_programmes_non_nommes=3) : tient")

try:
    BlocPropose.model_validate(_bloc_dev(plateforme=True, nombre_de_programmes_non_nommes=3))
    b.check(False, "[S13] — plateforme avec des `programmes` nommés devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("programmes" in str(e).lower(), f"[S13] — plateforme avec programmes nommés refusée : {e}")

try:
    BlocPropose.model_validate(_bloc_dev(programmes=[], plateforme=True))
    b.check(False, "[S13] — plateforme SANS `nombre_de_programmes_non_nommes` devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("nombre_de_programmes_non_nommes" in str(e),
            f"[S13] — plateforme sans compte refusée : {e}")

try:
    BlocPropose.model_validate(_bloc_dev(statut="metier_actuel", jalon=None, programmes=["Molécule A"]))
    b.check(False, "[S13] — `programmes` sur un bloc `metier_actuel` devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("réservé aux blocs" in str(e), f"[S13] — programmes hors `en_developpement` refusés : {e}")

# ── Cas fictifs §4/§7 de la spec (AUCUN nom réel) : un laboratoire à 6 programmes nommés + une
# plateforme de recherche amont ; société technologique dont la génération suivante est `rattache`.
MATIERE_LABO = matiere_fictive(
    ticker_id="FICTIF2", raison_sociale="Laboratoire Fictif SA", ventilation_structure=None,
    periodes_historiques=("FY2024", "FY2025"), periodes_projetees=("FY2026", "FY2027"),
    pieces_citables=frozenset({1}),
    me_7_verbatim="`me_7` (test) nomme six programmes : Molécule Alpha, Molécule Beta, Molécule "
                 "Gamma, Molécule Delta, Molécule Epsilon et Molécule Zeta ; nombre_de_programmes = 6.",
    me_7_nombre_de_programmes=6.0)
MOLECULES = ["Molécule Alpha", "Molécule Beta", "Molécule Gamma", "Molécule Delta", "Molécule Epsilon",
            "Molécule Zeta"]


def _bloc_molecule(i: int, nom: str) -> dict:
    return {"id": f"programme_{i}", "libelle": nom, "role": "programme", "statut": "en_developpement",
           "origine": "interne", "maille": "estime",
           "jalon": {"franchi": "preuve de concept", "franchi_le": "2026-01-01",
                     "prochain": "jalon suivant", "attendu_vers": "2027-01-01"},
           "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
           "variables": ["probabilite_de_succes"], "motif": f"{nom}, nommée individuellement par "
           "`me_7`, réussite incertaine.", "pieces": [1], "programmes": [nom]}


# Un bloc COMMUN, hors de tout programme, pour porter la formule de passage obligatoire
# (`passage_a_l_agrege` exige ≥ 1 ligne) sans entraîner les variables `probabilite_de_succes`
# (sans dimension M$) dans [S11]/[S7] — même patron que `_EXEMPLE_ARCHITECTURE`.
_COMMUN_LABO = {"id": "commun", "libelle": "Frais communs", "role": "commun", "statut": "metier_actuel",
               "origine": "interne", "maille": "estime",
               "rattachement": {"type": "agrege", "ligne": "autres_charges_exploitation"},
               "variables": ["couts_communs"], "motif": "Bloc commun de test, motif suffisant.",
               "pieces": [1]}


def _arch_labo(blocs: list[dict], inventaire: list[dict]) -> dict:
    return {"schema_version": "architecture-1.3.0", "ticker_id": "FICTIF2", "version": 1,
           "archetype": "rentable", "famille": "industrielle", "version_referentiel": REF.version,
           "blocs": blocs + [_COMMUN_LABO], "variables_propres": [],
           "passage_a_l_agrege": [{"ligne": "autres_charges_exploitation", "formule": "commun__couts_communs"}],
           "cellules_attendues": [
               {"bloc": blocs[0]["id"], "variable": "probabilite_de_succes", "periodes": ["sans_periode"],
                "auteur": {"type": "question", "question_id": "me_7"}},
               {"bloc": "commun", "variable": "couts_communs", "periodes": ["FY2026", "FY2027"],
                "auteur": {"type": "demande_ciblee"}}],
           "inventaire_des_programmes": inventaire}


INVENTAIRE_LABO = [
    {"programme": nom, "traitement": "bloc", "bloc": f"programme_{i}",
     "motif": f"{nom} nommée individuellement, sa propre ligne."}
    for i, nom in enumerate(MOLECULES)]
BLOCS_LABO = [_bloc_molecule(i, nom) for i, nom in enumerate(MOLECULES)]
ARCH_LABO = Architecture.model_validate(_arch_labo(BLOCS_LABO, INVENTAIRE_LABO))
r = valide_ou_motif(ARCH_LABO, MATIERE_LABO)
b.check(r.startswith("OK"),
        f"cas fictif — laboratoire à 6 programmes nommés, UNE ligne chacun : tient : {r[:300]}")

# Mutation du cas fictif : les six molécules REGROUPÉES dans un seul bloc non plateforme — exactement
# le défaut mesuré sur RVMD 2 (2026-10-22) — refusé par [S13], au niveau du CONTRAT.
try:
    Architecture.model_validate(_arch_labo(
        [{**_bloc_molecule(0, MOLECULES[0]), "programmes": MOLECULES}], INVENTAIRE_LABO))
    b.check(False, "cas fictif — six molécules regroupées dans un bloc non plateforme devait être refusé")
except Exception as e:  # noqa: BLE001
    b.check("[S13]" in str(e), f"cas fictif — regroupement refusé par [S13] : {e}")

# [S14] — un programme inventé, absent du verbatim de `me_7`.
BLOCS_LABO_INVENTE = BLOCS_LABO + [_bloc_molecule(6, "Molécule Inventée")]
INVENTAIRE_INVENTE = INVENTAIRE_LABO + [
    {"programme": "Molécule Inventée", "traitement": "bloc", "bloc": "programme_6",
     "motif": "Molécule inventée pour le test [S14], absente du verbatim."}]
ARCH_LABO_INVENTE = Architecture.model_validate(_arch_labo(BLOCS_LABO_INVENTE, INVENTAIRE_INVENTE))
r = valide_ou_motif(ARCH_LABO_INVENTE, MATIERE_LABO)
b.check(r.startswith("[S14]") and "Molécule Inventée" in r,
        f"[S14] — programme absent du verbatim de `me_7` refusé : {r[:300]}")

# [S14] — un programme nommé dans l'inventaire mais jamais une ligne propre ni rattaché : le bloc
# `en_developpement` qui le porte n'apparaît dans AUCUNE entrée de l'inventaire.
ARCH_LABO_OUBLI = Architecture.model_validate(_arch_labo(BLOCS_LABO, INVENTAIRE_LABO[:-1]))
r = valide_ou_motif(ARCH_LABO_OUBLI, MATIERE_LABO)
b.check(r.startswith("[S14]") and "programme_5" in r,
        f"[S14] — bloc `en_developpement` absent de l'inventaire refusé : {r[:300]}")

# [S14] — l'inventaire désigne un bloc INEXISTANT.
INVENTAIRE_BLOC_INEXISTANT = [{**INVENTAIRE_LABO[0], "bloc": "bloc_fantome"}] + INVENTAIRE_LABO[1:]
ARCH_LABO_FANTOME = Architecture.model_validate(_arch_labo(BLOCS_LABO, INVENTAIRE_BLOC_INEXISTANT))
r = valide_ou_motif(ARCH_LABO_FANTOME, MATIERE_LABO)
b.check(r.startswith("[S14]") and "bloc_fantome" in r,
        f"[S14] — entrée d'inventaire désignant un bloc inexistant refusée : {r[:300]}")

# [S14] — aucun verbatim de `me_7` disponible (matière à blanc, sans réponse instruite).
MATIERE_LABO_SANS_VERBATIM = matiere_fictive(
    ticker_id="FICTIF2", ventilation_structure=None, pieces_citables=frozenset({1}))
r = valide_ou_motif(ARCH_LABO, MATIERE_LABO_SANS_VERBATIM)
b.check(r.startswith("[S14]") and "aucun verbatim" in r,
        f"[S14] — aucun verbatim disponible pour vérifier les programmes nommés : {r[:300]}")

# Cas fictif — société technologique dont la génération suivante d'un produit VENDU est `rattache`
# à son activité (pas un pari binaire isolé) : admis, l'inventaire le dit.
BLOC_ACTIVITE_TECH = {"id": "produit_historique", "libelle": "Produit historique", "role": "activite",
                     "statut": "metier_actuel", "origine": "interne", "maille": "estime",
                     "rattachement": {"type": "agrege", "ligne": "chiffre_affaires"},
                     "variables": ["chiffre_affaires_du_bloc"],
                     "motif": "Produit vendu de longue date, motif de longueur suffisante.", "pieces": [1]}
ARCH_TECH_RATTACHE = Architecture.model_validate({
    "schema_version": "architecture-1.3.0", "ticker_id": "FICTIF2", "version": 1, "archetype": "rentable",
    "famille": "industrielle", "version_referentiel": REF.version, "blocs": [BLOC_ACTIVITE_TECH],
    "variables_propres": [], "passage_a_l_agrege": [
        {"ligne": "chiffre_affaires", "formule": "produit_historique__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [
        {"bloc": "produit_historique", "variable": "chiffre_affaires_du_bloc",
         "periodes": ["FY2026", "FY2027"], "auteur": {"type": "demande_ciblee"}}],
    "inventaire_des_programmes": [
        {"programme": "Produit Nova", "traitement": "rattache", "bloc": "produit_historique",
         "motif": "Génération suivante du produit historique, pas un pari isolé : rattachée."}],
})
MATIERE_TECH = matiere_fictive(
    ticker_id="FICTIF2", ventilation_structure=None, pieces_citables=frozenset({1}),
    me_7_verbatim="`me_7` (test) annonce Produit Nova, génération suivante du produit historique.")
r = valide_ou_motif(ARCH_TECH_RATTACHE, MATIERE_TECH)
b.check(r.startswith("OK"),
        f"cas fictif — génération suivante `rattache` à son activité, admise, dite dans l'inventaire : "
        f"{r[:300]}")

# [S14] — traitement `rattache` qui désigne un bloc du MAUVAIS statut. On vise un second bloc
# `extension_annoncee` HORS de toute formule de passage (pour isoler [S14] de [S8], qui refuserait
# de toute façon toute formule `chiffre_affaires` référençant un bloc `extension_annoncee`, §5).
BLOC_EXT_TECH = {"id": "extension_tech", "libelle": "Extension annoncée", "role": "activite",
                "statut": "extension_annoncee", "origine": "interne", "maille": "estime",
                "rattachement": {"type": "agrege", "ligne": "recherche_developpement"},
                "variables": ["taille_du_marche"], "motif": "Extension de test [S14], motif suffisant.",
                "pieces": [1]}
ARCH_TECH_MAUVAIS_STATUT_dict = ARCH_TECH_RATTACHE.model_dump(mode="json")
ARCH_TECH_MAUVAIS_STATUT_dict["blocs"].append(BLOC_EXT_TECH)
ARCH_TECH_MAUVAIS_STATUT_dict["inventaire_des_programmes"][0]["bloc"] = "extension_tech"
r = valide_ou_motif(Architecture.model_validate(ARCH_TECH_MAUVAIS_STATUT_dict), MATIERE_TECH)
b.check(r.startswith("[S14]") and "metier_actuel" in r,
        f"[S14] — `rattache` vers un bloc qui n'est pas `metier_actuel` refusé : {r[:300]}")
b.check("GÉNÉRATION SUIVANTE" in r and "SA ligne" in r,
        f"[S14] — le motif de `rattache` mal placé dit la RÈGLE (génération suivante ; programme nommé = "
        f"sa ligne), pas seulement le statut attendu : {r[:500]}")

# ── [S15] ─────────────────────────────────────────────────────────────────────────────────────
r = valide_ou_motif(ARCH_LABO, MATIERE_LABO)
b.check("[S15]" not in r, f"[S15] — inventaire (6) ≥ chiffre clé (6) de `me_7` : aucun refus : {r[:300]}")

MATIERE_LABO_SOUS_CHIFFRE = matiere_fictive(
    ticker_id="FICTIF2", ventilation_structure=None, pieces_citables=frozenset({1}),
    me_7_verbatim=MATIERE_LABO.me_7_verbatim, me_7_nombre_de_programmes=8.0)
r = valide_ou_motif(ARCH_LABO, MATIERE_LABO_SOUS_CHIFFRE)
b.check(r.startswith("[S15]") and "8" in r,
        f"[S15] — inventaire (6) < chiffre clé (8) de `me_7` refusé : {r[:300]}")

# [S15] (2026-10-23, mesure `b4d-apres3/rvmd_2`) — le dossier COMPTE 8 programmes et en NOMME 6 : les
# deux non nommés vont dans une plateforme, qui compte — refuser obligerait à inventer un nom.
_PLATEFORME_LABO = {**_bloc_molecule(9, "inutilisé"), "id": "plateforme_amont", "libelle": "Recherche amont",
                    "programmes": [], "plateforme": True, "nombre_de_programmes_non_nommes": 2,
                    "motif": "Deux programmes comptés par le dossier, jamais nommés."}
ARCH_LABO_PLATEFORME = Architecture.model_validate(_arch_labo(BLOCS_LABO + [_PLATEFORME_LABO], INVENTAIRE_LABO))
r = valide_ou_motif(ARCH_LABO_PLATEFORME, MATIERE_LABO_SOUS_CHIFFRE)
b.check("[S15]" not in r,
        f"[S15] — 6 nommés + plateforme de 2 non nommés ≥ chiffre clé 8 : la plateforme couvre l'écart : {r[:300]}")

# [S14] (2026-10-23, mesure `b4d-apres3/rvmd_1`) — les six programmes NOMMÉS mis dans UNE plateforme,
# l'inventaire les déclarant tous « ligne propre » vers elle : le regroupement par la porte dérobée.
_PLATEFORME_FOURRE_TOUT = {**_PLATEFORME_LABO, "nombre_de_programmes_non_nommes": 6}
_inv_fourre_tout = [{**i, "bloc": "plateforme_amont"} for i in INVENTAIRE_LABO]
_cellule_plateforme = _arch_labo([_PLATEFORME_FOURRE_TOUT], _inv_fourre_tout)
r = valide_ou_motif(Architecture.model_validate(_cellule_plateforme), MATIERE_LABO)
b.check("[S14]" in r and "pas SA ligne propre" in r,
        f"[S14] — programmes nommés regroupés dans une plateforme : pas SA ligne propre, refusé : {r[:400]}")

MATIERE_LABO_SANS_CHIFFRE = matiere_fictive(
    ticker_id="FICTIF2", ventilation_structure=None, pieces_citables=frozenset({1}),
    me_7_verbatim=MATIERE_LABO.me_7_verbatim, me_7_nombre_de_programmes=None)
signaux_s15 = valider_structure(ARCH_LABO, REF, MATIERE_LABO_SANS_CHIFFRE)
b.check(any("[S15]" in s and "non chiffré" in s for s in signaux_s15),
        f"[S15] — chiffre clé non établi : signal « inventaire non chiffré », pas un refus : {signaux_s15}")

# ── §3 — jamais de plantage : un invariant du CONTRAT levé À L'ASSEMBLAGE (bloc estimé sans pièce,
# cause de RVMD 1 le 2026-10-22) suit le même chemin « refus nommé → renvoi » que [P]/[S], il ne
# fait plus tomber le script.
SORTIE_PLANTAGE = json.dumps({
    "blocs": [{
        "id": "bloc_sans_piece", "libelle": "Bloc sans pièce", "role": "activite",
        "statut": "metier_actuel", "origine": "interne",
        "rattachement": {"type": "agrege", "ligne": "chiffre_affaires"},
        "variables": ["chiffre_affaires_du_bloc"],
        "motif": "Bloc de test §3 (jamais de plantage), volontairement sans pièce.",
        "pieces": [],
    }],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "chiffre_affaires",
                           "formule": "bloc_sans_piece__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [{"bloc": "bloc_sans_piece", "variable": "chiffre_affaires_du_bloc",
                           "periodes": ["FY2026", "FY2027"], "auteur": {"type": "demande_ciblee"}}],
    "autres_axes": [{"axe": "activites", "usage": "Axe non repris par ce bloc de test, hors de l'arbre, "
                                                  "information secondaire."}],
})
_sortie_plantage_dict = json.loads(SORTIE_PLANTAGE)
_sortie_plantage_dict["blocs"][0] = {**_sortie_plantage_dict["blocs"][0], "pieces": [100]}
SORTIE_PLANTAGE_CORRIGEE = json.dumps(_sortie_plantage_dict)

try:
    asyncio.run(_proposer_sans_db([SORTIE_PLANTAGE, SORTIE_PLANTAGE]))
    b.check(False, "§3 — bloc estimé sans pièce, deux fois : devait lever `ArchitectureRefusee`, "
                   "jamais planter")
except ArchitectureRefusee as e:
    b.check("[ASSEMBLAGE]" in e.motifs and "pièce" in e.motifs,
            f"§3 — refus NOMMÉ à l'assemblage (plus de plantage), motifs : {e.motifs}")
    b.check(len(e.sorties) == 2, f"§3 — les DEUX sorties refusées sont gardées (pour `--sortie`) : "
                                 f"{len(e.sorties)}")
except Exception as e:  # noqa: BLE001
    b.check(False, f"§3 — PLANTAGE au lieu d'un refus nommé ({type(e).__name__}) : {e}")

try:
    resultat_plantage_corrige, _ = asyncio.run(
        _proposer_sans_db([SORTIE_PLANTAGE, SORTIE_PLANTAGE_CORRIGEE]))
    b.check(resultat_plantage_corrige.architecture is not None,
            "§3 — premier appel refusé à l'assemblage, second corrigé (pièce ajoutée) → accepté "
            "après renvoi, comme [P]/[S]")
except Exception as e:  # noqa: BLE001 — même garde que ci-dessus : un PLANTAGE est un FAIL nommé,
    # jamais un script mort avant son bilan (2ᵉ faux vert, `feedback_check_degrade_en_sortant_a_zero`).
    b.check(False, f"§3 — PLANTAGE au lieu d'un renvoi réussi après correction ({type(e).__name__}) : {e}")

# §3 (suite, 2026-10-23) — une sortie que le CONTRAT refuse au décodage (ici [S13], deux programmes
# sur un bloc non plateforme : défaut RVMD 2 du 2026-10-22), même après les réparations du runner,
# devient un refus NOMMÉ `[CONTRAT]`, sortie brute gardée — jamais une `AgentOutputInvalid` qui tue
# le bureau.
_sortie_s13 = json.loads(json.dumps(_EXEMPLE_ARCHITECTURE))
for _b in _sortie_s13["blocs"]:
    if _b.get("programmes"):
        _b["programmes"] = _b["programmes"] + ["Programme Y"]
SORTIE_HORS_CONTRAT = json.dumps(_sortie_s13)
try:
    asyncio.run(_proposer_sans_db([SORTIE_HORS_CONTRAT] * 8))
    b.check(False, "§3 — sortie hors contrat ([S13]) à chaque essai : devait lever `ArchitectureRefusee`")
except ArchitectureRefusee as e:
    b.check(e.motifs.startswith("[CONTRAT]") and "[S13]" in e.motifs and len(e.sorties) == 1,
            f"§3 — sortie hors contrat → refus NOMMÉ [CONTRAT], sortie gardée : {e.motifs[:200]} "
            f"({len(e.sorties)} sortie(s))")
except Exception as e:  # noqa: BLE001
    b.check(False, f"§3 — sortie hors contrat : PLANTAGE au lieu d'un refus nommé ({type(e).__name__}) : {e}")

# [S14] (suite, 2026-10-23, mesure `mesures/2026-10-23/b4d-apres/`) — casse, espaces et
# apostrophes typographiques ne changent pas un nom ; une PRÉCISION AJOUTÉE (marque entre
# parenthèses), si — et le motif dit alors comment corriger. Formes fictives.
_inv_casse = json.loads(json.dumps(INVENTAIRE_LABO))
_inv_casse[0]["programme"] = "molécule   ALPHA"
_blocs_casse = json.loads(json.dumps(BLOCS_LABO))
_blocs_casse[0]["programmes"] = ["molécule   ALPHA"]
r = valide_ou_motif(Architecture.model_validate(_arch_labo(_blocs_casse, _inv_casse)), MATIERE_LABO)
b.check("[S14]" not in r, f"[S14] — même nom, casse et espaces différents : admis : {r[:300]}")
_inv_parenth = json.loads(json.dumps(INVENTAIRE_LABO))
_inv_parenth[0]["programme"] = "Molécule Alpha (Marque Fictive)"
r = valide_ou_motif(Architecture.model_validate(_arch_labo(BLOCS_LABO, _inv_parenth)), MATIERE_LABO)
b.check(r.startswith("[S14]") and "Marque Fictive" in r and "passage CONTINU" in r,
        f"[S14] — nom avec précision ajoutée refusé, le motif dit de recopier un passage continu : {r[:400]}")

# Le RENDU de l'outil (`tools/architecte.py`) s'exécute sur une architecture qui tient — mesuré le
# 2026-10-23 : la première architecture NVDA acceptée a fait planter l'affichage (champ `membre`
# renommé `membres` en 1.2.0, chemin jamais exercé tant que rien n'était accepté). Le laboratoire
# fictif porte programmes + inventaire ; l'exemple du prompt porte des blocs publiés.
import importlib
_outil = importlib.import_module("tools.architecte")
for _nom_cas, _arch_cas in (("laboratoire fictif", ARCH_LABO),
                            ("exemple du prompt", resultat.architecture)):
    try:
        _rendu = "\n".join(_outil._rendre_architecture(_arch_cas))
        b.check(len(_rendu) > 0, f"rendu de l'outil — {_nom_cas} : s'affiche ({len(_rendu)} caractères)")
    except Exception as e:  # noqa: BLE001
        b.check(False, f"rendu de l'outil — {_nom_cas} : PLANTE ({type(e).__name__}) : {e}")
b.check("Inventaire des programmes" in "\n".join(_outil._rendre_architecture(ARCH_LABO)),
        "rendu de l'outil — l'inventaire des programmes est affiché")

# ── Cas RÉELS du 2026-10-23 (fixture copiée du réel, §7) — bornés aux règles neuves [S13]-[S15],
# qui ne lisent que l'arbre, l'inventaire et le verbatim de `me_7` (copié tel quel de la matière).
FIX_ARCH_23 = Path(__file__).resolve().parent / "fixtures" / "architecte" / "2026-10-23"
import app.modele_entreprise.structure as structure_mod  # noqa: E402
_me7_reel = json.loads((FIX_ARCH_23 / "rvmd_me_7.json").read_text(encoding="utf-8"))
MATIERE_RVMD_REELLE = matiere_fictive(ticker_id="RVMD", me_7_verbatim=_me7_reel["verbatim"],
                                      me_7_nombre_de_programmes=_me7_reel["nombre_de_programmes"])
try:
    _acc = Architecture.model_validate(
        json.loads((FIX_ARCH_23 / "rvmd_acceptee.json").read_text(encoding="utf-8"))["architecture"])
    _m14, (_m15, _) = structure_mod._s14(_acc, MATIERE_RVMD_REELLE), structure_mod._s15(_acc, MATIERE_RVMD_REELLE)
    b.check(_m14 is None and _m15 is None,
            f"cas réel — RVMD acceptée le 2026-10-23 (une ligne par molécule, plateforme du 8ᵉ) : "
            f"[S13]-[S15] tiennent : {_m14} / {_m15}")
except Exception as e:  # noqa: BLE001
    b.check(False, f"cas réel — RVMD acceptée : ne se relit plus sous le contrat ({type(e).__name__}) : {e}")
_ft = ArchitecteSortie.model_validate(
    json.loads((FIX_ARCH_23 / "rvmd_plateforme_fourre_tout.json").read_text(encoding="utf-8"))["sortie"])
_m14 = structure_mod._s14(_ft, MATIERE_RVMD_REELLE) or ""
b.check("pas SA ligne propre" in _m14 and "zoldonrasib" in _m14,
        f"cas réel — RVMD, six molécules nommées dans UNE plateforme : refusé par [S14] : {_m14[:300]}")

# ── §2 — les pièces citables, visibles (cause de NVDA 2) ────────────────────────────────────────
FaitPosterieurFake = SimpleNamespace(
    effet="L'usine annoncée le 2026-09-01 est désormais en construction, ce qui soutient le volume "
         "prévu à l'horizon FY2028.",
    cited_entry_ids=[900])
ReponseFake = SimpleNamespace(
    verbatim="Verbatim de test, écrit avant l'événement postérieur.", chiffres_cles=[], sens=None,
    faits_posterieurs=[FaitPosterieurFake], encadre_lisible=lambda: [])
FondationFake = SimpleNamespace(
    cited_entry_ids=[800], actualite="perimee",
    motif_actualite="fait daté du 2026-01-01, antérieur de 100 jours à l'événement matériel du "
                    "2026-04-01 (test §6). Il reste EXACT à sa date : périmé n'est pas faux.")
ServieFake = SimpleNamespace(framework_id="fw", question_id="q1", statut="repondu",
                             fondation=FondationFake, reponse=ReponseFake)
RFake = SimpleNamespace(servie=ServieFake, cree_le=None, verdict="acquitte", motif_revue=None,
                        answer_id=99)
EtatFake = SimpleNamespace(reponses=[RFake])
eq_fake = EtatQuestionSource("q1", "fw", True, "réponse #99 qui tient", answer_id=99)

old_reponse_tient = parcours_mod.reponse_tient
parcours_mod.reponse_tient = lambda r: True
try:
    texte_q, pieces_q, verbatim_q, nprog_q = matiere_mod._texte_question(eq_fake, EtatFake, {})
finally:
    parcours_mod.reponse_tient = old_reponse_tient

b.check("réponse R-99" in texte_q and "réponse #99" not in texte_q,
        f"§2 — un numéro de RÉPONSE s'écrit `réponse R-99`, jamais `#99`, dans la matière : {texte_q!r}")
b.check(pieces_q == frozenset({800, 900}),
        f"§2 — les pièces citées sont l'union de `fondation.cited_entry_ids` et des `faits_posterieurs` "
        f": {pieces_q}")
b.check("pièces :" in texte_q and "#800" in texte_q and "#900" in texte_q,
        f"§2 — la réponse rend ses pièces citables sous le verbatim : {texte_q!r}")

# ── §6 — la péremption au pied du verbatim (lu dans la même source que la ligne de porte) ───────
b.check("⚠ écrite avant un fait plus récent" in texte_q,
        f"§6 — avertissement de péremption posé AVANT le verbatim : {texte_q!r}")
b.check("le fait postérieur dit :" in texte_q and "en construction" in texte_q,
        f"§6 — le fait postérieur (`faits_posterieurs[].effet`) est cité dans l'avertissement : "
        f"{texte_q!r}")
idx_avert = texte_q.index("⚠ écrite avant")
idx_verbatim = texte_q.index("verbatim :")
b.check(idx_avert < idx_verbatim, "§6 — l'avertissement précède le verbatim")

# Une réponse COURANTE ne porte PAS cet avertissement.
FondationCouranteFake = SimpleNamespace(cited_entry_ids=[800], actualite="courante",
                                        motif_actualite="chaque pièce est dans la durée de vie de ce "
                                                        "qu'elle fonde (test).")
ServieCouranteFake = SimpleNamespace(framework_id="fw", question_id="q1", statut="repondu",
                                     fondation=FondationCouranteFake, reponse=ReponseFake)
RCouranteFake = SimpleNamespace(servie=ServieCouranteFake, cree_le=None, verdict="acquitte",
                                motif_revue=None, answer_id=100)
parcours_mod.reponse_tient = lambda r: True
try:
    texte_courant, *_ = matiere_mod._texte_question(
        eq_fake, SimpleNamespace(reponses=[RCouranteFake]), {})
finally:
    parcours_mod.reponse_tient = old_reponse_tient
b.check("⚠ écrite avant un fait plus récent" not in texte_courant,
        f"§6 — une réponse `courante` ne porte aucun avertissement de péremption : {texte_courant!r}")

# `rendre_matiere` — la section finale « Pièces que tu peux citer ».
M_PIECES = matiere_fictive(pieces_citables_texte="  · #100 — Titre de test")
txt_pieces = rendre_matiere(M_PIECES)
b.check("Pièces que tu peux citer" in txt_pieces and "#100 — Titre de test" in txt_pieces,
        "§2 — `rendre_matiere` porte la section finale « Pièces que tu peux citer »")

# [S6] — le motif RAPPELLE la liste des pièces citables (déjà refusé plus haut, §6 du fichier) :
# revérifié ici explicitement sur `matiere.pieces_citables` triée.
r_s6 = valide_ou_motif(Architecture.model_validate(ARCH_S6_dict), MATIERE_RVMD)
b.check("pièces citables :" in r_s6 and str(sorted(MATIERE_RVMD.pieces_citables)) in r_s6,
        f"[S6] — le motif de renvoi rappelle la liste exacte des pièces citables : {r_s6[:300]}")

# ── §5 — la période des variables reprises (cause de NVDA 1) : [P4] NOMME les périodes attendues.
ARCH_P4 = Architecture.model_validate({
    "schema_version": "architecture-1.3.0", "ticker_id": "FICTIF", "version": 1, "archetype": "rentable",
    "famille": "industrielle", "version_referentiel": REF.version,
    "blocs": [{"id": "x", "libelle": "X", "role": "activite", "statut": "metier_actuel",
              "origine": "interne", "maille": "estime",
              "rattachement": {"type": "agrege", "ligne": "chiffre_affaires"},
              "variables": ["chiffre_affaires_du_bloc"], "motif": "Bloc de test [P4], motif suffisant.",
              "pieces": [1]}],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "chiffre_affaires", "formule": "x__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [{"bloc": "x", "variable": "chiffre_affaires_du_bloc",
                           "periodes": ["sans_periode"], "auteur": {"type": "demande_ciblee"}}],
})
try:
    valider_pont_architecture(ARCH_P4, REF, ("FY2026", "FY2027"))
    b.check(False, "[P4] — `sans_periode` sur une variable `exercice` devait être refusé")
except PontRefusee as e:
    b.check("périodes attendues" in str(e) and "FY2026" in str(e) and "FY2027" in str(e),
            f"[P4] — le message de renvoi NOMME les périodes attendues : {e}")

try:
    valider_pont_architecture(ARCH_P4, REF)
    b.check(False, "[P4] — sans `periodes_projetees`, devait quand même être refusé (juste sans la liste)")
except PontRefusee as e:
    b.check("périodes attendues" not in str(e),
            f"[P4] — sans `periodes_projetees` (appelants qui n'ont pas la matière) : message sans la "
            f"liste, jamais une erreur : {e}")

# `_fiches_texte` — la règle de période est dite au pied de CHAQUE fiche (pas seulement au renvoi).
from app.modele_entreprise.matiere import _fiches_texte  # noqa: E402

fiche_exercice = next(v for v in REF.variables if v.periode == "exercice")
fiche_sans_periode = next(v for v in REF.variables if v.periode == "sans_periode")
txt_fiches = _fiches_texte([fiche_exercice, fiche_sans_periode])
b.check("CHAQUE exercice projeté" in txt_fiches,
        f"§5 — la fiche `exercice` dit qu'une reprise s'applique à CHAQUE exercice projeté : "
        f"{txt_fiches[:400]}")
b.check("une seule cellule, sans période" in txt_fiches,
        f"§5 — la fiche `sans_periode` dit qu'elle ne porte qu'une seule cellule : {txt_fiches[:400]}")

sys.exit(b.summary())
