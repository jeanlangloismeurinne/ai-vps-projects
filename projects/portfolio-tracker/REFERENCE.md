# REFERENCE.md — portfolio-tracker (consultation à la demande)

> Matériel de référence pur (arborescence, listing exhaustif des endpoints, variables d'env).
> **Chargé à la demande** — pointé depuis `CLAUDE.md`. À ouvrir quand on a besoin du détail exact ;
> sinon `glob`/`grep` du code fait foi. Ne pas charger en permanence.

## Structure du repo

```
portfolio-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + APScheduler (V0 + V1 routers + price alerts)
│   │   ├── config.py             # Settings (pydantic-settings, toutes variables V0+V1)
│   │   ├── api/
│   │   │   ├── # V0 (legacy)
│   │   │   ├── positions.py      # CRUD positions V0
│   │   │   ├── trigger.py        # Régimes 1/2/3 + sector pulse V0
│   │   │   ├── watchlist.py      # Watchlist V0
│   │   │   ├── calendar.py       # Calendrier V0 (table v0_calendar_events)
│   │   │   ├── analysts.py       # Analystes
│   │   │   ├── portfolio.py      # Snapshot portfolio V0
│   │   │   ├── portfolio_settings.py
│   │   │   ├── market.py         # FRED température marché
│   │   │   ├── dust_runs.py      # Historique conversations Dust
│   │   │   ├── feedback.py       # Tickets feedback
│   │   │   ├── # V1 (nouveau)
│   │   │   ├── tickers.py        # CRUD tickers + price-history + alerts
│   │   │   ├── opportunity.py    # Briefs + chat opportunity-agent
│   │   │   ├── thesis_v2.py      # Thèses V1 + chat thesis-agent + validation
│   │   │   ├── monitoring_v2.py  # Sessions monitoring + chat monitoring-agent
│   │   │   ├── debates.py        # Conviction debates (option C)
│   │   │   ├── admin_v1.py       # Agent prompts + status + calendar + logs
│   │   │   ├── portfolio_v2.py   # Portfolio V1 (cash + positions)
│   │   │   └── calendar_v2.py    # Calendrier V1
│   │   ├── agents/
│   │   │   ├── dust_client.py          # Client Dust (budget, retry, extraction JSON)
│   │   │   ├── # V0 (legacy)
│   │   │   ├── research_agent.py       # Régime 1
│   │   │   ├── portfolio_agent.py      # Régimes 2/3 + pré-event
│   │   │   ├── sector_pulse.py         # Sector pulse V0
│   │   │   ├── thesis_chat.py          # Chat thèse V0 (streaming)
│   │   │   ├── scout_agent.py          # Pré-screening watchlist V0 — appelé par trigger.py
│   │   │   ├── # V1 (nouveau)
│   │   │   ├── opportunity_agent.py    # 3 modes, gemini-2-5-flash-preview
│   │   │   ├── thesis_agent.py         # 2 modes, claude-sonnet-4-5
│   │   │   └── monitoring_agent_v1.py  # 5 modes, modèles distincts
│   │   ├── calendar/
│   │   │   ├── event_router.py         # Déclenchements J-2/J+1 (utilise v0_calendar_events) — V0
│   │   │   ├── event_router_v1.py      # Déclenchements V1 — lit calendar_events, actif en prod (7h05)
│   │   │   ├── calendar_builder.py     # Refresh dates earnings
│   │   │   └── watchlist_monitor.py    # Surveillance prix watchlist V0
│   │   ├── data_collection/            # M1/M2/M3/M4 + assembler + cache + data_service
│   │   ├── db/
│   │   │   ├── database.py             # asyncpg pool + codec JSONB
│   │   │   ├── models.py               # Pydantic request/response models
│   │   │   └── migrations/             # 001 → 022 (V1 = migration 013, dernière = 022)
│   │   ├── notifications/
│   │   │   ├── slack_notifier.py       # V0 — Socket Mode (bot)
│   │   │   └── slack_webhook.py        # V1 — webhook entrant (plus simple)
│   │   └── portfolio/                  # portfolio_view, concentration_checker
│   └── sector_schemas/                 # IT_Services.json (complet), Luxury/Industrial (squelettes)
└── frontend/
    ├── pages/
    │   ├── portfolio.js                # Page 0 — /portfolio
    │   ├── watchlist-v2.js             # Page 1 — /watchlist-v2
    │   ├── calendrier.js               # Calendrier — /calendrier (consomme /calendar-v2, tous types d'events)
    │   ├── admin.js                    # Page Admin — /admin
    │   └── ticker/[ticker_id]/
    │       ├── index.js                # Page 2 — fiche entreprise
    │       ├── opportunity/[...slug].js # Page 3 — analyse opportunité (slug='new' ou brief_id)
    │       ├── thesis/[thesis_id].js   # Page 4 — thèse d'investissement
    │       ├── monitoring/[session_id].js # Page 5 — session monitoring (layout par mode 1-5)
    │       ├── decision/[thesis_id].js # Page DÉCISION
    │       └── debate/[debate_id].js   # Page DÉBAT
    └── components/
        ├── MarketTemperatureBadge.js   # Badge température de marché — header nav + page portfolio
        ├── AgentChat.js               # Chat générique réutilisé sur Pages 3/4/5/DÉBAT
        ├── AgentSyncOverlay.js        # Overlay non-dismissible si agent hors sync
        ├── PriceChart.js              # SVG pur (sans dépendances), gradient area
        ├── InvestmentBriefEditor.js   # Col 2 Page 3 (screening, anomalie, catalyseurs...)
        ├── ThesisEditorV2.js          # Col 2 Page 4 (scénarios, H1-H7, seuils, pairs...)
        ├── CalendarEditor.js          # Bandeau calendrier Page 4
        ├── M1DataPanel.js             # Données M1 (fondamentaux) — Page 2
        ├── AddPrivateCompanyModal.js  # Modal ajout société PE/VC non cotée
        └── PrivateMetricsModal.js     # Métriques PE/VC — valorisation, ARR, tour
```

---

## API REST V1 — Endpoints

```
# Tickers
GET    /tickers                               Liste (?status=watchlist|portfolio|archived)
POST   /tickers                               Créer {id, name, exchange, sector}
GET    /tickers/{ticker_id}                   Détail + prix actuel
PATCH  /tickers/{ticker_id}                   Mettre à jour (status, etc.)
GET    /tickers/{ticker_id}/price-history     Historique OHLCV (yfinance direct, ?period=1y|5y|max)
PATCH  /tickers/{ticker_id}/private-profile   Upsert profil PE/VC {stage, last_valuation_m, arr_or_revenue_m, …}
GET    /tickers/{ticker_id}/metrics           Métriques financières via DataService
GET    /tickers/{ticker_id}/alerts            Price alerts actives
POST   /tickers/{ticker_id}/alerts            Créer alerte {price, direction, label}
PATCH  /tickers/{ticker_id}/alerts/{id}       Modifier alerte
DELETE /tickers/{ticker_id}/alerts/{id}       Supprimer alerte

# Opportunity Briefs
GET    /tickers/{ticker_id}/opportunities         Liste briefs
POST   /tickers/{ticker_id}/opportunities         Créer brief {source}
GET    /tickers/{ticker_id}/opportunities/{id}    Détail
PATCH  /tickers/{ticker_id}/opportunities/{id}    Update brief_json, status
POST   /opportunities/{id}/chat                   Message → Dust opportunity-agent (freeform/conviction_challenge)
POST   /opportunities/{id}/refresh-json           Appel json_generation → update brief_json DB
GET    /opportunities/{id}/messages               Historique messages

# Thèses V1
GET    /tickers/{ticker_id}/theses                Liste thèses
POST   /tickers/{ticker_id}/theses                Créer {opportunity_id} → construit handoff
GET    /tickers/{ticker_id}/theses/{thesis_id}    Détail + messages
PATCH  /tickers/{ticker_id}/theses/{thesis_id}    Update thesis_json, one_liner
POST   /theses/{thesis_id}/chat                   Message → Dust thesis-agent
POST   /theses/{thesis_id}/refresh-json           Appel json_generation → update thesis_json
POST   /theses/{thesis_id}/validate               Valider → crée portfolio_position + cash_movement + calendar_events

# Monitoring V1
GET    /tickers/{ticker_id}/monitoring            Liste sessions
POST   /tickers/{ticker_id}/monitoring            Créer + exécuter session {trigger_type, trigger_label, mode, thesis_id}
GET    /tickers/{ticker_id}/monitoring/{id}       Détail session
POST   /tickers/{ticker_id}/monitoring/{id}/chat  Message supplémentaire
GET    /monitoring/{id}/messages                  Messages session

# Conviction Debates
POST   /debates                                   Créer debate {thesis_id, opportunity_brief_id, user_conviction_note}
GET    /debates/{id}                              Détail
POST   /debates/{id}/messages                     Message → Dust (mode conviction_challenge)
POST   /debates/{id}/close                        Fermer {outcome, action}

# Portfolio V1
GET    /portfolio-v2/summary                      Cash + valeur positions + total
GET    /portfolio-v2/positions                    Positions ouvertes avec prix live + perfs
POST   /portfolio-v2/cash                         Dépôt/retrait {type, amount, label}
GET    /portfolio-v2/cash/history                 10 derniers mouvements

# Calendrier V1
GET    /calendar-v2                               Liste (?ticker_id, ?thesis_id, ?from_date)
POST   /calendar-v2                               Créer événement
PATCH  /calendar-v2/{id}                          Modifier
DELETE /calendar-v2/{id}                          Supprimer
POST   /calendar-v2/{id}/validate                 Valider un event pending_validation
GET    /calendar-v2/{id}/sessions                 Sessions monitoring liées à cet événement

# Admin
GET    /admin/agents                              Liste agent_prompts
PATCH  /admin/agents/{name}                       Update prompt_text/dust_agent_id/dust_agent_url
POST   /admin/agents/{name}/sync                  Marquer synced=TRUE, version++
GET    /admin/status                              Ping Dust/Slack/FMP + agents sync status
GET    /admin/calendar                            Tous les events à venir (toutes thèses actives)
GET    /admin/logs                                Sessions monitoring récentes + erreurs
```

## API REST V0 — Endpoints (legacy)

```
GET/POST /positions · /positions/{id}/thesis · /positions/{id}/reviews
GET/POST /calendar · /calendar/refresh
GET/POST /watchlist · /watchlist/{id}/promote
GET/POST /analysts · /analysts/track-records
POST     /trigger/regime1/{ticker} · /trigger/regime2/{ticker} · /trigger/regime3/{ticker}
POST     /trigger/sector-pulse/{peer}
GET      /portfolio · /portfolio/snapshots
GET      /market/temperature
GET      /dust-runs/conversation/{id}
```

---

## Variables d'environnement

```bash
# Dust
DUST_API_KEY=                          # Bearer token dust.tt
DUST_WORKSPACE_ID=plm-siege
DUST_RESEARCH_AGENT_ID=eAYsKqZ1D2     # V0 legacy
DUST_PORTFOLIO_AGENT_ID=L5rXF6uilh    # V0 legacy
DUST_OPPORTUNITY_AGENT_ID=            # V1 — à renseigner après création dans Dust
DUST_THESIS_AGENT_ID=                 # V1
DUST_MONITORING_AGENT_ID=             # V1
DUST_MONTHLY_BUDGET_USD=5.0

# Slack
SLACK_BOT_TOKEN=xoxb-...              # V0 Socket Mode
SLACK_APP_TOKEN=xapp-...              # V0 Socket Mode
SLACK_PORTFOLIO_CHANNEL_ID=C0B13KANHPD
SLACK_WEBHOOK_URL=                    # fallback incoming webhook (optionnel, non utilisé en prod)
SLACK_ALERT_CHANNEL=#portfolio-alerts # V1

# Marché
FMP_API_KEY=                          # clé FMP (valeur en prod dans Coolify, ne pas committer)
FRED_API_KEY=                         # optionnel (indicateurs macro)
MARKET_DATA_PROVIDER=yfinance

# DB / Cache
DATABASE_URL=postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
REDIS_URL=redis://shared-redis:6379

# V2 — Provider agents (DeepInfra, endpoint OpenAI-compatible)
DEEPINFRA_API_KEY=                     # déployée dans Coolify (backend), jamais committée
DEEPINFRA_API_BASE=https://api.deepinfra.com/v1/openai

# V2 — Embeddings (migration 027 : knowledge_entries.embedding vector(1024))
EMBEDDING_MODEL=BAAI/bge-m3            # multilingue — le corpus est en français
EMBEDDING_DIM=1024                     # DOIT correspondre à vector(N) en DB

# V2 — Recherche web du search-worker
SEARCH_PROVIDER=exa                    # exa | serper | none
EXA_API_KEY=                           # à souscrire (10$/mois de crédits, sans carte)
SERPER_API_KEY=                        # débordement (~$1/1000)
SEARCH_TIMEOUT_S=20
FETCH_URL_MAX_CHARS=20000

# App
BASE_CURRENCY=EUR
MAX_SECTOR_CONCENTRATION_PCT=20.0
PULSE_ESCALATION_THRESHOLD=-3
```
