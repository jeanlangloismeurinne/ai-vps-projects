"""Vérification du BOUCLAGE comité → collecte (lot 5 — `app/agents/v2/bouclage.py`,
`app/contracts/bouclage_schema.py`).

Sans réseau, sans modèle, sans base : le contrat et la classification sont PURS (la frontière
gratuite, `feedback_frontiere_gratuite_avant_depense_modele`). L'orchestration `boucler_renvois`
dépense et écrit — elle se prouve à l'ACCEPTATION réelle (`tools/acceptation_bouclage.sh`), pas ici.

  • §1 LE CONTRAT PORTE EXACTEMENT SA CHARGE. `acquis` ⟺ `statut_apres != non_fondable` ; les trois
       sorts non fondés exigent `statut_apres == non_fondable`. `CompteRenduBouclage` refuse plus de
       boucles que de mandats lus et deux boucles sur un même mandat.
  • §2 `classer_sort` EST LE DÉTENTEUR UNIQUE (#46), ET SES QUATRE SORTS SONT ATTEIGNABLES (#63, 5ᵉ
       faux vert : un sort qu'aucune entrée ne produit n'est pas un sort). L'ordre des branches est la
       doctrine : une dispense prime sur le résultat de la collecte ; `sans_objet` fonde. Et
       `boucler_renvois` APPELLE `classer_sort` (AST) au lieu de re-décider en ligne.
  • §3 `collecte_insuffisante` vs `mandat_non_executable` se lit sur l'ORIGINE des mandats collecteur
       (`echec_collecte`/lien = tenté ; `inobtenable` seul = non exécutable), pas sur un jugement.
  • §4 EXERCÉ, PAS SEULEMENT VERT (#71, `feedback_controle_au_point_de_lecture`). On COMPTE les
       APPELANTS de `serve_mandate` ET `read_open_mandates` dans `app/` (AST) : le décideur avait 0
       appelant en production le 2026-09-25, garde verte. Retirer le câblage doit rougir ICI.
  • §7 POINT 14 (séance du 2026-10-18) : `bouclage.py` ne SERT plus lui-même les mandats —
       `persist_answer` (`framework_persist.py`) est le SEUL appelant de `serve_mandate` ; le
       bouclage ne garde que `id_du_mandat_ouvert`, pour NOMMER le mandat dans sa note AVANT que
       `persist_answer` ne le ferme. Un seul chemin de clôture (#46), que la réponse vienne de la
       chaîne ou du bouclage.
  • §5 LE MÊME PROCESSUS, SCOPÉ (#46 : pas de chemin de recherche parallèle). Le pont ne réclame que
       les questions du scope (`[R]`), refuse une ligne hors scope (`[P]`) ; le contexte du traducteur
       refuse un scope hors des questions applicables (#32).

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import ast
import sys
from pathlib import Path

from app.agents.v2 import bouclage as B
from app.agents.v2.bouclage import classer_sort, _a_tente_collecte_par_question
from app.agents.v2.frameworks import (
    CollectionPlanRefused,
    load_frameworks,
    valider_pont_collection_plan,
)
from datetime import date

from app.agents.v2.traducteur import (FraicheurQuestion, HorlogeDuPlan, TraducteurInapplicable,
                                      contexte_traducteur)
from app.knowledge.edgar_feed import IdentiteEmetteur
from app.contracts.bouclage_schema import (
    SORTS_BOUCLAGE,
    CompteRenduBouclage,
    MandatBoucle,
)
from app.contracts.collection_plan_schema import CollectionPlan, CollectionPlanItem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()
FICH = load_frameworks()
FW = "qualite_financiere"


def _boucle(sort, avant, apres, mid=1, qid="qf_1"):
    return MandatBoucle(question_id=qid, mandat_id=mid, sort=sort,
                        statut_avant=avant, statut_apres=apres, motif="m")


def _rejette(label, fn, motif=None):
    """Un refus attendu. `motif` : le refus doit venir de CETTE règle — un refus prononcé par une autre
    est un FAIL nommé (4ᵉ faux vert : la fixture déclenche une autre garde que celle qu'on éprouve)."""
    try:
        fn()
        b.check(False, f"{label} — accepté à tort")
    except Exception as e:
        b.check(motif is None or motif in str(e), f"{label}" + ("" if motif is None or motif in str(e)
                                                                 else f" — refusé, mais pas par la règle visée : {e}"))


# ── §1 LE CONTRAT PORTE EXACTEMENT SA CHARGE ────────────────────────────────────────────────────
print("[1] le contrat de la note honnête")
b.check(_boucle("acquis", "non_fondable", "repondu").sort == "acquis",
        "§1 `acquis` accepté avec un statut_apres fondé (repondu)")
b.check(_boucle("acquis", "repondu", "sans_objet").sort == "acquis",
        "§1 `acquis` accepté sur `sans_objet` — savoir qu'une question n'a pas d'objet fonde le renvoi")
for s in ("collecte_insuffisante", "mandat_non_executable", "classe_sans_suite"):
    b.check(_boucle(s, "non_fondable", "non_fondable").sort == s,
            f"§1 `{s}` accepté avec statut_apres non_fondable")
_rejette("§1 `acquis` avec statut_apres non_fondable est REFUSÉ (lirait « rien à signaler », #49)",
         lambda: _boucle("acquis", "non_fondable", "non_fondable"))
_rejette("§1 `collecte_insuffisante` avec statut_apres fondé est REFUSÉ (une question fondée est acquise)",
         lambda: _boucle("collecte_insuffisante", "non_fondable", "repondu"))

_cr = CompteRenduBouclage(ticker_id="RVMD", framework_id=FW, framework_version="v3.0.0",
                          mandats_lus=2, boucles=[_boucle("acquis", "non_fondable", "repondu", mid=1),
                                                  _boucle("collecte_insuffisante", "non_fondable",
                                                          "non_fondable", mid=2, qid="qf_2")])
b.check(len(_cr.boucles) == 2, "§1 un compte rendu à 2 boucles pour 2 mandats lus est valide")
_rejette("§1 plus de boucles que de mandats lus est REFUSÉ (on ne sert pas un mandat non ouvert)",
         lambda: CompteRenduBouclage(ticker_id="R", framework_id=FW, framework_version="v",
                                     mandats_lus=1,
                                     boucles=[_boucle("acquis", "non_fondable", "repondu", mid=1),
                                              _boucle("acquis", "non_fondable", "repondu", mid=2)]))
_rejette("§1 deux boucles sur le MÊME mandat_id est REFUSÉ (un mandat n'est servi qu'une fois)",
         lambda: CompteRenduBouclage(ticker_id="R", framework_id=FW, framework_version="v",
                                     mandats_lus=2,
                                     boucles=[_boucle("acquis", "non_fondable", "repondu", mid=7),
                                              _boucle("acquis", "non_fondable", "repondu", mid=7,
                                                      qid="qf_2")]))

# ── §2 classer_sort : DÉTENTEUR UNIQUE, QUATRE SORTS ATTEIGNABLES ───────────────────────────────
print("\n[2] classer_sort — les quatre sorts atteignables, la doctrine dans l'ordre des branches")
_obtenus = {
    classer_sort("non_fondable", "repondu", a_tente_collecte=True, dispensee=False),
    classer_sort("non_fondable", "non_fondable", a_tente_collecte=True, dispensee=True),
    classer_sort("non_fondable", "non_fondable", a_tente_collecte=True, dispensee=False),
    classer_sort("non_fondable", "non_fondable", a_tente_collecte=False, dispensee=False),
}
b.check(_obtenus == set(SORTS_BOUCLAGE), f"§2 les quatre sorts sont atteignables → {sorted(_obtenus)}")
b.check(classer_sort("non_fondable", "non_fondable", a_tente_collecte=True, dispensee=True)
        == "classe_sans_suite",
        "§2 la DISPENSE prime sur la collecte tentée (décision de comité)")
b.check(classer_sort("repondu", "sans_objet", a_tente_collecte=False, dispensee=False) == "acquis",
        "§2 `sans_objet` fonde même sans collecte tentée")
b.check(classer_sort("non_fondable", "non_fondable", a_tente_collecte=True, dispensee=False)
        == "collecte_insuffisante"
        and classer_sort("non_fondable", "non_fondable", a_tente_collecte=False, dispensee=False)
        == "mandat_non_executable",
        "§2 `a_tente_collecte` sépare collecte insuffisante (vrai) de mandat non exécutable (faux)")

_arbre = ast.parse(Path(B.__file__).read_text(encoding="utf-8"))
_appels_classer = [n for n in ast.walk(_arbre)
                   if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "classer_sort"]
b.check(len(_appels_classer) >= 1,
        "§2 `boucler_renvois` APPELLE `classer_sort` — le sort vient du détenteur, pas d'un if en ligne")

# ── §3 origine de la collecte → tenté ou non ────────────────────────────────────────────────────
print("\n[3] la distinction collecte_insuffisante / mandat_non_executable se lit sur l'origine")
_rap = {"liens": [{"question_id": "qf_2", "entry_id": 5}],
        "mandats": [{"question_id": "qf_3", "origine": "echec_collecte"},
                    {"question_id": "qf_4", "origine": "inobtenable"}]}
_tente = _a_tente_collecte_par_question(_rap)
b.check(_tente == {"qf_2": True, "qf_3": True, "qf_4": False},
        f"§3 lien→tenté, echec_collecte→tenté, inobtenable seul→non tenté → {_tente}")

# ── §4 EXERCÉ, PAS SEULEMENT VERT — on compte les APPELANTS en production ────────────────────────
print("\n[4] serve_mandate ET read_open_mandates ont un appelant en PRODUCTION (#71)")
_APP = Path(B.__file__).resolve().parent.parent.parent  # …/app
_DEF = "manager_persist.py"  # là où ils sont DÉFINIS — un `def` n'est pas un appel


def _appelants(nom: str) -> list[str]:
    """Fichiers de `app/` (hors le module de définition) qui APPELLENT `nom` (Call, AST)."""
    out = []
    for py in _APP.rglob("*.py"):
        if py.name == _DEF:
            continue
        try:
            arbre = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(arbre):
            if isinstance(n, ast.Call):
                f = n.func
                if (isinstance(f, ast.Name) and f.id == nom) or \
                   (isinstance(f, ast.Attribute) and f.attr == nom):
                    out.append(py.name)
                    break
    return out


_APPELANTS: dict[str, list[str]] = {}
for _nom in ("serve_mandate", "read_open_mandates", "id_du_mandat_ouvert"):
    _app = _appelants(_nom)
    _APPELANTS[_nom] = _app
    b.check(len(_app) >= 1,
            f"§4 `{_nom}` a un appelant de production dans app/ (exercé, pas seulement testé) → {_app}")

# ── §7 POINT 14 : UN SEUL chemin de clôture — `bouclage.py` ne SERT plus lui-même ────────────────
print("\n[7] `bouclage.py` ne sert plus lui-même (point 14) : `persist_answer` est le SEUL fermeur")
b.check("bouclage.py" not in _APPELANTS["serve_mandate"],
        f"§7 `bouclage.py` n'APPELLE plus `serve_mandate` directement (un seul chemin, #46) "
        f"→ appelants actuels {_APPELANTS['serve_mandate']}")
b.check("framework_persist.py" in _APPELANTS["serve_mandate"],
        f"§7 `framework_persist.py` (`persist_answer`) est bien l'appelant de `serve_mandate` "
        f"→ {_APPELANTS['serve_mandate']}")
b.check("bouclage.py" in _APPELANTS["id_du_mandat_ouvert"],
        "§7 `bouclage.py` continue d'appeler `id_du_mandat_ouvert` (pour NOMMER le mandat dans sa "
        f"note AVANT que `persist_answer` ne le ferme) → {_APPELANTS['id_du_mandat_ouvert']}")

# ── §5 LE MÊME PROCESSUS, SCOPÉ ─────────────────────────────────────────────────────────────────
print("\n[5] la collecte scopée : même pont, restreint aux questions renvoyées (#46)")
_V = FICH.schema_version
# qf_1 sous `rentable` est `variable`, essentiels À COLLECTER : resultat_operationnel_apres_impot,
# cout_du_capital (`capital_employe` se lit dans le socle depuis #116, il ne se collecte plus). Un plan
# qui ne couvre QUE qf_1 doit passer quand le scope vaut {qf_1}, et échouer sans scope (les autres
# questions ont des essentiels non couverts).
_essentiels_qf1 = ("resultat_operationnel_apres_impot", "cout_du_capital")
_items_qf1 = [CollectionPlanItem(question_id="qf_1", ingredient_id=ing, statut="traduit", periode="exercice_clos",
                                 metrique="résultat d'exploitation après impôt",
                                 source_pressentie="10-K", ancre="clôture de l'exercice")
              for ing in _essentiels_qf1]
_plan_qf1 = CollectionPlan(ticker_id="RVMD", framework_id=FW, framework_version=_V,
                           archetype="rentable", items=_items_qf1)
try:
    valider_pont_collection_plan(_plan_qf1, fichier=FICH, questions=frozenset({"qf_1"}))
    b.check(True, "§5 un plan couvrant qf_1 PASSE quand le scope vaut {qf_1}")
except CollectionPlanRefused as e:
    b.check(False, f"§5 le plan scopé qf_1 est refusé à tort → {e}")
_rejette("§5 le MÊME plan SANS scope est refusé ([R] exige toutes les questions applicables)",
         lambda: valider_pont_collection_plan(_plan_qf1, fichier=FICH))

# une ligne HORS scope est refusée ([P]). ⚠️ L'ingrédient débordant doit être COLLECTABLE : depuis #115,
# `qf_2.resultat_net` se lit dans le socle et serait refusé pour CETTE raison, quel que soit le scope —
# la mutation « [P] tolère hors scope » restait verte (fixture non discriminante, 1ᵉʳ faux vert).
_plan_deborde = CollectionPlan(
    ticker_id="RVMD", framework_id=FW, framework_version=_V, archetype="rentable",
    items=_items_qf1 + [CollectionPlanItem(question_id="qf_2", ingredient_id="variation_besoin_fonds_roulement",
                                           statut="traduit", periode="exercice_clos",
                                           metrique="variation du besoin en fonds de roulement",
                                           source_pressentie="10-K", ancre="clôture de l'exercice")])
_rejette("§5 une ligne HORS du scope de bouclage est refusée ([P])",
         lambda: valider_pont_collection_plan(_plan_deborde, fichier=FICH,
                                              questions=frozenset({"qf_1"})), motif="HORS du scope")

# Identité copiée du registre SEC réel (`resolve_identite("RVMD")`, relevé le 2026-09-26).
_RVMD = IdentiteEmetteur(symbole="RVMD", cik=1628171, raison_sociale="Revolution Medicines, Inc.")
# Clôture copiée du réel (10-Q RVMD du trimestre clos le 2026-06-30) — #120.
_H_RVMD = HorlogeDuPlan(date_du_jour=date(2026, 10, 13), derniere_cloture=date(2026, 6, 30),
                        fraicheur={q.id: FraicheurQuestion("aucun_fait", None, "témoin")
                                   for f in FICH.frameworks for q in f.questions})
# le contexte du traducteur refuse un scope hors des questions applicables (#32).
_rejette("§5 un scope nommant une question SANS OBJET (qf_1 sous pre_revenus) est refusé (#32)",
         lambda: contexte_traducteur(FICH, FW, "pre_revenus", "RVMD", emetteur=_RVMD, horloge=_H_RVMD,
                                     questions=frozenset({"qf_1"})))
_rejette("§5 un scope VIDE est refusé (l'orchestrateur s'arrête avant, #40)",
         lambda: contexte_traducteur(FICH, FW, "rentable", "RVMD", emetteur=_RVMD, horloge=_H_RVMD, questions=frozenset()))
_ctx = contexte_traducteur(FICH, FW, "rentable", "RVMD", emetteur=_RVMD, horloge=_H_RVMD, questions=frozenset({"qf_1"}))
b.check([q["id"] for q in _ctx["questions"]] == ["qf_1"],
        "§5 le contexte scopé ne montre QUE la question renvoyée")

# ── §6 chaque sort NOMME sa cause, et les motifs sont DISTINCTS ─────────────────────────────────
print("\n[6] chaque sort a son motif, et ils sont distincts (un lecteur doit pouvoir dire POURQUOI)")
_motifs = {s: B._MOTIF_DU_SORT[s] for s in SORTS_BOUCLAGE}
b.require(_motifs, len(SORTS_BOUCLAGE), "§6 un motif par sort")
b.check(len(set(_motifs.values())) == len(SORTS_BOUCLAGE),
        f"§6 les quatre motifs sont distincts → {len(set(_motifs.values()))}")

sys.exit(b.summary())
