"""Vérification de la RELANCE BORNÉE et de la RÉINITIALISATION (#137, point 17 et 17-bis).

Sans réseau, sans modèle, sans base. L'écriture au PV est éprouvée contre la vraie base par
`check_comite_persist.py` (ROLLBACK), la table par `negatif_058.sh`.

CE QUE FERAIT UN VRAI FONDS. Une décision du comité fait foi jusqu'à un fait nouveau : l'analyste ne
la défait pas en refaisant son travail. Une relance ne refait donc que l'OUVERT ; seul le gérant
rouvre une question close, par un geste tracé au procès-verbal.

  • §1 LE CONTRAT : `reinitialiser` est une décision du PV (signée, motivée), sans mandat, avec ou sans
       réponse relevée ; renvoyer et réinitialiser sont les décisions qui ROUVRENT.
  • §2 LA RÈGLE (`manque_de_la_question`, branche 1ter) : après un renvoi ou une réinitialisation,
       seules les réponses écrites APRÈS comptent ; aucune → `rouverte_comite`, même si une réponse
       antérieure tenait ; une réponse postérieure qui tient referme ; une acceptation postérieure
       aussi (la dernière décision prime).
  • §3 LE PÉRIMÈTRE (`questions_a_relancer`) : chaque question tombe dans ouverte / close avec sa
       raison ; un émetteur non classé est refusé.
  • §4 DÉTENTEURS ET ORDRE : le passage de chapitre calcule son périmètre par le détenteur, APRÈS la
       lecture des dépôts et AVANT la collecte ; la réinitialisation arrête la recherche en cours par
       le cycle du mandat ; le chapitre ne réinitialise que les questions applicables.
  • §5 LE POINT DE LECTURE : les écrans nomment la réinitialisation et la question rouverte.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import ast
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agents.v2.comite import position_du_comite
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.parcours import (
    EmetteurNonClasse, EtatDossier, ReponseLue, manque_de_la_question, questions_a_relancer)
from app.contracts.comite_schema import (
    ACTIONS_OUVRANTES, DecisionComite, DemandeReinitialisation)
from app.contracts.framework_answer_schema import (
    ControlesManager, FondationServie, FrameworkAnswerServie, ManagerVerdict, Reponse)
from app.contracts.readiness_report_schema import GapItem
from app.knowledge.material_events import MaterialEventLookup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

b = Bilan()
FICHIER = load_frameworks()
VER = FICHIER.schema_version
T_REP = datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc)      # la réponse instruite
T_DEC = datetime(2026, 10, 17, 9, 30, tzinfo=timezone.utc)     # le geste du comité / du gérant
APRES = T_DEC + timedelta(hours=2)
AUCUN_FAIT = MaterialEventLookup(status="none", cik=1045810)


def refuse(fn, motif: str, label: str) -> None:
    """Un refus prononcé par une AUTRE règle est un FAIL (4ᵉ faux vert)."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        b.check(motif in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
        return
    b.check(False, f"{label} — ACCEPTÉ")


def decision(i, action, *, answer_id=None, mandat_id=None, quand=T_DEC, qid="qf_6"):
    return DecisionComite(
        id=i, ticker_id="NVDA", framework_id="qualite_financiere", framework_version=VER,
        question_id=qid, action=action, answer_id=answer_id, mandat_id=mandat_id,
        auteur="J. Langlois-Meurinne", motif="reconstruction du test (#127)", ancre_etat="none",
        decide_le=quand)


OK4 = ControlesManager(completude="ok", fondation="ok", honnetete_approximation="sans_objet",
                       non_substitution="ok")


