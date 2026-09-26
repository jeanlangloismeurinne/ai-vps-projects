"""Vérification du PARCOURS DU COMITÉ — les trois niveaux et l'alerte « peut-on décider ? »
(lot 6 maillon 2, `app/agents/v2/parcours.py` + contrat `parcours_schema.py`).

Sans réseau, sans modèle, sans base : la moitié qui DÉCIDE (`manque_de_la_question`, `dresser_niveau*`)
est pure. La moitié qui LIT (`charger_etat_dossier`) est exercée sur la vraie base par
`tools/montrer_parcours.sh`, et son détenteur unique est gardé ici par AST (§6).

  • §1 LA RÈGLE DU MANQUE, CHAQUE BRANCHE ATTEIGNABLE (#63). L'ordre des branches est la doctrine :
       pas un manque (inapplicable, dispensée, une réponse qui tient) · renvoyée · périmée · non fondée
       · sans réponse. Chaque branche se prouve par un couple où le seul facteur visé bascule.
  • §2 LA CAUSE, ET SA PRÉSÉANCE (arbitrage du comité n°3). Formes COPIÉES DU RÉEL : `qf_7` RVMD porte
       un ingrédient en panne (budget de 180 s) et un ingrédient épuisé (poste EDGAR non fondé) — la
       cause affichée est la panne, parce qu'elle se relance. Une cause de collecte se PROUVE par ses
       ingrédients, et l'absence de plan n'est pas l'absence de source.
  • §3 LE CONTRAT REFUSE l'alerte muette : un dossier incomplet sans manque nommé, un complet qui en
       porte, une cause de collecte sans preuve, un état de revue qui ment sur l'avis attaché.
  • §4 NIVEAU 1 — l'alerte est EN TÊTE et NOMINATIVE ; non classé ⟹ `non_revalidable` (jamais un
       faux « complet ») ; l'ordre des méthodologies est celui du référentiel.
  • §5 NIVEAU 3 — la preuve : pièces citées et ingrédients, pièce absente du corpus DITE, rang le plus
       faible cité publié à côté du rang dérivé, renvoi sans mandat NOMMÉ (`renvoi_a_emettre`), une
       référence inconnue LÈVE (jamais un niveau vide).
  • §6 DÉTENTEUR UNIQUE DE L'ASSEMBLAGE (#46) — la note projetée et la note de qualité passent par
       `charger_etat_dossier` et ne recopient plus la plomberie ; l'assembleur APPELLE les détenteurs
       des règles (revue, service, applicabilité) au lieu de les ré-écrire.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import ast
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.parcours import (
    Collecte, EtatDossier, ReferenceInconnue, ReponseLue, dresser_niveau1, dresser_niveau2,
    dresser_niveau3, manque_de_la_question)
from app.agents.v2.projection_memo import memo_de_l_etat
from app.contracts.framework_answer_schema import (
    Approximation, ControlesManager, FondationServie, FrameworkAnswerServie, ManagerVerdict,
    Reponse, SansObjet)
from app.contracts.parcours_schema import (
    IngredientManquant, Manque, PeutOnDecider, PreuveReponse)
from app.contracts.readiness_report_schema import GapItem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

b = Bilan()
FICHIER = load_frameworks()
VER = FICHIER.schema_version
T0 = datetime(2026, 9, 21, tzinfo=timezone.utc)


def refuse(fn, motif: str, label: str) -> None:
    """Un refus prononcé par une AUTRE règle est un FAIL (4ᵉ faux vert)."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        b.check(motif in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
        return
    b.check(False, f"{label} — ACCEPTÉ")


# ── fabriques ──────────────────────────────────────────────────────────────────────────────────
OK4 = ControlesManager(completude="ok", fondation="ok", honnetete_approximation="sans_objet",
                       non_substitution="ok")
KO1 = ControlesManager(completude="ko", fondation="ok", honnetete_approximation="sans_objet",
                       non_substitution="ok")


