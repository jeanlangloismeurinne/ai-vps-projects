"""Vérification des garde-fous déterministes du search-worker (sans appel réseau ni modèle).

On simule une sortie de modèle HOSTILE : source surqualifiée, score gonflé, mauvais entry_type,
doublons, dépassement de plafond, mémoire modèle non déclarée. Tout doit être rabattu côté Python.
"""
import ast
import sys
import textwrap
from datetime import date

from app.agents.v2.worker import (
    _apply_deterministic_overrides, _build_user_message, _resolve_source_type, request_hash,
    titre_de_fiche,
)
# Les 8 colonnes archivées par la 036, lues sur leur détenteur (#46).
from app.db.migrations._gen_036 import COLONNES_RETIREES
from app.agents.v2.tools import RetrievalLog
from pydantic import ValidationError

from app.contracts import OutputSchema, WorkerExchange, WorkerRequest, WorkerResponse
from app.contracts.worker_delegation_schema import TAG_LECTURE, est_lecture_du_collecteur
from app.knowledge.websearch import (
    SearchUnavailable, classify_source_type, get_search_backend, html_to_text,
    issuer_domains_for,
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


print("\n1. classify_source_type — plafond par domaine")
cases = {
    "https://www.sec.gov/Archives/edgar/data/1045810/x.htm": "edgar_official",
    "https://ir.nvidia.com/news/press-release": "company_ir_official",
    "https://investor.tesla.com/x": "company_ir_official",
    "https://www.reuters.com/technology/x": "financial_press",
    "https://lesechos.fr/x": "financial_press",
    "https://www.amf-france.org/x": "regulator_filing_eu",
    "https://blog.random-guy.dev/nvidia-moat": "web_search_generic",
    # Sans ticker, le site d'un émetteur n'est plus « réputé » : ce plafond se mérite désormais
    # émetteur par émetteur (#31), pas depuis une constante globale. Cf. §1bis.
    "https://nvidia.com/fr-fr/data-center/": "web_search_generic",
    None: "llm_memory",
}
for url, expected in cases.items():
    got = classify_source_type(url)
    check(f"{str(url)[:52]:<54} → {got}", got == expected, f"attendu {expected}")

print("\n1bis. Domaines d'émetteur — clefés par ticker, jamais globaux (#31)")
# Le défaut de généralité corrigé le 2026-08-31 : `nvidia.com` était en dur dans
# `_REPUTABLE_SUFFIXES` et Microsoft n'avait rien, si bien que microsoft.com/en-us/investor/ — de
# l'IR officiel — tombait en `web_search_generic` (0.50) au lieu de `company_ir_official` (0.90).
check("chemin IR de l'émetteur analysé → company_ir_official (cas Microsoft)",
      classify_source_type("https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4", "MSFT")
      == "company_ir_official")
check("site de l'émetteur hors section IR → web_search_reputable",
      classify_source_type("https://nvidia.com/fr-fr/data-center/", "NVDA")
      == "web_search_reputable")
check("registre insensible à la casse du ticker",
      classify_source_type("https://nvidia.com/x", "nvda") == "web_search_reputable")

# Le point qui compte : le privilège ne FUIT PAS d'un émetteur à l'autre. Sur une analyse MSFT,
# nvidia.com est le site marketing d'un concurrent, pas une source primaire.
check("le domaine d'un émetteur ne vaut rien pour un AUTRE émetteur",
      classify_source_type("https://nvidia.com/fr-fr/data-center/", "MSFT")
      == "web_search_generic")
check("chemin IR sur un domaine tiers → aucune promotion (pas de /investor/ magique)",
      classify_source_type("https://unblogquelconque.com/investor/msft-analyse", "MSFT")
      == "web_search_generic")
check("ticker inconnu → aucun domaine d'émetteur, donc aucune promotion héritée",
      classify_source_type("https://microsoft.com/en-us/investor/", "AAPL")
      == "web_search_generic")
check("issuer_domains_for rend un tuple vide pour un ticker non enregistré",
      issuer_domains_for("AAPL") == () and issuer_domains_for(None) == ())

# Non-régression : le sous-domaine `ir.` reste GÉNÉRIQUE. Le restreindre au registre ferait tomber
# l'IR d'un concurrent de 0.90 à 0.50 sur toute analyse — un faux trou de couverture creusé par le
# correctif censé en boucher un (#32).
check("ir.<concurrent>.com reste company_ir_official sur une analyse MSFT",
      classify_source_type("https://ir.nvidia.com/news/press-release", "MSFT")
      == "company_ir_official")
check("sec.gov prime sur le registre d'émetteur",
      classify_source_type("https://www.sec.gov/Archives/edgar/data/789019/x.htm", "MSFT")
      == "edgar_official")
check("le mandat porte l'émetteur jusqu'à _resolve_source_type",
      _resolve_source_type("web_search_generic",
                           "https://www.microsoft.com/en-us/investor/", "MSFT")
      == "company_ir_official")

print("\n2. _resolve_source_type — le domaine tranche, sauf aveu llm_memory")
check("edgar sur-déclaré sur un blog → web_search_generic",
      _resolve_source_type("edgar_official", "https://blog.x.dev/p") == "web_search_generic")
check("IR sous-déclaré en générique → company_ir_official (le domaine corrige)",
      _resolve_source_type("web_search_generic", "https://ir.nvidia.com/x") == "company_ir_official")
check("llm_memory déclaré sur sec.gov → llm_memory (l'aveu prime sur le domaine)",
      _resolve_source_type("llm_memory", "https://www.sec.gov/x") == "llm_memory")
check("source_type inventé → qualification du domaine",
      _resolve_source_type("mon_source_type", "https://www.reuters.com/x") == "financial_press")

print("\n2bis. Câblage réel : le ticker du mandat atteint-il les outils ?")
# Une table de domaines correcte ne sert à rien si `ticker_id` n'arrive pas jusqu'à l'appel. C'est
# LE défaut que §1bis ne peut pas voir : on remplace le backend de recherche par un bouchon et on
# regarde ce que l'exécuteur annonce réellement au modèle dans `source_type_max`.
import asyncio  # noqa: E402

from app.agents.v2 import tools as _tools  # noqa: E402
from app.knowledge.websearch import SearchHit  # noqa: E402

_IR_MSFT = "https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4"


async def _stub_web_search(query, max_results=5, ticker_id=None):
    return [SearchHit(title="Earnings", url=_IR_MSFT, snippet="…")]


_reel = _tools.web_search
_tools.web_search = _stub_web_search
try:
    execs = _tools.build_tool_executors(ticker_id="MSFT", query="revenus Microsoft Cloud")
    res = asyncio.run(execs["web_search"]({"query": "microsoft investor relations revenus"}))
    annonce = (res.get("results") or [{}])[0].get("source_type_max")
    check(f"web_search annonce {annonce!r} sur l'IR de l'émetteur analysé",
          annonce == "company_ir_official",
          "le ticker du mandat ne descend pas jusqu'à classify_source_type")

    # Même bouchon, même URL, mais le mandat porte sur un AUTRE émetteur.
    execs_autre = _tools.build_tool_executors(ticker_id="NVDA", query="marché des GPU")
    res_autre = asyncio.run(execs_autre["web_search"]({"query": "microsoft investor relations"}))
    annonce_autre = (res_autre.get("results") or [{}])[0].get("source_type_max")
    check(f"le même lien vaut {annonce_autre!r} quand le mandat porte sur un autre émetteur",
          annonce_autre == "web_search_generic")
finally:
    _tools.web_search = _reel

print("\n3. _apply_deterministic_overrides — sortie de modèle hostile")
req = WorkerRequest(
    requester="knowledge-curator", worker="search-worker", ticker_id="NVDA",
    query="Preuves de switching costs CUDA",
    output_schema=OutputSchema(entry_type="fact_qualitative", dimension="moat",
                               field_path="moat.preuves"),
    reliability_min=0.60, max_entries=2,
)
_TEXTES_LUS = {'https://blog.random-guy.dev/cuda': 'developers told us they feel locked into the CUDA ecosystem', 'https://www.reuters.com/tech/cuda': 'rewriting kernels away from CUDA carries significant engineering costs', 'https://www.sec.gov/x': 'revenue for fiscal year 2026 was $130.5 billion', 'https://ir.nvidia.com/ecosystem': 'the CUDA developer ecosystem now counts millions of developers', 'https://lesechos.fr/cuda': "l'outillage propriétaire de NVIDIA reste difficile à répliquer"}
hostile = {
    "request_hash": "peu importe",
    "worker": "search-worker",
    "status": "found",
    # #79 — chaque entry DÉCLARE sa datation (deux dates nommées), sinon l'ouvrier la rejette
    # AVANT tout le reste. Les dates du fait et du document sont tenues DISTINCTES : les faire
    # coïncider rendrait la dérivation `source_date` indiscernable d'une recopie, et le rejet
    # des entries (a)/(c) doit être prononcé par SA règle — plancher, type — jamais par la
    # datation (un refus prononcé par une autre règle est un faux vert, cf. #56).
    "entries": [
        # a) source surqualifiée + score gonflé sur un blog → doit tomber sous le plancher
        {"entry_type": "fact_qualitative", "title": "CUDA lock-in", "content": "Blog affirmant un lock-in.",
         "source_type": "edgar_official", "source_url": "https://blog.random-guy.dev/cuda",
         "extraits": ["developers told us they feel locked into the CUDA ecosystem"],
         "portee_temporelle": "constatee", "date_du_fait": "2026-06-30",
         "date_du_document": "2026-07-02",
         "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "source officielle"},
        # b) presse financière, score gonflé → recalculé à 0.75
        {"entry_type": "fact_qualitative", "title": "Coût de migration hors CUDA",
         "content": "Reuters rapporte des coûts de réécriture de kernels significatifs.",
         "source_type": "financial_press", "source_url": "https://www.reuters.com/tech/cuda",
         "extraits": ["rewriting kernels away from CUDA carries significant engineering costs"],
         "portee_temporelle": "constatee", "date_du_fait": "2026-07-10",
         "date_du_document": "2026-07-14", "reliability_score": 0.99, "reliability_tier": "A",
         "reliability_note": "je suis confiant"},
        # c) mauvais entry_type → rejet
        {"entry_type": "fact_financial", "title": "CA FY26", "content": "130 Md$",
         "source_type": "edgar_official", "source_url": "https://www.sec.gov/x",
         "extraits": ["revenue for fiscal year 2026 was $130.5 billion"],
         "portee_temporelle": "constatee", "date_du_fait": "2026-01-25",
         "date_du_document": "2026-02-25",
         "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "10-K"},
        # d) doublon exact de (b) — mêmes dates, sinon ce ne serait plus un doublon
        {"entry_type": "fact_qualitative", "title": "Coût de migration hors CUDA",
         "content": "Reuters rapporte des coûts de réécriture de kernels significatifs.",
         "source_type": "financial_press", "source_url": "https://www.reuters.com/tech/cuda",
         "extraits": ["rewriting kernels away from CUDA carries significant engineering costs"],
         "portee_temporelle": "constatee", "date_du_fait": "2026-07-10",
         "date_du_document": "2026-07-14", "reliability_score": 0.99, "reliability_tier": "A",
         "reliability_note": "doublon"},
        # e) IR officiel → 0.90, doit finir premier au tri. C'est aussi le cas `indatable` du
        #    vocabulaire #79 : une page décrivant l'ampleur d'un écosystème n'affirme aucune
        #    date de fait. `source_date` y est donc NULL — l'absence est le RÉSULTAT, pas un
        #    échec —, la décote d'âge ne mord pas, et le 0.90 lu ici est bien la promotion par
        #    le domaine et rien d'autre.
        {"entry_type": "fact_qualitative", "title": "Écosystème CUDA",
         "content": "Page IR NVIDIA décrivant l'ampleur de l'écosystème développeurs.",
         "source_type": "web_search_generic", "source_url": "https://ir.nvidia.com/ecosystem",
         "extraits": ["the CUDA developer ecosystem now counts millions of developers"],
         "portee_temporelle": "indatable", "date_du_document": "2026-06-01",
         "datation_motif": "description stable d'un écosystème, aucune date de fait affirmée",
         "reliability_score": 0.50, "reliability_tier": "C+", "reliability_note": "prudent"},
        # f) 3ᵉ entry valide → doit être tronquée (max_entries=2)
        {"entry_type": "fact_qualitative", "title": "Barrière outillage",
         "content": "Les Échos : outillage propriétaire difficile à répliquer.",
         "source_type": "financial_press", "source_url": "https://lesechos.fr/cuda",
         "extraits": ["l'outillage propriétaire de NVIDIA reste difficile à répliquer"],
         "portee_temporelle": "constatee", "date_du_fait": "2026-04-02",
         "date_du_document": "2026-04-08",
         "reliability_score": 0.75, "reliability_tier": "B+", "reliability_note": "presse"},
    ],
    "uncovered_fields": [],
    "execution": {"tier": "ouvrier", "model_used": "je-mens", "tokens_in": 999999,
                  "tokens_out": 999999, "cost_usd": 42.0},
}
# #126 — le journal du run : chaque adresse a rapporté un texte qui CONTIENT l'extrait de son entry
# (le refus des entries (a)/(c) doit rester prononcé par SA règle — plancher, type —, jamais par les
# extraits : un refus prononcé par une autre règle est un faux vert, #56).
LOG = RetrievalLog()
for _u, _q in _TEXTES_LUS.items():
    LOG.record(_u, "full")
    LOG.record_text(_u, f"Préambule de la page. {_q}. Suite de la page.")
out = _apply_deterministic_overrides(
    hostile, req, model_used="deepseek-ai/DeepSeek-V4-Flash-0731",
    tokens_in=1200, tokens_out=800, cost_usd=0.000240, log=LOG,
)
# Chaque fiche est suivie de la LECTURE du collecteur, rangée à part (#126) : les asserts de cette
# section portent sur les fiches ; les lectures ont leur section (§3bis).
toutes = out["entries"]
entries = [e for e in toutes if TAG_LECTURE not in e["tags"]]
check(f"plafond max_entries=2 respecté (obtenu {len(entries)})", len(entries) == 2)
urls = [e["source_url"] for e in entries]
check("blog surqualifié écarté (score 0.50 < plancher 0.60)",
      "https://blog.random-guy.dev/cuda" not in urls)
check("entry de mauvais type rejetée", not any(e["entry_type"] != "fact_qualitative" for e in entries))
check("doublon dédupliqué", urls.count("https://www.reuters.com/tech/cuda") <= 1)
check("IR NVIDIA promu par le domaine et classé 1er (0.90)",
      entries[0]["source_url"] == "https://ir.nvidia.com/ecosystem"
      and entries[0]["source_type"] == "company_ir_official"
      and entries[0]["reliability_score"] == 0.90,
      f"→ {entries[0]['source_type']} {entries[0]['reliability_score']}")
# La 2ᵉ est de la presse DATÉE (#79) : son 0.75 de base porte la décote d'âge, qui bouge avec
# le jour où le check tourne — d'où la fenêtre, comme le `≤` de check_provenance. Ce que
# l'assert tient vraiment est l'ORDRE et les deux bases, pas une décimale.
check("troncature = les 2 MIEUX notées, pas les 2 premières venues",
      entries[0]["reliability_score"] == 0.90
      and 0.73 <= entries[1]["reliability_score"] <= 0.75
      and entries[0]["reliability_score"] > entries[1]["reliability_score"],
      f"→ {[e['reliability_score'] for e in entries]}")

# Même sortie, plafond desserré : on voit alors le recalcul de score sur chaque entry retenue.
large = _apply_deterministic_overrides(
    hostile, req.model_copy(update={"max_entries": 10}),
    model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0, log=LOG,
)
reuters = next((e for e in large["entries"] if "reuters" in (e["source_url"] or "")), None)
check("score Reuters gonflé 0.99 → recalculé à la baseline presse, décote d'âge comprise",
      reuters is not None and 0.70 < reuters["reliability_score"] < 0.75,
      f"→ {reuters and reuters['reliability_score']}")
check("aucun score conservé du modèle dans la sortie élargie",
      all(e["reliability_score"] <= 0.90 for e in large["entries"]),
      f"→ {[e['reliability_score'] for e in large['entries']]}")
# _COUVERTURE_NON_CABLEE — écart déclaré, sur la forme de #52 : il vit dans le check du lot qui l'a
# créé et virera au vert de lui-même le jour du câblage. `_resolve_covers` forçait ici le
# `field_path` du mandat dans `entry["covers"]` ; la 036 archive la colonne, parce que la couverture
# est une propriété de la RELATION entry ↔ question (#57) et que ce lien s'écrit au DISPATCH, comme
# sous-produit déterministe (#58) — pas au retour d'un agent qui rédige.
# ⚠️ Ce qui se garde ici n'est pas l'absence d'un mot : un grep d'interdit se satisfait de la prose
# et se met en défaut sur elle (#56). C'est la STRUCTURE de l'entry produite — le worker rend une
# ligne de `knowledge_entries` telle que la 036 la laisse, et le contrat `ProducedEntry` est
# `extra="forbid"`, donc y remettre une clef ferait rejeter TOUTE entry par le filet de validation.
_COUVERTURE_NON_CABLEE = sorted(set(COLONNES_RETIREES) & set().union(*(set(e) for e in toutes)))
check("aucune entry produite ne porte une colonne archivée par la 036",
      _COUVERTURE_NON_CABLEE == [], f"→ {_COUVERTURE_NON_CABLEE}")
check("le mandat porte toujours son champ (le worker SAIT ce qu'il couvre, il ne l'écrit plus)",
      req.output_schema.field_path == "moat.preuves",
      "→ si le dispatch du lot 2c est câblé, c'est ce champ qu'il relie, et cette section change")
check("note de fiabilité jamais muette et traçant le calcul",
      all("base " in e["reliability_note"] for e in entries))
check("exécution mesurée, pas déclarée (le modèle disait 42 $)",
      out["execution"]["cost_usd"] == 0.00024 and out["execution"]["tokens_in"] == 1200,
      f"→ {out['execution']}")
check("status recalculé = found", out["status"] == "found", f"→ {out['status']}")

print("\n4. Validation de contrat (le filet, après correction)")
# Un refus du filet est un FAIL NOMMÉ, jamais la mort du script avant son bilan (2ᵉ faux vert).
try:
    resp = WorkerResponse.model_validate(out)
    exch = WorkerExchange(request=req, response=resp)
    _filet = exch.response.status == "found"
except ValidationError as e:
    _filet = False
    print(f"       refus du filet : {str(e)[:300]}")
check("WorkerResponse + WorkerExchange valident", _filet)
check("request_hash stable", request_hash(req) == request_hash(req.model_copy(deep=True)))

print("\n5. Tout écarté → not_found explicite (jamais muet, A6)")
req_div = req.model_copy(update={"divergent": True, "reliability_min": 0.99})
out2 = _apply_deterministic_overrides(
    dict(hostile), req_div, model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0, log=LOG,
)
check("status not_found", out2["status"] == "not_found", f"→ {out2['status']}")
check("uncovered_fields renseigné", out2["uncovered_fields"] == ["moat.preuves"],
      f"→ {out2['uncovered_fields']}")
try:
    WorkerExchange(request=req_div, response=WorkerResponse.model_validate(out2))
    _a6 = True
except ValidationError as e:
    _a6 = str(e)[:300]
check("mandat divergent sans résultat : l'invariant croisé A6 passe", _a6 is True, f"→ {_a6}")

print("\n6. llm_memory — P2 imposé même si le modèle l'oublie")
req_mem = req.model_copy(update={"reliability_min": 0.0})
out3 = _apply_deterministic_overrides(
    # Un souvenir de modèle n'affirme aucune date : `indatable` (#79), donc `source_date` NULL
    # et aucune décote d'âge — le 0.40 lu plus bas est le plancher llm_memory, rien d'autre.
    {"entries": [{"entry_type": "fact_qualitative", "title": "De mémoire",
                  "content": "CUDA domine depuis longtemps.", "source_type": "llm_memory",
                  "extraits": [],
                  "portee_temporelle": "indatable",
                  "datation_motif": "restitution de mémoire, aucune date affirmée",
                  "reliability_score": 0.9, "reliability_tier": "A", "reliability_note": "sûr",
                  "requires_human_review": False}],
     "uncovered_fields": []},
    req_mem, model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0, log=RetrievalLog(),
)
e = out3["entries"][0]
check("requires_human_review forcé", e["requires_human_review"] is True)
check("model_cutoff renseigné", bool(e["model_cutoff"]))
check("score ramené à 0.40 / tier C", e["reliability_score"] == 0.40 and e["reliability_tier"] == "C",
      f"→ {e['reliability_score']} {e['reliability_tier']}")
# Arbitrage du 2026-10-18 : même un aveu `llm_memory` (sans extrait, donc sans document à nommer)
# ne garde PLUS le titre rédigé par le modèle (« De mémoire » ici) — ce chemin ÉCRIT en base dès
# que son score passe `reliability_min` (il le fait ici), donc le repli `raw.get("title")` était
# atteignable en production, pas seulement en théorie.
check("même en aveu `llm_memory` (aucun extrait), le titre est TOUJOURS `titre_de_fiche(url)` — "
      "jamais le titre rédigé par le modèle",
      e["title"] == titre_de_fiche(None) and e["title"] != "De mémoire", f"→ {e['title']!r}")
WorkerResponse.model_validate(out3)
check("ProducedEntry valide (P2 satisfait)", True)

print("\n7. fetch_url — extraction texte stdlib")
title, text = html_to_text(
    "<html><head><title>NVIDIA IR</title><style>.a{color:red}</style></head>"
    "<body><nav>menu accueil</nav><script>var x=1;</script>"
    "<h1>Résultats FY2026</h1><p>Le chiffre d'affaires atteint 130&nbsp;Md$.</p>"
    "<p>Marge brute&nbsp;: 75&nbsp;%.</p><footer>mentions</footer></body></html>"
)
check("titre extrait", title == "NVIDIA IR", f"→ {title!r}")
check("script/style/nav/footer écartés",
      "var x" not in text and "color:red" not in text and "menu accueil" not in text
      and "mentions" not in text, f"→ {text!r}")
check("contenu et entités conservés",
      "130" in text and "Md$" in text and "75" in text, f"→ {text!r}")
check("blocs séparés en lignes", text.count("\n") >= 2, f"→ {text!r}")

# 7bis — un TABLEAU (#132). Ligne COPIÉE du réel (circulaire DEF 14A NVIDIA du 2026-05-12, accession
# 0001045810-26-000036, styles retirés) : cellules vides, renvoi de note dans un <div>, espaces
# insécables. Avant : « Jen-Hsun Huang870,604,104 » — aucune citation propre d'une ligne de tableau ne
# passait la vérification mot pour mot, la fiche ne gardait que la phrase d'en-tête.
from app.knowledge.citation import extrait_introuvable  # noqa: E402
_LIGNE_DEF14A = (
    '<tr><td colspan="3"><span>Jen-Hsun Huang</span></td><td colspan="3"/><td colspan="2">'
    '<span>870,604,104&#160;</span></td><td/><td colspan="3"><div><span>(1)</span></div></td>'
    '<td colspan="3"/><td colspan="2"><span>&#8212;&#160;</span></td><td/><td colspan="3"/>'
    '<td colspan="2"><span>870,604,104&#160;</span></td><td/><td colspan="3"/><td colspan="3">'
    '<span>3.58%</span></td></tr>')
_, ttab = html_to_text(
    "<html><body><p>Percentages are based on 24,312,141,810 shares.</p><table>"
    "<tr><th>Name of Beneficial Owner</th><th>Shares Owned</th><th>Percent</th></tr>"
    + _LIGNE_DEF14A + "</table><p>* Represents less than 1%.</p>"
    # cellule jamais fermée (HTML implicite) : elle ne doit pas avaler les sauts de ligne qui suivent
    "<table><tr><td>Colette M. Kress<td>4,443,523<tr><td>Ajay K. Puri<td>3,266,897</table>"
    "<p>Paragraphe suivant.</p></body></html>")
check("#132 : une citation d'une ligne de tableau passe la vérification mot pour mot",
      extrait_introuvable(["Jen-Hsun Huang 870,604,104 (1) — 870,604,104 3.58%"], [ttab]) is None,
      f"→ {ttab!r}")
check("#132 : les cellules d'en-tête ne sont plus collées",
      extrait_introuvable(["Name of Beneficial Owner Shares Owned Percent"], [ttab]) is None, f"→ {ttab!r}")
check("#132 : une ligne de tableau tient sur une ligne (le renvoi de note ne la coupe pas)",
      any("Jen-Hsun Huang" in ln and "3.58%" in ln for ln in ttab.split("\n")), f"→ {ttab!r}")
check("#132 : une cellule non fermée ne fait pas déborder une ligne sur la suivante",
      not any("Colette M. Kress" in ln and "Ajay K. Puri" in ln for ln in ttab.split("\n")),
      f"→ {ttab!r}")
check("#132 : une cellule non fermée ne déborde pas sur le paragraphe suivant",
      "Paragraphe suivant." in ttab.split("\n"), f"→ {ttab!r}")
check("#132 : le texte hors tableau garde ses sauts de ligne",
      "* Represents less than 1%." in ttab.split("\n"), f"→ {ttab!r}")

print("\n8. Absence de clé = échec EXPLICITE (jamais 0 résultat muet)")
try:
    get_search_backend()
    check("SearchUnavailable levée sans EXA_API_KEY", False, "aucune exception !")
except SearchUnavailable as e:
    check("SearchUnavailable levée sans EXA_API_KEY", True)
    check("message actionnable (nomme la clé et où la poser)",
          "EXA_API_KEY" in str(e) and "Coolify" in str(e), f"→ {e}")

print("\n9. Ancrage temporel du mandat (F12) — le modèle doit connaître le PRÉSENT")
# Le message ne portait aucune date : le modèle datait donc le présent à sa coupure
# d'entraînement et citait un 10-K vieux d'un cycle annuel en le croyant le plus récent
# (RVMD, 2026-09-04). Ce qui se vérifie ici est ce qui PART vers le modèle — pas ce qu'il
# en fait, qui n'est mesurable que par un run réel.
_req_f12 = WorkerRequest(
    requester="knowledge-curator", worker="search-worker", ticker_id="RVMD",
    query="modèle d'affaires", output_schema=OutputSchema(
        entry_type="fact_qualitative", dimension="business_model",
        field_path="business_model.description"),
    reliability_min=0.60,
)

msg_sans_ancre = _build_user_message(_req_f12, None)
aujourdhui = date.today().isoformat()
check("la date du jour est dans le message", aujourdhui in msg_sans_ancre,
      f"→ {aujourdhui!r} absent")
check("la date est présentée comme le présent, pas comme une donnée de plus",
      "coupure" in msg_sans_ancre.lower(), "→ mention de la coupure d'entraînement absente")
# Un ticker sans dépôt connu ne doit pas produire un message SILENCIEUX sur l'ancre : une ancre
# absente et une ancre tue se lisent pareil côté modèle (cf. « un check qui dégrade en sortant à 0 »).
check("ancre absente = DITE, jamais tue",
      "INCONNUE" in msg_sans_ancre, "→ l'absence d'ancre ne s'annonce pas")

msg_ancre = _build_user_message(
    _req_f12, {"source_date": date(2026, 6, 30), "fiscal_period": "FY2025",
               "source_url": "https://www.sec.gov/x"})
check("l'ancre de dépôt connue est transmise", "2026-06-30" in msg_ancre, f"→ absente")
check("l'exercice de l'ancre est transmis", "FY2025" in msg_ancre)
check("une source antérieure à l'ancre est explicitement disqualifiée",
      "ANTÉRIEURE" in msg_ancre, "→ aucune consigne sur les sources périmées")
check("les deux branches restent distinctes",
      "INCONNUE" not in msg_ancre, "→ le message avec ancre annonce aussi une ancre inconnue")
# Le contrat lui-même ne doit pas avoir bougé : l'ancrage s'AJOUTE au mandat, il ne le remplace pas.
check("le WorkerRequest part toujours en JSON dans le message",
      '"field_path": "business_model.description"' in msg_ancre,
      "→ le mandat n'est plus transmis intégralement")

print("\n10. Le drapeau de provenance ATTEINT le stockage (F13)")
# `_verify_provenance` calculait `requires_human_review`, l'API le renvoyait, et
# `persist_worker_entries` ne le passait pas à `store_knowledge` : le drapeau mourait entre la
# réponse HTTP et la base. On ne vérifie donc pas qu'il est CALCULÉ (§5 le fait déjà) mais qu'il
# est TRANSMIS — c'est-à-dire l'appel réellement émis vers la couche de stockage.
import inspect

import app.agents.v2.worker as _w

_src_persist = inspect.getsource(_w.persist_worker_entries)
check("persist_worker_entries transmet requires_human_review",
      "requires_human_review=" in _src_persist,
      "→ le drapeau est calculé puis perdu à l'écriture")
# Le paramètre doit exister côté stockage, sinon la transmission serait un TypeError en prod —
# et un check qui ne lit que l'appelant validerait un appel impossible.
_params_store = inspect.signature(_w.store_knowledge).parameters
check("store_knowledge expose bien ce paramètre",
      "requires_human_review" in _params_store,
      f"→ paramètres : {list(_params_store)}")
check("le défaut côté stockage reste False (le drapeau s'ajoute, ne s'impose pas)",
      _params_store["requires_human_review"].default is False,
      f"→ défaut = {_params_store['requires_human_review'].default!r}")
# Les autres champs décidés par les overrides déterministes doivent suivre le même chemin :
# un seul oubli de ce genre suffit à vider un garde-fou de sa portée (#28, #29).
# ⚠️ `covers` a quitté cette liste avec la 036 : le transmettre lèverait, `store_knowledge` ne
# l'accepte plus. Les trois autres restent, mais l'assert change de nature. `f"{champ}=" in source`
# est un grep de PRÉSENCE, donc satisfait par la prose (#56) — et ce module contient précisément un
# commentaire qui écrit « Plus de `covers=` ». On lit donc la STRUCTURE : les mots-clefs réellement
# passés à `store_knowledge`, extraits par `ast`, qu'aucun commentaire ne peut fabriquer.
_appel_store = next(
    (n for n in ast.walk(ast.parse(textwrap.dedent(_src_persist)))
     if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "store_knowledge"),
    None)
check("l'appel à `store_knowledge` est trouvé dans `persist_worker_entries`",
      _appel_store is not None, "→ sans lui les asserts suivants seraient verts sur rien")
_kw_store = {k.arg for k in (_appel_store.keywords if _appel_store else []) if k.arg}
for _champ in ("source_type", "source_url", "fiscal_period", "requires_human_review"):
    check(f"{_champ} transmis au stockage (mot-clef réel, pas une mention en commentaire)",
          _champ in _kw_store, f"→ décidé côté Python mais jamais écrit — vus : {sorted(_kw_store)}")
    check(f"… et `store_knowledge` expose bien `{_champ}`", _champ in _params_store,
          "→ transmis à un paramètre inexistant : TypeError en prod")
# Les colonnes archivées, dans les DEUX sens : ni transmises par l'appelant, ni acceptées par le
# stockage. Un seul des deux laisserait passer la moitié du défaut.
_kw_mortes = sorted(set(COLONNES_RETIREES) & _kw_store)
_params_morts = sorted(set(COLONNES_RETIREES) & set(_params_store))
check("aucune colonne archivée n'est transmise au stockage", _kw_mortes == [], f"→ {_kw_mortes}")
check("… et `store_knowledge` n'en accepte plus aucune", _params_morts == [], f"→ {_params_morts}")


print("\n11. EXTRAITS LITTÉRAUX (#126) — une fiche ne dit que ce que son document écrit")
# Arbitrage du 2026-10-15 : une fiche tirée d'un document porte des extraits mot pour mot, vérifiés
# contre le texte que les outils ont RÉELLEMENT rapporté pour son adresse ; un seul extrait
# introuvable la fait refuser ; la lecture du collecteur est rangée à part, sans l'autorité du
# document. Texte copié du document RÉEL (CFO Commentary NVIDIA du T2 de l'exercice 2027, lu sur
# EDGAR le 2026-10-15) : la pièce #1087 lui faisait dire « demande excédant l'offre », #1086 lisait
# sa dernière phrase comme une réaction des volumes aux prix de NVIDIA.
import inspect  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.agents.v2 import note_flash as _nf  # noqa: E402
from app.agents.v2 import worker as _w  # noqa: E402
from app.agents.v2.common import derive_nature  # noqa: E402
from app.contracts.worker_delegation_schema import ProducedEntry  # noqa: E402
from app.knowledge import citation as _cit  # noqa: E402

_CFO_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/q2fy27cfocommentary.htm"
_CFO_TEXTE = (
    "Revenue for the second quarter was a record $96.2 billion, up 106% from a year ago and up 18% "
    "sequentially. Data Center revenue for the second quarter was a record $89.0 billion, up 117% from "
    "a year ago and up 18% sequentially, driven by the ramp of our Blackwell Ultra infrastructure. "
    "Hyperscale revenue more than doubled from a year ago and increased 13% sequentially on the "
    "strength of Blackwell Ultra. […] for the second quarter was $7.2 billion, up 27% from a year ago "
    "and up 13% sequentially. The increases were driven by strong sales of Blackwell workstations, "
    "partially offset by slower consumer PC sales that were tempered by elevated memory and systems "
    "prices. […] We’ve partnered with our extensive network of suppliers to secure the critical "
    "components needed.")
_BON_1 = "Data Center revenue for the second quarter was a record $89.0 billion, up 117% from a year ago"
_BON_2 = "slower consumer PC sales that were tempered by elevated memory and systems prices"
req_q = WorkerRequest(
    requester="knowledge-curator", worker="search-worker", ticker_id="NVDA",
    query="Réaction des volumes aux prix", output_schema=OutputSchema(entry_type="fact_qualitative"),
    reliability_min=0.40, max_entries=1)
log_q = RetrievalLog()
log_q.record(_CFO_URL, "full")
log_q.record_text(_CFO_URL, _CFO_TEXTE)


def _fiche(extraits, url=_CFO_URL, **kw):
    base = {"entry_type": "fact_qualitative", "title": "CFO Commentary T2",
            "content": "Lecture : la croissance vient de Blackwell Ultra ; la demande excède l'offre.",
            "content_structured": {"metric": "data_center_revenue", "value": 89.0},
            "source_type": "edgar_official", "source_url": url, "extraits": extraits,
            "portee_temporelle": "constatee", "date_du_fait": "2026-07-26",
            "date_du_document": "2026-08-26",
            "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "CFO commentary"}
    base.update(kw)
    return base


def _passe(raw, log=log_q, r=req_q):
    try:
        return _apply_deterministic_overrides({"entries": [raw], "uncovered_fields": []}, r,
                                              model_used="m", tokens_in=1, tokens_out=1,
                                              cost_usd=0.0, log=log)
    except Exception as e:  # noqa: BLE001 — un refus inattendu est un FAIL nommé, pas la mort du script
        return {"entries": [], "status": f"LEVÉ : {e!r}"}


def _refusee(label, raw, log=log_q):
    o = _passe(raw, log)
    check(label, o["entries"] == [] and o["status"] == "not_found",
          f"→ status={o['status']} · {len(o['entries'])} ligne(s)")


o = _passe(_fiche([_BON_1, _BON_2]))
_fs = [e for e in o["entries"] if TAG_LECTURE not in e["tags"]]
_ls = [e for e in o["entries"] if TAG_LECTURE in e["tags"]]
check("deux extraits RÉELS du document → la fiche passe, suivie de sa lecture",
      len(_fs) == 1 and len(_ls) == 1, f"→ {o['status']} · {len(_fs)} fiche(s), {len(_ls)} lecture(s)")
_f = _fs[0] if _fs else {}
_l = _ls[0] if _ls else {}
check("le texte de la fiche porte les extraits…",
      _BON_1 in _f.get("content", "") and _BON_2 in _f.get("content", ""))
check("… et RIEN de la lecture du collecteur (« la demande excède l'offre » n'y est pas)",
      "demande excède" not in _f.get("content", ""), f"→ {_f.get('content', '')[:200]!r}")
check("les valeurs structurées du collecteur ne sont PAS sous l'autorité du document",
      _f.get("content_structured") is None, f"→ {_f.get('content_structured')}")
check("le titre de la fiche NOMME le document et n'affirme rien (le titre du collecteur part avec la lecture)",
      _f.get("title") == _w.titre_de_fiche(_CFO_URL), f"→ {_f.get('title')!r}")
# Arbitrage du 2026-10-18 : le titre dit ce que la pièce CONTIENT, jamais ce qu'on lui a demandé —
# même geste que #58 appliqué au worker. La « lecture du collecteur » nomme le DOCUMENT (même forme
# que `titre_de_fiche`, détenteur unique), jamais le titre rédigé par le modèle (« CFO Commentary
# T2 » ici) : ce titre AFFIRME, il ne nomme pas. Avant ce lot, le repli `raw.get("title")` le
# laissait passer dès qu'un titre de modèle existait.
check("le titre de la LECTURE DU COLLECTEUR nomme le document par le même détenteur que la fiche "
      "(`titre_de_fiche`), jamais le titre rédigé par le modèle",
      _l.get("title") == f"Lecture du collecteur — {_w.titre_de_fiche(_CFO_URL)}"
      and "CFO Commentary T2" not in _l.get("title", ""),
      f"→ {_l.get('title')!r}")
o2b = _apply_deterministic_overrides(
    {"entries": [_fiche([_BON_1]), _fiche([_BON_2])], "uncovered_fields": []},
    req_q.model_copy(update={"max_entries": 3}), model_used="m", tokens_in=1, tokens_out=1,
    cost_usd=0.0, log=log_q)
check("deux fiches d'un même document, extraits différents → deux fiches (pas un doublon)",
      sum(1 for e in o2b["entries"] if TAG_LECTURE not in e["tags"]) == 2,
      f"→ {[e['title'] for e in o2b['entries']]}")
check("la fiche garde ses extraits et la source de son domaine (tier A)",
      _f.get("extraits") == [_BON_1, _BON_2] and _f.get("source_type") == "edgar_official"
      and _f.get("reliability_tier") == "A")
check("la lecture est une synthèse d'agent, tier B-, sans adresse, étiquetée",
      _l.get("source_type") == "agent_synthesis" and _l.get("reliability_tier") == "B-"
      and _l.get("source_url") is None
      and est_lecture_du_collecteur(SimpleNamespace(source_type=_l.get("source_type"), tags=_l.get("tags"))),
      f"→ {_l.get('source_type')} {_l.get('reliability_tier')} {_l.get('source_url')}")
check("la lecture porte la prose et les valeurs structurées du collecteur, sans extrait",
      "demande excède" in _l.get("content", "") and _l.get("content_structured") == {
          "metric": "data_center_revenue", "value": 89.0} and _l.get("extraits") == [])
_nat_f, _ = derive_nature(entry_type="fact_qualitative", source_type="agent_synthesis",
                          content=_l.get("content"))
check("au guichet, la lecture est une INTERPRÉTATION (jamais un relevé)", _nat_f == "interpretation",
      f"→ {_nat_f}")
try:
    WorkerExchange(request=req_q, response=WorkerResponse.model_validate(o))
    _exch_ok = True
except ValidationError as e:
    _exch_ok = f"{e}"[:200]
check("max_entries=1 se compte en FICHES : 1 fiche + sa lecture passent l'invariant croisé",
      _exch_ok is True, f"→ {_exch_ok}")

# Les refus — chacun prononcé par la règle #126, sur un défaut RÉEL du 2026-10-14.
_refusee("paraphrase inventée (#1087 : « demand exceeded supply ») → fiche ENTIÈRE refusée",
         _fiche([_BON_1, "demand for Blackwell continued to exceed supply in the quarter"]))
_refusee("chiffre arrondi ($89 billion pour $89.0 billion) → refusée",
         _fiche(["Data Center revenue for the second quarter was a record $89 billion"]))
_refusee("extrapolation du collecteur (#1028, son texte réel) → refusée",
         _fiche(["à ce rythme, un programme complet de Phase 1 à 3 sur 6-8 ans représenterait un "
                 "investissement de l'ordre de 2 à 4 Md$ pour un seul actif"]))
_log_2 = RetrievalLog()
_log_2.record(_CFO_URL, "full")
_log_2.record_text(_CFO_URL, _CFO_TEXTE)
_AUTRE = "https://www.reuters.com/world/french-competition-authoritys-nvidia-probe-nearing-end-2026-07-09/"
_log_2.record(_AUTRE, "full")
_log_2.record_text(_AUTRE, "France's competition authority is nearing the end of its probe into Nvidia.")
_refusee("phrase d'un AUTRE document lu pendant le run (#1069) → refusée",
         _fiche(["France's competition authority is nearing the end of its probe into Nvidia"]), log=_log_2)
_refusee("adresse jamais lue (aucun texte rapporté) → refusée, plus rétrogradée en mémoire",
         _fiche([_BON_1], url="https://www.sec.gov/Archives/edgar/data/1045810/autre.htm"))
_sans = _fiche([_BON_1])
del _sans["extraits"]
_refusee("clef `extraits` absente → refusée (même garde que la liste vide)", _sans)
_refusee("liste d'extraits vide sur un document → refusée", _fiche([]))

# C1 (2026-10-21) — l'EXTRAIT COURT : un cours, un intitulé. Refusé d'office jusqu'ici, il faisait tomber
# la seule fiche qui portait la valeur (NVDA ma_3 « $198.89 », ma_4 « X Director », 2026-10-16). Le code
# le remplace par son passage du document s'il y est UNIQUE ; présent à plusieurs endroits, il ne désigne
# rien et reste refusé. Fixture COPIÉE DU RÉEL : le 10-K NVIDIA 0001045810-26-000021 converti par
# `websearch.html_to_text` (tableau des rachats, le « $ » et le nombre dans deux cellules, #132).
_K10_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm"
_K10_TEXTE = (
    "The following table presents details of our share repurchase transactions during the fourth "
    "quarter of fiscal year 2026:\n"
    "Period\t\tTotal Number   of Shares Purchased   (In millions)\t\tAverage Price Paid per Share (1)"
    "\t\tTotal Number of Shares Purchased as Part of Publicly Announced Program (In millions)\t\t"
    "Approximate Dollar Value of Shares that May Yet Be Purchased Under the Program (In billions)\n"
    "October 27, 2025 - November 23, 2025\t\t5.6\xa0\t\t\t$\t198.89\xa0\t\t\t5.6\xa0\t\t\t$\t61.1\n"
    "November 24, 2025 - December 21, 2025\t\t6.6\xa0\t\t\t$\t179.41\xa0\t\t\t6.6\xa0\t\t\t$\t59.9\n"
    "December 22, 2025 - January 25, 2026\t\t7.3\xa0\t\t\t$\t186.52\xa0\t\t\t7.3\xa0\t\t\t$\t58.5\n"
    "Total\t\t19.5\xa0\t\t\t\t\t19.5\n"
    "(1)\xa0\xa0\xa0\xa0Average price paid per share includes broker commissions, but excludes our "
    "liability under the 1% excise tax on the net amount of our share repurchases required by the "
    "Inflation Reduction Act of 2022.")
_LIGNE_198 = "October 27, 2025 - November 23, 2025 5.6 $ 198.89 5.6 $ 61.1"
log_k = RetrievalLog()
log_k.record(_K10_URL, "full")
log_k.record_text(_K10_URL, _K10_TEXTE)
o = _passe(_fiche(["$198.89"], url=_K10_URL), log=log_k)
_fk = [e for e in o["entries"] if TAG_LECTURE not in e["tags"]]
check("extrait court UNIQUE (« $198.89 », cellule du tableau des rachats) → la fiche passe, l'extrait "
      "remplacé par SA LIGNE du tableau, copiée du document",
      len(_fk) == 1 and _fk[0]["extraits"] == [_LIGNE_198] and _LIGNE_198 in _fk[0]["content"],
      f"→ {o['status']} · {[e.get('extraits') for e in _fk]}")
check("« $ » et le nombre dans deux cellules : « $198.89 » se retrouve (espace après le symbole "
      "monétaire normalisé)",
      _cit.extrait_introuvable(["$198.89"], [_K10_TEXTE]) is None
      and _cit.extrait_introuvable(["$198.90"], [_K10_TEXTE]) == "$198.90")
_refusee("extrait court AMBIGU (« Total », trois passages du tableau) → refusé, non discriminant",
         _fiche(["Total"], url=_K10_URL), log=log_k)
_ets, _motif_amb = _cit.etablir_extraits(["Total"], [_K10_TEXTE])
check("… et le motif nomme l'ambiguïté (pas « introuvable »)",
      _ets == [] and _motif_amb is not None and "passages différents" in (_motif_amb or ""),
      f"→ {_motif_amb!r}")
_refusee("extrait court introuvable (« $198.90 ») → refusé", _fiche(["$198.90"], url=_K10_URL), log=log_k)
# Deux vues du MÊME document (page entière + extrait de recherche) : une occurrence dans chacune n'est
# pas une ambiguïté ; le passage retenu est celui du texte le plus long.
log_k2 = RetrievalLog()
log_k2.record(_K10_URL, "full")
log_k2.record_text(_K10_URL, "Average Price Paid per Share $ 198.89 in the period")
log_k2.record_text(_K10_URL, _K10_TEXTE)
o = _passe(_fiche(["$198.89"], url=_K10_URL), log=log_k2)
_fk2 = [e for e in o["entries"] if TAG_LECTURE not in e["tags"]]
check("deux textes lus d'une même adresse, une occurrence dans chacun → pas ambigu, passage du texte "
      "le plus long", len(_fk2) == 1 and _fk2[0]["extraits"] == [_LIGNE_198],
      f"→ {o['status']} · {[e.get('extraits') for e in _fk2]}")
# Une ligne trop courte (« Total 19.5 19.5 ») s'étend à ses voisines ; une page sans saut de ligne est
# coupée autour de l'extrait, sur des blancs.
_et_tot, _ = _cit.etablir_extraits(["19.5 19.5"], [_K10_TEXTE])
check("ligne de l'extrait trop courte (« Total 19.5 19.5 ») → étendue à ses deux voisines",
      len(_et_tot) == 1 and _et_tot[0].startswith("December 22, 2025") and "Total 19.5" in _et_tot[0]
      and _et_tot[0].endswith("Inflation Reduction Act of 2022."), f"→ {_et_tot!r}")
_et_seul, _motif_seul = _cit.etablir_extraits(["X Director"], ["X Director"])
check("passage encore trop court même avec ses voisines (un document réduit à « X Director ») → refusé, "
      "non discriminant", _et_seul == [] and "moins de" in (_motif_seul or ""), f"→ {_motif_seul!r}")
_et_mem, _ = _cit.etablir_extraits(["elevated memory"], [_CFO_TEXTE])
check("page sans saut de ligne → fenêtre autour de l'extrait, coupée sur des blancs, vérifiable mot "
      "pour mot", len(_et_mem) == 1 and "elevated memory" in _et_mem[0]
      and len(_et_mem[0]) <= _cit.CONTEXTE_MAX_CARS
      and _cit.extrait_introuvable(_et_mem, [_CFO_TEXTE]) is None
      and _et_mem[0].split(" ")[0] in _CFO_TEXTE.split(), f"→ {_et_mem!r}")

o = _passe(_fiche(["We've partnered with our extensive network of suppliers",
                   "DATA CENTER revenue for the  second quarter was a record $89.0 billion"]))
check("typographie, espaces et casse normalisés (apostrophe droite contre courbe) → acceptée",
      o["status"] == "found", f"→ {o['status']}")
o = _passe(_fiche([_BON_1]), r=req_q.model_copy(update={"reliability_min": 0.65}))
check("lecture sous le plancher du mandat (0.60 < 0.65) → la fiche reste, la lecture tombe",
      len(o["entries"]) == 1 and TAG_LECTURE not in o["entries"][0]["tags"],
      f"→ {[e['source_type'] for e in o['entries']]}")
o = _passe(_fiche(["n'importe quoi de plus de vingt caractères"], source_type="llm_memory",
                  model_cutoff="2026-01"), log=RetrievalLog(),
           r=req_q.model_copy(update={"reliability_min": 0.0}))  # 0.40 décoté par l'âge du fait
check("aveu llm_memory : pas de document, donc ni extrait ni lecture séparée",
      len(o["entries"]) == 1 and o["entries"][0]["extraits"] == []
      and o["entries"][0]["source_type"] == "llm_memory", f"→ {o['status']}")

# Le contrat redit la règle (le filet derrière le worker).
def _contrat(**kw):
    try:
        ProducedEntry(**{**{k: v for k, v in _f.items()}, **kw})
        return "ACCEPTÉ"
    except ValidationError as e:
        return str(e)


check("contrat : une fiche de document sans extrait est refusée",
      "au moins un extrait" in _contrat(extraits=[]), f"→ {_contrat(extraits=[])[:160]}")
check("contrat : une lecture (agent_synthesis) qui porterait un extrait est refusée",
      "aucun extrait" in _contrat(source_type="agent_synthesis", extraits=[_BON_1]))
# C1 : la longueur ne se juge plus au contrat, qui valide aussi la sortie BRUTE (le worker établit).
check("contrat : un extrait court n'est PAS refusé par le contrat (le worker l'établit ou refuse la fiche)",
      _contrat(extraits=["$198.89"]) == "ACCEPTÉ", f"→ {_contrat(extraits=['$198.89'])[:160]}")
check("contrat : `extraits` est REQUIS, sans défaut", ProducedEntry.model_fields["extraits"].is_required())

# Le journal se remplit au point de récupération RÉEL : les deux exécuteurs d'outils, bouchonnés au
# niveau du réseau seulement. Sans ce câblage, toute fiche serait refusée en production alors que les
# fixtures ci-dessus, qui remplissent le journal à la main, resteraient vertes.
async def _stub_fetch(url, *, query=None, chercher=None, ticker_id=None, max_chars=None):
    return {"url": url, "final_url": url + "?redirige", "status": 200, "title": "CFO Commentary",
            "text": _CFO_TEXTE, "via": "direct"}


async def _stub_search(query, max_results=5, ticker_id=None):
    return [SearchHit(title="Article", url="https://www.reuters.com/x", snippet="accroche seule",
                      text="Full excerpt text returned by the search backend for this article."),
            SearchHit(title="Lien", url="https://www.ft.com/y", snippet="accroche d'un simple lien")]


_reels = (_tools.fetch_url, _tools.web_search)
_tools.fetch_url, _tools.web_search = _stub_fetch, _stub_search
try:
    _lg = RetrievalLog()
    _ex = _tools.build_tool_executors(ticker_id="NVDA", query="volumes", log=_lg)
    asyncio.run(_ex["fetch_url"]({"url": _CFO_URL}))
    asyncio.run(_ex["web_search"]({"query": "nvidia"}))
    check("fetch_url : le texte rapporté est journalisé sous l'adresse demandée…",
          _extrait_ok := (_cit.extrait_introuvable([_BON_1], _lg.textes_de(_CFO_URL)) is None))
    check("… et sous l'adresse finale (redirection)",
          _cit.extrait_introuvable([_BON_1], _lg.textes_de(_CFO_URL + "?redirige")) is None)
    check("web_search : le texte d'extrait d'un résultat est journalisé",
          _cit.extrait_introuvable(["Full excerpt text returned by the search backend"],
                                   _lg.textes_de("https://www.reuters.com/x")) is None)
    check("web_search : une simple accroche de lien n'est PAS un texte citable",
          _lg.textes_de("https://www.ft.com/y") == [], f"→ {_lg.textes_de('https://www.ft.com/y')}")
finally:
    _tools.fetch_url, _tools.web_search = _reels

# Le journal est REQUIS : sans lui aucun extrait ne se vérifie (un appelant qui l'oublie ne doit pas
# faire passer des fiches non vérifiées).
check("`_normalise_entry` exige le journal (aucun défaut)",
      inspect.signature(_w._normalise_entry).parameters["log"].default is inspect.Parameter.empty)
check("`_apply_deterministic_overrides` exige le journal (aucun défaut)",
      inspect.signature(_w._apply_deterministic_overrides).parameters["log"].default
      is inspect.Parameter.empty)
_run = next((n for n in ast.walk(ast.parse(textwrap.dedent(inspect.getsource(_w.run_search_worker))))
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_apply_deterministic_overrides"),
            None)
_kw_log = next((k.value for k in (_run.keywords if _run else []) if k.arg == "log"), None)
check("en production, le journal du run est celui passé à la vérification",
      isinstance(_kw_log, ast.Name) and _kw_log.id == "retrieval_log", f"→ {ast.dump(_kw_log) if _kw_log else None}")
check("détenteur unique : la note flash compare ses citations avec la même normalisation",
      _nf._normaliser is _cit.normaliser)

print("\n12. La source d'origine d'abord (arbitrage du 2026-10-16) — le site de l'émetteur, à défaut ailleurs")
# Cas réel : la prévision de NVIDIA (ma_5, plan #267) n'a été trouvée que sur un miroir brésilien alors
# que le communiqué est sur nvidia.com. Le backend est bouchonné au niveau du réseau ; `web_search` est
# le détenteur unique de l'ordre, l'exécuteur d'outils ne fait que lui passer le ticker.
from app.knowledge import websearch as _ws  # noqa: E402

_ORIG = "https://investor.nvidia.com/news/press-release-details/2026/Q2-FY2027/"
_MIROIR = "https://www.miroir.com.br/nvidia-previsao"


class _BackendEspion(_ws.SearchBackend):
    name = "espion"

    def __init__(self):
        self.appels = []

    async def search(self, query, max_results, include_domains=()):
        self.appels.append(tuple(include_domains))
        if include_domains:
            return [SearchHit(title="Communiqué", url=_ORIG, text="Revenue is expected to be $54.0 billion.")]
        return [SearchHit(title="Miroir", url=_MIROIR, text="Receita esperada de US$ 54 bilhões."),
                SearchHit(title="Communiqué", url=_ORIG, text="Revenue is expected to be $54.0 billion.")]


_espion = _BackendEspion()
_get_reel = _ws.get_search_backend
_ws.get_search_backend = lambda: _espion
try:
    _ex12 = _tools.build_tool_executors(ticker_id="NVDA", query="prévision du trimestre")
    _r12 = asyncio.run(_ex12["web_search"]({"query": "NVIDIA outlook next quarter"})).get("results") or []
    check("émetteur enregistré : le site de l'émetteur est interrogé, restreint à SES domaines",
          ("nvidia.com",) in _espion.appels, f"→ appels {_espion.appels}")
    check("… et le web ouvert l'est aussi (une taille de marché n'est pas sur le site de l'émetteur)",
          () in _espion.appels, f"→ appels {_espion.appels}")
    check("les pages de l'émetteur passent EN TÊTE des résultats",
          bool(_r12) and _r12[0]["url"] == _ORIG, f"→ {[r['url'] for r in _r12]}")
    check("une page déjà rendue par le site de l'émetteur n'est pas répétée",
          [r["url"] for r in _r12].count(_ORIG) == 1, f"→ {[r['url'] for r in _r12]}")
    check("le résultat dit au modèle qu'une page vient du site de l'émetteur…",
          bool(_r12) and _r12[0].get("site_emetteur") is True, f"→ {_r12[:1]}")
    check("… et qu'une reprise n'en vient pas",
          any(r["url"] == _MIROIR and r.get("site_emetteur") is False for r in _r12), f"→ {_r12}")

    _espion.appels.clear()
    _ex_inconnu = _tools.build_tool_executors(ticker_id="ZZZZ", query="prévision")
    _r_inc = asyncio.run(_ex_inconnu["web_search"]({"query": "outlook"})).get("results") or []
    check("émetteur sans site enregistré : une seule recherche, ouverte (aucun domaine deviné)",
          _espion.appels == [()], f"→ appels {_espion.appels}")
    check("… et aucune page n'y est annoncée comme site de l'émetteur",
          not any(r.get("site_emetteur") for r in _r_inc), f"→ {_r_inc}")
finally:
    _ws.get_search_backend = _get_reel

check("site de l'émetteur : un sous-domaine compte (investor.nvidia.com pour NVDA)",
      _ws.est_site_emetteur("https://investor.nvidia.com/x", "NVDA"))
check("site de l'émetteur : un domaine qui se termine pareil ne compte pas (notnvidia.com)",
      not _ws.est_site_emetteur("https://notnvidia.com/x", "NVDA"))
check("site de l'émetteur : nvidia.com n'est pas le site de l'émetteur d'une analyse MSFT",
      not _ws.est_site_emetteur("https://investor.nvidia.com/x", "MSFT"))
from app.db.migrations._gen_025 import PROMPTS as _PROMPTS  # noqa: E402

_consigne = (_PROMPTS / "11-search-worker.md").read_text()
check("la consigne du collecteur nomme la règle (site_emetteur, à défaut une reprise)",
      "`site_emetteur: true`" in _consigne and "ne se cite qu'à défaut" in _consigne)

print("\n13. Lecture tolérante entry par entry (#128) + relance sans recherche web (#B)")
# Mesuré sur l'historique de production (2026-10-12→16, 11 échecs) et un replay : (A) une seule
# fiche fautive (extrait trop court) faisait LEVER toute la WorkerResponse, perdant les bonnes
# entries avec elle — même défaut que #128 (analyste), transposé au worker ; (B) un replay a
# répondu `not_found` après deux appels `query_knowledge` SEULS, sans aucun `web_search`/
# `fetch_url`, alors que la même ligne trouvait 4-6 entries sur deux autres replays.
#
# `run_search_worker` est exécuté pour de vrai ; seuls les points de contact avec le réseau/la DB/le
# modèle sont bouchonnés (comme §2bis/§11/§12) : `run_tool_json_agent` (tel qu'IMPORTÉ dans worker.py),
# `get_agent_provider`, `get_db_session`, `ancre_temporelle`, `material_anchor_for_ticker`,
# `search_is_configured`, et — au niveau outil — `_tools.fetch_url`/`_tools.web_search`, pour que les
# appels simulés traversent le VRAI `RetrievalLog` du run (compteurs ET textes).
import contextlib  # noqa: E402
import json as _json  # noqa: E402

from app.agents.v2.runner import AgentOutputInvalid as _AOI13  # noqa: E402

req13 = WorkerRequest(
    requester="knowledge-curator", worker="search-worker", ticker_id="NVDA",
    query="Marge opérationnelle du trimestre",
    output_schema=OutputSchema(entry_type="fact_qualitative", field_path="qf.marge_operationnelle"),
    reliability_min=0.40, max_entries=5,
)
_U13 = "https://www.sec.gov/Archives/edgar/data/1045810/x13.htm"
_AUTRE_U13 = "https://www.sec.gov/Archives/edgar/data/1045810/autre13.htm"
_REUTERS_U13 = "https://www.reuters.com/x13"
_TXT13 = ("Operating margin expanded to 62 percentage points in the quarter, driven by strong "
          "Data Center demand.")
_BON13 = "Operating margin expanded to 62 percentage points in the quarter"
_TEXTES13 = {
    _U13: _TXT13,
    _REUTERS_U13: ("Analysts noted that margins are expanding faster than peers according to "
                   "analysts surveyed in a recent report."),
}


def _entree13(extraits, **kw):
    base = {"entry_type": "fact_qualitative", "title": "10-Q marge",
            "content": "Lecture : la marge s'améliore.",
            "source_type": "edgar_official", "source_url": _U13, "extraits": extraits,
            "portee_temporelle": "constatee", "date_du_fait": "2026-07-26",
            "date_du_document": "2026-08-26",
            "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "10-Q"}
    base.update(kw)
    return base


# Structurellement correcte (extrait ≥ 20 caractères) SAUF le plafond de score (financial_press
# plafonne à 0.85 = baseline 0.75 + cross-val 0.10) : `ProducedEntry` la refuse (#128), mais
# `_normalise_entry` ne regarde JAMAIS le score déclaré — il le RECALCULE — donc rien, en aval, ne
# la retiendrait si la lecture tolérante la laissait passer. C'est le cas qui démasque « entrée
# fautive gardée » : les autres gardes du worker sont redondantes avec #128 sur ce point, celle-ci
# ne l'est pas.
_ENTREE_SURQUALIFIEE13 = {
    "entry_type": "fact_qualitative", "title": "Presse", "content": "Reuters commente la marge.",
    "source_type": "financial_press", "source_url": _REUTERS_U13,
    "extraits": ["margins are expanding faster than peers according to analysts surveyed"],
    "portee_temporelle": "constatee", "date_du_fait": "2026-07-20", "date_du_document": "2026-07-21",
    "reliability_score": 0.99, "reliability_tier": "A", "reliability_note": "je suis confiant",
}
_ENTREE_MEMOIRE13 = {
    "entry_type": "fact_qualitative", "title": "De mémoire", "content": "La marge s'améliore.",
    "source_type": "llm_memory", "extraits": [], "portee_temporelle": "indatable",
    "datation_motif": "restitution de mémoire, aucune date affirmée",
    "reliability_score": 0.9, "reliability_tier": "A", "reliability_note": "sûr",
    "requires_human_review": True, "model_cutoff": "2026-01",
}


class _FauxResult13:
    """Imite `AgentRunResult` côté champs lus par `_executer_tour` — rien de plus."""

    def __init__(self, data, raw_content, *, tokens_in=10, tokens_out=5, cost_usd=0.001, model="m13"):
        self.data = data
        self.raw_content = raw_content
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd
        self.completion = SimpleNamespace(model=model)


def _succes13(entries, *, uncovered=None, appeler=None, **kw):
    """Un tour qui RÉUSSIT la clôture — éventuellement après avoir appelé UN outil (pour simuler
    une recherche web effectivement tentée)."""
    async def _action(executors):
        if appeler:
            nom, args = appeler
            await executors[nom](args)
        data = {"entries": entries, "uncovered_fields": uncovered or []}
        return _FauxResult13(data, _json.dumps(data, ensure_ascii=False), **kw)
    return _action


def _leve13(raw_content, *, population=None, **kw):
    """Un tour dont la clôture ÉCHOUE (`AgentOutputInvalid`), portant `raw_content` brut — après
    avoir, éventuellement, fait passer du texte sous les yeux du modèle (pour peupler le `RetrievalLog`
    AVANT le refus, exactement comme un run réel l'aurait fait pendant la boucle d'outils)."""
    async def _action(executors):
        for nom, args in (population or []):
            await executors[nom](args)
        raise _AOI13(agent_name="search-worker", schema_name="WorkerResponse", attempts=2,
                     last_error="hors contrat (#128)", raw_content=raw_content,
                     tokens_in=kw.get("tokens_in", 10), tokens_out=kw.get("tokens_out", 5),
                     cost_usd=kw.get("cost_usd", 0.001))
    return _action


def _stub_run13(sequence):
    """Un appel par TOUR — indexation STRICTE (`sequence[len(appels)-1]`) : un tour EN TROP lève
    `IndexError` plutôt que de boucler indéfiniment si une mutation transforme la relance unique en
    boucle (sans cette garde, une mutation « ça boucle » ferait tourner le check indéfiniment au
    lieu de rougir)."""
    appels: list = []

    async def _run(agent, messages, executors, schema, *, closing_instruction, max_iterations,
                   temperature, timeout, max_tokens_recherche=None):
        appels.append(messages)
        action = sequence[len(appels) - 1]
        return await action(executors)
    return _run, appels


@contextlib.asynccontextmanager
async def _fake_db13():
    yield None


async def _stub_ancre13(conn, ticker_id):
    return None


async def _stub_materiel13(conn, ticker_id):
    return None


async def _stub_agent_provider13(name, version):
    return SimpleNamespace(model="stub-agent-13")


async def _stub_fetch13(url, *, query=None, chercher=None, ticker_id=None, max_chars=None):
    return {"url": url, "final_url": url, "status": 200, "title": "Doc",
            "text": _TEXTES13.get(url, _TXT13), "via": "direct"}


async def _stub_search13(query, max_results=5, ticker_id=None):
    return []


def _run_worker13(sequence, *, allow_without_web=False):
    stub_run, appels = _stub_run13(sequence)
    vrais = (_w.run_tool_json_agent, _w.get_agent_provider, _w.get_db_session,
             _w.ancre_temporelle, _w.material_anchor_for_ticker, _w.search_is_configured)
    _w.run_tool_json_agent = stub_run
    _w.get_agent_provider = _stub_agent_provider13
    _w.get_db_session = _fake_db13
    _w.ancre_temporelle = _stub_ancre13
    _w.material_anchor_for_ticker = _stub_materiel13
    _w.search_is_configured = lambda: True  # EXA_API_KEY absente du check (§8) — ce point le contourne
    _reel_fetch, _reel_search = _tools.fetch_url, _tools.web_search
    _tools.fetch_url, _tools.web_search = _stub_fetch13, _stub_search13
    try:
        resultat = asyncio.run(_w.run_search_worker(req13, allow_without_web=allow_without_web))
        return resultat, appels
    except Exception as exc:  # noqa: BLE001 — un FAIL nommé, pas la mort du script
        return exc, appels
    finally:
        (_w.run_tool_json_agent, _w.get_agent_provider, _w.get_db_session,
         _w.ancre_temporelle, _w.material_anchor_for_ticker, _w.search_is_configured) = vrais
        _tools.fetch_url, _tools.web_search = _reel_fetch, _reel_search


# ── A1 : une fiche fautive (extrait court) ET une fiche fautive (score au-delà du plafond) sont
#    écartées ; la bonne survit — jamais réparée (#128) ──────────────────────────────────────────
_RAW_A1 = _json.dumps({
    "entries": [_entree13([_BON13]), _entree13(["Revenue"], title="bad-court"),
                _ENTREE_SURQUALIFIEE13],
    "uncovered_fields": [],
}, ensure_ascii=False)
_res_a1, _ap_a1 = _run_worker13([
    _leve13(_RAW_A1, population=[("fetch_url", {"url": _U13}), ("fetch_url", {"url": _REUTERS_U13})]),
])
_fiches_a1 = ([e for e in _res_a1.response.entries if TAG_LECTURE not in e.tags]
              if not isinstance(_res_a1, Exception) else [])
check("A1 : lecture tolérante entry par entry — la bonne fiche survit, les deux fautives sont "
      "écartées (#128)",
      not isinstance(_res_a1, Exception) and len(_ap_a1) == 1 and len(_fiches_a1) == 1
      and _fiches_a1[0].source_url == _U13,
      f"→ {_res_a1!r}"[:300] if isinstance(_res_a1, Exception) else f"→ {len(_fiches_a1)} fiche(s)")

# ── A2 : toutes les entries sont fautives → not_found, le champ part en uncovered_fields ─────────
_RAW_A2 = _json.dumps({
    "entries": [_entree13(["Revenue"]), _entree13(["X Director"], title="bad2")],
    "uncovered_fields": [],
}, ensure_ascii=False)
_res_a2, _ap_a2 = _run_worker13([
    # Un appel web est simulé ici uniquement pour ne pas déclencher la relance #B — hors sujet pour A2.
    _leve13(_RAW_A2, population=[("fetch_url", {"url": _U13})]),
])
check("A2 : toutes les entries fautives (#128) → not_found, champ non couvert déclaré",
      not isinstance(_res_a2, Exception) and len(_ap_a2) == 1
      and _res_a2.response.status == "not_found" and _res_a2.response.entries == []
      and "qf.marge_operationnelle" in _res_a2.response.uncovered_fields,
      f"→ {_res_a2!r}"[:300] if isinstance(_res_a2, Exception)
      else f"→ status={_res_a2.response.status} uncovered={_res_a2.response.uncovered_fields}")

# ── A3 : sortie brute illisible (pas de JSON exploitable) → l'exception d'origine est relevée ────
_res_a3, _ap_a3 = _run_worker13([_leve13("pas du JSON du tout")])
check("A3 : sortie brute illisible → l'exception d'origine (`AgentOutputInvalid`) est relevée, "
      "comme avant #128",
      isinstance(_res_a3, _AOI13) and _res_a3.raw_content == "pas du JSON du tout" and len(_ap_a3) == 1,
      f"→ {_res_a3!r}"[:300])

# ── A4 : entrée tolérée (conforme à ProducedEntry) reste soumise à #126 — extrait absent du
#    journal du run → refusée malgré tout ─────────────────────────────────────────────────────────
_RAW_A4 = _json.dumps({"entries": [_entree13([_BON13])], "uncovered_fields": []}, ensure_ascii=False)
_res_a4, _ap_a4 = _run_worker13([
    _leve13(_RAW_A4, population=[("fetch_url", {"url": _AUTRE_U13})]),  # PAS l'URL de l'entrée
])
check("A4 : entrée tolérée par #128 reste vérifiée par #126 — extrait absent du journal du run → "
      "refusée malgré tout",
      not isinstance(_res_a4, Exception) and len(_ap_a4) == 1
      and _res_a4.response.status == "not_found" and _res_a4.response.entries == [],
      f"→ {_res_a4!r}"[:300] if isinstance(_res_a4, Exception) else f"→ {_res_a4.response.status}")

# ── B1 : zéro entrée et AUCUN appel web pendant le tour → relance UNIQUE, avec le rappel ─────────
_res_b1, _ap_b1 = _run_worker13([
    _succes13([], uncovered=[], tokens_in=11, tokens_out=6, cost_usd=0.0011, model="m1"),
    _succes13([_ENTREE_MEMOIRE13], uncovered=[], tokens_in=22, tokens_out=9, cost_usd=0.0022, model="m2"),
])
check("B1 : zéro entrée et AUCUN appel web_search/fetch_url pendant le tour → relance UNIQUE, "
      "le rappel est bien dans le message (#B)",
      not isinstance(_res_b1, Exception) and len(_ap_b1) == 2
      and "jamais tentée" in _ap_b1[1][-1]["content"],
      f"→ {_res_b1!r}"[:300] if isinstance(_res_b1, Exception) else f"→ {len(_ap_b1)} tour(s)")
check("B1 : le second tour est pris pour FINAL quel qu'il soit",
      not isinstance(_res_b1, Exception) and _res_b1.response.status == "found"
      and len(_res_b1.response.entries) == 1,
      f"→ {_res_b1!r}"[:300] if isinstance(_res_b1, Exception) else f"→ {_res_b1.response.status}")
check("B1 : le coût (et les tokens) des DEUX tours sont cumulés dans l'exécution (#41/#B)",
      not isinstance(_res_b1, Exception)
      and abs(_res_b1.response.execution.cost_usd - (0.0011 + 0.0022)) < 1e-9
      and _res_b1.response.execution.tokens_in == 11 + 22
      and _res_b1.response.execution.tokens_out == 6 + 9,
      f"→ {_res_b1!r}"[:300] if isinstance(_res_b1, Exception) else f"→ {_res_b1.response.execution}")

# ── B2 : zéro entrée MAIS un appel `web_search` a eu lieu → AUCUNE relance ────────────────────────
_res_b2, _ap_b2 = _run_worker13([
    _succes13([], uncovered=[], appeler=("web_search", {"query": "marge opérationnelle"})),
])
check("B2 : zéro entrée MAIS un appel `web_search` a eu lieu pendant le tour → AUCUNE relance (#B)",
      not isinstance(_res_b2, Exception) and len(_ap_b2) == 1 and _res_b2.response.status == "not_found",
      f"→ {_res_b2!r}"[:300] if isinstance(_res_b2, Exception) else f"→ {len(_ap_b2)} tour(s)")

# ── B3 : des entrées sont trouvées sans AUCUN appel web (ex. llm_memory) → AUCUNE relance ────────
_res_b3, _ap_b3 = _run_worker13([
    _succes13([_ENTREE_MEMOIRE13], uncovered=[]),
])
check("B3 : des entrées trouvées sans aucun appel web_search/fetch_url (restitution llm_memory) → "
      "AUCUNE relance (#B)",
      not isinstance(_res_b3, Exception) and len(_ap_b3) == 1 and _res_b3.response.status == "found",
      f"→ {_res_b3!r}"[:300] if isinstance(_res_b3, Exception) else f"→ {len(_ap_b3)} tour(s)")

# ── B4 : le second tour est AUSSI vide → pas de troisième tour (la relance reste UNIQUE) ─────────
_res_b4, _ap_b4 = _run_worker13([
    _succes13([], uncovered=[]),
    _succes13([], uncovered=[]),
])
check("B4 : le second tour est aussi vide → pas de troisième tour",
      not isinstance(_res_b4, Exception) and len(_ap_b4) == 2 and _res_b4.response.status == "not_found",
      f"→ {_res_b4!r}"[:300] if isinstance(_res_b4, Exception) else f"→ {len(_ap_b4)} tour(s)")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
