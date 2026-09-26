"""Vérification du REGISTRE DU COMITÉ — acquitter / renvoyer, tracés (lot 6 maillon 3,
`app/agents/v2/comite.py` + contrat `comite_schema.py` + branchement dans `parcours.py`).

Sans réseau, sans modèle, sans base : la règle « l'acceptation tient-elle aujourd'hui ? » est PURE
(`servir_acceptation`), et le parcours qui la lit aussi. L'écriture du PV est éprouvée contre la vraie
base par `check_comite_persist.py` (ROLLBACK), la table par `negatif_048.sh`.

  • §1 LE CONTRAT refuse un PV incomplet (arbitrage n°1) : motif ou auteur blancs, acceptation sans
       réponse, acceptation sur des faits illisibles, renvoi sans mandat (Écart B), ancre qui ment sur
       son fait, acceptation « tombée sur un fait » qui ne nomme pas le fait, position qui n'est pas
       la tête du registre.
  • §2 LA RÈGLE (arbitrage n°2), CHAQUE BRANCHE ATTEIGNABLE (#63) — formes COPIÉES DU RÉEL (le flux
       EDGAR de RVMD relevé le 2026-09-05) : l'acceptation tient tant que le fait connu est le dernier ;
       elle TOMBE sur le 8-K du 2026-09-01 (accord important) ; un 8-K de pure forme (9.01) ne la fait
       PAS tomber (c'est `ancre_substantielle` qui l'écarte, pas une copie de la règle) ; une réponse
       refaite la fait tomber ; EDGAR injoignable ⟹ `non_verifiable`, jamais « en vigueur ».
  • §3 LA POSITION : la décision la plus récente prime (un renvoi après une acceptation la remplace).
  • §4 LE PARCOURS : une acceptation en vigueur retire la question de l'alerte, même non fondée ; une
       acceptation tombée la remet DANS l'alerte en disant pourquoi ; le niveau 1 dit que la complétude
       repose sur le comité ; les décomptes distinguent le comité du contrôle ; le niveau 3 porte le PV.
  • §5 DÉTENTEURS UNIQUES (#46) : seul `comite.py` écrit au PV ; le renvoi emprunte `persist_mandate`
       (même canal que le manager) ; l'assembleur appelle `lire_registre` et `position_du_comite` ;
       le POST juge contre `ancre_substantielle`.
  • §6 LE POINT DE LECTURE : chaque champ du PV et de l'acceptation servie a son pixel (bijection
       `data-pv` ↔ contrat) ; le niveau 3 pose le bloc du comité APRÈS la preuve.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import ast
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import get_args

from app.agents.v2.comite import position_du_comite, servir_acceptation
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.parcours import (
    EtatDossier, ReponseLue, dresser_niveau1, dresser_niveau2, dresser_niveau3,
    manque_de_la_question)
from app.agents.v2.projection_memo import memo_de_l_etat
from app.contracts.comite_schema import (
    AcceptationServie, DecisionComite, DemandeAcquittement, DemandeRenvoi, FaitImportant,
    PositionComite)
from app.contracts.framework_answer_schema import (
    ControlesManager, FondationServie, FrameworkAnswerServie, ManagerVerdict, Reponse)
from app.contracts.memo_projete_schema import PointProjete, RetenueParLeComite
from app.contracts.parcours_schema import Manque, PreuvesQuestion
from app.contracts.readiness_report_schema import GapItem
from app.knowledge.material_events import (
    MaterialEvent, MaterialEventLookup, ancre_substantielle, parse_material_events)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

b = Bilan()
FICHIER = load_frameworks()
VER = FICHIER.schema_version
T_ACC = datetime(2026, 8, 28, 9, 30, tzinfo=timezone.utc)


def refuse(fn, motif: str, label: str) -> None:
    """Un refus prononcé par une AUTRE règle est un FAIL (4ᵉ faux vert)."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        b.check(motif in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
        return
    b.check(False, f"{label} — ACCEPTÉ")


