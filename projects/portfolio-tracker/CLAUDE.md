# CLAUDE.md — portfolio-tracker

## Contexte

Système de suivi d'investissement boursier long terme sur VPS Hetzner (jlmvpscode.duckdns.org).
URL : `portfolio.jlmvpscode.duckdns.org`
Backend : port 8050 → `/api` | Frontend : port 8051 → `/`
Workspace Dust : `plm-siege`

**État (2026-06-18) : frontend V1 uniquement. Pages et composants V0 supprimés. Données historiques CAP/TSLA conservées dans les tables V0 en DB. Backend V0 (API legacy + schedulers) toujours actif.**

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
| Notifications V0 + V1 | Slack bot @ai_vps_jlm — `SLACK_BOT_TOKEN` + `chat.postMessage` → `#portfolio-management` `C0B13KANHPD` |
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

Arborescence complète backend/frontend (fichiers + rôles) : **`REFERENCE.md`** § Structure du repo.
`glob`/`grep` du code fait foi si divergence.

## Base de données

Driver : **asyncpg** (direct, pas SQLAlchemy).
Paramètres SQL : `$1`, `$2`… (jamais `%s`).
Codec JSONB configuré dans `db/database.py` → les champs JSONB sont des dicts Python nativement. **Ne jamais faire `json.dumps()` pour écrire en DB.**

