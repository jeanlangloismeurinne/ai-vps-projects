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
EXA_API_KEY=                           # déployée dans Coolify (backend) le 2026-08-23, jamais committée
SERPER_API_KEY=                        # débordement (~$1/1000)
SEARCH_TIMEOUT_S=20
FETCH_URL_MAX_CHARS=20000

# App
BASE_CURRENCY=EUR
MAX_SECTOR_CONCENTRATION_PCT=20.0
PULSE_ESCALATION_THRESHOLD=-3
```


---

# Repris de CLAUDE.md le 2026-10-16 — V0/V1, schéma, migrations, scheduling, données

> Texte d'origine, inchangé. Utile pour l'infrastructure et l'historique, jamais pour l'avancement V3.

## Migration V1 — Checklist post-déploiement

Après déploiement initial, faire une fois :
1. Aller sur `/admin` → créer les 3 agents dans l'UI Dust (`plm-siege`) en copiant les prompts affichés
2. Renseigner le `dust_agent_id` de chaque agent dans la Page Admin (zone mise en avant)
3. Cliquer "✓ Marquer synchronisé" pour chaque agent
4. Ajouter dans `backend/.env` : `DUST_OPPORTUNITY_AGENT_ID`, `DUST_THESIS_AGENT_ID`, `DUST_MONITORING_AGENT_ID`
   (ou `compose-deploy.sh portfolio-backend -e DUST_…=… --rebuild-only`)
5. Optionnel : `SLACK_WEBHOOK_URL` pour les notifications V1 (webhook entrant Slack, distinct du bot Socket Mode V0)

**Tables V0 préservées** : `v0_theses` et `v0_calendar_events` — données historiques CAP/TSLA intactes.
**Permissions DB** : `ALTER DEFAULT PRIVILEGES` configuré sur `db_portfolio` → les futures migrations créées par `admin` sont automatiquement accessibles à `portfolio_user`.

---

## Parcours utilisateur V1 de bout en bout

```
[Page 1 /watchlist-v2]  Ajout ticker → tickers.status = 'watchlist'
         ↓ clic "Analyser"
[Page 3 /ticker/:id/opportunity/new]  Opportunity Agent (freeform) → brief
         ↓ "Lancer la thèse approfondie" (si PROCEED)
[Page 4 /ticker/:id/thesis/:id]  Thesis Agent → thèse + calendrier → validation
         ↓ "Valider la thèse et enregistrer la position"
[Page 0 /portfolio]  Position enregistrée, calendrier activé
         ↓ (déclenchement calendaire J-2 ou J+1, ou ad hoc)
[Page 5 /ticker/:id/monitoring/:id]  Monitoring Agent → impact sur thèse
         ↓ (si REVIEW_REQUIRED + Mode 5 → opportunity_agent)
[Page DÉCISION /ticker/:id/decision/:thesis_id]  4 options
         ↓ option C "Maintenir"
