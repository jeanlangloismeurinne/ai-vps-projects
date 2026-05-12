# CLAUDE.md — portfolio-tracker

## Contexte

Système de suivi d'investissement boursier long terme sur VPS Hetzner (jlmvpscode.duckdns.org).
URL : `portfolio.jlmvpscode.duckdns.org`
Backend : port 8050 → `/api` | Frontend : port 8051 → `/`
Workspace Dust : `plm-siege`

**État (2026-05-12) : système en production, deux positions actives (CAP + TSLA).**

---

## Bootstrap initial — tout coché ✅

- [x] Agents Dust : `research-agent` ID `eAYsKqZ1D2` · `portfolio-agent` ID `L5rXF6uilh`
- [x] Canal Slack `#portfolio-management` — Channel ID `C0B13KANHPD`
- [x] `FMP_API_KEY` = `dpl0XXr5F5ElF2M5s70Qmd80Pi3xBS6k`
- [x] Base `db_portfolio` créée, toutes migrations appliquées
- [x] Variables Coolify configurées (sauf `DUST_API_KEY` — à renseigner quand disponible)
- [x] `"portfolio-tracker"` ajouté dans `_KNOWN_PROJECTS` (assistant-ia)
- [x] DuckDNS `portfolio.jlmvpscode` opérationnel
- [x] Positions Capgemini (CAP) et Tesla (TSLA) bootstrapées avec thèses

---

## Architecture

### Stack

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.12 / FastAPI / APScheduler |
| Database | PostgreSQL 16 (shared-postgres:5432, base : `db_portfolio`) |
| Cache | Redis 7 (shared-redis:6379) |
| Frontend | Next.js 14 / Tailwind CSS |
| Agents IA | Dust.tt API (workspace plm-siege) |
| Notifications | Slack bot @ai_vps_jlm (Socket Mode) |

### Les 3 régimes d'analyse

| Régime | Déclenchement | Modèle | Coût |
|--------|--------------|--------|------|
| 1 — Thesis Construction | Manuel (`POST /api/trigger/regime1/{ticker}`) | claude-sonnet-4-5 | ~$0.30 |
| 2 — Monitoring Routine | Calendrier événementiel (J+1 publication) | gemini-2-5-flash-preview | ~$0.005 |
| 3 — Decision Review | Escalade R2 ou seuil cours | claude-sonnet-4-5 | ~$0.25 |

Budget hard cap : **$5.00/mois** — alerte Slack à 80%.

### Structure du repo

```
portfolio-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + APScheduler
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── api/                  # Endpoints REST
│   │   ├── agents/               # Dust client + régimes 1/2/3 + sector pulse
│   │   ├── calendar/             # event_router, calendar_builder, watchlist_monitor
│   │   ├── data_collection/      # M1/M2/M3/M4 + assembler + data_cache + data_service
│   │   ├── db/                   # asyncpg pool, modèles Pydantic, migrations SQL
│   │   ├── learning/             # STUBS P3 : analyst_tracker, pattern_library, thesis_versioning
│   │   ├── notifications/        # Slack notifier
│   │   └── portfolio/            # portfolio_view, concentration_checker, post_mortem (STUB P3)
│   └── sector_schemas/           # IT_Services.json (complet), Luxury.json, Industrial.json (squelettes)
└── frontend/
    ├── pages/                    # index, position/[id], calendar, watchlist, analysts
    └── components/               # HypothesisScorecard, ThesisTimeline, SectorPulseLog,
                                  # PeerComparison, CalendarView, RecommendationBadge
```

---

## Couche données — DataService

Tous les accès aux données de marché (yfinance + FMP) passent par `app/data_collection/data_service.py`.
Ne jamais appeler `collect_quantitative()` directement depuis un nouveau code — passer par `DataService`.

### Deux méthodes, deux usages

```python
# Lecture avec cache — pour dashboard, watchlist, monitoring quotidien
m1 = await DataService().get_m1(ticker, settings.FMP_API_KEY)

# Fetch forcé — pour les régimes (snapshot DB systématique avec contexte)
m1 = await DataService().refresh_m1(ticker, settings.FMP_API_KEY, context="regime2")
```

### TTL Redis

| Données | Clé Redis | TTL |
|---------|-----------|-----|
| M1 complet (prix, valorisation, financials) | `pt:m1:{ticker}` | 4h |
| Earnings date | `pt:calendar:{ticker}` | 7j |

### Flux de données

```
get_m1()     : Redis (4h) → DB market_snapshots (4h) → yfinance/FMP
refresh_m1() : yfinance/FMP → DB market_snapshots (avec context) → Redis

get_calendar()     : Redis (7j) → DB earnings_calendar_cache (7j) → yfinance
refresh_calendar() : yfinance → DB earnings_calendar_cache → Redis
```

