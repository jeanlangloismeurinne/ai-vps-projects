"""Vérification de l'alimentateur `valorisation` (sprint 1) — transformation PURE, sans réseau ni DB.

On alimente `build_valuation_entries()` avec un m1 réel (NVDA au 2026-08-25) et un m1 à multiples
partiels (KO, sans rendement FCF), et on vérifie que les deux champs de valorisation fondables par le
quant — `prix_actuel` et `relatif_multiple` — sortent proprement, taggés pour le curator, sans jamais
prétendre fonder `base_rate_anchor`. Le cas « prix absent » doit LEVER, pas rendre une entrée vide.
"""
import sys
from datetime import date

from app.knowledge.valuation_feed import (
    ValuationUnavailable, build_valuation_entries, _num,
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


AS_OF = date(2026, 8, 25)

# m1 réel NVDA (yfinance-shape, chiffres du 2026-08-25)
NVDA_M1 = {
    "price": {
        "current_price": 212.28, "currency": "USD",
        "market_cap": 5_140_000_000_000, "enterprise_value": 5_110_000_000_000,
        "distance_from_52w_high_pct": -3.1,
    },
    "valuation": {
        "pe_ntm": 20.77, "pe_ttm": 31.93, "ev_ebitda": 30.26,
        "ev_revenue": 19.76, "price_to_book": 25.83, "fcf_yield_pct": 2.1,
    },
}
# m1 à multiples partiels (KO — pas de rendement FCF renvoyé)
KO_M1 = {
    "price": {"current_price": 91.68, "currency": "USD", "market_cap": 394_440_000_000,
              "enterprise_value": 430_000_000_000},
    "valuation": {"pe_ttm": 27.65, "pe_ntm": 27.06, "ev_ebitda": 24.93,
                  "ev_revenue": 8.45, "price_to_book": None, "fcf_yield_pct": None},
}

print("\n1. NVDA — deux champs de valorisation, dans le bon ordre")
entries = build_valuation_entries("NVDA", "NVDA", NVDA_M1, as_of=AS_OF)
check("2 entrées produites", len(entries) == 2, f"→ {len(entries)}")
fields = [e.field for e in entries]
check("champs = prix_actuel puis relatif_multiple", fields == ["prix_actuel", "relatif_multiple"], f"→ {fields}")
check("aucune entrée ne prétend fonder base_rate_anchor",
      all("base_rate_anchor" not in e.field for e in entries))

prix, mult = entries
print("\n2. prix_actuel — contenu et structure")
check("entry_type fact_financial", prix.entry_type == "fact_financial")
check("source_type yfinance (mesuré, pas déclaré)", prix.source_type == "yfinance")
check("tags ciblent valorisation+prix_actuel (pour supersede + curator)",
      "valorisation" in prix.tags and "prix_actuel" in prix.tags, f"→ {prix.tags}")
check("content_structured.metric = prix_actuel", prix.content_structured["metric"] == "prix_actuel")
check("prix et devise portés", prix.content_structured["current_price"] == 212.28
      and prix.content_structured["currency"] == "USD")
check("as_of figé", prix.content_structured["as_of"] == "2026-08-25")
check("prix lisible dans le content", "212" in prix.content and "USD" in prix.content, f"→ {prix.content}")

print("\n3. relatif_multiple — multiples portés, ancre explicitement hors-champ")
check("content_structured.metric = relatif_multiple", mult.content_structured["metric"] == "relatif_multiple")
check("P/E TTM et EV/EBITDA portés", mult.content_structured["pe_ttm"] == 31.93
      and mult.content_structured["ev_ebitda"] == 30.26)
check("le content distingue multiples actuels et base_rate_anchor",
      "base_rate_anchor" in mult.content and "relatif_multiple" in mult.content, f"→ {mult.content}")
check("tags ciblent relatif_multiple", "relatif_multiple" in mult.tags, f"→ {mult.tags}")

print("\n4. KO — multiples partiels : None → 'n/d', jamais une valeur inventée")
ko = build_valuation_entries("KO", "KO", KO_M1, as_of=AS_OF)
ko_mult = ko[1]
check("fcf_yield None conservé en structuré (pas 0)", ko_mult.content_structured["fcf_yield_pct"] is None)
check("None rendu 'n/d' dans le texte", "n/d" in ko_mult.content, f"→ {ko_mult.content}")
check("_num(None) = n/d", _num(None) == "n/d")
check("_num formate en FR (virgule)", _num(31.93, suffix='×') == "31,93×", f"→ {_num(31.93, suffix='×')}")

print("\n5. Prix absent = échec EXPLICITE (jamais une entrée vide, #25)")
try:
    build_valuation_entries("X", "X", {"price": {}, "valuation": {}}, as_of=AS_OF)
    check("ValuationUnavailable levée si prix absent", False, "aucune exception !")
except ValuationUnavailable as e:
    check("ValuationUnavailable levée si prix absent", True)
    check("message nomme le ticker/symbole", "X" in str(e), f"→ {e}")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
