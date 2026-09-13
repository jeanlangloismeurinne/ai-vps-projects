# Spécification Technique — Portfolio Tracker (PARTIE 2/2)
## Système de Suivi d'Investissement Long Terme
### Document à destination de Claude Code — VPS jlmvpscode

> **Lire PART1 avant cette partie.**

---

## 11. RESEARCH AGENT — RÉGIME 1

### backend/app/agents/research_agent.py

```python
import json, logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """Tu es un expert en investissement long terme (horizon 3-15 ans).
Construis une thèse d'investissement complète pour {company_name} ({ticker}).

## DONNÉES

### Data Brief :
```json
{data_brief}
```

### Schéma sectoriel :
```json
{sector_schema}
```

## PROCESSUS EN 8 ÉTAPES OBLIGATOIRES

### ÉTAPE 1 — PRÉ-QUALIFICATION
Si moins de 3 critères sur 5, retourner uniquement {"prequalification":"failed","reasons":[]}.
Critères : 1/ PER NTM < 20x OU FCF Yield > 5% ; 2/ Leader sectoriel ou position défendable ;
3/ Catalyseur identifiable à 6-18 mois ; 4/ FCF positif 2 derniers exercices ; 5/ Dette nette < 4x EBITDA.

### ÉTAPE 2 — ANALYSE FONDAMENTALE
Trajectoire CA 3 ans, marges, bilan, track record management, politique retour actionnaires.

### ÉTAPE 3 — ANALYSE CONCURRENTIELLE
Positionnement vs. 4-6 peers, écarts de valorisation, dynamiques sectorielles, moat.

### ÉTAPE 4 — EQUITY PITCH M&A (si acquisition centrale à la thèse)
Terms, logique stratégique, accrétion EPS, synergies réalistes, risques intégration.

### ÉTAPE 5 — SCÉNARIOS ET RENDEMENTS (Bear / Central / Bull, horizon 5 ans)
Pour chaque scénario : EPS CAGR, multiple de sortie, prix cible, dividendes cumulés, CAGR total.
Comparer avec CAC40/S&P500 long terme (~9%/an).

### ÉTAPE 6 — HYPOTHÈSES FONDATRICES (H1 à H7 maximum)
Pour chaque hypothèse : code, label court, description, criticité (critical/important/secondary),
horizon de vérification, KPI à surveiller, seuil de confirmation, seuil d'alerte.

### ÉTAPE 7 — TRACK RECORD ANALYSTES
Recommandations actuelles, évolution récente 12 mois, timing (laggard / en avance),
pondération recommandée (high/medium/low).

### ÉTAPE 8 — AVOCAT DU DIABLE (OBLIGATOIRE — ne pas adoucir)
Les 3 risques structurels les plus sérieux avec les MÊMES données.
Ne pas équilibrer, ne pas atténuer. Conclure avec prix baissier chiffré sur 5 ans.

## FORMAT DE SORTIE — JSON ENTRE ```json et ``` UNIQUEMENT

```json
{
  "ticker": "...", "company_name": "...", "prequalification": "passed",
  "thesis_one_liner": "...",
  "fundamental_analysis": {},
  "competitive_analysis": {},
  "ma_equity_pitch": {},
  "scenarios": {
    "bear":    {"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0},
    "central": {"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0},
    "bull":    {"eps_cagr_pct":0,"exit_pe":0,"price_target_5y":0,"dividends_cumulated":0,"cagr_pct":0}
  },
  "hypotheses": [
    {"code":"H1","label":"...","description":"...",
     "criticality":"critical|important|secondary",
     "verification_horizon":"...","kpi_to_watch":"...",
     "confirmation_threshold":"...","alert_threshold":"..."}
  ],
  "price_thresholds": {
    "reinforce_below":0, "alert_below":0,
    "partial_exit_zone1":{"from":0,"to":0,"pct_to_sell":25},
    "partial_exit_zone2":{"from":0,"to":0,"pct_to_sell":50}
  },
  "analyst_track_record": [
    {"firm":"...","current_reco":"...","current_target":0,
     "timing_quality":"high|medium|low","credibility_weight":"high|medium|low"}
  ],
  "bear_steel_man": {
    "risk_1":{"title":"...","argument":"...","evidence":"..."},
    "risk_2":{"title":"...","argument":"...","evidence":"..."},
    "risk_3":{"title":"...","argument":"...","evidence":"..."},
    "downside_scenario":"Si ces 3 risques se matérialisent : [X€] dans [Y] ans"
  }
}
```"""

async def run_regime_1(ticker: str, company_name: str, data_brief: dict,
                       sector_schema: dict, dust_client: DustClient) -> dict:
    prompt = RESEARCH_PROMPT.format(
        ticker=ticker, company_name=company_name,
        data_brief=json.dumps(data_brief, indent=2, default=str),
        sector_schema=json.dumps(sector_schema, indent=2),
    )
    result = await dust_client.run_agent(
        agent_id=settings.DUST_RESEARCH_AGENT_ID,
        message=prompt, model_override="claude-sonnet-4-5",
        temperature=0.2, timeout=180,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        thesis = json.loads(c[j+7:c.find("```", j+7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}")+1])
        thesis["dust_cost_usd"] = result.get("cost_usd")
        return thesis
    except json.JSONDecodeError as e:
        logger.error(f"Regime 1 parse error {ticker}: {e}")
        return {"error": "parse_error", "raw_content": result["content"][:2000]}
