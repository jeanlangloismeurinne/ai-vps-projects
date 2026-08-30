"""Vérification de l'alimentateur du SOCLE EDGAR (postes comptables bruts) — PURE, sans réseau ni DB.

Ce que ce check protège, dans l'ordre d'importance :

  1. **La sélection de concept par FRAÎCHEUR, pas par convention.** C'est le mode de panne central,
     mesuré contre l'API réelle le 2026-08-30 : `Revenues` répond HTTP 200 pour MSFT mais son dernier
     point date de **2010** (le tag courant est `RevenueFromContractWithCustomerExcludingAssessedTax`),
     exactement comme `PaymentsToAcquirePropertyPlantAndEquipment` s'arrête en **2012** pour NVDA.
     « Le premier tag qui répond » écrirait un CA de 2010 en tier A, présenté comme le CA courant :
     un faux tier A, silencieux, qui empoisonnerait tous les ratios en aval.
  2. **Le garde-fou de durée sur les flux.** Un point `fp=FY` déposé en 10-K peut porter un trimestre ;
     le prendre pour un flux annuel diviserait le CA par ~4 sans aucun signal d'erreur.
  3. **L'alignement sur un seul exercice** — jamais deux exercices mélangés dans un même socle.
  4. **Le format de sortie est bien celui que `financials_feed.extract_edgar_facts()` sait lire** :
     ces deux modules se parlent par le `content_structured`, donc on referme la boucle ici en
     faisant relire les specs produites par le consommateur réel.
  5. **Un poste absent reste absent** (`unfounded`), jamais estimé (#25).
"""
import sys
from datetime import date

from app.knowledge.edgar_facts import _parse_annual_points, cik_from_url
from app.knowledge.edgar_feed import (
    POSTES, build_edgar_entries, fiscal_label, filing_url, is_annual_flow, select_concept,
)
from app.knowledge.financials_feed import extract_edgar_facts

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def pt(end, val, *, start=None, form="10-K", accn="0000789019-26-000010", fy=None):
    return {"end": end, "val": float(val), "start": start, "fy": fy, "form": form,
            "accn": accn, "filed": end}


def annual(end, val, **kw):
    """Point de FLUX couvrant un exercice complet (start = end - 364 j)."""
    e = date.fromisoformat(end)
    return pt(end, val, start=(e.replace(year=e.year - 1)).isoformat(), **kw)


# ── 1. Sélection de concept par fraîcheur — le cas MSFT/NVDA réellement mesuré ────────────────────
print("\n[1] sélection du concept XBRL par fraîcheur (le piège du tag périmé qui répond 200)")

ANCHOR = date(2026, 6, 30)
# Reproduction fidèle du relevé MSFT : `Revenues` s'arrête en 2010, le tag ASC 606 est à jour.
msft_revenue = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": [
        annual("2025-06-30", 270_010_000_000), annual("2026-06-30", 331_840_000_000)],
    "Revenues": [annual("2009-06-30", 58_437_000_000), annual("2010-06-30", 62_484_000_000)],
}
concept, point = select_concept(msft_revenue, ANCHOR, flow=True)
check("MSFT: le tag ASC 606 (frais) est retenu",
      concept == "RevenueFromContractWithCustomerExcludingAssessedTax", f"→ {concept}")
check("MSFT: la valeur retenue est celle de l'exercice ancré (331,84 Md$)",
      point and point["val"] == 331_840_000_000, f"→ {point and point['val']}")

# Ordre inversé dans le dict : la fraîcheur doit primer sur l'ordre de déclaration.
msft_inverse = {k: msft_revenue[k] for k in reversed(list(msft_revenue))}
concept2, _ = select_concept(msft_inverse, ANCHOR, flow=True)
check("MSFT: la fraîcheur prime sur l'ordre des candidats",
      concept2 == "RevenueFromContractWithCustomerExcludingAssessedTax", f"→ {concept2}")

# Le cas NVDA capex, déjà documenté, doit passer par le même chemin générique.
nvda_capex = {
    "PaymentsToAcquirePropertyPlantAndEquipment": [annual("2012-01-29", 143_000_000)],
    "PaymentsToAcquireProductiveAssets": [annual("2026-01-25", 6_042_000_000)],
}
concept3, point3 = select_concept(nvda_capex, date(2026, 1, 25), flow=True)
check("NVDA: capex → le tag non-standard mais frais",
      concept3 == "PaymentsToAcquireProductiveAssets", f"→ {concept3}")
check("NVDA: capex = 6,042 Md$ (valeur vérifiée en prod le 2026-08-25)",
      point3 and point3["val"] == 6_042_000_000)

check("aucun candidat frais → None (le poste restera non fondé, pas estimé)",
      select_concept({"Revenues": [annual("2010-06-30", 62_484_000_000)]}, ANCHOR, flow=True)
      == (None, None))
check("dict de candidats vide → None", select_concept({}, ANCHOR, flow=True) == (None, None))