# ── Le flux EDGAR RÉEL de RVMD (copie conforme de `check_material_events`, relevé le 2026-09-05) ─
PAYLOAD = {"filings": {"recent": {
    "form": ["4", "8-K", "144", "8-K", "4", "10-Q", "8-K", "SCHEDULE 13G", "8-K", "10-K"],
    "filingDate": ["2026-09-02", "2026-09-01", "2026-08-31", "2026-08-26", "2026-08-25",
                   "2026-08-05", "2026-08-05", "2026-08-14", "2026-06-22", "2026-02-25"],
    "reportDate": ["", "2026-08-27", "", "2026-08-26", "", "2026-06-30", "2026-08-05",
                   "", "2026-06-18", "2025-12-31"],
    "items": ["", "1.01,2.03", "", "8.01", "", "", "2.02,9.01", "", "5.02,5.07", ""],
    "accessionNumber": ["0001193125-26-380277", "0001193125-26-377362", "0001968582-26-000898",
                        "0001193125-26-366931", "0001610717-26-000388", "0001193125-26-335104",
                        "0001193125-26-335039", "0001104659-26-097049", "0001193125-26-000001",
                        "0001193125-26-100000"]}}}
TOUS = parse_material_events(PAYLOAD, 1628171)          # plus récent d'abord
FDA = next(e for e in TOUS if e.accession == "0001193125-26-366931")      # 8.01, 2026-08-26
ACCORD = next(e for e in TOUS if e.accession == "0001193125-26-377362")   # 1.01/2.03, 2026-09-01
# CONSTRUIT, et dit comme tel : un 8-K de pure forme (9.01 seul) déposé après l'acceptation. Le flux
# RVMD relevé n'en porte pas après le 2026-08-26 ; sa forme est celle du 8-K réel du 2026-08-05.
FORMEL = MaterialEvent(form="8-K", event_date=date(2026, 9, 3), filing_date=date(2026, 9, 3),
                       items=("9.01",), accession="0001193125-26-390000")


def ancre(*evts) -> MaterialEventLookup:
    """L'ancre telle que le parcours la lit : le flux BRUT, passé par `ancre_substantielle`."""
    evts = sorted(evts, key=lambda e: (e.filing_date, e.event_date), reverse=True)
    brut = (MaterialEventLookup(status="found", event=evts[0], cik=1628171, recents=tuple(evts))
            if evts else MaterialEventLookup(status="none", cik=1628171))
    return ancre_substantielle(brut)


INJOIGNABLE = MaterialEventLookup(status="unavailable", raison="EDGAR 503")
CONNU_FDA = FaitImportant(publie_le=FDA.filing_date, accession=FDA.accession, resume=FDA.resume())


def decision(i=1, action="acquitter", *, answer_id=469, ancre_etat="found", fait=CONNU_FDA,
             mandat_id=None, quand=T_ACC, qid="qf_7", motif="on décide sans la marge des pairs"):
    return DecisionComite(
        id=i, ticker_id="RVMD", framework_id="qualite_financiere", framework_version=VER,
        question_id=qid, action=action, answer_id=answer_id, mandat_id=mandat_id,
        auteur="J. Langlois-Meurinne", motif=motif, ancre_etat=ancre_etat,
        fait_connu=fait if ancre_etat == "found" else None, decide_le=quand)


ACC = decision()
RENVOI = decision(2, "renvoyer", answer_id=None, mandat_id=700,
                  quand=datetime(2026, 9, 2, tzinfo=timezone.utc))

# ══ §1 LE CONTRAT ═════════════════════════════════════════════════════════════════════════════
print("[1] le contrat refuse un procès-verbal incomplet (arbitrage n°1)")
refuse(lambda: DemandeAcquittement(answer_id=1, auteur="x", motif="   "), "texte blanc",
       "§1 une justification BLANCHE est refusée")
refuse(lambda: DemandeAcquittement(answer_id=1, auteur=" ", motif="parce que"), "texte blanc",
       "§1 un PV non SIGNÉ est refusé")
refuse(lambda: DemandeRenvoi(auteur="x", motif="m", mandat="\n\t"), "texte blanc",
       "§1 un renvoi sans CONSIGNE de recherche est refusé")
b.check(DemandeAcquittement(answer_id=1, auteur="  x ", motif=" m ").auteur == "x",
        "§1 les blancs de bord sont retirés (le PV garde le texte, pas la saisie)")
refuse(lambda: decision(answer_id=None), "version du dossier",
       "§1 acquitter SANS réponse précise est refusé")
refuse(lambda: decision(mandat_id=3), "n'ouvre aucune recherche",
       "§1 acquitter en portant un mandat est refusé")
refuse(lambda: decision(ancre_etat="unavailable"), "ne pourrait jamais tomber",
       "§1 acquitter sur des faits ILLISIBLES est refusé (on ne pourrait jamais la faire tomber)")
