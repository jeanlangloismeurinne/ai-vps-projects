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
4. Ajouter dans `backend/.env` : `DUST_OPPORTUNITY_AGENT_ID`, `DUST_THESIS_AGENT_ID`, `DUST_MONITORING_AGENT_ID`
   (ou `compose-deploy.sh portfolio-backend -e DUST_…=… --rebuild-only`)
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
**Migration 025 = V2 Agents / Provider (socle couche 2)** : `agent_prompts` += `provider` (`dust`|`deepinfra`), `model`, `tools_json` (JSONB), **`flow_version`** (`v1`|`v2`) ; unicité passée à `(agent_name, flow_version)`. Insert des **12 agents V2** (flow_version='v2', provider='deepinfra', modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`, prompts = préambule + corps de `roadmap/provenance-cards/prompts/`). Générateur reproductible `db/migrations/_gen_025.py`. `tools_json` (web_search/fetch_url/query_knowledge) sur `search-worker` uniquement.
**Migration 027 = V2 Embeddings** : `knowledge_entries.embedding` passe de `vector(768)` à **`vector(1024)`** (modèle `BAAI/bge-m3`, multilingue, via DeepInfra `/v1/openai/embeddings`), index HNSW reconstruit en `vector_cosine_ops` (opérateur `<=>` inchangé) + index **partiel** `idx_knowledge_entries_unembedded` sur `embedding IS NULL`. Motif : le corpus est en **français** et `bge-base-en-v1.5` (anglais seul) ratait les entrées financières EDGAR Tier A — bench sur corpus réel, hit@3 4/7 contre 7/7. Justification chiffrée dans l'en-tête de la migration et dans `roadmap/provenance-cards/00-REPRISE.md`.
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
actives. Prochaine migration : **035**.

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
Les valeurs réelles vivent dans `backend/.env` et `frontend/.env` (chmod 600, gitignored) — jamais
committées. Copies de référence : `/root/secrets/coolify-env-backup/portfolio-{backend,frontend}.env`.

## Conventions et pièges

### Généraux (V0 + V1)
1. **asyncpg** : paramètres `$1, $2`… pas `%s`. JSONB auto-décodé — ne pas `json.dumps()` avant INSERT.
2. **Labels Traefik** : explicites dans `docker-compose.yml`. Backend et frontend partagent le
   domaine : `/api` (avec middleware `stripprefix`) l'emporte sur le catch-all frontend, Traefik
   routant sur la règle la plus spécifique. Le backend expose ses routes **sans** le préfixe `/api`.
3. **`env_file` requis** (depuis la migration du 2026-09-03) : `backend/.env` et `frontend/.env`,
   deux fichiers distincts, `chmod 600`, gitignored. C'est l'inverse de la règle Coolify qui
   valait ici jusqu'au 2026-09-03 (« env_file interdit, Coolify injecte »).
4. **`NEXT_PUBLIC_*` est inliné AU BUILD**, pas lu au runtime. `NEXT_PUBLIC_API_URL` et
   `NEXT_PUBLIC_DUST_STREAMING` passent en `args:` du service frontend et en `ARG`/`ENV` dans
   `frontend/Dockerfile` **avant** `npm run build`. Les oublier ne casse rien au démarrage : le
   bundle part avec le défaut `http://localhost:8050` et c'est le navigateur qui échoue.
   Ils sont écrits en clair dans le compose à dessein — `NEXT_PUBLIC_` signifie « expédié au
   navigateur », ce ne sont pas des secrets.
5. **Commit + push AVANT** tout rebuild — `infrastructure/compose-deploy.sh` s'en charge dans le
   bon ordre. Clés : `portfolio-tracker` (les deux services), `portfolio-backend`,
   `portfolio-frontend` (un seul). Pour `-e KEY=VALUE`, viser le service : la stack a deux `.env`.
6. **Traefik + multi-réseaux** : `traefik.docker.network=coolify` sur tout conteneur attaché à
   plusieurs réseaux, sinon gateway timeout intermittent.
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
19. **Cohérence format JSON — règle des 3 points de synchronisation** : tout changement de structure de données (opportunity, thèse, thèse PE/VC) doit être répercuté simultanément sur Prompt Dust / Frontend / Import JSON manuel — en omettre un crée des désynchronisations silencieuses. Détail + garde : `check_analysis_contract.py`, `check_decision_validate.py`, `check_exit_debate.py`, `check_monitoring_v2.py`.
17. **Migrations non auto-appliquées** : `startup()` dans `main.py` n'exécute aucune migration — il appelle uniquement `init_pool()` et `init_redis()`. Toute nouvelle migration doit être appliquée manuellement via `docker cp` (le heredoc `psql << 'EOF'` via `docker exec` échoue silencieusement — pas d'erreur, pas de changement) :
    ```bash
    docker cp /tmp/migration.sql shared-postgres:/tmp/migration.sql
    docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/migration.sql
    ```
