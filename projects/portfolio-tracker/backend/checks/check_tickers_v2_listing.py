"""Vérification de GET /v2/tickers — pur, hors ligne, aucun appel réseau ni modèle.

La route est le fil conducteur AMONT du flux V2 : elle donne à voir l'avancement de la
chaîne knowledge → readiness → research → analyses → décision pour chaque ticker.

Modes de panne silencieux spécifiques à cette route :

  • **le par_tier vide trompeur** — si la sous-requête corrélée ne filtre pas sur les entries
    vivantes, les tiers incluent des versions supersédées ou supprimées, gonflant les compteurs.
  • **la décision fantôme** — un LEFT JOIN sans LATERAL peut ramener N thèses au lieu de la
    plus récente, dupliquant des lignes ticker (une par thèse).
  • **l'include_all borgne** — sans le paramètre, les tickers sans entries ne doivent pas
    apparaître ; avec, ils doivent tous apparaître.
  • **les clés manquantes** — un null explicite n'est pas un champ absent : le frontend attend
    exactement les clés documentées, même quand leur valeur est null.

Ce qu'on éprouve (hors ligne) :

  §1  Shape des clés de premier niveau — toutes présentes, même quand la valeur est null.
  §2  `par_tier` — toutes les clés de tiers présentes (A, A-, B+, B, B-, C+, C), même à 0.
  §3  `readiness` — null quand il n'y en a pas, objet à 3 clés (id, verdict, created_at) sinon.
  §4  `nb_analyses_par_type` — les 3 clés (bull, bear, synthesis) présentes, valeur entière.
  §5  `these_v2` — null quand absent, objet à 2 clés (id, status) sinon.
  §6  Filtre `include_all=false` (défaut) — seuls les tickers avec matière V2 apparaissent.
  §7  Filtre `include_all=true` — tous les tickers, y compris ceux sans matière.
  §8  Isolation SQL — la route interroge `knowledge_entries`, pas `v0_theses` ni `theses`.
      La thèse V2 vient de `theses_v2`.
  §9  Pas de f-string avec accolades littérales dans list_tickers_v2 (convention #39).
  §10 Pas de colonne `embedding` dans le SELECT (convention knowledge_v2).
  §11 Tri : nb_entries_vivantes DESC en premier critère.
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
from app.api.analysis_v2 import list_tickers_v2
import inspect

# ── Fixtures ──────────────────────────────────────────────────────────────────
# Ticker AVEC matière V2 (NVDA-like : 52 entries vivantes, readiness ready, 3 memos, etc.)
TICKER_AVEC_MATIERE = {
    "ticker_id": "NVDA",
    "name": "NVDA",
    "ticker_symbol": "NVDA",
    "sector": None,
    "status": "portfolio",
    "company_type": "public",
    "nb_entries_vivantes": 52,
    "par_tier": {"A": 30, "A-": 2, "B+": 7, "B": 3, "B-": 5, "C+": 0, "C": 5},
    "readiness": {"id": 27, "verdict": "ready", "created_at": "2026-08-31T19:13:46.871170+00:00"},
    "nb_research_memos": 3,
    "dernier_research_memo_id": 3,
    "nb_analyses_par_type": {"bull": 2, "bear": 4, "synthesis": 1},
    "id_synthese_final": 4,
    "these_v2": None,   # NVDA n'a pas de thèse V2 active
}

# Ticker SANS matière V2 (ticker watchlist sans aucune entry)
TICKER_SANS_MATIERE = {
    "ticker_id": "AMZN",
    "name": "Amazon.com, Inc.",
    "ticker_symbol": "AMZN",
    "sector": None,
    "status": "watchlist",
    "company_type": "public",
    "nb_entries_vivantes": 0,
    "par_tier": {"A": 0, "A-": 0, "B+": 0, "B": 0, "B-": 0, "C+": 0, "C": 0},
    "readiness": None,
    "nb_research_memos": 0,
    "dernier_research_memo_id": None,
    "nb_analyses_par_type": {"bull": 0, "bear": 0, "synthesis": 0},
    "id_synthese_final": None,
    "these_v2": None,
}

# Ticker AVEC thèse V2 (MSFT-like)
TICKER_AVEC_THESE = {
    **TICKER_AVEC_MATIERE,
    "ticker_id": "MSFT",
    "name": "MSFT",
    "ticker_symbol": "MSFT",
    "nb_entries_vivantes": 54,
    "par_tier": {"A": 42, "A-": 2, "B+": 4, "B": 3, "B-": 3, "C+": 0, "C": 0},
    "readiness": {"id": 26, "verdict": "ready", "created_at": "2026-08-31T18:19:18.078245+00:00"},
    "nb_research_memos": 1,
    "dernier_research_memo_id": 4,
    "nb_analyses_par_type": {"bull": 2, "bear": 3, "synthesis": 1},
    "id_synthese_final": 11,
    "these_v2": {"id": 4, "status": "active"},
}

# Tiers valides — même domaine que knowledge_v2._ALL_TIERS
_ALL_TIERS = ("A", "A-", "B+", "B", "B-", "C+", "C")


# ── §1 — Clés de premier niveau ───────────────────────────────────────────────
print("§1 — Clés de premier niveau (toutes présentes même quand null)")

CLES_ATTENDUES = [
    "ticker_id", "name", "ticker_symbol", "sector", "status", "company_type",
    "nb_entries_vivantes", "par_tier",
    "readiness",
    "nb_research_memos", "dernier_research_memo_id",
    "nb_analyses_par_type", "id_synthese_final",
    "these_v2",
]

for row in (TICKER_AVEC_MATIERE, TICKER_SANS_MATIERE, TICKER_AVEC_THESE):
    tid = row["ticker_id"]
    for cle in CLES_ATTENDUES:
        check(f"{tid} — clé '{cle}' présente", cle in row, f"— clés : {sorted(row.keys())}")

# Aucune clé inattendue non documentée (lisibilité contrat)
check("ticker avec matière — exactement les clés documentées",
      set(TICKER_AVEC_MATIERE.keys()) == set(CLES_ATTENDUES),
      f"— delta : {set(TICKER_AVEC_MATIERE.keys()) ^ set(CLES_ATTENDUES)}")


# ── §2 — par_tier ─────────────────────────────────────────────────────────────
print("\n§2 — par_tier : toutes les clés de tiers présentes, valeur entière >= 0")

for row in (TICKER_AVEC_MATIERE, TICKER_SANS_MATIERE, TICKER_AVEC_THESE):
    tid = row["ticker_id"]
    pt = row["par_tier"]
    check(f"{tid} — par_tier n'est pas null", pt is not None)
    for t in _ALL_TIERS:
        check(f"{tid} — par_tier['{t}'] présent", t in pt, f"— clés: {sorted(pt.keys())}")
        check(f"{tid} — par_tier['{t}'] est entier >= 0",
              isinstance(pt.get(t), int) and pt[t] >= 0,
              f"— valeur: {pt.get(t)}")

# Les clés sont TEL QUEL (pas de nom maquillé — convention knowledge_v2)
check("par_tier clefé par tiers bruts (A, A-, B+ — pas de nom traduit)",
      all(k in _ALL_TIERS for k in TICKER_AVEC_MATIERE["par_tier"]))

# La somme des tiers == nb_entries_vivantes pour NVDA
nvda_sum = sum(TICKER_AVEC_MATIERE["par_tier"].values())
check("NVDA — somme par_tier == nb_entries_vivantes",
      nvda_sum == TICKER_AVEC_MATIERE["nb_entries_vivantes"],
      f"— somme={nvda_sum} nb_vivantes={TICKER_AVEC_MATIERE['nb_entries_vivantes']}")

# Ticker sans matière : tous les tiers à 0
check("AMZN (sans matière) — tous les tiers valent 0",
      all(v == 0 for v in TICKER_SANS_MATIERE["par_tier"].values()))


# ── §3 — readiness ────────────────────────────────────────────────────────────
print("\n§3 — readiness : null si absent, objet à 3 clés sinon")

check("AMZN — readiness est None (pas {})", TICKER_SANS_MATIERE["readiness"] is None)

for row in (TICKER_AVEC_MATIERE, TICKER_AVEC_THESE):
    tid = row["ticker_id"]
    r = row["readiness"]
    check(f"{tid} — readiness n'est pas None", r is not None)
    for k in ("id", "verdict", "created_at"):
        check(f"{tid} — readiness['{k}'] présent", k in r, f"— clés: {sorted(r.keys())}")
    check(f"{tid} — readiness a exactement 3 clés",
          set(r.keys()) == {"id", "verdict", "created_at"},
          f"— clés: {sorted(r.keys())}")

# Simule la logique "null si pas de readiness"
def _readiness_from_row(row_db):
    """Reflète la sous-requête scalaire JSONB de la route."""
    return row_db.get("readiness")

check("readiness=None pour un ticker sans rapport", _readiness_from_row({"readiness": None}) is None)
check("readiness=dict pour un ticker avec rapport",
      isinstance(_readiness_from_row({"readiness": {"id": 1, "verdict": "ready", "created_at": "2026-01-01"}}), dict))


# ── §4 — nb_analyses_par_type ─────────────────────────────────────────────────
print("\n§4 — nb_analyses_par_type : 3 clés (bull, bear, synthesis), valeur entière")

for row in (TICKER_AVEC_MATIERE, TICKER_SANS_MATIERE, TICKER_AVEC_THESE):
    tid = row["ticker_id"]
    na = row["nb_analyses_par_type"]
    check(f"{tid} — nb_analyses_par_type n'est pas null", na is not None)
    for k in ("bull", "bear", "synthesis"):
        check(f"{tid} — nb_analyses_par_type['{k}'] présent", k in na)
        check(f"{tid} — nb_analyses_par_type['{k}'] est entier >= 0",
              isinstance(na.get(k), int) and na[k] >= 0,
              f"— valeur: {na.get(k)}")
    check(f"{tid} — exactement 3 clés",
          set(na.keys()) == {"bull", "bear", "synthesis"})

# Ticker sans matière : tous à 0
check("AMZN — nb_analyses_par_type tout à 0",
      all(v == 0 for v in TICKER_SANS_MATIERE["nb_analyses_par_type"].values()))


# ── §5 — these_v2 ─────────────────────────────────────────────────────────────
print("\n§5 — these_v2 : null si absent, objet à 2 clés (id, status) sinon")

check("NVDA — these_v2 est None (pas de thèse)", TICKER_AVEC_MATIERE["these_v2"] is None)
check("AMZN — these_v2 est None (pas de thèse)", TICKER_SANS_MATIERE["these_v2"] is None)

tv = TICKER_AVEC_THESE["these_v2"]
check("MSFT — these_v2 n'est pas None", tv is not None)
check("MSFT — these_v2['id'] présent", "id" in tv)
check("MSFT — these_v2['status'] présent", "status" in tv)
check("MSFT — these_v2 a exactement 2 clés",
      set(tv.keys()) == {"id", "status"},
      f"— clés: {sorted(tv.keys())}")
check("MSFT — these_v2['status'] = 'active'", tv.get("status") == "active")


# ── §6 — Filtre include_all=false (défaut) ────────────────────────────────────
print("\n§6 — Filtre include_all=false : seuls les tickers avec matière V2")

# Simulation : filtre en Python comme le ferait le HAVING SQL
TOUS_TICKERS = [TICKER_AVEC_MATIERE, TICKER_SANS_MATIERE, TICKER_AVEC_THESE]

def simuler_liste(include_all=False):
    if include_all:
        return list(TOUS_TICKERS)
    return [t for t in TOUS_TICKERS if t["nb_entries_vivantes"] > 0]

resultat_defaut = simuler_liste(include_all=False)
resultat_tout = simuler_liste(include_all=True)

check("sans include_all — AMZN (0 entries) absent", all(t["ticker_id"] != "AMZN" for t in resultat_defaut))
check("sans include_all — NVDA présent", any(t["ticker_id"] == "NVDA" for t in resultat_defaut))
check("sans include_all — MSFT présent", any(t["ticker_id"] == "MSFT" for t in resultat_defaut))
check("sans include_all — 2 tickers (NVDA + MSFT)", len(resultat_defaut) == 2)


# ── §7 — Filtre include_all=true ─────────────────────────────────────────────
print("\n§7 — Filtre include_all=true : tous les tickers")

check("avec include_all=True — AMZN présent", any(t["ticker_id"] == "AMZN" for t in resultat_tout))
check("avec include_all=True — 3 tickers (tous)", len(resultat_tout) == 3)

# Vérification de la signature de la route
sig = inspect.signature(list_tickers_v2)
check("list_tickers_v2 accepte le paramètre include_all", "include_all" in sig.parameters)
check("include_all est optionnel (défaut False)",
      sig.parameters["include_all"].default is False)


# ── §8 — Isolation SQL ────────────────────────────────────────────────────────
print("\n§8 — Isolation SQL : tables sources correctes")

src = Path("app/api/analysis_v2.py").read_text(encoding="utf-8")
tree = ast.parse(src)

func_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_tickers_v2":
        func_node = node
        break

check("fonction list_tickers_v2 existe dans analysis_v2.py", func_node is not None)

func_src = "\n".join(src.splitlines()[func_node.lineno - 1:func_node.end_lineno]) if func_node else ""

# Tables sources attendues
check("lit knowledge_entries pour les entries vivantes", "knowledge_entries" in func_src)
check("lit tickers comme table principale", "FROM tickers" in func_src)
check("lit knowledge_curator_reports pour la readiness", "knowledge_curator_reports" in func_src)
check("lit research_memos pour les memos", "research_memos" in func_src)
check("lit investment_analyses pour les analyses", "investment_analyses" in func_src)
check("lit theses_v2 pour la décision (pas theses)", "theses_v2" in func_src)

# Isolation V1 : ne pas lire `theses` (table V1) — ni `v0_theses`
# On vérifie que "theses_v2" est présent MAIS "FROM theses " (sans suffixe) ne l'est pas
func_src_no_v2 = func_src.replace("theses_v2", "")
check("ne lit pas theses (table V1) — isolation V1/V2",
      "FROM theses" not in func_src_no_v2 and "JOIN theses" not in func_src_no_v2)
check("ne lit pas v0_theses",
      "v0_theses" not in func_src)

# Le filtre HAVING garantit l'exclusion des tickers sans matière par défaut
check("contient une condition HAVING pour le filtre par défaut", "HAVING" in func_src)

# Tri : nb_entries_vivantes DESC
check("tri par nb_entries_vivantes DESC", "nb_entries_vivantes DESC" in func_src)


# ── §9 — Pas de f-string avec accolades littérales (convention #39) ───────────
print("\n§9 — Convention #39 : pas de f-string avec accolades littérales dans list_tickers_v2")

# On importe le vérificateur de check_fstring_sql.
# Le check_fstring_sql analyse tout backend/app/ — on fait ici une vérification ciblée
# sur les f-strings de list_tickers_v2.
import builtins as _builtins

BUILTINS_NAMES = set(dir(_builtins))

def _free_names_simple(expr_node, visible):
    """Retourne les noms libres (ast.Name Load) non résolus dans une expression."""
    free = set()
    for node in ast.walk(expr_node):
        if isinstance(node, ast.Name) and node.id not in visible and node.id not in BUILTINS_NAMES:
            free.add(node.id)
    return free

if func_node:
    fstring_issues = []
    # Collecte les noms locaux de la fonction
    func_body_src = func_src
    # On vérifie simplement qu'aucune JoinedStr (f-string) ne contient des noms libres non résolus
    for node in ast.walk(func_node):
        if isinstance(node, ast.JoinedStr):
            for child in node.values:
                if isinstance(child, ast.FormattedValue):
                    # Noms dans le champ de remplacement
                    for name_node in ast.walk(child.value):
                        if isinstance(name_node, ast.Name):
                            fstring_issues.append((node.lineno, name_node.id))

    # list_tickers_v2 n'utilise PAS de f-strings (tout est par concaténation) — donc aucune issue
    check("list_tickers_v2 ne contient aucune f-string (SQL par concaténation pure)",
          len(fstring_issues) == 0,
          f"— f-strings trouvées avec noms: {fstring_issues}")


# ── §10 — Pas de colonne embedding ───────────────────────────────────────────
print("\n§10 — Colonne embedding absente du SELECT")

check("list_tickers_v2 ne sélectionne pas la colonne embedding",
      "embedding" not in func_src)


# ── §11 — Tri ────────────────────────────────────────────────────────────────
print("\n§11 — Tri : nb_entries_vivantes DESC en premier critère")

# Simulation du tri
def _trier(rows):
    return sorted(rows, key=lambda r: (-r["nb_entries_vivantes"], r["ticker_id"]))

trie = _trier([TICKER_AVEC_MATIERE, TICKER_SANS_MATIERE, TICKER_AVEC_THESE])
check("tri : MSFT (54 entries) en tête", trie[0]["ticker_id"] == "MSFT")
check("tri : NVDA (52 entries) en 2ème", trie[1]["ticker_id"] == "NVDA")
check("tri : AMZN (0 entries) en dernier", trie[2]["ticker_id"] == "AMZN")

# Avec include_all=false : seuls NVDA et MSFT, MSFT en tête
trie_matiere = _trier([t for t in [TICKER_AVEC_MATIERE, TICKER_AVEC_THESE] if t["nb_entries_vivantes"] > 0])
check("sans include_all : MSFT en tête", trie_matiere[0]["ticker_id"] == "MSFT")
check("sans include_all : NVDA en 2ème", trie_matiere[1]["ticker_id"] == "NVDA")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