refuse(lambda: decision(2, "renvoyer", answer_id=None), "Écart B",
       "§1 renvoyer sans mandat est refusé (Écart B)")
refuse(lambda: DecisionComite(**{**ACC.model_dump(), "fait_connu": None}), "un fait est cité ssi",
       "§1 une ancre « trouvée » sans fait cité est refusée (#49)")
refuse(lambda: DecisionComite(**{**ACC.model_dump(), "ancre_etat": "none"}), "un fait est cité ssi",
       "§1 un fait cité sous une ancre « aucun fait » est refusé (#49)")
refuse(lambda: AcceptationServie(decision=ACC, etat="tombee_fait_nouveau", motif_etat="x"),
       "NOMME ce fait", "§1 une acceptation tombée sur un fait NOMME le fait")
refuse(lambda: AcceptationServie(decision=ACC, etat="en_vigueur", motif_etat="x",
                                 fait_nouveau=CONNU_FDA),
       "NOMME ce fait", "§1 une acceptation en vigueur ne porte aucun fait nouveau")
refuse(lambda: AcceptationServie(decision=RENVOI, etat="en_vigueur", motif_etat="x"),
       "porte une décision `acquitter`", "§1 un renvoi n'est pas une acceptation")
refuse(lambda: PositionComite(derniere=RENVOI,
                              acceptation=AcceptationServie(decision=ACC, etat="en_vigueur",
                                                            motif_etat="x")),
       "ssi la dernière décision", "§1 une acceptation servie sous un renvoi plus récent est refusée")
acc_ok = AcceptationServie(decision=ACC, etat="en_vigueur", motif_etat="x")
refuse(lambda: Manque(framework_id="f", libelle_framework="L", question_id="q", enonce="e",
                      nature="sans_reponse", cause="pas_encore_cherchee", explication="x",
                      acceptation_tombee=acc_ok),
       "EN VIGUEUR", "§1 un manque porteur d'une acceptation EN VIGUEUR est refusé")

# ══ §2 LA RÈGLE ═══════════════════════════════════════════════════════════════════════════════
print("[2] la règle : l'acceptation tient-elle aujourd'hui ? (arbitrage n°2)")
COURANTES = frozenset({469})


def servie(dec=ACC, *, courantes=COURANTES, a=None):
    return servir_acceptation(dec, reponses_courantes=courantes, ancre=a if a is not None
                              else ancre(FDA))


s_ok = servie()
b.check(s_ok.etat == "en_vigueur",
        f"§2 le fait connu est toujours le dernier → `en_vigueur` — obtenu {s_ok.etat}")
s_ac = servie(a=ancre(FDA, ACCORD))
b.check(s_ac.etat == "tombee_fait_nouveau",
        f"§2 RÉEL : le 8-K du 2026-09-01 (accord important) publié après → TOMBE — obtenu {s_ac.etat}")
b.check(s_ac.fait_nouveau is not None and s_ac.fait_nouveau.accession == ACCORD.accession
        and "2026-08-27" in s_ac.motif_etat,
        "§2 l'acceptation tombée NOMME le fait (quel dépôt, quelle date) — le comité sait quoi relire")
s_fo = servie(a=ancre(FDA, FORMEL))
b.check(s_fo.etat == "en_vigueur",
        f"§2 un 8-K de PURE FORME (9.01) ne fait rien tomber — obtenu {s_fo.etat}")
s_rp = servie(courantes=frozenset({512}))
b.check(s_rp.etat == "tombee_reponse_remplacee",
        f"§2 l'analyse a été REFAITE → le comité avait lu un autre dossier — obtenu {s_rp.etat}")
s_rp2 = servie(courantes=frozenset({512}), a=INJOIGNABLE)
b.check(s_rp2.etat == "tombee_reponse_remplacee",
        "§2 préséance : une réponse remplacée se SAIT sans EDGAR (elle passe devant « non vérifiable »)")
s_nv = servie(a=INJOIGNABLE)
b.check(s_nv.etat == "non_verifiable",
        f"§2 EDGAR injoignable → `non_verifiable`, JAMAIS « en vigueur » (#49) — obtenu {s_nv.etat}")
AVANT_FDA = datetime(2026, 8, 20, 14, tzinfo=timezone.utc)
s_none = servie(decision(ancre_etat="none", quand=AVANT_FDA), a=ancre(FDA))
b.check(s_none.etat == "tombee_fait_nouveau",
        "§2 le comité savait qu'AUCUN fait n'était publié ; l'approbation FDA arrive → elle tombe")
