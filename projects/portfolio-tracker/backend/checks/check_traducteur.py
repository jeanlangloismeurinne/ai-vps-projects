"""Vérification du TRADUCTEUR (chantier v3, lot 2c — `app/agents/v2/traducteur.py`), MOITIÉ
DÉTERMINISTE seulement. Sans réseau ni modèle ni base.

Le modèle traduit ; mais ce qu'on lui MONTRE et ce qu'on lui LAISSE décider sont déterministes, et
c'est là que se jouent les garanties. On les éprouve avant toute dépense
(`feedback_frontiere_gratuite_avant_depense_modele`). La traduction elle-même (l'appel modèle) est
hors périmètre ici : son acceptation se fait contre le vrai modèle, séparément.

  • §1 FILTRAGE PAR ARCHÉTYPE — une question `sans_objet` n'est pas planifiée (sinon on fabrique une
       réponse là où le framework dit qu'il n'y a pas de question, §0.2). Chaque question rendue a
       bien `mode == 'variable'` pour l'archétype.
  • §2 LE CONTEXTE EST LEVER-FREE (#59) — ce que le modèle voit ne porte NI `plancher_tier` NI
       `nature_attendue`. Le traducteur dit *où chercher*, jamais *combien de preuve suffit* ; les
       montrer rouvrirait le levier `RESSERRER` que le lot 2c retire.
  • §3 LE CONTEXTE EST COMPLET — chaque ingrédient essentiel d'une question applicable y figure (le
       modèle ne peut planifier que ce qu'il voit), avec sa variable d'archétype, le ticker et la
       méthodologie.
  • §4 L'EN-TÊTE EST DÉTENU PAR LE CODE — le modèle ne produit que des LIGNES (`TraducteurSortie` n'a
       que `items`) ; ticker/framework/version/archétype sont posés par `traduire`, pas par le
       modèle (#36/#53/#57 : ce qui se persiste n'est pas ce que le modèle émet).
  • §5 L'INAPPLICABLE EST REFUSÉ TÔT (#40) — framework ou archétype inconnu lève AVANT tout appel,
       pas au retour d'un modèle qu'on aurait payé pour rien.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import inspect
import json
import sys
from datetime import date

from app.agents.v2 import traducteur as T
from app.contracts.collection_plan_schema import PERIODES
from app.knowledge.edgar_feed import IdentiteEmetteur, identite_de_l_emetteur
from app.agents.v2.frameworks import load_frameworks

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def refuse_tot(label, fn, motif_type=T.TraducteurInapplicable):
    """La demande DOIT lever `TraducteurInapplicable` (pas une autre exception, pas un retour)."""
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors que la demande n'a pas d'objet")
    except motif_type:
        ok += 1
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:120]}")


F = load_frameworks()
FW = {f.id: f for f in F.frameworks}["qualite_financiere"]

# ── §1 filtrage par archétype ───────────────────────────────────────────────────────────────────
print("[1] une question SANS OBJET pour l'archétype n'est pas planifiée")
_appl_pr = T.questions_applicables(F, "qualite_financiere", "pre_revenus")
_ids_pr = [q.id for q in _appl_pr]
check("qf_1 (rendement du capital) est ABSENT pour un pré-revenus (sans objet)",
      "qf_1" not in _ids_pr, f"→ {_ids_pr}")
check("chaque question rendue a bien `mode == variable` pour l'archétype (aucun sans_objet passé)",
      all(q.variables_par_archetype["pre_revenus"].mode == "variable" for q in _appl_pr))
_appl_rt = T.questions_applicables(F, "qualite_financiere", "rentable")
check("un archétype rentable garde les questions applicables (le filtre ne vide pas tout, #32)",
      len(_appl_rt) >= 1 and "qf_1" in [q.id for q in _appl_rt], f"→ {[q.id for q in _appl_rt]}")

# ── §2 le contexte est lever-free ─────────────────────────────────────────────────────────────────
print("\n[2] ce que le modèle voit ne porte AUCUN levier d'exigence (#59)")
# Identité copiée du registre SEC réel (`edgar_feed.resolve_identite("NVDA")`, relevé le 2026-09-26).
NVDA = IdentiteEmetteur(symbole="NVDA", cik=1045810, raison_sociale="NVIDIA CORP")
# Clôture copiée du réel : 10-Q NVDA du trimestre clos le 2026-07-26 (accession 0001045810-26-000075).
# Horloge par question NEUTRE ici (« aucun fait ») : §8 éprouve la fraîcheur sur le flux réel.
SANS_FAIT = {q.id: T.FraicheurQuestion("aucun_fait", None, "aucun dépôt ne rouvre (témoin)")
             for f in F.frameworks for q in f.questions}
H_NVDA = T.HorlogeDuPlan(date_du_jour=date(2026, 10, 13), derniere_cloture=date(2026, 7, 26),
                         fraicheur=SANS_FAIT)
CTX = T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", emetteur=NVDA, horloge=H_NVDA)
_ser = json.dumps(CTX, ensure_ascii=False)
check("le contexte ne contient pas `plancher_tier` (le modèle ne fixe pas le niveau de preuve)",
      "plancher_tier" not in _ser)
check("le contexte ne contient pas `nature_attendue` (idem — c'est la méthode qui le tient)",
      "nature_attendue" not in _ser)

# ── §3 le contexte est complet ────────────────────────────────────────────────────────────────────
print("\n[3] le modèle ne peut planifier que ce qu'on lui montre — donc on montre tout le requis")
# Lu dans la DONNÉE (pas via `ingredients_a_collecter`, la règle éprouvée) : un ingrédient repris ou lu
# dans le socle des comptes ne se planifie pas — il n'a pas à figurer au contexte.
_essentiels = {(q.id, i.id) for q in _appl_rt for i in q.ingredients_requis
               if i.essentiel and not i.repris_de and not i.depuis_le_socle}
_socle_vus = {(q.id, i.id) for q in _appl_rt for i in q.ingredients_requis if i.depuis_le_socle}
_ctx_couples = {(qq["id"], ii["id"]) for qq in CTX["questions"] for ii in qq["ingredients"]}
check("tous les ingrédients essentiels des questions applicables figurent au contexte",
      _essentiels <= _ctx_couples, f"→ manquants : {sorted(_essentiels - _ctx_couples)}")
check("… et AUCUN ingrédient lu dans le socle des comptes (il ne se collecte pas ligne à ligne)",
      bool(_socle_vus) and not (_socle_vus & _ctx_couples), f"→ {sorted(_socle_vus & _ctx_couples)}")
check("chaque question porte sa VARIABLE d'archétype (ce que la question devient pour ce type)",
      all(qq.get("variable_archetype") for qq in CTX["questions"]))
check("le contexte nomme le ticker et la méthodologie (le modèle traduit pour CETTE entreprise)",
      CTX.get("ticker") == "NVDA" and len(CTX.get("framework", {}).get("methodologie", "")) > 20)

# ── §4 l'en-tête est détenu par le code, pas par le modèle ────────────────────────────────────────
print("\n[4] le modèle produit des LIGNES ; l'en-tête (ticker/version/archétype) est posé par le code")
check("`TraducteurSortie` n'a QUE `items` (le modèle ne peut pas dater/étiqueter son plan, #57)",
      set(T.TraducteurSortie.model_fields) == {"items"}, f"→ {set(T.TraducteurSortie.model_fields)}")
_src = inspect.getsource(T.traduire)
check("`traduire` valide la sortie modèle contre `TraducteurSortie`, pas contre `CollectionPlan`",
      "TraducteurSortie" in _src and "run_json_agent" in _src)
check("… et pose lui-même `framework_version` depuis le référentiel (pas depuis le modèle)",
      "framework_version=fichier.schema_version" in _src)
check("… puis passe le plan au pont avant de le rendre (jamais un plan non validé) — au premier tour "
      "ET après le renvoi",
      _src.count("valider_pont_collection_plan(plan, fichier=fichier, questions=questions)") == 2)

# ── §5 l'inapplicable est refusé AVANT toute dépense ──────────────────────────────────────────────
print("\n[5] framework ou archétype inconnu lève AVANT l'appel modèle (#40)")
refuse_tot("[N-tôt] framework inconnu → TraducteurInapplicable",
           lambda: T.questions_applicables(F, "framework_bidon", "rentable"))
refuse_tot("[O-tôt] archétype inconnu → TraducteurInapplicable",
           lambda: T.questions_applicables(F, "qualite_financiere", "archetype_bidon"))
refuse_tot("[tôt] le contexte lui-même lève sur un archétype inconnu (pas de contexte muet)",
           lambda: T.contexte_traducteur(F, "qualite_financiere", "archetype_bidon", "NVDA",
                                         emetteur=NVDA, horloge=H_NVDA))

# ── §6 l'entreprise est NOMMÉE, pas devinée depuis son sigle (lot 7, 2026-09-26) ─────────────────
print("\n[6] le modèle reçoit la raison sociale et le CIK — un sigle n'est pas une identité")
# Le défaut mesuré : plan 103 (RVMD × defendabilite, 2026-09-25) planifié sur RVU120 / CDK8/19, les
# produits de Ryvu Therapeutics — le contexte ne portait que « RVMD ».
check("le contexte porte la raison sociale ET le CIK SEC de l'entreprise",
      CTX.get("entreprise") == {"raison_sociale": "NVIDIA CORP", "symbole": "NVDA", "cik_sec": 1045810},
      f"→ {CTX.get('entreprise')}")
try:
    T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", horloge=H_NVDA)
    check("le contexte REFUSE de se construire sans identité (aucun défaut silencieux)", False)
except TypeError as e:
    check("le contexte REFUSE de se construire sans identité (aucun défaut silencieux)",
          "emetteur" in str(e), f"→ {e}")
check("la consigne dit que l'entreprise est celle de la raison sociale, jamais celle du sigle",
      "JAMAIS CELLE QUE SUGGÈRE LE SIGLE" in T._TRADUCTEUR_SYSTEM_PROMPT)
check("la consigne ENSEIGNE la période (#113) : TOUTES les valeurs de PERIODES (détenteur unique, "
      "#46 — pas une liste recopiée ici), et « quatre derniers trimestres » ⟹ douze_mois_glissants",
      all(f"`{v}`" in T._TRADUCTEUR_SYSTEM_PROMPT for v in PERIODES)
      and "jamais `exercice_clos`" in T._TRADUCTEUR_SYSTEM_PROMPT)
check("la consigne distingue `cumul_publie` (lu tel quel) de `douze_mois_glissants` (reconstruit) — "
      "#119, sinon un rapprochement non-GAAP se fait recalculer comme une fenêtre glissante",
      "jamais `douze_mois_glissants`" in T._TRADUCTEUR_SYSTEM_PROMPT
      and "JAMAIS recalculé" in T._TRADUCTEUR_SYSTEM_PROMPT)
_src_tr = inspect.getsource(T.traduire)
_i_id, _i_run = _src_tr.find("identite_de_l_emetteur("), _src_tr.find("run_json_agent(")
check("`traduire` résout l'identité par son détenteur unique AVANT la dépense modèle (#40/#46)",
      0 <= _i_id < _i_run, f"→ positions {_i_id} / {_i_run}")
check("… et la passe au contexte (pas une identité résolue puis oubliée)",
      "emetteur=emetteur" in _src_tr)
_src_id = inspect.getsource(identite_de_l_emetteur)
check("l'identité passe par `symbole_de_marche` (#11) — jamais l'id interne chez la SEC",
      "symbole_de_marche(conn, ticker_id)" in _src_id and "resolve_identite(" in _src_id)

# ── §7 le traducteur reçoit l'horloge — il n'en a pas (#120, 2026-10-13) ─────────────────────────
print("\n[7] la date du jour et la clôture des derniers comptes publiés sont DONNÉES au modèle")
# Le défaut mesuré : plan #221 (NVDA × qualite_financiere) — 19 lignes sur 19 ancrées « clôture du
# dernier exercice fiscal », source « 10-K », six semaines après le dépôt du 10-Q clos le 2026-07-26 ;
# la revue des clauses (qf_8) naît périmée à chaque trimestre.
_cal = CTX.get("calendrier") or {}
check("le contexte porte la clôture des derniers comptes publiés, datée",
      _cal.get("cloture_des_derniers_comptes_publies") == "2026-07-26", f"→ {_cal}")
check("le contexte porte la date du jour (un modèle sans date fournie date à sa coupure)",
      _cal.get("date_du_jour") == "2026-10-13", f"→ {_cal}")
check("la lecture rendue au modèle nomme la clôture (pas seulement un champ brut)",
      "2026-07-26" in (_cal.get("lecture") or ""), f"→ {_cal.get('lecture')}")
_ctx_inconnue = T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", emetteur=NVDA,
                                      horloge=T.HorlogeDuPlan(date(2026, 10, 13), None, SANS_FAIT))
_cal_i = _ctx_inconnue.get("calendrier") or {}
check("clôture inconnue : la clé est PRÉSENTE à null et la lecture dit INCONNUE (jamais omise ni devinée)",
      "cloture_des_derniers_comptes_publies" in _cal_i
      and _cal_i["cloture_des_derniers_comptes_publies"] is None
      and "INCONNUE" in (_cal_i.get("lecture") or ""), f"→ {_cal_i}")
try:
    T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", emetteur=NVDA)
    check("le contexte REFUSE de se construire sans horloge (aucun défaut silencieux)", False)
except Exception as e:  # noqa: BLE001 — une autre exception est un FAIL nommé, jamais la mort du script
    check("le contexte REFUSE de se construire sans horloge (aucun défaut silencieux)",
          isinstance(e, TypeError) and "horloge" in str(e), f"→ {type(e).__name__}: {e}")
check("la consigne enseigne la RÈGLE DE FRAÎCHEUR : viser le rapport périodique qui couvre la clôture, "
      "y compris pour une clause (`sans_periode`)",
      "RÈGLE DE FRAÎCHEUR" in T._TRADUCTEUR_SYSTEM_PROMPT
      and "LE RAPPORT PÉRIODIQUE QUI COUVRE CETTE CLÔTURE" in T._TRADUCTEUR_SYSTEM_PROMPT
      and "AUSSI pour une clause" in T._TRADUCTEUR_SYSTEM_PROMPT)
_i_h, _i_run = _src_tr.find("horloge_du_plan("), _src_tr.find("run_json_agent(")
check("`traduire` lit l'horloge AVANT la dépense modèle", 0 <= _i_h < _i_run,
      f"→ positions {_i_h} / {_i_run}")
check("… et la passe au contexte du modèle (#120)", "horloge=horloge" in _src_tr)
_src_h = inspect.getsource(T.horloge_du_plan)
check("l'horloge du plan est celle qui servira les réponses (`horloge_du_titre` + "
      "`derniere_cloture_publiee`, détenteurs uniques — #46)",
      "horloge_du_titre(conn, ticker_id, fichier)" in _src_h
      and "derniere_cloture_publiee(ancre)" in _src_h)


# ── §8 chaque question porte SA fraîcheur — le fait qui la rouvre (jalon A, 2026-10-13) ────────────
print("\n[8] la date avant laquelle une pièce naît périmée est donnée PAR QUESTION au modèle")
# Le défaut mesuré à blanc (modèle économique, 2026-10-13) : NVDA ancré au rapport annuel du 26/01 sur
# des questions que les comptes du 26/07 rouvrent ; RVMD décrit « produit non encore commercialisé »
# sur le rapport annuel 2025, alors que l'approbation FDA du 26/08 rouvre me_1/me_5. Flux RÉEL RVMD
# (relevé EDGAR du 2026-09-30, `check_evenements`), note flash réelle du 8.01 FDA (#80).
from app.knowledge.evenements import QualificationLue  # noqa: E402
from app.knowledge.material_events import MaterialEventLookup, parse_material_events  # noqa: E402

_cols = ("form", "reportDate", "filingDate", "items", "accessionNumber")
_lignes = (("8-K", "2026-08-27", "2026-09-01", "1.01,2.03", "0001193125-26-377362"),
           ("8-K", "2026-08-26", "2026-08-26", "8.01", "acc-rvmd-fda"),
           ("10-Q", "2026-06-30", "2026-08-05", "", "0001193125-26-335104"),
           ("8-K", "2026-08-05", "2026-08-05", "2.02,9.01", "0001193125-26-335039"))
_flux = MaterialEventLookup(status="found", cik=1628171, recents=tuple(parse_material_events(
    {"filings": {"recent": {c: [l[i] for l in _lignes] for i, c in enumerate(_cols)}}},
    1628171, limit=100)))
_notes = {"acc-rvmd-fda": QualificationLue(
    types=frozenset({"reglementaire_favorable"}),
    resume="note flash du 2026-09-26 : « the U.S. Food and Drug Administration approved RASONQUE™ »"),
          # condition 1 (2026-10-16) : le communiqué de résultats est LU — ici, rien de plus que les comptes
          "0001193125-26-335039": QualificationLue(types=frozenset({"routine"}),
                                                   resume="note flash : rien de plus que les comptes")}
try:
    FQ = T.fraicheur_des_questions(_flux, _notes, F)
except Exception as e:  # noqa: BLE001 — un refus inattendu est un FAIL nommé, pas la mort du script
    FQ = {}
    check("fraicheur_des_questions rend une horloge", False, f"→ LÈVE {e!r}")
_toutes = {q.id for f in F.frameworks for q in f.questions}
check("une horloge pour CHAQUE question du référentiel (aucune tue)", set(FQ) == _toutes,
      f"→ manquent {sorted(_toutes - set(FQ))[:5]}")
_m1, _m2, _m6 = FQ.get("me_1"), FQ.get("me_2"), FQ.get("me_6")
check("me_1 (rouverte par l'approbation du 26/08, POSTÉRIEURE aux comptes) : un fait À LIRE, nommé — "
      "il ne fixe pas de date minimale (#117, lire et annoter)",
      _m1 is not None and _m1.depuis is None and len(_m1.a_lire) == 1
      and "reglementaire_favorable" in _m1.a_lire[0], f"→ {_m1}")
check("me_2 (rouverte par les résultats) : date minimale = la CLÔTURE publiée (30/06), pas le 05/08 (#102)",
      _m2 is not None and _m2.etat == "fait_important" and _m2.depuis == date(2026, 6, 30), f"→ {_m2}")
check("me_6 (ni accord ni incident au flux) : `aucun_fait`, sans date inventée ni fait à lire",
      _m6 is not None and _m6.etat == "aucun_fait" and _m6.depuis is None and _m6.a_lire == (),
      f"→ {_m6}")
_q4 = FQ.get("qf_4")
check("qf_4 (rouverte par le financement du 27/08 ET les résultats) : date minimale = la clôture 30/06, "
      "le financement postérieur est À LIRE, jamais la date minimale",
      _q4 is not None and _q4.depuis == date(2026, 6, 30)
      and any("financement" in x for x in _q4.a_lire), f"→ {_q4}")
_fq_inc = T.fraicheur_des_questions(MaterialEventLookup(status="unavailable", raison="EDGAR 503"), {}, F)
check("flux illisible : `inconnu` — jamais « aucun fait » (#49)",
      _fq_inc.get("me_1") is not None and _fq_inc["me_1"].etat == "inconnu", f"→ {_fq_inc.get('me_1')}")
if FQ:
    _H_RVMD = T.HorlogeDuPlan(date(2026, 10, 13), date(2026, 6, 30), FQ)
    _ctx_me = T.contexte_traducteur(F, "modele_economique", "pre_revenus", "RVMD", emetteur=IdentiteEmetteur(
        symbole="RVMD", cik=1628171, raison_sociale="Revolution Medicines, Inc."), horloge=_H_RVMD)
    _fr = {qq["id"]: qq.get("fraicheur") or {} for qq in _ctx_me["questions"]}
    check("le contexte porte la date minimale de me_2 ET la lecture la nomme",
          _fr.get("me_2", {}).get("date_minimale_des_pieces") == "2026-06-30"
          # la PHRASE du seuil, pas la date nue : un résumé de dépôt peut la porter (faux vert mesuré)
          and "AVANT le 2026-06-30" in (_fr.get("me_2", {}).get("lecture") or ""), f"→ {_fr.get('me_2')}")
    check("le contexte de me_1 nomme l'approbation comme fait À LIRE, et dit qu'il ne périme rien",
          len(_fr.get("me_1", {}).get("faits_a_lire_depuis_les_comptes") or []) == 1
          and "ne périment PAS" in (_fr.get("me_1", {}).get("lecture_des_faits") or ""),
          f"→ {_fr.get('me_1')}")
    check("une question sans fait porte sa fraîcheur À null, dite (clé présente, jamais omise)",
          "date_minimale_des_pieces" in _fr.get("me_6", {})
          and _fr["me_6"]["date_minimale_des_pieces"] is None, f"→ {_fr.get('me_6')}")
try:
    T.contexte_traducteur(F, "modele_economique", "pre_revenus", "RVMD", emetteur=NVDA,
                          horloge=T.HorlogeDuPlan(date(2026, 10, 13), None, {}))
    check("une question SANS horloge fait refuser le contexte (pas de défaut silencieux)", False)
except KeyError:
    check("une question SANS horloge fait refuser le contexte (pas de défaut silencieux)", True)
check("la consigne dit que la date minimale PRIME sur la clôture, `exercice_clos` compris",
      "`date_minimale_des_pieces`" in T._TRADUCTEUR_SYSTEM_PROMPT
      and "PRIME sur la clôture" in T._TRADUCTEUR_SYSTEM_PROMPT
      and "y compris une ligne `exercice_clos`" in T._TRADUCTEUR_SYSTEM_PROMPT)
_src_h8 = inspect.getsource(T.horloge_du_plan)
check("l'horloge par question est lue sur l'ancre ET les notes de `horloge_du_titre` (#46)",
      "fraicheur_des_questions(ancre, notes, fichier)" in _src_h8)
_src_fq = inspect.getsource(T.fraicheur_des_questions)
check("… par les détenteurs uniques `ancre_de_la_question` et `types_qui_rouvrent` (#89)",
      "ancre_de_la_question(ancre, rouvrent=types_qui_rouvrent(fichier, q.id)" in _src_fq)
check("… la date est le SEUIL du dépôt (#102), et les faits à lire viennent de `faits_a_lire` (#103)",
      "pese.seuil" in _src_fq and "faits_a_lire(lk, cloture=cloture)" in _src_fq)


# ── §9 une ligne `exercice_clos` sur une question rouverte par des comptes plus récents est refusée ──
print("\n[9] `exercice_clos` ne vise pas un rapport antérieur à la date minimale de la question")
# Mesuré à blanc (2026-10-13) : NVDA × modèle économique, 6 lignes `exercice_clos` (rapport annuel
# clos le 25/01) sur me_2/me_3/me_6, que les comptes du 26/07 rouvrent — plan ancré au 26/07 malgré tout.
from app.contracts.collection_plan_schema import CollectionPlan  # noqa: E402


def _ligne(qid, iid, periode):
    # Forme copiée du plan NVDA lu à blanc le 2026-10-13.
    return {"question_id": qid, "ingredient_id": iid, "statut": "traduit", "periode": periode,
            "metrique": "Revenus par segment (Compute & Networking, Graphics)",
            "source_pressentie": "10-K (notes aux états financiers - information sectorielle), 10-Q",
            "ancre": "2026-07-26"}


_FQ9 = dict(SANS_FAIT)
_FQ9["me_2"] = T.FraicheurQuestion("fait_important", date(2026, 7, 26), "8-K du 2026-08-26 (résultats)")
_plan9 = CollectionPlan(ticker_id="NVDA", framework_id="modele_economique", framework_version=F.schema_version,
                        archetype="rentable", items=[
                            _ligne("me_2", "repartition_du_chiffre_d_affaires", "exercice_clos"),
                            # chiffres courants TRIMESTRIELS (2026-10-16) : seuls ceux-là restent jugés par
                            # la garde sous la règle de durée de vie — une fixture d'historiques ou de
                            # descriptions ne discriminerait plus « cumul_publie » ni « sans date minimale »
                            _ligne("me_2", "montant_engage_non_reconnu", "cumul_publie"),
                            _ligne("me_6", "poids_des_premiers_clients", "exercice_clos")])
_nvda9 = T.HorlogeDuPlan(date(2026, 10, 13), date(2026, 7, 26), _FQ9, derniere_cloture_annuelle=None)
def _fautives(plan, horloge, fichier=F):
    try:
        return T.lignes_exercice_clos_perimees(plan, horloge, fichier=fichier)
    except Exception as e:  # noqa: BLE001 — un refus inattendu est un FAIL nommé, pas la mort du script
        return [f"LÈVE : {e!r}"]


_f9 = _fautives(_plan9, _nvda9)
check("NVDA (dernière clôture = un trimestre) : la seule ligne `exercice_clos` d'une question à date "
      "minimale est refusée, nommée — pas `cumul_publie`, pas une question sans date minimale",
      len(_f9) == 1 and _f9[0].startswith("me_2.repartition_du_chiffre_d_affaires"), f"→ {_f9}")
_nvda9b = T.HorlogeDuPlan(date(2026, 10, 13), date(2026, 7, 26), _FQ9,
                          derniere_cloture_annuelle=date(2026, 1, 25))
check("NVDA, exercice clos le 25/01 connu : toujours refusée (25/01 < 26/07)",
      len(_fautives(_plan9, _nvda9b)) == 1)
_FQ9m = dict(SANS_FAIT)
_FQ9m["me_2"] = T.FraicheurQuestion("fait_important", date(2026, 6, 30), "8-K du 2026-07-29 (résultats)")
_msft9 = T.HorlogeDuPlan(date(2026, 10, 13), date(2026, 6, 30), _FQ9m, derniere_cloture_annuelle=date(2026, 6, 30))
check("MSFT (la dernière clôture EST l'exercice, 30/06) : `exercice_clos` est la bonne lecture — admise",
      _fautives(_plan9, _msft9) == [], f"→ {_fautives(_plan9, _msft9)}")
# Règle de fraîcheur par durée de vie (2026-10-16) — le cas qui a fait refuser le plan NVDA × management :
# un historique pluriannuel et une description annuelle se lisent au rapport annuel.
_FQma = dict(SANS_FAIT)
for _q in ("ma_1", "ma_2", "ma_6"):
    _FQma[_q] = T.FraicheurQuestion("fait_important", date(2026, 7, 26), "8-K du 2026-08-26 (résultats)")
_nvda_ma = T.HorlogeDuPlan(date(2026, 10, 16), date(2026, 7, 26), _FQma, derniere_cloture_annuelle=date(2026, 1, 25))
_plan_ma = CollectionPlan(ticker_id="NVDA", framework_id="management_capital", framework_version=F.schema_version,
                          archetype="rentable", items=[
                              _ligne("ma_1", "repartition_des_usages", "exercice_clos"),
                              _ligne("ma_2", "acquisitions_realisees", "exercice_clos"),
                              _ligne("ma_6", "independance_du_conseil", "exercice_clos")])
check("durée de vie : historiques et description annuelle à l'exercice clos sont ADMIS (interrupteur actif)",
      _fautives(_plan_ma, _nvda_ma) == [], f"→ {_fautives(_plan_ma, _nvda_ma)}")
_off = F.model_copy(update={"fraicheur_par_duree_de_vie": False})
check("témoin ordre 0 (interrupteur coupé, ou fichier absent) : les trois lignes sont refusées",
      len(_fautives(_plan_ma, _nvda_ma, _off)) == 3 and len(_fautives(_plan_ma, _nvda_ma, None)) == 3,
      f"→ {_fautives(_plan_ma, _nvda_ma, _off)}")
_ctx_ma = T.contexte_traducteur(F, "management_capital", "rentable", "NVDA", emetteur=NVDA, horloge=_nvda_ma)
_ing_ma = {i["id"]: i for q in _ctx_ma["questions"] for i in q["ingredients"]}
check("le contexte montre la durée de vie et la cadence de chaque ingrédient (interrupteur actif)",
      _ing_ma.get("repartition_des_usages", {}).get("duree_de_vie") == "historique"
      and _ing_ma.get("repartition_des_usages", {}).get("cadence") == "trimestrielle"
      and _ing_ma.get("independance_du_conseil", {}).get("duree_de_vie") == "description_annuelle",
      f"→ {_ing_ma.get('repartition_des_usages')}")
_ctx_off = T.contexte_traducteur(_off, "management_capital", "rentable", "NVDA", emetteur=NVDA, horloge=_nvda_ma)
check("interrupteur coupé : la durée de vie n'est pas montrée (la consigne traite tout en chiffre courant)",
      all("duree_de_vie" not in i for q in _ctx_off["questions"] for i in q["ingredients"]))
check("la consigne enseigne la durée de vie (historique complété, description au document annuel)",
      "DURÉE DE VIE" in T._TRADUCTEUR_SYSTEM_PROMPT and "se complète de la dernière période publiée"
      in T._TRADUCTEUR_SYSTEM_PROMPT)
_ctx9 = T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", emetteur=NVDA, horloge=_nvda9b)
check("le contexte montre la clôture du dernier exercice, datée (et à null, clé présente, si inconnue)",
      _ctx9["calendrier"].get("cloture_du_dernier_exercice_publie") == "2026-01-25"
      and CTX["calendrier"].get("cloture_du_dernier_exercice_publie", "ABSENTE") is None,
      f"→ {_ctx9['calendrier']}")
_src_tr9 = inspect.getsource(T.traduire)
check("`traduire` applique la garde APRÈS le pont, renvoie UNE fois, puis refuse nommément",
      _src_tr9.count("lignes_exercice_clos_perimees(plan, horloge, fichier=fichier)") == 2
      and "raise CollectionPlanRefused(" in _src_tr9 and _src_tr9.count("run_json_agent(") == 2)
check("… et le passage coûte les DEUX appels (#41)",
      "cost_usd=run.cost_usd + second.cost_usd" in _src_tr9)
check("`horloge_du_plan` lit la clôture d'exercice sur le flux (`derniere_cloture_annuelle_publiee`)",
      "derniere_cloture_annuelle=derniere_cloture_annuelle_publiee(ancre)" in inspect.getsource(T.horloge_du_plan))


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
