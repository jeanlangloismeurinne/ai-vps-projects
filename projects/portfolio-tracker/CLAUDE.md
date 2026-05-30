# CLAUDE.md — portfolio-tracker

## Contexte

Système de suivi d'investissement boursier long terme sur VPS Hetzner (jlmvpscode.duckdns.org).
URL : `portfolio.jlmvpscode.duckdns.org`
Backend : port 8050 → `/api` | Frontend : port 8051 → `/`
Workspace Dust : `plm-siege`

**État (2026-05-30) : migration V1 déployée en production. Architecture agents scindée (opportunity / thesis / monitoring). Pages V1 actives. Pages V0 conservées pour les données historiques CAP/TSLA.**

---

## Migration V1 — Checklist post-déploiement

Après déploiement initial, faire une fois :
1. Aller sur `/admin` → créer les 3 agents dans l'UI Dust (`plm-siege`) en copiant les prompts affichés
2. Renseigner le `dust_agent_id` de chaque agent dans la Page Admin (zone mise en avant)
3. Cliquer "✓ Marquer synchronisé" pour chaque agent
4. Ajouter dans Coolify (backend) : `DUST_OPPORTUNITY_AGENT_ID`, `DUST_THESIS_AGENT_ID`, `DUST_MONITORING_AGENT_ID`
5. Optionnel : `SLACK_WEBHOOK_URL` pour les notifications V1 (webhook entrant Slack, distinct du bot Socket Mode V0)

**Tables V0 préservées** : `v0_theses` et `v0_calendar_events` — données historiques CAP/TSLA intactes.
**Permissions DB** : `ALTER DEFAULT PRIVILEGES` configuré sur `db_portfolio` → les futures migrations créées par `admin` sont automatiquement accessibles à `portfolio_user`.

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.12 / FastAPI / APScheduler (asyncio) |
| Database | PostgreSQL 16 — `shared-postgres:5432` — base `db_portfolio` |
| Cache | Redis 7 — `shared-redis:6379` |
| Frontend | Next.js 14 / React 18 / Tailwind CSS 3.4 |
| Agents IA | Dust.tt API — workspace `plm-siege` |
| Notifications V0 | Slack bot @ai_vps_jlm (Socket Mode) — `#portfolio-management` `C0B13KANHPD` |
| Notifications V1 | Slack webhook entrant (`SLACK_WEBHOOK_URL`) |
| Données marché | yfinance (EOD) + FMP API (fondamentaux) + FRED (macro) |

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
│   │   │   ├── # V1 (nouveau)
│   │   │   ├── opportunity_agent.py    # 3 modes, gemini-2-5-flash-preview
│   │   │   ├── thesis_agent.py         # 2 modes, claude-sonnet-4-5
│   │   │   └── monitoring_agent_v1.py  # 5 modes, modèles distincts
│   │   ├── calendar/
│   │   │   ├── event_router.py         # Déclenchements J-2/J+1 (utilise v0_calendar_events)
│   │   │   ├── calendar_builder.py     # Refresh dates earnings
│   │   │   └── watchlist_monitor.py    # Surveillance prix watchlist V0
│   │   ├── data_collection/            # M1/M2/M3/M4 + assembler + cache + data_service
│   │   ├── db/
│   │   │   ├── database.py             # asyncpg pool + codec JSONB
│   │   │   ├── models.py               # Pydantic request/response models
│   │   │   └── migrations/             # 001 → 013 (V1 = migration 013)
│   │   ├── notifications/
│   │   │   ├── slack_notifier.py       # V0 — Socket Mode (bot)
│   │   │   └── slack_webhook.py        # V1 — webhook entrant (plus simple)
│   │   └── portfolio/                  # portfolio_view, concentration_checker
│   └── sector_schemas/                 # IT_Services.json (complet), Luxury/Industrial (squelettes)
└── frontend/
    ├── pages/
    │   ├── # V0 (legacy)
    │   ├── index.js                    # Dashboard portfolio V0
    │   ├── position/[id].js            # Détail position V0
    │   ├── watchlist.js                # Watchlist V0
    │   ├── calendar.js                 # Calendrier V0
    │   ├── analysts.js                 # Analystes V0
    │   ├── market-temperature.js       # FRED V0
    │   ├── # V1 (nouveau)
    │   ├── portfolio.js                # Page 0 — /portfolio
    │   ├── watchlist-v2.js             # Page 1 — /watchlist-v2
    │   ├── admin.js                    # Page Admin — /admin
    │   └── ticker/[ticker_id]/
    │       ├── index.js                # Page 2 — fiche entreprise
    │       ├── opportunity/[...slug].js # Page 3 — analyse opportunité (slug='new' ou brief_id)
    │       ├── thesis/[thesis_id].js   # Page 4 — thèse d'investissement
    │       ├── monitoring/[session_id].js # Page 5 — session monitoring
    │       ├── decision/[thesis_id].js # Page DÉCISION
    │       └── debate/[debate_id].js   # Page DÉBAT
    └── components/
        ├── # V0 (legacy)
        ├── HypothesisScorecard.js, ThesisTimeline.js, ThesisChat.js, ...
        ├── # V1 (nouveau)
        ├── AgentChat.js               # Chat générique réutilisé sur Pages 3/4/5/DÉBAT
        ├── AgentSyncOverlay.js        # Overlay non-dismissible si agent hors sync
        ├── PriceChart.js              # SVG pur (sans dépendances), gradient area
        ├── InvestmentBriefEditor.js   # Col 2 Page 3 (screening, anomalie, catalyseurs...)
        ├── ThesisEditorV2.js          # Col 2 Page 4 (scénarios, H1-H7, seuils, pairs...)
        └── CalendarEditor.js          # Bandeau calendrier Page 4
