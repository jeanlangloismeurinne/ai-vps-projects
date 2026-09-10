"""Vérification de GET /tickers/{ticker_id}/knowledge/entries et
GET /knowledge/entries/{entry_id} — pur, hors ligne, sans appel réseau ni DB ni LLM.

Routes nouvelles (sprint UX-2) : elles exposent le corpus de connaissance V2 au frontend.
Sans elles, la base de connaissance existe en DB mais est invisible à l'utilisateur.

Ce qu'on éprouve (hors ligne — aucun appel réseau, aucune DB) :

  §1  Colonnes exportées — `embedding` ABSENT de _ENTRY_SELECT et de _ENTRY_COLUMNS ;
      les colonnes de la spec sont présentes, et les 8 colonnes retirées par la 036 —
      lues sur leur détenteur, `_gen_036.COLONNES_RETIREES` — n'y sont plus.
  §2  _build_entries_query — numérotation des paramètres positionnels ($1, $2…) :
      chaque filtre optionnel reçoit le bon indice en fonction des filtres activés avant
      lui. Un décalage d'un cran (le bug d'origine : idx=2 au lieu de idx=1) ferait
      pointer $3 sur un paramètre inexistant → asyncpg lèverait en prod.
  §3  Filtre `include_inactive=False` (défaut) — `superseded_by IS NULL` est le SEUL
      prédicat de vivacité (`is_deleted` est archivée) ; `include_inactive=True` — il
      est absent.
  §4  Aucun filtre de couverture — la structure de la fonction, pas un grep d'interdit.
  §5  Filtre `entry_type` + `reliability_tier` combinés — indices consécutifs corrects.
  §6  SQL TIER — la requête de comptage par tier ne contient aucune accolade littérale
      susceptible de casser une f-string (convention #39) ; toutes les clés attendues
      sont présentes dans le template SQL (A, A-, B+, etc.).
  §7  Route `list_knowledge_entries` — signature et paramètres par défaut corrects ;
      la validation `reliability_tier` rejette les valeurs hors domaine.
  §8  Route `get_knowledge_entry` — signature, paramètre `entry_id: int`.
  §9  Réponse listing — clés de retour exactes : `total`, `par_tier`, `entries`.
  §10 Embedding absent du SELECT — le SQL généré ne contient pas le mot `embedding`.
"""
import ast
import inspect
import sys
from pathlib import Path

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# ── Imports ───────────────────────────────────────────────────────────────────
from app.api.knowledge_v2 import (
    _ENTRY_COLUMNS,
    _ENTRY_SELECT,
    _ALL_TIERS,
    _build_entries_query,
    list_knowledge_entries,
    get_knowledge_entry,
)
# Les 8 colonnes que la 036 retire, LUES sur leur détenteur (#46) plutôt que recopiées ici. Une
# liste jumelle serait d'accord avec son modèle aujourd'hui et divergerait au prochain retrait,
# en silence — c'est précisément le mode de panne que #46 décrit.
from app.db.migrations._gen_036 import COLONNES_RETIREES

# ── §1 — Colonnes exportées ───────────────────────────────────────────────────
print("§1 — Colonnes exportées : embedding absent, colonnes spec présentes")

# embedding doit être ABSENT (vector 1024 = bruit illisible)
check("embedding absent de _ENTRY_COLUMNS", "embedding" not in _ENTRY_COLUMNS)
check("embedding absent de _ENTRY_SELECT", "embedding" not in _ENTRY_SELECT)

# Colonnes obligatoires selon la spec du schéma
COLONNES_REQUISES = (
    "id", "ticker_id", "entry_type", "title", "content", "content_structured",
    "tags", "lang", "source_type", "source_url", "source_date", "fiscal_period",
    "reliability_score", "reliability_tier", "reliability_note",
    "requires_human_review", "nature",
    "last_reviewed_at", "model_cutoff", "version", "valid_from", "superseded_by",
    "is_outdated", "created_at", "updated_at",
)
for col in COLONNES_REQUISES:
    check(f"colonne '{col}' présente dans _ENTRY_COLUMNS", col in _ENTRY_COLUMNS)

# `nature` est l'axe de la 034 (#51), et c'est ICI qu'il compte : un axe dérivé à l'écriture mais
# absent du point de LECTURE ne serait qu'un calcul (`feedback_controle_au_point_de_lecture`).
check("`nature` est servie au lecteur, pas seulement dérivée à l'écriture",
      "nature" in _ENTRY_COLUMNS)
