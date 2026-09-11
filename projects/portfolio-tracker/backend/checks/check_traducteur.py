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

from app.agents.v2 import traducteur as T
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
CTX = T.contexte_traducteur(F, "qualite_financiere", "rentable", "NVDA")
_ser = json.dumps(CTX, ensure_ascii=False)
check("le contexte ne contient pas `plancher_tier` (le modèle ne fixe pas le niveau de preuve)",
      "plancher_tier" not in _ser)
check("le contexte ne contient pas `nature_attendue` (idem — c'est la méthode qui le tient)",
      "nature_attendue" not in _ser)

# ── §3 le contexte est complet ────────────────────────────────────────────────────────────────────
print("\n[3] le modèle ne peut planifier que ce qu'on lui montre — donc on montre tout le requis")
_essentiels = {(q.id, i.id) for q in _appl_rt for i in q.ingredients_requis if i.essentiel}
_ctx_couples = {(qq["id"], ii["id"]) for qq in CTX["questions"] for ii in qq["ingredients"]}
check("tous les ingrédients essentiels des questions applicables figurent au contexte",
      _essentiels <= _ctx_couples, f"→ manquants : {sorted(_essentiels - _ctx_couples)}")
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
           lambda: T.contexte_traducteur(F, "qualite_financiere", "archetype_bidon", "NVDA"))


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
