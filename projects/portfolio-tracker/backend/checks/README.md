# checks/ — vérifications exécutables des agents V2

Scripts autonomes, hors image de production (le build ne copie que `app/`). Ils tournent dans un
container jetable bâti sur l'image backend, seul endroit où pydantic est en **v2** (le python hôte
est en v1).

```bash
cd projects/portfolio-tracker/backend
IMG=$(docker inspect $(docker ps --format '{{.Names}}' | grep portfoliobackend) --format '{{.Config.Image}}')
ENV="-e DUST_API_KEY=x -e DUST_RESEARCH_AGENT_ID=x -e DUST_PORTFOLIO_AGENT_ID=x \
     -e DATABASE_URL=postgresql://u:p@h:5432/d -e SLACK_BOT_TOKEN=x -e SLACK_APP_TOKEN=x \
     -e SLACK_PORTFOLIO_CHANNEL_ID=x -e FMP_API_KEY=x"

# garde-fous déterministes du search-worker — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_search_worker.py

# fetch_url en conditions réelles — réseau ouvert, aucune clé requise
docker run --rm -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_fetch_live.py

# provenance vérifiée + recherche intra-document — hors ligne, déterministe
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_provenance.py

# ratios dérivés financials (arithmétique + fondation partielle honnête) — hors ligne
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_financials_feed.py

# synthèse grounded (dérivation de tier + grounding vérifié) — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_synthesis_feed.py

# curator : couverture recomputée depuis l'index `covers` — hors ligne, aucun appel modèle
docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app $ENV $IMG \
  python checks/check_readiness_recompute.py
```

Le seul check qui exige des **clés réelles** (Exa + embeddings DeepInfra) est `check_fetch_relevance.py` :
il n'est donc pas jouable dans un conteneur jetable sans exposer les secrets. On le lance **dans le
conteneur backend en prod**, dont l'env porte déjà les clés — elles restent confinées :

```bash
CT=$(docker ps --format '{{.Names}}' | grep portfoliobackend)
docker cp checks/check_fetch_relevance.py "$CT":/tmp/ && \
docker exec -w /app "$CT" python /tmp/check_fetch_relevance.py; \
docker exec "$CT" rm -f /tmp/check_fetch_relevance.py
```

| Script | Ce qu'il éprouve | Réseau / clés |
|---|---|---|
| `check_search_worker.py` | `_apply_deterministic_overrides` face à une sortie de modèle **hostile** (source surqualifiée, score gonflé, mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) + `classify_source_type` + extraction HTML + échec explicite sans clé de recherche. 40 assertions. | aucun (`--network none`) |
| `check_provenance.py` | `canonical_url`, `RetrievalLog` (profondeur monotone), `_verify_provenance` (rétrogradation `llm_memory` si l'URL n'a jamais été lue), `_cited_documents` (une entrée = un document), `document_search.select_relevant` (passage cible atteint, repli lexical déclaré, budget respecté). 42 assertions. | aucun (`--network none`) |
| `check_financials_feed.py` | Alimentateur `financials` : `extract_edgar_facts` (choix d'exercice, poste composite, capex absent = None), `build_financials_entries` (arithmétique des 4 ratios sur NVDA FY2026, fondation partielle honnête sans capex, tout en `edgar_official`), helpers EDGAR (`cik_from_url`, appariement annuel). 32 assertions. | aucun (`--network none`) |
| `check_synthesis_feed.py` | Alimentateur de **synthèse grounded** (ingestion-agent mode synthèse) : `derive_synthesis_reliability` (règle « un cran sous la plus faible entry citée » — jamais de surévaluation), `validate_grounding` (citation hors corpus / assertion non sourcée = violation), contrat `GroundedSynthesis` (≥1 citation/claim, union des ids), `build_content_structured` (traçabilité), registre des cibles + `citable_tiers`. | aucun (`--network none`) |
| `check_readiness_recompute.py` | **Curator — couverture pilotée par l'index `covers`** (029) : `_tier_ge`/`_plancher_for` (plancher par champ, dégradé `croissance=B`), `_covers_index` (multi-champ, entry non taguée absente), `recompute_coverage` (le plancher MORD ; l'index DÉCOUVRE une entry que le LLM n'a pas citée ; une citation LLM sans tag ne fonde plus rien ; `produits.description` ne fonde pas `business_model.description`), `_exigences` (le LLM peut resserrer les champs requis / le plancher, jamais les desserrer), `reconcile_gaps` (bijection), et le **déterminisme** : même corpus + `fondations` LLM différentes → couverture strictement identique. 49 assertions. | aucun (`--network none`) |
| `check_fetch_live.py` | `fetch_url` sur des URL réelles (IR client-rendu, EDGAR, page statique) et ses erreurs attendues (URL vide, non-http, 404, `web_search` sans clé). | réseau, pas de clé |
| `check_fetch_relevance.py` | Fin de la troncature : `fetch_url(url, query=…)` rapporte l'info même quand elle est loin dans le document — 10-K NVDA (`22%`/`14%` à 37,6 %, `via=direct mode=relevance`) et article CNBC (`Maia` à 71,5 %, `via=search_backend_cache mode=whole`). | réseau **+ Exa + DeepInfra** → run in-container |

Les trois premiers n'ont pas besoin de secret : ils vérifient ce qui doit être vrai **avant** qu'une
clé soit posée. Le run réel de bout en bout (search-worker → entries → readiness `ready`) reste à
faire une fois une session de recherche complète jouée sur un ticker.