18. **Architecture PE/VC (sociétés non cotées)** : `tickers.company_type = 'private'` est le discriminateur principal. Les agents Python injectent `[company_type: private]\n\n` en tête de message Dust — les prompts Dust détectent ce signal et appliquent toute la logique PE/VC (marqueurs "→ Non coté :"). Tables associées : `private_company_profiles` (stage, valuation, ARR, investors, next event) + colonnes `ownership_pct_at_entry` / `current_ownership_pct` sur `portfolio_positions`. La réponse JSON du monitoring mode 2 inclut un bloc `private_valuation_update` automatiquement parsé et appliqué à `private_company_profiles` par `monitoring_v2.py`. DataService (yfinance/FMP) est ignoré pour les tickers privés.
20. **`pending_manual` dans monitoring_sessions** : statut ajouté en migration 020, distinct de `blocked_sync`. Détail + garde : `check_monitoring_v2.py` §8.
21. ⚠️ **Non couvert par check — vigilance manuelle.** **`hypotheses_reviewed[]` vs `hypothesis_reviews[]`** : `hypothesis_reviews[]` est la sortie brute de l'agent Dust (modes 2/3/4). `monitoring_v2.py` appelle `_normalize_monitoring_result()` qui fusionne ces reviews avec les hypothèses de la thèse pour produire `hypotheses_reviewed[]` — champ enrichi utilisé par la Page 5 (contient `text`, `weight`, `kpi_metric`, `kpi_unit`, `alert_threshold`, `invalidation_threshold`, `status`, `observation`). Toujours lire `hypotheses_reviewed[]` côté frontend, pas `hypothesis_reviews[]`.
22. ⚠️ **Non couvert par check — vigilance manuelle.** **Recherche knowledge (V2)** : `query_knowledge()` est **vectorielle** (`embedding <=> $vec::vector`, bge-m3 1024d). Le chemin texte ILIKE est un **repli strict** — jamais un co-classement. Mesuré sur corpus réel : fusionner les deux (RRF) **dégrade** le résultat (MRR 0.905 → 0.655), le signal lexical français étant trop faible. Ne pas « améliorer » en hybride sans re-mesurer. Les entrées à `embedding IS NULL` sont invisibles au vectoriel : elles sont rattrapées par une passe texte à quota réservé (`_RESCUE_QUOTA`), qui doit tourner **inconditionnellement** — la conditionner au budget restant la rend morte dès que le corpus dépasse `limit`.
23. ⚠️ **Non couvert par check — vigilance manuelle.** **pgvector et `atttypmod`** : la dimension y est stockée **telle quelle**, sans le `+4` (VARHDRSZ) des types natifs. Un `atttypmod - 4` réflexe lit `1020` pour un `vector(1024)`. Dans une migration, cette erreur fait échouer la garde d'idempotence et **efface tout le corpus d'embeddings** au rejeu. Comparer `format_type(atttypid, atttypmod)` à `'vector(N)'`.
24. **search-worker — le modèle ne qualifie jamais sa propre source (V2)** : `source_type` est déterminé par le **domaine** (`classify_source_type`), jamais par la déclaration de l'agent — la sur-qualification gonfle le score, la sous-qualification creuse un **faux trou de couverture**. Détail + garde : `check_search_worker.py`, `check_readiness_recompute.py`, `check_synthesis_feed.py`, `check_exit_debate.py`, `check_monitoring_v2.py`.
25. **Un échec de recherche n'est jamais un résultat vide (V2)** : `web_search` sans clé lève `SearchUnavailable` (503) plutôt qu'un `not_found` fabriqué — un worker sans recherche ne doit jamais ressembler à une recherche qui n'a rien trouvé. Même règle pour `fetch_url` (page vide/SPA). Détail + garde : `check_edgar_feed.py`, `check_financials_feed.py`, `check_valuation_feed.py`, `check_fetch_live.py`.
26. **`fetch_url` a deux chemins, et le domaine décide de ce qui vaut la peine d'être lu (V2)** : récupération directe d'abord, puis repli `SearchBackend.fetch_contents()` si l'échec est **récupérable** (401/403/429/5xx/SPA-vide) ; 404/410 = absence réelle, aucun repli. Champ `via` (`direct` | `search_backend_cache`) sur le retour. Détail + garde : `check_fetch_live.py`, `check_fetch_relevance.py`.
27. **On ne tronque pas un document, on y cherche (V2)** : `fetch_url` récupère la page ENTIÈRE puis `document_search.select_relevant()` n'en rend que les passages pertinents à la question du mandat — pas de taille de troncature défendable a priori, ça dépend du genre du document. Mode toujours déclaré (`whole`|`relevance`|`lexical`|`head`). Détail + garde : `check_provenance.py`.
28. **La provenance est vérifiée, pas déclarée (V2)** : `RetrievalLog` journalise ce que les outils ont réellement rapporté, et `_verify_provenance()` y confronte chaque `source_url` avant scoring — jamais rapportée ou simple lien → rétrogradée `llm_memory`. Corollaire : une entrée = un document (une entry citant plusieurs dépôts sous un seul `source_url` est marquée `requires_human_review`). Détail + garde : `check_synthesis_feed.py`, `check_provenance.py`.
29. **La couverture se LIT dans un index, elle ne se demande pas au modèle (V2, migration 029)** : `curator.recompute_coverage` interroge `knowledge_entries.covers` pour chaque champ requis — le LLM ne produit plus que le narratif, `fondations` est RÉÉCRIT depuis l'index (un véto sur citation laissait passer un faux creux). `champs_requis`/`tier_plancher` : le modèle peut RESSERRER, jamais desserrer. Détail + garde : `check_readiness_recompute.py` §13, `check_synthesis_feed.py` §7.

30. **Le concept XBRL se choisit par FRAÎCHEUR, jamais par convention (V2, `knowledge/edgar_feed.py`)** : un concept us-gaap peut répondre `200` avec un historique arrêté depuis 15 ans sans rien signaler — `select_concept()` retient le point le plus proche de l'ancre du bilan parmi une LISTE de concepts candidats, jamais « le premier qui répond ». Détail + garde : `check_edgar_feed.py`.

