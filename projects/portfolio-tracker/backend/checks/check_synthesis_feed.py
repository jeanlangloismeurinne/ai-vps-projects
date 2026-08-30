"""Vérification de l'alimentateur de SYNTHÈSE grounded — transformations PURES, sans réseau ni DB ni LLM.

Couvre les trois garde-fous déterministes du feed (tout ce que le LLM ne décide PAS) :
  • `derive_synthesis_reliability` : la règle « un cran sous la plus faible entry citée » (validée
    2026-08-26), y compris les 4 cas de la décision (tableau AskUserQuestion) ;
  • `validate_grounding` : une citation hors du corpus citable, ou une assertion sans citation, est
    une VIOLATION (le grounding est vérifié, pas déclaré — #24/#28) ;
  • `build_content_structured` + le contrat `GroundedSynthesis` (union des ids, min 1 citation/claim).
"""
import sys

from app.contracts import GroundedSynthesis, SynthesisClaim
from app.knowledge.synthesis_feed import (
    CITABLE_TIERS,
    SYNTHESIS_TARGETS,
    _synthesis_task_message,
    build_content_structured,
    derive_synthesis_reliability,
    validate_grounding,
)

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


print("\n1. derive_synthesis_reliability — un cran sous la plus faible entry citée")
# cas exacts de la décision (préviews) : la plus faible cité pilote le tier
s, t, _ = derive_synthesis_reliability(["A", "A"])
check("[A, A] → A- 0.85 (≥ B+, fonde)", (t, s) == ("A-", 0.85), f"→ {t} {s}")
s, t, _ = derive_synthesis_reliability(["A", "A-"])
check("[A, A-] → B+ 0.75 (== B+, fonde)", (t, s) == ("B+", 0.75), f"→ {t} {s}")
s, t, _ = derive_synthesis_reliability(["A", "B+"])
check("[A, B+] → B 0.70 (< B+, ne fonde pas)", (t, s) == ("B", 0.70), f"→ {t} {s}")
s, t, _ = derive_synthesis_reliability(["B+", "B+"])
check("[B+, B+] → B 0.70 (< B+, ne fonde pas)", (t, s) == ("B", 0.70), f"→ {t} {s}")
# ordre indifférent : c'est la plus faible qui compte, pas la position
s1, t1, _ = derive_synthesis_reliability(["B+", "A", "A-"])
s2, t2, _ = derive_synthesis_reliability(["A-", "B+", "A"])
check("ordre indifférent (min pilote)", (t1, s1) == (t2, s2) == ("B", 0.70), f"→ {t1} {t2}")
_, _, note = derive_synthesis_reliability(["A", "A-"])
check("la note explique la dérivation", "un cran sous" in note and "revue humaine" in note, f"→ {note}")
check("note tolère les doublons de tier", "A-" in derive_synthesis_reliability(["A", "A", "A"])[2])
try:
    derive_synthesis_reliability([])
    check("aucune citation → lève", False, "pas d'exception")
except ValueError:
    check("aucune citation → lève", True)

print("\n2. Ne jamais surévaluer — la synthèse est toujours SOUS sa meilleure source")
for weakest, expected in [("A", "A-"), ("A-", "B+"), ("B+", "B")]:
    _, t, _ = derive_synthesis_reliability(["A", weakest])  # A comme meilleure, weakest comme plancher
    check(f"plus faible {weakest} → {expected} (jamais A)", t == expected, f"→ {t}")

print("\n3. validate_grounding — citations vérifiées contre le corpus RÉELLEMENT chargé")
citable = {10, 11, 12}
good = [{"text": "x", "cited_entry_ids": [10, 11]}, {"text": "y", "cited_entry_ids": [12]}]
check("grounding valide → aucune violation", validate_grounding(good, citable) == [])
bad = [{"text": "x", "cited_entry_ids": [10, 999]}]
errs = validate_grounding(bad, citable)
check("citation hors corpus → violation", len(errs) == 1 and "999" in errs[0], f"→ {errs}")
empty = [{"text": "x", "cited_entry_ids": []}]
check("assertion sans citation → violation", validate_grounding(empty, citable) != [])
mixed = [{"text": "x", "cited_entry_ids": [10]}, {"text": "y", "cited_entry_ids": [7, 8]}]
check("2 ids hors corpus → 2 violations", len(validate_grounding(mixed, citable)) == 2)

