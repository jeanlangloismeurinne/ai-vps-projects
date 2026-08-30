"""Provenance vérifiée + recherche intra-document — hors ligne, aucune clé ni réseau.

Trois blocs :
  1. `RetrievalLog` : ce que les outils ont réellement rapporté, et sa forme canonique d'URL.
  2. `_verify_provenance` / `_cited_documents` : les deux garde-fous appliqués dans `_normalise_entry`.
  3. `document_search.select_relevant` : la sélection par pertinence, en mode dégradé lexical
     (l'embedding n'est pas joignable hors ligne — c'est justement le repli qu'on veut voir marcher).
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.agents.v2.curator import FIELD_PLANCHER_OVERRIDES, _tier_ge  # noqa: E402
from app.agents.v2.tools import RetrievalLog, canonical_url  # noqa: E402
from app.agents.v2.worker import _cited_documents, _normalise_entry, _verify_provenance  # noqa: E402
from app.contracts import WorkerRequest  # noqa: E402
from app.knowledge import document_search  # noqa: E402
from app.knowledge.service import compute_reliability  # noqa: E402
from app.knowledge.websearch import classify_source_type  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}")
    else:
        fail += 1
        print(f"  ✗ {label} {detail}")


EDGAR = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm"

print("1. canonical_url — même document, écritures différentes")
check("www/schéma/slash/ancre neutralisés",
      canonical_url("https://WWW.sec.gov/a/b.htm") == canonical_url("http://sec.gov/a/b.htm/#toc"),
      f"→ {canonical_url('https://WWW.sec.gov/a/b.htm')!r}")
check("query string conservée (elle désigne le document)",
      canonical_url("https://x.com/d?doc=10k") != canonical_url("https://x.com/d?doc=10q"))
check("URL vide → clé vide", canonical_url("") == "" and canonical_url(None) == "")

print("\n2. RetrievalLog — profondeur monotone")
log = RetrievalLog()
log.record(EDGAR, "link")
check("lien enregistré", log.depth_of(EDGAR) == "link")
log.record(EDGAR, "full")
check("promotion link → full", log.depth_of(EDGAR) == "full")
log.record(EDGAR, "excerpt")
check("pas de rétrogradation full → excerpt", log.depth_of(EDGAR) == "full")
check("URL inconnue → None", log.depth_of("https://ailleurs.com/x") is None)
log.record("https://x.com/y", "n_importe_quoi")
check("profondeur invalide ignorée", log.depth_of("https://x.com/y") is None)

print("\n3. _verify_provenance — l'URL déclarée a-t-elle été lue ?")
log = RetrievalLog()
log.record("https://www.cnbc.com/article", "full")
log.record("https://www.reuters.com/piece", "excerpt")
log.record("https://ir.nvidia.com/page", "link")

unv, note = _verify_provenance("https://www.cnbc.com/article", log)
check("page récupérée → rien à signaler", unv is False and note is None)
unv, note = _verify_provenance("https://www.reuters.com/piece", log)
check("extrait seul → source gardée, mais signalée", unv is False and note and "extrait" in note)
unv, note = _verify_provenance("https://ir.nvidia.com/page", log)
check("lien sans contenu → non vérifiée", unv is True and note and "lien" in note)
unv, note = _verify_provenance(EDGAR, log)
check("URL jamais vue → non vérifiée", unv is True and note)
check("sans journal, aucune rétrogradation", _verify_provenance(EDGAR, None) == (False, None))

print("\n4. _cited_documents — une entrée = un document")
check("un seul dépôt cité", _cited_documents("Le 10-K FY2026 indique 22% du CA") == ["10-K"])
check("deux dépôts cités",
      _cited_documents("Le 10-K FY2026 et la mise à jour Q1 FY2027 (10-Q) indiquent") == ["10-K", "10-Q"])
check("insensible à la casse et aux espaces",
      _cited_documents("le def  14a et le 8-K") == ["8-K", "DEF 14A"])
check("aucun dépôt dans un article de presse",
      _cited_documents("CNBC rapporte que Google déploie Ironwood") == [])

print("\n5. _normalise_entry — les deux règles appliquées bout en bout")
req = WorkerRequest(
    requester="knowledge-curator",
    worker="search-worker",
    ticker_id="NVDA",
    query="concurrence ASIC internes des hyperscalers",
    output_schema={"entry_type": "fact_qualitative", "field_path": "competitive.threats"},
    reliability_min=0.0,
    max_entries=5,
)
raw_edgar = {
    "entry_type": "fact_qualitative",
    "content": "Le 10-K FY2026 révèle que deux clients directs représentaient 22% et 14% du CA.",
    "source_url": EDGAR,
    "source_type": "edgar_official",
    "source_date": "2026-02-25",
    "reliability_note": "dépôt officiel",
}

e = _normalise_entry(dict(raw_edgar), req, log)
check("URL jamais récupérée → source_type ramené à llm_memory", e["source_type"] == "llm_memory",
      f"→ {e['source_type']}")
# 0.40 de base moins la décote d'âge (0.02/an sur du qualitatif) — d'où le ≤, pas le ==.
check("score effondré au plancher llm_memory (au lieu de 0.94 tier A)",
      e["reliability_score"] <= 0.40 and e["reliability_tier"] == "C",
      f"→ {e['reliability_score']} {e['reliability_tier']}")
check("revue humaine exigée", e["requires_human_review"] is True)
check("motif tracé dans la note", "provenance" in e["reliability_note"])

log2 = RetrievalLog()
log2.record(EDGAR, "full")
e = _normalise_entry(dict(raw_edgar), req, log2)
check("URL réellement récupérée → edgar_official conservé", e["source_type"] == "edgar_official")
check("score plein rendu", e["reliability_score"] > 0.90, f"→ {e['reliability_score']}")
check("aucune revue humaine imposée", e["requires_human_review"] is False)

multi = dict(raw_edgar)
multi["content"] = "Le 10-K FY2026 et la mise à jour Q1 FY2027 (10-Q) indiquent : 'Some of our customers…'"
e = _normalise_entry(multi, req, log2)
check("multi-documents → revue humaine", e["requires_human_review"] is True)
check("multi-documents → score NON pénalisé (la source est réelle)",
      e["reliability_score"] > 0.90, f"→ {e['reliability_score']}")
check("désignations listées dans la note",
      "10-K" in e["reliability_note"] and "10-Q" in e["reliability_note"])

print("\n6. select_relevant — l'information est atteinte où qu'elle soit")
# Document synthétique calqué sur la structure d'un 10-K : l'information utile au tiers du texte.
bruit = "Table of Contents. UNITED STATES SECURITIES AND EXCHANGE COMMISSION. Washington D.C. " * 400
cible = ("Two direct customers accounted for 22% and 14% of total revenue, primarily attributable "
         "to the Compute & Networking segment. ")
doc = bruit + cible + bruit
position = doc.index(cible) / len(doc)

QUESTION = "concentration client part du chiffre d'affaires customers revenue"

res = asyncio.run(document_search.select_relevant(doc, QUESTION, max_chars=4000))
check("mode déclaré", res["mode"] in ("relevance", "lexical"), f"→ {res['mode']}")
print(f"    (mode obtenu ici : {res['mode']})")
check(f"passage cible atteint alors qu'il est à {position:.0%} du document",
      "22% and 14%" in res["text"])
check("budget respecté", res["chars_returned"] <= 4000, f"→ {res['chars_returned']}")
check("réduction réelle du volume", res["chars_returned"] < res["chars_total"] / 5,
      f"→ {res['chars_returned']} / {res['chars_total']}")
check("coupures matérialisées", "caractères omis" in res["text"])
check("spans en ordre de document",
      [s["start"] for s in res["spans"]] == sorted(s["start"] for s in res["spans"]))

# Repli lexical forcé : c'est le chemin qui sert quand DeepInfra tombe, et il ne doit ni échouer
# silencieusement ni se faire passer pour une sélection sémantique.
_vrai = document_search.embeddings.is_configured
document_search.embeddings.is_configured = lambda: False
try:
    deg = asyncio.run(document_search.select_relevant(doc, QUESTION, max_chars=4000))
finally:
    document_search.embeddings.is_configured = _vrai
check("embedding indisponible → mode 'lexical' DÉCLARÉ", deg["mode"] == "lexical", f"→ {deg['mode']}")
check("le repli atteint la cible lui aussi", "22% and 14%" in deg["text"])

head = asyncio.run(document_search.select_relevant(doc, "", max_chars=4000))
check("sans question → tête, et c'est DIT", head["mode"] == "head" and "22%" not in head["text"])

whole = asyncio.run(document_search.select_relevant("texte court", "question", max_chars=4000))
check("document sous le budget → rendu entier", whole["mode"] == "whole" and whole["text"] == "texte court")

vide = asyncio.run(document_search.select_relevant("", "question", max_chars=4000))
check("texte vide → pas d'exception", vide["mode"] == "whole" and vide["text"] == "")

print("\n7. chunk_text — frontières et couverture")
chunks = document_search.chunk_text(doc)
check("découpage non vide", len(chunks) > 1)
check("aucun chunk au-delà de la cible + marge",
      all(len(c.text) <= 1400 for c in chunks), f"→ max {max(len(c.text) for c in chunks)}")
check("positions croissantes", [c.start for c in chunks] == sorted(c.start for c in chunks))
check("fin du document couverte", chunks[-1].end >= len(doc) - 5)

print("\n8. classify_source_type — un cabinet d'études atteint le plancher de son champ (MSFT 2026-08-30)")
# Régression : `marche.croissance_marche_historique` a un plancher abaissé à B, mais AUCUNE source ne
# pouvait l'atteindre — les cabinets d'études tombaient en `web_search_generic` (C+/0.50). Le plancher
# et la table de domaines doivent se rejoindre, sinon le champ est infondable quel que soit l'émetteur.
_PLANCHER_MARCHE = FIELD_PLANCHER_OVERRIDES["marche.croissance_marche_historique"]
for dom in ("srgresearch.com", "canalys.com", "gartner.com", "idc.com", "techinsights.com"):
    st = classify_source_type(f"https://www.{dom}/articles/cloud-market-q2-2026")
    score, tier, _ = compute_reliability(st, entry_type="fact_qualitative")
    check(f"{dom} → {st} ({tier}) ≥ plancher {_PLANCHER_MARCHE}",
          st == "web_search_reputable" and _tier_ge(tier, _PLANCHER_MARCHE),
          f"→ {st}/{tier}/{score}")
check("un blog quelconque reste generic (la liste n'est pas un passe-droit)",
      classify_source_type("https://cloudblogexample.io/2026/cloud-market") == "web_search_generic")
check("la presse financière garde la priorité sur la liste réputée",
      classify_source_type("https://www.reuters.com/technology/cloud") == "financial_press")
check("un dépôt EDGAR reste au-dessus de tout", classify_source_type(EDGAR) == "edgar_official")

print(f"\n{'='*60}\n{ok} OK / {fail} KO")
sys.exit(1 if fail else 0)
