# CLAUDE.md — portfolio-tracker

## Contexte

Système de suivi d'investissement boursier long terme sur VPS Hetzner (jlmvpscode.duckdns.org).
URL : `portfolio.jlmvpscode.duckdns.org`
Backend : port 8050 → `/api` | Frontend : port 8051 → `/`
Workspace Dust : `plm-siege`

---

## ⚠️ ACTIONS RESTANTES AVANT PREMIER DÉPLOIEMENT

> À cocher dans l'ordre. Dernière mise à jour : 2026-05-02.

### Étape 1 — Agents Dust ✅

- [x] **`research-agent`** — ID : `eAYsKqZ1D2`
- [x] **`portfolio-agent`** — ID : `L5rXF6uilh`

### Étape 2 — Canal Slack ✅

- [x] Canal `#portfolio-management` créé — Channel ID : `C0B13KANHPD`

### Étape 3 — Clé FMP ✅

- [x] `FMP_API_KEY` = `dpl0XXr5F5ElF2M5s70Qmd80Pi3xBS6k`

### Étape 4 — Base de données

```bash
docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_portfolio;'

docker exec -i shared-postgres psql -U admin -d db_portfolio < \
  backend/app/db/migrations/001_initial.sql
```

- [ ] Créer la base `db_portfolio`
- [ ] Appliquer la migration `001_initial.sql`

### Étape 5 — Variables d'environnement dans Coolify

- [ ] Renseigner dans Coolify (service portfolio-backend) :

```
DUST_API_KEY=sk-dust-...
DUST_WORKSPACE_ID=plm-siege
DUST_RESEARCH_AGENT_ID=[copié étape 1]
DUST_PORTFOLIO_AGENT_ID=[copié étape 1]
DUST_MONTHLY_BUDGET_USD=5.0
DATABASE_URL=postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
REDIS_URL=redis://shared-redis:6379
SLACK_BOT_TOKEN=[depuis /opt/cyber-agent/.env]
SLACK_APP_TOKEN=[depuis /opt/cyber-agent/.env]
SLACK_PORTFOLIO_CHANNEL_ID=[copié étape 2]
FMP_API_KEY=[copié étape 3]
BASE_CURRENCY=EUR
```

### Étape 6 — Enregistrer le projet dans assistant-ia

- [ ] Ajouter `"portfolio-tracker"` dans `_KNOWN_PROJECTS` dans `projects/assistant-ia/app/slack_app.py`

### Étape 7 — Commit, push, deploy

```bash
git add .
git commit -m "feat: portfolio-tracker initial setup"
git push origin main
# Déclencher rebuild via API Coolify (cf. CLAUDE.md global)
```

- [ ] Commit + push
- [ ] Rebuild Coolify (pas restart)
- [ ] Vérifier `/health` sur `portfolio.jlmvpscode.duckdns.org/api/health`

### Étape 8 — Bootstrap Capgemini

- [ ] Créer la position CAP :

```bash
curl -X POST https://portfolio.jlmvpscode.duckdns.org/api/positions \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "CAP",
    "company_name": "Capgemini",
    "sector_schema": "IT_Services",
    "exchange": "EURONEXT",
    "entry_date": "2026-05-01",
    "entry_price": 102.00,
    "entry_price_currency": "EUR",
    "allocation_pct": 8.5
  }'
```

- [ ] Importer la thèse Capgemini :
  - Récupérer le `POSITION_ID` retourné par l'appel précédent
  - `curl -X POST .../api/positions/{POSITION_ID}/thesis -d @- << 'EOF' [...] EOF`
  - Payload complet dans la spec §17 étape 6

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
│   │   ├── calendar/             # event_router (cœur scheduling), calendar_builder, watchlist_monitor
│   │   ├── data_collection/      # M1 (quantitatif), M2 (événementiel), M3 (qualitatif), assembler
│   │   ├── db/                   # asyncpg pool, modèles Pydantic, migration SQL
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

## API REST — Endpoints principaux

