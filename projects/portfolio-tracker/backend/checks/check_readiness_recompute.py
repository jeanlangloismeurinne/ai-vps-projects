"""Vérification du recompute déterministe du curator — pur, sans réseau ni DB ni LLM.

Depuis la 029, la couverture est DÉRIVÉE DE LA BASE, plus des citations du LLM : pour chaque champ
requis, le backend cherche dans l'index `covers` une entry qui PORTE ce champ (chemin complet
`dimension.champ`) à un tier ≥ plancher. Ce qu'on éprouve ici :

  • le plancher mord (une entry sous plancher ne fonde pas — bug #54 : tier B compté pour un B+) ;
  • le plancher PAR CHAMP (dégradé `croissance_marche_historique=B`) est respecté ;
  • l'index DÉCOUVRE une entry que le LLM n'a pas citée (le faux creux qui faisait osciller le
    verdict à corpus figé — rapports NVDA #11/#13/#14) ;
  • le chemin complet discrimine `business_model.description` de `produits.description` ;
  • une entry non taguée ne fonde plus rien (fin du fallback tier-only de la 028) ;
  • le LLM ne peut plus DESSERRER champs_requis / tier_plancher, seulement les resserrer ;
  • les gaps restent en bijection avec les non-fondables, et le ReadinessReport final valide.
"""
import sys