_encore_la = sorted(set(COLONNES_RETIREES) & set(_ENTRY_COLUMNS))
check("aucune des colonnes retirées par la 036 n'est encore SELECTée",
      not _encore_la,
      f"→ {_encore_la} — la requête lèverait en prod (colonnes passées en archive_v2)")

# ── §2 — Numérotation des paramètres ─────────────────────────────────────────
print("\n§2 — Numérotation des paramètres positionnels")

# Cas de base : uniquement ticker_id → $1
sql_count, sql_page, sql_tier, params = _build_entries_query("NVDA", None, None, False, 50, 0)
check("sans filtre : WHERE ticker_id = $1", "$1" in sql_count and "$2" not in sql_count.split("$1")[1].split("WHERE")[0])
check("sans filtre : params_filter = [ticker_id]", params[:-2] == ["NVDA"])
check("sans filtre : params = [ticker_id, limit, offset]", params == ["NVDA", 50, 0])

# entry_type seul : doit être $2
sql_count2, sql_page2, sql_tier2, params2 = _build_entries_query("NVDA", "fact_qualitative", None, False, 50, 0)
check("entry_type seul : entry_type = $2 dans WHERE", "ke.entry_type = $2" in sql_count2,
      f"— WHERE={sql_count2}")
check("entry_type seul : params_filter = [ticker, type]",
      params2[:-2] == ["NVDA", "fact_qualitative"])

# reliability_tier seul : doit être $2
sql_count3, _, _, params3 = _build_entries_query("NVDA", None, "A", False, 50, 0)
check("reliability_tier seul : reliability_tier = $2 dans WHERE",
      "ke.reliability_tier = $2" in sql_count3, f"— WHERE={sql_count3}")
check("reliability_tier seul : params_filter = [ticker, tier]",
      params3[:-2] == ["NVDA", "A"])

# entry_type + reliability_tier : $2 et $3
sql_count5, _, _, params5 = _build_entries_query("NVDA", "fact_qualitative", "A", False, 50, 0)
check("entry_type+tier : entry_type = $2 ET tier = $3",
      "ke.entry_type = $2" in sql_count5 and "ke.reliability_tier = $3" in sql_count5,
      f"— WHERE={sql_count5}")
check("entry_type+tier : params_filter = [ticker, type, tier]",
      params5[:-2] == ["NVDA", "fact_qualitative", "A"])

# Tous filtres : $2, $3 ; limit=$4, offset=$5
sql_count6, sql_page6, _, params6 = _build_entries_query(
    "NVDA", "fact_qualitative", "A", False, 20, 10,
)
check("tous filtres : entry_type=$2, tier=$3",
      "ke.entry_type = $2" in sql_count6
      and "ke.reliability_tier = $3" in sql_count6,
      f"— WHERE={sql_count6}")
check("tous filtres : LIMIT $4 OFFSET $5 dans sql_page",
      "LIMIT $4 OFFSET $5" in sql_page6, f"— PAGE={sql_page6[-50:]}")
check("tous filtres : params = [ticker, type, tier, 20, 10]",
      params6 == ["NVDA", "fact_qualitative", "A", 20, 10])

# ── §3 — Filtre include_inactive ───────────────────────────────────────────────
print("\n§3 — Filtre include_inactive")

sql_active, _, _, _ = _build_entries_query("NVDA", None, None, False, 50, 0)
sql_all, _, _, _ = _build_entries_query("NVDA", None, None, True, 50, 0)

# ⚠️ `is_deleted` a disparu des DEUX branches (036). Le mode de panne à garder est asymétrique :
# le laisser dans le WHERE `False` casserait la requête (colonne archivée), donc bruyamment. Le
# laisser dans la branche `True` ne casserait rien mais RÉTRÉCIRAIT silencieusement le « tout
# afficher » — c'est ce sens-là qui vaut deux asserts.
check("include_inactive=False : `is_deleted` ne figure plus dans le WHERE",
      "is_deleted" not in sql_active,
      "→ la colonne est archivée : la requête lèverait en prod")
check("include_inactive=False : superseded_by IS NULL dans WHERE",
      "ke.superseded_by IS NULL" in sql_active)
