"""Vérification de l'alimentateur de SYNTHÈSE grounded — transformations PURES, sans réseau ni DB ni LLM.

Couvre les trois garde-fous déterministes du feed (tout ce que le LLM ne décide PAS) :
  • `derive_synthesis_reliability` : la règle « un cran sous la plus faible entry citée » (validée
    2026-08-26), y compris les 4 cas de la décision (tableau AskUserQuestion) ;
  • `validate_grounding` : une citation hors du corpus citable, ou une assertion sans citation, est
    une VIOLATION (le grounding est vérifié, pas déclaré — #24/#28) ;
  • `build_content_structured` + le contrat `GroundedSynthesis` (union des ids, min 1 citation/claim) ;
  • § 8-10 (capacité 5, 2026-09-09) : la LACUNE DÉCLARÉE et son approximation — le trou cesse d'être
    de la prose et devient une donnée nommée, dont le rang est DÉRIVÉ et le grounding VÉRIFIÉ.
"""
import sys

from app.contracts import Approximation, GroundedSynthesis, LacuneDeclaree, SynthesisClaim
from app.knowledge.synthesis_feed import (
    CITABLE_TIERS,
    SYNTHESIS_TARGETS,
    _CONSIGNE_LACUNES,
    _SYNTHESIS_SKELETON,
    _SYNTHESIS_SYSTEM_PROMPT,
    _synthesis_task_message,
    build_content_structured,
    derive_synthesis_reliability,
    qualify_lacunes,
    render_lacunes_markdown,
    validate_grounding,
)

ok = fail = 0


def _accepte(fabrique) -> bool:
    """True si la construction PASSE. Sert aux tests négatifs de contrat : on veut affirmer qu'une
    forme interdite est REFUSÉE, et ce helper évite d'écrire `try/except: check(True)` — motif où
    l'exception attrapée peut venir d'ailleurs que de la validation visée."""
    try:
        fabrique()
        return True
    except Exception:
        return False


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
    lacunes=[],
)
check("cited_entry_ids() = union triée dédupliquée", synth.cited_entry_ids() == [32, 33, 34],
      f"→ {synth.cited_entry_ids()}")
try:
    SynthesisClaim(text="non sourcé", cited_entry_ids=[])
    check("claim sans citation rejeté par le contrat", False, "accepté !")
except Exception:
    check("claim sans citation rejeté par le contrat", True)
try:
    # ⚠️ `lacunes=[]` est fourni EXPRÈS : sans lui, ce test rougirait pour le mauvais motif (champ
    # requis manquant) et n'éprouverait plus `claims` du tout. Un test négatif qui rougit à côté de
    # sa cible est un faux rouge, aussi trompeur qu'un faux vert.
    GroundedSynthesis(title="t", synthesis_markdown="m", claims=[], lacunes=[])
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
check("aucune lacune → compte AFFIRMÉ à 0, pas clef absente",
      cs["lacunes"] == [] and cs["lacunes_n"] == 0 and cs["lacunes_approximees_n"] == 0)

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

# La consigne de lacune a UN detenteur (_CONSIGNE_LACUNES) et passe par resolve(). Si quelqu'un la
# recopie dans un descripteur, ou debranche la concatenation, ces deux asserts le disent.
for fp, t2 in SYNTHESIS_TARGETS.items():
    check(f"{fp} : la guidance ne recopie PAS la consigne de lacune",
          "lacunes[]" not in t2.guidance)
    check(f"{fp} : resolve() y adjoint la consigne unique",
          _CONSIGNE_LACUNES.strip()[:40] in t2.resolve("ACME")[1])
# Le trou ne se declare plus en prose : aucune guidance ne doit encore le demander (le correctif
# doit RETIRER l'ancienne formulation, pas seulement ajouter la nouvelle).
for fp, t2 in SYNTHESIS_TARGETS.items():
    bas = t2.guidance.lower()
    check(f"{fp} : plus de consigne de trou EN PROSE",
          "non document" not in bas and "non observable" not in bas)


print("\n8. Contrat de la LACUNE — une estimation sans base n'existe pas (capacité 5)")
approx_ok = Approximation(
    valeur="80,5 %", methode="267 143 / 331 839 = 80,5 %",
    sens_erreur="plancher", hypotheses=["une part des Produits est reconnue over time"],
    cited_entry_ids=[32, 33],
)
check("approximation complète acceptée", approx_ok.sens_erreur == "plancher")
for label, kw in [
    ("sans ingrédient cité → refusée par le contrat", dict(cited_entry_ids=[])),
    ("sans hypothèse énoncée → refusée par le contrat", dict(hypotheses=[])),
    ("sens d'erreur hors des 3 états → refusé", dict(sens_erreur="peut-etre")),
    ("méthode vide → refusée (un chiffre sans chemin)", dict(methode="")),
    ("valeur vide → refusée", dict(valeur="")),
    ("ingrédient d'id négatif → refusé", dict(cited_entry_ids=[-1])),
]:
    base = dict(valeur="80,5 %", methode="a/b", sens_erreur="plancher",
                hypotheses=["h"], cited_entry_ids=[32])
    try:
        Approximation(**(base | kw))
        check(label, False, "accepté !")
    except Exception:
        check(label, True)