```

---

## 12. PORTFOLIO AGENT — RÉGIMES 2, 3 ET PRÉ-EVENT

### backend/app/agents/portfolio_agent.py

```python
import json, logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)


# ── PRÉ-EVENT BRIEF (J-2) ────────────────────────────────────────────────────

async def run_pre_event_brief(ticker: str, company_name: str, hypotheses: list,
                               event_type: str, guidance_published: dict,
                               dust_client: DustClient) -> dict:
    prompt = f"""Demain : publication {event_type} pour {company_name} ({ticker}).

HYPOTHÈSES ACTIVES :
{json.dumps(hypotheses, indent=2)}

GUIDANCE PUBLIÉE (si dispo) :
{json.dumps(guidance_published, indent=2)}

Produis un brief de lecture JSON (3 items max dans reading_checklist) :
{{
  "event":"{event_type}","ticker":"{ticker}",
  "reading_checklist":[
    {{"hypothesis_code":"H1","what_to_look_for":"...",
      "confirmation_signal":"...","alert_signal":"..."}}
  ],
  "ignore_completely":["cours à l'ouverture","commentaires analystes premières heures"],
  "key_numbers_to_find":["..."]
}}
JSON uniquement."""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gpt-4o-mini", temperature=0.1,
    )
    try:
        c = result["content"]
        return json.loads(c[c.find("{"):c.rfind("}")+1])
    except Exception:
        return {"error": "parse_error"}


# ── RÉGIME 2 ─────────────────────────────────────────────────────────────────

async def run_regime_2(ticker: str, company_name: str, data_brief: dict,
                       dust_client: DustClient) -> dict:
    prompt = f"""Tu exécutes la revue trimestrielle de {company_name} ({ticker}).

## DATA BRIEF
```json
{json.dumps(data_brief, indent=2, default=str)}
```

## INSTRUCTIONS
Pour chaque hypothèse dans active_thesis.hypotheses :
- Statut : "confirmed" | "neutral" | "alert" | "invalidated"
- Justification en 1 phrase avec fait chiffré

Règles d'escalade :
- 1 hypothèse critique "invalidated" → flag = "REVIEW_REQUIRED"
- 2 hypothèses (quelle criticité) "alert" → flag = "REVIEW_REQUIRED"
- Sinon → flag = "RAS"

```json
{{
  "ticker":"{ticker}","review_date":"ISO","regime":2,
  "hypotheses_scores":[
    {{"code":"H1","status":"confirmed|neutral|alert|invalidated","evidence":"1 phrase"}}
  ],
  "kpis_observed":{{
    "organic_growth_cc_pct":null,"operating_margin_pct":null,
    "guidance_vs_consensus":"above|inline|below|maintained|raised|cut"
  }},
  "sector_context":"1 phrase sur les pairs",
  "flag":"RAS|REVIEW_REQUIRED","escalation_reason":null,
  "recommendation":"maintain|reinforce|reduce_25|reduce_50|exit",
  "alert_level":"green|orange|red"
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gemini-2-5-flash-preview", temperature=0.1,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        return json.loads(c[j+7:c.find("```", j+7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}")+1])
    except json.JSONDecodeError:
        return {"error":"parse_error","flag":"REVIEW_REQUIRED",
                "escalation_reason":"parse_error_requires_manual_review"}


# ── RÉGIME 3 ─────────────────────────────────────────────────────────────────

async def run_regime_3(ticker: str, company_name: str, data_brief: dict,
                       position_context: dict, deviation_trigger: dict,
                       dust_client: DustClient) -> dict:
    current_price = position_context.get("current_price", "?")
    prompt = f"""Tu es gestionnaire de portefeuille. Décision requise — {company_name} ({ticker}).

