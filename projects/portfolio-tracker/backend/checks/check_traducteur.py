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
H_NVDA = T.HorlogeDuPlan(date_du_jour=date(2026, 10, 13), derniere_cloture=date(2026, 7, 26))
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
check("… puis passe le plan au pont avant de le rendre (jamais un plan non validé)",
      "valider_pont_collection_plan" in _src)

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
                                      horloge=T.HorlogeDuPlan(date(2026, 10, 13), None))
_cal_i = _ctx_inconnue.get("calendrier") or {}
check("clôture inconnue : la clé est PRÉSENTE à null et la lecture dit INCONNUE (jamais omise ni devinée)",
      "cloture_des_derniers_comptes_publies" in _cal_i
      and _cal_i["cloture_des_derniers_comptes_publies"] is None
      and "INCONNUE" in (_cal_i.get("lecture") or ""), f"→ {_cal_i}")
try:
    T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA", emetteur=NVDA)
    check("le contexte REFUSE de se construire sans horloge (aucun défaut silencieux)", False)
except TypeError as e:
    check("le contexte REFUSE de se construire sans horloge (aucun défaut silencieux)",
          "horloge" in str(e), f"→ {e}")
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


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