s_none2 = servie(decision(ancre_etat="none"), a=ancre())
b.check(s_none2.etat == "en_vigueur",
        "§2 aucun fait avant, aucun fait maintenant → en vigueur (`none` est un état CONNU)")
ANCIEN = FaitImportant(publie_le=date(2026, 6, 22), accession="0001193125-26-000001", resume="8-K")
s_old = servie(decision(fait=CONNU_FDA), a=ancre(next(e for e in TOUS
                                                    if e.accession == ANCIEN.accession)))
b.check(s_old.etat == "en_vigueur",
        "§2 un fait PLUS ANCIEN que celui connu n'est pas « nouveau » (le flux a reculé, rien n'est publié)")
# CONSTRUIT : un second 8-K substantiel déposé le jour même de l'approbation (forme réelle 5.02).
MEME_JOUR = MaterialEvent(form="8-K", event_date=FDA.event_date, filing_date=FDA.filing_date,
                          items=("5.02",), accession="0001193125-26-366999")
LE_JOUR = datetime(2026, 8, 26, 15, tzinfo=timezone.utc)      # 11 h à New York, le jour du dépôt
s_mj = servie(decision(quand=LE_JOUR), a=ancre(FDA, MEME_JOUR))
b.check(s_mj.etat == "tombee_fait_nouveau",
        "§2 un AUTRE fait déposé le JOUR de la décision fait tomber (rien ne prouve qu'il la précédait)")
s_mj2 = servie(decision(quand=LE_JOUR), a=ancre(FDA))
b.check(s_mj2.etat == "en_vigueur",
        "§2 le fait connu lui-même, déposé le jour de la décision, ne fait pas tomber")
s_av = servie(a=ancre(FDA, MEME_JOUR))
b.check(s_av.etat == "en_vigueur",
        "§2 un fait déposé AVANT le jour de la décision était public : il ne fait pas tomber (n°2 = « après »)")
# Le cas DISCRIMINANT du fuseau (le seul où New York et UTC divergent) : décidé le 31/08 à 22 h à New
# York, soit le 1er/09 en UTC ; un 8-K déposé le 31/08 est du JOUR de la décision à New York (donc
# nouveau), mais « de la veille » en UTC (donc public avant). CONSTRUIT, forme réelle 8.01.
SOIR = datetime(2026, 9, 1, 2, tzinfo=timezone.utc)
LE_31 = MaterialEvent(form="8-K", event_date=date(2026, 8, 31), filing_date=date(2026, 8, 31),
                      items=("8.01",), accession="0001193125-26-375000")
s_tz = servie(decision(quand=SOIR), a=ancre(FDA, LE_31))
b.check(s_tz.etat == "tombee_fait_nouveau",
        "§2 le jour d'une décision se lit à NEW YORK : décidé le 31/08 au soir (1er/09 UTC), le 8-K du "
        f"31/08 est du jour même, donc nouveau — obtenu {s_tz.etat}")

# ══ §3 LA POSITION ════════════════════════════════════════════════════════════════════════════
print("[3] la position : la décision la plus récente prime")
p_r = position_du_comite([RENVOI, ACC], reponses_courantes=COURANTES, ancre=ancre(FDA))
b.check(p_r is not None and p_r.derniere.action == "renvoyer" and p_r.acceptation is None,
        "§3 un renvoi APRÈS une acceptation la remplace : aucune acceptation servie")
ACC2 = decision(3, quand=datetime(2026, 9, 3, tzinfo=timezone.utc))
p_a = position_du_comite([ACC2, RENVOI, ACC], reponses_courantes=COURANTES, ancre=ancre(FDA))
b.check(p_a is not None and p_a.acceptation is not None and p_a.acceptation.decision.id == 3,
        "§3 une acceptation APRÈS un renvoi est la position du comité")
b.check(position_du_comite([], reponses_courantes=COURANTES, ancre=ancre(FDA)) is None,
        "§3 un registre vide → aucune position (le comité ne s'est pas prononcé)")

# ══ §4 LE PARCOURS ════════════════════════════════════════════════════════════════════════════
print("[4] le parcours lit l'acceptation")
OK4 = ControlesManager(completude="ok", fondation="ok", honnetete_approximation="sans_objet",
                       non_substitution="ok")


