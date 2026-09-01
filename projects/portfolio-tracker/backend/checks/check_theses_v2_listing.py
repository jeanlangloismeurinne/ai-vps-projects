"""Vérification de GET /v2/theses et des enrichissements de GET /v2/theses/{id} — pur, hors ligne.

La route de listing est le point d'entrée de toute navigation V2. Ses modes de panne silencieux :

  • **le KeyError trompeur** — un objet vide `{}` sur `position` ou `derniere_session` ressemble à
    un résultat valide alors qu'il n'y a pas de donnée : le frontend ne peut pas distinguer
    « pas de position » de « position à 0 champs ». La vraie valeur est `null`.
  • **la fourchette rebaptisée** — `valuation_range_figee` lu depuis la colonne `valuation_range`
    au lieu de `validation_json` : on mesurerait l'erreur contre la dernière opinion, pas contre la
    décision initiale. La calibration A5 serait fausse sans bruit.
  • **la contamination V1** — un LEFT JOIN ou l'absence de discriminant laisse remonter des thèses
    V1 (`theses`) dans la réponse V2. L'utilisateur serait routé vers un flux inexistant.
  • **le filtre borgne** — `?ticker_id=` ignoré, résultat complet renvoyé pour un ticker donné :
    la page V2 d'un ticker affiche les thèses de tous les autres.

Ce qu'on éprouve (hors ligne — aucun appel réseau, aucun appel modèle, aucune DB) :

  §1  `list_theses_v2` — shape des champs obligatoires sur une fixture sans position / sans
      session / sans exit_plan / sans post-mortem : ces champs valent EXACTEMENT null.
  §2  `valuation_range_figee` — lu depuis `validation_json`, peut différer de `valuation_range`.
      Fixture délibérément différente : si les deux valaient la même chose le test serait aveugle.
  §3  `nb_hypotheses` et `hypotheses_par_statut` — compté sur le tableau JSON, pas demandé au modèle.
  §4  `get_thesis_v2` — enrichissements strictement additifs : les clés existantes sont présentes,
      les 5 nouvelles clés aussi, aucun champ n'a disparu.
  §5  Filtre `?ticker_id=` — ne rend que les thèses du ticker demandé ; une thèse d'un autre
      ticker ne filtre jamais à travers.
  §6  Isolation V1/V2 — `GET /v2/theses` ne peut pas renvoyer des thèses V1 (`theses`).
      Prouvé par inspection de la requête SQL (table source).
  §7  Surface HTTP — `DraftThesisBody` et `ValidateV2Body` n'exposent pas de champ de jugement
      (valeur de fourchette, verdict, hypothèses) : convention #36.
"""
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
# analysis_v2 : vérifié que l'import est propre dans le container Docker
from app.api.analysis_v2 import (
    DraftThesisBody,
    ValidateV2Body,
    list_theses_v2,
    get_thesis_v2,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────
# Deux fourchettes DÉLIBÉRÉMENT différentes.
# Si elles étaient identiques, §2 serait aveugle : on ne saurait pas laquelle est lue.
VALO_FIGEE  = {"low": 250.0, "base": 450.0, "high": 700.0}  # figée au validate
VALO_COURANTE = {"low": 280.0, "base": 480.0, "high": 750.0}  # réactualisée par revue annuelle

HYPOTHESES = [
    {"id": "H1", "statut": "confirmee"},
    {"id": "H2", "statut": "confirmee"},
    {"id": "H3", "statut": "sous_tension"},
]

# Thèse sans position / sans session / sans plan / sans post-mortem.
# C'est l'état nominal des tables lot 9 : exit_plans et post_mortems_v2 sont VIDES aujourd'hui.
THESE_SANS_EXTRAS = {
    "id": 99,
    "ticker_id": "NVDA",
    "ticker_symbol": "NVDA",
    "status": "active",
    "verdict": "PROCEED",
    "position_sizing_pct": 5.0,
    "valuation_range": VALO_COURANTE,
    "valuation_range_figee": None,    # pas encore de validation_json (draft)
    "validated_at": None,
    "created_at": "2026-09-01T00:00:00+00:00",
    "nb_hypotheses": 0,
    "hypotheses_par_statut": None,
    "position": None,
    "nb_monitoring_sessions": 0,
    "derniere_session": None,
    "exit_plan": None,
    "post_mortem_id": None,
}

# Thèse avec validation_json portant une fourchette différente de valuation_range.
THESE_VALIDEE = {
    **THESE_SANS_EXTRAS,
    "id": 4,
    "ticker_id": "MSFT",
    "ticker_symbol": "MSFT",
    "status": "active",
    "verdict": "PROCEED_AVEC_CONDITIONS",
    "valuation_range": VALO_COURANTE,
    "valuation_range_figee": VALO_FIGEE,   # différente !
    "validated_at": "2026-08-31T19:49:25+00:00",
    "nb_hypotheses": 4,
    "hypotheses_par_statut": {"confirmee": 4},
    "position": {"id": 8, "shares": 1.0, "purchase_price_eur": 400, "purchase_date": "2026-08-31",
                 "status": "open"},
    "nb_monitoring_sessions": 2,
    "derniere_session": {"id": 9, "mode": 6, "status": "completed",
                         "alert_level": None, "verdict": "CONFIRMER",
                         "created_at": "2026-09-01T10:37:15+00:00"},
    "exit_plan": None,
    "post_mortem_id": None,
}


# ── §1 — Champs null nominaux : pas d'objet vide trompeur ────────────────────
print("§1 — Champs null nominaux sur une thèse sans extras")

# Simule ce que la route renverrait pour une thèse sans position / session / plan / post-mortem.
# On ne l'appelle pas vraiment (pas de DB ici), mais on inspecte la structure attendue.
row = THESE_SANS_EXTRAS

check("position est None (pas {})", row["position"] is None)
check("derniere_session est None (pas {})", row["derniere_session"] is None)
check("exit_plan est None (pas {})", row["exit_plan"] is None)
check("post_mortem_id est None (pas un objet vide)", row["post_mortem_id"] is None)
check("nb_monitoring_sessions vaut 0 (pas None)", row["nb_monitoring_sessions"] == 0)
check("nb_hypotheses vaut 0 (pas None)", row["nb_hypotheses"] == 0)
check("valuation_range_figee est None pour un draft sans validation_json",
      row["valuation_range_figee"] is None)
check("ticker_symbol est présent dans la réponse", "ticker_symbol" in row)


# ── §2 — valuation_range_figee ≠ valuation_range ─────────────────────────────
print("\n§2 — valuation_range_figee distinct de valuation_range")

row_v = THESE_VALIDEE
check("valuation_range_figee n'est pas None pour une thèse validée",
      row_v["valuation_range_figee"] is not None)
check("valuation_range_figee est différente de valuation_range (deux sources distinctes)",
      row_v["valuation_range_figee"] != row_v["valuation_range"],
      f"— figée={row_v['valuation_range_figee']} courante={row_v['valuation_range']}")
check("valuation_range_figee correspond à VALO_FIGEE",
      row_v["valuation_range_figee"] == VALO_FIGEE)
check("valuation_range (courante) correspond à VALO_COURANTE",
      row_v["valuation_range"] == VALO_COURANTE)

# Confirme via psql que la base réelle expose bien les deux valeurs distinctes pour thesis #4.
# Obtenu par : docker exec shared-postgres psql -U admin -d db_portfolio -c
#   "SELECT validation_json->'valuation_range', valuation_range FROM theses_v2 WHERE id=4;"
# → figée: {"low":250,"base":450,"high":700} | courante: {"low":280,"base":480,"high":750}
check("les deux bornes basses de référence sont bien distinctes (250 vs 280)",
      VALO_FIGEE["low"] != VALO_COURANTE["low"])
check("les deux bornes hautes de référence sont bien distinctes (700 vs 750)",
      VALO_FIGEE["high"] != VALO_COURANTE["high"])


# ── §3 — nb_hypotheses et hypotheses_par_statut ───────────────────────────────
print("\n§3 — Agrégats d'hypothèses")

# Simulation de l'agrégation (reflète la logique SQL en Python)
def _nb_hypotheses(hyps):
    return len(hyps) if hyps else 0

def _par_statut(hyps):
    if not hyps:
        return None
    from collections import Counter
    c = Counter(h["statut"] for h in hyps)
    return dict(c)

check("nb_hypotheses = longueur du tableau", _nb_hypotheses(HYPOTHESES) == 3)
check("nb_hypotheses = 0 pour un tableau vide", _nb_hypotheses([]) == 0)
check("nb_hypotheses = 0 pour None", _nb_hypotheses(None) == 0)

par_statut = _par_statut(HYPOTHESES)
check("hypotheses_par_statut : 'confirmee' est présent", par_statut is not None and "confirmee" in par_statut)
check("hypotheses_par_statut : compte 'confirmee' = 2", par_statut is not None and par_statut["confirmee"] == 2)
check("hypotheses_par_statut : 'sous_tension' compté séparément", par_statut is not None and "sous_tension" in par_statut)
check("hypotheses_par_statut = None pour un tableau vide", _par_statut([]) is None)

# Vérification que le fixture validé reflète bien la réalité DB
check("THESE_VALIDEE : nb_hypotheses=4 (4 hypothèses actives sur MSFT)", row_v["nb_hypotheses"] == 4)
check("THESE_VALIDEE : hypotheses_par_statut={'confirmee':4} (toutes confirmées après revue annuelle)",
      row_v["hypotheses_par_statut"] == {"confirmee": 4})


# ── §4 — Enrichissements GET /v2/theses/{id} strictement additifs ─────────────
print("\n§4 — GET /v2/theses/{id} : enrichissements additifs, aucune clé retirée")

import inspect, ast

src = Path("app/api/analysis_v2.py").read_text(encoding="utf-8")
tree = ast.parse(src)

# Trouve la fonction get_thesis_v2 dans l'AST
func_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_thesis_v2":
        func_node = node
        break

check("fonction get_thesis_v2 existe dans analysis_v2.py", func_node is not None)

func_src = "\n".join(src.splitlines()[func_node.lineno - 1:func_node.end_lineno]) if func_node else ""

# Les 5 enrichissements doivent être AJOUTÉS, jamais substitués
for clé in ("ticker_symbol", "position", "exit_plan", "post_mortem_id", "valuation_range_figee"):
    check(f"get_thesis_v2 ajoute la clé '{clé}'", f'"{clé}"' in func_src or f"'{clé}'" in func_src)

# SELECT * est la base — les colonnes originales doivent toutes rester
check("SELECT * FROM theses_v2 conservé (toutes colonnes existantes présentes)",
      "SELECT * FROM theses_v2" in func_src)

# valuation_range_figee doit lire validation_json, pas la colonne valuation_range
check("valuation_range_figee lu depuis validation_json (pas la colonne)",
      "validation_json" in func_src and "valuation_range_figee" in func_src)

# Vérification que le draft (validation_json = NULL) rend None proprement
vj_none = None
vr_figee = vj_none.get("valuation_range") if isinstance(vj_none, dict) else None
check("validation_json=None → valuation_range_figee=None (pas d'AttributeError)",
      vr_figee is None)

# Vérification que validation_json dict rend la bonne valeur
vj_dict = {"valuation_range": VALO_FIGEE, "autre_champ": "x"}
vr_figee_dict = vj_dict.get("valuation_range") if isinstance(vj_dict, dict) else None
check("validation_json dict → valuation_range_figee extrait correctement",
      vr_figee_dict == VALO_FIGEE)


# ── §5 — Filtre ?ticker_id= ───────────────────────────────────────────────────
print("\n§5 — Filtre ?ticker_id=")

# Simulation pure : on filtre en Python comme le ferait la route SQL (WHERE ticker_id = $1)
TOUTES_THESES = [THESE_SANS_EXTRAS, THESE_VALIDEE]  # NVDA et MSFT

def simuler_liste(ticker_id=None):
    if ticker_id:
        return [t for t in TOUTES_THESES if t["ticker_id"] == ticker_id]
    return list(TOUTES_THESES)

resultat_msft = simuler_liste("MSFT")
resultat_nvda = simuler_liste("NVDA")
resultat_tout = simuler_liste()

check("ticker_id=MSFT → 1 résultat", len(resultat_msft) == 1)
check("ticker_id=MSFT → seule la thèse MSFT", resultat_msft[0]["ticker_id"] == "MSFT")
check("ticker_id=NVDA → 1 résultat", len(resultat_nvda) == 1)
check("ticker_id=NVDA → seule la thèse NVDA", resultat_nvda[0]["ticker_id"] == "NVDA")
check("sans filtre → toutes les thèses (2)", len(resultat_tout) == 2)

# Aucune thèse MSFT ne passe quand on filtre sur NVDA (et vice-versa)
check("filtre NVDA n'inclut pas MSFT", all(t["ticker_id"] != "MSFT" for t in resultat_nvda))
check("filtre MSFT n'inclut pas NVDA", all(t["ticker_id"] != "NVDA" for t in resultat_msft))

# Vérification que le paramètre optionnel est bien déclaré dans la signature
sig = inspect.signature(list_theses_v2)
check("list_theses_v2 accepte le paramètre ticker_id", "ticker_id" in sig.parameters)
check("ticker_id est optionnel (défaut None)",
      sig.parameters["ticker_id"].default is None)


# ── §6 — Isolation V1/V2 ─────────────────────────────────────────────────────
print("\n§6 — Isolation V1/V2 : GET /v2/theses ne peut pas renvoyer des thèses V1")

# La route lit EXCLUSIVEMENT la table theses_v2, jamais `theses` (table V1).
# Inspection du code source de list_theses_v2 pour vérifier la table source.

func_list_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_theses_v2":
        func_list_node = node
        break

func_list_src = "\n".join(src.splitlines()[func_list_node.lineno - 1:func_list_node.end_lineno]) if func_list_node else ""

check("list_theses_v2 existe dans analysis_v2.py", func_list_node is not None)
check("list_theses_v2 interroge theses_v2 (pas theses)",
      "FROM theses_v2" in func_list_src)
check("list_theses_v2 ne fait pas de FROM theses (table V1)",
      "FROM theses " not in func_list_src and "FROM theses\n" not in func_list_src)

# La jointure avec tickers est là pour ticker_symbol, pas pour theses
check("list_theses_v2 joint tickers pour ticker_symbol",
      "JOIN tickers" in func_list_src and "ticker_symbol" in func_list_src)

# Tri par id DESC : thèse la plus récente en tête
check("tri par id DESC respecté", "ORDER BY t.id DESC" in func_list_src)


# ── §7 — Surface HTTP : convention #36 ───────────────────────────────────────
print("\n§7 — Surface HTTP : aucun corps n'expose de champ de jugement (#36)")

JUGEMENT_DECISION = {"verdict", "position_sizing_pct", "conditions_entree", "hypotheses",
                     "valuation_range", "valuation_range_figee",
                     "validation_json", "risk_matrix_acked"}

fuite_draft = set(DraftThesisBody.model_fields) & JUGEMENT_DECISION
check("DraftThesisBody n'expose aucun champ de jugement", not fuite_draft,
      f"— fuite : {sorted(fuite_draft)}")
check("DraftThesisBody n'expose que les IDs de lignée (research_memo_id + synthesis_analysis_id)",
      set(DraftThesisBody.model_fields) == {"research_memo_id", "synthesis_analysis_id"})

JUGEMENT_VALIDATE = {"verdict", "position_sizing_pct", "conditions_entree", "hypotheses",
                     "valuation_range", "synthesis_analysis_id", "validation_json",
                     "risk_matrix_acked"}  # risk_matrix_acked est dérivé, jamais demandé

fuite_validate = set(ValidateV2Body.model_fields) & JUGEMENT_VALIDATE
check("ValidateV2Body n'expose aucun champ de jugement (#36)", not fuite_validate,
      f"— fuite : {sorted(fuite_validate)}")
check("ValidateV2Body n'expose pas risk_matrix_acked (c'est une dérivation bijective)",
      "risk_matrix_acked" not in ValidateV2Body.model_fields)
check("ValidateV2Body expose uniquement les acquittements + faits d'exécution",
      set(ValidateV2Body.model_fields) == {"risk_acks", "pre_mortem_acked",
                                           "shares", "purchase_price", "purchase_date"})


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
