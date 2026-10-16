"""Provenance vérifiée + recherche intra-document — hors ligne, aucune clé ni réseau.

Quatre blocs :
  1. `RetrievalLog` : ce que les outils ont réellement rapporté, et sa forme canonique d'URL.
  2. `_verify_provenance` / `_cited_documents` : les deux garde-fous appliqués dans `_normalise_entry`.
  3. `document_search.select_relevant` : la sélection par pertinence, en mode dégradé lexical
     (l'embedding n'est pas joignable hors ligne — c'est justement le repli qu'on veut voir marcher).
  4. `focus` (§9-§12) : l'ouvrier dit ce qu'il cherche DANS le document, dans les mots du document —
     et la moitié du budget de restitution lui est dédiée (prompt search-worker §12).
"""
import asyncio
import hashlib
import sys

sys.path.insert(0, ".")

import app.agents.v2.tools as tools_mod  # noqa: E402
import app.knowledge.websearch as websearch_mod  # noqa: E402
from app.agents.v2.common import FIELD_PROFILES  # noqa: E402
from app.agents.v2.curator import _tier_ge  # noqa: E402
from app.agents.v2.tools import RetrievalLog, canonical_url  # noqa: E402
from app.agents.v2.worker import _cited_documents, _normalise_entry, _verify_provenance  # noqa: E402
from app.contracts import WorkerRequest  # noqa: E402
from app.db.migrations._gen_025 import PROMPTS, SEARCH_WORKER_TOOLS  # noqa: E402
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
        # "FAIL" (pas seulement "✗") : c'est le motif que `checks/_negatif.sh` grep pour vérifier
        # qu'une mutation rougit sur l'assert NOMMÉ — sans lui, ce fichier resterait indétectable
        # par le harnais de test négatif quel que soit l'assert visé.
        print(f"  ✗ FAIL {label} {detail}")


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
    # #79 — deux dates NOMMÉES, jamais une. Le fait est la clôture de l'exercice ; le document
    # est le 10-K qui le dépose un mois plus tard. Les garder DISTINCTS est ce qui rend la
    # fixture discriminante : les confondre rendrait la dérivation invisible.
    "portee_temporelle": "constatee",
    "date_du_fait": "2026-01-25",
    "date_du_document": "2026-02-25",
    "reliability_note": "dépôt officiel",
}

_EXTRAIT = "Two direct customers accounted for 22% and 14% of total revenue"
raw_edgar["extraits"] = [_EXTRAIT]

e = _normalise_entry(dict(raw_edgar), req, log)
# #126 (2026-10-15) : une citation dont le document n'a pas été lu n'est plus rétrogradée en
# `llm_memory` — elle est REFUSÉE, parce que ses extraits ne se retrouvent dans aucun texte rapporté.
# La protection de #28 tient toujours, plus strictement : une adresse plausible n'entre plus du tout.
check("URL jamais récupérée → fiche refusée (ses extraits ne se vérifient contre rien)", e is None,
      f"→ {e and e['source_type']}")

log2 = RetrievalLog()
log2.record(EDGAR, "full")
log2.record_text(EDGAR, f"Concentration of revenue. {_EXTRAIT}, primarily attributable to the "
                        "Compute & Networking segment.")
e = _normalise_entry(dict(raw_edgar), req, log2) or {}
check("URL réellement récupérée, extrait retrouvé → edgar_official conservé",
      e.get("source_type") == "edgar_official")
check("score plein rendu", e.get("reliability_score", 0) > 0.90, f"→ {e.get('reliability_score')}")
check("aucune revue humaine imposée", e.get("requires_human_review") is False)

# Une entrée = un document (#28) : des extraits vérifiés contre UNE adresse ne peuvent pas mêler deux
# documents, même s'ils NOMMENT un autre dépôt (un 10-Q renvoie couramment au 10-K) ; la règle ne
# garde plus que la restitution de mémoire, dont la prose est le seul contenu.
renvoi = dict(raw_edgar, extraits=[f"{_EXTRAIT}"],
              content="Le 10-K FY2026 et la mise à jour Q1 FY2027 (10-Q) indiquent la concentration.")
e = _normalise_entry(renvoi, req, log2) or {}
check("fiche à extraits vérifiés → jamais marquée multi-documents",
      e.get("requires_human_review") is False, f"→ {e.get('reliability_note')}")
multi = dict(raw_edgar, source_type="llm_memory", extraits=[], model_cutoff="2026-01",
             content="Le 10-K FY2026 et la mise à jour Q1 FY2027 (10-Q) indiquent : 'Some of our customers…'")