def lue(i, statut, *, verdict="acquitte", act="courante", qid="qf_7"):
    commun = dict(framework_id="qualite_financiere", framework_version=VER, question_id=qid,
                  ticker_id="RVMD", analyste="a", statut=statut)
    if statut == "repondu":
        a = FrameworkAnswerServie(
            **commun, manager=(ManagerVerdict(verdict="acquitte", controles=OK4, motif="ok")
                               if verdict == "acquitte" else None),
            reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
            fondation=FondationServie(cited_entry_ids=[10], rang_derive="A",
                                      nature_effective="mesure", actualite=act,
                                      motif_actualite=f"motif-{act}"))
    else:
        a = FrameworkAnswerServie(
            **commun, manager=ManagerVerdict(verdict="acquitte", controles=OK4, motif="ok"),
            gap=GapItem(dimension="d", champs_cibles=[qid], manque="m", priorite="haute",
                        coverage_actuelle="0/1"))
    return ReponseLue(answer_id=i, servie=a, verdict=verdict, controles=OK4, motif_revue="ok",
                      etat_revue="revue")


NF = lue(469, "non_fondable")


def manque(acc):
    return manque_de_la_question(
        framework_id="qualite_financiere", libelle_framework="Qualité financière",
        question_id="qf_7", enonce="e", applicable=True, dispensee=False, reponses=[NF],
        collecte=None, mandat_ouvert_id=None, acceptation=acc)


b.check(manque(None) is not None, "§4 témoin : une réponse NON FONDÉE sans décision est un manque")
b.check(manque(s_ok) is None,
        "§4 une acceptation EN VIGUEUR retire la question de l'alerte, même non fondée (n°1)")
m_t = manque(s_ac)
b.check(m_t is not None and m_t.acceptation_tombee is not None
        and m_t.acceptation_tombee.etat == "tombee_fait_nouveau",
        "§4 une acceptation TOMBÉE remet la question dans l'alerte ET dit pourquoi (n°2)")
m_nv = manque(s_nv)
b.check(m_nv is not None and m_nv.acceptation_tombee is not None,
        "§4 une acceptation NON VÉRIFIABLE ne protège rien (elle ne fonde pas une décision du jour)")

seule_qf7 = {f.id: (frozenset({"qf_7"}) if f.id == "qualite_financiere" else frozenset())
             for f in FICHIER.frameworks}


def etat(comite=None, registre=None, reponses=(NF,)):
    return EtatDossier(
        ticker_id="RVMD", fichier=FICHIER, archetype="pre_revenus", reponses=list(reponses),
        pieces={}, applicables=seule_qf7,
        dispenses={f.id: frozenset() for f in FICHIER.frameworks}, mandats_ouverts={},
        collecte={}, genere_le=T_ACC, registre=registre or {}, comite=comite or {})


def memo_de(e):
    """La note du niveau 1. Un refus du contrat (point mal formé) est un FAIL NOMMÉ ; la suite se
    mesure sur une note sans comité, pour que le script atteigne quand même ses asserts §4bis."""
    try:
        return memo_de_l_etat(e, genere_le=T_ACC)
    except Exception as ex:  # noqa: BLE001
        b.check(False, f"§4 la note du niveau 1 est REFUSÉE par son contrat : {str(ex)[:160]}")
        from dataclasses import replace
        return memo_de_l_etat(replace(e, comite={}), genere_le=T_ACC)


CLE = ("qualite_financiere", "qf_7")
pos_ok = position_du_comite([ACC], reponses_courantes=COURANTES, ancre=ancre(FDA))
e_acc = etat(comite={CLE: pos_ok}, registre={CLE: [ACC]})
n1 = dresser_niveau1(e_acc, memo_de(e_acc))
b.check(n1.peut_on_decider.etat == "dossier_complet",
        f"§4 niveau 1 : la seule question applicable est acceptée → complet — obtenu {n1.peut_on_decider.etat}")
b.check("acceptée(s) par le comité" in n1.peut_on_decider.motif,
        "§4 niveau 1 : le motif DIT que la complétude repose sur le comité (≠ dossier sans faiblesse)")
s_qf = next(s for s in n1.frameworks if s.framework_id == "qualite_financiere")
b.check(s_qf.n_acceptees_comite == 1 and s_qf.n_acquittees == 1,
        f"§4 comité et contrôle COMPTÉS À PART — obtenu comité={s_qf.n_acceptees_comite} "
        f"contrôle={s_qf.n_acquittees}")
