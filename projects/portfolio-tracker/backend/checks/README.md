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
```

| Script | Ce qu'il éprouve |
|---|---|
| `check_search_worker.py` | `_apply_deterministic_overrides` face à une sortie de modèle **hostile** (source surqualifiée, score gonflé, mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) + `classify_source_type` + extraction HTML + échec explicite sans clé de recherche. 40 assertions. |
| `check_fetch_live.py` | `fetch_url` sur des URL réelles (IR client-rendu, EDGAR, page statique) et ses erreurs attendues (URL vide, non-http, 404, `web_search` sans clé). |

Ces scripts n'ont pas besoin de secret : ils vérifient précisément ce qui doit être vrai **avant**
qu'une clé soit posée. Un run réel de bout en bout (search-worker → entries → readiness `ready`)
reste à faire une fois `EXA_API_KEY` déployée.
