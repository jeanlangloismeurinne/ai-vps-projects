"""Vérification du recompute déterministe du curator (Option C) — pur, sans réseau ni DB ni LLM.

Éprouve que le PLANCHER mord en Python : un champ dont l'unique entry citée est sous le plancher est
DÉMOTÉ (bug observé : #54 tier B compté pour un champ B+), le plancher PAR CHAMP (dégradé
`croissance_marche_historique=B`) est respecté, les gaps sont reconciliés (bijection du contrat), et le
ReadinessReport final valide. Le LLM propose `fondations` ; le code dispose.
"""
import sys

from app.agents.v2.common import MVDD_SPEC
from app.agents.v2.curator import (
    FIELD_PLANCHER_OVERRIDES,
    _apply_deterministic_overrides,
    _plancher_for,
    _tier_ge,
    recompute_coverage,
    reconcile_gaps,
)
from app.contracts import ReadinessReport

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


print("\n1. _tier_ge — comparaison de plancher (A meilleur)")
check("A ≥ B+", _tier_ge("A", "B+"))
check("B+ ≥ B+", _tier_ge("B+", "B+"))
check("B NON ≥ B+ (le bug #54)", not _tier_ge("B", "B+"))
check("A- NON ≥ A", not _tier_ge("A-", "A"))
check("None ne satisfait jamais", not _tier_ge(None, "B"))

print("\n2. _plancher_for — plancher par champ (dégradé Q1)")
check("croissance_marche_historique → B (override)",
      _plancher_for("marche", "croissance_marche_historique", "B+") == "B")
check("autre champ → plancher dimension",
      _plancher_for("marche", "structure_5forces", "B+") == "B+")
check("override enregistré", "marche.croissance_marche_historique" in FIELD_PLANCHER_OVERRIDES)

# ── fabrique de couverture depuis MVDD_SPEC ──────────────────────────────────
_SPEC = {s["dimension"]: s for s in MVDD_SPEC}


def dim_cov(dimension, fondations):
    s = _SPEC[dimension]
    return {"dimension": dimension, "tier_plancher": s["tier_plancher"],
            "champs_requis": list(s["champs_requis"]), "fondations": fondations,
            "champs_non_fondables": [], "tier_atteint": None, "ok": True}


def all_founded(dimension, tier, start_id):
    """fondations couvrant TOUS les champs requis, chacun par une entry au tier donné."""
    fonds, entries, i = [], [], start_id
    for champ in _SPEC[dimension]["champs_requis"]:
        fonds.append({"champ": champ, "entry_ids": [i]})
        entries.append({"id": i, "reliability_tier": tier, "source_type": "edgar_official"})
        i += 1
    return dim_cov(dimension, fonds), entries, i


print("\n3. recompute_coverage — le plancher mord")
# marche : structure_5forces fondé par une entry tier B (plancher B+) → doit être DÉMOTÉ ;
#          croissance_marche_historique fondé par une entry tier B (plancher B via override) → OK
entries = [
    {"id": 54, "reliability_tier": "B", "source_type": "agent_synthesis"},   # 5forces (B < B+)
    {"id": 60, "reliability_tier": "B", "source_type": "web_search_reputable"},  # croissance (B ≥ B override)
]
marche = dim_cov("marche", [
    {"champ": "structure_5forces", "entry_ids": [54]},
    {"champ": "croissance_marche_historique", "entry_ids": [60]},
])
cov = {"structuree": {"dimensions": [], "bloc_ok": True},
       "qualitative_marche": {"dimensions": [marche], "bloc_ok": True}}
recompute_coverage(cov, entries)
md = cov["qualitative_marche"]["dimensions"][0]
check("structure_5forces (B) DÉMOTÉ sous plancher B+", "structure_5forces" in md["champs_non_fondables"])
check("croissance (B) FONDÉ via plancher B", "croissance_marche_historique" not in md["champs_non_fondables"])
check("dimension marche ok=False", md["ok"] is False)
check("tier_atteint = meilleur cité (B)", md["tier_atteint"] == "B", f"→ {md['tier_atteint']}")

print("\n4. recompute — entry citée inexistante = non fondé (garde déterministe)")
d2 = dim_cov("risques", [{"champ": "risques_cles", "entry_ids": [9999]}])
cov2 = {"structuree": {"dimensions": [], "bloc_ok": True},
        "qualitative_marche": {"dimensions": [d2], "bloc_ok": True}}