## CONTEXTE DE POSITION
```json
{json.dumps(position_context, indent=2, default=str)}
```

## DÉCLENCHEUR DE L'ESCALADE
```json
{json.dumps(deviation_trigger, indent=2)}
```

## DATA BRIEF COMPLET (avec M3 qualitatif)
```json
{json.dumps(data_brief, indent=2, default=str)}
```

## PROCESSUS EN 3 ÉTAPES OBLIGATOIRES

### ÉTAPE 1 — DIAGNOSTIC
Écart structurel (change la thèse) ou conjoncturel (bruit) ? 3-5 phrases avec faits.

### ÉTAPE 2 — RÉVISION DE LA THÈSE
Si positif : scénarios à réviser ? Cible à repousser ?
Si négatif : quelle hypothèse est compromise ? La thèse tient-elle encore ?

TEST DE MUNGER (OBLIGATOIRE) :
"En faisant abstraction de ma position, achèterais-je ce titre
aujourd'hui à {current_price} ?" → OUI ou NON + 2 phrases de justification.

### ÉTAPE 3 — DÉCISION
reinforce | maintain | reduce_25 | reduce_50 | exit — 3-4 phrases de justification.

```json
{{
  "ticker":"{ticker}","review_date":"ISO","regime":3,
  "deviation_type":"positive|negative",
  "diagnosis":{{"nature":"structural|cyclical","explanation":"..."}},
  "thesis_revision":{{
    "strength_change":"stronger|unchanged|weaker|invalidated",
    "revised_scenarios":null,"hypotheses_updated":[]
  }},
  "munger_test":{{"answer":"yes|no","rationale":"..."}},
  "decision":{{
    "recommendation":"reinforce|maintain|reduce_25|reduce_50|exit",
    "rationale":"...","urgency":"immediate|next_session|week"
  }},
  "updated_thresholds":{{"partial_exit_zone1":null,"partial_exit_zone2":null}},
  "alert_level":"green|orange|red"
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="claude-sonnet-4-5", temperature=0.2, timeout=180,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        return json.loads(c[j+7:c.find("```", j+7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}")+1])
    except json.JSONDecodeError as e:
        logger.error(f"Regime 3 parse error {ticker}: {e}")
        return {"error": "parse_error", "raw_content": result["content"][:1000]}
```

---

## 13. SECTOR PULSE

### backend/app/agents/sector_pulse.py

```python
import json, logging
from app.agents.dust_client import DustClient
from app.config import settings

logger = logging.getLogger(__name__)

async def run_sector_pulse(peer_ticker: str, peer_company: str,
                            main_position_ticker: str, peer_m2_data: dict,
                            main_hypotheses: list, dust_client: DustClient) -> dict:
    prompt = f"""Le pair {peer_company} ({peer_ticker}) vient de publier.
Impact sur la thèse de {main_position_ticker} ?

## RÉSULTATS DU PAIR
```json
{json.dumps(peer_m2_data, indent=2, default=str)}
```

## HYPOTHÈSES DE {main_position_ticker}
```json
{json.dumps(main_hypotheses, indent=2)}
```

Règles :
- Réponds UNIQUEMENT sur les hypothèses listées ci-dessus
- Pour chaque hypothèse impactée : direction + 1 phrase de justification
- Score : -5 (très négatif) à +5 (très positif)
- action = "store" si score entre -2 et +2
- action = "escalate_to_regime3" si score ≤ -3

```json
{{
  "peer_ticker":"{peer_ticker}",
  "main_position_ticker":"{main_position_ticker}",
  "peer_result_summary":"1 phrase avec chiffres clés",
  "hypothesis_impacts":{{
    "H2":{{"direction":"positive|negative|neutral","rationale":"..."}}
  }},
  "pulse_score":0,
  "action":"store|escalate_to_regime3",
  "escalation_reason":null
}}
```"""

    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID, message=prompt,
        model_override="gemini-2-5-flash-preview", temperature=0.1,
    )
    try:
        c = result["content"]
        j = c.find("```json")
        pulse = json.loads(c[j+7:c.find("```", j+7)].strip()) if j >= 0 \
            else json.loads(c[c.find("{"):c.rfind("}")+1])
        pulse["dust_cost_usd"] = result.get("cost_usd")
        return pulse
    except json.JSONDecodeError:
        return {"peer_ticker":peer_ticker,"action":"store","pulse_score":0,"error":"parse_error"}