e_ok = etat()
n1_temoin = dresser_niveau1(e_ok, memo_de(e_ok))
b.check(n1_temoin.peut_on_decider.etat == "dossier_incomplet",
        "§4 témoin : sans l'acceptation, le même dossier est incomplet")
pos_tb = position_du_comite([ACC], reponses_courantes=COURANTES, ancre=ancre(FDA, ACCORD))
e_tb = etat(comite={CLE: pos_tb}, registre={CLE: [ACC]})
n1_tb = dresser_niveau1(e_tb, memo_de(e_tb))
b.check(n1_tb.peut_on_decider.etat == "dossier_incomplet"
        and n1_tb.peut_on_decider.manques[0].acceptation_tombee is not None,
        "§4 niveau 1 : une acceptation tombée → la question REPASSE en alerte, avec l'acceptation")
b.check(next(s for s in n1_tb.frameworks
             if s.framework_id == "qualite_financiere").n_acceptees_comite == 0,
        "§4 une acceptation tombée n'est pas comptée acceptée")
n2 = dresser_niveau2(e_acc, "qualite_financiere")
lq7 = next(lq for lq in n2.questions if lq.question_id == "qf_7")
b.check(lq7.comite is not None and lq7.comite.acceptation.etat == "en_vigueur" and lq7.manque is None,
        "§4 niveau 2 : la ligne porte la position du comité")
e_hist = etat(comite={CLE: position_du_comite([RENVOI, ACC], reponses_courantes=COURANTES,
                                              ancre=ancre(FDA))},
              registre={CLE: [RENVOI, ACC]})
# Un refus du contrat en cours de route est un FAIL NOMMÉ, jamais la mort du script avant son bilan.
try:
    n3 = dresser_niveau3(e_hist, "qualite_financiere", "qf_7")
    ordre = ([d.id for d in n3.registre], n3.comite.derniere.id if n3.comite else None)
except Exception as e:  # noqa: BLE001
    n3, ordre = None, f"REFUSÉ : {e}"
b.check(ordre == ([2, 1], 2),
        f"§4 niveau 3 : le PV COMPLET, le plus récent d'abord, et la position en tête — obtenu {ordre}")
n3_vide = dresser_niveau3(etat(), "qualite_financiere", "qf_7")
b.check(n3_vide.comite is None and n3_vide.registre == [],
        "§4 niveau 3 : sans décision, ni position ni PV (pas de faux « le comité a statué »)")
refuse(lambda: PreuvesQuestion(**{**n3_vide.model_dump(), "comite": p_r.model_dump(),
                                  "registre": [ACC.model_dump(),
                                                                  RENVOI.model_dump()]}),
       "la plus récente", "§4 une position qui n'est pas la tête du registre est refusée")

# ══ §4bis LA NOTE DE COMITÉ (arbitrage A, 2026-09-26) ═════════════════════════════════════════
print("[4bis] la note reprend ce que le comité a retenu, marqué, avec la faiblesse surmontée")
# La forme RÉELLE d'une réponse que le comité a acceptée malgré le contrôle : `acquitter` abandonne
# le mandat ouvert, donc `charger_etat_dossier` la sert SANS avis attaché (`renvoi_a_emettre`), avec
# le verdict et le motif de la revue recalculés à côté. Pas un avis « renvoyé » inventé : sans
# mandat, le contrat l'interdirait (Écart B).
FAIBLESSE = "② actualité ko : la marge publiée précède l'approbation FDA du 2026-08-26"
NF_FAIBLE = ReponseLue(answer_id=469, servie=NF.servie.model_copy(update={"manager": None}),
                       verdict="renvoye", controles=OK4, motif_revue=FAIBLESSE,
                       etat_revue="renvoi_a_emettre")


def note_qf(comite):
    e = etat(comite=comite, registre={CLE: [ACC]}, reponses=(NF_FAIBLE,))
    try:
        return memo_de_l_etat(e, genere_le=T_ACC).par_bloc()[
            next(f.bloc_memo for f in FICHIER.frameworks if f.id == "qualite_financiere")]
    except Exception as e:  # noqa: BLE001 — un refus est un FAIL nommé, pas la mort du script
        return f"REFUSÉ : {e}"


r_acc = note_qf({CLE: pos_ok})
pt = r_acc.points[0] if not isinstance(r_acc, str) and r_acc.points else None
b.check(pt is not None and pt.question_id == "qf_7" and pt.retenue_par_comite is not None,
        f"§4bis une acceptation EN VIGUEUR fait entrer la réponse dans la note — obtenu {r_acc if pt is None else 'ok'}")
