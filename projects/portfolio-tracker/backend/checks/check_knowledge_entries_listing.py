"""Vérification de GET /tickers/{ticker_id}/knowledge/entries et
GET /knowledge/entries/{entry_id} — pur, hors ligne, sans appel réseau ni DB ni LLM.

Routes nouvelles (sprint UX-2) : elles exposent le corpus de connaissance V2 au frontend.
Sans elles, la base de connaissance existe en DB mais est invisible à l'utilisateur.

Ce qu'on éprouve (hors ligne — aucun appel réseau, aucune DB) :

  §1  Colonnes exportées — `embedding` ABSENT de _ENTRY_SELECT et de _ENTRY_COLUMNS ;
      toutes les autres colonnes de la spec sont présentes.
  §2  _build_entries_query — numérotation des paramètres positionnels ($1, $2…) :
      chaque filtre optionnel reçoit le bon indice en fonction des filtres activés avant
      lui. Un décalage d'un cran (le bug d'origine : idx=2 au lieu de idx=1) ferait
      pointer $3 sur un paramètre inexistant → asyncpg lèverait en prod.
  §3  Filtre `include_inactive=False` (défaut) — `is_deleted = false` ET
      `superseded_by IS NULL` dans le WHERE ; `include_inactive=True` — ces deux
      conditions sont absentes.
  §4  Filtre `covers` — génère `$N = ANY(ke.covers)` avec le bon indice.
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
    "has_conflict", "conflict_entry_id", "requires_human_review", "reviewed_by_user",
    "last_reviewed_at", "model_cutoff", "version", "valid_from", "superseded_by",
    "question_status", "question_priority", "resolves_entry_id",
    "is_outdated", "is_deleted", "created_at", "updated_at", "covers",
)
for col in COLONNES_REQUISES:
    check(f"colonne '{col}' présente dans _ENTRY_COLUMNS", col in _ENTRY_COLUMNS)

# ── §2 — Numérotation des paramètres ─────────────────────────────────────────
print("\n§2 — Numérotation des paramètres positionnels")

# Cas de base : uniquement ticker_id → $1
sql_count, sql_page, sql_tier, params = _build_entries_query(
    "NVDA", None, None, None, False, 50, 0,
)
check("sans filtre : WHERE ticker_id = $1", "$1" in sql_count and "$2" not in sql_count.split("$1")[1].split("WHERE")[0])
check("sans filtre : params_filter = [ticker_id]", params[:-2] == ["NVDA"])
check("sans filtre : params = [ticker_id, limit, offset]", params == ["NVDA", 50, 0])

# entry_type seul : doit être $2
sql_count2, sql_page2, sql_tier2, params2 = _build_entries_query(
    "NVDA", "fact_qualitative", None, None, False, 50, 0,
)
check("entry_type seul : entry_type = $2 dans WHERE", "ke.entry_type = $2" in sql_count2,
      f"— WHERE={sql_count2}")
check("entry_type seul : params_filter = [ticker, type]",
      params2[:-2] == ["NVDA", "fact_qualitative"])

# reliability_tier seul : doit être $2
sql_count3, _, _, params3 = _build_entries_query(
    "NVDA", None, "A", None, False, 50, 0,
)
check("reliability_tier seul : reliability_tier = $2 dans WHERE",
      "ke.reliability_tier = $2" in sql_count3, f"— WHERE={sql_count3}")
check("reliability_tier seul : params_filter = [ticker, tier]",
      params3[:-2] == ["NVDA", "A"])

# covers seul : doit être $2
sql_count4, _, _, params4 = _build_entries_query(
    "NVDA", None, None, "financials.roic_pct", False, 50, 0,
)
check("covers seul : $2 = ANY(ke.covers) dans WHERE",
      "$2 = ANY(ke.covers)" in sql_count4, f"— WHERE={sql_count4}")
check("covers seul : params_filter = [ticker, covers]",
      params4[:-2] == ["NVDA", "financials.roic_pct"])

# entry_type + reliability_tier : $2 et $3
sql_count5, _, _, params5 = _build_entries_query(
    "NVDA", "fact_qualitative", "A", None, False, 50, 0,
)
check("entry_type+tier : entry_type = $2 ET tier = $3",
      "ke.entry_type = $2" in sql_count5 and "ke.reliability_tier = $3" in sql_count5,
      f"— WHERE={sql_count5}")
check("entry_type+tier : params_filter = [ticker, type, tier]",
      params5[:-2] == ["NVDA", "fact_qualitative", "A"])

# Tous filtres : $2, $3, $4 ; limit=$5, offset=$6
sql_count6, sql_page6, _, params6 = _build_entries_query(
    "NVDA", "fact_qualitative", "A", "financials.roic_pct", False, 20, 10,
)
check("tous filtres : entry_type=$2, tier=$3, covers=$4",
      "ke.entry_type = $2" in sql_count6
      and "ke.reliability_tier = $3" in sql_count6
      and "$4 = ANY(ke.covers)" in sql_count6,
      f"— WHERE={sql_count6}")
check("tous filtres : LIMIT $5 OFFSET $6 dans sql_page",
      "LIMIT $5 OFFSET $6" in sql_page6, f"— PAGE={sql_page6[-50:]}")
check("tous filtres : params = [ticker, type, tier, covers, 20, 10]",
      params6 == ["NVDA", "fact_qualitative", "A", "financials.roic_pct", 20, 10])

# ── §3 — Filtre include_inactive ───────────────────────────────────────────────
print("\n§3 — Filtre include_inactive")

sql_active, _, _, _ = _build_entries_query("NVDA", None, None, None, False, 50, 0)
sql_all, _, _, _ = _build_entries_query("NVDA", None, None, None, True, 50, 0)

check("include_inactive=False : is_deleted = false dans WHERE",
      "ke.is_deleted = false" in sql_active)
check("include_inactive=False : superseded_by IS NULL dans WHERE",
      "ke.superseded_by IS NULL" in sql_active)
check("include_inactive=True : is_deleted absent du WHERE",
      "is_deleted" not in sql_all)
check("include_inactive=True : superseded_by IS NULL absent du WHERE",
      "superseded_by IS NULL" not in sql_all)

# ── §4 — Filtre covers ────────────────────────────────────────────────────────
print("\n§4 — Filtre covers (index GIN)")

_, _, sql_tier_covers, params_covers = _build_entries_query(
    "NVDA", None, None, "financials.roic_pct", False, 50, 0,
)
check("covers : ANY(ke.covers) dans le WHERE du tier",
      "ANY(ke.covers)" in sql_tier_covers)
# Le paramètre covers est le 2ème dans la liste filtrée
check("covers : params_filter[1] = chemin covers",
      params_covers[:-2][1] == "financials.roic_pct")

# ── §5 — Filtres combinés — indices consécutifs ───────────────────────────────
print("\n§5 — Filtres combinés : indices consécutifs sans trou")

_, sql_page_all, _, params_all = _build_entries_query(
    "MSFT", "fact_financial", "A", "financials.levier", False, 10, 5,
)
check("filtres combinés : $1=ticker, $2=type, $3=tier, $4=covers, $5=limit, $6=offset",
      params_all == ["MSFT", "fact_financial", "A", "financials.levier", 10, 5])
check("filtres combinés : ORDER BY ke.id DESC dans PAGE",
      "ORDER BY ke.id DESC" in sql_page_all)

# ── §6 — SQL TIER sans accolades littérales ───────────────────────────────────
print("\n§6 — SQL TIER : pas d'accolades susceptibles de casser une f-string")

_, _, sql_tier_base, _ = _build_entries_query("NVDA", None, None, None, False, 50, 0)

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
_, sql_page_base, _, _ = _build_entries_query("NVDA", None, None, None, False, 50, 0)
check("sql_count ne contient aucune accolade littérale",
      "{" not in sql_count and "}" not in sql_count)
check("sql_page ne contient aucune accolade littérale",
      "{" not in sql_page_base and "}" not in sql_page_base)

# ── §7 — Signature list_knowledge_entries ────────────────────────────────────
print("\n§7 — Signature et defaults de list_knowledge_entries")

import inspect
sig = inspect.signature(list_knowledge_entries)
params_sig = sig.parameters

check("list_knowledge_entries : paramètre ticker_id", "ticker_id" in params_sig)
check("list_knowledge_entries : paramètre entry_type (optionnel)",
      "entry_type" in params_sig and params_sig["entry_type"].default is None)
check("list_knowledge_entries : paramètre reliability_tier (optionnel)",
      "reliability_tier" in params_sig and params_sig["reliability_tier"].default is None)
check("list_knowledge_entries : paramètre covers (optionnel)",
      "covers" in params_sig and params_sig["covers"].default is None)
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

for include_del in (False, True):
    for et in (None, "fact_qualitative"):
        for t in (None, "A"):
            for cov in (None, "financials.roic_pct"):
                sc, sp, st, _ = _build_entries_query(
                    "NVDA", et, t, cov, include_del, 50, 0,
                )
                check(
                    f"embedding absent du SELECT (del={include_del}, type={et}, tier={t}, covers={cov})",
                    "embedding" not in sp and "embedding" not in sc and "embedding" not in st,
                )


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
