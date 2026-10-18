"""Vérification du FILTRE refus→mandat de `tools/executer_chaine.py` (addendum à la spec du point
14, même lot — 2026-10-18).

CE QUE ÇA CORRIGE. Un refus d'AGENT (panne au maillon 2, `resultat.refus`) n'est jamais une demande
de recherche. Constat : une question refusée n'entre jamais dans `resultat.answers`, donc
`reviser_framework` (pur, lu ailleurs — on ne le touche pas) la compte comme « question applicable
sans aucune réponse » (contrôle ①, §3.2) et lui ouvre un mandat au maillon 4 — alors que le script
imprimait « AUCUN mandat n'en sort » pour elle au maillon 2 : la sortie imprimée mentait.
`_retirer_refus_des_mandats_manquants` (fonction PURE, extraite pour être testable sans dépense —
`tools/executer_chaine.py` appelle le modèle et écrit en prod, hors périmètre d'un check) retire les
questions refusées de `questions_manquantes`/`mandats_manquantes` avant la persistance.

Sans réseau, sans modèle, sans base — fonction pure, fixture construite (`ManagerReview`/
`FrameworkMandate`), pas de corpus réel. L'IMPORT de `tools.executer_chaine` lui-même ne dépense
rien (aucun effet de bord au niveau module : tout vit dans `main()`, gardé par `if __name__ ==
"__main__"`).

  • §1 une question PRÉSENTE dans `resultat.refus` sort de `questions_manquantes` ET
       `mandats_manquantes` — zéro mandat pour un refus d'agent ;
  • §2 NON-RÉGRESSION : une question sans réponse mais PAS refusée garde son mandat intact ;
  • §3 IDEMPOTENCE/PÉRIMÈTRE : un refus sur une question étrangère à `questions_manquantes` ne
       touche rien (mixte de cas, aucun effet de bord sur les autres questions) ;
  • §4 la liste des RETIRÉS est NOMMÉE (ce qui a été filtré, jamais tu en silence).
"""
import sys
from pathlib import Path

from app.agents.v2.manager import ManagerReview
from app.contracts.framework_answer_schema import FrameworkMandate
from tools.executer_chaine import _retirer_refus_des_mandats_manquants

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()


def _mandat(qid: str) -> FrameworkMandate:
    return FrameworkMandate(
        framework_id="qualite_financiere", question_id=qid, ticker_id="RVMD",
        origine="manager_renvoi", motif=f"question applicable `{qid}` sans aucune réponse",
        mandat=f"{qid} : collecter de quoi la fonder", etat="ouvert")


# ── §1 un refus d'agent ne produit AUCUN mandat « sans réponse » ───────────────────────────────
print("[1] une question refusée par l'agent sort de questions_manquantes ET mandats_manquantes")
_rev1 = ManagerReview(decisions={}, questions_manquantes=["qf_1", "qf_2"],
                      mandats_manquantes=[_mandat("qf_1"), _mandat("qf_2")])
_nettoyee1, _retires1 = _retirer_refus_des_mandats_manquants(_rev1, [("qf_1", "panne d'agent")])
b.check(_nettoyee1.questions_manquantes == ["qf_2"],
        f"§1 qf_1 (refusée) retirée de questions_manquantes → {_nettoyee1.questions_manquantes}")
b.check([m.question_id for m in _nettoyee1.mandats_manquantes] == ["qf_2"],
        "§1 qf_1 (refusée) retirée de mandats_manquantes → "
        f"{[m.question_id for m in _nettoyee1.mandats_manquantes]}")

# ── §2 NON-RÉGRESSION : sans réponse mais PAS refusée, le mandat reste ──────────────────────────
print("\n[2] une question SANS réponse mais PAS refusée garde intact son mandat")
_rev2 = ManagerReview(decisions={}, questions_manquantes=["qf_3"], mandats_manquantes=[_mandat("qf_3")])
_nettoyee2, _retires2 = _retirer_refus_des_mandats_manquants(_rev2, [])
b.check(_nettoyee2.questions_manquantes == ["qf_3"] and len(_nettoyee2.mandats_manquantes) == 1,
        f"§2 sans refus, rien n'est retiré → {_nettoyee2.questions_manquantes}")
b.check(_retires2 == [], f"§2 aucune question nommée comme retirée → {_retires2}")

# ── §3 un refus sur une question ÉTRANGÈRE ne touche rien ──────────────────────────────────────
print("\n[3] un refus sur une question hors de questions_manquantes n'a aucun effet de bord")
_rev3 = ManagerReview(decisions={}, questions_manquantes=["qf_4"], mandats_manquantes=[_mandat("qf_4")])
_nettoyee3, _retires3 = _retirer_refus_des_mandats_manquants(_rev3, [("qf_9", "panne d'agent")])
b.check(_nettoyee3.questions_manquantes == ["qf_4"] and len(_nettoyee3.mandats_manquantes) == 1,
        f"§3 qf_4 n'est pas touchée par un refus qui la nomme pas → {_nettoyee3.questions_manquantes}")
b.check(_retires3 == [], f"§3 qf_9 (refusée mais pas dans questions_manquantes) n'est pas listée → {_retires3}")

# ── §4 la liste des RETIRÉS est NOMMÉE (mixte : une question retirée, une épargnée) ─────────────
print("\n[4] la liste des retirés nomme exactement ce qui a été filtré, rien de plus")
_rev4 = ManagerReview(decisions={}, questions_manquantes=["qf_5", "qf_6"],
                      mandats_manquantes=[_mandat("qf_5"), _mandat("qf_6")])
_nettoyee4, _retires4 = _retirer_refus_des_mandats_manquants(
    _rev4, [("qf_5", "panne"), ("qf_7", "panne, mais qf_7 n'était pas manquante")])
b.check(_retires4 == ["qf_5"], f"§4 seul qf_5 est nommé retiré (qf_7 n'était pas manquante) → {_retires4}")
b.check(_nettoyee4.questions_manquantes == ["qf_6"],
        f"§4 qf_6 (non refusée) reste seule dans questions_manquantes → {_nettoyee4.questions_manquantes}")

sys.exit(b.summary())