31. **Ce qui décrit UN émetteur ne vit jamais dans une constante globale (V2)** : trouvé sur un 2ᵉ ticker (MSFT) — dispenses et gabarits de synthèse rédigés pour NVIDIA s'appliquaient en silence à tout émetteur. Règle : une dispense se clef sur `ticker_id` (défaut = aucune, le champ BLOQUE) ; un descripteur de champ est un gabarit paramétré, jamais un texte nommant un acteur. Détail + garde : `check_readiness_recompute.py` §13, `check_synthesis_feed.py` §7, `check_search_worker.py`.

32. **Un plancher qu'aucun domaine ne peut atteindre est un champ infondable déguisé en lacune (V2)** : abaisser un plancher pour un champ ne sert à rien si aucun `source_type` réel ne l'atteint — le trou se bouche dans la **table de domaines**, pas par une dispense de plus. Détail + garde : `check_provenance.py` §8.

33. **Le site d'un émetteur se reconnaît PAR ÉMETTEUR, et sur deux niveaux (V2)** : application de #31 — `nvidia.com` en dur dans la table globale, Microsoft n'avait rien, donc son IR officiel tombait sous le plancher. Registre `issuer_domains_for(ticker_id)` (défaut vide) à deux niveaux : domaine+chemin IR → `company_ir_official` ; domaine hors IR → `web_search_reputable`. Une règle spécifique ne resserre jamais la règle générique au passage. Détail + garde : `check_search_worker.py` §1bis/§2bis.

34. **Les jugements sont disjoints, les faits du monde sont PARTAGÉS (V2, migration 030)** : un **jugement** (`theses`|`theses_v2`) se duplique sainement par flux ; un **fait du monde** (positions, cash, calendrier) ne se duplique jamais — colonne discriminante + CHECK d'exclusivité **par ligne**. Le partage crée une obligation de filtrage dans les DEUX sens (un LEFT JOIN sans garde peut appeler un agent sur une thèse inexistante). Détail + garde : `check_monitoring_v2.py`.

35. ⚠️ **Non couvert par check — vigilance manuelle.** **`get_db_session()` n'ouvre AUCUNE transaction** : il *acquiert* une connexion du pool et chaque `execute` part en **autocommit**. La validation V1 documentée « 4 écritures atomiques » (convention #13) **ne l'est donc pas** : une panne au milieu laisse une thèse `active` sans position, ou une position sans mouvement de trésorerie. L'atomicité doit être **explicite** — `async with conn.transaction():` — comme le fait `agents/v2/decision.py`. Corollaire : les appels réseau (FX, calendrier) se font **avant** l'ouverture de la transaction. V1 est délibérément laissée telle quelle (hors périmètre, risque de régression) : ne pas lire #13 comme une garantie.

36. **Un contrat de décision ne vaut que par ce que le corps HTTP n'expose PAS (V2, G2)** : `ValidateV2Body` n'accepte que les **acquittements** et les **faits d'exécution** — `verdict`, `position_sizing_pct`, `conditions_entree`, `hypotheses`, `valuation_range` sont **lus en base**, jamais acceptés du client (sinon les garde-fous deviennent décoratifs). Champs dérivés (`risk_matrix_acked`, `valuation_range`) jamais redemandés. Détail + garde : `check_decision_validate.py` §8 (`model_fields`).

37. **Un contrat valide un objet, JAMAIS la cohérence entre deux (V2, lot 8)** : limite structurelle de Pydantic — `Mode2QuarterlyReview` accepte parfaitement une escalade sur une hypothèse `H7` inexistante dans la thèse, contrat satisfait mais anti-churn mort. Un invariant **relationnel** se vérifie en code (`_valider_pont_hypotheses` : référentiel/exhaustivité/citations), jamais dans le schéma. Seuils figés en **lecture seule** — une revue ne peut jamais abaisser le seuil qu'elle vient de franchir. Détail + garde : `check_monitoring_v2.py` §3.

38. **Le rattrapage d'une échéance dépend de ce qu'elle commente, pas d'une règle uniforme (V2)** : dans `EventRouterV2`, seul le **mode 6** se rattrape (`scheduled_date <= today`) ; les modes calendaires restent sur une date **exacte** (rejouer un brief périmé ne sert à rien, une revue annuelle en retard est au contraire plus urgente). À `v2_auto_enabled=FALSE`, session `pending_manual` persistée avec contexte exact, jamais perdue ; un **échec** en revanche ne consomme rien. Détail + garde : `check_monitoring_v2.py` §8.

39. **L'EXEMPLE JSON d'un prompt est une pièce du contrat, et la DB est le 3ᵉ point de synchro (V2, migration 033)** : la règle #19 mord aussi à l'intérieur du prompt — un exemple JSON périmé dans `agent_prompts` fait recopier au modèle un format obsolète, ce qui peut rendre une dérivation en aval **no-op silencieuse**, invisible à tout check hors ligne (les fixtures sont déjà conformes). Tout figeage de contrat Pydantic se répercute le jour même dans l'exemple du prompt et en DB. Détail + garde : `check_fstring_sql.py`.

40. **Une pré-condition d'ÉTAT se refuse avant l'appel, pas dans le pont (V2, lot 9)** : `_verifier_etat` doit refuser AVANT toute dépense de tokens — une condition d'état vivant seulement dans le pont (après l'appel) fait payer un appel modèle complet pour apprendre ce qu'on savait déjà. Un **pont** juge la sortie du modèle (→ 422) ; un **état** dit que la question n'avait pas lieu d'être posée (→ 409), sans ligne `failed`. Détail + garde : `check_exit_debate.py`.