b.check(pt is not None and pt.retenue_par_comite.faiblesse == FAIBLESSE
        and pt.retenue_par_comite.acceptation.decision.auteur == ACC.auteur
        and pt.retenue_par_comite.acceptation.decision.motif == ACC.motif,
        "§4bis … marquée : la faiblesse (lue à la revue du jour), qui a tranché, et pourquoi")
b.check(not isinstance(r_acc, str) and r_acc.etat == "instruite"
        and r_acc.reponses_non_acquittees == 0
        and "1 retenu(s) par le comité malgré leur faiblesse" in r_acc.motif,
        f"§4bis la rubrique DIT combien de points reposent sur le comité — obtenu "
        f"{r_acc if isinstance(r_acc, str) else r_acc.motif}")
r_sans = note_qf({})
b.check(not isinstance(r_sans, str) and r_sans.points == [] and r_sans.reponses_non_acquittees == 1,
        "§4bis témoin : sans décision du comité, la réponse faible reste hors de la note, comptée")
r_tb = note_qf({CLE: pos_tb})
b.check(not isinstance(r_tb, str) and r_tb.points == [],
        "§4bis une acceptation TOMBÉE (fait nouveau) sort de la note : la question repasse en alerte")
pos_autre = position_du_comite([decision(answer_id=470)], reponses_courantes=frozenset({469, 470}),
                               ancre=ancre(FDA))
r_autre = note_qf({CLE: pos_autre})
b.check(not isinstance(r_autre, str) and r_autre.points == [],
        "§4bis une acceptation d'une AUTRE version de la réponse ne couvre pas celle-ci")
r_renv = note_qf({CLE: p_r})
b.check(not isinstance(r_renv, str) and r_renv.points == [],
        "§4bis un renvoi POSTÉRIEUR à l'acceptation la remplace : rien n'entre dans la note")
try:
    r_acq = memo_de_l_etat(e_acc, genere_le=T_ACC).par_bloc()[
        next(f.bloc_memo for f in FICHIER.frameworks if f.id == "qualite_financiere")]
except Exception as e:  # noqa: BLE001
    r_acq = f"REFUSÉ : {e}"
b.check(not isinstance(r_acq, str) and len(r_acq.points) == 1
        and r_acq.points[0].retenue_par_comite is None,
        "§4bis une réponse ACQUITTÉE par le contrôle n'est pas marquée « retenue malgré » même si le "
        "comité l'a aussi acceptée (pas de faiblesse inventée)")
if pt is not None:
    refuse(lambda: RetenueParLeComite(acceptation=s_ac, faiblesse="x"), "ne fonde plus rien",
           "§4bis contrat : une acceptation tombée ne se porte pas au mémo")
    refuse(lambda: PointProjete(**{**pt.model_dump(), "answer_id": 470}), "UNE version du dossier",
           "§4bis contrat : la décision ne se prête pas à une autre réponse")
    refuse(lambda: PointProjete(**{**pt.model_dump(), "answer": NF.servie.model_dump()}),
           "inventerait une faiblesse",
           "§4bis contrat : un point acquitté ne peut pas être marqué « retenu malgré »")
    refuse(lambda: PointProjete(**{**pt.model_dump(), "retenue_par_comite": None}),
           "n'est pas acquittée", "§4bis contrat : sans décision du comité, le non-acquitté reste refusé")
else:
    b.check(False, "§4bis contrat non mesuré : aucun point retenu à muter")
assembleurs = sorted(str(p) for p in [*Path("app").rglob("*.py"), *Path("tools").rglob("*.py")]
                     if "projeter_memo(" in strip_code(p.read_text(encoding="utf-8"))
                     and p.name != "projection_memo.py")
b.check(assembleurs == [],
        f"§4bis SEUL `memo_de_l_etat` assemble la note (aucun `projeter_memo` recopié) — obtenu {assembleurs}")
b.check(Path("/frontend/components/v2/DossierComite.js").exists()
        and "retenue_par_comite" in Path("/frontend/components/v2/DossierComite.js").read_text(),
        "§4bis point de lecture : l'écran de la note LIT la mention du comité")

# ══ §5 DÉTENTEURS UNIQUES ═════════════════════════════════════════════════════════════════════
print("[5] détenteurs uniques (#46)")