`DATABASE_URL` format Coolify : `postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio`
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
**Migration 025 = V2 Agents / Provider (socle couche 2)** : `agent_prompts` += `provider` (`dust`|`deepinfra`), `model`, `tools_json` (JSONB), **`flow_version`** (`v1`|`v2`) ; unicité passée à `(agent_name, flow_version)`. Insert des **12 agents V2** (flow_version='v2', provider='deepinfra', modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`, prompts = préambule + corps de `roadmap/provenance-cards/prompts/`). Générateur reproductible `db/migrations/_gen_025.py`. `tools_json` (web_search/fetch_url/query_knowledge) sur `search-worker` uniquement.
**Migration 027 = V2 Embeddings** : `knowledge_entries.embedding` passe de `vector(768)` à **`vector(1024)`** (modèle `BAAI/bge-m3`, multilingue, via DeepInfra `/v1/openai/embeddings`), index HNSW reconstruit en `vector_cosine_ops` (opérateur `<=>` inchangé) + index **partiel** `idx_knowledge_entries_unembedded` sur `embedding IS NULL`. Motif : le corpus est en **français** et `bge-base-en-v1.5` (anglais seul) ratait les entrées financières EDGAR Tier A — bench sur corpus réel, hit@3 4/7 contre 7/7. Justification chiffrée dans l'en-tête de la migration et dans `roadmap/provenance-cards/00-REPRISE.md`.
**Migration 028 = `knowledge_entries.covers`** : le champ MVDD que l'entry fonde (pertinence du contenu au gate, pas seulement le tier).
**Migration 029 = `covers` en `TEXT[]` + chemins COMPLETS + index GIN** : une entry fonde plusieurs champs (#19 en porte 3), et `description` étant requis par `business_model` ET `produits`, un nom nu ferait passer l'autre. Backfill relu des 17 entries qualitatives legacy NVDA (#19-#35), que le search-worker n'avait jamais taguées. C'est l'index que le curator interroge désormais pour rendre son verdict — cf. convention #29.
**Migration 030 = V2 theses_flow (lot 7, acte de décision)** : table **`theses_v2`** (jugement V2, disjoint de `theses` qui reste le pivot V1) portant la décision figée — `validation_json`, `verdict` (CHECK `PROCEED`|`PROCEED_AVEC_CONDITIONS`), `position_sizing_pct`, `valuation_range`, `conditions_entree TEXT[]`, `hypotheses`, `risk_acks`, `pre_mortem_acked`, `risk_matrix_acked`, lignée `research_memo_id`/`synthesis_analysis_id`. CHECK `theses_v2_active_complete` : une thèse `active` doit avoir tous ses champs de décision, les deux acquittements à TRUE, et des conditions non vides si `PROCEED_AVEC_CONDITIONS` (le CHECK ne mord que sur `active` — un `draft` reste libre). Côté **faits du monde** (cf. convention #34) : `portfolio_positions` et `calendar_events` reçoivent une colonne **`thesis_v2_id`** nullable + CHECK d'exclusivité `thesis_id IS NULL OR thesis_v2_id IS NULL`, et `event_router_v1.py` filtre `AND ce.thesis_v2_id IS NULL` sur ses 4 requêtes. Route : **`POST /v2/theses/{id}/validate`** — préfixée `/v2` parce que `POST /theses/{id}/validate` existe **déjà** en V1 (`api/thesis_v2.py`, où « v2 » désigne la 2ᵉ version du fichier V1). Contrat `ThesisValidation` dans `app/contracts/decision_validate_schema.py`.
**Migration 031 = V2 monitoring_flow (lot 8, la surveillance)** : table **`monitoring_sessions_v2`** (session de suivi V2, disjointe de `monitoring_sessions` qui reste le pivot V1) — `thesis_v2_id`, `mode` (1-6), `trigger_type`, `calendar_event_id`, `result_json`, `context_sent`, `raw_content`, colonnes de routage `alert_level` / `verdict` / `routing_suggestion`, télémétrie `provider_used` / `model_used` / `tokens_in` / `tokens_out` / `cost_usd`. Les **CHECK contraignent les domaines par mode** : `alert_level` n'existe qu'au **mode 2**, `verdict` qu'aux modes **3 et 6**, avec des vocabulaires distincts (`RE_SYNTHESE` n'existe qu'au mode 3). Ajoute `calendar_events.session_v2_id` et `portfolio_settings.v2_auto_enabled` (**FALSE par défaut** — pas de dépense automatique non supervisée). Routes : `POST|GET /v2/theses/{id}/monitoring`, `GET /v2/monitoring/{session_id}`. Contrats `app/contracts/monitoring_modes_1_5_schema.py` + `monitoring_mode6_schema.py`. Routeur calendaire `calendar/event_router_v2.py` (job scheduler **séparé** à 7h15, 10 min après le V1).
⚠️ **Ce CLAUDE.md a longtemps affirmé « le lot 8 n'en demande pas a priori » — c'était FAUX**, et c'est le genre d'affirmation qui se vérifie au lieu de se supposer : `monitoring_sessions.thesis_id` porte une FK vers `theses`, la table **V1**. Une session V2 n'a littéralement pas de ligne où pointer. Même schéma que le `LEFT JOIN` du lot 7 : l'énoncé « ça marche nativement » n'a pas résisté à une lecture du schéma.
**Collision 023 résolue** : la spec V2 §14 nommait `023_v2_knowledge_platform.sql`, mais 023 était pris par `purchase_price_eur`. Toute la séquence V2 décale de +1 → 024 knowledge platform (fait), 025 agents/provider (fait), 026 investment_analyses + research_memos (fait), 027 embeddings 1024d (fait), 028 covers (fait), 029 covers[] (fait), 030 theses_flow (fait), 031 monitoring_flow (fait) → **032** exit/calibration.
Prochaine migration : `032_v2_exit_calibration.sql` (lot 9).

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
| 7h15 | tous | `_daily_check_v2` | EventRouterV2 — modes 1/2/4/3 aux mêmes échéances + **mode 6** (revue annuelle, **avec rattrapage** `scheduled_date <= today`, cf. #38) — lit `calendar_events` du flux V2 (`thesis_v2_id IS NOT NULL`, INNER JOIN `theses_v2` active). Job **séparé** du V1 à dessein : les enchaîner ferait qu'une exception d'un flux empêcherait l'autre de tourner. Gouverné par `portfolio_settings.v2_auto_enabled` (**FALSE** par défaut → session `pending_manual` avec contexte, notifiée, au lieu d'une dépense) |
| 7h30 | tous | `_refresh_watchlist_prices` | Prix watchlist V0 via `get_m1()` |
| 8h00 | lundi | `_weekly_review` | Snapshot portfolio V0 → digest Slack |
| 8h15 | lundi | `_refresh_market_temperature` | FRED — Buffett indicator, CAPE |
| 8h30 | lundi | `_refresh_all_calendars` | Earnings dates via `CalendarBuilder.refresh_all()` |
| 8h45 | lundi | `_weekly_m1_snapshot` | `refresh_m1(context='weekly')` toutes positions V0, 2s entre tickers |
| 18h00 | vendredi | `_refresh_watchlist_peer_calendars` | Peer calendars (écrit dans `v0_calendar_events`) |

**Note** : `_daily_check` V0 (7h00, `v0_calendar_events`) est désactivé depuis 2026-06-14. Ne pas le réactiver — remplacé par `_daily_check_v1`.
`_daily_check_v1` → `EventRouterV1` dans `calendar/event_router_v1.py` (604 lignes, actif en prod). Spec complète : `specs/scheduler-v1-monitoring-page.md`.

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
Les valeurs réelles vivent dans Coolify — jamais committées.

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
11. **`tickers.id` ≠ symbole yfinance** : depuis la migration 018, `tickers.id` est la PK stable mais peut être `PUB-XXXXXXXX` (ticker coté ajouté sans symbole), `PRIV-XXXXXXXX` (privé), ou directement le symbole (anciens tickers backfillés). **Utiliser `tickers.ticker_symbol`** pour tout appel DataService/yfinance/FMP. Si `ticker_symbol IS NULL`, ignorer DataService.
12. **Handoff opportunity→thesis** : lit le `brief_json` édité en Col 2, pas le JSON brut de l'agent. Construit côté backend dans `POST /tickers/{id}/theses`.
13. **Validation thèse** : `POST /theses/{id}/validate` fait 4 choses atomiquement — `thesis.status='active'`, `tickers.status='portfolio'`, crée `portfolio_positions`, crée `cash_movements` (type='buy'), persiste `calendar_events`.
14. **Tables V0 renommées** : `theses` → `v0_theses`, `calendar_events` → `v0_calendar_events`. Le scheduler V0 (`_daily_check`, `_refresh_watchlist_peer_calendars`) écrit dans `v0_calendar_events`.
15. **Permissions DB** : `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES/SEQUENCES TO portfolio_user` — actif depuis 2026-05-30. Les nouvelles tables créées par `admin` sont automatiquement accessibles.
16. **Next.js routes imbriquées** : `pages/ticker/[ticker_id]/opportunity/[...slug].js` — `slug[0]` vaut `'new'` (création) ou l'ID numérique du brief.
19. **Cohérence format JSON — règle des 3 points de synchronisation** : tout changement de structure de données (opportunity, thèse, thèse PE/VC) doit être répercuté simultanément sur les 3 points suivants — en omettre un crée des désynchronisations silencieuses :
    1. **Prompt Dust** (`agent_prompts` en DB → copié dans Dust) — le schéma JSON attendu en sortie de l'agent
    2. **Frontend** (`ThesisEditorV2.js`, `InvestmentBriefEditor.js`, pages ticker) — l'affichage et l'édition des champs
    3. **Import JSON manuel** (`POST /tickers/{id}/theses` via `ImportLegacyBody` dans `thesis_v2.py`) — les champs acceptés à l'import
17. **Migrations non auto-appliquées** : `startup()` dans `main.py` n'exécute aucune migration — il appelle uniquement `init_pool()` et `init_redis()`. Toute nouvelle migration doit être appliquée manuellement via `docker cp` (le heredoc `psql << 'EOF'` via `docker exec` échoue silencieusement — pas d'erreur, pas de changement) :
    ```bash
    docker cp /tmp/migration.sql shared-postgres:/tmp/migration.sql
    docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/migration.sql
    ```
18. **Architecture PE/VC (sociétés non cotées)** : `tickers.company_type = 'private'` est le discriminateur principal. Les agents Python injectent `[company_type: private]\n\n` en tête de message Dust — les prompts Dust détectent ce signal et appliquent toute la logique PE/VC (marqueurs "→ Non coté :"). Tables associées : `private_company_profiles` (stage, valuation, ARR, investors, next event) + colonnes `ownership_pct_at_entry` / `current_ownership_pct` sur `portfolio_positions`. La réponse JSON du monitoring mode 2 inclut un bloc `private_valuation_update` automatiquement parsé et appliqué à `private_company_profiles` par `monitoring_v2.py`. DataService (yfinance/FMP) est ignoré pour les tickers privés.
20. **`pending_manual` dans monitoring_sessions** : statut ajouté en migration 020. Indique qu'une session a été planifiée par le scheduler mais non exécutée car `portfolio_settings.dust_auto_enabled = FALSE`. Différent de `blocked_sync` (agent Dust non synchronisé). L'utilisateur peut déclencher manuellement depuis la Page 5.
21. **`hypotheses_reviewed[]` vs `hypothesis_reviews[]`** : `hypothesis_reviews[]` est la sortie brute de l'agent Dust (modes 2/3/4). `monitoring_v2.py` appelle `_normalize_monitoring_result()` qui fusionne ces reviews avec les hypothèses de la thèse pour produire `hypotheses_reviewed[]` — champ enrichi utilisé par la Page 5 (contient `text`, `weight`, `kpi_metric`, `kpi_unit`, `alert_threshold`, `invalidation_threshold`, `status`, `observation`). Toujours lire `hypotheses_reviewed[]` côté frontend, pas `hypothesis_reviews[]`.
22. **Recherche knowledge (V2)** : `query_knowledge()` est **vectorielle** (`embedding <=> $vec::vector`, bge-m3 1024d). Le chemin texte ILIKE est un **repli strict** — jamais un co-classement. Mesuré sur corpus réel : fusionner les deux (RRF) **dégrade** le résultat (MRR 0.905 → 0.655), le signal lexical français étant trop faible. Ne pas « améliorer » en hybride sans re-mesurer. Les entrées à `embedding IS NULL` sont invisibles au vectoriel : elles sont rattrapées par une passe texte à quota réservé (`_RESCUE_QUOTA`), qui doit tourner **inconditionnellement** — la conditionner au budget restant la rend morte dès que le corpus dépasse `limit`.
23. **pgvector et `atttypmod`** : la dimension y est stockée **telle quelle**, sans le `+4` (VARHDRSZ) des types natifs. Un `atttypmod - 4` réflexe lit `1020` pour un `vector(1024)`. Dans une migration, cette erreur fait échouer la garde d'idempotence et **efface tout le corpus d'embeddings** au rejeu. Comparer `format_type(atttypid, atttypmod)` à `'vector(N)'`.
24. **search-worker — le modèle ne qualifie jamais sa propre source (V2)** : dans `agents/v2/worker.py`,
    `_apply_deterministic_overrides()` recalcule en Python tout ce qui est dérivable, sur le modèle de
    `curator._apply_deterministic_overrides`. `source_type` est déterminé par le **domaine**
    (`classify_source_type`), pas par la déclaration de l'agent — dans les **deux sens** : la
    sur-qualification gonfle le score (`edgar_official` sur un blog), la sous-qualification fait tomber
    une bonne source sous le plancher `reliability_min` et creuse un **faux trou de couverture**
    (`ir.nvidia.com` déclaré `web_search_generic`). Seul l'aveu `llm_memory` est honoré tel quel : il
    porte sur ce que le modèle a fait, pas sur la source. `reliability_score`/`tier`/`note` viennent
    ensuite de `compute_reliability()`, et l'`ExecutionDeclaration` (tokens/coût) est **mesurée**,
    jamais déclarée. La validation `WorkerExchange` est un **filet** après correction, pas le mécanisme.
25. **Un échec de recherche n'est jamais un résultat vide (V2)** : `web_search` sans clé lève
    `SearchUnavailable` (→ HTTP 503), et `run_search_worker()` refuse de démarrer si aucun backend
    n'est configuré. Motif : un worker sans recherche rend un `not_found` parfaitement bien formé que
    le curator lit comme « cette information n'existe pas » alors qu'elle n'a **pas été cherchée** —
    c'est le mode de panne qui a fait écarter SearXNG. Même règle pour `fetch_url` : une page
    volumineuse dont on extrait < 200 caractères (SPA rendue en JS — constaté sur
    `investor.nvidia.com` : HTTP 200, titre correct, **0 caractère**) lève une erreur explicite au lieu
    de rendre un texte vide. Basculer Exa ↔ Serper ↔ autre = une classe dans `knowledge/websearch.py`,
    sans toucher au `tools_json` en DB ni au prompt de l'agent.
26. **`fetch_url` a deux chemins, et le domaine décide de ce qui vaut la peine d'être lu (V2)** :
    récupération directe d'abord, puis repli sur `SearchBackend.fetch_contents()` (Exa `POST
    /contents`) si l'échec est **récupérable**. 404/410 = absence réelle → aucun repli, on lève tout
    de suite ; 401/403/429/5xx/SPA-vide/PDF = refus opposé à **cette IP** → Exa a souvent la page
    dans son cache de crawl. Le champ `via` (`direct` | `search_backend_cache`) accompagne le retour.
    Motif, mesuré sur NVDA le 2026-08-23 : le premier run réel a produit 5 entrées, **5 rejetées sous
    le plancher** `reliability_min=0.60`, parce que les seules pages lisibles depuis le VPS étaient
    des blogs (`web_search_generic` = 0.50, plafond structurellement sous le plancher). Les sources
    qualifiantes étaient inaccessibles : CNBC (`financial_press` 0.75) en 403, `investor.nvidia.com`
    (`company_ir_official` 0.90) en SPA vide. Exa rend 12 189 et 29 909 caractères de ces deux pages.
    **Ne pas croire qu'un User-Agent règle le 403** : testé le 2026-08-23, bot déclaré et Chrome
    desktop donnent des codes strictement identiques (CNBC 403, Reuters 401, SeekingAlpha 403,
    MarketWatch 401) — le filtrage est sur la réputation d'IP, pas sur l'en-tête.
27. **On ne tronque pas un document, on y cherche (V2)** : `fetch_url` récupère la page ENTIÈRE
    (`_RETRIEVAL_MAX_CHARS` = 400 000) puis `document_search.select_relevant()` n'en rend que les
    passages qui répondent à la question du mandat, recomposés **dans l'ordre du document** avec des
    marqueurs `[… N caractères omis …]`. Motif mesuré le 2026-08-23 : dans le 10-K NVDA FY2026
    (356 990 car.), la concentration client est à **37,6 %** du texte — le plafond de 20 000 en
    captait 5,5 %, soit la page de garde et le sommaire, et Exa `/contents` tronquait en tête lui
    aussi. Aucun des deux chemins n'atteignait le corps du dépôt. Le même défaut existe sur un
    article de presse : dans le comparatif CNBC de 12 189 car., « Maia » est à 71,5 % — **il n'existe
    pas de taille de troncature défendable a priori**, elle dépend du genre du document. Après
    sélection : 356 990 → 19 275 car. (17 passages sur 387), et l'article CNBC passe entier
    (`mode: whole`, aucune coupure). Le mode est **toujours déclaré** dans `extract.mode`
    (`whole` | `relevance` | `lexical` | `head`) et une phrase l'explicite au modèle : un extrait doit
    se lire comme un extrait, sans quoi il conclut « le 10-K ne mentionne pas X » là où c'est la
    sélection qui a coupé. `document_search` ne connaît ni URL ni HTTP (texte + question seulement) :
    il sert aussi les **documents uploadés à la main**, seul canal pour les sociétés non cotées.
28. **La provenance est vérifiée, pas déclarée (V2)** : `RetrievalLog` journalise ce que les outils
    ont réellement rapporté (`full` = `fetch_url` abouti, `excerpt` = texte d'un résultat de
    recherche, `link` = URL vue sans contenu), et `_verify_provenance()` y confronte chaque
    `source_url` avant scoring. Jamais rapportée ou simple lien → **rétrogradée en `llm_memory`**
    (0.40, revue humaine) ; extrait seul → score du domaine conservé mais revue humaine exigée.
    Motif : la convention #24 retire au modèle le choix de son `source_type`, mais **pas celui de son
    URL** — or l'URL fixe le domaine, donc le source_type, donc le score. Le contournement était
    total et involontaire : run C sur NVDA (2026-08-23), 5 entrées `edgar_official` **0.94 tier A**
    pointant sec.gov, alors qu'aucune URL sec.gov n'avait jamais été récupérée de toute la vie du
    conteneur. Corollaire, **une entrée = un document** : une entry citant plusieurs dépôts
    (`_cited_documents` : 10-K, 10-Q, 8-K, 20-F, DEF 14A…) sous un seul `source_url` attribue à l'un
    les propos de l'autre — elle entre (la base est append-only, G3 interdit de réécrire son contenu)
    mais marquée `requires_human_review` avec le motif dans `reliability_note`.
29. **La couverture se LIT dans un index, elle ne se demande pas au modèle (V2, migration 029)** :
    `curator.recompute_coverage` interroge `knowledge_entries.covers` (`TEXT[]`, chemins COMPLETS
    `dimension.champ`) — pour chaque champ requis, ∃ une entry courante qui le porte à un tier ≥
    plancher. Le LLM ne produit plus que le narratif (`rationale`, `gaps`, incertitudes) ;
    `fondations` est RÉÉCRIT depuis l'index. Motif : la version précédente filtrait les `entry_ids`
    que le LLM avait CITÉS — un véto sur la citation, pas un index. Elle fermait le sur-crédit (entry
    hors-sujet) mais pas le sous-crédit : une entry adéquate non citée creusait un **faux creux**, et
    le rattachement par-champ n'étant pas déterministe, le verdict oscillait `not_ready` ↔
    `thin_qualitative` **à corpus strictement figé** (NVDA, rapports #11/#13/#14, données
    identiques). Trois corollaires : (a) le chemin est COMPLET parce que `description` est requis par
    `business_model` ET `produits` — un nom nu ferait passer l'autre ; (b) poser un tag, c'est voter
    sur le verdict, donc `covers` n'est écrit que par des chemins déterministes (feeds, `field_path`
    du mandat du worker, backfill relu en migration) et la déclaration spontanée d'un modèle est
    filtrée par le vocabulaire fermé `MVDD_FIELD_PATHS` (même esprit que #24) ; (c) `champs_requis`
    et `tier_plancher` étant le dernier levier du modèle sur le verdict, `_exigences()` lui laisse
    les RESSERRER (ajouter un champ, relever un plancher) mais jamais les desserrer. Une entry non
    taguée ne fonde plus rien — elle reste dans le corpus narratif et le context_pack.

30. **Le concept XBRL se choisit par FRAÎCHEUR, jamais par convention (V2, `knowledge/edgar_feed.py`)** :
    un concept us-gaap répond `200` avec un historique qui s'est **arrêté il y a quinze ans** — la
    requête réussit, la donnée est périmée, et rien ne le signale. Mesuré : `Revenues` pour MSFT a
    pour dernier point **2010-06-30** quand `RevenueFromContractWithCustomerExcludingAssessedTax`
    va jusqu'à 2026-06-30 ; `PaymentsToAcquirePropertyPlantAndEquipment` s'arrête en **2012-01-29**
    pour NVDA quand `PaymentsToAcquireProductiveAssets` est à jour. Le « piège capex NVDA » qui
    était documenté comme un cas particulier était en fait cette règle générale. Donc : chaque poste
    porte une LISTE de concepts candidats et `select_concept()` retient celui dont le point est le
    plus proche de l'ancre du bilan — « le premier tag qui répond » est un bug silencieux. Corollaire
    d'amorçage : `resolve_cik()` (registre `company_tickers.json` de la SEC) rend le socle EDGAR
    atteignable pour **tout** ticker, là où `financials` n'était fondable que via le seed NVDA écrit
    à la main. Les faits EDGAR bruts ne sont délibérément PAS tagués `covers` : ce sont les intrants
    des ratios, pas les champs MVDD eux-mêmes (cf. #29).

31. **Ce qui décrit UN émetteur ne vit jamais dans une constante globale (V2)** : trouvé en exerçant
    la chaîne sur un 2ᵉ ticker (MSFT, 2026-08-30) — deux mécanismes se croyaient génériques alors que
    seule leur *mécanique* l'était. (a) `curator.DECLARED_NONBLOCKING_GAPS` dispensait
    `business_model.recurrence_pct` pour *tout* ticker au motif que « NVIDIA est un business
    hardware-dominant » : MSFT héritait donc en silence d'un passe-droit sur un champ qu'il publie
    précisément (Microsoft Cloud, RPO), le champ n'était **ni fondé ni compté comme manque**, et le
    libellé parlant de NVIDIA partait dans les `incertitudes_investissables` de MSFT. (b) Les
    `SYNTHESIS_TARGETS` annonçaient « génériques par construction » avec des `query`/`guidance`
    rédigées pour NVIDIA (« segments Data Center Gaming », « coût par GPU », « écosystème CUDA »,
    « TSMC/HBM ») : sur un autre émetteur, la requête sémantique cherchait le mauvais vocabulaire et
    la consigne demandait de synthétiser une entreprise qui n'est pas celle analysée — dans le seul
    agent dont toute la valeur est de ne pas sortir de son corpus. Règle : une dispense se clef sur
    l'émetteur (`nonblocking_gaps_for(ticker_id)`, défaut = **aucune**, donc le champ BLOQUE — on
    refuse un `ready` de trop, on n'en accorde pas un par héritage) ; un descripteur de champ est un
    gabarit paramétré par `{company}` et ne nomme aucun acteur, l'émetteur venant des entries citées.
    Test de non-régression dans `check_readiness_recompute.py` §13 et `check_synthesis_feed.py` §7.
    Plus largement : **une constante globale qui contient un fait sur un émetteur est un bug qui
    attend le 2ᵉ ticker.**

32. **Un plancher qu'aucun domaine ne peut atteindre est un champ infondable déguisé en lacune (V2)** :
    `marche.croissance_marche_historique` avait DEUX aménagements construits pour lui —
    `FIELD_PLANCHER_OVERRIDES` abaissant son plancher à `B` (une taille de marché n'est jamais une
    donnée d'émetteur) et une dispense `DECLARED_NONBLOCKING_GAPS` sur NVDA. Aucun des deux ne pouvait
    marcher : les cabinets qui produisent ces chiffres (Synergy, Canalys, Omdia, Gartner, IDC)
    tombaient tous dans `web_search_generic` (C+/0.50), donc **sous** le plancher B (0.65) qu'on venait
    d'abaisser pour eux. Mesuré sur MSFT le 2026-08-30 : deux mandats, 35 puis 15 URL rapportées,
    recherche réelle, provenance vérifiée, `sous-plancher:5` puis `sous-plancher:3` — et un `not_found`
    que le curator lit comme « ce chiffre n'existe pas » alors qu'il avait été trouvé cinq fois.
    Le trou se bouche dans la **table de domaines** (`websearch._REPUTABLE_SUFFIXES`, plafond B : un
    organisme qui publie SES PROPRES chiffres est primaire pour ce chiffre-là sans être une source
    d'émetteur ni de presse), pas par une dispense de plus. Corollaire de méthode : quand on abaisse un
    plancher, **vérifier dans la foulée qu'au moins un `source_type` l'atteint** — deux garde-fous
    réglés séparément peuvent rendre un champ inatteignable, et l'échec se présente alors comme une
    absence de donnée. Test : `check_provenance.py` §8, qui confronte la table de domaines au plancher
    effectif du champ au lieu de les tester chacun de son côté.

33. **Le site d'un émetteur se reconnaît PAR ÉMETTEUR, et sur deux niveaux (V2, 2026-08-31)** :
    application directe de #31, trouvée là où elle était annoncée. `nvidia.com` vivait en dur dans
    `websearch._REPUTABLE_SUFFIXES` et Microsoft n'avait rien, si bien que
    `microsoft.com/en-us/investor/…` — de l'IR officiel — était classé `web_search_generic` (0.50),
    **sous le plancher `reliability_min=0.60`** : l'entry était rejetée et le champ paraissait
    infondable alors que la source était la meilleure possible. Cause : Microsoft publie son IR sur
    un **chemin**, pas sur un sous-domaine `ir.`, que `_IR_HOST_PATTERN` était seul à savoir lire.
    Donc `classify_source_type(url, ticker_id)` et un registre `issuer_domains_for(ticker_id)`
    (défaut **vide** — aucune promotion par héritage, comme `nonblocking_gaps_for`), à **deux
    niveaux** : domaine de l'émetteur **+ chemin IR** → `company_ir_official` (0.90) ; domaine de
    l'émetteur **hors** section IR (page produit, salle de presse) → `web_search_reputable` (B, le
    plafond qu'avait `nvidia.com`, rendu au seul NVDA). Le niveau bas existe parce qu'une page
    marketing n'est pas de l'information réglementée ; le registre parce que `microsoft.com` n'est un
    site d'émetteur **que d'une analyse MSFT** — sur une analyse NVDA, c'est le site d'un concurrent.
    **Corollaire de méthode, le plus transposable** : quand on ajoute une règle spécifique, on ne
    resserre PAS la règle générique au passage. `_IR_HOST_PATTERN` reste volontairement générique —
    le restreindre au registre ferait tomber `ir.<concurrent>.com` de 0.90 à 0.50 sur toute analyse,
    soit un faux trou de couverture creusé par le correctif censé en boucher un (#32). Le changement
    ne peut donc que promouvoir, jamais démoter, hormis le retrait délibéré de `nvidia.com` du global.
    **Pourquoi un registre écrit à la main** : EDGAR `submissions` expose `website` et
    `investorWebsite`, mais les deux sont **vides** — vérifié sur NVDA, AAPL, MSFT, GOOGL, AMZN,
    cinq fois la chaîne vide. Deviner le domaine depuis la raison sociale promouvrait un homonyme à
    0.90, soit la sur-qualification que #24 retire au modèle. ⚠️ **Ajouter l'entrée du registre en
    même temps que le ticker.** Enfin, `ticker_id` est **fermé dans `build_tool_executors`** au même
    titre que `query` et `log` : il décide du score, donc il ne peut pas être un argument du modèle
    (#28). Tests : `check_search_worker.py` §1bis (la table) et **§2bis (le câblage** — une table
    juste ne sert à rien si le ticker n'arrive pas jusqu'à l'appel, et c'est le seul défaut que
    §1bis ne peut pas voir).

34. **Les jugements sont disjoints, les faits du monde sont PARTAGÉS (V2, migration 030)** : la règle
    qui tranche « nouvelle table ou colonnes en plus ? » quand deux flux cohabitent. Un **jugement**
    (`theses` | `theses_v2`) est l'opinion d'un flux : le dupliquer est sain, chaque flux a la
    sienne. Un **fait du monde** (`tickers`, `portfolio_positions`, `cash_movements`,
    `calendar_events`) décrit ce qui s'est réellement passé : le dupliquer donnerait **deux soldes de
    trésorerie sur de l'argent réel**. Donc table séparée pour le jugement, **colonne discriminante**
    (`thesis_v2_id`, sœur nullable de `thesis_id`) + CHECK d'exclusivité pour le fait. Corollaire à ne
    pas rater : le CHECK d'exclusivité est **par ligne**, pas par ticker — un même titre peut porter
    une position V1 **et** une position V2, et toute vue qui agrège sans filtrer le flux double-compte
    (constaté sur MSFT : `portfolio_v2.py` lit toutes les positions ouvertes, la page V1 affiche donc
    la position V2). ⚠️ **Le partage crée une obligation de filtrage dans les DEUX sens** :
    `_daily_check_v1` faisait un `LEFT JOIN theses … AND th.status='active'` — un LEFT JOIN **rend la
    ligne même sans thèse jointe** — sans aucun garde `thesis_json IS NULL` en aval : le scheduler V1
    aurait appelé l'**agent Dust V1 sur une thèse inexistante**, silencieusement et avec dépense
    réelle. Vérifier le JOIN, ne pas le supposer : `AND ce.thesis_v2_id IS NULL` sur les 4 requêtes.

35. **`get_db_session()` n'ouvre AUCUNE transaction** : il *acquiert* une connexion du pool
    (`async with _pool.acquire() as conn: yield conn`) et chaque `execute` part en **autocommit**. La
    validation V1 documentée « 4 écritures atomiques » (convention #13) **ne l'est donc pas** : une
    panne au milieu laisse une thèse `active` sans position, ou une position sans mouvement de
    trésorerie. L'atomicité doit être **explicite** — `async with conn.transaction():` — comme le fait
    `agents/v2/decision.py`. Corollaire : les appels réseau (FX, calendrier) se font **avant**
    l'ouverture de la transaction, on ne tient pas de verrou pendant un aller-retour yfinance. V1 est
    délibérément laissée telle quelle (hors périmètre, risque de régression) : ne pas lire #13 comme
    une garantie.

36. **Un contrat de décision ne vaut que par ce que le corps HTTP n'expose PAS (V2, G2)** : le
    `ValidateV2Body` du validate V2 n'accepte que les **acquittements** (`risk_acks`,
    `pre_mortem_acked`) et les **faits d'exécution** (titres, prix, date). `verdict`,
    `position_sizing_pct`, `conditions_entree`, `hypotheses`, `valuation_range` et la synthèse sont
    **lus en base** : les accepter du client rendrait les 17 garde-fous décoratifs — il suffirait
    d'envoyer une synthèse complaisante pour valider n'importe quoi. `risk_matrix_acked` est
    **dérivé** (la bijection `risk_acks` ↔ `risques_acceptes` vaut acquittement), jamais demandé :
    on ne fait pas déclarer ce qui est calculable (même esprit que #24). Un sizing autre que le
    recommandé n'est **pas** un paramètre du validate — il se trace en amont dans la synthèse
    (`position_sizing.override_utilisateur`, A7), ce qui le rend auditable au lieu d'être un argument
    qu'on passe en douce. La `valuation_range` est **dérivée** du research memo (`iv_range` +
    `dcf_scenarios.base`) et jamais reconstituée par moyenne des bornes : ce serait inventer une
    donnée que l'analyse n'a pas produite. Test : `check_decision_validate.py` **§8**, qui inspecte
    `model_fields` — la seule vérification qui tienne, parce qu'un commentaire ne contraint rien.

37. **Un contrat valide un objet, JAMAIS la cohérence entre deux (V2, lot 8)** : c'est la limite
    structurelle de Pydantic, et elle est invisible depuis le schéma — d'où un garde-fou qui paraît
    tenir alors qu'il est contournable. Mesuré : `Mode2QuarterlyReview` **accepte parfaitement** une
    escalade motivée par une hypothèse **`H7` qui n'existe pas dans la thèse**. Contrat satisfait,
    `extra='forbid'` satisfait — et pourtant l'**anti-churn est mort**, puisqu'il dit « n'escalader
    que sur un seuil PRÉ-ENREGISTRÉ » et que rien, dans le schéma, ne relie la sortie du modèle à la
    liste figée au validate. Un invariant qui porte sur une **relation** entre deux objets se vérifie
    donc en code, jamais dans le contrat : `_valider_pont_hypotheses` fait trois vérifications
    distinctes — **référentiel** (ids cités ⊆ ids figés, tous modes citant des hypothèses),
    **exhaustivité** (ids figés ⊆ ids cités, **mode 6 seul**), **citations** (tout `entry_id` cité
    appartient aux entries réellement envoyées). L'asymétrie est délibérée : le référentiel protège
    tous les modes, l'exhaustivité n'est exigée que là où la carte figée la demande. Refus →
    `MonitoringRefused` → **HTTP 422** (la requête est valide, c'est la *sortie du modèle* qui est
    incohérente ; un 400 accuserait l'appelant) + session `failed` persistée, pour qu'un refus reste
    visible au lieu de disparaître. **Corollaire, le plus important** : les seuils figés sont en
    **lecture seule**. `_reporter_statuts` fusionne **par id** et n'écrit que `statut`,
    `derniere_revue`, `derniere_observation` — `seuil_alerte`, `seuil_invalidation`, `base_rate`,
    `source_entry_refs` ne sont jamais repris du modèle, sinon une revue pourrait **abaisser le seuil
    qu'elle vient de franchir**. Vérifié en réel : le modèle a rendu `seuil_invalidation: 5.0` là où
    la thèse portait `25.0` ; c'est `25.0` qui est resté. Test : `check_monitoring_v2.py` **§3**, qui
    prouve les **deux moitiés** — le contrat accepte le `H7`, le pont le refuse. Une vérification qui
    ne montrerait que le refus ne prouverait pas que le trou existait.

38. **Le rattrapage d'une échéance dépend de ce qu'elle commente, pas d'une règle uniforme (V2)** :
    dans `EventRouterV2`, seul le **mode 6** se rattrape (`scheduled_date <= today`) ; les modes
    calendaires restent sur une date **exacte**. Un brief J-2 ou une revue J+1 joués trois semaines
    plus tard commentent une publication déjà digérée — les rejouer coûte un appel modèle pour
    produire un commentaire périmé. Une revue **annuelle** en retard est au contraire **plus** urgente,
    pas moins : c'est la colonne vertébrale du suivi LT, et une journée d'indisponibilité du scheduler
    ne doit pas coûter une année de surveillance. Corollaire côté dépense : à `v2_auto_enabled=FALSE`
    l'échéance n'est **pas perdue** — session `pending_manual` persistée **avec son contexte exact**
    (`build_monitoring_context`) + notification. Et le drapeau calendaire est **consommé** dans le même
    temps, sinon le routeur recréerait la même attente chaque jour. En revanche un **échec** ne
    consomme rien : `_persister_echec` ne marque pas l'événement.

### yfinance rate limiting
Yahoo Finance (Fastly CDN) : ~500 calls/h avec 1s de délai. En cas de 429, le crumb CSRF est corrompu → toutes les requêtes suivantes échouent. Le cache Redis/DB couvre la production normale.

---

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

### Note réseau infra-net
Le `post_deployment_command` Coolify connecte les containers à `infra-net`. Coolify génère `portfolio0tracker000000000_infra-net` au lieu de `infra-net` — la commande post-deploy corrige ça.

## Base de connaissance (Knowledge Platform)

Spec : `roadmap/roadmap-1786358823158-architecture-v2-knowledge-platform.md` (LLM Wiki Pattern
Karpathy — Ingest/Query/Lint, Postgres+pgvector, pivot Markdown `/knowledge/`, entrées
append-only versionnées, `reliability_score` par source).

**Ce projet est l'implémentation de référence** de la charte transverse
`../../KNOWLEDGE_ARCHITECTURE.md`. Contrainte à respecter lors de l'implémentation :

- Exposer une vue **`knowledge_federation_export`** projetant `knowledge_entries` vers l'« enveloppe
  document commune » (contrat §3 de la charte). Modèle : `../../templates/knowledge-base/federation_export.example.sql`.
- `doc_id` = `portfolio-tracker:postgres:knowledge_entry/{id}`, `source='postgres'`, `visibility='public'`.
- Ne monter **aucune** couche fédérée (`db_knowledge_federation`) tant qu'un besoin multi-source
  réel n'existe pas — seul l'export est requis dès maintenant.

## Système de contrôle

Voir `CONTROL_SYSTEM.md` à la racine du repo pour le protocole complet.
Commande : **"execute le brief session pour portfolio-tracker"**
→ Lire `SESSION_BRIEF.md` à la racine de ce projet, puis suivre le protocole.