41. **Un abandon est facturé comme un succès — il doit être comptabilisé comme tel (V2, runner)** :
    `run_json_agent` levait un `RuntimeError` nu, donc l'appelant persistait une session `failed`
    chiffrée à **0 token / $0** et jetait le texte fautif, seule pièce permettant de diagnostiquer
    la sortie hors contrat. Un échec gratuit dans les comptes est un échec qu'on ne cherche pas à
    réduire. → `AgentOutputInvalid` (sous-classe de `RuntimeError`, pour ne casser aucun
    `except RuntimeError` existant) porte `raw_content` / `tokens_in` / `tokens_out` / `cost_usd`
    sous **exactement** les noms lus par les `_persister_echec`, et se passe donc en `run=` telle
    quelle. ⚠️ Le trou principal n'était pas la dernière tentative mais la **boucle d'outils** :
    quand la clôture de `run_tool_json_agent` échoue, `add_upstream()` doit reporter le coût des
    tours d'outils déjà payés — mesuré en test négatif à **78 % de la facture** (3 850 tokens réels
    contre 850 comptabilisés). Les types comptent autant que les noms (`int`/`int`/`float` : les
    colonnes sont INTEGER/NUMERIC et `_persister_echec` avale toute `DataError` dans un
    `except Exception`, donc une erreur de binding perdrait la trace **une seconde fois**, en
    silence). Détail + garde : `check_runner_telemetry.py` (§3 somme exacte, §6 noms **et** types,
    §7 report de la boucle) — éprouvé par test négatif.