```

---

## 14. NOTIFICATIONS SLACK

### backend/app/notifications/slack_notifier.py

```python
import logging
from slack_sdk.web.async_client import AsyncWebClient
from app.config import settings

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self):
        self.client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        self.channel = settings.SLACK_PORTFOLIO_CHANNEL_ID

    async def send_pre_event_brief(self, ticker: str, brief: dict, event: dict):
        checklist = "\n".join(
            f"• *{i['hypothesis_code']}* : {i['what_to_look_for']}\n"
            f"  ✅ {i['confirmation_signal']} | 🚨 {i['alert_signal']}"
            for i in brief.get("reading_checklist", [])
        )
        await self._send([
            {"type":"header","text":{"type":"plain_text","text":f"⚡ Brief Pré-Event — {ticker}"}},
            {"type":"section","text":{"type":"mrkdwn",
             "text":f"*Événement demain :* {event['event_type']}\n\n{checklist}"}},
        ])

    async def send_regime2_report(self, ticker: str, review: dict):
        emoji = {"green":"🟢","orange":"🟡","red":"🔴"}.get(review.get("alert_level","green"),"⚪")
        scores = "\n".join(
            f"• *{s['code']}* : {s['status'].upper()} — {s.get('evidence','')}"
            for s in review.get("hypotheses_scores",[])
        )
        await self._send([
            {"type":"header","text":{"type":"plain_text",
             "text":f"{emoji} Revue Trimestrielle — {ticker}"}},
            {"type":"section","fields":[
                {"type":"mrkdwn","text":f"*Flag :* {review.get('flag','RAS')}"},
                {"type":"mrkdwn","text":f"*Recommandation :* {review.get('recommendation','').upper()}"},
            ]},
            {"type":"section","text":{"type":"mrkdwn","text":f"*Hypothèses :*\n{scores}"}},
        ])

    async def send_regime3_decision(self, ticker: str, review: dict):
        d = review.get("decision",{})
        munger = review.get("munger_test",{})
        urgency_emoji = {"immediate":"🚨","next_session":"⚡","week":"📅"}.get(d.get("urgency","week"),"📅")
        await self._send([
            {"type":"header","text":{"type":"plain_text","text":f"🔍 DÉCISION REQUISE — {ticker}"}},
            {"type":"section","fields":[
                {"type":"mrkdwn","text":f"*Nature :* {review.get('diagnosis',{}).get('nature','')}"},
                {"type":"mrkdwn","text":f"*Force thèse :* {review.get('thesis_revision',{}).get('strength_change','')}"},
            ]},
            {"type":"section","text":{"type":"mrkdwn",
             "text":f"*Diagnostic :* {review.get('diagnosis',{}).get('explanation','')}"}},
            {"type":"section","text":{"type":"mrkdwn",
             "text":f"*Test Munger :* {'✅ OUI' if munger.get('answer')=='yes' else '❌ NON'} — {munger.get('rationale','')}"}},
            {"type":"section","text":{"type":"mrkdwn",
             "text":f"{urgency_emoji} *RECOMMANDATION : {d.get('recommendation','').upper()}*\n{d.get('rationale','')}"}},
        ])

    async def send_sector_pulse_escalation(self, main_ticker: str, peer_ticker: str, pulse: dict):
        await self._send([{"type":"section","text":{"type":"mrkdwn",
            "text":f"🚨 *Sector Pulse Escalation* — {main_ticker}\n"
                   f"Pair *{peer_ticker}* score {pulse.get('pulse_score')}\n"
                   f"{pulse.get('peer_result_summary','')}\n*Action :* Régime 3 déclenché"}}])

    async def send_weekly_digest(self, snapshot: dict):
        positions_text = "\n".join(
            f"• *{p['ticker']}* : {p.get('recommendation','maintain')} "
            f"| Score : {p.get('thesis_score','?')}/7 | P&L : {p.get('unrealized_pnl_pct',0):.1f}%"
            for p in snapshot.get("positions",[])
        )
        flags = snapshot.get("concentration_flags",[])
        flags_text = ("\n⚠️ *Flags :*\n" + "\n".join(
            f"• {f['type'].upper()} {f.get('sector','')} = {f.get('total_pct',0):.0f}%"
            for f in flags)) if flags else ""
        await self._send([
            {"type":"header","text":{"type":"plain_text","text":"📊 Revue Hebdomadaire Portfolio"}},
            {"type":"section","text":{"type":"mrkdwn","text":f"*Positions :*\n{positions_text}{flags_text}"}},
        ])

    async def send_budget_alert(self, spent: float, budget: float):
        await self._send([{"type":"section","text":{"type":"mrkdwn",
            "text":f"⚠️ *Budget Dust 80% atteint* : ${spent:.2f}/${budget:.2f}\n"
                   f"Régimes 1 et 3 suspendus si dépassement."}}])

    async def send_error_alert(self, ticker: str, error: str):
        await self._send([{"type":"section","text":{"type":"mrkdwn",
            "text":f"❌ *Erreur* — {ticker}\n```{error[:500]}```"}}])

    async def _send(self, blocks: list):
        try:
            await self.client.chat_postMessage(channel=self.channel, blocks=blocks)
        except Exception as e:
            logger.error(f"Slack error: {e}")