# ── 2. Garde-fou de durée sur les flux ───────────────────────────────────────────────────────────
print("\n[2] un point `fp=FY` trimestriel ne passe pas pour un flux annuel")

check("flux annuel (364 j) accepté", is_annual_flow(annual("2026-06-30", 1)))
check("flux trimestriel (92 j) refusé",
      not is_annual_flow(pt("2026-06-30", 1, start="2026-03-31")))
check("point de bilan (sans `start`) refusé comme flux", not is_annual_flow(pt("2026-06-30", 1)))

quarterly_only = {"Revenues": [pt("2026-06-30", 82_960_000_000, start="2026-03-31")]}
check("un CA uniquement trimestriel n'est PAS retenu comme annuel",
      select_concept(quarterly_only, ANCHOR, flow=True) == (None, None))
check("le même point EST retenu pour un poste de bilan (flow=False)",
      select_concept(quarterly_only, ANCHOR, flow=False)[0] == "Revenues")

# ── 3. Construction des entries + alignement sur un seul exercice ────────────────────────────────
print("\n[3] specs d'entries : un seul exercice, format lisible par financials_feed")

CIK = 789019
ACCN = "0000950170-26-000123"
resolved = {
    "stockholders_equity": {"concept": "StockholdersEquity", "unit": "USD",
                            "point": pt("2026-06-30", 442_390_000_000, accn=ACCN, fy=2026)},
    "revenue": {"concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "unit": "USD",
                "point": annual("2026-06-30", 331_840_000_000, accn=ACCN, fy=2026)},
    "net_income": {"concept": "NetIncomeLoss", "unit": "USD",
                   "point": annual("2026-06-30", 133_750_000_000, accn=ACCN, fy=2026)},
    "gross_profit": {"concept": "GrossProfit", "unit": "USD",
                     "point": annual("2026-06-30", 225_470_000_000, accn=ACCN, fy=2026)},
    "operating_cash_flow": {"concept": "NetCashProvidedByUsedInOperatingActivities", "unit": "USD",
                            "point": annual("2026-06-30", 182_940_000_000, accn=ACCN, fy=2026)},
    "total_assets": {"concept": "Assets", "unit": "USD",
                     "point": pt("2026-06-30", 758_380_000_000, accn=ACCN, fy=2026)},
    "capital_expenditure": {"concept": "PaymentsToAcquirePropertyPlantAndEquipment", "unit": "USD",
                            "point": annual("2026-06-30", 115_950_000_000, accn=ACCN, fy=2026)},
    "cash_and_lt_debt": {
        "concept": "CashAndCashEquivalentsAtCarryingValue", "unit": "USD",
        "point": pt("2026-06-30", 30_200_000_000, accn=ACCN, fy=2026),
        "second": {"concept": "LongTermDebtNoncurrent", "unit": "USD",
                   "point": pt("2026-06-30", 39_700_000_000, accn=ACCN, fy=2026)},
    },
}
specs, unfounded = build_edgar_entries("MSFT", "MSFT", CIK, resolved)

check("8 postes produits", len(specs) == 8, f"→ {len(specs)}")
check("aucun poste non fondé quand EDGAR les porte tous", unfounded == [], f"→ {unfounded}")
check("tous les postes sur le MÊME exercice",
      {s.content_structured["period_end"] for s in specs} == {"2026-06-30"})
check("période fiscale lisible", {s.fiscal_period for s in specs} == {"FY2026"})
check("le concept XBRL réellement utilisé est tracé dans chaque entry",
      all(s.content_structured["xbrl_tag"].startswith("us-gaap:") for s in specs))
check("l'accession du dépôt est tracée", all(s.content_structured["accn"] == ACCN for s in specs))