from app.agents.v2.common import MVDD_FIELD_PATHS, MVDD_SPEC, format_entries_for_prompt
from app.agents.v2.curator import (
    DECLARED_NONBLOCKING_GAPS,
    FIELD_PLANCHER_OVERRIDES,
    _apply_deterministic_overrides,
    _covers_index,
    _declare_nonblocking_gaps,
    _exigences,
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


_SPEC = {s["dimension"]: s for s in MVDD_SPEC}


def entry(eid, tier, covers, source_type="edgar_official"):
    return {"id": eid, "reliability_tier": tier, "source_type": source_type, "covers": covers}


def dim_cov(dimension, fondations=None):
    """Squelette de dimension tel que le LLM le rend (fondations ignorées : le backend les réécrit)."""
    s = _SPEC[dimension]
    return {"dimension": dimension, "tier_plancher": s["tier_plancher"],
            "champs_requis": list(s["champs_requis"]), "fondations": fondations or [],
            "champs_non_fondables": [], "tier_atteint": None, "ok": True}


def run(dims_qual, entries, dims_struct=None):
    cov = {"structuree": {"dimensions": dims_struct or [], "bloc_ok": True},
           "qualitative_marche": {"dimensions": dims_qual, "bloc_ok": True}}
    recompute_coverage(cov, entries)
    return cov


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

print("\n3. MVDD_FIELD_PATHS — vocabulaire fermé de l'index")
check("chemins complets uniquement", all("." in p for p in MVDD_FIELD_PATHS))
check("business_model.description présent", "business_model.description" in MVDD_FIELD_PATHS)
check("produits.description présent (homonyme distinct)", "produits.description" in MVDD_FIELD_PATHS)
check("nom nu absent", "description" not in MVDD_FIELD_PATHS)
check("un chemin par champ requis",
      len(MVDD_FIELD_PATHS) == sum(len(s["champs_requis"]) for s in MVDD_SPEC))

print("\n4. _covers_index — construction depuis la base")
idx = _covers_index([
    entry(1, "A", ["risques.risques_cles", "marche.structure_5forces"]),
    entry(2, "B+", ["risques.risques_cles"]),
    entry(3, "A", None),                       # non taguée : ne fonde rien
    entry(4, "A", "risques.risques_cles"),     # tolérance pré-029 (chaîne nue)
    entry(5, None, ["risques.risques_cles"]),  # sans tier : ignorée
])
check("multi-champ : une entry alimente 2 clés",
      idx["marche.structure_5forces"] == [(1, "A")])
check("agrégation par champ, triée par id",
      idx["risques.risques_cles"] == [(1, "A"), (2, "B+"), (4, "A")], f"→ {idx.get('risques.risques_cles')}")
check("entry non taguée absente de l'index",
      all(3 not in [i for i, _ in v] for v in idx.values()))
check("entry sans tier écartée", all(5 not in [i for i, _ in v] for v in idx.values()))

print("\n5. recompute_coverage — le plancher mord")
# structure_5forces fondé par une entry tier B (plancher B+) → DÉMOTÉ ;
# croissance_marche_historique = lacune déclarée → ni fondée, ni comptée comme manque.
cov = run([dim_cov("marche")], [entry(54, "B", ["marche.structure_5forces"], "agent_synthesis")])
md = cov["qualitative_marche"]["dimensions"][0]
check("structure_5forces (B) DÉMOTÉ sous plancher B+", md["champs_non_fondables"] == ["structure_5forces"])
check("dimension marche ok=False", md["ok"] is False)
check("tier_atteint=None (rien ne fonde vraiment)", md["tier_atteint"] is None, f"→ {md['tier_atteint']}")
check("fondations vides quand rien ne tient le plancher", md["fondations"] == [])

print("\n6. recompute_coverage — l'index DÉCOUVRE, il ne filtre plus des citations")
# LE cas qui faisait osciller le verdict : le LLM ne cite RIEN (fondations=[]), mais une entry
# taguée existe en base → le champ est fondé quand même.
cov = run([dim_cov("risques", fondations=[])], [entry(28, "A", ["risques.risques_cles"])])
rd = cov["qualitative_marche"]["dimensions"][0]
check("champ fondé SANS citation du LLM (fin du faux creux)", rd["ok"] is True, f"→ {rd}")
check("fondations RÉÉCRITES depuis l'index",
      rd["fondations"] == [{"champ": "risques_cles", "entry_ids": [28]}], f"→ {rd['fondations']}")
check("tier_atteint dérivé des entries retenues", rd["tier_atteint"] == "A")

# … et symétriquement : une citation LLM sans entry taguée derrière ne fonde plus rien.
cov = run([dim_cov("risques", fondations=[{"champ": "risques_cles", "entry_ids": [28]}])],
          [entry(28, "A", None)])
check("citation LLM sur entry NON taguée → non fondé (fin du fallback tier-only)",
      cov["qualitative_marche"]["dimensions"][0]["champs_non_fondables"] == ["risques_cles"])

print("\n7. Chemin complet — `description` ne traverse pas les dimensions")
cov = run([dim_cov("produits")],
          [entry(20, "A", ["produits.description"]), entry(53, "A-", ["produits.unit_economics"])],
          dims_struct=[dim_cov("business_model")])
bm = cov["structuree"]["dimensions"][0]
pr = cov["qualitative_marche"]["dimensions"][0]
check("produits.description fondé", "description" not in pr["champs_non_fondables"])
check("produits ok (description + unit_economics)", pr["ok"] is True, f"→ {pr['champs_non_fondables']}")
check("business_model.description NON fondé par le tag produits",
      "description" in bm["champs_non_fondables"], f"→ {bm['champs_non_fondables']}")

print("\n8. _exigences — le LLM peut RESSERRER, jamais DESSERRER")
r, p = _exigences("business_model", {"champs_requis": ["description"], "tier_plancher": "C"})
check("champ requis retiré par le LLM → réintroduit",
      set(r) >= set(_SPEC["business_model"]["champs_requis"]), f"→ {r}")
check("plancher assoupli (C) → ramené au socle B+", p == "B+", f"→ {p}")
r2, p2 = _exigences("business_model",
                    {"champs_requis": ["description", "part_recurrente_cloud"], "tier_plancher": "A"})
check("champ ajouté par le LLM → conservé", "part_recurrente_cloud" in r2)
check("socle en tête, ajouts ensuite (ordre stable)",
      r2[:3] == _SPEC["business_model"]["champs_requis"], f"→ {r2}")
check("plancher resserré (A) → conservé", p2 == "A", f"→ {p2}")
r3, p3 = _exigences("risques", {})
check("dimension sans proposition → socle MVDD", r3 == _SPEC["risques"]["champs_requis"] and p3 == "B")

print("\n9. reconcile_gaps — bijection champs_non_fondables ↔ gaps")
cov = run([dim_cov("marche")], [entry(54, "B", ["marche.structure_5forces"], "agent_synthesis")])
report = {"gaps": [
    {"dimension": "marche", "champs_cibles": ["structure_5forces", "croissance_marche_historique"],
     "manque": "x", "queries_suggerees": [], "priorite": "haute", "coverage_actuelle": "B",
     "origine": "curator"}]}
reconcile_gaps(report, cov)
g = report["gaps"]
check("gap raboté aux non-fondables réels (croissance = lacune déclarée, retirée)",
      len(g) == 1 and g[0]["champs_cibles"] == ["structure_5forces"], f"→ {g}")
report2 = {"gaps": []}
reconcile_gaps(report2, cov)
check("gap synthétisé pour un non-fondable orphelin",
      any("structure_5forces" in x["champs_cibles"] for x in report2["gaps"]))

print("\n10. Lacune déclarée non-bloquante — croissance_marche_historique")
check("croissance enregistrée comme lacune déclarée",
      "marche.croissance_marche_historique" in DECLARED_NONBLOCKING_GAPS)
cov9 = run([dim_cov("marche")], [entry(56, "A-", ["marche.structure_5forces"], "agent_synthesis")])
md9 = cov9["qualitative_marche"]["dimensions"][0]
check("croissance ABSENTE des non-fondables (skippée)",
      "croissance_marche_historique" not in md9["champs_non_fondables"])
check("marche ok=True malgré croissance introuvable", md9["ok"] is True, f"→ {md9}")
rep9 = {"incertitudes_investissables": []}
_declare_nonblocking_gaps(rep9, cov9)
check("lacune portée en incertitude investissable VISIBLE",
      any("croissance" in u["question"].lower() for u in rep9["incertitudes_investissables"]))
_declare_nonblocking_gaps(rep9, cov9)
check("dédup (pas de doublon d'incertitude)", len(rep9["incertitudes_investissables"]) == 1)

print("\n11. format_entries_for_prompt — l'index est visible au modèle")
listing = format_entries_for_prompt([
    {"id": 19, "title": "Data Center", "content": "x", "reliability_tier": "A",
     "source_type": "company_ir_official", "covers": ["business_model.drivers_revenus"], "version": 1},
    {"id": 25, "title": "Buybacks", "content": "y", "reliability_tier": "A",
     "source_type": "edgar_official", "covers": None, "version": 1},
])
check("entry taguée annonce ce qu'elle couvre", "couvre business_model.drivers_revenus" in listing)
check("entry non taguée n'annonce rien", "couvre" not in listing.split("\n")[1])

print("\n12. Intégration — ReadinessReport valide, verdict = fonction du corpus")


def full_report(coverage, verdict="not_ready"):
    return {"schema_version": "v2.0.0", "verdict": verdict, "coverage": coverage,
            "entries_par_tier": {"tier_A": 0, "tier_B": 0, "tier_C_llm_memory": 0, "total": 0},
            "indicateurs": {"qualite_info": 0.6, "conviction": 0.9, "marge_securite": 0.1},
            "incertitudes_bloquantes": [], "incertitudes_investissables": [],
            "gaps": [], "arret_pareto_recommande": False, "rationale": "test"}


def corpus_complet():
    """Une entry tier A par champ requis (hors lacune déclarée) — le cas `ready`."""
    ents, eid = [], 100
    for s in MVDD_SPEC:
        for champ in s["champs_requis"]:
            path = f"{s['dimension']}.{champ}"
            if path in DECLARED_NONBLOCKING_GAPS:
                continue
            ents.append(entry(eid, "A", [path]))
            eid += 1
    return ents


ents = corpus_complet()
cov_ready = {"structuree": {"dimensions": [dim_cov(d) for d in
                                           ("business_model", "financials", "valorisation")], "bloc_ok": True},
             "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                   ("produits", "positionnement", "marche",
                                                    "management_allocation", "risques")], "bloc_ok": True}}
