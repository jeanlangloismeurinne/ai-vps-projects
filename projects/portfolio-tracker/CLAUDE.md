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
001 → 022. Migration 013 = schéma V1 complet (2026-05-30). Migration 017 = support PE/VC. Migration 018 = `tickers.ticker_symbol`. Migration 019 = `calendar_events.brief_triggered` + `monitoring_sessions.calendar_event_id`. Migration 020 = `portfolio_settings.dust_auto_enabled` + statut `pending_manual`. Migrations 021/022 = mise à jour prompt monitoring-agent en DB.
Prochaine migration : `023_*.sql`.

---

## API REST — Endpoints

Listing exhaustif des endpoints V1 + V0 (legacy) : **`REFERENCE.md`** § API REST.
Les routers sont dans `backend/app/api/` — `grep` fait foi si divergence.

## Scheduling automatique

| Heure | Jour | Job | Détail |
|-------|------|-----|--------|
| `*/5` | lun-ven 9h-17h | `_check_price_alerts_v1` | Vérifie price_alerts V1, notifie Slack |
| 7h05 | tous | `_daily_check_v1` | EventRouterV1 — mode 1 (J-2), mode 2 (J+1), mode 4 (sector pulse J+1), mode 3 (conviction_review jour J) — lit `calendar_events` V1 |
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