def _servie(qid, statut, *, fw="qualite_financiere", act="courante", analyste="a", cites=(10,),
            manager=None):
    commun = dict(framework_id=fw, framework_version=VER, question_id=qid, ticker_id="RVMD",
                  analyste=analyste, statut=statut, manager=manager)
    if statut == "repondu":
        return FrameworkAnswerServie(
            **commun, reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
            fondation=FondationServie(cited_entry_ids=list(cites), rang_derive="A",
                                      nature_effective="mesure", actualite=act,
                                      motif_actualite=f"motif-{act}"))
    if statut == "approxime":
        return FrameworkAnswerServie(
            **commun, reponse=Reponse(verbatim="x", valeur=1.0, unite="%"),
            fondation=FondationServie(cited_entry_ids=list(cites), rang_derive="A-",
                                      nature_effective="interpretation", actualite=act,
                                      motif_actualite=f"motif-{act}"),
            approximation=Approximation(methode="m", ingredients_entry_ids=[11, 12],
                                        hypotheses_explicites=["h"], sensibilite="s"))
    if statut == "sans_objet":
        return FrameworkAnswerServie(
            **commun, sans_objet=SansObjet(motif="sans revenus", aucun_substitut=True))
    return FrameworkAnswerServie(
        **commun, gap=GapItem(dimension="d", champs_cibles=[qid], manque="m", priorite="haute",
                              coverage_actuelle="0/1"))


def _lue(i, qid, statut, *, verdict="acquitte", **kw):
    ctrl = OK4 if verdict != "renvoye" else KO1
    if statut == "approxime" and verdict != "renvoye":
        ctrl = ControlesManager(completude="ok", fondation="ok", honnetete_approximation="ok",
                                non_substitution="ok")
    mgr = (ManagerVerdict(verdict="acquitte", controles=ctrl, motif="4 contrôles au vert")
           if verdict == "acquitte" else None)
    etat = {"acquitte": "revue", "renvoye": "renvoi_a_emettre", None: "non_revalidable"}[verdict]
    return ReponseLue(answer_id=i, servie=_servie(qid, statut, manager=mgr, **kw),
                      verdict=verdict, controles=ctrl if verdict else None,
                      motif_revue=("completude ko — réponse fabriquée" if verdict == "renvoye"
                                   else "4 contrôles au vert" if verdict else None),
                      etat_revue=etat)


# Formes COPIÉES DU RÉEL (RVMD, `framework_mandates` 296/297 et 588-591, 2026-09-21/25).
QF7_PANNE = IngredientManquant(
    ingredient_id="charges_fixes_decaissables", cause="source_indisponible", constate_le=T0,
    motif="collecte web abandonnée : budget de 180 s dépassé pour « Charges fixes décaissables sur "
          "les douze prochains mois (estimation) » (ligne convertie en mandat, aucune donnée écrite)")
QF7_EPUISE = IngredientManquant(
    ingredient_id="echeances_a_douze_mois", cause="recherche_epuisee", constate_le=T0,
    motif="poste EDGAR 'long_term_debt_current' non fondé pour RVMD (aucun concept XBRL "
          "exploitable dans les dépôts)")
MO2_SANS = tuple(IngredientManquant(ingredient_id=i, cause="sans_source_possible", constate_le=T0,
                                    motif=f"RVMD n'a pas de produit commercialisé ({i})")
                 for i in ("marges_relatives_aux_pairs", "evolution_des_parts_de_marche"))


def manque(qid="qf_7", *, reponses=(), collecte=None, applicable=True, dispensee=False, mandat=None):
    return manque_de_la_question(
        framework_id="qualite_financiere", libelle_framework="Qualité financière",
        question_id=qid, enonce="énoncé", applicable=applicable, dispensee=dispensee,
        reponses=list(reponses), collecte=collecte, mandat_ouvert_id=mandat)