def appels(path: str, fonction: str) -> set[str]:
    arbre = ast.parse(Path(path).read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == fonction:
            return {(c.func.id if isinstance(c.func, ast.Name) else
                     c.func.attr if isinstance(c.func, ast.Attribute) else "")
                    for c in ast.walk(n) if isinstance(c, ast.Call)}
    return set()


ecrivains = []
for p in sorted(Path("app").rglob("*.py")):
    if re.search(r"INSERT\s+INTO\s+comite_decisions", p.read_text(encoding="utf-8")):
        ecrivains.append(str(p))
b.check(ecrivains == ["app/agents/v2/comite.py"],
        f"§5 SEUL `comite.py` inscrit au procès-verbal — obtenu {ecrivains}")
a_renv = appels("app/agents/v2/comite.py", "renvoyer")
b.check("persist_mandate" in a_renv,
        "§5 renvoyer emprunte `persist_mandate` — le MÊME canal que le renvoi du manager (§8.2)")
code_comite = Path("app/agents/v2/comite.py").read_text(encoding="utf-8")
b.check("INSERT INTO framework_mandates" not in code_comite,
        "§5 aucun second chemin d'écriture de mandat dans `comite.py`")
b.check("abandonner_mandat" in appels("app/agents/v2/comite.py", "_arreter_la_recherche_en_cours")
        and "id_du_mandat_ouvert" in appels("app/agents/v2/comite.py",
                                            "_arreter_la_recherche_en_cours"),
        "§5 la recherche en cours s'arrête par les détenteurs du cycle du mandat (manager_persist)")
a_ch = appels("app/agents/v2/parcours.py", "charger_etat_dossier")
b.check({"lire_registre", "position_du_comite"} <= a_ch,
        "§5 l'assembleur APPELLE `lire_registre` et `position_du_comite` (jamais une ré-écriture)")
a_dec = appels("app/api/parcours_v2.py", "_decider")
b.check("ancre_substantielle" in a_dec,
        "§5 le POST juge contre l'ancre qui PÈSE, la même qui jugera l'acceptation à la lecture")
code_parc = strip_code(Path("app/agents/v2/parcours.py").read_text(encoding="utf-8"))
b.check("INSERT" not in code_parc and "UPDATE" not in code_parc,
        "§5 l'assembleur n'écrit toujours RIEN : l'état d'une acceptation se recalcule à la lecture")

# ══ §6 LE POINT DE LECTURE ════════════════════════════════════════════════════════════════════
print("[6] le point de lecture — chaque champ du PV a son pixel")
FRONT = Path("/frontend")
REG = FRONT / "components/v2/RegistreComite.js"
N3 = FRONT / "pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/q/[question_id].js"
if not (REG.exists() and N3.exists()):
    b.check(False, f"§6 écrans absents de {FRONT} — section non mesurée (montage /frontend manquant ?)")
else:
    def feuilles(modele, prefixe=""):
        out = []
        for nom, f in modele.model_fields.items():
            sous = [x for x in (get_args(f.annotation) or (f.annotation,)) if hasattr(x, "model_fields")]
            out += feuilles(sous[0], f"{prefixe}{nom}.") if sous else [f"{prefixe}{nom}"]
        return out

    attendus = set(feuilles(DecisionComite)) | {
        f"acceptation.{c}" for c in feuilles(AcceptationServie) if not c.startswith("decision.")}
    jsx = re.sub(r"/\*.*?\*/", "", REG.read_text(encoding="utf-8"), flags=re.S)
    jsx = re.sub(r"(?m)^\s*//.*$", "", jsx)
    marques = set(re.findall(r'data-pv="([a-z_.]+)"', jsx))
    b.require(attendus, 21, "§6 le PV (16 champs) et l'acceptation servie (5) ont 21 champs terminaux")
    b.check(not (attendus - marques),
            f"§6 tout champ du PV a son pixel — sans pixel : {sorted(attendus - marques)}")
    b.check(not (marques - attendus),
            f"§6 … et tout pixel rend un champ RÉEL — pixels sans champ : {sorted(marques - attendus)}")
    n3 = N3.read_text(encoding="utf-8")
    i_preuve, i_comite = n3.find("d.preuves.map(pr =>"), n3.find("<RegistreComite")
    b.check(0 <= i_preuve < i_comite,
            "§6 le comité décide APRÈS avoir lu la preuve (le bloc suit les réponses au niveau 3)")

sys.exit(b.summary())