[Page DÉBAT /ticker/:id/debate/:debate_id]  Opportunity Agent conviction_challenge
```

---

## Les 3 agents Dust V1

### Tableau de synthèse

| Agent | Pages | Modèle | Modes |
|-------|-------|--------|-------|
| `opportunity-agent` | Page 3, Page DÉBAT | `gemini-2-5-flash-preview` | `freeform` · `json_generation` · `conviction_challenge` |
| `thesis-agent` | Page 4 | `claude-sonnet-4-5` | `freeform` · `json_generation` |
| `monitoring-agent` | Page 5 | mode 1 → `gpt-4o-mini`, mode 2/4/5 → `gemini-2-5-flash-preview`, mode 3 → `claude-sonnet-4-5` | modes 1-5 |

### Monitoring Agent — 5 modes

| Mode | Déclencheur | Comportement | Calendar update |
|------|-------------|-------------|-----------------|
| 1 — Pré-event brief | J-2 avant publication | Checklist lecture (max 3 points) | Non |
| 2 — Revue trimestrielle | J+1 après publication | Statut hypothèses + flag RAS/REVIEW_REQUIRED | Oui |
| 3 — Décision Review | Escalade manuelle ou auto | Diagnostic + test Munger + décision | Oui |
| 4 — Sector Pulse | J+1 résultats pair | Score -5→+5 sur hypothèses surveillées | Oui |
| 5 — Routing d'alerte | Après Mode 2/4 si REVIEW_REQUIRED | thesis_agent_regime3 ou opportunity_agent | Non |

### Synchro agents — logique synced/unsynced

`agent_prompts.synced` contrôle l'accès aux pages et jobs :

| Agent hors sync | Pages bloquées (overlay non-dismissible) | Scheduler |
|-----------------|----------------------------------------|-----------|
| `opportunity-agent` | Page 3, Page DÉBAT | Watchlist threshold suspendu |
| `thesis-agent` | Page 4 | Aucun job auto affecté |
| `monitoring-agent` | Page 5 | **Tous les jobs monitoring** mis en `blocked_sync` |

**Règle PATCH `/admin/agents/{name}`** : `synced` passe à `FALSE` uniquement si `prompt_text` est modifié. Modifier le `dust_agent_id` ou `dust_agent_url` ne change **pas** le statut synced.

**Flux sync** : modifier prompt dans l'UI Dust → PATCH `prompt_text` → `synced=FALSE` → overlay apparaît → coller dans Dust → POST `/admin/agents/{name}/sync` → `synced=TRUE, version++` → overlay disparaît.

### Injection du mode dans les messages Dust

Le code Python injecte le mode en tête de message avant l'envoi :
```python
full_message = f"[mode: {mode}]\n\n{message}"
```
Les agents Dust lisent ce préfixe pour adapter leur comportement. L'agent est **stateless** — tout l'historique pertinent doit être inclus dans le message `json_generation`.

### Handoff Opportunity → Thesis

Construit depuis l'état édité de la Col 2 (Page 3) au moment du clic "Lancer la thèse approfondie". Lit les champs actuels du `brief_json` (y compris éditions manuelles), pas le JSON brut de l'agent.

---

## Base de données

Driver : **asyncpg** (direct, pas SQLAlchemy).
Paramètres SQL : `$1`, `$2`… (jamais `%s`).
Codec JSONB configuré dans `db/database.py` → les champs JSONB sont des dicts Python nativement. **Ne jamais faire `json.dumps()` pour écrire en DB.**

`DATABASE_URL` : `postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio`
Le préfixe `+asyncpg` est strippé automatiquement dans `database.py`.

### Tables V1 (migration 013 — 2026-05-30)

| Table | PK | Description |
|-------|-----|-------------|
| `tickers` | `id TEXT` | Univers de titres — statuts: `watchlist`/`portfolio`/`archived`. `id` peut être `PUB-XXXXXXXX`, `PRIV-XXXXXXXX` ou le symbole direct. Colonne `ticker_symbol` = symbole yfinance réel (migration 018) |
| `portfolio_positions` | SERIAL | Positions V1 — shares, purchase_price, purchase_date, thesis_id, ownership_pct_at_entry, current_ownership_pct |
| `cash_movements` | SERIAL | Flux cash — types: `deposit`/`withdrawal`/`buy`/`sell` |
| `price_alerts` | SERIAL | Alertes de cours — direction: `above`/`below`, active, triggered_at |
| `opportunity_briefs` | SERIAL | Briefs d'analyse — statuts: `draft`/`validated`/`passed`/`dismissed` |
| `opportunity_messages` | SERIAL | Historique chat opportunity-agent (brief_id ou debate_id) |
| `theses` | SERIAL | Thèses V1 — statuts: `draft`/`active`/`under_review`/`superseded`/`invalidated` |
| `thesis_messages` | SERIAL | Historique chat thesis-agent |
| `monitoring_sessions` | SERIAL | Sessions monitoring — modes 1-5, alert_level: `RAS`/`REVIEW_REQUIRED`/`CRITICAL`, statuts: `pending`/`running`/`completed`/`blocked_sync`/`pending_manual`/`archived`, colonne `calendar_event_id` (migration 019) |
| `monitoring_messages` | SERIAL | Messages supplémentaires dans une session |
| `calendar_events` | SERIAL | Calendrier V1 — source: `thesis_agent`/`monitoring_agent`/`manual`/`conviction_override`. Colonne `brief_triggered BOOL` (migration 019) |
| `conviction_debates` | SERIAL | Débats option C — statuts: `open`/`closed_pass`/`closed_monitor`/`closed_proceed` |
| `agent_prompts` | SERIAL | Prompts Dust — synced, version, dust_agent_id, dust_agent_url |
| `private_company_profiles` | ticker_id FK | Profil PE/VC — stage, valuation, ARR, investors, next_event (migration 017) |
| `portfolio_settings` | — | Paramètres globaux — `dust_auto_enabled BOOL DEFAULT TRUE` (migration 020) |

### Tables V0 (conservées en DB, frontend supprimé)

Les pages V0 ont été supprimées le 2026-06-18. Les données restent en DB et les API legacy backend sont toujours actives (utilisées par les schedulers V0).

| Table | Note |
|-------|------|
| `positions` | Positions V0 (CAP, TSLA) — données historiques, plus de frontend |
| `v0_theses` | Renommée depuis `theses` lors de la migration 013 |
| `v0_calendar_events` | Renommée depuis `calendar_events` lors de la migration 013 |
| `hypotheses`, `reviews`, `sector_pulses`, `peers` | Données V0 intactes |
| `watchlist` | Watchlist V0 — distincte de `tickers`, utilisée par `_refresh_watchlist_prices` |
| `market_snapshots`, `earnings_calendar_cache` | Partagées V0/V1 |
| `dust_budget` | Budget mensuel Dust — partagé V0/V1 |

### Migrations appliquées
001 → 024. Migration 013 = schéma V1 complet (2026-05-30). Migration 017 = support PE/VC. Migration 018 = `tickers.ticker_symbol`. Migration 019 = `calendar_events.brief_triggered` + `monitoring_sessions.calendar_event_id`. Migration 020 = `portfolio_settings.dust_auto_enabled` + statut `pending_manual`. Migrations 021/022 = mise à jour prompt monitoring-agent en DB. Migration 023 = `portfolio_positions.purchase_price_eur`. **Migration 024 = V2 Knowledge Platform (socle couche 3)** : `knowledge_documents`, `knowledge_entries` versionnées/append-only (A1), `analysis_knowledge_refs` (snapshot figé A1/A2), `eu_ir_scrapers`, `knowledge_curator_reports` (mvdd|readiness|lint), extension pgvector + index HNSW, vue `knowledge_federation_export` (enveloppe commune). Seed NVDA cas-pilote : `db/seeds/nvda_v2_knowledge_seed.sql` (10 fact_financial Tier A EDGAR + 5 qualitatifs llm_memory → readiness `thin_qualitative`).
**Migration 025 = V2 Agents / Provider (socle couche 2)** : `agent_prompts` += `provider` (`dust`|`deepinfra`), `model`, `tools_json` (JSONB), **`flow_version`** (`v1`|`v2`) ; unicité passée à `(agent_name, flow_version)`. Insert des **12 agents V2** (flow_version='v2', provider='deepinfra', modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`, prompts = préambule + corps de `roadmap/V3/provenance-cards/prompts/`). Générateur reproductible `db/migrations/_gen_025.py`. `tools_json` (web_search/fetch_url/query_knowledge) sur `search-worker` uniquement.
**Migration 027 = V2 Embeddings** : `knowledge_entries.embedding` passe de `vector(768)` à **`vector(1024)`** (modèle `BAAI/bge-m3`, multilingue, via DeepInfra `/v1/openai/embeddings`), index HNSW reconstruit en `vector_cosine_ops` (opérateur `<=>` inchangé) + index **partiel** `idx_knowledge_entries_unembedded` sur `embedding IS NULL`. Motif : le corpus est en **français** et `bge-base-en-v1.5` (anglais seul) ratait les entrées financières EDGAR Tier A — bench sur corpus réel, hit@3 4/7 contre 7/7. Justification chiffrée dans l'en-tête de la migration et dans `roadmap/V3/00-REPRISE.md`.
**Migration 028 = `knowledge_entries.covers`** : le champ MVDD que l'entry fonde (pertinence du contenu au gate, pas seulement le tier).
**Migration 029 = `covers` en `TEXT[]` + chemins COMPLETS + index GIN** : une entry fonde plusieurs champs (#19 en porte 3), et `description` étant requis par `business_model` ET `produits`, un nom nu ferait passer l'autre. Backfill relu des 17 entries qualitatives legacy NVDA (#19-#35), que le search-worker n'avait jamais taguées. C'est l'index que le curator interroge désormais pour rendre son verdict — cf. convention #29.
**Migration 030 = V2 theses_flow (lot 7, acte de décision)** : table **`theses_v2`** (jugement V2, disjoint de `theses` qui reste le pivot V1) portant la décision figée — `validation_json`, `verdict` (CHECK `PROCEED`|`PROCEED_AVEC_CONDITIONS`), `position_sizing_pct`, `valuation_range`, `conditions_entree TEXT[]`, `hypotheses`, `risk_acks`, `pre_mortem_acked`, `risk_matrix_acked`, lignée `research_memo_id`/`synthesis_analysis_id`. CHECK `theses_v2_active_complete` : une thèse `active` doit avoir tous ses champs de décision, les deux acquittements à TRUE, et des conditions non vides si `PROCEED_AVEC_CONDITIONS` (le CHECK ne mord que sur `active` — un `draft` reste libre). Côté **faits du monde** (cf. convention #34) : `portfolio_positions` et `calendar_events` reçoivent une colonne **`thesis_v2_id`** nullable + CHECK d'exclusivité `thesis_id IS NULL OR thesis_v2_id IS NULL`, et `event_router_v1.py` filtre `AND ce.thesis_v2_id IS NULL` sur ses 4 requêtes. Route : **`POST /v2/theses/{id}/validate`** — préfixée `/v2` parce que `POST /theses/{id}/validate` existe **déjà** en V1 (`api/thesis_v2.py`, où « v2 » désigne la 2ᵉ version du fichier V1). Contrat `ThesisValidation` dans `app/contracts/decision_validate_schema.py`.
**Migration 031 = V2 monitoring_flow (lot 8, la surveillance)** : table **`monitoring_sessions_v2`** (session de suivi V2, disjointe de `monitoring_sessions` qui reste le pivot V1) — `thesis_v2_id`, `mode` (1-6), `trigger_type`, `calendar_event_id`, `result_json`, `context_sent`, `raw_content`, colonnes de routage `alert_level` / `verdict` / `routing_suggestion`, télémétrie `provider_used` / `model_used` / `tokens_in` / `tokens_out` / `cost_usd`. Les **CHECK contraignent les domaines par mode** : `alert_level` n'existe qu'au **mode 2**, `verdict` qu'aux modes **3 et 6**, avec des vocabulaires distincts (`RE_SYNTHESE` n'existe qu'au mode 3). Ajoute `calendar_events.session_v2_id` et `portfolio_settings.v2_auto_enabled` (**FALSE par défaut** — pas de dépense automatique non supervisée). Routes : `POST|GET /v2/theses/{id}/monitoring`, `GET /v2/monitoring/{session_id}`. Contrats `app/contracts/monitoring_modes_1_5_schema.py` + `monitoring_mode6_schema.py`. Routeur calendaire `calendar/event_router_v2.py` (job scheduler **séparé** à 7h15, 10 min après le V1).
⚠️ **Ce CLAUDE.md a longtemps affirmé « le lot 8 n'en demande pas a priori » — c'était FAUX**, et c'est le genre d'affirmation qui se vérifie au lieu de se supposer : `monitoring_sessions.thesis_id` porte une FK vers `theses`, la table **V1**. Une session V2 n'a littéralement pas de ligne où pointer. Même schéma que le `LEFT JOIN` du lot 7 : l'énoncé « ça marche nativement » n'a pas résisté à une lecture du schéma.
**Collision 023 résolue** : la spec V2 §14 nommait `023_v2_knowledge_platform.sql`, mais 023 était pris par `purchase_price_eur`. Toute la séquence V2 décale de +1 → 024 knowledge platform (fait), 025 agents/provider (fait), 026 investment_analyses + research_memos (fait), 027 embeddings 1024d (fait), 028 covers (fait), 029 covers[] (fait), 030 theses_flow (fait), 031 monitoring_flow (fait) → **032** exit/calibration.
**Migration 032 = V2 exit / calibration / débat (lot 9, le dernier maillon)** : `exit_plans` (plan de
sortie **thèse-driven** — `origine` contrainte au domaine §11, `plan_json`, `exit_status`, index unique
partiel `uq_exit_plan_actif` interdisant deux plans ouverts sur la même thèse), `exit_executions` (une
ligne par tranche vendue, `cash_movement_id` vers le fait de trésorerie), `post_mortems_v2` (bilan
unique par thèse, `duree_jours`/`performance_pct` **calculés**, `lesson_entry_ids` vers les
`knowledge_entries` type `lesson_learned`, + colonnes `calibration_*` portant l'acte A5),
`calibration_registry` (le registre prédit/réalisé, grain = une paire par ligne),
`conviction_debates_v2` (débat V2 disjoint de `conviction_debates` V1 — `challenge_json`,
`resolution_suggeree`, `invalidation_franchie`, CHECK anti-complaisance interdisant
`resolution_suggeree='closed_proceed'` quand `invalidation_franchie`). `price_alerts` reçoit
`exit_plan_id` + `alert_type` (une alerte de tranche est adossée au plan, pas flottante).
**Migration 033 = resynchro du prompt `debate-agent`** (générateur `_gen_prompt_refresh_20260901.py`,
cf. convention #39).
**Migration 034 = l'axe `nature` d'une knowledge_entry (capacité 1 de la roadmap 02)** : colonne
`knowledge_entries.nature` (`mesure`|`evenement`|`interpretation`), CHECK nommé
`knowledge_entries_nature_check`, index PARTIEL `(ticker_id, nature)` sur les entrées courantes,
`NOT NULL` posé dans la même migration parce que le backfill couvre **les 180 lignes** (y compris
les superseded, qu'`analysis_knowledge_refs` continue de lire). Générateur `_gen_034.py` : il
n'écrit **aucune règle en SQL**, il appelle `derive_nature` sur un instantané `psql` et n'émet que
des listes d'ids — un `UPDATE … CASE WHEN` aurait ré-implémenté la règle dans un second langage
(#46). Répartition obtenue : **66 `mesure` / 68 `interpretation` / 0 `evenement`** sur les entrées
actives.
**Migration 035 = `content_structured.poste_kind` sur le socle EDGAR (F16)** : la clef d'identité
#43 dépend du type de poste, mais son discriminant n'était **pas dans la ligne** — absent de tout le
socle NVDA et MSFT (écrit avant F4), soit **19 des 43 faits financiers courants** non keyables par un
LECTEUR. Générateur `_gen_035.py` : il importe `edgar_feed.POSTES` (détenteur unique de la règle
flux/bilan, #46), refuse d'émettre si une ligne stockée contredit `POSTES`, et n'écrit que des listes
d'ids — un `UPDATE … CASE WHEN metric IN (…)` aurait ré-implémenté `POSTES[].flow` en SQL. Périmètre
délibérément borné aux 8 postes du socle : les métriques dérivées (`roic`, `levier`,
`fcf_conversion`…) et les données de marché (`yfinance`) n'ont **aucune identité réglementaire** au
sens de #43, leur en inventer une serait un faux. Appliquée : `UPDATE 18` (flow) + `UPDATE 9` (stock),
garde `DO $$ … RAISE EXCEPTION` nommée et **éprouvée en négatif avant application** (elle rendait 27).
**Migration 036 = archivage de la grappe V2 et dévocabularisation (lot 2b, 2026-09-10)** : les 15
tables V2 passent en schéma **`archive_v2`** par `SET SCHEMA` (**rien n'est détruit** — 180 entries
restent lisibles), `public.knowledge_entries` est recréée **amaigrie de 8 colonnes**
(`conflict_entry_id`, `covers`, `has_conflict`, `is_deleted`, `question_priority`,
`question_status`, `resolves_entry_id`, `reviewed_by_user` — les 7 premières mesurées à **zéro
écriture** par `tools/inventaire_grappe_v2.py` avant retrait, jamais supposé), et `entry_type` est
ramené à un vocabulaire **fermé de 5 jetons** (`agent_synthesis`, `analysis`, `fact_financial`,
`fact_qualitative`, `fact_statistical`) par CHECK. `covers` n'était pas morte mais **mal placée**
(#57) → table de liaison versionnée `question_coverage`.
**Migration 037 = resynchro des prompts `ingestion-agent` et `search-worker`** : #39 rendu
non-optionnel — `ProducedEntry` étant `extra="forbid"`, un exemple JSON portant encore `covers` ou
`"entry_type": "risk"` fait rejeter **l'entry entière**, soit une panne **totale et muette**
qu'aucun check hors ligne ne voit (leurs fixtures sont déjà conformes). Générateur `_gen_037.py`
avec garde de génération sur les **formes d'émission** (`"covers":` avec guillemets et deux-points,
jamais le mot nu — `feedback_grep_interdit_lit_sa_propre_enonciation`). Test négatif
`checks/negatif_037.sh` **bidirectionnel** (satisfiabilité 5/0 puis une mutation par garde).
⚠️ Elle ne touche **pas** `base_rate` dans les 10 autres prompts : c'est un **champ de contrat**
(règle 2), homonyme de l'`entry_type` renommé — un assert le dit **en positif**.
**Migration 038 = `archive_v2` en lecture seule pour `portfolio_user`** : `SET SCHEMA` déplace la
table avec ses privilèges de TABLE mais **pas** l'`USAGE` sur le schéma neuf — toute lecture
échouait en `InsufficientPrivilegeError`, et les 15 tables archivées arrivaient au contraire
**écrivables** (K2 a rougi au premier passage). GRANT USAGE+SELECT, REVOKE du reste. ⚠️ Les gardes
interrogent `pg_class` **par OID** : `has_table_privilege(role, 'archive_v2.'||nom, …)` a reçu
`archive_v2.positions` — un nom de `public` recollé au mauvais schéma, le filtre n'étant pas
garanti évalué avant la fonction. Un faux ROUGE ici, un faux VERT si le nom avait existé des deux
côtés. **Un OID ne se résout pas : il désigne.**
**Migration 039 = les tables de la CHAÎNE DE COLLECTE (chantier v3, lot 2c)** : trois tables
ADDITIVES, `collection_plans` (le plan, daté et versionné §3.6, id propre + `created_at` — jamais
d'unicité sur `(ticker, framework, version)`, qui interdirait de re-planifier), `collection_plan_items`
(une ligne par ingrédient, CHECK `collection_plan_items_charge` redisant `traduit` ⟺ métrique+source
+ancre / `inobtenable` ⟺ motif seul — projection du contrat `collection_plan_schema`, jamais une
conception de schéma indépendante), et `framework_mandates` (les mandats de collecte). L'AGENT
dicte la table : contrat, pont `valider_pont_collection_plan` et aiguilleur `collecteur.aiguiller_plan`
écrits et éprouvés avant la migration. Gardes éprouvées en négatif par `check_collecte_persist.py`.
**Migration 040 = `framework_answers` / `framework_dispenses` (chantier v3, lot 3 maillon 2)** :
remplace le dict codé en dur `DECLARED_NONBLOCKING_GAPS`. `framework_answers` est **append-only et
versionnée** (A1, comme `knowledge_entries` — une correction ne fait jamais d'UPDATE, elle INSERT et
pose `superseded_by` sur l'ancienne ligne), lignée `(ticker_id, framework, framework_version,
question_id, analyste)` : voir #64 pour pourquoi `framework_version` y est et pourquoi `analyste` y
est (§3.4, N ≥ 1 — deux analystes ne se supersèdent jamais). CHECK `framework_answers_statut` sur le
vocabulaire fermé à 4 valeurs, index partiel sur les lignes courantes. `framework_dispenses` :
`UNIQUE (ticker_id, framework_id, framework_version, question_id)`, `motif` obligatoire, idempotente
(`ON CONFLICT ... DO UPDATE`). Écriture : `app/agents/v2/framework_persist.py`
(`persist_answer`/`persist_dispense`, #35 — l'appelant doit envelopper `persist_answer` dans
`async with conn.transaction():`, ses deux écritures liées ne sont pas atomiques par elles-mêmes).
Détail + garde : `check_framework_persist.py` (13/0), `negatif_framework_persist.sh` (6 mutations/0
échec, zéro résidu vérifié en base réelle).
**Migration 042 = `appariement_cartes`** (carte d'appariement persistable, grain ticker × framework ×
version — cf. #68/#71).
**Migration 043 = réconciliation `framework_mandates` contrat↔table** (cf. #77) : `ingredient_id`
rendu NULLABLE, colonnes `mandat`/`ticker_id`/`statut_avant`/`statut_apres`/`consomme_at`/
`entry_ids_produits`, origine ouverte à `comite`, CHECK `forme` + CHECK `trace`.
**Migration 044 = rejeu de `derive_nature` après l'entrée de `content` dans la règle** (garde du
guichet, #78) : **16 entries requalifiées** `mesure` → `interpretation` (leur prose annonce sa propre
dérivation). Générateur `_gen_044.py` — il n'écrit **aucune règle en SQL**, il appelle `derive_nature`
sur un instantané **JSON par ligne** (et non le `psql -tA` des 034/035 : `content` est de la prose
multi-lignes contenant des `|`) et n'émet que des listes d'ids (#46). ⚠️ `reliability_tier` /
`reliability_score` **pas touchés** (#50). ⚠️ Sa garde est un **invariant GLOBAL** (`mesure = 213`),
pas un accusé de réception de son propre UPDATE : la première version comptait les lignes de sa
propre liste `id IN (…)` **après** les avoir écrites — une garde nourrie de sa propre valeur, donc
invisible (#70). Éprouvée en négatif AVANT application : jouée seule sur l'état d'avant, elle RAISE
sur 229.
**Migration 045 = les deux dates d'une pièce (#79)** : `knowledge_entries` reçoit `date_du_fait`,
`date_du_document`, `portee_temporelle` (CHECK sur le vocabulaire fermé `constatee|prospective|
indatable`) et `periode_visee`. `source_date` **reste** la colonne de tri, mais elle n'est plus
reçue : elle est **DÉRIVÉE** des deux dates par `app/knowledge/datation.py` (détenteur unique #46),
comme `nature` l'est au guichet depuis la 034. Additive et sans backfill par modèle : les lignes
antérieures ont `portee_temporelle IS NULL`, qui désigne un **héritage à re-collecter** (174 entries
courantes, dénombrées par `check_datation.py` §7) et non un quatrième état du vocabulaire.
**Migration 048 = le registre du comité (#84)** : `comite_decisions`, procès-verbal APPEND-ONLY des
décisions `acquitter`/`renvoyer` (auteur, instant, version, réponse lue, motif non blanc, dernier fait
important connu). Le rôle applicatif n'a que SELECT/INSERT, un trigger refuse toute réécriture même au
propriétaire, garde `048/K1` sur les droits. Éprouvée par `negatif_048.sh` (14/0) sur copie de la base.
**Migration 049 = le registre des pièces écartées (#87)** : `pieces_ecartees` — une pièce déposée au
dossier d'un émetteur alors qu'elle porte sur une AUTRE société en SORT (la ligne quitte
`knowledge_entries`, donc aucun agent ne la lit plus, par construction) et y est conservée ENTIÈRE en
JSONB avec ses rattachements aux questions, qui/quand/pourquoi. Append-only, lecture seule pour le rôle
applicatif. Appliquée le 2026-09-26 sur les 5 pièces Ryvu du dossier RVMD (#665-667, #671, #672).
Éprouvée par `negatif_049.sh` (19/0) sur copie de la base.
**Migration 050 = les notes flash (#90)** : `notes_flash` — la lecture d'un dépôt 8-K/6-K que la
forme ne qualifie pas : types retenus (dérivés par le code), passages cités, documents lus, modèle, version
du CATALOGUE D'ÉVÉNEMENTS (`types_evenement_version`, distincte de `schema_version`). Une note par
`(accession, catalogue_version)`, append-only (le rôle applicatif écrit et lit, trigger contre toute
réécriture). Deux formes exclusives par CHECK : lisible (≥ 1 type, jamais `a_qualifier`) ou illisible
(`{a_qualifier}` + motif). Éprouvée par `negatif_050.sh` (18/0) sur copie de la base.
**Migration 051 = le modèle de valorisation (#98)** : `modeles_valorisation` (une ligne par VERSION proposée,
le `ModeleValorisation` entier en JSONB, CHECK que la ligne et son contenu disent le même titre / la même
version / le même schéma) et `modeles_valorisation_decisions` (PV : `signer` | `ecarter`, auteur et motif non
blancs, fourchette signée ordonnée ssi signer, UNE décision par version). Append-only sur les deux (droits +
trigger, garde `051/K1`). Appliquée le 2026-09-29, tables vides. Éprouvée par `negatif_051.sh` (26/0).
Prochaine migration : **052**.
**Migration 052 = la période d'une ligne de plan (#113)** : `collection_plan_items.periode` (nullable,
quatre valeurs). **Migration 053 = `cumul_publie`, cinquième valeur (#119)** : un cumul tel que publié
par l'émetteur, jamais recalculé — détail convention #119. Prochaine migration : **054**.

### Deux espaces disjoints V1 / V2 (2026-08-22)

La V2 tourne **en parallèle** de la V1 tant qu'elle n'est pas validée. **Seul l'univers de tickers est partagé** ; tout le reste est disjoint (agents `flow_version='v2'`, base de connaissance, analyses, routes frontend `/v2`, nav V2). Les 3 agents V1 (dust) restent `flow_version='v1'` et intacts.
- **Backend** : abstraction provider provider-agnostic dans `backend/app/agents/providers/` (`AgentProvider` + `DeepInfraProvider` OpenAI-compat + `DustProvider` shim + factory `get_agent_provider(agent_name, flow_version)` lisant `agent_prompts`). Var d'env : `DEEPINFRA_API_KEY`. Les classes agent V1 continuent d'appeler `DustClient` directement (inchangées).
- **Alimentation de la connaissance (2026-08-23)** : `knowledge/websearch.py` (backends de recherche
  interchangeables Exa/Serper + `fetch_url` + `classify_source_type`), `agents/v2/tools.py` (exécuteurs
  des 3 outils du `tools_json`), `agents/v2/worker.py` (`search-worker`, contrat C1) et
  `api/knowledge_v2.py` (`POST /tickers/{id}/knowledge/search`, `GET /knowledge/search/status`).
  `runner.run_tool_json_agent()` = boucle d'outils + tour de clôture JSON validé, joué par un clone de
  l'agent **sans outils** (sinon le modèle peut répondre par un tool_call de plus au lieu du contrat).
  Vérifications exécutables : `backend/checks/` (voir son README).
- **Frontend** : `/` = page de choix V1/V2 ; espace V1 = routes existantes ; espace V2 = `/v2/**` (shell). `_app.js` choisit la nav selon le préfixe. `GET /admin/agents?flow_version=` filtre par flux ; `PATCH/POST /admin/agents/{name}` prend `?flow_version=` (défaut v1) ; `synced=FALSE` sur édition de prompt uniquement si provider='dust'.

---

## API REST — Endpoints

Listing exhaustif des endpoints V1 + V0 (legacy) : **`REFERENCE.md`** § API REST.
Les routers sont dans `backend/app/api/` — `grep` fait foi si divergence.

## Scheduling automatique

| Heure | Jour | Job | Détail |
|-------|------|-----|--------|
| `*/5` | lun-ven 9h-17h | `_check_price_alerts_v1` | Vérifie price_alerts V1, notifie Slack |
| 7h05 | tous | `_daily_check_v1` | EventRouterV1 — mode 1 (J-2), mode 2 (J+1), mode 4 (sector pulse J+1), mode 3 (conviction_review jour J) — lit `calendar_events` V1 (`thesis_v2_id IS NULL`) |
| 7h00 | tous | `_notes_flash_matin` | Notes flash (#91) — pour chaque titre suivi (`tickers.status` ∈ portfolio/watchlist), lit les dépôts 8-K/6-K « à qualifier » non lus. Dépense gardée par `v2_auto_enabled` : FALSE ⟹ **recensement gratuit**, Slack seulement si un dépôt non lu a été publié depuis la veille ; TRUE ⟹ notes écrites (≤ 20 par titre et par matin), Slack avec types, passage et refus. Titre hors EDGAR = « hors flux », silencieux |
| 7h15 | tous | `_daily_check_v2` | EventRouterV2 — modes 1/2/4/3 aux mêmes échéances + **mode 6** (revue annuelle, **avec rattrapage** `scheduled_date <= today`, cf. #38) — lit `calendar_events` du flux V2 (`thesis_v2_id IS NOT NULL`, INNER JOIN `theses_v2` active). Job **séparé** du V1 à dessein : les enchaîner ferait qu'une exception d'un flux empêcherait l'autre de tourner. Gouverné par `portfolio_settings.v2_auto_enabled` (**FALSE** par défaut → session `pending_manual` avec contexte, notifiée, au lieu d'une dépense) |
| 7h30 | tous | `_refresh_watchlist_prices` | Prix watchlist V0 via `get_m1()` |
| 8h00 | lundi | `_weekly_review` | Snapshot portfolio V0 → digest Slack |
| 8h15 | lundi | `_refresh_market_temperature` | FRED — Buffett indicator, CAPE |
| 8h30 | lundi | `_refresh_all_calendars` | Earnings dates via `CalendarBuilder.refresh_all()` |
| 8h45 | lundi | `_weekly_m1_snapshot` | `refresh_m1(context='weekly')` toutes positions V0, 2s entre tickers |
| 18h00 | vendredi | `_refresh_watchlist_peer_calendars` | Peer calendars (écrit dans `v0_calendar_events`) |

**Note** : `_daily_check` V0 (7h00, `v0_calendar_events`) est désactivé depuis 2026-06-14. Ne pas le réactiver — remplacé par `_daily_check_v1`.
`_daily_check_v1` → `EventRouterV1` dans `calendar/event_router_v1.py` (604 lignes, actif en prod). Spec complète : `roadmap/archive/v1/scheduler-v1-monitoring-page.md`.

---

## Couche données — DataService

Tous les accès données de marché passent par `app/data_collection/data_service.py`.
**Ne jamais appeler `collect_quantitative()` directement.**

```python
m1 = await DataService().get_m1(ticker, settings.FMP_API_KEY)      # cache (dashboard)
m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime2")  # forcé (agents)
```

TTL Redis : M1 complet → `pt:m1:{ticker}` 4h | Earnings date → `pt:calendar:{ticker}` 7j

### Tickers et symboles yfinance

`TICKER_EXCHANGE_MAP` dans `m1_quantitative.py` mappe les tickers sans suffixe vers yfinance :
```python
"CAP": "CAP.PA",  # Euronext Paris
```
**Règle V1 (migration 018)** : ne jamais utiliser `tickers.id` directement pour les appels yfinance/FMP/DataService. Toujours lire `tickers.ticker_symbol` (colonne dédiée, nullable). Si `ticker_symbol IS NULL` → ticker ajouté sans symbole boursier (ex: PRIV- ou PUB-UUID), DataService doit être ignoré. Les `tickers.id` anciens ont été backfillés avec leur symbole, mais les nouveaux tickers cotés sans symbole reçoivent un id `PUB-XXXXXXXX`.

---

## Variables d'environnement

Liste complète (Dust, Slack, Marché, DB/Cache, App) : **`REFERENCE.md`** § Variables d'environnement.
Les valeurs réelles vivent dans `backend/.env` et `frontend/.env` (chmod 600, gitignored) — jamais
committées. Copies de référence : `/root/secrets/coolify-env-backup/portfolio-{backend,frontend}.env`.

## Priorités en attente

### P3 — après 1ère clôture de position (stubs existants, à compléter)

Les fichiers existent déjà comme stubs vides — ne pas les recréer, les compléter :

| Fichier | Fonctionnalité |
|---------|---------------|
| `portfolio/post_mortem.py` | Post-mortem automatisé sur exit / réduction >50% |
| `learning/analyst_tracker.py` | Calcul verdict analystes J+30/J+90 |
| `learning/thesis_versioning.py` | Archivage + nouvelle version post-R3 |
| `learning/pattern_library.py` | Enrichissement depuis post-mortems |

`market_snapshots` accumule les données depuis 2026-05-12 — les P3 auront du recul historique.

### Schémas sectoriels à compléter
- `sector_schemas/Luxury.json` — kpis, queries, peers
- `sector_schemas/Industrial.json` — idem

---

## Données existantes

### Positions V0 (dans tables V0 — données historiques, plus de frontend)
- **Capgemini (CAP)** : entrée 2026-05-01 à 102€, 8.5% allocation, 6 hypothèses H1-H6, peers CTSH (T1) / ACN (T2). Scénarios Bear -5.2% / Central +12.4% / Bull +23.7% CAGR 5 ans.
- **Tesla (TSLA)** : position active, thèse définie.

### Note réseau — obsolète depuis le 2026-09-03
Coolify créait un réseau par app (`portfolio0tracker000000000_infra-net` au lieu de `infra-net`),
qu'un `post_deployment_command` devait corriger après chaque déploiement. Cette bricole n'existe
plus : la stack déclare `networks: [coolify]` en réseau **externe**, donc les conteneurs
rejoignent directement le bon réseau à la création. Le réseau parasite a été supprimé.

## Base de connaissance (Knowledge Platform)

Invariants vivants : `roadmap/V3/03-spec-frameworks.md` §1.7 (feeds déterministes, `query_knowledge`
vectoriel bge-m3 1024d, migrations 024→035) et `roadmap/V3/doctrine-trois-axes.md` (les trois axes).
Architecture d'origine (historique, supersédée) : `roadmap/archive/v2/roadmap-1786358823158-architecture-v2-knowledge-platform.md`
(LLM Wiki Pattern Karpathy — Ingest/Query/Lint, Postgres+pgvector, pivot Markdown `/knowledge/`,
entrées append-only versionnées, `reliability_score` par source).

**Ce projet est l'implémentation de référence** de la charte transverse
`../../KNOWLEDGE_ARCHITECTURE.md`. Contrainte à respecter lors de l'implémentation :

- Exposer une vue **`knowledge_federation_export`** projetant `knowledge_entries` vers l'« enveloppe
  document commune » (contrat §3 de la charte). Modèle : `../../templates/knowledge-base/federation_export.example.sql`.
- `doc_id` = `portfolio-tracker:postgres:knowledge_entry/{id}`, `source='postgres'`, `visibility='public'`.
- Ne monter **aucune** couche fédérée (`db_knowledge_federation`) tant qu'un besoin multi-source
  réel n'existe pas — seul l'export est requis dès maintenant.