```

---

## Base de données

Driver : **asyncpg** (direct, pas SQLAlchemy).
Paramètres SQL : `$1`, `$2`… (jamais `%s`).
Codec JSONB configuré dans `db/database.py` → les champs JSONB sont des dicts Python nativement. **Ne jamais faire `json.dumps()` pour écrire en DB.**

`DATABASE_URL` format Coolify : `postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio`
Le préfixe `+asyncpg` est strippé automatiquement dans `database.py`.

### Tables V1 (migration 013 — 2026-05-30)

| Table | PK | Description |
|-------|-----|-------------|
| `tickers` | `id TEXT` ("CAP.PA") | Univers de titres — statuts: `watchlist`/`portfolio`/`archived` |
| `portfolio_positions` | SERIAL | Positions V1 — shares, purchase_price, purchase_date, thesis_id |
| `cash_movements` | SERIAL | Flux cash — types: `deposit`/`withdrawal`/`buy`/`sell` |
| `price_alerts` | SERIAL | Alertes de cours — direction: `above`/`below`, active, triggered_at |
| `opportunity_briefs` | SERIAL | Briefs d'analyse — statuts: `draft`/`validated`/`passed`/`dismissed` |
| `opportunity_messages` | SERIAL | Historique chat opportunity-agent (brief_id ou debate_id) |
| `theses` | SERIAL | Thèses V1 — statuts: `draft`/`active`/`under_review`/`superseded`/`invalidated` |
| `thesis_messages` | SERIAL | Historique chat thesis-agent |
| `monitoring_sessions` | SERIAL | Sessions monitoring — modes 1-5, alert_level: `RAS`/`REVIEW_REQUIRED`/`CRITICAL` |
| `monitoring_messages` | SERIAL | Messages supplémentaires dans une session |
| `calendar_events` | SERIAL | Calendrier V1 — source: `thesis_agent`/`monitoring_agent`/`manual`/`conviction_override` |
| `conviction_debates` | SERIAL | Débats option C — statuts: `open`/`closed_pass`/`closed_monitor`/`closed_proceed` |
| `agent_prompts` | SERIAL | Prompts Dust — synced, version, dust_agent_id, dust_agent_url |

### Tables V0 (conservées, legacy)

| Table | Note |
|-------|------|
| `positions` | Positions V0 (CAP, TSLA) — toujours utilisées par les pages V0 |
| `v0_theses` | Renommée depuis `theses` lors de la migration 013 |
| `v0_calendar_events` | Renommée depuis `calendar_events` lors de la migration 013 |
| `hypotheses`, `reviews`, `sector_pulses`, `peers` | Données V0 intactes |
| `watchlist` | Watchlist V0 — distincte de `tickers` |
| `market_snapshots`, `earnings_calendar_cache` | Partagées V0/V1 |
| `dust_budget` | Budget mensuel Dust — partagé V0/V1 |

### Migrations appliquées
001 → 013. Migration 013 = schéma V1 complet (créé le 2026-05-30).
Prochaine migration : `014_*.sql`.

---

## API REST V1 — Endpoints

```
# Tickers
GET    /tickers                               Liste (?status=watchlist|portfolio|archived)
POST   /tickers                               Créer {id, name, exchange, sector}
GET    /tickers/{ticker_id}                   Détail + prix actuel
PATCH  /tickers/{ticker_id}                   Mettre à jour (status, etc.)
GET    /tickers/{ticker_id}/price-history     Historique OHLCV (yfinance direct, ?period=1y|5y|max)
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