42. **Un poste de bilan se date à un INSTANT, un flux à un EXERCICE — et un ratio se date par les
    postes qui le composent (V2, `knowledge/financials_feed.py`)** : trouvé sur RVMD, où le socle
    ne lisait que les dépôts annuels et ignorait six mois de trimestriels (trésorerie 383,7 →
    815,4 M$, convertibles 0 → 487,4 M$). Une fois l'ancre de bilan corrigée, `levier` — bâti à
    100 % de postes au 2026-06-30 — sortait toujours étiqueté « FY2025 » en titre, en texte et en
    `fiscal_period` : **tous ses nombres justes, le fait faux**, donc invisible à tout contrôle
    arithmétique et à tout contrat. Un ratio mono-ancre porte l'ancre de ses postes (`AU
    <date>`, `poste_kind='stock'`) ; un ratio **mixte** (ROIC : flux au numérateur, bilan au
    dénominateur) reste licite mais le **DÉCLARE** — `periods_mixed` / `balance_end` /
    `jours_entre_ancres` en structuré **et en toutes lettres dans le contenu**, qui est ce que
    l'agent lit. ⚠️ Ne pas porter la mention sur les ratios mono-ancre : la mettre partout la rend
    invisible là où elle compte. ⚠️ Les libellés `fp` d'EDGAR ne sont **pas** fiables (RVMD tague
    `fp=Q2` sur un point au 2026-03-31) — discriminer sur la présence/absence de `start`, jamais
    sur `fp`. Détail + garde : `check_financials_feed.py` §8, `check_edgar_feed.py` §8/§9.

43. **L'identité d'un fait est ce qu'il MESURE, et cette règle vit à un seul endroit (V2,
    `knowledge/edgar_feed.py`)** : sur un stockage append-only, la clef de supersedage décide de ce
    qui est **retiré**. Elle incluait la période, donc corriger l'ancre du bilan **ajoutait** la
    vérité sans retirer le fait périmé — deux valeurs de capitaux propres actives simultanément.
    Aucun ratio n'était faux (`extract_edgar_facts` prend la plus récente) : c'est le **corpus
    narratif lu par les agents** qui portait deux réponses. Règle : un **flux** s'identifie par
    `(metric, period_end)`, un **poste de bilan** par `metric` **seul** (borné `<= period_end`,
    pour qu'un EDGAR qui reculerait ne supersede jamais un instant plus récent) ; le supersedage
    balaie **TOUTES** les entrées courantes, pas la plus récente. `_current_fact_ids` est le
    **seul** détenteur de cette règle — `financials_feed` l'importe au lieu de la ré-implémenter
    (il l'avait ré-implémentée par tags `{financials,capex,fact}` contre `{financials,capex,edgar}`
    du socle : un mot d'écart, deux `capital_expenditure` courants pour le même exercice, invisible
    sur NVDA dont le seed portait déjà le bon tag). ⚠️ **Corollaire de méthode** : ces défauts ne se
    voient **ni dans le diff, ni dans la suite de checks** — seulement en inspectant l'état
    persisté **après déploiement**. Sur toute écriture qui remplace une vérité antérieure, la
    question n'est pas « la nouvelle valeur est-elle bonne ? » mais « **combien de lignes sont
    actives sur cette clef maintenant ?** ». Détail + garde : `check_edgar_feed.py` §10,
    `check_financials_feed.py` §8.

44. **Un ratio à dénominateur négatif n'est pas un niveau, c'est une perte — et « non calculable »
    n'est pas « absent » (V2, `knowledge/valuation_feed.py`)** : yfinance rend `pe_ntm=-35,95×` et
    `ev_ebitda=-26,23×` sur RVMD, que le feed publiait tels quels dans le corpus narratif. Un P/E
    négatif n'ordonne rien et n'est même pas monotone — une perte plus lourde le rapproche de zéro
    par le bas, donc fait paraître l'émetteur « moins cher ». Même famille que `fcf_conversion_pct`
    calculé sur deux négatifs. `_trier_multiples()` sépare **trois** états, jamais deux confondus :
    **calculé** (dénominateur > 0) · **non calculable** (≤ 0, écarté à `None` **avec son motif**) ·
    **absent** (le fournisseur ne rend rien). Confondre les deux derniers ferait lire une propriété
    de l'émetteur (il perd de l'argent) comme un trou de collecte. ⚠️ Les clefs restent **présentes
    à `None`** (une clef manquante se lirait comme un oubli du producteur), le contenu le dit **en
    toutes lettres** (#42 : c'est le texte que l'agent lit), et `fcf_yield_pct` **traverse le tri
    sans être écarté** — c'est un RENDEMENT, monotone et vrai même négatif ; uniformiser la règle
    supprimerait une information juste. Zéro multiple calculable ne crée pas un faux trou :
    l'entrée est produite et l'annonce (symétrique de #32). Détail + garde :
    `check_valuation_feed.py` §4/§6/§7.

45. **Un libellé qualifie la maille RÉELLEMENT mesurée, et un montant choisit son unité (V2,
    `knowledge/base_rate_corpus.py`)** : `base-rate-anchor` annonçait « small-cap (CA < 1 Md$) »
    pour RVMD, capitalisée 44,8 Md$. La classe est juste — le Base Rate Book raisonne en chiffre
    d'affaires — mais son libellé empruntait le vocabulaire de la capitalisation. Tous les nombres
    justes, le fait faux : famille de #42. Deux règles, aucune ne change la maille du livre :
    (a) le libellé est **composé avec la base effectivement utilisée** (le repli capitalisation
    écrivait « large-cap (CA 10-50 Md$) » sans qu'aucun CA soit connu) ; (b) quand les deux mailles
    **divergent**, l'entry le DÉCLARE — `sales_usd`, `market_cap_usd`,
    `size_bucket_par_capitalisation`, `mailles_divergentes` en structuré **et** un paragraphe ⚠ en
    clair, l'écart étant présenté comme l'information distinctive de l'émetteur, pas comme un
    défaut de classement. ⚠️ Mention portée **uniquement** en cas de divergence — la mettre partout
    la rendrait invisible là où elle compte. ⚠️ **Corollaire de format** : un montant arrondi à zéro
    n'est pas imprécis, il est **faux** — 11,58 M$ de ventes écrits « 0,0 Md$ » se lisent comme
    *aucune vente*, et c'est le chiffre même sur lequel repose la divergence déclarée. `_mds()`
    choisit son unité par ordre de grandeur, **après** l'arrondi (sinon 999 999 $ s'écrit
    « 1000,0 k$ ») ; `None` → « n/d » et un vrai zéro → « 0 $ », qui ne se confond avec aucun
    arrondi. Détail + garde : `check_base_rate_corpus.py` §7 à §10.

46. **Une règle de FORMAT recopiée dans trois producteurs n'est corrigée dans aucun (V2,
    `knowledge/units.py`)** : le correctif #45 (« un montant choisit son unité par ordre de
    grandeur ») avait été écrit dans `base_rate_corpus._mds`, et **seulement là**. `edgar_feed._md`
    et `financials_feed._md` divisaient toujours par `1e9` en dur. Sur RVMD : capex FY2025
    = 15,99 M$ (vérifié contre l'API EDGAR `companyconcept`, CIK 0001628171) publié
    « 0,02 MdUSD » côté socle et « 0,0 Md » côté ratios — un agent y lit *aucun investissement*.
    Pire, `fcf_conversion_pct` publiait « FCF -0,9 Md = cash-flow opérationnel -0,9 Md − capex
    0,0 Md » : une soustraction dont l'arithmétique **paraît juste** précisément parce que ses
    deux termes sont écrasés à la même unité — donc invisible à tout contrôle de cohérence, comme
    #42 et #45. C'est le **corollaire de méthode de #43 appliqué à un format** : la règle vit dans
    `knowledge/units.py`, les trois producteurs l'importent, aucun ne la ré-implémente.
    ⚠️ **Corollaire d'appelant** : une fois l'unité choisie par ordre de grandeur, deux termes
    d'une **même phrase** peuvent légitimement porter des paliers différents (M et Md).
    Factoriser la devise sur le dernier terme — `f"{_md(x)}{cur}"`, ce que faisaient les deux
    modules — laisserait alors deux ordres de grandeur se lire comme un seul : la devise est
    passée **à chaque appel**, et un vrai zéro s'écrit « 0 USD » (sans mantisse ni palier, sinon
    la concaténation produirait « 0USD »). Détail + garde : `check_edgar_feed.py` §11,
    `check_financials_feed.py` §9 — éprouvés par test négatif (4 FAIL chacun).

47. **Un zéro est une VALEUR mesurée, et `if x:` ne sait pas le distinguer d'une absence (V2,
    `knowledge/base_rate_corpus.py`)** : `_latest_revenue_usd()` parcourait les exercices avec
    `if rev:` — un CA légitime de `0.0` était donc sauté comme s'il n'avait pas été déposé, et la
    boucle continuait de reculer dans le temps. Sur RVMD (2023 : 11,58 M$ · 2024 : 0 · 2025 : 0),
    `base-rate-anchor` publiait « pour 11,6 M$ de ventes » — **deux exercices de retard**, dans le
    paragraphe même que #45 venait d'ajouter, et **en contradiction directe** avec l'entry EDGAR
    tier A qui dit 0 : deux réponses actives à une seule question (famille de #43). C'est #44
    transposé au filtre booléen — *calculé / non calculable / absent* sont trois états, et `0.0`
    appartient au premier. Test à faire partout où une valeur financière peut valoir zéro :
    `is not None`, jamais la véracité. ⚠️ **Un flux se date par son exercice** (#42) : la mention
    « (FY2023) » rend la péremption visible **même sans le correctif** — c'est la datation qui
    transforme un chiffre faux et muet en chiffre faux et détectable. ⚠️ **Corollaire de fond** :
    une base de ventes nulle ne retire pas l'ancre de taux de base, elle en **déclare la limite**
    (un CAGR ne se calcule pas depuis zéro — le premier dollar vendu est une croissance infinie) ;
    le zéro est une propriété **mesurée** de l'émetteur, pas un trou de collecte, et la mention
    n'est portée **qu'en cas de base nulle** (la mettre partout la rendrait invisible).
    Détail + garde : `check_base_rate_corpus.py` §11/§12 — éprouvé par test négatif (9 FAIL).
    ⚠️ La fixture du check portait 11,58 M$ en 2025, chiffres **plus favorables que la
    production** : une fixture qui embellit le réel est un check qui ne peut pas voir le défaut.

48. **La COLONNE `source_date` est un porteur de la date au même titre que le texte — et c'est le
    seul sur lequel trient les machines (V2, `knowledge/financials_feed.py`)** : #42 avait daté le
    titre, le `fiscal_period`, le contenu narratif et le `content_structured` du `levier` ; le site
    d'écriture passait quand même `source_date=facts['period_end']`, l'ancre de FLUX, identique
    pour les quatre ratios. La ligne #169 de RVMD **se contredisait elle-même** (`fiscal_period='AU
    2026-06-30'` contre `source_date=2025-12-31`) et le levier paraissait vieux de 239 jours au
    lieu de 58. Les quatre porteurs corrigés sont lus par un **agent** ; celui-ci est lu par
    l'**ancre temporelle**, le **balayage de péremption** et toute requête « la plus récente » —
    corriger l'affichage en laissant l'index faux fabrique une base qui *dit* juste et *se classe*
    faux. Détenteur unique `_spec_source_date(spec, facts)` (#46 transposé aux porteurs d'un même
    fait **à l'intérieur d'une ligne**), jamais un `if` par site de construction. ⚠️ **Trouvé en
    PROD par un outil écrit le même jour pour autre chose** (le balayage) : ni le diff ni les
    assertions hors ligne ne pouvaient le voir, les fixtures portant déjà la bonne date — corollaire
    de méthode du #43. ⚠️ **Le check doit éprouver la valeur REÇUE par `store_knowledge`**, pas le
    helper en isolation : le premier test négatif ne faisait rougir que le grep de source, un proxy
    syntaxique. Détail + garde : `check_financials_feed.py` §10 — éprouvé par test négatif (3 FAIL,
    dont la reproduction exacte du symptôme de prod).