# ══ §1 LA RÈGLE DU MANQUE ═════════════════════════════════════════════════════════════════════
print("[1] la règle du manque — chaque branche atteignable")
b.check(manque(applicable=False) is None, "§1 une question INAPPLICABLE n'est jamais un manque")
b.check(manque(dispensee=True) is None,
        "§1 une question DISPENSÉE (le comité a accepté le trou) n'est pas un manque")
b.check(manque(reponses=[_lue(1, "qf_7", "repondu")]) is None,
        "§1 une réponse acquittée, fondée et COURANTE tient : pas un manque")
b.check(manque(reponses=[_lue(1, "qf_7", "sans_objet")]) is None,
        "§1 un hors-sujet acquitté tient : pas un manque")
b.check(manque(reponses=[_lue(1, "qf_7", "non_fondable"),
                         _lue(2, "qf_7", "repondu", analyste="b")]) is None,
        "§1 deux analystes = deux points : il SUFFIT qu'un point tienne (§3.4)")
m_nv = manque(reponses=[_lue(1, "qf_7", "repondu", verdict=None)])
b.check(m_nv is not None,
        "§1 une réponse que personne n'a pu relire ne TIENT pas (l'avis n'est pas un détail)")

m_r = manque(reponses=[_lue(1, "qf_7", "repondu", verdict="renvoye")], mandat=42)
b.check(m_r is not None and m_r.nature == "renvoyee" and m_r.cause == "controle_ko",
        f"§1 renvoyée → nature `renvoyee`, cause `controle_ko` — obtenu {m_r and (m_r.nature, m_r.cause)}")
b.check(m_r is not None and "réponse fabriquée" in m_r.explication,
        "§1 le manque RENVOYÉ nomme le contrôle qui a refusé (le motif du manager, pas un générique)")
b.check(m_r is not None and m_r.mandat_ouvert_id == 42,
        "§1 le manque dit si la question est DÉJÀ repartie en recherche (mandat ouvert)")

m_p = manque(reponses=[_lue(1, "qf_7", "repondu", act="perimee")])
b.check(m_p is not None and (m_p.nature, m_p.cause) == ("perimee", "fait_nouveau_publie"),
        f"§1 fondée mais PÉRIMÉE → `perimee` / `fait_nouveau_publie` — obtenu {m_p and (m_p.nature, m_p.cause)}")
b.check(m_p is not None and "motif-perimee" in m_p.explication,
        "§1 le manque PÉRIMÉ porte le motif d'actualité (quel fait, quelle date) — pas un état nu")
m_i = manque(reponses=[_lue(1, "qf_7", "approxime", act="indeterminable")])
b.check(m_i is not None and m_i.cause == "actualite_indeterminable",
        "§1 `indeterminable` a SA cause, distincte de `perimee` : son remède est « rendre datable »")
m_rp = manque(reponses=[_lue(1, "qf_7", "repondu", act="perimee"),
                        _lue(2, "qf_7", "repondu", analyste="b", verdict="renvoye")])
b.check(m_rp is not None and m_rp.nature == "renvoyee",
        "§1 préséance : un RENVOI passe devant une péremption (le contrôle a refusé la réponse)")

# ══ §2 LA CAUSE ET SA PRÉSÉANCE ═══════════════════════════════════════════════════════════════
print("[2] la cause — ce que la dernière collecte a rencontré")
col_mixte = Collecte(plan_id=78, ingredients_vus=("charges_fixes_decaissables",
                                                   "echeances_a_douze_mois"),
                     mandats=(QF7_EPUISE, QF7_PANNE))
m_q7 = manque(collecte=col_mixte)
b.check(m_q7 is not None and m_q7.nature == "sans_reponse",
        "§2 aucune réponse au dossier → nature `sans_reponse`")
b.check(m_q7 is not None and m_q7.cause == "source_indisponible",
        f"§2 qf_7 RÉEL (panne + épuisé) → la cause en tête est la PANNE, qui se relance — obtenu {m_q7 and m_q7.cause}")