## Scheduling automatique

| Heure | Jour | Job | Détail |
|-------|------|-----|--------|
| `*/5` | lun-ven 9h-17h | `_check_price_alerts_v1` | Vérifie price_alerts V1, notifie Slack webhook |
| 7h00 | tous | `_daily_check` | Brief J-2, Régime 2 J+1, sector pulses V0 (utilise `v0_calendar_events`) |
| 7h30 | tous | `_refresh_watchlist_prices` | Prix watchlist V0 via `get_m1()` |
| 8h00 | lundi | `_weekly_review` | Snapshot portfolio V0 → digest Slack |
| 8h15 | lundi | `_refresh_market_temperature` | FRED — Buffett indicator, CAPE |
| 8h30 | lundi | `_refresh_all_calendars` | Earnings dates via `CalendarBuilder.refresh_all()` |
| 8h45 | lundi | `_weekly_m1_snapshot` | `refresh_m1(context='weekly')` toutes positions V0, 2s entre tickers |
| 18h00 | vendredi | `_refresh_watchlist_peer_calendars` | Peer calendars (écrit dans `v0_calendar_events`) |

**Note V1** : le scheduler monitoring automatique (J-2/J+1 basé sur `calendar_events` V1) n'est pas encore implémenté — les sessions V1 se créent manuellement ou depuis `event_router.py` (à étendre).

---

## Couche données — DataService

Tous les accès données de marché passent par `app/data_collection/data_service.py`.
**Ne jamais appeler `collect_quantitative()` directement.**

```python
m1 = await DataService().get_m1(ticker, settings.FMP_API_KEY)      # cache (dashboard)
m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime2")  # forcé (agents)
```

TTL Redis : M1 complet → `pt:m1:{ticker}` 4h | Earnings date → `pt:calendar:{ticker}` 7j

### Tickers Euronext

`TICKER_EXCHANGE_MAP` dans `m1_quantitative.py` mappe les tickers sans suffixe vers yfinance :
```python
"CAP": "CAP.PA",  # Euronext Paris
```
**Règle V1** : les `tickers.id` peuvent déjà contenir le suffixe `.PA` — vérifier avant d'appliquer la map.

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
SLACK_WEBHOOK_URL=                    # V1 webhook entrant (optionnel)
SLACK_ALERT_CHANNEL=#portfolio-alerts # V1

# Marché
FMP_API_KEY=dpl0XXr5F5ElF2M5s70Qmd80Pi3xBS6k
FRED_API_KEY=                         # optionnel (indicateurs macro)
MARKET_DATA_PROVIDER=yfinance

# DB / Cache
DATABASE_URL=postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
REDIS_URL=redis://shared-redis:6379