def lue(i, statut="repondu", *, quand=T_REP, qid="qf_6", analyste="a", verdict="acquitte"):
    """Formes du réel : NVDA qf_6 #1289 (répondue, acquittée, courante)."""
    commun = dict(framework_id="qualite_financiere", framework_version=VER, question_id=qid,
                  ticker_id="NVDA", analyste=analyste, statut=statut,
                  manager=(ManagerVerdict(verdict="acquitte", controles=OK4, motif="ok")
                           if verdict == "acquitte" else None))
    if statut == "repondu":
        a = FrameworkAnswerServie(
            **commun, reponse=Reponse(verbatim="part faible", chiffres_cles=[{
                "id": "chiffre", "unite": "%", "valeur": 1.0, "date_ou_periode": "exercice 2026"}]),
            fondation=FondationServie(cited_entry_ids=[10], rang_derive="A",
                                      nature_effective="mesure", actualite="courante",
                                      motif_actualite="courante"))
    else:
        a = FrameworkAnswerServie(
            **commun, gap=GapItem(dimension="d", champs_cibles=[qid], manque="m", priorite="haute",
                                  coverage_actuelle="0/1"))
    return ReponseLue(answer_id=i, servie=a, verdict=verdict, controles=OK4, motif_revue="ok",
                      etat_revue="revue", cree_le=quand)


def manque(reponses, ouvrante=None, acceptation=None):
    return manque_de_la_question(
        framework_id="qualite_financiere", libelle_framework="Qualité financière",
        question_id="qf_6", enonce="e", applicable=True, dispensee=False, reponses=list(reponses),
        collecte=None, mandat_ouvert_id=None, acceptation=acceptation, decision_ouvrante=ouvrante)


# ══ §1 LE CONTRAT ═════════════════════════════════════════════════════════════════════════════
print("[1] le contrat — la réinitialisation est une décision du PV")
REINIT = decision(1, "reinitialiser", answer_id=1289)
RENVOI = decision(2, "renvoyer", mandat_id=700)
b.check(REINIT.action == "reinitialiser" and REINIT.mandat_id is None,
        "§1 une réinitialisation s'archive, en relevant la réponse mise de côté")
b.check(decision(3, "reinitialiser").answer_id is None,
        "§1 … et sans réponse : on réinitialise aussi une question qui n'en a pas")
refuse(lambda: decision(4, "reinitialiser", mandat_id=700), "relance bornée",
       "§1 une réinitialisation qui porterait un mandat est refusée (la question repart par la relance)")
refuse(lambda: DemandeReinitialisation(auteur="J. L-M", motif="  "), "texte blanc",
       "§1 une réinitialisation non MOTIVÉE est refusée")
refuse(lambda: DemandeReinitialisation(auteur=" ", motif="reconstruction"), "texte blanc",
       "§1 une réinitialisation non SIGNÉE est refusée")
b.check(set(ACTIONS_OUVRANTES) == {"renvoyer", "reinitialiser"},
        f"§1 renvoyer et réinitialiser ROUVRENT, accepter ferme — obtenu {ACTIONS_OUVRANTES}")

# ══ §2 LA RÈGLE ═══════════════════════════════════════════════════════════════════════════════
print("[2] la règle — seules les réponses écrites après le geste comptent")
TIENT = lue(1289)
b.check(manque([TIENT]) is None, "§2 témoin : la réponse NVDA qf_6 acquittée et courante TIENT")
m_ri = manque([TIENT], ouvrante=REINIT)
b.check(m_ri is not None and (m_ri.nature, m_ri.cause) == ("rouverte_comite", "reinitialisation"),
        f"§2 RÉINITIALISÉE : une réponse antérieure qui tenait ne ferme plus — obtenu "
        f"{m_ri and (m_ri.nature, m_ri.cause)}")
b.check(m_ri is not None and "J. Langlois-Meurinne" in m_ri.explication
        and "reconstruction du test" in m_ri.explication and "2026-10-17" in m_ri.explication,
        "§2 le manque rouvert dit QUI, QUAND et POURQUOI (le PV, pas un générique)")
m_rv = manque([TIENT], ouvrante=RENVOI)
b.check(m_rv is not None and (m_rv.nature, m_rv.cause) == ("rouverte_comite", "renvoi_comite"),
        f"§2 RENVOYÉE PAR LE COMITÉ : la question rouvre même si la réponse tenait — obtenu "
        f"{m_rv and (m_rv.nature, m_rv.cause)}")
b.check(manque([TIENT, lue(1700, quand=APRES)], ouvrante=REINIT) is None,
        "§2 une réponse écrite APRÈS la réinitialisation, et qui tient, REFERME la question")