```

---

## 15. DOCKER-COMPOSE ET DOCKERFILES

### docker-compose.yml

```yaml
# IMPORTANT :
# - Labels Traefik explicites (pas d'auto-injection mode dockercompose)
# - Pas de env_file : Coolify injecte les variables directement
# - Rebuild via /deploy, jamais /restart

networks:
  infra-net:
    external: true

services:
  portfolio-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: portfolio-backend
    networks:
      - infra-net
    expose:
      - "8050"
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.portfolio-backend.rule=Host(`portfolio.jlmvpscode.duckdns.org`) && PathPrefix(`/api`)"
      - "traefik.http.routers.portfolio-backend.entrypoints=websecure"
      - "traefik.http.routers.portfolio-backend.tls.certresolver=letsencrypt"
      - "traefik.http.services.portfolio-backend.loadbalancer.server.port=8050"

  portfolio-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: portfolio-frontend
    networks:
      - infra-net
    expose:
      - "8051"
    restart: unless-stopped
    environment:
      - NEXT_PUBLIC_API_URL=https://portfolio.jlmvpscode.duckdns.org/api
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.portfolio-frontend.rule=Host(`portfolio.jlmvpscode.duckdns.org`)"
      - "traefik.http.routers.portfolio-frontend.entrypoints=websecure"
      - "traefik.http.routers.portfolio-frontend.tls.certresolver=letsencrypt"
      - "traefik.http.services.portfolio-frontend.loadbalancer.server.port=8051"
```

### backend/Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8050
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050", "--workers", "1"]
```

### backend/requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.0
asyncpg==0.30.0
sqlalchemy[asyncio]==2.0.36
pydantic-settings==2.6.0
apscheduler==3.10.4
yfinance==0.2.48
feedparser==6.0.11
requests==2.32.3
slack-sdk==3.33.0
```

---

## 16. SCHÉMA SECTORIEL IT SERVICES

### sector_schemas/IT_Services.json

```json
{
  "sector": "IT_Services",
  "display_name": "IT Services & Consulting",
  "kpis_specifiques": [
    "organic_growth_constant_currency",
    "book_to_bill_ratio",
    "attrition_rate",
    "offshore_ratio",
    "ai_bookings_percentage",
    "large_deals_tcv"
  ],
  "peers_defaut": ["ACN", "CTSH", "TCS", "INFY", "HCLTECH", "WIT"],
  "queries_sectorielles": [
    "IT services spending enterprise {year} outlook",
    "generative AI enterprise adoption IT services {year}",
    "IT services pricing pressure automation {year}"
  ],
  "red_flags_sectoriels": [
    "budget freeze", "discretionary spending cut",
    "AI replacing developers", "headcount reduction clients"
  ],
  "positive_signals": [
    "cloud migration", "AI transformation", "record bookings", "deal acceleration"
  ]
}
```

---

## 17. GUIDE DE DÉMARRAGE ET BOOTSTRAP CAPGEMINI

### Étape 1 — Infrastructure

```bash
docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_portfolio;'