rev = next(s for s in specs if s.metric == "revenue")
check("le CA cite le tag ASC 606, pas `Revenues`",
      rev.content_structured["xbrl_tag"]
      == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
check("le contenu est en français et cite la source",
      "Chiffre d'affaires" in rev.content and "EDGAR" in rev.content, rev.content[:70])

cash = next(s for s in specs if s.metric == "cash_and_lt_debt")
check("poste composite : deux nombres dans un seul fait",
      cash.content_structured.get("cash") == 30_200_000_000
      and cash.content_structured.get("long_term_debt") == 39_700_000_000)
check("poste composite : les deux concepts sont tracés",
      cash.content_structured.get("xbrl_tag_2") == "us-gaap:LongTermDebtNoncurrent")

# ── 4. source_url : provenance réelle ET relisible par cik_from_url ──────────────────────────────
print("\n[4] source_url = dépôt réel, et le CIK s'en relit (recâble edgar_facts en aval)")

url = filing_url(CIK, ACCN)
check("URL construite sur l'accession",
      url == "https://www.sec.gov/Archives/edgar/data/789019/000095017026000123/"
             "0000950170-26-000123-index.htm", f"→ {url}")
check("cik_from_url relit le CIK depuis l'URL produite", cik_from_url(url) == CIK,
      f"→ {cik_from_url(url)}")
check("toutes les entries portent cette URL", all(s.source_url == url for s in specs))
check("accession absente → pas d'URL inventée", filing_url(CIK, None) is None)

# ── 5. La boucle se referme : financials_feed sait relire ce qu'on écrit ─────────────────────────
print("\n[5] boucle fermée — extract_edgar_facts() relit les specs produites")

entries = [{
    "id": 100 + i, "entry_type": "fact_financial", "source_type": "edgar_official",
    "content_structured": s.content_structured, "source_url": s.source_url,
    "source_date": s.period_end, "fiscal_period": s.fiscal_period,
} for i, s in enumerate(specs)]
facts = extract_edgar_facts(entries)

check("ancrage retrouvé", facts["period_end"] == date(2026, 6, 30), f"→ {facts['period_end']}")
check("CA relu", facts.get("revenue") == 331_840_000_000, f"→ {facts.get('revenue')}")
check("résultat net relu", facts.get("net_income") == 133_750_000_000)
check("OCF relu", facts.get("operating_cash_flow") == 182_940_000_000)
check("capitaux propres relus", facts.get("stockholders_equity") == 442_390_000_000)
check("total actif relu", facts.get("total_assets") == 758_380_000_000)
check("marge brute relue", facts.get("gross_profit") == 225_470_000_000)
check("capex relu — le poste qui manquait au seed NVDA", facts.get("capex") == 115_950_000_000)
check("trésorerie relue (poste composite)", facts.get("cash") == 30_200_000_000)
check("dette LT relue (poste composite)", facts.get("long_term_debt") == 39_700_000_000)
check("URL de provenance relue", facts.get("source_url") == url)
check("AUCUN poste ne manque → les 4 ratios seront fondables",
      all(facts.get(k) is not None for k in
          ("revenue", "net_income", "operating_cash_flow", "stockholders_equity",
           "total_assets", "capex", "cash", "long_term_debt")))

# ── 6. Couverture partielle : un trou reste un trou ──────────────────────────────────────────────
print("\n[6] poste introuvable → `unfounded`, jamais estimé (#25)")

partial = {k: v for k, v in resolved.items() if k not in ("capital_expenditure", "gross_profit")}
specs_p, unfounded_p = build_edgar_entries("MSFT", "MSFT", CIK, partial)
check("6 postes produits sur 8", len(specs_p) == 6, f"→ {len(specs_p)}")
check("les 2 manquants sont déclarés",
      {u["metric"] for u in unfounded_p} == {"capital_expenditure", "gross_profit"},
      f"→ {unfounded_p}")
check("aucun zéro fabriqué pour le capex",
      extract_edgar_facts([{
          "id": 200 + i, "entry_type": "fact_financial", "source_type": "edgar_official",
          "content_structured": s.content_structured, "source_url": s.source_url,
          "source_date": s.period_end, "fiscal_period": s.fiscal_period,
      } for i, s in enumerate(specs_p)]).get("capex") is None)

# composite dont la 2ᵉ jambe manque → le fait entier est non fondé (pas de demi-fait trompeur)
half = dict(resolved)
half["cash_and_lt_debt"] = {k: v for k, v in resolved["cash_and_lt_debt"].items() if k != "second"}
_, unf_half = build_edgar_entries("MSFT", "MSFT", CIK, half)
check("composite incomplet → non fondé plutôt qu'à moitié écrit",
      any(u["metric"] == "cash_and_lt_debt" for u in unf_half), f"→ {unf_half}")

# ── 7. Helpers ───────────────────────────────────────────────────────────────────────────────────
print("\n[7] helpers")

check("fiscal_label préfère le `fy` d'EDGAR", fiscal_label(pt("2026-01-25", 1, fy=2026)) == "FY2026")
check("fiscal_label retombe sur l'année de clôture", fiscal_label(pt("2026-06-30", 1)) == "FY2026")
check("_parse_annual_points écarte les formes non annuelles",
      _parse_annual_points(
          {"units": {"USD": [
              {"end": "2026-06-30", "val": 1, "form": "10-Q", "fp": "Q3"},
              {"end": "2026-06-30", "val": 2, "form": "10-K", "fp": "FY"},
          ]}}, unit="USD") == [{"end": "2026-06-30", "val": 2.0, "start": None, "fy": None,
                                "form": "10-K", "accn": None, "filed": None}])
check("les 8 postes attendus sont déclarés",
      {p.metric for p in POSTES} == {
          "revenue", "net_income", "gross_profit", "operating_cash_flow", "stockholders_equity",
          "total_assets", "capital_expenditure", "cash_and_lt_debt"})
check("aucun poste ne porte de `covers` (ce sont des intrants, cf. migration 029)",
      all("covers" not in s.content_structured for s in specs))

print(f"\n=== {ok} ok / {fail} FAIL ===")
sys.exit(1 if fail else 0)