m_nf = manque([TIENT, lue(1700, "non_fondable", quand=APRES, analyste="b")], ouvrante=REINIT)
b.check(m_nf is not None and m_nf.nature == "non_fondee",
        f"§2 après le geste, la réponse ANTÉRIEURE ne « tient » plus pour un autre analyste — "
        f"obtenu {m_nf and m_nf.nature}")
b.check(manque([lue(1289, quand=None)], ouvrante=REINIT) is not None,
        "§2 une réponse sans instant d'écriture compte comme antérieure (prudence, jamais l'inverse)")
b.check(manque([lue(1289, quand=T_DEC)], ouvrante=REINIT) is not None,
        "§2 une réponse écrite au MÊME instant que le geste ne le consomme pas (strictement après)")
refuse(lambda: manque([TIENT], ouvrante=decision(5, "acquitter", answer_id=1289)), "ouvrante",
       "§2 une ACCEPTATION passée comme décision ouvrante est refusée")
ACC_APRES = decision(6, "acquitter", answer_id=1289, quand=APRES)
pos = position_du_comite([ACC_APRES, REINIT], reponses_courantes=frozenset({1289}), ancre=AUCUN_FAIT)
b.check(pos is not None and pos.acceptation is not None and pos.acceptation.etat == "en_vigueur"
        and manque([TIENT], acceptation=pos.acceptation) is None,
        "§2 une acceptation APRÈS la réinitialisation est la position du comité : la question est close")

# ══ §3 LE PÉRIMÈTRE ═══════════════════════════════════════════════════════════════════════════
print("[3] le périmètre d'une relance — l'ouvert, et pourquoi le reste est laissé")
QF = next(f for f in FICHIER.frameworks if f.id == "qualite_financiere")
ids = [q.id for q in QF.questions]
b.require(ids[:6], 6, "§3 qualité financière a au moins six questions (fixture)")
q_tient, q_acc, q_disp, q_hors, q_nf, q_reinit = ids[:6]
rep = [lue(10, qid=q_tient), lue(11, "non_fondable", qid=q_acc), lue(12, qid=q_disp),
       lue(13, "non_fondable", qid=q_nf), lue(14, qid=q_reinit)]
reinit = decision(20, "reinitialiser", answer_id=14, qid=q_reinit)
acc = decision(21, "acquitter", answer_id=11, qid=q_acc)
comite = {("qualite_financiere", q_reinit): position_du_comite(
              [reinit], reponses_courantes=frozenset({14}), ancre=AUCUN_FAIT),
          ("qualite_financiere", q_acc): position_du_comite(
              [acc], reponses_courantes=frozenset({11}), ancre=AUCUN_FAIT)}


def etat(*, applicables="defaut", archetype="rentable"):
    app = {f.id: frozenset(q.id for q in f.questions) - {q_hors} for f in FICHIER.frameworks}
    return EtatDossier(
        ticker_id="NVDA", fichier=FICHIER, archetype=archetype, reponses=rep, pieces={},
        applicables=app if applicables == "defaut" else applicables,
        dispenses={f.id: (frozenset({q_disp}) if f.id == "qualite_financiere" else frozenset())
                   for f in FICHIER.frameworks},
        mandats_ouverts={}, collecte={}, genere_le=APRES, registre={}, comite=comite)


per = questions_a_relancer(etat(), "qualite_financiere")
attendues = tuple(q for q in ids if q not in (q_tient, q_acc, q_disp, q_hors))
b.check(per.ouvertes == attendues,
        f"§3 ouvertes = non fondée + réinitialisée + sans réponse, dans l'ordre du référentiel — "
        f"obtenu {per.ouvertes}, attendu {attendues}")
b.check(q_reinit in per.ouvertes, "§3 la question RÉINITIALISÉE est refaite, bien que sa réponse tienne")
b.check(per.closes.get(q_tient, "").startswith("à jour"),
        f"§3 la réponse qui tient n'est pas refaite (« à jour ») — obtenu {per.closes.get(q_tient)}")