### Contextes DB (champ `context` de `market_snapshots`)

| Valeur | Déclencheur |
|--------|-------------|
| `regime1` | Trigger Régime 1 manuel |
| `regime2` | Trigger Régime 2 (manuel ou automatique J+1) |
| `regime3` | Trigger Régime 3 |
| `weekly` | Snapshot lundi 8h45 |
| `warmup` | Création de thèse (background) |
| `api` | Appel API courant (cache miss) |

### Callers actuels

| Fichier | Méthode utilisée | Raison |
|---------|-----------------|--------|
| `api/trigger.py` R1/R2/R3 | `refresh_m1(context='regime*')` | Snapshot obligatoire |
| `calendar/event_router.py` R2 auto | `refresh_m1(context='regime2')` | Snapshot obligatoire |
| `calendar/watchlist_monitor.py` | `get_m1()` | Prix courant suffit |
| `portfolio/portfolio_view.py` | `get_m1()` | Prix courant suffit |
| `calendar/calendar_builder.py` | `get_calendar()` | Cache 7j acceptable |
| `main.py` `_weekly_m1_snapshot` | `refresh_m1(context='weekly')` | Snapshot hebdo |
| `main.py` `_refresh_watchlist_peer_calendars` | `refresh_calendar()` | Peer calendars |
| `api/positions.py` `create_thesis` | `refresh_m1(context='warmup')` en background | Warmup silencieux |

---

## yfinance — comportement et limites

### Format retourné

`yf.Ticker(ticker).calendar` retourne un **dict** (pas un DataFrame). Ne pas utiliser `.empty` — tester avec `if cal:`.

### Tickers Euronext

`TICKER_EXCHANGE_MAP` dans `m1_quantitative.py` — ajouter chaque nouveau ticker Euronext au format `"CAP": "CAP.PA"`. Sans cette map, yfinance retourne `None` pour les cours.

### Rate limiting (429)

Yahoo Finance utilise Fastly comme CDN. En cas de 429 :
1. Fastly bloque l'IP (rate limit par IP, pas par token)
2. La requête de re-fetch du crumb CSRF échoue aussi → Fastly retourne le message d'erreur comme crumb
3. Toutes les requêtes suivantes échouent avec `crumb=Edge%3A+Too+Many+Requests`

**Cause principale** : appels en rafale sans délai. Le cache Redis/DB élimine ce risque en production normale. Ajouter `asyncio.sleep(1-2)` dans les boucles de batch si besoin.

**Volume sûr** : ~500 appels/heure avec 1s de délai. En production normale (2-3 positions), très loin de ce plafond.

---

## Scheduling automatique

| Heure | Jour | Job | Détail |
|-------|------|-----|--------|
| 7h00 | tous | `_daily_check` | Brief J-2, Régime 2 J+1, sector pulses, check watchlist |
| 7h30 | tous | `_refresh_watchlist_prices` | Prix watchlist via `get_m1()` |
| 8h00 | lundi | `_weekly_review` | Snapshot portfolio → digest Slack |
| 8h15 | lundi | `_refresh_market_temperature` | FRED — Buffett indicator, CAPE |
| 8h30 | lundi | `_refresh_all_calendars` | Earnings dates via `CalendarBuilder.refresh_all()` |
| 8h45 | lundi | `_weekly_m1_snapshot` | `refresh_m1(context='weekly')` toutes positions, 2s entre tickers |
| 18h00 | vendredi | `_refresh_watchlist_peer_calendars` | Peer calendars via `refresh_calendar()`, 1s entre tickers |

---

## Base de données

Driver : **asyncpg** (direct, pas SQLAlchemy).
Paramètres : `$1`, `$2`… (pas `%s`).
Codec JSONB configuré dans `db/database.py` → les champs JSONB passent en Python dict nativement. **Ne pas envelopper dans `json.dumps()` avant d'écrire en DB.**

DATABASE_URL format Coolify : `postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio`
Le `+asyncpg` est strippé automatiquement dans `database.py` pour asyncpg.

### Tables clés

| Table | Usage |
|-------|-------|
| `positions` | Positions actives/clôturées |
| `theses` + `hypotheses` | Thèses d'investissement versionnées |
| `calendar_events` | Événements déclencheurs (J-2 brief, J+1 review) |
| `sector_pulses` | Résultats d'analyse des peers |
| `reviews` | Historique des revues R1/R2/R3 |
| `market_snapshots` | ★ Historique M1 par contexte (post-mortem, pattern library) |
| `earnings_calendar_cache` | ★ Persistence des dates earnings (survit aux redémarrages Redis) |
| `market_indicators` | FRED macro (Buffett indicator, CAPE) |
| `watchlist` | Titres en surveillance pré-entrée |