b.require(m_q7.ingredients if m_q7 else [], 2,
          "§2 la preuve de la cause : CHAQUE ingrédient manquant, avec sa propre cause")
b.check(m_q7 is not None and any("budget de 180 s" in i.motif for i in m_q7.ingredients),
        "§2 le motif du producteur est rendu TEL QUEL (le comité lit ce que la machine a rencontré)")
m_ep = manque(reponses=[_lue(1, "qf_7", "non_fondable")],
              collecte=Collecte(plan_id=78, mandats=(QF7_EPUISE,)))
b.check(m_ep is not None and (m_ep.nature, m_ep.cause) == ("non_fondee", "recherche_epuisee"),
        f"§2 non fondée + recherche allée au bout → `recherche_epuisee` — obtenu {m_ep and (m_ep.nature, m_ep.cause)}")
m_ss = manque(reponses=[_lue(1, "qf_7", "non_fondable")],
              collecte=Collecte(plan_id=103, mandats=MO2_SANS))
b.check(m_ss is not None and m_ss.cause == "sans_source_possible",
        "§2 tous les ingrédients sans source → `sans_source_possible` (la question est à reformuler)")
m_pi = manque(reponses=[_lue(1, "qf_7", "non_fondable")],
              collecte=Collecte(plan_id=103, ingredients_vus=("a", "b"), mandats=()))
b.check(m_pi is not None and m_pi.cause == "pieces_insuffisantes",
        "§2 plan exécuté SANS aucun mandat → `pieces_insuffisantes` (tout a été collecté, rien ne fonde)")
m_pc = manque()
b.check(m_pc is not None and m_pc.cause == "pas_encore_cherchee",
        "§2 aucun plan n'a couvert la question → `pas_encore_cherchee`, JAMAIS une recherche épuisée")
m_pc2 = manque(collecte=Collecte(plan_id=None))
b.check(m_pc2 is not None and m_pc2.cause == "pas_encore_cherchee",
        "§2 une collecte sans plan (plan_id None) n'est pas une recherche menée")

# ══ §3 LE CONTRAT ═════════════════════════════════════════════════════════════════════════════
print("[3] le contrat refuse l'alerte muette")
refuse(lambda: Manque(framework_id="f", libelle_framework="L", question_id="q", enonce="e",
                      nature="non_fondee", cause="recherche_epuisee", explication="x"),
       "se prouve", "§3 une cause de collecte SANS ingrédient est refusée")
refuse(lambda: PeutOnDecider(etat="dossier_incomplet", motif="x"),
       "sans aucun manque nommé", "§3 un dossier INCOMPLET sans manque nommé est refusé")
refuse(lambda: PeutOnDecider(etat="dossier_complet", motif="x", manques=[m_pc]),
       "l'alerte serait tue", "§3 un dossier COMPLET qui porte un manque est refusé")
refuse(lambda: PreuveReponse(answer_id=1, answer=_servie("qf_7", "repondu"), etat_revue="revue"),
       "avis attaché", "§3 `etat_revue=revue` sans avis attaché est refusé")

# ══ §4 NIVEAU 1 ═══════════════════════════════════════════════════════════════════════════════
print("[4] niveau 1 — l'alerte en tête, nominative")


def etat(reponses, *, archetype="pre_revenus", collecte=None, applicables=None, pieces=None,
         mandats=None):
    ids = {f.id: frozenset(q.id for q in f.questions) for f in FICHIER.frameworks}
    return EtatDossier(
        ticker_id="RVMD", fichier=FICHIER, archetype=archetype, reponses=list(reponses),
        pieces=pieces or {}, dispenses={f.id: frozenset() for f in FICHIER.frameworks},
        applicables=(applicables if applicables is not None else
                     {f: (None if archetype is None else qs) for f, qs in ids.items()}),
        mandats_ouverts=mandats or {}, collecte=collecte or {}, genere_le=T0)