check("include_inactive=False : `superseded_by IS NULL` est le SEUL prédicat de vivacité",
      sql_active.count("superseded_by") == 1 and "is_deleted" not in sql_active,
      f"— WHERE={sql_active}")
check("include_inactive=True : `is_deleted` absent du WHERE", "is_deleted" not in sql_all)
check("include_inactive=True : superseded_by IS NULL absent du WHERE",
      "superseded_by IS NULL" not in sql_all)

# ── §4 — Le filtre `covers` a été retiré, pas remplacé ────────────────────────
print("\n§4 — Aucun filtre de couverture tant qu'aucun émetteur ne l'alimente")
# ⚠️ §4 éprouvait `$N = ANY(ke.covers)` sur l'index GIN. Le filtre est parti avec la colonne (036).
# Ce qui est gardé ici n'est PAS son absence textuelle — un `grep` d'interdit se satisfait de la
# prose et se met en défaut sur elle (#56) — mais la STRUCTURE de la fonction : elle n'a que deux
# filtres arbitrables, et la table de liens n'est pas encore interrogée. Le remplacer tout de suite
# par un `EXISTS (SELECT 1 FROM question_coverage …)` produirait un filtre câblé de bout en bout que
# rien ne peut satisfaire — `question_coverage` est vide tant que le dispatch du lot 2c n'écrit pas —
# donc zéro ligne rendue sans que rien ne dise pourquoi : #50 réintroduit le jour où on le retire.
_PARAMS_BUILD = list(inspect.signature(_build_entries_query).parameters)
check("`_build_entries_query` n'expose que ticker + 2 filtres + pagination",
      _PARAMS_BUILD == ["ticker_id", "entry_type", "reliability_tier",
                        "include_inactive", "limit", "offset"],
      f"→ {_PARAMS_BUILD}")
check("aucun filtre de couverture n'est câblé au SQL généré",
      "question_coverage" not in sql_count6 and "covers" not in sql_count6,
      "→ le filtre par question revient AVEC son émetteur, pas avant")

# ── §5 — Filtres combinés — indices consécutifs ───────────────────────────────
print("\n§5 — Filtres combinés : indices consécutifs sans trou")

_, sql_page_all, _, params_all = _build_entries_query(
    "MSFT", "fact_financial", "A", False, 10, 5,
)
check("filtres combinés : $1=ticker, $2=type, $3=tier, $4=limit, $5=offset",
      params_all == ["MSFT", "fact_financial", "A", 10, 5])
check("filtres combinés : ORDER BY ke.id DESC dans PAGE",
      "ORDER BY ke.id DESC" in sql_page_all)

# ── §6 — SQL TIER sans accolades littérales ───────────────────────────────────
print("\n§6 — SQL TIER : pas d'accolades susceptibles de casser une f-string")

_, _, sql_tier_base, _ = _build_entries_query("NVDA", None, None, False, 50, 0)

# Toutes les clés par tier doivent être présentes
CLES_ATTENDUES = (
    "A", "A-", "B+", "B", "B-", "C+", "C",
)
for cle in CLES_ATTENDUES:
    check(f"clé '{cle}' présente dans sql_tier", "'" + cle + "'" in sql_tier_base)

# Aucune accolade { ou } dans le SQL tier (convention #39)
check("sql_tier ne contient aucune accolade littérale { }",
      "{" not in sql_tier_base and "}" not in sql_tier_base,
      f"— trouvé dans : {[c for c in sql_tier_base if c in '{}'][:5]}")

# Même vérification sur sql_count et sql_page
_, sql_page_base, _, _ = _build_entries_query("NVDA", None, None, False, 50, 0)
check("sql_count ne contient aucune accolade littérale",
      "{" not in sql_count and "}" not in sql_count)
check("sql_page ne contient aucune accolade littérale",
      "{" not in sql_page_base and "}" not in sql_page_base)

# ── §7 — Signature list_knowledge_entries ────────────────────────────────────
print("\n§7 — Signature et defaults de list_knowledge_entries")

sig = inspect.signature(list_knowledge_entries)
params_sig = sig.parameters

check("list_knowledge_entries : paramètre ticker_id", "ticker_id" in params_sig)
check("list_knowledge_entries : paramètre entry_type (optionnel)",
      "entry_type" in params_sig and params_sig["entry_type"].default is None)
check("list_knowledge_entries : paramètre reliability_tier (optionnel)",
      "reliability_tier" in params_sig and params_sig["reliability_tier"].default is None)