b.check(per.closes.get(q_acc, "").startswith("acceptée par le comité"),
        f"§3 la question ACCEPTÉE n'est pas refaite, même non fondée — obtenu {per.closes.get(q_acc)}")
b.check(per.closes.get(q_disp) == "dispensée", f"§3 la question dispensée — {per.closes.get(q_disp)}")
b.check(per.closes.get(q_hors) == "hors sujet pour cet émetteur",
        f"§3 la question hors sujet — {per.closes.get(q_hors)}")
b.check(set(per.ouvertes).isdisjoint(per.closes) and set(per.ouvertes) | set(per.closes) == set(ids),
        "§3 chaque question tombe dans UNE case : ouverte ou close")
refuse(lambda: questions_a_relancer(
           etat(applicables={f.id: None for f in FICHIER.frameworks}, archetype=None),
           "qualite_financiere"),
       "n'est pas classé", "§3 un émetteur NON CLASSÉ est refusé (on ne sait pas ce qui est ouvert)")

# ══ §4 DÉTENTEURS ET ORDRE ════════════════════════════════════════════════════════════════════
print("[4] détenteurs uniques et ordre du passage de chapitre")


def appels(path: str, fonction: str) -> list[str]:
    arbre = ast.parse(Path(path).read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == fonction:
            return [(c.func.id if isinstance(c.func, ast.Name) else
                     c.func.attr if isinstance(c.func, ast.Attribute) else "")
                    for c in sorted((c for c in ast.walk(n) if isinstance(c, ast.Call)),
                                    key=lambda c: (c.lineno, c.col_offset))]
    return []


ch = appels("tools/executer_chaine.py", "main")
ordre = [ch.index(f) if f in ch else -1 for f in (
    "lire_les_depots_en_attente", "questions_a_relancer", "executer_collecte_framework", "repondre")]
b.check(all(x >= 0 for x in ordre) and ordre == sorted(ordre),
        f"§4 le passage lit les dépôts, PUIS calcule son périmètre, PUIS collecte et répond — "
        f"positions {ordre}")
src_ch = strip_code(Path("tools/executer_chaine.py").read_text(encoding="utf-8"))
b.check("perimetre = frozenset(relance.ouvertes)" in src_ch,
        "§4 sans --questions, le périmètre EST l'ouvert du détenteur")
b.check("demandees & set(relance.closes)" in src_ch,
        "§4 une question close nommée dans --questions est refusée")
b.check("questions=perimetre" in src_ch and src_ch.count("questions=perimetre") >= 2,
        "§4 le périmètre borne la collecte ET la préparation du dossier de l'analyste")
lg = appels("app/agents/v2/parcours.py", "_lignes")
mpq = appels("app/agents/v2/parcours.py", "manque_pour_question")
# Lot M3 (`porte.py`) : `_lignes` et `porte_de_l_architecte` partagent désormais la PRÉPARATION des
# arguments de `manque_de_la_question` via `manque_pour_question` (détenteur unique, #46) — la
# chaîne reste directe : `_lignes` → `manque_pour_question` → `manque_de_la_question`, jamais
# dupliquée. `#46 appliqué à l'extraction` : vérifier la chaîne ENTIÈRE, pas seulement son premier
# maillon.
b.check("manque_pour_question" in lg and "manque_de_la_question" in mpq,
        "§4 le périmètre et l'alerte lisent la MÊME règle du manque (via `manque_pour_question`, "
        "détenteur unique de la préparation d'arguments — lot M3)")
src_lg = strip_code(Path("app/agents/v2/parcours.py").read_text(encoding="utf-8"))
b.check("decision_ouvrante=(position.derniere" in src_lg,
        "§4 l'alerte passe la dernière décision du comité quand elle ouvre")
b.check("_lignes" in appels("app/agents/v2/parcours.py", "questions_a_relancer"),
        "§4 `questions_a_relancer` dérive des lignes du dossier (aucune règle recopiée, #46)")
b.check("_arreter_la_recherche_en_cours" in appels("app/agents/v2/comite.py", "_reinitialiser_une"),
        "§4 la réinitialisation ARRÊTE la recherche en cours (cycle du mandat)")
b.check("_reinitialiser_une" in appels("app/agents/v2/comite.py", "reinitialiser_chapitre"),
        "§4 le chapitre réinitialise question par question, par le même geste")
b.check("questions_applicables" in appels("app/api/parcours_v2.py", "comite_reinitialiser_chapitre"),
        "§4 le chapitre ne réinitialise que les questions APPLICABLES (pas de bruit indélébile au PV)")

# ══ §5 LE POINT DE LECTURE ════════════════════════════════════════════════════════════════════
print("[5] le point de lecture — les écrans nomment le geste et la question rouverte")
FRONT = Path("/frontend")
REG = FRONT / "components/v2/RegistreComite.js"
PAR = FRONT / "components/v2/parcours.js"
N2 = FRONT / "pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/index.js"
if not (REG.exists() and PAR.exists() and N2.exists()):
    b.check(False, f"§5 écrans absents de {FRONT} — section non mesurée (montage /frontend manquant ?)")
else:
    def _code(path):
        t = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        return re.sub(r"(?m)^\s*//.*$", "", t)
    reg, par, n2 = _code(REG), _code(PAR), _code(N2)
    b.check(re.search(r"reinitialiser:\s*\{\s*label:", reg) is not None,
            "§5 le PV affiché nomme la réinitialisation")
    b.check("setGeste('reinitialiser')" in reg and "/${geste}`" in reg,
            "§5 le niveau 3 offre la réinitialisation d'une question (le geste nomme la route)")
    b.check("/reinitialiser`" in n2, "§5 le niveau 2 offre la réinitialisation du chapitre")
    b.check(re.search(r"rouverte_comite:\s*'", par) is not None,
            "§5 l'alerte nomme la question rouverte par le comité")
    # #138 — l'attente se NOMME et se JUSTIFIE à l'écran (le comité juge la cause sur pièce).
    b.check(re.search(r"pas_encore_observable:\s*'", par) is not None,
            "§5 l'alerte nomme la question « pas encore observable »")
    b.check("{m.attente && <AttenteBloc a={m.attente} />}" in par
            and all(f"a.{c}" in par for c in ("cause", "fait_declencheur", "depuis", "piece_du_fait",
                                               "historique_requis", "revoir_le")),
            "§5 l'alerte montre la justification ENTIÈRE d'une attente")
    b.check("s.n_pas_encore_observable" in n2, "§5 le niveau 2 compte les attentes du chapitre")
    for cause in ("renvoi_comite", "reinitialisation", "pas_encore_observable"):
        b.check(re.search(rf"{cause}:\s*\{{", par) is not None, f"§5 l'alerte explique la cause `{cause}`")

# ══ §6 « PAS ENCORE OBSERVABLE » (#138) ═══════════════════════════════════════════════════════
# Arbitrage du 2026-10-18 : une attente ne ferme RIEN d'elle-même — elle reste à l'alerte (le comité
# juge la cause), mais aucune relance ne la recollecte avant sa date de revue ; échue, elle redevient
# une question à collecter sans geste. Forme du réel : RVMD mo_6 en grille rentable (2026-10-18).
print("[6] « pas encore observable » : à l'alerte, fermée à la relance, rouverte par sa date")
from app.agents.v2.parcours import dresser_niveau2  # noqa: E402
from app.contracts.readiness_report_schema import AttenteObservation  # noqa: E402


def lue_att(i, *, qid="qf_6", revoir="2027-11-15"):
    att = AttenteObservation(
        cause="RASONQUE n'est vendu que depuis le 26 août : aucun prix n'a encore été éprouvé",
        fait_declencheur="approbation de la FDA", depuis="2026-08-26", piece_du_fait=1147,
        historique_requis="quatre trimestres de ventes publiés", revoir_le=revoir)
    a = FrameworkAnswerServie(
        framework_id="qualite_financiere", framework_version=VER, question_id=qid, ticker_id="NVDA",
        analyste="a", statut="non_fondable",
        manager=ManagerVerdict(verdict="acquitte", controles=OK4, motif="ok"),
        gap=GapItem(dimension="d", champs_cibles=[qid], manque="pouvoir de prix non mesurable",
                    priorite="haute", coverage_actuelle="1/1", remede="attente", attente=att))
    return ReponseLue(answer_id=i, servie=a, verdict="acquitte", controles=OK4, motif_revue="ok",
                      etat_revue="revue", cree_le=T_REP)


def manque_j(reponses, jour, **kw):
    return manque_de_la_question(
        framework_id="qualite_financiere", libelle_framework="Qualité financière",
        question_id="qf_6", enonce="e", applicable=True, dispensee=False, reponses=list(reponses),
        collecte=None, mandat_ouvert_id=None, aujourd_hui=jour, **kw)


ATT = lue_att(1800)
m_att = manque_j([ATT], APRES.date())
b.check(m_att is not None and (m_att.nature, m_att.cause) == ("pas_encore_observable", "pas_encore_observable"),
        f"§6 une attente non échue RESTE à l'alerte, sous sa nature — obtenu {m_att and (m_att.nature, m_att.cause)}")
b.check(m_att is not None and m_att.attente is not None and "26 août" in m_att.attente.cause
        and "Revue le 2027-11-15" in m_att.explication and "#1147" in m_att.explication,
        "§6 l'alerte porte la justification ENTIÈRE : cause, fait, pièce, date de revue (le comité juge sur pièce)")
m_ech = manque_j([ATT], datetime(2027, 11, 15).date())
b.check(m_ech is not None and m_ech.nature == "non_fondee" and m_ech.attente is None,
        f"§6 au jour de la revue, l'attente est ÉCHUE : la question redevient à collecter — obtenu "
        f"{m_ech and m_ech.nature}")
m_rv6 = manque_j([ATT], APRES.date(), decision_ouvrante=decision(30, "renvoyer", mandat_id=701))
b.check(m_rv6 is not None and m_rv6.nature == "rouverte_comite",
        "§6 le comité qui CONTESTE la cause (renvoi) rouvre la question en recherche")
pos6 = position_du_comite([decision(31, "acquitter", answer_id=1800, quand=APRES)],
                          reponses_courantes=frozenset({1800}), ancre=AUCUN_FAIT)
b.check(pos6 is not None and manque_j([ATT], APRES.date(), acceptation=pos6.acceptation) is None,
        "§6 le comité qui ACCEPTE la cause ferme la question (c'est lui, pas l'analyste, qui ferme)")

q_att, q_ech = ids[6], ids[7]
b.require(ids[:8], 8, "§6 qualité financière a au moins huit questions (fixture)")
rep6 = rep + [lue_att(15, qid=q_att), lue_att(16, qid=q_ech, revoir="2026-10-17")]
etat6 = EtatDossier(
    ticker_id="NVDA", fichier=FICHIER, archetype="rentable", reponses=rep6, pieces={},
    applicables={f.id: frozenset(q.id for q in f.questions) - {q_hors} for f in FICHIER.frameworks},
    dispenses={f.id: (frozenset({q_disp}) if f.id == "qualite_financiere" else frozenset())
               for f in FICHIER.frameworks},
    mandats_ouverts={}, collecte={}, genere_le=APRES, registre={}, comite=comite)
per6 = questions_a_relancer(etat6, "qualite_financiere")
b.check(q_att not in per6.ouvertes and per6.closes.get(q_att, "").startswith(
            "pas encore observable jusqu'au 2027-11-15"),
        f"§6 la relance NE recollecte PAS une attente non échue, et dit pourquoi — obtenu {per6.closes.get(q_att)}")
b.check(q_ech in per6.ouvertes, f"§6 … mais refait une attente ÉCHUE — ouvertes {per6.ouvertes}")
n2_6 = dresser_niveau2(etat6, "qualite_financiere")
b.check(n2_6.synthese.n_pas_encore_observable == 1,
        f"§6 le chapitre COMPTE ses attentes (l'abus se voit) — obtenu {n2_6.synthese.n_pas_encore_observable}")

sys.exit(b.summary())
