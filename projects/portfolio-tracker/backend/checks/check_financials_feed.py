"""Vérification de l'alimentateur `financials` (ratios dérivés) — transformation PURE, sans réseau ni DB.

On confronte :
  • `extract_edgar_facts()` à des entries EDGAR au format du seed NVDA (choix du dernier exercice,
    lecture du poste composite cash_and_lt_debt, capex absent) ;
  • `build_financials_entries()` à l'arithmétique réelle des 4 ratios sur les chiffres NVDA FY2026 —
    d'abord SANS capex (2 champs fondés, 2 non fondés HONNÊTEMENT, jamais fabriqués), puis capex injecté
    (4 champs), en vérifiant que tout sort en `edgar_official` (condition du tier A du plancher) ;
  • les helpers purs d'EDGAR (`cik_from_url`, parsing/appariement des points annuels).
"""
import sys
from datetime import date

from app.knowledge.edgar_facts import (
    _parse_annual_points, _pick_for_period, cik_from_url,
)
from app.knowledge.financials_feed import (
    build_financials_entries, extract_edgar_facts,
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


def approx(a, b, tol=0.05):
    return a is not None and abs(a - b) <= tol


AS_OF = date(2026, 8, 25)
URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm"


def _fact(metric, extra, period="FY2026", end="2026-01-25", eid=1):
    cs = {"metric": metric, "currency": "USD", "period": period, "period_end": end}
    cs.update(extra)
    return {
        "id": eid, "entry_type": "fact_financial", "source_type": "edgar_official",
        "content_structured": cs, "source_url": URL, "source_date": end, "fiscal_period": period,
    }


# KB EDGAR NVDA (format seed) — FY2026 complet + un comparatif FY2025 pour tester le choix d'exercice
ENTRIES = [
    _fact("revenue", {"value": 215938000000}, eid=1),
    _fact("revenue", {"value": 130497000000}, period="FY2025", end="2025-01-26", eid=2),
    _fact("net_income", {"value": 120067000000}, eid=3),
    _fact("net_income", {"value": 72880000000}, period="FY2025", end="2025-01-26", eid=4),
    _fact("operating_cash_flow", {"value": 102718000000}, eid=5),
    _fact("stockholders_equity", {"value": 157293000000}, eid=6),
    _fact("total_assets", {"value": 206803000000}, eid=7),
    _fact("cash_and_lt_debt", {"cash": 10605000000, "long_term_debt": 7469000000}, eid=8),
]

print("\n1. extract_edgar_facts — dernier exercice, poste composite, capex absent")
facts = extract_edgar_facts(ENTRIES)
check("exercice ancré sur le bilan le plus récent (FY2026, fin 2026-01-25)",
      facts["period_end"] == date(2026, 1, 25) and facts["period"] == "FY2026", f"→ {facts['period_end']}")
check("CA FY2026 pris (pas le comparatif FY2025)", facts["revenue"] == 215938000000, f"→ {facts['revenue']}")
check("résultat net FY2026", facts["net_income"] == 120067000000)
check("cash + dette LT lus depuis le poste composite",
      facts["cash"] == 10605000000 and facts["long_term_debt"] == 7469000000)
check("capex absent de la base = None (jamais 0)", facts.get("capex") is None)
check("URL de provenance conservée (→ CIK)", facts["source_url"] == URL)

print("\n2. build SANS capex — levier + roic fondés, les 2 dépendants du capex non fondés (#25)")
specs, unfounded = build_financials_entries("NVDA", "NVDA", facts, as_of=AS_OF)
fields = {s.field for s in specs}
check("2 ratios fondés (levier, roic_pct)", fields == {"levier", "roic_pct"}, f"→ {fields}")
unf_fields = {u["field"] for u in unfounded}
check("2 champs non fondés = fcf_conversion_pct + intensite_capex_pct",
      unf_fields == {"fcf_conversion_pct", "intensite_capex_pct"}, f"→ {unf_fields}")
check("raison des non fondés cite le capex EDGAR",
      all("capex" in u["reason"] for u in unfounded), f"→ {unfounded}")
check("tous les ratios en edgar_official (tier A à l'écriture)",
      all(s.source_type == "edgar_official" for s in specs))
check("tous en entry_type fact_financial", all(s.entry_type == "fact_financial" for s in specs))

by = {s.field: s for s in specs}
lev = by["levier"].content_structured
check("levier : dette nette = dette LT − trésorerie", approx(lev["net_debt"], -3136000000.0, 1e6))
check("levier : position de trésorerie nette positive détectée", lev["net_cash_position"] is True)
check("levier : gearing dette/capitaux propres ≈ 4,75 %", approx(lev["debt_to_equity_pct"], 4.75))
check("levier : le content signale la trésorerie nette",
      "trésorerie nette" in by["levier"].content.lower())

roic = by["roic_pct"].content_structured
check("roic : capital investi = CP + dette LT − trésorerie", approx(roic["invested_capital"], 154157000000.0, 1e6))
check("roic ≈ 77,9 %", approx(roic["roic_pct"], 77.88, 0.05), f"→ {roic['roic_pct']}")
check("roic : approximation NOPAT ≈ résultat net déclarée",
      roic["nopat_approx"] == "net_income" and "NOPAT" in by["roic_pct"].content)
check("roic : tags ciblent le champ (curator + supersede)",
      by["roic_pct"].tags[:2] == ["financials", "roic_pct"], f"→ {by['roic_pct'].tags}")

print("\n3. build AVEC capex EDGAR injecté — 4 ratios, arithmétique complète")
facts_c = dict(facts, capex=3236000000)
specs2, unf2 = build_financials_entries("NVDA", "NVDA", facts_c, as_of=AS_OF)
check("4 ratios fondés", {s.field for s in specs2} ==
      {"levier", "roic_pct", "fcf_conversion_pct", "intensite_capex_pct"}, f"→ {[s.field for s in specs2]}")
check("aucun champ non fondé", unf2 == [], f"→ {unf2}")
by2 = {s.field: s for s in specs2}
conv = by2["fcf_conversion_pct"].content_structured
# FCF = 102 718 − 3 236 = 99 482 ; conversion = 99 482 / 120 067 = 82,86 %
check("fcf_conversion : FCF = OCF − capex", approx(conv["free_cash_flow"], 99482000000.0, 1e6))
check("fcf_conversion ≈ 82,9 %", approx(conv["fcf_conversion_pct"], 82.86, 0.05), f"→ {conv['fcf_conversion_pct']}")
inten = by2["intensite_capex_pct"].content_structured
# 3 236 / 215 938 = 1,499 %
check("intensite_capex = capex / CA ≈ 1,50 %", approx(inten["intensite_capex_pct"], 1.50, 0.02),
      f"→ {inten['intensite_capex_pct']}")

print("\n4. build DÉGRADÉ — sans capitaux propres, levier ET roic tombent proprement")
facts_bad = dict(facts, stockholders_equity=None)
specs3, unf3 = build_financials_entries("NVDA", "NVDA", facts_bad, as_of=AS_OF)
check("levier et roic_pct non fondés si capitaux propres manquent",
      {"levier", "roic_pct"} <= {u["field"] for u in unf3}, f"→ {unf3}")
check("aucun ratio inventé (specs limitées)", all(s.field not in {"roic_pct", "levier"} for s in specs3))

print("\n5. EDGAR — CIK depuis l'URL + appariement des points annuels")
check("cik_from_url extrait 1045810", cik_from_url(URL) == 1045810, f"→ {cik_from_url(URL)}")
check("cik_from_url(None) = None", cik_from_url(None) is None)
payload = {"units": {"USD": [
    {"end": "2026-01-25", "val": 3236000000, "fy": 2026, "fp": "FY", "form": "10-K", "accn": "a1", "filed": "2026-02-25"},
    {"end": "2025-01-26", "val": 3236000000, "fy": 2025, "fp": "FY", "form": "10-K", "accn": "a0", "filed": "2025-02-21"},
    {"end": "2025-10-26", "val": 900000000, "fy": 2026, "fp": "Q3", "form": "10-Q", "accn": "aq", "filed": "2025-11-19"},
    {"end": "2026-01-25", "val": 3236000000, "fy": 2026, "fp": "FY", "form": "10-K/A", "accn": "a1b", "filed": "2026-06-01"},
]}}
pts = _parse_annual_points(payload, unit="USD")
check("points annuels seulement (les 10-Q trimestriels écartés)", len(pts) == 2, f"→ {len(pts)}")
check("dédoublonnage par 'end' : 10-K préféré au 10-K/A",
      next(p for p in pts if p["end"] == "2026-01-25")["form"] == "10-K")
picked = _pick_for_period(pts, date(2026, 1, 25))
check("appariement au period_end visé (2026-01-25)", picked and picked["val"] == 3236000000)
check("hors tolérance → aucun point", _pick_for_period(pts, date(2030, 1, 1)) is None)

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