# App
BASE_CURRENCY=EUR
MAX_SECTOR_CONCENTRATION_PCT=20.0
PULSE_ESCALATION_THRESHOLD=-3
```

---

## Conventions et pièges

### Généraux (V0 + V1)
1. **asyncpg** : paramètres `$1, $2`… pas `%s`. JSONB auto-décodé — ne pas `json.dumps()` avant INSERT.
2. **Labels Traefik** : explicites dans `docker-compose.yml` — pas d'auto-injection Coolify.
3. **env_file interdit** : Coolify injecte les variables directement.
4. **Rebuild ≠ Restart** : toujours déclencher un rebuild complet (PHP script), jamais restart.
5. **Commit + push AVANT** tout déclenchement de rebuild Coolify.
6. **Traefik + multi-réseaux** : `portfolio-frontend` a le custom label `traefik.docker.network=coolify`.
7. **yfinance `.calendar`** : retourne un dict, pas un DataFrame — tester `if cal:`, pas `if not cal.empty:`.
8. **DataService** : seul point d'accès données marché — ne pas appeler `collect_quantitative()` directement.

### Spécifiques V1
9. **Vérification sync avant appel Dust** : toute classe agent V1 appelle `_check_sync()` qui lève une exception si `agent_prompts.synced = FALSE`. Ne pas bypasser.
10. **PATCH agent ne change pas synced** : sauf si `prompt_text` est dans le payload. Modifier `dust_agent_id` seul → synced inchangé.
11. **`tickers.id` = clé lisible** : "CAP.PA", "TSLA" etc. — pas d'UUID. Peut déjà contenir le suffixe exchange.
12. **Handoff opportunity→thesis** : lit le `brief_json` édité en Col 2, pas le JSON brut de l'agent. Construit côté backend dans `POST /tickers/{id}/theses`.
13. **Validation thèse** : `POST /theses/{id}/validate` fait 4 choses atomiquement — `thesis.status='active'`, `tickers.status='portfolio'`, crée `portfolio_positions`, crée `cash_movements` (type='buy'), persiste `calendar_events`.
14. **Tables V0 renommées** : `theses` → `v0_theses`, `calendar_events` → `v0_calendar_events`. Le scheduler V0 (`_daily_check`, `_refresh_watchlist_peer_calendars`) écrit dans `v0_calendar_events`.
15. **Permissions DB** : `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES/SEQUENCES TO portfolio_user` — actif depuis 2026-05-30. Les nouvelles tables créées par `admin` sont automatiquement accessibles.
16. **Next.js routes imbriquées** : `pages/ticker/[ticker_id]/opportunity/[...slug].js` — `slug[0]` vaut `'new'` (création) ou l'ID numérique du brief.

### yfinance rate limiting
Yahoo Finance (Fastly CDN) : ~500 calls/h avec 1s de délai. En cas de 429, le crumb CSRF est corrompu → toutes les requêtes suivantes échouent. Le cache Redis/DB couvre la production normale.

---

## Priorités en attente

### V1 — scheduler monitoring automatique
Le `event_router.py` (V0) gère les déclenchements J-2/J+1 sur `v0_calendar_events`.
Il n'existe pas encore d'équivalent V1 qui lirait `calendar_events` (V1) et créerait des `monitoring_sessions` automatiquement. À implémenter dans `calendar/event_router_v1.py`.

### P3 — après 1ère clôture de position

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

### Positions V0 (dans tables V0)
- **Capgemini (CAP)** : entrée 2026-05-01 à 102€, 8.5% allocation, 6 hypothèses H1-H6, peers CTSH (T1) / ACN (T2). Scénarios Bear -5.2% / Central +12.4% / Bull +23.7% CAGR 5 ans.
- **Tesla (TSLA)** : position active, thèse définie.

### Note réseau infra-net
Le `post_deployment_command` Coolify connecte les containers à `infra-net`. Coolify génère `portfolio0tracker000000000_infra-net` au lieu de `infra-net` — la commande post-deploy corrige ça.