def memo_de(e):
    return memo_de_l_etat(e, genere_le=T0)


QF = next(f for f in FICHIER.frameworks if f.id == "qualite_financiere")
seule_qf7 = {f.id: (frozenset({"qf_7"}) if f.id == "qualite_financiere" else frozenset())
             for f in FICHIER.frameworks}
e_ok = etat([_lue(1, "qf_7", "repondu")], applicables=seule_qf7)
n1 = dresser_niveau1(e_ok, memo_de(e_ok))
b.check(n1.peut_on_decider.etat == "dossier_complet" and not n1.peut_on_decider.manques,
        f"§4 toutes les applicables tiennent → `dossier_complet` — obtenu {n1.peut_on_decider.etat}")
e_ko = etat([_lue(1, "qf_7", "non_fondable")], applicables=seule_qf7,
            collecte={("qualite_financiere", "qf_7"): col_mixte})
n1k = dresser_niveau1(e_ko, memo_de(e_ko))
b.check(n1k.peut_on_decider.etat == "dossier_incomplet",
        "§4 une applicable qui ne tient pas → `dossier_incomplet`")
b.require(n1k.peut_on_decider.manques, 1, "§4 l'alerte NOMME chaque manque")
b.check(n1k.peut_on_decider.manques and n1k.peut_on_decider.manques[0].enonce == next(
            q.enonce for q in QF.questions if q.id == "qf_7"),
        "§4 le manque porte l'ÉNONCÉ de la question (le comité lit une question, pas un identifiant)")
b.check("1 question applicable" in n1k.peut_on_decider.motif
        and "l'obtenir" in n1k.peut_on_decider.motif,
        f"§4 le motif est une phrase juste au singulier — obtenu « {n1k.peut_on_decider.motif} »")
e_nc = etat([_lue(1, "qf_7", "repondu", verdict=None)], archetype=None)
n1n = dresser_niveau1(e_nc, memo_de(e_nc))
b.check(n1n.peut_on_decider.etat == "non_revalidable",
        "§4 société NON CLASSÉE → `non_revalidable`, jamais un faux « complet » sur zéro question")
# L'ordre attendu est relu dans le FICHIER, pas dans l'objet chargé : l'assembleur reçoit ce même
# objet, et un assert qui s'y comparerait suivrait toute mutation de l'ordre (assert écrit depuis sa
# propre constante — mesuré : la mutation « tri alphabétique » restait verte).
import yaml  # noqa: E402
ORDRE_YAML = [f["id"] for f in yaml.safe_load(
    Path("app/frameworks/frameworks.yaml").read_text(encoding="utf-8"))["frameworks"]]
b.require(ORDRE_YAML, 2, "§4 l'ordre de référence est lu dans le fichier")
b.check([s.framework_id for s in n1.frameworks] == ORDRE_YAML,
        "§4 les méthodologies suivent l'ordre du RÉFÉRENTIEL (ajouter un cadre = une donnée)")
s_qf = next(s for s in n1k.frameworks if s.framework_id == "qualite_financiere")
b.check(s_qf.n_manques == 1 and s_qf.n_applicables == 1 and s_qf.n_acquittees == 1,
        f"§4 la synthèse d'une méthodologie compte ses manques — obtenu {s_qf.n_manques}/{s_qf.n_applicables}/{s_qf.n_acquittees}")
n2 = dresser_niveau2(e_ko, "qualite_financiere")
b.require(n2.questions, len(QF.questions),
          "§4bis niveau 2 : UNE ligne par question du référentiel, y compris les sans réponse")
lq7 = next(lq for lq in n2.questions if lq.question_id == "qf_7")
b.check(lq7.manque is not None and lq7.reponses and lq7.reponses[0].verdict == "acquitte",
        "§4bis niveau 2 : la ligne porte le statut, l'avis du manager ET le manque")