recompute_coverage(cov2, [])  # aucune entry en base
check("champ citant un id fantôme → non fondé", d2["champs_non_fondables"] == ["risques_cles"])

print("\n5. reconcile_gaps — bijection champs_non_fondables ↔ gaps")
report = {"gaps": [
    {"dimension": "marche", "champs_cibles": ["structure_5forces", "croissance_marche_historique"],
     "manque": "x", "queries_suggerees": [], "priorite": "haute", "coverage_actuelle": "B",
     "origine": "curator"}]}
reconcile_gaps(report, cov)  # cov: seul structure_5forces est non fondable
g = report["gaps"]
check("gap raboté aux non-fondables réels",
      len(g) == 1 and g[0]["champs_cibles"] == ["structure_5forces"], f"→ {g}")

print("\n6. reconcile_gaps — synthétise un gap pour un non-fondable orphelin")
report2 = {"gaps": []}
reconcile_gaps(report2, cov)
check("gap synthétisé pour structure_5forces",
      any("structure_5forces" in x["champs_cibles"] for x in report2["gaps"]))

print("\n7. Intégration — ReadinessReport valide après _apply_deterministic_overrides")


def full_report(scenario_entries, coverage, verdict="not_ready"):
    return {"schema_version": "v2.0.0", "verdict": verdict, "coverage": coverage,
            "entries_par_tier": {"tier_A": 0, "tier_B": 0, "tier_C_llm_memory": 0, "total": 0},
            "indicateurs": {"qualite_info": 0.6, "conviction": 0.9, "marge_securite": 0.1},
            "incertitudes_bloquantes": [], "incertitudes_investissables": [],
            "gaps": [], "arret_pareto_recommande": False, "rationale": "test"}


# READY : tous les champs fondés au bon tier (croissance en B via override)
struct_dims, ents = [], []
i = 1
for dim in ("business_model", "financials", "valorisation"):
    dc, es, i = all_founded(dim, "A", i)
    struct_dims.append(dc); ents += es
qual_dims = []
for dim in ("produits", "positionnement", "management_allocation", "risques"):
    dc, es, i = all_founded(dim, "A", i)
    qual_dims.append(dc); ents += es
# marche : structure_5forces en B+ (OK), croissance en B (OK via override)
m = dim_cov("marche", [{"champ": "structure_5forces", "entry_ids": [i]},
                       {"champ": "croissance_marche_historique", "entry_ids": [i + 1]}])
ents += [{"id": i, "reliability_tier": "B+", "source_type": "financial_press"},
         {"id": i + 1, "reliability_tier": "B", "source_type": "web_search_reputable"}]
qual_dims.append(m)
cov_ready = {"structuree": {"dimensions": struct_dims, "bloc_ok": True},
             "qualitative_marche": {"dimensions": qual_dims, "bloc_ok": True}}
rep = full_report(ents, cov_ready)
_apply_deterministic_overrides(rep, ents)
check("verdict recalculé = ready", rep["verdict"] == "ready", f"→ {rep['verdict']}")
rep["context_pack_entry_id"] = 999  # posé par run_readiness quand ready
try:
    ReadinessReport.model_validate(rep)
    check("ReadinessReport valide (ready)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (ready)", False, str(e)[:200])

# THIN : on casse structure_5forces (B < B+) → marche non ok → thin_qualitative
m["fondations"] = [{"champ": "structure_5forces", "entry_ids": [777]},
                   {"champ": "croissance_marche_historique", "entry_ids": [778]}]
ents_thin = [e for e in ents if e["id"] not in (m["fondations"][0]["entry_ids"][0],)]
ents_thin += [{"id": 777, "reliability_tier": "B", "source_type": "agent_synthesis"},
              {"id": 778, "reliability_tier": "B", "source_type": "web_search_reputable"}]
rep2 = full_report(ents_thin, cov_ready)
_apply_deterministic_overrides(rep2, ents_thin)
check("verdict recalculé = thin_qualitative (5forces B démoté)",
      rep2["verdict"] == "thin_qualitative", f"→ {rep2['verdict']}")
try:
    ReadinessReport.model_validate(rep2)
    check("ReadinessReport valide (thin, gaps reconciliés)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (thin, gaps reconciliés)", False, str(e)[:200])

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
