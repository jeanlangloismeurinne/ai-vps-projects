"""Vérification des garde-fous déterministes du search-worker (sans appel réseau ni modèle).

On simule une sortie de modèle HOSTILE : source surqualifiée, score gonflé, mauvais entry_type,
doublons, dépassement de plafond, mémoire modèle non déclarée. Tout doit être rabattu côté Python.
"""
import sys
from datetime import date

from app.agents.v2.worker import (
    _apply_deterministic_overrides, _build_user_message, _resolve_source_type, request_hash,
)
from app.contracts import OutputSchema, WorkerExchange, WorkerRequest, WorkerResponse
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


async def _stub_web_search(query, max_results=5):
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
hostile = {
    "request_hash": "peu importe",
    "worker": "search-worker",
    "status": "found",
    "entries": [
        # a) source surqualifiée + score gonflé sur un blog → doit tomber sous le plancher
        {"entry_type": "fact_qualitative", "title": "CUDA lock-in", "content": "Blog affirmant un lock-in.",
         "source_type": "edgar_official", "source_url": "https://blog.random-guy.dev/cuda",
         "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "source officielle"},
        # b) presse financière, score gonflé → recalculé à 0.75
        {"entry_type": "fact_qualitative", "title": "Coût de migration hors CUDA",
         "content": "Reuters rapporte des coûts de réécriture de kernels significatifs.",
         "source_type": "financial_press", "source_url": "https://www.reuters.com/tech/cuda",
         "source_date": "2026-07-14", "reliability_score": 0.99, "reliability_tier": "A",
         "reliability_note": "je suis confiant"},
        # c) mauvais entry_type → rejet
        {"entry_type": "fact_financial", "title": "CA FY26", "content": "130 Md$",
         "source_type": "edgar_official", "source_url": "https://www.sec.gov/x",
         "reliability_score": 0.95, "reliability_tier": "A", "reliability_note": "10-K"},
        # d) doublon exact de (b)
        {"entry_type": "fact_qualitative", "title": "Coût de migration hors CUDA",
         "content": "Reuters rapporte des coûts de réécriture de kernels significatifs.",
         "source_type": "financial_press", "source_url": "https://www.reuters.com/tech/cuda",
         "source_date": "2026-07-14", "reliability_score": 0.99, "reliability_tier": "A",
         "reliability_note": "doublon"},
        # e) IR officiel → 0.90, doit finir premier au tri
        {"entry_type": "fact_qualitative", "title": "Écosystème CUDA",
         "content": "Page IR NVIDIA décrivant l'ampleur de l'écosystème développeurs.",
         "source_type": "web_search_generic", "source_url": "https://ir.nvidia.com/ecosystem",
         "reliability_score": 0.50, "reliability_tier": "C+", "reliability_note": "prudent"},
        # f) 3ᵉ entry valide → doit être tronquée (max_entries=2)
        {"entry_type": "fact_qualitative", "title": "Barrière outillage",
         "content": "Les Échos : outillage propriétaire difficile à répliquer.",
         "source_type": "financial_press", "source_url": "https://lesechos.fr/cuda",
         "reliability_score": 0.75, "reliability_tier": "B+", "reliability_note": "presse"},
    ],
    "uncovered_fields": [],
    "execution": {"tier": "ouvrier", "model_used": "je-mens", "tokens_in": 999999,
                  "tokens_out": 999999, "cost_usd": 42.0},
}
out = _apply_deterministic_overrides(
    hostile, req, model_used="deepseek-ai/DeepSeek-V4-Flash-0731",
    tokens_in=1200, tokens_out=800, cost_usd=0.000240,
)
entries = out["entries"]
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
check("troncature = les 2 MIEUX notées, pas les 2 premières venues",
      [e["reliability_score"] for e in entries] == [0.90, 0.75],
      f"→ {[e['reliability_score'] for e in entries]}")

# Même sortie, plafond desserré : on voit alors le recalcul de score sur chaque entry retenue.
large = _apply_deterministic_overrides(
    hostile, req.model_copy(update={"max_entries": 10}),
    model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0,
)
reuters = next((e for e in large["entries"] if "reuters" in (e["source_url"] or "")), None)
check("score Reuters gonflé 0.99 → recalculé à la baseline presse, décote d'âge comprise",
      reuters is not None and 0.70 < reuters["reliability_score"] < 0.75,
      f"→ {reuters and reuters['reliability_score']}")
check("aucun score conservé du modèle dans la sortie élargie",
      all(e["reliability_score"] <= 0.90 for e in large["entries"]),
      f"→ {[e['reliability_score'] for e in large['entries']]}")
check("covers forcé au field_path de la requête",
      all(e["covers"] == "moat.preuves" for e in entries))
check("note de fiabilité jamais muette et traçant le calcul",
      all("base " in e["reliability_note"] for e in entries))
check("exécution mesurée, pas déclarée (le modèle disait 42 $)",
      out["execution"]["cost_usd"] == 0.00024 and out["execution"]["tokens_in"] == 1200,
      f"→ {out['execution']}")
check("status recalculé = found", out["status"] == "found", f"→ {out['status']}")

print("\n4. Validation de contrat (le filet, après correction)")
resp = WorkerResponse.model_validate(out)
exch = WorkerExchange(request=req, response=resp)
check("WorkerResponse + WorkerExchange valident", exch.response.status == "found")
check("request_hash stable", request_hash(req) == request_hash(req.model_copy(deep=True)))

print("\n5. Tout écarté → not_found explicite (jamais muet, A6)")
req_div = req.model_copy(update={"divergent": True, "reliability_min": 0.99})
out2 = _apply_deterministic_overrides(
    dict(hostile), req_div, model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0,
)
check("status not_found", out2["status"] == "not_found", f"→ {out2['status']}")
check("uncovered_fields renseigné", out2["uncovered_fields"] == ["moat.preuves"],
      f"→ {out2['uncovered_fields']}")
WorkerExchange(request=req_div, response=WorkerResponse.model_validate(out2))
check("mandat divergent sans résultat : l'invariant croisé A6 passe", True)

print("\n6. llm_memory — P2 imposé même si le modèle l'oublie")
req_mem = req.model_copy(update={"reliability_min": 0.0})
out3 = _apply_deterministic_overrides(
    {"entries": [{"entry_type": "fact_qualitative", "title": "De mémoire",
                  "content": "CUDA domine depuis longtemps.", "source_type": "llm_memory",
                  "reliability_score": 0.9, "reliability_tier": "A", "reliability_note": "sûr",
                  "requires_human_review": False}],
     "uncovered_fields": []},
    req_mem, model_used="m", tokens_in=1, tokens_out=1, cost_usd=0.0,
)
e = out3["entries"][0]
check("requires_human_review forcé", e["requires_human_review"] is True)
check("model_cutoff renseigné", bool(e["model_cutoff"]))
check("score ramené à 0.40 / tier C", e["reliability_score"] == 0.40 and e["reliability_tier"] == "C",
      f"→ {e['reliability_score']} {e['reliability_tier']}")
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
for _champ in ("covers", "source_type", "source_url", "fiscal_period"):
    check(f"{_champ} transmis au stockage", f"{_champ}=" in _src_persist,
          f"→ {_champ} décidé côté Python mais jamais écrit")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