# ══ §5 NIVEAU 3 ═══════════════════════════════════════════════════════════════════════════════
print("[5] niveau 3 — la preuve")
pieces = {10: dict(title="10-K FY2025", source_type="edgar_official", source_url="u",
                   source_date=None, date_du_fait=None, reliability_tier="A",
                   nature="mesure", superseded_by=None),
          11: dict(title="presse", source_type="web_search_reputable", source_url=None,
                   source_date=None, date_du_fait=None, reliability_tier="B+",
                   nature="interpretation", superseded_by=99)}
e3 = etat([_lue(5, "qf_6", "approxime", cites=(10, 11))], pieces=pieces)
n3 = dresser_niveau3(e3, "qualite_financiere", "qf_6")
b.require(n3.preuves, 1, "§5 une preuve par réponse")
p = n3.preuves[0] if n3.preuves else None
roles = sorted((x.entry_id, x.role) for x in p.pieces) if p else []
b.check(roles == [(10, "citee"), (11, "citee"), (11, "ingredient"), (12, "ingredient")],
        f"§5 pièces citées ET ingrédients de l'approximation, chacun avec son rôle — obtenu {roles}")
b.check(p is not None and any(x.entry_id == 12 and not x.present_au_corpus for x in p.pieces),
        "§5 une pièce citée ABSENTE du corpus est dite (`present_au_corpus=False`), jamais omise")
b.check(p is not None and any(x.entry_id == 11 and x.remplacee for x in p.pieces),
        "§5 une pièce REMPLACÉE depuis la réponse est signalée")
b.check(p is not None and p.rang_plus_faible_cite == "B+",
        f"§5 le rang le plus faible CITÉ est publié (le rang dérivé se conteste) — obtenu {p and p.rang_plus_faible_cite}")
e3r = etat([_lue(6, "qf_7", "repondu", verdict="renvoye")])
p_r = dresser_niveau3(e3r, "qualite_financiere", "qf_7").preuves[0]
b.check(p_r.etat_revue == "renvoi_a_emettre" and p_r.answer.manager is None
        and p_r.renvoi_a_emettre is not None and "fabriquée" in p_r.renvoi_a_emettre.motif,
        "§5 un renvoi SANS mandat ouvert est NOMMÉ `renvoi_a_emettre`, jamais un mandat inventé")
refuse(lambda: dresser_niveau3(e3, "qualite_financiere", "qf_99"), "inconnue",
       "§5 une question inconnue LÈVE (jamais un niveau 3 vide)")
refuse(lambda: dresser_niveau2(e3, "cadre_fictif"), "absent du référentiel",
       "§5 un framework inconnu LÈVE (jamais un niveau 2 vide)")

# ══ §6 DÉTENTEUR UNIQUE ═══════════════════════════════════════════════════════════════════════
print("[6] détenteur unique de l'assemblage (#46)")


def appels(path: str, fonction: str) -> set[str]:
    arbre = ast.parse(Path(path).read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, ast.AsyncFunctionDef) and n.name == fonction:
            return {(c.func.id if isinstance(c.func, ast.Name) else
                     c.func.attr if isinstance(c.func, ast.Attribute) else "")
                    for c in ast.walk(n) if isinstance(c, ast.Call)}
    return set()


for mod, fn in (("app/agents/v2/projection_memo.py", "servir_memo"),
                ("app/agents/v2/qualite_info.py", "servir_qualite_info")):
    a = appels(mod, fn)
    b.check("charger_etat_dossier" in a, f"§6 `{fn}` passe par `charger_etat_dossier`")
    b.check(not ({"read_answers_courantes", "servir_answer", "reviser_framework",
                  "material_anchor_for_ticker"} & a),
            f"§6 `{fn}` ne recopie plus la plomberie — obtenu {sorted(a)}")
a_ch = appels("app/agents/v2/parcours.py", "charger_etat_dossier")
for detenteur in ("reviser_framework", "servir_answer", "questions_applicables",
                  "assemble_verdict", "read_answers_courantes", "material_anchor_for_ticker"):
    b.check(detenteur in a_ch, f"§6 l'assembleur APPELLE `{detenteur}` (jamais une ré-écriture)")
