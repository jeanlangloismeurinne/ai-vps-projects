"""Vérification du MANAGER d'un framework et de ses quatre contrôles (lot 4 — `app/agents/v2/manager.py`).

Sans réseau, sans modèle, sans base : le manager est une fonction PURE (aucun contrôle ne demande un
jugement d'investissement, §3.2), donc toute sa décision se joue hors ligne — c'est la frontière
gratuite (`feedback_frontiere_gratuite_avant_depense_modele`).

  • §1 CHAQUE CONTRÔLE A SON `ok` ET SON `ko`, ET LE `ko` EST ATTEIGNABLE. Un contrôle qu'aucune
       mutation ne peut faire rougir n'est pas un contrôle (#63, 5ᵉ faux vert). Les quatre `ko`
       naissent d'un `FrameworkAnswer` VALIDE (que Pydantic accepte) rendu incohérent avec le
       corpus ou le référentiel — ce que le contrat ne peut pas juger (#37), et donc ce que le
       manager existe pour attraper.
  • §2 ACQUITTE / RENVOIE. Quatre contrôles au vert ⟹ acquittement sans mandat ; un `ko` ⟹ renvoi
       AVEC un mandat qui nomme sa cause (jamais « le manager a renvoyé »). Une question applicable
       restée sans réponse produit un mandat au niveau du framework (contrôle ①).
  • §3 DÉTENTEURS UNIQUES RÉUTILISÉS, JAMAIS RECOPIÉS (#46). Le grounding (②) est `validate_grounding`,
       le cran (③) est `derive_synthesis_reliability`, le substitut (④) est `motif_substitut_hors_sujet`
       — partagé avec le pont —, l'applicabilité est `questions_applicables`. Vérifié par AST (un
       import réel, pas une mention), et aucune table de tier recopiée dans le module.
  • §4 UN RENVOI FERME L'ÉCART B. Tout renvoi porte un `FrameworkMandate` `ouvert`,
       `origine='manager_renvoi'`, qui nomme sa question ; un acquittement n'en porte aucun (§3.1).
  • §5 LE MANAGER NE RÉÉCRIT NI NE PROMEUT (§3.3). Il ne construit aucune `Reponse`/`Fondation`, donc
       il n'a nulle part où écrire une correction ou un rang — la garantie est STRUCTURELLE.

⚠️ CE QUE CE CHECK NE MESURE PAS : le bout-en-bout T8 (un renvoi crée un mandat consommable, le
re-run change le statut). C'est l'affaire de la couche données + acceptation réelle (migration 043,
persistance, collecteur) — le maillon suivant. Un vert ici dit que la LOGIQUE du manager est juste,
pas qu'elle a fait bouger un statut en base (#71 : décider n'est pas encore produire).

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import sys
from pathlib import Path

from app.agents.v2 import manager as M
from app.agents.v2.frameworks import load_frameworks, motif_substitut_hors_sujet
from app.contracts.framework_answer_schema import (
    Approximation,
    Fondation,
    FrameworkAnswer,
    FrameworkMandate,
    Reponse,
    SansObjet,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, imports_symbol, strip_code  # noqa: E402

b = Bilan()
FICH = load_frameworks()

# Un corpus minimal : deux entries tier A, une entry tier B — de quoi dériver un cran.
CORPUS = {
    10: {"reliability_tier": "A", "nature": "mesure"},
    11: {"reliability_tier": "A", "nature": "mesure"},
    20: {"reliability_tier": "B", "nature": "interpretation"},
}


def _repondu(qid, ticker, analyste="a", cites=(10,), rang="A", nature="mesure"):
    return FrameworkAnswer(
        framework_id="qualite_financiere", framework_version="v3.0.0", question_id=qid,
        ticker_id=ticker, analyste=analyste, statut="repondu",
        reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
        fondation=Fondation(cited_entry_ids=list(cites), rang_derive=rang, nature_effective=nature))


def _approxime(qid, ticker, cites=(10, 11), rang="A-"):
    return FrameworkAnswer(
        framework_id="qualite_financiere", framework_version="v3.0.0", question_id=qid,
        ticker_id=ticker, analyste="a", statut="approxime",
        reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
        fondation=Fondation(cited_entry_ids=list(cites), rang_derive=rang,
                            nature_effective="interpretation"),
        approximation=Approximation(methode="m", ingredients_entry_ids=list(cites),
                                    hypotheses_explicites=["h"], sensibilite="s"))


def _sans_objet(qid, ticker, analyste="a", sub_appli=None, sub_id=None):
    return FrameworkAnswer(
        framework_id="qualite_financiere", framework_version="v3.0.0", question_id=qid,
        ticker_id=ticker, analyste=analyste, statut="sans_objet",
        sans_objet=SansObjet(motif="sans revenus", substitut_applique=sub_appli,
                             substitut_answer_id=sub_id, aucun_substitut=sub_appli is None))


def _controles(ans, *, applicable, autres=None):
    c, motif = M.controles_de_la_reponse(ans, applicable=applicable, entries=CORPUS,
                                         autres_reponses=autres)
    return c, motif


# ══ §1 — chaque contrôle : un ok atteignable ET un ko atteignable ═══════════════════════════════

# ① COMPLÉTUDE — une question inapplicable pour l'archétype répondue autrement que `sans_objet`.
c_ok, _ = _controles(_sans_objet("qf_1", "RVMD"), applicable=False)
b.check(c_ok.completude == "ok", "① ok : question inapplicable traitée en `sans_objet`")
c_ko, _ = _controles(_repondu("qf_1", "RVMD"), applicable=False)
b.check(c_ko.completude == "ko", "① ko : question inapplicable répondue `repondu` (défaut T4, #190)")
# ⚠️ atteignabilité : le MÊME `repondu` sur une question APPLICABLE passe — le ko tient à
#    l'applicabilité, pas au statut (sinon le contrôle refuserait toute réponse).
c_appl, _ = _controles(_repondu("qf_1", "MSFT"), applicable=True)
b.check(c_appl.completude == "ok", "① ok : la même réponse sur une question applicable passe")

# ② FONDATION — une citation hors du corpus fourni au manager (une entry supersédée depuis l'analyse).
c_ok, _ = _controles(_repondu("qf_2", "MSFT", cites=(10,)), applicable=True)
b.check(c_ok.fondation == "ok", "② ok : citation dans le corpus fourni")
c_ko, mko = _controles(_repondu("qf_2", "MSFT", cites=(99,)), applicable=True)
b.check(c_ko.fondation == "ko", "② ko : citation #99 hors du corpus fourni")
b.check("99" in mko, "② ko nomme l'entry fautive (le motif finit dans un mandat)")

# ③ HONNÊTETÉ — une approximation dont le rang N'EST PAS dégadé sous la plus faible citée.
c_ok, _ = _controles(_approxime("qf_1", "MSFT", cites=(10, 11), rang="A-"), applicable=True)
b.check(c_ok.honnetete_approximation == "ok", "③ ok : approximation dégradée d'un cran (A → A-)")
c_ko, _ = _controles(_approxime("qf_1", "MSFT", cites=(10, 11), rang="A"), applicable=True)
b.check(c_ko.honnetete_approximation == "ko", "③ ko : approximation gardant le rang A (non dégradé)")
c_so, _ = _controles(_repondu("qf_2", "MSFT"), applicable=True)
b.check(c_so.honnetete_approximation == "sans_objet",
        "③ sans_objet : une réponse qui n'approxime pas n'a pas d'approximation à juger")

# ④ NON-SUBSTITUTION — un substitut qui pointe la réponse d'une AUTRE question (ok) ou de la SIENNE (ko).
sub_autre = _repondu("qf_2", "RVMD", analyste="b")   # une réponse à une AUTRE question
so_ok = _sans_objet("qf_1", "RVMD", sub_appli="voir qf_2", sub_id=77)
c_ok, _ = _controles(so_ok, applicable=True, autres={77: sub_autre})
b.check(c_ok.non_substitution == "ok", "④ ok : substitut vers la réponse d'une AUTRE question")
sub_meme = _repondu("qf_1", "RVMD", analyste="b")    # une réponse à la MÊME question
so_ko = _sans_objet("qf_1", "RVMD", sub_appli="voir qf_1", sub_id=88)
c_ko, _ = _controles(so_ko, applicable=True, autres={88: sub_meme})
b.check(c_ko.non_substitution == "ko", "④ ko : substitut vers une réponse à la MÊME question")

# ══ §2 — acquitte / renvoie, et le mandat nomme sa cause ════════════════════════════════════════

# Acquittement : 4 contrôles au vert (une seule question applicable pour restreindre les manquantes).
rev_ok = M.reviser_framework(
    [_repondu(q, "MSFT") for q in ("qf_1", "qf_2", "qf_3", "qf_4", "qf_5", "qf_6", "qf_7")],
    fichier=FICH, framework_id="qualite_financiere", archetype="rentable", ticker_id="MSFT",
    entries=CORPUS)
verdicts = [d.verdict for d in rev_ok.decisions.values()]
b.require(verdicts, 7, "§2 sept réponses révisées")
b.check(all(v == "acquitte" for v in verdicts), "§2 toutes acquittées quand tout est au vert")
b.check(not rev_ok.mandats(), "§2 aucun mandat quand tout est acquitté")
b.check(not rev_ok.questions_manquantes, "§2 aucune question manquante quand les 7 sont répondues")

# Renvoi : une réponse fondée hors corpus parmi des réponses saines.
answers_mix = [_repondu(q, "MSFT") for q in ("qf_2", "qf_3", "qf_4", "qf_5", "qf_6", "qf_7")]
answers_mix.append(_repondu("qf_1", "MSFT", cites=(99,)))   # fondation ko
rev_mix = M.reviser_framework(
    answers_mix, fichier=FICH, framework_id="qualite_financiere", archetype="rentable",
    ticker_id="MSFT", entries=CORPUS)
renvoyees = [k for k, d in rev_mix.decisions.items() if d.verdict == "renvoye"]
acquittees = [k for k, d in rev_mix.decisions.items() if d.verdict == "acquitte"]
b.require(renvoyees, 1, "§2 exactement une réponse renvoyée (celle hors corpus)")
# `renvoyees[:1]` plutôt que `[0]` : une mutation qui désarme un contrôle rend la liste vide, et le
# check DOIT atteindre son bilan malgré tout (2ᵉ faux vert — script mort avant ses asserts).
b.check(renvoyees[:1] == [("qf_1", "a")], "§2 c'est bien `qf_1` qui est renvoyée")
b.check(len(acquittees) == 6, "§2 les six autres réponses restent acquittées (le renvoi est PAR réponse)")

# ══ §3 — détenteurs uniques réutilisés, jamais recopiés (#46) ═══════════════════════════════════

MOD = "app/agents/v2/manager.py"
b.check(imports_symbol(MOD, "validate_grounding", from_module="app.knowledge.synthesis_feed"),
        "§3 ② importe `validate_grounding` (grounding = détenteur unique #46/#28)")
b.check(imports_symbol(MOD, "derive_synthesis_reliability", from_module="app.knowledge.synthesis_feed"),
        "§3 ③ importe `derive_synthesis_reliability` (la règle du cran, un seul détenteur)")
b.check(imports_symbol(MOD, "motif_substitut_hors_sujet", from_module="app.agents.v2.frameworks"),
        "§3 ④ importe le substitut PARTAGÉ avec le pont (pas un jumeau)")
b.check(imports_symbol(MOD, "questions_applicables", from_module="app.agents.v2.traducteur"),
        "§3 ① importe `questions_applicables` (l'applicabilité par archétype)")

# La règle du substitut est LA MÊME que celle du pont : le détenteur rend un motif ⟺ le manager `ko`.
_motif = motif_substitut_hors_sujet(so_ko, {88: sub_meme})
b.check(_motif is not None and c_ko.non_substitution == "ko",
        "§3 le substitut du manager EST le verdict du détenteur partagé (aucun second contrôle)")

# Aucune table de tier ni littéral de rang recopié dans le module (le cran se DÉRIVE, il ne s'écrit pas).
CODE = strip_code(Path(MOD).read_text(encoding="utf-8"))
b.check("'A-'" not in CODE and '"A-"' not in CODE,
        "§3 aucun tier dégradé écrit en dur (le cran vient de `derive_synthesis_reliability`)")

# ══ §4 — un renvoi ferme l'Écart B ; les mandats des questions manquantes ═══════════════════════

mandat = rev_mix.decisions[("qf_1", "a")].mandat
_est_mandat = isinstance(mandat, FrameworkMandate)  # une mutation peut le rendre None : ne pas crasher
b.check(_est_mandat, "§4 un renvoi PORTE un FrameworkMandate")
b.check(_est_mandat and mandat.etat == "ouvert" and mandat.origine == "manager_renvoi",
        "§4 le mandat est `ouvert` et `manager_renvoi` (le canal de l'Écart B, §3.1)")
b.check(_est_mandat and mandat.question_id == "qf_1" and mandat.ticker_id == "MSFT",
        "§4 le mandat nomme SA question et son émetteur")
b.check(rev_ok.decisions[("qf_1", "a")].mandat is None, "§4 un acquittement ne porte AUCUN mandat")

# Contrôle ① au niveau du framework : les questions applicables sans réponse deviennent des mandats.
rev_creux = M.reviser_framework(
    [_repondu("qf_2", "MSFT")], fichier=FICH, framework_id="qualite_financiere",
    archetype="rentable", ticker_id="MSFT", entries=CORPUS)
b.check(set(rev_creux.questions_manquantes) == {"qf_1", "qf_3", "qf_4", "qf_5", "qf_6", "qf_7"},
        "§4 ① les six questions applicables sans réponse sont listées manquantes")
b.require(rev_creux.mandats_manquantes, 6, "§4 ① un mandat par question manquante")
b.check(all(m.origine == "manager_renvoi" and m.etat == "ouvert"
            for m in rev_creux.mandats_manquantes),
        "§4 ① chaque question manquante produit un mandat ouvert (un blanc n'est pas un `sans_objet`)")
# Une question DISPENSÉE n'est pas manquante (la dispense décrit l'émetteur, §5.1).
rev_disp = M.reviser_framework(
    [_repondu("qf_2", "MSFT")], fichier=FICH, framework_id="qualite_financiere",
    archetype="rentable", ticker_id="MSFT", entries=CORPUS,
    dispenses=frozenset({"qf_1", "qf_3", "qf_4", "qf_5", "qf_6", "qf_7"}))
b.check(not rev_disp.questions_manquantes and not rev_disp.mandats(),
        "§4 ① une question dispensée n'est ni manquante ni mandatée")

# ══ §5 — le manager ne réécrit ni ne promeut (§3.3) : garantie STRUCTURELLE ═════════════════════

# Le module ne construit aucune Reponse/Fondation/Approximation — il n'a nulle part où écrire une
# correction ni un rang. Vérifié sur le CODE dépouillé (une mention en commentaire ne compte pas).
for interdit in ("Reponse(", "Fondation(", "Approximation("):
    b.check(interdit not in CODE,
            f"§5 le manager ne construit pas `{interdit[:-1]}` (il acquitte ou renvoie, jamais réécrit)")

sys.exit(b.summary())
