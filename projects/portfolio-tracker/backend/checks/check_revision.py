"""Vérification de LA RÉVISION À LA BAISSE — point 13 (arbitrage de l'utilisateur, 2026-10-18),
`app/agents/v2/revision.py` (PURE : aucune base, aucun réseau, aucun modèle).

  • §1 LES TROIS BAISSES POSSIBLES (ordre de fondement `repondu`(3) > `approxime`(2) >
       `non_fondable`(1)) : chaque couple (précédente plus haute, courante plus basse) est reconnu,
       avec la raison de l'analyste et la précédente côte à côte.
  • §2 LA NON-BAISSE : à fondement ÉGAL ou en HAUSSE, aucun signal — `reponse_tient` fait foi
       ailleurs, `baisse_a_lire` ne se prononce que sur la BAISSE.
  • §3 `sans_objet` N'ENTRE DANS AUCUNE COMPARAISON : ni comme précédente, ni comme courante.
  • §4 LA LIGNÉE SANS PRÉCÉDENTE n'est jamais une baisse (rien à comparer).
  • §5 LA FIN DU SIGNAL : une décision du comité datée APRÈS la création de la courante l'éteint,
       quelle qu'en soit l'action (acquitter/renvoyer/reinitialiser/retablir) ; une décision
       ANTÉRIEURE à la courante ne l'éteint PAS — le comité n'a pas encore vu CETTE réponse.
  • §6 LE RÉTABLISSEMENT : `retablissable` est vrai ssi la précédente valide encore contre le
       contrat EN VIGUEUR (`precedente_validee`) ; sinon le motif nomme le report vers #137.

Lancer : `docker run … python checks/check_revision.py` (sans réseau — voir `run_all.sh`).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agents.v2.revision import RANG_FONDEMENT, ReponsePourBaisse, baisse_a_lire, precedente_validee
from app.contracts.comite_schema import DecisionComite
from app.contracts.framework_answer_schema import Fondation, FrameworkAnswer, Reponse, SansObjet
from app.contracts.readiness_report_schema import GapItem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
COMMUN = dict(framework_id="qualite_financiere", framework_version="v3.0.0",
              question_id="qf_7", ticker_id="RVMD", analyste="analyste_A")


def _repondu(verbatim="texte répondu", analyste="analyste_A") -> FrameworkAnswer:
    return FrameworkAnswer(**{**COMMUN, "analyste": analyste}, statut="repondu",
                           reponse=Reponse(verbatim=verbatim),
                           fondation=Fondation(cited_entry_ids=[10], rang_derive="A",
                                               nature_effective="mesure"))


def _approxime(analyste="analyste_A") -> FrameworkAnswer:
    from app.contracts.framework_answer_schema import Approximation
    return FrameworkAnswer(**{**COMMUN, "analyste": analyste}, statut="approxime",
                           reponse=Reponse(verbatim="texte approximé"),
                           fondation=Fondation(cited_entry_ids=[10], rang_derive="A-",
                                               nature_effective="interpretation"),
                           approximation=Approximation(
                               methode="m", ingredients_entry_ids=[11],
                               hypotheses_explicites=["h"], sensibilite="s"))


def _non_fondable(manque="le chiffre n'est publié nulle part", analyste="analyste_A") -> FrameworkAnswer:
    return FrameworkAnswer(**{**COMMUN, "analyste": analyste}, statut="non_fondable",
                           gap=GapItem(dimension="d", champs_cibles=["qf_7"], manque=manque,
                                      priorite="haute", coverage_actuelle="0/1"))


def _sans_objet(analyste="analyste_A") -> FrameworkAnswer:
    return FrameworkAnswer(**{**COMMUN, "analyste": analyste}, statut="sans_objet",
                           sans_objet=SansObjet(motif="hors sujet", aucun_substitut=True))


def _r(answer, i=1, *, cree_le=T0) -> ReponsePourBaisse:
    return ReponsePourBaisse(answer_id=i, cree_le=cree_le, statut_brut=answer.statut, answer=answer)


def _decision(decide_le, action="acquitter", **kw) -> DecisionComite:
    base = dict(id=1, ticker_id="RVMD", framework_id="qualite_financiere", framework_version="v3.0.0",
                question_id="qf_7", action=action, auteur="membre", motif="motif",
                ancre_etat="none", decide_le=decide_le)
    if action == "acquitter":
        base["answer_id"] = 2
    elif action == "renvoyer":
        base["mandat_id"] = 99
    elif action == "retablir":
        base["answer_id"], base["retablie_depuis_id"] = 2, 1
    base.update(kw)
    return DecisionComite(**base)


# ══ §1 LES TROIS BAISSES POSSIBLES ════════════════════════════════════════════════════════════
print("[1] les trois baisses possibles")
b.check(RANG_FONDEMENT == {"non_fondable": 1, "approxime": 2, "repondu": 3},
        f"§1 l'ordre de fondement est EXACTEMENT celui de la spec — obtenu {RANG_FONDEMENT}")

APRES = T0 + timedelta(days=5)
cas = (
    ("repondu→approxime", _repondu(), _approxime()),
    ("repondu→non_fondable", _repondu(), _non_fondable()),
    ("approxime→non_fondable", _approxime(), _non_fondable()),
)
for nom, prec_ans, cour_ans in cas:
    prec = _r(prec_ans, 1, cree_le=T0)
    cour = _r(cour_ans, 2, cree_le=APRES)
    bs = baisse_a_lire(cour, prec, [])
    b.check(bs is not None, f"§1 {nom} EST une baisse à lire")
    if bs is not None:
        b.check(bs.precedente.answer_id == 1 and bs.courante.answer_id == 2,
                f"§1 {nom} : précédente et courante correctement identifiées")
        b.check(bs.precedente.statut == prec_ans.statut and bs.courante.statut == cour_ans.statut,
                f"§1 {nom} : les DEUX statuts sont portés côte à côte")
        attendu_raison = (cour_ans.gap.manque if cour_ans.statut == "non_fondable"
                          else cour_ans.reponse.verbatim)
        b.check(bs.raison_analyste == attendu_raison,
                f"§1 {nom} : la raison de l'analyste est celle de la COURANTE — obtenu "
                f"{bs.raison_analyste!r}")
        attendu_resume_prec = (prec_ans.gap.manque if prec_ans.statut == "non_fondable"
                               else prec_ans.reponse.verbatim)
        b.check(bs.precedente.resume == attendu_resume_prec,
                f"§1 {nom} : le résumé de la précédente est son propre verbatim/motif — obtenu "
                f"{bs.precedente.resume!r}")
        b.check(bs.retablissable is True and bs.motif_non_retablissable is None,
                f"§1 {nom} : rétablissable (contrat en vigueur) sans motif de refus")

# ══ §2 LA NON-BAISSE : égal, hausse ═══════════════════════════════════════════════════════════
print("[2] la non-baisse : égal, hausse")
b.check(baisse_a_lire(_r(_repondu(), 2), _r(_repondu(analyste="analyste_A"), 1), []) is None,
        "§2 fondement ÉGAL (repondu → repondu) : pas une baisse")
b.check(baisse_a_lire(_r(_repondu(), 2), _r(_non_fondable(), 1), []) is None,
        "§2 HAUSSE (non_fondable → repondu) : jamais une baisse — la dernière analyse fait foi")
b.check(baisse_a_lire(_r(_non_fondable(), 2), _r(_approxime(), 1), []) is not None
        and baisse_a_lire(_r(_approxime(), 2), _r(_non_fondable(), 1), []) is None,
        "§2 témoin directionnel : seul le sens précédente-haute → courante-basse signale")

# ══ §3 `sans_objet` HORS DE TOUTE COMPARAISON ═════════════════════════════════════════════════
print("[3] `sans_objet` n'entre dans aucune comparaison")
b.check(baisse_a_lire(_r(_sans_objet(), 2), _r(_repondu(), 1), []) is None,
        "§3 courante `sans_objet` (même après un `repondu`) : jamais une baisse")
b.check(baisse_a_lire(_r(_non_fondable(), 2), _r(_sans_objet(), 1), []) is None,
        "§3 précédente `sans_objet` : jamais une baisse — pas de fondement à comparer")

# ══ §4 LIGNÉE SANS PRÉCÉDENTE ═════════════════════════════════════════════════════════════════
print("[4] une lignée sans précédente n'est jamais une baisse")
b.check(baisse_a_lire(_r(_non_fondable(), 1), None, []) is None,
        "§4 `precedente=None` (première réponse de la lignée) : rien à comparer")

# ══ §5 LA FIN DU SIGNAL — décision POSTÉRIEURE, pas antérieure ═══════════════════════════════════
print("[5] fin du signal par une décision postérieure (et pas par une antérieure)")
prec, cour = _r(_repondu(), 1, cree_le=T0), _r(_non_fondable(), 2, cree_le=APRES)
b.check(baisse_a_lire(cour, prec, []) is not None,
        "§5 témoin : sans AUCUNE décision, la baisse est à lire")
AVANT_COURANTE = APRES - timedelta(days=1)
POST_COURANTE = APRES + timedelta(days=1)
for action in ("acquitter", "renvoyer", "reinitialiser", "retablir"):
    d_avant = _decision(AVANT_COURANTE, action)
    b.check(baisse_a_lire(cour, prec, [d_avant]) is not None,
            f"§5 une décision `{action}` ANTÉRIEURE à la courante NE l'éteint PAS (le comité n'a "
            "pas encore vu cette réponse-là)")
    d_apres = _decision(POST_COURANTE, action)
    b.check(baisse_a_lire(cour, prec, [d_apres]) is None,
            f"§5 une décision `{action}` POSTÉRIEURE éteint le signal — « le comité a lu »")
b.check(baisse_a_lire(cour, prec, [_decision(AVANT_COURANTE, "acquitter"),
                                   _decision(POST_COURANTE, "renvoyer")]) is None,
        "§5 PLUSIEURS décisions : il suffit qu'UNE seule soit postérieure pour éteindre le signal")

# ══ §6 LE RÉTABLISSEMENT ══════════════════════════════════════════════════════════════════════
print("[6] le rétablissement : `retablissable` et son motif")
b.check(precedente_validee("repondu", _repondu().model_dump(mode="json")) is not None,
        "§6 un `answer_json` qui valide contre le contrat en vigueur se relit")
b.check(precedente_validee("repondu", {"statut": "repondu"}) is None,
        "§6 un `answer_json` incomplet (contrat antérieur, champs manquants) ne valide plus")
prec_illisible = ReponsePourBaisse(answer_id=1, cree_le=T0, statut_brut="repondu", answer=None)
cour_baisse = _r(_non_fondable(), 2, cree_le=APRES)
bs_illisible = baisse_a_lire(cour_baisse, prec_illisible, [])
b.require([bs_illisible] if bs_illisible else [], 1,
          "§6 une précédente ILLISIBLE sous le contrat actuel reste une baisse SIGNALÉE (le rang "
          "vient de la colonne `statut`, jamais du JSON)")
if bs_illisible is not None:
    b.check(bs_illisible.retablissable is False
            and bs_illisible.motif_non_retablissable is not None
            and "contrat antérieur" in bs_illisible.motif_non_retablissable
            and "réinitialiser" in bs_illisible.motif_non_retablissable,
            f"§6 … mais NON rétablissable, et le motif renvoie vers #137 — obtenu "
            f"{bs_illisible.motif_non_retablissable!r}")
    b.check("illisible" in bs_illisible.precedente.resume,
            "§6 le résumé de la précédente illisible le DIT, sans deviner un verbatim")

try:
    baisse_a_lire(ReponsePourBaisse(answer_id=2, cree_le=APRES, statut_brut="non_fondable", answer=None),
                  prec, [])  # prec = repondu (rang 3) : une vraie baisse (1 < 3), appel fautif
    b.check(False, "§6 une COURANTE sans `answer` validé doit LEVER (elle vient toujours de "
                   "`read_answers_courantes`, qui lève sinon) — jamais un silence")
except ValueError as e:
    b.check("COURANTE" in str(e), f"§6 … et la levée NOMME que c'est la courante — obtenu {e}")

sys.exit(b.summary())