★ = tables ajoutées en 2026-05-12

### Migrations appliquées
001 (initial) → 011 (market_data_history). La prochaine sera 012.

---

## API REST — Endpoints principaux

```
GET  /api/positions                        Liste positions actives
POST /api/positions                        Créer position
GET  /api/positions/{id}                   Détail position (thèse, hypothèses, revues, peers, pulses)
POST /api/positions/{id}/thesis            Créer/remplacer thèse → déclenche warmup M1 + calendar en background
GET  /api/positions/{id}/thesis            Thèse courante + hypothèses
GET  /api/positions/{id}/reviews           Historique revues

GET  /api/portfolio                        Snapshot portfolio (prix live, P&L, flags concentration)
GET  /api/portfolio/snapshots              Historique snapshots

GET  /api/calendar                         Événements calendrier
POST /api/calendar                         Créer événement manuel
POST /api/calendar/refresh                 Re-fetcher les dates earnings (toutes positions actives)

GET  /api/watchlist                        Liste watchlist
POST /api/watchlist                        Ajouter
POST /api/watchlist/{id}/promote           Promouvoir en position

GET  /api/analysts                         Actions analystes
POST /api/analysts                         Logger une action
GET  /api/analysts/track-records           Vue agrégée (lagging_rate, signal_quality)

POST /api/trigger/regime1/{ticker}         Déclencher régime 1
POST /api/trigger/regime2/{ticker}         Déclencher régime 2
POST /api/trigger/regime3/{ticker}         Déclencher régime 3 ?escalation_reason=...
POST /api/trigger/sector-pulse/{peer}      Déclencher sector pulse ?main_ticker=...
```

---

## Conventions et pièges

1. **Labels Traefik** : explicites dans `docker-compose.yml` — pas d'auto-injection
2. **env_file interdit** : Coolify injecte directement — ne pas ajouter `env_file: .env`
3. **Rebuild ≠ Restart** : toujours `/deploy` (rebuild complet), jamais `/restart`
4. **Commit + push AVANT** tout déclenchement de rebuild Coolify
5. **Tickers Euronext** : enrichir `TICKER_EXCHANGE_MAP` dans `m1_quantitative.py` pour chaque nouveau ticker Euronext
6. **Traefik + multi-réseaux** : `portfolio-frontend` a le custom label `traefik.docker.network=coolify` dans Coolify
7. **yfinance `.calendar`** : retourne un dict, pas un DataFrame — tester avec `if cal:`, pas `if not cal.empty:`
8. **DataService** : seul point d'accès aux données de marché — ne pas appeler `collect_quantitative()` directement
9. **Régimes → refresh_m1()** : les déclencheurs de régimes doivent toujours utiliser `refresh_m1()` pour garantir un snapshot DB daté et contextualisé
10. **`create_thesis` auto-warmup** : la création d'une thèse déclenche automatiquement en background le calendar + M1 via `asyncio.ensure_future`

---

## Priorités en attente (P3 — après 1ère position clôturée)

Ces modules sont des stubs avec `NotImplementedError` :

| Fichier | Fonctionnalité | Dépend de |
|---------|---------------|-----------|
| `portfolio/post_mortem.py` | Post-mortem automatisé sur exit / réduction >50% | `market_snapshots` (disponible) |
| `learning/analyst_tracker.py` | Calcul verdict analystes à J+30 et J+90 | — |
| `learning/thesis_versioning.py` | Archivage + nouvelle version de thèse post-R3 | — |
| `learning/pattern_library.py` | Enrichissement depuis post-mortems | `market_snapshots` (disponible) |

`market_snapshots` accumule déjà les données dès maintenant — les P3 auront du recul historique dès qu'on les implémentera.

Schémas sectoriels à compléter :
- `sector_schemas/Luxury.json` — ajouter kpis, queries, peers complets
- `sector_schemas/Industrial.json` — idem

---

## Données initiales

### Capgemini (CAP)
Position entrée 2026-05-01 à 102€, allocation 8.5% · 6 hypothèses H1-H6 · Peers : CTSH (T1), ACN (T2)
Scénarios Bear -5.2%/an → Central 12.4%/an → Bull 23.7%/an (5 ans)

### Tesla (TSLA)
Position active, thèse définie.

### Note réseau infra-net
Le `post_deployment_command` Coolify connecte automatiquement les containers à `infra-net` après chaque rebuild. Coolify crée `portfolio0tracker000000000_infra-net` au lieu de `infra-net` — la commande post-deploy corrige ça.