```
GET  /api/positions                        Liste positions actives
POST /api/positions                        Créer position
GET  /api/positions/{id}                   Détail position (thèse, hypothèses, revues, peers, pulses)
POST /api/positions/{id}/thesis            Créer/remplacer thèse (crée hypothèses + peers)
GET  /api/positions/{id}/thesis            Thèse courante + hypothèses
GET  /api/positions/{id}/reviews           Historique revues

GET  /api/portfolio                        Snapshot portfolio (prix live, P&L, flags concentration)
GET  /api/portfolio/snapshots              Historique snapshots

GET  /api/calendar                         Événements calendrier
POST /api/calendar                         Créer événement manuel
POST /api/calendar/refresh                 Re-fetcher les dates earnings depuis yfinance

GET  /api/watchlist                        Liste watchlist
POST /api/watchlist                        Ajouter
POST /api/watchlist/{id}/promote           Promouvoir en position

GET  /api/analysts                         Actions analystes
POST /api/analysts                         Logger une action
GET  /api/analysts/track-records           Vue agrégée (lagging_rate, signal_quality)

POST /api/trigger/regime1/{ticker}         Déclencher régime 1 (fond)
POST /api/trigger/regime2/{ticker}         Déclencher régime 2 (fond)
POST /api/trigger/regime3/{ticker}         Déclencher régime 3 (fond) ?escalation_reason=...
POST /api/trigger/sector-pulse/{peer}      Déclencher sector pulse ?main_ticker=...
```

---

## Scheduling automatique

- **Tous les jours à 7h00 Paris** : `EventRouter.process_daily_events()`
  - Brief pré-event (J-2 avant publication) → Slack
  - Revue Régime 2 (J+1 après publication) → Slack
  - Sector pulses (pairs publiant le même jour)
  - Check prix watchlist → alerte Slack si seuil franchi

- **Lundi 8h00 Paris** : Portfolio snapshot → digest Slack hebdomadaire

---

## Base de données

Driver : **asyncpg** (direct, pas SQLAlchemy).
Paramètres : `$1`, `$2`… (pas `%s`).
Codec JSONB configuré dans `db/database.py` → les champs JSONB passent en Python dict nativement. **Ne pas envelopper dans `json.dumps()` avant d'écrire en DB.**

DATABASE_URL format Coolify : `postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio`
Le `+asyncpg` est strippé automatiquement dans `database.py` pour asyncpg.

---

## Conventions héritées de la stack

1. **Labels Traefik** : explicites dans `docker-compose.yml` — pas d'auto-injection
2. **env_file interdit** : Coolify injecte directement — ne pas ajouter `env_file: .env`
3. **Rebuild ≠ Restart** : toujours `/deploy` (rebuild complet), jamais `/restart`
4. **Commit + push AVANT** tout déclenchement de rebuild Coolify
5. **post_deployment_command** : payload JSON construit en Python (pas curl avec guillemets)
6. **Tickers Euronext** : format `CAP.PA` dans yfinance — enrichir `TICKER_EXCHANGE_MAP` dans `m1_quantitative.py` au fil des nouvelles positions

---

## Priorités en attente (P3 — après 1ère position clôturée)

Ces modules sont des stubs avec `NotImplementedError` :

| Fichier | Fonctionnalité |
|---------|---------------|
| `portfolio/post_mortem.py` | Post-mortem automatisé sur exit / réduction >50% |
| `learning/analyst_tracker.py` | Calcul verdict analystes à J+30 et J+90 |
| `learning/thesis_versioning.py` | Archivage + nouvelle version de thèse post-Régime 3 |
| `learning/pattern_library.py` | Enrichissement pattern library depuis post-mortems |

Schémas sectoriels à compléter (squelettes actuels insuffisants) :
- `sector_schemas/Luxury.json` — ajouter kpis, queries, peers complets
- `sector_schemas/Industrial.json` — idem

---

## Données initiales — Thèse Capgemini

Position bootstrapée manuellement (entrée 2026-05-01 à 102€, allocation 8.5%) :
- 6 hypothèses H1-H6 (synergies WNS, organique >2%, marge ≥13.3%, reprise EU IT, IA nette positive, Fit for Growth)
- Scénarios : Bear -5.2%/an → Central 12.4%/an → Bull 23.7%/an (horizon 5 ans)
- Peers Tier 1 : CTSH (analogie directe), Tier 2 : ACN (bellwether)
- Seuils : renforcer < 88€, alerte < 78€, sortie partielle 25% à 155-165€, 50% à 200-220€
- Payload complet dans la spec `portfolio-tracker-spec-v0.md` §17 étape 6