e = _normalise_entry(multi, req, log2) or {}
check("restitution de mémoire multi-documents → revue humaine", e.get("requires_human_review") is True)
check("désignations listées dans la note",
      "10-K" in e.get("reliability_note", "") and "10-Q" in e.get("reliability_note", ""))

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
# Lu dans `FIELD_PROFILES`, détenteur unique du plancher par champ depuis la capacité 4
# (`curator.FIELD_PLANCHER_OVERRIDES`, la seconde table, a été supprimée — #46).
_PLANCHER_MARCHE = FIELD_PROFILES["marche.croissance_marche_historique"]["plancher"]
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

print("\n9. select_relevant — `focus` : chercher DANS le document par ses propres mots (#27, §12)")
# Document synthétique calqué en FORME sur le cas réel (circulaire DEF 14A NVIDIA, 2026-10-16) :
# beaucoup de prose qui partage des mots avec le mandat (compensation, directors, executives,
# NVIDIA…), PUIS une ligne de tableau d'actionnariat qui n'en partage PRESQUE AUCUN — seul son
# intitulé (« Security Ownership of Certain Beneficial Owners and Management ») la rend trouvable.
_MANDAT_9 = (
    "compensation des dirigeants NVIDIA, composition du comite de remuneration, administrateurs, "
    "say-on-pay, indemnites de depart, actions attribuees aux cadres executifs"
)
_TITRE_TABLEAU = "Security Ownership of Certain Beneficial Owners and Management"
_LIGNE_TABLEAU = "Jen-Hsun Huang\t\t870,604,104\t\t—\t\t870,604,104\t\t3.58%"
_NARRATION_9 = (
    "The Compensation Committee reviewed executive compensation for the named executive "
    "officers. The Board of Directors approved the compensation program for NVIDIA's "
    "management team, including say-on-pay provisions and severance arrangements for "
    "senior executives. "
) * 10
_DOC_9 = _NARRATION_9 * 3 + "\n\n" + _TITRE_TABLEAU + ".\n" + _LIGNE_TABLEAU + "\n\n" + _NARRATION_9 * 3

sans_focus = asyncio.run(document_search.select_relevant(_DOC_9, _MANDAT_9, max_chars=3000))
check("a. sans `focus`, la ligne de tableau N'EST PAS sélectionnée (fixture discriminante)",
      _LIGNE_TABLEAU not in sans_focus["text"])

avec_focus = asyncio.run(
    document_search.select_relevant(_DOC_9, _MANDAT_9, max_chars=3000, focus=_TITRE_TABLEAU)
)
check("b. avec `focus` = l'intitulé, la ligne de tableau EST sélectionnée",
      _LIGNE_TABLEAU in avec_focus["text"])
_origines_9 = {s.get("origine") for s in avec_focus["spans"]}
check("c. au moins un span vient de la question ET un du focus (budget partagé, pas fusionné)",
      "question" in _origines_9 and "chercher" in _origines_9, f"→ {_origines_9}")
check("d. `focus=None` rend un résultat IDENTIQUE à un appel sans le paramètre",
      asyncio.run(document_search.select_relevant(_DOC_9, _MANDAT_9, max_chars=3000, focus=None))
      == sans_focus)
check("e. `chars_returned` reste sous le budget avec `focus`",
      avec_focus["chars_returned"] <= 3000, f"→ {avec_focus['chars_returned']}")

print("\n10. select_relevant — chemin relevance (embedding bouchonné, déterministe, hors ligne)")
# bge-m3 n'est pas joignable hors ligne : on bouchonne `embeddings` par un bag-of-words haché dans un
# petit vecteur — assez pour discriminer la fixture, et ça permet de COMPTER les appels HTTP évités.
_DIM_10 = 32


def _vecteur_bow(texte: str) -> list:
    vec = [0.0] * _DIM_10
    for w in document_search._WORD.findall(texte.lower()):
        vec[int(hashlib.md5(w.encode()).hexdigest(), 16) % _DIM_10] += 1.0
    return vec


_appels_embed_texts: list = []


async def _faux_embed_texts(textes, **kw):
    _appels_embed_texts.append((len(textes), bool(kw.get("is_query"))))
    return [_vecteur_bow(t) for t in textes]


async def _faux_embed_one(texte, **kw):
    return _vecteur_bow(texte)