b.check("ancre_substantielle" in a_ch,
        "§6 l'actualité se juge contre l'ancre qui PÈSE (`ancre_substantielle`) : un 8-K de pure "
        "forme ne fait tomber aucune réponse (arbitrage du comité n°2, #54)")
code = strip_code(Path("app/agents/v2/parcours.py").read_text(encoding="utf-8"))
b.check("INSERT" not in code and "UPDATE" not in code and "DELETE" not in code,
        "§6 l'assembleur N'ÉCRIT RIEN (tout se recalcule à la lecture, #53/#54/#77)")
b.check("qualite_financiere" not in code and "defendabilite" not in code,
        "§6 l'assembleur ne NOMME aucune méthodologie (ajouter un cadre = une donnée)")

# ══ §7 LE POINT DE LECTURE ════════════════════════════════════════════════════════════════════
print("[7] le point de lecture — chaque champ a son pixel, l'alerte est en tête")
# Le frontend est monté en `/frontend` par `run_all.sh` et par le harnais (WITH_FRONT=1). Absent, la
# section sort en ÉCHEC : un prérequis manquant ne passe jamais pour un 0.
FRONT = Path("/frontend")
N3 = FRONT / "pages/v2/tickers/[ticker_id]/frameworks/[framework_id]/q/[question_id].js"
PAGE = FRONT / "pages/v2/tickers/[ticker_id]/index.js"
DOSSIER = FRONT / "components/v2/DossierComite.js"
if not (N3.exists() and PAGE.exists() and DOSSIER.exists()):
    b.check(False, f"§7 écrans absents de {FRONT} — section non mesurée (montage /frontend manquant ?)")
else:
    import re  # noqa: E402
    from typing import get_args  # noqa: E402

    def feuilles(modele, prefixe=""):
        out = []
        for nom, f in modele.model_fields.items():
            sous = [x for x in (get_args(f.annotation) or (f.annotation,)) if hasattr(x, "model_fields")]
            out += feuilles(sous[0], f"{prefixe}{nom}.") if sous else [f"{prefixe}{nom}"]
        return out

    attendus = set(feuilles(FrameworkAnswerServie))
    # Les marqueurs se lisent sur le JSX DÉPOUILLÉ de ses commentaires : un chemin cité en prose
    # n'est pas un pixel (#56 — un grep de présence est satisfait par la prose).
    jsx = re.sub(r"/\*.*?\*/", "", N3.read_text(encoding="utf-8"), flags=re.S)
    jsx = re.sub(r"(?m)^\s*//.*$", "", jsx)
    marques = set(re.findall(r'data-champ="([a-z_.]+)"', jsx))
    b.require(attendus, 39, "§7 le contrat servi a ses 39 champs terminaux")
    b.check(not (attendus - marques),
            f"§7 tout champ du contrat a son pixel au niveau 3 — sans pixel : {sorted(attendus - marques)}")
    b.check(not (marques - attendus),
            f"§7 … et tout pixel rend un champ RÉEL — pixels sans champ : {sorted(marques - attendus)}")
    page = PAGE.read_text(encoding="utf-8")
    i_dossier, i_identite = page.find("<DossierComite"), page.find('title="Identité"')
    b.check(0 <= i_dossier < i_identite,
            "§7 la page d'un titre répond D'ABORD à « peut-on décider ? » (arbitrage du comité n°3)")
    dos = DOSSIER.read_text(encoding="utf-8")
    ret = dos[dos.rfind("return ("):]
    ordre = [ret.find(t) for t in ("<Alerte", "<NotesQualite", "<Conclusions")]
    b.check(all(x >= 0 for x in ordre) and ordre == sorted(ordre),
            f"§7 l'ordre du niveau 1 est alerte → notes de qualité → conclusions — obtenu {ordre}")

sys.exit(b.summary())