docker exec -i shared-postgres psql -U admin -d db_portfolio < \
  backend/app/db/migrations/001_initial.sql
```

### Étape 2 — Créer les agents Dust (UI dust.tt, workspace plm-siege)

**Agent 1 : `research-agent`**
- Model : Claude Sonnet (latest)
- Web search : activé
- Instructions système :
  ```
  Tu es un expert en investissement long terme chargé de construire des thèses
  d'investissement complètes et rigoureuses. Tu suis toujours le processus en
  8 étapes fourni dans chaque message. Tu retournes toujours du JSON valide
  entre ```json et ```. Tu n'omets jamais l'étape 8 (Avocat du Diable).
  ```
- Copier l'ID → `DUST_RESEARCH_AGENT_ID`

**Agent 2 : `portfolio-agent`**
- Model : Claude Sonnet (latest) — overridé par le code selon le régime
- Web search : activé (utilisé en Régime 3 et M3 uniquement)
- Instructions système :
  ```
  Tu es un agent de gestion de portefeuille long terme. Tu exécutes
  précisément les instructions fournies dans chaque message.
  Tu retournes toujours du JSON valide entre ```json et ```.
  Tu ne fournis jamais d'information non demandée.
  ```
- Copier l'ID → `DUST_PORTFOLIO_AGENT_ID`

### Étape 3 — Canal Slack

```
1. Créer #portfolio-management dans Slack
2. Inviter @ai_vps_jlm
3. Récupérer le Channel ID (depuis l'URL ou l'API Slack)
   → renseigner SLACK_PORTFOLIO_CHANNEL_ID dans Coolify
```

### Étape 4 — Variables d'environnement Coolify

```
DUST_API_KEY=sk-dust-...
DUST_WORKSPACE_ID=plm-siege
DUST_RESEARCH_AGENT_ID=[copié depuis UI Dust]
DUST_PORTFOLIO_AGENT_ID=[copié depuis UI Dust]
DUST_MONTHLY_BUDGET_USD=5.0
DATABASE_URL=postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
REDIS_URL=redis://shared-redis:6379
SLACK_BOT_TOKEN=[depuis /opt/cyber-agent/.env]
SLACK_APP_TOKEN=[depuis /opt/cyber-agent/.env]
SLACK_PORTFOLIO_CHANNEL_ID=C0XXXXXXXXX
FMP_API_KEY=[Financial Modeling Prep free tier]
BASE_CURRENCY=EUR
```

### Étape 5 — Deploy

```bash
git add .
git commit -m "feat: portfolio-tracker initial setup"
git push origin main

python3 -c "
import requests
r = requests.get(
    'http://localhost:8000/api/v1/deploy',
    params={'uuid': 'COOLIFY_APP_UUID', 'force': 'false'},
    headers={'Authorization': 'Bearer COOLIFY_TOKEN'}
)
print(r.status_code, r.text)
"
```

### Étape 6 — Bootstrap Capgemini

La thèse est déjà construite. Importer directement via l'API :

```bash
# 1. Créer la position
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