rep = full_report(cov_ready)
_apply_deterministic_overrides(rep, ents)
check("verdict recalculé = ready", rep["verdict"] == "ready", f"→ {rep['verdict']}")
rep["context_pack_entry_id"] = 999  # posé par run_readiness quand ready
try:
    ReadinessReport.model_validate(rep)
    check("ReadinessReport valide (ready)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (ready)", False, str(e)[:200])

# DÉTERMINISME : deux passes sur le MÊME corpus, avec des `fondations` LLM différentes (ce qui
# faisait basculer le verdict avant la 029) → verdict et couverture strictement identiques.
cov_a = {"structuree": {"dimensions": [dim_cov(d) for d in
                                       ("business_model", "financials", "valorisation")], "bloc_ok": True},
         "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                               ("produits", "positionnement", "marche",
                                                "management_allocation", "risques")], "bloc_ok": True}}
cov_b = {"structuree": {"dimensions": [dim_cov(d, [{"champ": "description", "entry_ids": [1]}]) for d in
                                       ("business_model", "financials", "valorisation")], "bloc_ok": True},
         "qualitative_marche": {"dimensions": [dim_cov(d, []) for d in
                                               ("produits", "positionnement", "marche",
                                                "management_allocation", "risques")], "bloc_ok": True}}
ra, rb = full_report(cov_a), full_report(cov_b, verdict="too_hard")
_apply_deterministic_overrides(ra, ents)
_apply_deterministic_overrides(rb, ents)
check("verdict indépendant des citations LLM", ra["verdict"] == "ready")
check("couverture identique à corpus figé", ra["coverage"] == rb["coverage"])

# THIN : on retire l'entry qui fonde structure_5forces → bloc qualitatif tombe, structuré intact
ents_thin = [e for e in ents if e["covers"] != ["marche.structure_5forces"]]
cov_thin = {"structuree": {"dimensions": [dim_cov(d) for d in
                                          ("business_model", "financials", "valorisation")], "bloc_ok": True},
            "qualitative_marche": {"dimensions": [dim_cov(d) for d in
                                                  ("produits", "positionnement", "marche",
                                                   "management_allocation", "risques")], "bloc_ok": True}}
rep2 = full_report(cov_thin)
_apply_deterministic_overrides(rep2, ents_thin)
check("verdict recalculé = thin_qualitative (5forces retiré du corpus)",
      rep2["verdict"] == "thin_qualitative", f"→ {rep2['verdict']}")
try:
    ReadinessReport.model_validate(rep2)
    check("ReadinessReport valide (thin, gaps reconciliés)", True)
except Exception as e:  # noqa: BLE001
    check("ReadinessReport valide (thin, gaps reconciliés)", False, str(e)[:200])

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