_vrai_cfg = document_search.embeddings.is_configured
_vrai_et = document_search.embeddings.embed_texts
_vrai_eo = document_search.embeddings.embed_one
document_search.embeddings.is_configured = lambda: True
document_search.embeddings.embed_texts = _faux_embed_texts
document_search.embeddings.embed_one = _faux_embed_one
try:
    _appels_embed_texts.clear()
    relevance = asyncio.run(
        document_search.select_relevant(_DOC_9, _MANDAT_9, max_chars=3000, focus=_TITRE_TABLEAU)
    )
    check("f. chemin relevance : mode déclaré 'relevance'", relevance["mode"] == "relevance")
    check("f. chemin relevance : ligne de tableau sélectionnée", _LIGNE_TABLEAU in relevance["text"])
    _chunks_9 = [a for a in _appels_embed_texts if not a[1]]
    check("f. chemin relevance : les chunks ne sont embeddés qu'UNE fois pour deux requêtes",
          len(_chunks_9) == 1, f"→ appels {_appels_embed_texts}")
    check("f. chemin relevance : les requêtes portent l'instruction de requête (is_query)",
          (2, True) in _appels_embed_texts, f"→ appels {_appels_embed_texts}")
finally:
    document_search.embeddings.is_configured = _vrai_cfg
    document_search.embeddings.embed_texts = _vrai_et
    document_search.embeddings.embed_one = _vrai_eo

print("\n11. exec_fetch_url / fetch_url / _finalise — `chercher` transmis de bout en bout")
_captures_11: dict = {}


async def _stub_fetch_url_g(url, *, query=None, chercher=None, ticker_id=None, max_chars=None):
    _captures_11["chercher"] = chercher
    return {"url": url, "final_url": url, "status": 200, "title": "", "text": "x", "via": "direct"}


_reel_fetch = tools_mod.fetch_url
tools_mod.fetch_url = _stub_fetch_url_g
try:
    asyncio.run(tools_mod.exec_fetch_url(
        {"url": "https://x.com/a", "chercher": _TITRE_TABLEAU}, query=_MANDAT_9
    ))
    check("g. exec_fetch_url : `chercher` transmis tel quel à fetch_url",
          _captures_11.get("chercher") == _TITRE_TABLEAU)
    asyncio.run(tools_mod.exec_fetch_url({"url": "https://x.com/a", "chercher": "   "}, query=_MANDAT_9))
    check("g. exec_fetch_url : `chercher` blanc devient None", _captures_11.get("chercher") is None)
    asyncio.run(tools_mod.exec_fetch_url({"url": "https://x.com/a"}, query=_MANDAT_9))
    check("g. exec_fetch_url : `chercher` absent devient None", _captures_11.get("chercher") is None)
finally:
    tools_mod.fetch_url = _reel_fetch


async def _stub_direct_h(url, ticker_id=None):
    return {
        "url": url, "final_url": url, "status": 200, "content_type": "text/html",
        "title": "Titre", "text": _DOC_9, "source_type_max": "web_search_generic", "via": "direct",
    }


_reel_direct = websearch_mod._fetch_url_direct
websearch_mod._fetch_url_direct = _stub_direct_h
try:
    out_h = asyncio.run(
        websearch_mod.fetch_url(
            "https://x.com/doc", query=_MANDAT_9, chercher=_TITRE_TABLEAU, max_chars=3000
        )
    )
    check("h. fetch_url/_finalise : `chercher` atteint select_relevant (ligne de tableau rendue)",
          _LIGNE_TABLEAU in out_h["text"])
    check("h. fetch_url/_finalise : `extract.chercher` rapporte ce qui a été demandé",
          out_h["extract"].get("chercher") == _TITRE_TABLEAU, f"→ {out_h['extract'].get('chercher')}")
finally:
    websearch_mod._fetch_url_direct = _reel_direct

print("\n12. tools_json (migration 025) et prompt (règle 12) portent `chercher`")
_fetch_tool_12 = next(t for t in SEARCH_WORKER_TOOLS if t["function"]["name"] == "fetch_url")
check("i. tools_json fetch_url déclare `chercher`",
      "chercher" in _fetch_tool_12["function"]["parameters"]["properties"])
check("i. `chercher` reste FACULTATIF (absent de `required`)",
      "chercher" not in _fetch_tool_12["function"]["parameters"].get("required", []))
_consigne_12 = (PROMPTS / "11-search-worker.md").read_text()
check("j. le prompt search-worker porte la règle 12 (marqueur)",
      "CHERCHER DANS UN LONG DOCUMENT" in _consigne_12)

print(f"\n{'='*60}\n{ok} OK / {fail} KO")
sys.exit(1 if fail else 0)