# 2. Importer la thèse
curl -X POST https://portfolio.jlmvpscode.duckdns.org/api/positions/{POSITION_ID}/thesis \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "thesis_one_liner": "Leader mondial ESN décoté de 40-50% vs. peers par excès de risque géographique et IA, dont la thèse de redressement est calquée sur Cognizant 2023-2025",
  "bear_steel_man": "Risques structurels : 1/ Disruption IA cannibalise les revenus offshore avant monétisation. 2/ Europe IT en contraction 3+ ans (récession). 3/ WNS synergies décevantes, dilution EPS longue.",
  "scenarios": {
    "bear":    {"eps_cagr_pct": -2, "exit_pe": 9,  "price_target_5y": 72,  "dividends_cumulated": 17, "cagr_pct": -5.2},
    "central": {"eps_cagr_pct":  8, "exit_pe": 14, "price_target_5y": 172, "dividends_cumulated": 21, "cagr_pct": 12.4},
    "bull":    {"eps_cagr_pct": 14, "exit_pe": 18, "price_target_5y": 285, "dividends_cumulated": 24, "cagr_pct": 23.7}
  },
  "price_thresholds": {
    "reinforce_below": 88, "alert_below": 78,
    "partial_exit_zone1": {"from": 155, "to": 165, "pct_to_sell": 25},
    "partial_exit_zone2": {"from": 200, "to": 220, "pct_to_sell": 50}
  },
  "hypotheses": [
    {
      "code": "H1", "label": "Synergies WNS",
      "description": "L'acquisition WNS génère les synergies revenus annoncées dans les délais prévus",
      "criticality": "critical",
      "verification_horizon": "FY2026/FY2027",
      "kpi_to_watch": "Contribution inorganique WNS en pts de croissance CA",
      "confirmation_threshold": "Synergies revenus > 100M€ run-rate fin 2027",
      "alert_threshold": "Contribution WNS < 3.5 pts CA en FY2026"
    },
    {
      "code": "H2", "label": "Organique > 2%",
      "description": "La croissance organique refranchit les 2-3% en CC dès H1 2026",
      "criticality": "critical",
      "verification_horizon": "Q1-Q2 2026",
      "kpi_to_watch": "Croissance organique constant currency publiée trimestriellement",
      "confirmation_threshold": "Croissance organique CC > 3.5%",
      "alert_threshold": "Croissance organique CC < 1.5%"
    },
    {
      "code": "H3", "label": "Marge >= 13.3%",
      "description": "La marge opérationnelle se maintient ou s'améliore malgré les coûts de restructuration",
      "criticality": "important",
      "verification_horizon": "FY2026",
      "kpi_to_watch": "Marge opérationnelle semestrielle et annuelle",
      "confirmation_threshold": "Marge opérationnelle >= 13.6%",
      "alert_threshold": "Marge opérationnelle < 12.8%"
    },
    {
      "code": "H4", "label": "Reprise Europe IT",
      "description": "L'environnement IT européen se normalise d'ici 2027",
      "criticality": "important",
      "verification_horizon": "2027",
      "kpi_to_watch": "PMI manufacturier EU + commentary peers ESN sur budgets IT Europe",
      "confirmation_threshold": "PMI EU > 50 deux trimestres consécutifs",
      "alert_threshold": "Contraction IT Europe > 2 trimestres consécutifs"
    },
    {
      "code": "H5", "label": "IA : demande nette positive",
      "description": "L'IA générative crée plus de demande de services IT qu'elle n'en détruit",
      "criticality": "important",
      "verification_horizon": "2026-2028",
      "kpi_to_watch": "Bookings IA Capgemini + Accenture AI bookings comme signal sectoriel",
      "confirmation_threshold": "Bookings IA Capgemini > 1.5Md€/an",
      "alert_threshold": "Accenture et TCS reportent cannibalisation nette revenus IT traditionnels"
    },
    {
      "code": "H6", "label": "Fit for Growth exécuté",
      "description": "Le programme Fit for Growth de 700M€ est livré dans les délais et le budget",
      "criticality": "secondary",
      "verification_horizon": "FY2026",
      "kpi_to_watch": "Coûts restructuration cumulés vs. 700M€ budget",
      "confirmation_threshold": "700M€ costs-out livré sans dépassement à fin 2026",
      "alert_threshold": "Coûts > 850M€ ou délai repoussé après 2027"
    }
  ],
  "peers": [
    {
      "ticker": "CTSH", "tier_level": 1,
      "rationale": "Analogie directe de transformation — CTSH 2023 = CAP 2026, même playbook post-acquisition transformante (Belcan = WNS analogue)",
      "hypotheses_watched": ["H2", "H3", "H6"],
      "metrics_to_extract": ["organic_growth_cc", "margin_trend", "acquisition_synergies_progress"]
    },
    {
      "ticker": "ACN", "tier_level": 2,
      "rationale": "Bellwether mondial IT services — indicateur IA et pricing sectoriel",
      "hypotheses_watched": ["H2", "H4", "H5"],
      "metrics_to_extract": ["organic_growth_cc", "ai_bookings", "guidance_language", "new_bookings"]
    },
    {"ticker": "TCS",     "tier_level": 3},
    {"ticker": "INFY",    "tier_level": 3},
    {"ticker": "HCLTECH", "tier_level": 3}
  ],
  "analyst_track_record": [
    {
      "firm": "UBS", "current_reco": "neutral", "current_target": 110,
      "timing_quality": "low", "credibility_weight": "low",
      "notes": "Dégradé le 24/04/2026 après -30% de baisse — pattern laggard confirmé"
    },
    {
      "firm": "Oddo BHF", "current_reco": "buy", "current_target": 145,
      "timing_quality": "high", "credibility_weight": "high",
      "notes": "Maintien buy tout au long de la baisse — signal contrarian fiable"
    }
  ]
}
EOF
```

### Étape 7 — Mettre à jour _KNOWN_PROJECTS

```python
# projects/assistant-ia/app/slack_app.py
_KNOWN_PROJECTS = [
    "assistant-ia", "bank-review", "tool-file-intake",
    "ev-prices", "homepage",
    "portfolio-tracker",  # AJOUTER
]
```

---

## 18. PIÈGES CONNUS (STACK EXISTANTE)

1. **Labels Traefik** : explicites dans docker-compose.yml. Pas d'auto-injection en mode dockercompose.

2. **env_file interdit** : ne pas ajouter `env_file: .env` dans docker-compose.yml. Coolify injecte ses variables directement.

3. **Rebuild ≠ Restart** : utiliser `/deploy` ou `/start`, jamais `/restart` pour les apps dockercompose.

4. **post_deployment_command** : construire le payload JSON en Python, pas via curl avec guillemets.

5. **APScheduler** : utiliser `AsyncIOScheduler`. Ne pas utiliser `BackgroundScheduler` (non async-safe avec FastAPI asyncio).

6. **Tickers Euronext** : format `CAP.PA` dans yfinance. Utiliser `TICKER_EXCHANGE_MAP` dans m1_quantitative.py. Enrichir cette map au fil des nouvelles positions.

7. **Coolify token** : générer à la volée via insertion directe en base Coolify-DB (cf. CLAUDE.md existant sur le VPS).

8. **PostgreSQL asyncpg** : les paramètres sont en `$1`, `$2`... (pas `%s` comme psycopg2). Attention aux requêtes copiées depuis d'autres projets.

---

## 19. BUDGET MENSUEL — SIMULATION

| Tâche | Modèle | Coût/run | Fréquence (8 pos.) | Coût mensuel |
|---|---|---|---|---|
| Nouvelle thèse | claude-sonnet-4-5 | ~$0.30 | 0.5×/mois | ~$0.15 |
| Régime 2 | gemini-2-5-flash | ~$0.005 | 2.7×/mois | ~$0.013 |
| Sector Pulse | gemini-2-5-flash | ~$0.003 | 8×/mois | ~$0.024 |
| Régime 3 | claude-sonnet-4-5 | ~$0.25 | 0.25×/mois | ~$0.063 |
| Pre-event brief | gpt-4o-mini | ~$0.001 | 10×/mois | ~$0.010 |
| M3 qualitatif | gemini-2-5-flash | ~$0.008 | 3×/mois | ~$0.024 |
| **TOTAL** | | | | **~$0.28/mois** |
| **Marge sur $5** | | | | **$4.72** |

---

## 20. AMÉLIORATIONS FUTURES (PRIORITÉ 3)

Ces fonctionnalités sont documentées pour implémentation ultérieure (après 1ère position clôturée) :

### Post-Mortem automatisé

Déclenché sur exit total ou réduction > 50%. Appel Portfolio Agent avec 5 questions structurées :
1. Quelle hypothèse a le plus contribué à la performance ?
2. Quelle hypothèse s'est avérée fausse ?
3. L'analogie de pair était-elle prédictive ?
4. Le timing d'entrée/sortie était-il optimal ?
5. Quel signal aurait permis d'agir plus tôt ?

Output → enrichissement `pattern_library` et `analyst_tracker`.

### Track Record Analystes (automatisation)

Après 30 et 90 jours suivant chaque action analyste enregistrée :
- Récupérer le cours via M1
- Calculer le verdict : `early` / `timely` / `lagging` / `contrarian`
- Mettre à jour `lagging_rate` et `signal_quality_rate` dans la vue `analyst_track_records`

### Version Control des Thèses

Quand Régime 3 révise des hypothèses :
1. Archiver la version actuelle (`is_current = FALSE`, `invalidated_at = NOW()`)
2. Créer une nouvelle version (version + 1) avec les paramètres révisés
3. Les hypothèses originales (H1-H7 de la thèse v1) restent immuables

---

*Document généré le 2026-05-01 — Version 1.0 — PARTIE 2/2*
*Workspace Dust : plm-siege | VPS : jlmvpscode.duckdns.org*