print("\n4. Contrat GroundedSynthesis — min 1 citation/claim, union des ids")
synth = GroundedSynthesis(
    title="Éco. unitaire NVDA",
    synthesis_markdown="Marge brute élevée…",
    claims=[
        SynthesisClaim(text="marge brute ~73%", cited_entry_ids=[32, 33]),
        SynthesisClaim(text="pricing power fort", cited_entry_ids=[33, 34]),
    ],
)
check("cited_entry_ids() = union triée dédupliquée", synth.cited_entry_ids() == [32, 33, 34],
      f"→ {synth.cited_entry_ids()}")
try:
    SynthesisClaim(text="non sourcé", cited_entry_ids=[])
    check("claim sans citation rejeté par le contrat", False, "accepté !")
except Exception:
    check("claim sans citation rejeté par le contrat", True)
try:
    GroundedSynthesis(title="t", synthesis_markdown="m", claims=[])
    check("synthèse sans aucun claim rejetée", False, "acceptée !")
except Exception:
    check("synthèse sans aucun claim rejetée", True)

print("\n5. build_content_structured — traçabilité du grounding")
target = SYNTHESIS_TARGETS["produits.unit_economics"]
tiers_by_id = {32: "A", 33: "A", 34: "B+"}
cs = build_content_structured(target, synth, [32, 33, 34], tiers_by_id)
check("field_path porté", cs["field_path"] == "produits.unit_economics")
check("dimension portée", cs["dimension"] == "produits")
check("cited_entry_ids portés", cs["cited_entry_ids"] == [32, 33, 34])
check("tiers d'origine tracés", cs["derived_from_tiers"] == {"32": "A", "33": "A", "34": "B+"})
check("claims sérialisés", len(cs["claims"]) == 2 and cs["claims"][0]["cited_entry_ids"] == [32, 33])
check("review_status pending", cs["review_status"] == "pending")

print("\n6. Registre des cibles — les 2 champs bloquants sont couverts")
check("produits.unit_economics enregistré", "produits.unit_economics" in SYNTHESIS_TARGETS)
check("marche.structure_5forces enregistré", "marche.structure_5forces" in SYNTHESIS_TARGETS)
check("CITABLE_TIERS = A/A-/B+ (≥ plancher B+)", set(CITABLE_TIERS) == {"A", "A-", "B+"})
for fp, tgt in SYNTHESIS_TARGETS.items():
    check(f"{fp} : entry_type=analysis, min_citations≥2", tgt.entry_type == "analysis" and tgt.min_citations >= 2)
    check(f"{fp} : field_path cohérent avec la clé", tgt.field_path == fp)

print("\n7. Descripteurs AGNOSTIQUES de l'emetteur (regression MSFT 2026-08-30)")
# Le trou : les cibles se disaient generiques mais leurs query/guidance etaient redigees pour
# NVIDIA. Sur un autre emetteur, la requete semantique cherchait le mauvais vocabulaire et la
# consigne demandait de synthetiser une AUTRE entreprise que celle analysee.
_EMETTEURS = ("nvidia", "nvda", "cuda", "nvlink", "blackwell", "rubin", "tsmc", "huawei",
              "hyperscaler", "microsoft", "msft", "azure", "amd")
for fp, tgt in SYNTHESIS_TARGETS.items():
    for texte, quoi in ((tgt.query, "query"), (tgt.guidance, "guidance")):
        fautes = [m for m in _EMETTEURS if m in texte.lower()]
        check(f"{fp} : {quoi} sans nom d'emetteur code en dur", not fautes, f"-> {fautes}")
    check(f"{fp} : query parametree par {{company}}", "{company}" in tgt.query)
    check(f"{fp} : guidance parametree par {{company}}", "{company}" in tgt.guidance)

# resolve() specialise sans laisser fuiter de placeholder.
tgt = SYNTHESIS_TARGETS["business_model.description"]
q_msft, g_msft = tgt.resolve("MSFT")
q_nvda, g_nvda = tgt.resolve("NVDA")
check("resolve injecte l'emetteur dans la query", "MSFT" in q_msft and "NVDA" in q_nvda)
check("resolve injecte l'emetteur dans la guidance", "MSFT" in g_msft and "NVDA" in g_nvda)
check("aucun placeholder residuel", "{company}" not in q_msft and "{company}" not in g_msft)
check("deux emetteurs -> deux consignes distinctes", g_msft != g_nvda)
check("le message de tache porte la guidance resolue",
      "MSFT" in _synthesis_task_message(tgt, "#1 v1 [A] fact — x", g_msft))


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