# La route n'expose plus de filtre de couverture : elle ne peut pas en exposer un que le SQL
# généré ne sait pas honorer (§4). Assert en POSITIF sur la liste des paramètres — un `not in`
# seul serait satisfait par n'importe quelle signature, y compris une signature vide.
check("la route expose exactement les filtres que le SQL sait honorer",
      set(params_sig) == {"ticker_id", "entry_type", "reliability_tier",
                          "include_inactive", "limit", "offset"},
      f"→ {sorted(params_sig)}")
check("list_knowledge_entries : include_inactive défaut False",
      "include_inactive" in params_sig and params_sig["include_inactive"].default is False)
check("list_knowledge_entries : limit défaut 50",
      "limit" in params_sig and params_sig["limit"].default == 50)
check("list_knowledge_entries : offset défaut 0",
      "offset" in params_sig and params_sig["offset"].default == 0)

# Validation du domaine reliability_tier (simulation de la garde HTTPException)
# On vérifie que _ALL_TIERS contient exactement les tiers du CHECK de la migration 024.
TIERS_MIGRATION_024 = ("A", "A-", "B+", "B", "B-", "C+", "C")
check("_ALL_TIERS correspond aux tiers du CHECK migration 024",
      set(_ALL_TIERS) == set(TIERS_MIGRATION_024))

# ── §8 — Signature get_knowledge_entry ───────────────────────────────────────
print("\n§8 — Signature de get_knowledge_entry")

sig_detail = inspect.signature(get_knowledge_entry)
params_detail = sig_detail.parameters
check("get_knowledge_entry : paramètre entry_id",
      "entry_id" in params_detail)
check("get_knowledge_entry : entry_id est int (annotation)",
      params_detail["entry_id"].annotation is int)

# SQL detail : embedding absent, $1 utilisé
src = Path("app/api/knowledge_v2.py").read_text(encoding="utf-8")
tree = ast.parse(src)
func_detail = None
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_knowledge_entry":
        func_detail = node
        break

func_detail_src = (
    "\n".join(src.splitlines()[func_detail.lineno - 1:func_detail.end_lineno])
    if func_detail else ""
)
check("get_knowledge_entry existe dans knowledge_v2.py", func_detail is not None)
# La docstring peut mentionner "embedding" pour expliquer l'exclusion ;
# ce qui importe c'est que le SELECT SQL ne le contient pas.
# On cherche "embedding" dans le corps hors docstrings (lignes qui ne commencent pas par triple-quote).
func_detail_lines_no_doc = [
    l for l in func_detail_src.splitlines()
    if not l.strip().startswith('"""') and not l.strip().startswith("'''")
    and "embedding" in l
    and "SELECT" in l  # seule ligne dangereuse : un SELECT * ou SELECT embedding
]
check("get_knowledge_entry : pas d'embedding dans les SELECT SQL",
      len(func_detail_lines_no_doc) == 0,
      f"— lignes suspectes : {func_detail_lines_no_doc}")
check("get_knowledge_entry utilise $1 comme paramètre",
      "$1" in func_detail_src)
check("get_knowledge_entry lève 404 si introuvable",
      "404" in func_detail_src and "introuvable" in func_detail_src.lower())

# ── §9 — Clés de retour du listing ───────────────────────────────────────────
print("\n§9 — Clés de retour de list_knowledge_entries")

func_list = None
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_knowledge_entries":
        func_list = node
        break

func_list_src = (
    "\n".join(src.splitlines()[func_list.lineno - 1:func_list.end_lineno])
    if func_list else ""
)
check("list_knowledge_entries existe dans knowledge_v2.py", func_list is not None)
for key in ("total", "par_tier", "entries"):
    check(f"list_knowledge_entries renvoie la clé '{key}'",
          f'"{key}"' in func_list_src or f"'{key}'" in func_list_src)

# ── §10 — embedding jamais dans le SELECT ────────────────────────────────────
print("\n§10 — embedding absent de tout SQL généré")

for include_inactive in (False, True):
    for et in (None, "fact_qualitative"):
        for t in (None, "A"):
            sc, sp, st, _ = _build_entries_query("NVDA", et, t, include_inactive, 50, 0)
            check(
                f"embedding absent du SELECT (inactive={include_inactive}, type={et}, tier={t})",
                "embedding" not in sp and "embedding" not in sc and "embedding" not in st,
            )


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