49. **La péremption est une SECONDE horloge, et elle produit un rapport — jamais un `superseded_by`
    (V2, `knowledge/material_events.py` + `knowledge/staleness.py`)** : la porte de complétude (#29)
    compte les champs *couverts* et est structurellement **aveugle à la péremption** — sur RVMD,
    quatre entries tier A actives disaient « aucun produit approuvé pour la vente commerciale »
    après l'approbation FDA du 2026-08-26, aucune fausse (chacune fidèle à sa source et
    correctement datée), toutes périmées ; le gate aurait conclu à un socle prêt. Les dépôts
    **périodiques** (10-K/10-Q) ne datent pas le monde : un 8-K/6-K le fait. Trois règles :
    (a) le seuil est la date de l'**ÉVÉNEMENT** (`reportDate`), pas du dépôt — le monde change quand
    le fait se produit, et sur EDGAR les deux peuvent différer de plusieurs semaines ;
    (b) **trois états jamais confondus** (#25/#44) — `found` / `none` (l'émetteur n'a rien publié) /
    `unavailable` (flux injoignable) : confondre les deux derniers ferait lire une panne réseau
    comme « il ne s'est rien passé », la phrase la plus rassurante produite par la pire raison ; le
    rapport lui-même sort `indeterminable` **en le disant**, et l'absence d'ancre route le prompt
    vers la branche PRUDENTE, jamais vers le silence ;
    (c) le module **n'écrit rien** — décider qu'un fait est remplacé est un jugement sémantique,
    l'automatiser donnerait à une heuristique de dates une voix sur ce que le corpus affirme
    (desserrage refusé en #29). Route `GET /tickers/{id}/knowledge/staleness`, **toujours 200** :
    un 503 ferait disparaître le rapport, ce qui se lit « rien à signaler ». Détail + garde :
    `check_material_events.py` — ⚠️ sa §2bis utilise une fixture **construite** (deux 8-K dont
    l'ordre s'inverse selon la clef de tri) parce que le flux RVMD réel, pourtant copié fidèlement,
    donne le **même gagnant** avec les deux tris : une fixture peut être aveugle en étant *non
    discriminante*, pas seulement en étant plus favorable (#47).

50. **Un champ a TROIS propriétés indépendantes, et le standing est une propriété du COUPLE
    (source × nature) — jamais de la source seule (V2, `agents/v2/common.py: FIELD_PROFILES`)** :
    le `reliability_score` confondait *à quel point je fais confiance à cette source* et *ce fait
    décrit-il encore le monde*. Mesuré : sur un émetteur dont un produit vient d'être approuvé,
    l'information la plus fraîche du corpus est la moins bien classée (tier A moyen 0,931 sur des
    faits antérieurs · tier B+ 0,750 sur l'information du jour) et la porte prononce quand même
    `ready`. Trois causes, toutes structurelles : la porte ne lit que le `tier`, qui « NE change pas
    à la modulation » ; le score est **figé à l'écriture** (les seuls `UPDATE` du code touchent
    `superseded_by` et `embedding`), donc le corpus ne vieillit jamais ; `cross_validated` /
    `has_conflict` sont câblés de bout en bout mais **aucun appelant de production ne les passe**.
    D'où la table `FIELD_PROFILES` — **nature** (stockée : l'autorité qu'elle commande) · **plancher**
    de fiabilité · **actualité bloquante** (calculée à la LECTURE, jamais persistée : la stocker
    reproduirait la cause n°2). ⚠️ **Aucun des 19 champs n'a `evenement` pour nature dominante, et
    c'est le résultat** : un événement ne *fonde* aucun champ, il *périme* les deux autres natures.
    Si la nature suffisait à décider de la péremption, la troisième colonne n'existerait pas.
    ⚠️ Corollaires : **jamais de score composite** (trois nombres recombinés redeviennent un
    scalaire et reproduisent le défaut au premier arrondi — la porte lit un **triplet**) ; **jamais
    de promotion automatique** d'un domaine, pas même par corroboration (N sources recopiant un
    communiqué ne sont pas N sources indépendantes : la corroboration deviendrait un amplificateur
    de rumeur) ; l'actualité se mesure sur la date du **FAIT**, jamais de la publication (#42,
    `material_events` trie sur `reportDate`) ; un `motif` de profil est un **gabarit** qui ne nomme
    aucun émetteur ni juridiction (#31), sans quoi la doctrine casse au premier émetteur non
    américain. ⚠️ Trois champs sont **desserrés** B+ → B (`positionnement.moat_preuves`,
    `positionnement.position_vs_pairs`, `marche.structure_5forces`) : sur un champ
    d'*interprétation*, un dépôt réglementaire est du boilerplate juridique malgré son tier A. Ce
    desserrage **ne prend effet qu'avec le registre nominatif** (capacité 2) — sans lui il n'admet
    personne de nouveau — et tout desserrage tacite fait rougir un assert (`feedback_optional_
    schema_gate`). Détail + garde : `check_field_profiles.py` §1 (un champ retiré est nommé, pas un
    KeyError), §3 (#32 atteignabilité), §5 (desserrage déclaré), §6 (gabarit), §7 (pas de
    composite) — éprouvé par test négatif (5 cas, chacun rouge sur son assert nommé).

51. **La nature d'une ENTRY et la nature dominante d'un CHAMP sont deux vocabulaires, et le second
    ne dérive jamais le premier (V2, migration 034, `agents/v2/common.py: derive_nature`)** :
    `FIELD_PROFILES[…]["nature"]` dit ce qui doit AVOIR AUTORITÉ pour fonder un champ — c'est une
    exigence co-écrite, elle ne décrit aucune donnée. `knowledge_entries.nature` dit ce que
    l'assertion PRÉTEND ÊTRE — c'est un fait sur la ligne. Dériver la seconde de la première aurait
    trois conséquences, toutes fausses : `evenement` deviendrait **inatteignable** (aucun des 19
    champs ne l'a pour nature dominante — c'est le résultat de la capacité 0, pas un oubli) ; une
    donnée se mettrait à dire ce qu'on **attend** d'elle plutôt que ce qu'elle est ; et la
    confrontation des deux, qui est tout le travail de la porte (capacité 4), n'aurait plus lieu
    puisqu'elles coïncideraient par construction. Cas d'école en base : `valorisation.base_rate_anchor`
    est un champ d'**interprétation** (ce qui devrait le fonder est un raisonnement de classe de
    référence) alors que l'entry qui le remplit est une **fréquence empirique**, donc une `mesure` ;
    et deux entries `analysis` couvrent `produits.unit_economics`, champ de nature `mesure`, en
    restant des interprétations. ⚠️ Corollaires : `mesure` est la nature FORTE (elle donne autorité à
    la fiabilité et soustrait le fait à l'horloge matérielle) donc elle ne s'accorde **jamais par
    défaut** — entry_type inconnu, `covers` vide ou **hétérogène** retombent sur `interpretation`
    (#44 : « non qualifiable » n'est pas « mesure au rabais ») ; le `source_type` **l'emporte sur**
    l'entry_type (`llm_memory` / `agent_synthesis` ne mesurent jamais, sinon un `fact_financial`
    restitué de mémoire hériterait de l'autorité d'un dépôt) ; le modèle ne peut que **promouvoir
    vers `evenement`**, seule nature qui SOUMET l'assertion à l'horloge — toute autre proposition
    est écartée **en le disant** (garde symétrique de #29). ⚠️ La règle est un **détenteur unique**
    (#46) appelé par `store_knowledge`, seul passage obligé des 8 producteurs : aucun feed ne la
    ré-implémente, et `store_knowledge` n'accepte **pas** de paramètre `nature` (seulement
    `nature_declaree`, qui est arbitrée). Le motif de dérivation n'est **pas** persisté — la règle
    est une fonction pure de trois colonnes déjà stockées, donc rejouable ; et il n'entre pas dans
    `reliability_note`, car on ne mélange pas deux axes, fût-ce en prose (#50). ⚠️ **Aucune entry
    n'est `evenement` après backfill** et c'est déclaré dans la migration : aucun producteur n'écrit
    encore d'entry adossée à un 8-K/6-K (`material_events` signale et n'écrit rien, #49), donc le
    canal de déclaration n'a **aucun émetteur** aujourd'hui — état volontaire et nommé, à ne pas
    confondre avec le défaut de #50 (`cross_validated` câblé et jamais passé) : ici l'absence de
    déclarant rend la nature 100 % déterministe, donc plus stricte, jamais plus permissive.
    Détail + garde : `check_entry_nature.py` §1 (atteignabilité #32), §2 (les deux vocabulaires),
    §3 (unanimité de `covers`), §4 (la source l'emporte), §5 (resserrer/desserrer), §6 (détenteur
    unique), §7 (l'ÉTAT persisté, pas seulement la règle — #43) — éprouvé par test négatif (5 cas).

52. **Une source est admise pour un COUPLE (source × nature), et l'ordre `nature` PUIS `registre`
    est ce qui rend cette phrase vraie (V2, `knowledge/source_registry.py`)** : application de #50
    à un registre nominatif. Le premier câblage repliait la promotion dans `classify_source_type` —
    `endpts.com` sortait alors `web_search_reputable` **avant** que la nature soit dérivée, donc la
    condition « admise pour l'interprétation » ne s'appliquait plus jamais et la source gagnait du
    standing sur une **mesure**. Règle : `qualify()` dérive la nature depuis le `source_type`
    **générique**, et n'applique le registre **que si** ce source_type vaut encore
    `web_search_generic` (#33 : une règle spécifique ne resserre ni ne démote la générique — un
    `sec.gov` traverse `qualify` intact). Le refus est **dit** (« aucun standing sur `<nature>` »
    ajouté au motif), jamais muet. ⚠️ **Plafond ≠ qualification** : le plafond montré au modèle dans
    les résultats de recherche est une **seconde** fonction (`websearch.source_type_max`), pas une
    modification de `classify_source_type`, qui reste générique. ⚠️ **Deux sites de câblage, et le
    second est celui qui compte** : `store_knowledge` qualifie **avant** de scorer (scorer d'abord
    écrirait une ligne se contredisant elle-même, mode de panne de #48), mais c'est l'appel dans
    `worker.py` **avant le filtre `reliability_min`** qui fait que le registre admet réellement
    quelqu'un — le worker rejette sous plancher avant que `store_knowledge` soit atteint. ⚠️ **Le
    secteur est déclaré en code, pas lu en base, et c'est une MESURE qui l'a décidé** :
    `tickers.sector` est NULL sur les 17 tickers ; un registre clefé dessus n'aurait admis
    personne, silencieusement (#32 transposé à une clef de jointure). ⚠️ **L'admission reste un
    acte humain** — pas de promotion automatique, pas même par corroboration (#50). ⚠️ **Écart
    connu, nommé dans `_DESSERRAGE_NON_CABLE`** : le desserrage B+ → B de #50 vit dans
    `FIELD_PROFILES` (doctrine) tandis que la porte lit `FIELD_PLANCHER_OVERRIDES` — une entry B
    admise par le registre est **encore refusée** au gate tant que la capacité 4 ne l'a pas câblé ;
    l'assert « la liste des écarts ne survit pas à leur câblage » vire au vert de lui-même ce
    jour-là. Détail + garde : `check_source_registry.py` §1 (atteignabilité #32), §1bis (portée
    réelle du desserrage), §2 (**l'assert central du couple**), §3 (hors registre → 0,50), §4
    (jamais de démotion), §5 (portée), §6 (détenteur unique #46), §7 (plafond ≠ qualification), §8
    (métadonnées d'admission), §9 (gabarit, pas d'acteur nommé — #31) — éprouvé par test négatif
    (5 cas). ⚠️ **Pas de section « état persisté »**, et c'est écrit dans la docstring du check : la
    capacité n'écrit rien en base, une section SQL serait verte sur zéro ligne (#47/#49).

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

### Note réseau — obsolète depuis le 2026-09-03
Coolify créait un réseau par app (`portfolio0tracker000000000_infra-net` au lieu de `infra-net`),
qu'un `post_deployment_command` devait corriger après chaque déploiement. Cette bricole n'existe
plus : la stack déclare `networks: [coolify]` en réseau **externe**, donc les conteneurs
rejoignent directement le bon réseau à la création. Le réseau parasite a été supprimé.

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

## Système de pilotage

Voir `CONTROL_SYSTEM.md` à la racine du repo pour le protocole complet.
Déclencheur : **« reprends le projet portfolio-tracker à partir du fichier de reprise »**
→ Lire **`roadmap/provenance-cards/00-REPRISE.md`** (⚠️ pas à la racine du projet, contrairement à
la convention — chemin historique conservé), puis la roadmap qu'il déclare active, annoncer le lot
de conversation, exécuter, cocher les capacités livrées.

Roadmap de référence du projet : `roadmap/01-spec-v2-unifiee.md` **§18** (liste ordonnée de
capacités) sous `roadmap/00-principe-directeur-v2.md` (constitution). Les autres fichiers de
`roadmap/` sont de la documentation, pas des roadmaps actives.
