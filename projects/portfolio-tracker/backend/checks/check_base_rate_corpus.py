"""Vérification du corpus base rate + ancre `valorisation.base_rate_anchor` — PUR, sans réseau ni DB.

On vérifie : (1) l'arithmétique de la distribution colle aux chiffres EXACTS de l'Exhibit 2 (somme
des colonnes = 100 %, P(≥20 %/3 ans)=11,9 %) ; (2) le classifieur range NVDA en méga-cap et une
mid-cap correctement ; (3) l'ancre méga-cap est marquée « borne haute » ; (4) une base rate n'est
jamais fondée sur une classe inventée (lève si ni CA ni capitalisation).
"""
import sys

from app.knowledge.base_rate_corpus import (
    BaseRateUnavailable, SALES_GROWTH_DISTRIBUTION, base_rate_ge,
    build_base_rate_anchor_spec, classify_reference_class, size_bucket,
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


print("\n1. Distribution = Exhibit 2 (chiffres exacts) — colonnes somment à 100 %")
for h in ("1Y", "3Y", "5Y", "10Y"):
    total = round(sum(freq[h] for _, freq in SALES_GROWTH_DISTRIBUTION), 1)
    check(f"colonne {h} = 100 %", abs(total - 100.0) < 0.15, f"→ {total}")

print("\n2. base_rate_ge — lookup conservateur, valeurs du livre")
check("P(≥20 %/an, 3 ans) = 11,9 %", base_rate_ge(20, "3Y") == 11.9, f"→ {base_rate_ge(20, '3Y')}")
check("P(≥15 %/an, 3 ans) = 18,6 %", base_rate_ge(15, "3Y") == 18.6, f"→ {base_rate_ge(15, '3Y')}")
check("P(≥45 %/an, 3 ans) = 2,5 %", base_rate_ge(45, "3Y") == 2.5, f"→ {base_rate_ge(45, '3Y')}")
check("P(≥20 %/an, 5 ans) = 8,5 %", base_rate_ge(20, "5Y") == 8.5, f"→ {base_rate_ge(20, '5Y')}")
check("P(≥20 %/an, 10 ans) = 4,5 %", base_rate_ge(20, "10Y") == 4.5, f"→ {base_rate_ge(20, '10Y')}")
check("horizon plus long ⇒ persistance plus rare", base_rate_ge(20, "3Y") > base_rate_ge(20, "10Y"))

print("\n3. size_bucket — maille du livre (CA, méga = >50 Md$)")
check("NVDA (CA 216 Md$) = mega", size_bucket(216e9, 5.1e12)[0] == "mega")
check("CA 25 Md$ = large", size_bucket(25e9, 300e9)[0] == "large")
check("CA 4 Md$ = mid", size_bucket(4e9, 20e9)[0] == "mid")
check("CA absent → repli capitalisation (basis noté)", size_bucket(None, 300e9)[2] == "capitalisation")

print("\n4. classify + ancre NVDA (méga-cap = borne haute)")
NVDA_M1 = {
    "price": {"market_cap": 5_140_000_000_000, "currency": "USD"},
    "financials_3y": {"2026": {"revenue": 215_938_000_000}, "2025": {"revenue": 130_497_000_000}},
}
rc = classify_reference_class(NVDA_M1)
check("classe NVDA = méga-cap sur base CA", rc["size_bucket"] == "mega" and rc["size_basis"] == "CA", f"→ {rc}")
spec = build_base_rate_anchor_spec("NVDA", "NVDA", NVDA_M1)
check("field = base_rate_anchor", spec.field == "base_rate_anchor")
check("entry_type = base_rate", spec.entry_type == "base_rate")
check("tags fondent valorisation.base_rate_anchor",
      "valorisation" in spec.tags and "base_rate_anchor" in spec.tags, f"→ {spec.tags}")
check("distribution complète portée en structuré",
      len(spec.content_structured["distribution"]) == 16)
check("seuils représentatifs présents (15/20/25)",
      set(spec.content_structured["thresholds_pct_ge"]) == {"15", "20", "25"})
check("méga-cap marquée borne haute", spec.content_structured["upper_bound_for_size"] is True)
check("le content dit que c'est une fréquence, pas un multiple",
      "FRÉQUENCE" in spec.content and "multiple" in spec.content, f"→ {spec.content[:120]}")
check("borne haute explicitée pour la taille", "Borne HAUTE" in spec.content)
check("source citée (Base Rate Book)", "Base Rate Book" in spec.content and spec.source_url.endswith(".pdf"))

print("\n5. mid-cap (non méga) : PAS de borne haute")
MID_M1 = {"price": {"market_cap": 20e9}, "financials_3y": {"2026": {"revenue": 4e9}}}
mid_spec = build_base_rate_anchor_spec("MID", "MID", MID_M1)
check("mid-cap non marquée borne haute", mid_spec.content_structured["upper_bound_for_size"] is False)
check("mid-cap sans mention 'Borne HAUTE'", "Borne HAUTE" not in mid_spec.content)

print("\n6. Classe indéterminable = échec EXPLICITE (jamais une classe inventée)")
try:
    classify_reference_class({"price": {}, "financials_3y": {}})
    check("BaseRateUnavailable si ni CA ni capitalisation", False, "aucune exception !")
except BaseRateUnavailable:
    check("BaseRateUnavailable si ni CA ni capitalisation", True)

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