check("statut hors des 2 causes nommées → refusé",
      not _accepte(lambda: LacuneDeclaree(question="q", statut="bof")))
lac_sans = LacuneDeclaree(question="prix de vente moyen unitaire", statut="non_publie_source")
check("une lacune SANS approximation est valide (5ᵉ barreau)", lac_sans.approximation is None)

print("\n9. qualify_lacunes — le rang de l'estimation est DÉRIVÉ, jamais déclaré")
lacs = [
    LacuneDeclaree(question="taux de récurrence", statut="non_publie_source", approximation=approx_ok),
    LacuneDeclaree(question="coût unitaire par siège", statut="non_documente_base"),
]
q = qualify_lacunes(lacs, {32: "A", 33: "A"})
check("2 pièces A → estimation A- (un cran sous), pas A",
      q[0]["approximation"]["derived_tier"] == "A-", f"→ {q[0]['approximation']['derived_tier']}")
check("l'estimation n'hérite JAMAIS du rang de ses ingrédients",
      q[0]["approximation"]["derived_tier"] != "A")
check("le maillon faible pilote (A + B+ → B)",
      qualify_lacunes(lacs, {32: "A", 33: "B+"})[0]["approximation"]["derived_tier"] == "B")
check("une estimation est une INTERPRÉTATION, pas une mesure (#51)",
      q[0]["approximation"]["nature"] == "interpretation")
check("le barreau atteint est DANS la ligne",
      [x["barreau"] for x in q] == ["approximee", "declaree"])
check("la lacune non approchée n'invente pas d'estimation", q[1]["approximation"] is None)
check("les tiers des ingrédients sont tracés",
      q[0]["approximation"]["cited_tiers"] == {"32": "A", "33": "A"})
check("hypothèses et méthode conservées mot pour mot",
      q[0]["approximation"]["methode"] == "267 143 / 331 839 = 80,5 %"
      and q[0]["approximation"]["hypotheses"] == ["une part des Produits est reconnue over time"])

synth_lac = GroundedSynthesis(
    title="t", synthesis_markdown="m",
    claims=[SynthesisClaim(text="x", cited_entry_ids=[32])], lacunes=lacs,
)
check("approximation_entry_ids() ≠ cited_entry_ids() (une pièce peut ne servir qu'au calcul)",
      synth_lac.approximation_entry_ids() == [32, 33] and synth_lac.cited_entry_ids() == [32])
cs2 = build_content_structured(SYNTHESIS_TARGETS["produits.unit_economics"], synth_lac, [32],
                               {32: "A", 33: "A"})
check("content_structured compte les lacunes et les approchées",
      cs2["lacunes_n"] == 2 and cs2["lacunes_approximees_n"] == 1)

print("\n10. Le grounding d'une ESTIMATION obéit à la même règle que celui d'une assertion")
citable2 = {32, 33}
claims2 = [{"text": "x", "cited_entry_ids": [32]}]
check("estimation dans le corpus → aucune violation",
      validate_grounding(claims2, citable2,
                         approximations=[{"question": "q", "cited_entry_ids": [32, 33]}]) == [])
errs2 = validate_grounding(claims2, citable2,
                           approximations=[{"question": "taux de récurrence",
                                            "cited_entry_ids": [32, 4242]}])
check("ingrédient hors corpus → violation NOMMANT la question",
      len(errs2) == 1 and "4242" in errs2[0] and "taux de récurrence" in errs2[0], f"→ {errs2}")
check("estimation sans ingrédient → violation",
      validate_grounding(claims2, citable2,
                         approximations=[{"question": "q", "cited_entry_ids": []}]) != [])
check("les claims restent vérifiés quand des approximations sont passées",
      len(validate_grounding([{"text": "x", "cited_entry_ids": [999]}], citable2,
                             approximations=[{"question": "q", "cited_entry_ids": [32]}])) == 1)

md = render_lacunes_markdown(q)
check("le rendu nomme la question, la valeur, le sens de l'erreur et la base",
      all(s in md for s in ("taux de récurrence", "80,5 %", "plancher", "#32", "#33")), f"→ {md}")
check("le rendu dit qu'aucune méthode n'est tenable pour l'autre",
      "aucune méthode d'approche tenable" in md)
check("aucune lacune → le rendu l'AFFIRME (pas un silence)",
      "aucune" in render_lacunes_markdown([]).lower())

check("le prompt système décrit les 2 causes nommées",
      "non_publie_source" in _SYNTHESIS_SYSTEM_PROMPT
      and "non_documente_base" in _SYNTHESIS_SYSTEM_PROMPT)
check("le prompt système enseigne les 3 sens d'erreur",
      all(s in _SYNTHESIS_SYSTEM_PROMPT for s in ("plancher", "plafond", "indetermine")))
check("le prompt système n'envoie plus le trou en prose",
      "non documenté en base" not in _SYNTHESIS_SYSTEM_PROMPT)
check("le squelette montre AUSSI la forme sans approximation (null est une réponse normale)",
      '"approximation": null' in _SYNTHESIS_SKELETON)


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
