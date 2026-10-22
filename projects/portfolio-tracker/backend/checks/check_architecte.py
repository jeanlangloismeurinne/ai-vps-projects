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
from app.contracts.modele_entreprise_schema import Architecture  # noqa: E402
from app.contracts.parcours_schema import Manque  # noqa: E402
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
from app.modele_entreprise.periodes import PeriodesInvalides, periode_du_classeur, periodes_du_classeur  # noqa: E402
from app.modele_entreprise.porte import EtatQuestionSource, Porte, porte_de_l_architecte  # noqa: E402
from app.modele_entreprise.referentiel import load_referentiel  # noqa: E402
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
        pieces_citables=frozenset({100, 101, 102, 103}))
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
b.check(len(sortie.blocs) == 6, f"exemple — 6 blocs (obtenu {len(sortie.blocs)})")
arch_exemple = _poser_entete(sortie, ticker_id="FICTIF", version=1, archetype="rentable",
                             famille="industrielle", version_referentiel=REF.version)
matiere_exemple = matiere_fictive(pieces_citables=frozenset({100, 101, 102, 103}))
tient, motif, signaux = juger_architecture(arch_exemple, REF, matiere_exemple)
b.check(tient, f"exemple — valide contre le contrat, [P1]-[P5] et [S1]-[S11] (motif : {motif})")

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
DEPOTS_NVDA = [charger_depot("NVDA", "0001045810-26-000021"), charger_depot("NVDA", "0001045810-26-000075")]
V_NVDA = vt.relever(DEPOTS_NVDA, GAB, REF_VENT, SOCLE_STRUCT_NVDA)
STRUCT_NVDA = vt.structure_de_ventilation(V_NVDA, version_referentiel=REF_VENT.version,
                                          version_gabarit=GAB.version, depots=tuple(DEPOTS_NVDA))

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
    d = {"schema_version": "architecture-1.2.0", "ticker_id": "NVDA", "version": 1, "archetype": "rentable",
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
        f"[S1]-[S9] — architecture NVDA plausible au découpage du 10-K, signal [S3b] attendu : {r[:300]}")

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
    "schema_version": "architecture-1.2.0", "ticker_id": "FICTIF", "version": 1, "archetype": "rentable",
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
b.check("n'est pas la plus récente publiée" in valide_ou_motif(ARCH_10K),
        "[S3b] — signal : le découpage du 10-K n'est pas le plus récent (10-Q)")

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
                               pieces_citables=frozenset({1, 2}))
ARCH_RVMD = Architecture.model_validate({
    "schema_version": "architecture-1.2.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
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
         "classe de référence documentée en pièce.", "pieces": [1]},
    ],
    "variables_propres": [],
    "passage_a_l_agrege": [{"ligne": "chiffre_affaires", "formule": "produit__chiffre_affaires_du_bloc"}],
    "cellules_attendues": [
        {"bloc": "produit", "variable": "chiffre_affaires_du_bloc",
         "periodes": list(MATIERE_RVMD.periodes_projetees), "auteur": {"type": "demande_ciblee"}},
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
        "schema_version": "architecture-1.2.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
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
        "schema_version": "architecture-1.2.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
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
    "schema_version": "architecture-1.2.0", "ticker_id": "RVMD", "version": 1, "archetype": "rentable",
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
    socle_piece_id=1, ventilation_piece_id=2, pieces_citables=frozenset(range(800, 1100)))


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
        return matiere_fictive()

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

sys.exit(b.summary())
