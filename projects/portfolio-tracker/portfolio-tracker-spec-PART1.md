# Spécification Technique — Portfolio Tracker (PARTIE 1/2)
## Système de Suivi d'Investissement Long Terme
### Document à destination de Claude Code — VPS jlmvpscode

> **Ce document est en 2 parties. Lire PART1 puis PART2 dans l'ordre.**

---

## CONTEXTE D'EXÉCUTION

Système de suivi d'investissement boursier long terme, déployé sur le VPS Hetzner (jlmvpscode.duckdns.org) selon les conventions de la stack en place.

**Conventions obligatoires héritées de la stack :**
- Labels Traefik explicites dans docker-compose.yml (pas d'auto-injection)
- Pas de `env_file` dans docker-compose — Coolify injecte les variables
- Rebuild via API Coolify `/deploy`, jamais `/restart`
- Commit + push GitHub AVANT tout déclenchement de rebuild
- post_deployment_command : payload JSON construit en Python

---

## 1. VUE D'ENSEMBLE

### 1.1 Les 3 Régimes d'Analyse

```
RÉGIME 1 — THESIS CONSTRUCTION
  Déclenchement : manuel uniquement
  Modèle Dust   : claude-sonnet-4-5
  Web search    : OUI
  Données       : M1 + M2 + M3
  Coût estimé   : ~$0.30/run
  Inclut        : analyse fondamentale, concurrentielle, scénarios,
                  hypothèses H1-H7, AVOCAT DU DIABLE obligatoire

RÉGIME 2 — MONITORING ROUTINE
  Déclenchement : calendrier événementiel (J+1 publications)
  Modèle Dust   : gemini-2-5-flash-preview
  Web search    : NON
  Données       : M1 + M2 + sector_pulses accumulés
  Coût estimé   : ~$0.005/run
  Output        : score H1-H7 + flag RAS / REVIEW_REQUIRED

RÉGIME 3 — DECISION REVIEW
  Déclenchement : escalade Régime 2 OU seuil cours franchi
  Modèle Dust   : claude-sonnet-4-5 + web search
  Données       : M1 + M2 + M3 + position_context
  Coût estimé   : ~$0.25/run
  Output        : diagnostic + thèse révisée + décision + test Munger
```

### 1.2 Les 2 Agents Dust (à créer from scratch, workspace : `plm-siege`)

- **research-agent** : Régime 1 uniquement
- **portfolio-agent** : Régimes 2, 3, Sector Pulse, Pre-Event Brief

### 1.3 Budget

- Hard cap : $5.00/mois
- Alerte Slack à $4.00 (80%)

---

## 2. STACK ET DÉPLOIEMENT

### 2.1 Stack

```
Backend       : Python 3.12 / FastAPI / APScheduler
Database      : PostgreSQL 16 + pgvector (shared-postgres:5432)
Cache         : Redis 7 (shared-redis:6379)
Frontend      : Next.js 14 / Tailwind CSS
Conteneurs    : Docker via Coolify
Reverse proxy : Traefik v3
Notifications : Slack bot @ai_vps_jlm (Socket Mode)
```

### 2.2 Checklist Nouveau Projet

```bash
mkdir -p /projects/portfolio-tracker

docker exec shared-postgres psql -U admin -c \
  'CREATE DATABASE db_portfolio;'

# Créer #portfolio-management dans Slack, inviter @ai_vps_jlm
# Récupérer Channel ID → SLACK_PORTFOLIO_CHANNEL_ID

# Ajouter "portfolio-tracker" dans _KNOWN_PROJECTS
# dans projects/assistant-ia/app/slack_app.py
```

### 2.3 Ports et URL

```
Backend  : 8050 → portfolio.jlmvpscode.duckdns.org/api
Frontend : 8051 → portfolio.jlmvpscode.duckdns.org
```

### 2.4 Structure du Repository

```
projects/portfolio-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── positions.py
│   │   │   ├── calendar.py
│   │   │   ├── portfolio.py
│   │   │   ├── watchlist.py
│   │   │   ├── analysts.py
│   │   │   └── trigger.py
│   │   ├── data_collection/
│   │   │   ├── m1_quantitative.py
│   │   │   ├── m2_events.py
│   │   │   ├── m3_qualitative.py
│   │   │   └── assembler.py
│   │   ├── calendar/
│   │   │   ├── calendar_builder.py
│   │   │   ├── event_router.py
│   │   │   └── watchlist_monitor.py
│   │   ├── agents/
│   │   │   ├── dust_client.py
│   │   │   ├── research_agent.py
│   │   │   ├── portfolio_agent.py
│   │   │   └── sector_pulse.py
│   │   ├── portfolio/
│   │   │   ├── portfolio_view.py
│   │   │   ├── concentration_checker.py
│   │   │   └── post_mortem.py
│   │   ├── learning/
│   │   │   ├── analyst_tracker.py
│   │   │   ├── pattern_library.py
│   │   │   └── thesis_versioning.py
│   │   ├── notifications/
│   │   │   └── slack_notifier.py
│   │   └── db/
│   │       ├── database.py
│   │       ├── models.py
│   │       └── migrations/001_initial.sql
│   ├── sector_schemas/
│   │   ├── IT_Services.json
│   │   ├── Luxury.json
│   │   └── Industrial.json
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── pages/
│   │   ├── index.js
│   │   ├── position/[id].js
│   │   ├── calendar.js
│   │   ├── watchlist.js
│   │   └── analysts.js
│   ├── components/
│   │   ├── HypothesisScorecard.js
│   │   ├── ThesisTimeline.js
│   │   ├── SectorPulseLog.js
│   │   ├── PeerComparison.js
│   │   ├── CalendarView.js
│   │   └── RecommendationBadge.js
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

---

## 3. SCHÉMA DE BASE DE DONNÉES

### migrations/001_initial.sql

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- POSITIONS
CREATE TABLE positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker          VARCHAR(20) NOT NULL UNIQUE,
    company_name    VARCHAR(200) NOT NULL,
    sector_schema   VARCHAR(50) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    entry_date      DATE NOT NULL,
    entry_price     DECIMAL(12,4) NOT NULL,
    entry_price_currency VARCHAR(3) DEFAULT 'EUR',
    allocation_pct  DECIMAL(5,2),
    status          VARCHAR(20) DEFAULT 'active',
    base_currency   VARCHAR(3) DEFAULT 'EUR',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- THÈSES (versionnées)
CREATE TABLE theses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id     UUID REFERENCES positions(id),
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT NOW(),
    thesis_one_liner TEXT NOT NULL,
    bear_steel_man  TEXT NOT NULL,
    scenarios_json  JSONB NOT NULL,
    price_thresholds_json JSONB,
    entry_context_json JSONB,
    invalidated_at  TIMESTAMP,
    invalidation_reason TEXT,
    is_current      BOOLEAN DEFAULT TRUE,
    embedding       vector(1536)
);

-- HYPOTHÈSES
CREATE TABLE hypotheses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thesis_id       UUID REFERENCES theses(id),
    position_id     UUID REFERENCES positions(id),
    code            VARCHAR(5) NOT NULL,
    label           VARCHAR(200) NOT NULL,
    description     TEXT,
    criticality     VARCHAR(10) NOT NULL,
    verification_horizon VARCHAR(50),
    kpi_to_watch    TEXT,
    confirmation_threshold TEXT,
    alert_threshold TEXT,
    current_status  VARCHAR(20) DEFAULT 'neutral',
    last_updated    TIMESTAMP DEFAULT NOW(),
    original        BOOLEAN DEFAULT TRUE
);

-- REVIEWS
CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id     UUID REFERENCES positions(id),
    regime          INTEGER NOT NULL,
    triggered_by    VARCHAR(100),
    review_date     TIMESTAMP DEFAULT NOW(),
    hypotheses_scores_json JSONB,
    recommendation  VARCHAR(20),
    rationale       TEXT,
    data_brief_json JSONB,
    full_output_json JSONB,
    dust_tokens_used INTEGER,
    dust_cost_usd   DECIMAL(8,6),
    alert_level     VARCHAR(10)
);

-- SECTOR PULSES
CREATE TABLE sector_pulses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peer_ticker         VARCHAR(20) NOT NULL,
    main_position_id    UUID REFERENCES positions(id),
    pulse_date          TIMESTAMP DEFAULT NOW(),
    peer_result_summary TEXT,
    hypothesis_impacts_json JSONB,
    pulse_score         INTEGER,
    action              VARCHAR(20),
    accumulated         BOOLEAN DEFAULT FALSE,
    dust_cost_usd       DECIMAL(8,6)
);

-- PEERS
CREATE TABLE peers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id         UUID REFERENCES positions(id),
    peer_ticker         VARCHAR(20) NOT NULL,
    peer_company_name   VARCHAR(200),
    tier_level          INTEGER NOT NULL,
    rationale           TEXT,
    hypotheses_watched  VARCHAR(20)[],
    metrics_to_extract  VARCHAR(100)[],
    created_at          TIMESTAMP DEFAULT NOW()
);

-- CALENDAR EVENTS
CREATE TABLE calendar_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker              VARCHAR(20) NOT NULL,
    event_type          VARCHAR(50) NOT NULL,
    event_date          DATE NOT NULL,
    trigger_brief_date  DATE,
    trigger_review_date DATE,
    priority            VARCHAR(10) DEFAULT 'high',
    source              VARCHAR(50),
    processed           BOOLEAN DEFAULT FALSE,
    brief_processed     BOOLEAN DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- WATCHLIST
CREATE TABLE watchlist (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker              VARCHAR(20) NOT NULL UNIQUE,
    company_name        VARCHAR(200),
    sector_schema       VARCHAR(50),
    identified_date     DATE DEFAULT CURRENT_DATE,
    rationale           TEXT,
    entry_price_target  DECIMAL(12,4),
    trigger_alert_price DECIMAL(12,4),
    current_price       DECIMAL(12,4),
    gap_to_entry        DECIMAL(8,4),
    scout_brief         TEXT,
    status              VARCHAR(20) DEFAULT 'watching',
    last_checked        TIMESTAMP,
    promoted_to_position_id UUID REFERENCES positions(id)
);

-- ANALYST ACTIONS
CREATE TABLE analyst_actions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analyst_firm        VARCHAR(100) NOT NULL,
    ticker              VARCHAR(20) NOT NULL,
    action_date         DATE NOT NULL,
    action_type         VARCHAR(20),
    from_recommendation VARCHAR(20),
    to_recommendation   VARCHAR(20),
    from_target         DECIMAL(10,2),
    to_target           DECIMAL(10,2),
    stock_price_at_action DECIMAL(10,2),
    stock_price_30d_after DECIMAL(10,2),
    stock_price_90d_after DECIMAL(10,2),
    verdict             VARCHAR(20),
    timing_quality      VARCHAR(10),
    notes               TEXT
);

CREATE VIEW analyst_track_records AS
SELECT analyst_firm, ticker, COUNT(*) as total_actions,
    AVG(CASE WHEN verdict = 'lagging' THEN 1.0 ELSE 0.0 END) as lagging_rate,
    AVG(CASE WHEN verdict IN ('early','contrarian') THEN 1.0 ELSE 0.0 END) as signal_quality_rate,
    COUNT(CASE WHEN verdict = 'contrarian' THEN 1 END) as contrarian_calls
FROM analyst_actions WHERE verdict IS NOT NULL
GROUP BY analyst_firm, ticker;

-- PORTFOLIO SNAPSHOTS
CREATE TABLE portfolio_snapshots (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date       TIMESTAMP DEFAULT NOW(),
    positions_json      JSONB,
    concentration_flags_json JSONB,
    portfolio_metrics_json JSONB
);

-- POST-MORTEMS
CREATE TABLE post_mortems (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id         UUID REFERENCES positions(id),
    exit_date           DATE,
    exit_price          DECIMAL(12,4),
    total_return_pct    DECIMAL(8,4),
    holding_months      INTEGER,
    thesis_accuracy_json JSONB,
    lessons_json        JSONB,
    pattern_tags        VARCHAR(100)[],
    created_at          TIMESTAMP DEFAULT NOW()
);

-- PATTERN LIBRARY
CREATE TABLE pattern_library (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_key         VARCHAR(100) UNIQUE NOT NULL,
    sector              VARCHAR(50),
    pattern_type        VARCHAR(50),
    description         TEXT,
    evidence_position_ids UUID[],
    confidence_score    DECIMAL(3,2),
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- BUDGET TRACKER
CREATE TABLE dust_budget (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    month               VARCHAR(7) NOT NULL UNIQUE,
    spent_usd           DECIMAL(8,4) DEFAULT 0,
    budget_usd          DECIMAL(8,4) DEFAULT 5.0,
    alert_sent          BOOLEAN DEFAULT FALSE,
    last_updated        TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX idx_positions_ticker ON positions(ticker);
CREATE INDEX idx_reviews_position_date ON reviews(position_id, review_date);
CREATE INDEX idx_calendar_date ON calendar_events(event_date, processed);
CREATE INDEX idx_sector_pulses_position ON sector_pulses(main_position_id, pulse_date);
```

---

## 4. MODULE M1 — COLLECTEUR QUANTITATIF

### backend/app/data_collection/m1_quantitative.py

```python
import yfinance as yf
import requests
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"

TICKER_EXCHANGE_MAP = {
    "CAP": "CAP.PA", "MC": "MC.PA", "AIR": "AIR.PA",
    "SAN": "SAN.PA", "OR": "OR.PA", "BNP": "BNP.PA",
    "ACN": "ACN", "CTSH": "CTSH", "TCS": "TCS",
    "INFY": "INFY", "HCLTECH": "HCLTECH.NS", "WIT": "WIT",
}

def get_yfinance_ticker(ticker: str) -> str:
    return TICKER_EXCHANGE_MAP.get(ticker, ticker)

def get_fmp_data(endpoint: str, api_key: str, params: dict = {}) -> dict:
    params["apikey"] = api_key
    resp = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def collect_quantitative(ticker: str, fmp_api_key: str, base_currency: str = "EUR") -> dict:
    yf_ticker = get_yfinance_ticker(ticker)
    stock = yf.Ticker(yf_ticker)
    info = stock.info or {}

    price_data = {
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency", "USD"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }

    if price_data["current_price"] and price_data["52w_high"]:
        price_data["distance_from_52w_high_pct"] = round(
            (price_data["current_price"] / price_data["52w_high"] - 1) * 100, 2
        )

    hist = stock.history(period="1y")
    if not hist.empty:
        price_data["ytd_change_pct"] = _calc_ytd_change(hist)
        price_data["1m_change_pct"] = _calc_period_change(hist, 21)
        price_data["3m_change_pct"] = _calc_period_change(hist, 63)
        price_data["6m_change_pct"] = _calc_period_change(hist, 126)
        price_data["1y_change_pct"] = _calc_period_change(hist, 252)

    valuation = {
        "pe_ntm": info.get("forwardPE"),
        "pe_ttm": info.get("trailingPE"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ev_revenue": info.get("enterpriseToRevenue"),
        "price_to_book": info.get("priceToBook"),
        "fcf_yield_pct": None,
    }

    financials = {}
    try:
        fin = stock.financials
        cf = stock.cashflow
        if not fin.empty:
            for i, col in enumerate(fin.columns[:3]):
                year = str(col.year)
                financials[year] = {
                    "revenue": _safe_float(fin, "Total Revenue", i),
                    "operating_income": _safe_float(fin, "Operating Income", i),
                    "net_income": _safe_float(fin, "Net Income", i),
                }
        if not cf.empty:
            for i, col in enumerate(cf.columns[:3]):
                year = str(col.year)
                if year in financials:
                    fcf_val = _safe_float(cf, "Free Cash Flow", i)
                    financials[year]["fcf"] = fcf_val
                    if fcf_val and price_data.get("market_cap"):
                        valuation["fcf_yield_pct"] = round(
                            (fcf_val / price_data["market_cap"]) * 100, 2
                        )
    except Exception as e:
        logger.warning(f"Financials error for {ticker}: {e}")

    eps_estimates = {}
    try:
        fmp_est = get_fmp_data(
            f"analyst-estimates/{yf_ticker}", fmp_api_key,
            {"period": "annual", "limit": 3}
        )
        for item in (fmp_est or [])[:3]:
            eps_estimates[item.get("date", "")[:4]] = {
                "eps_avg": item.get("estimatedEpsAvg"),
                "revenue_avg": item.get("estimatedRevenueAvg"),
            }
    except Exception as e:
        logger.warning(f"FMP estimates error for {ticker}: {e}")

    return {
        "ticker": ticker,
        "yf_ticker": yf_ticker,
        "collected_at": datetime.utcnow().isoformat(),
        "price": price_data,
        "valuation": valuation,
        "financials_3y": financials,
        "dividend": {
            "annual_dividend": info.get("dividendRate"),
            "dividend_yield_pct": round((info.get("dividendYield") or 0) * 100, 2),
            "payout_ratio": info.get("payoutRatio"),
        },
        "eps_estimates": eps_estimates,
    }

def collect_peers_quantitative(tickers: list, fmp_api_key: str) -> dict:
    result = {}
    for t in tickers:
        try:
            result[t] = collect_quantitative(t, fmp_api_key)
        except Exception as e:
            result[t] = {"error": str(e)}
    return result

def _safe_float(df, row_name: str, col_idx: int) -> Optional[float]:
    try:
        val = df.loc[row_name].iloc[col_idx]
        return float(val) if val is not None else None
    except Exception:
        return None

def _calc_period_change(hist, days: int) -> Optional[float]:
    if len(hist) < days:
        return None
    return round((hist["Close"].iloc[-1] / hist["Close"].iloc[-days] - 1) * 100, 2)

def _calc_ytd_change(hist) -> Optional[float]:
    ytd = hist[hist.index.year == datetime.now().year]
    if ytd.empty:
        return None
    return round((ytd["Close"].iloc[-1] / ytd["Close"].iloc[0] - 1) * 100, 2)
```

---

## 5. MODULE M2 — COLLECTEUR ÉVÉNEMENTIEL

### backend/app/data_collection/m2_events.py

```python
import feedparser
import requests
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

IR_FEEDS = {
    "CAP":  "https://www.capgemini.com/fr-fr/feed/",
    "ACN":  "https://newsroom.accenture.com/rss/",
    "CTSH": "https://ir.cognizant.com/rss/",
    "TCS":  "https://www.tcs.com/rss/press-release",
    "INFY": "https://www.infosys.com/newsroom/rss.xml",
}

MATERIAL_KEYWORDS_NEGATIVE = [
    "profit warning", "avertissement sur résultats", "below expectations",
    "revises guidance downward", "fraud", "investigation",
    "downgrade", "dégradation", "underweight",
]
MATERIAL_KEYWORDS_POSITIVE = [
    "raises guidance", "relève ses objectifs", "above expectations",
    "record", "acquisition", "strategic partnership", "upgrade", "outperform",
]

def get_earnings_calendar(ticker: str) -> dict:
    try:
        from app.data_collection.m1_quantitative import get_yfinance_ticker
        stock = yf.Ticker(get_yfinance_ticker(ticker))
        cal = stock.calendar
        if cal is not None and not cal.empty:
            dates = cal.get("Earnings Date", [])
            if dates:
                next_date = dates[0]
                return {
                    "ticker": ticker,
                    "next_earnings_date": str(next_date.date()),
                    "trigger_brief_date": str((next_date - timedelta(days=2)).date()),
                    "trigger_review_date": str((next_date + timedelta(days=1)).date()),
                    "source": "yfinance",
                }
    except Exception as e:
        logger.warning(f"Earnings calendar error for {ticker}: {e}")
    return {"ticker": ticker, "next_earnings_date": None, "source": "manual_required"}

def get_google_news_rss(company_name: str, ticker: str, max_items: int = 15) -> list:
    articles = []
    for query in [f"{company_name} results earnings guidance",
                  f"{company_name} acquisition downgrade upgrade"]:
        url = (f"https://news.google.com/rss/search"
               f"?q={requests.utils.quote(query)}&hl=fr&gl=FR&ceid=FR:fr")
        try:
            for entry in feedparser.parse(url).entries[:max_items]:
                score, direction = _score_materiality(
                    entry.get("title", ""), entry.get("summary", "")
                )
                if score > 0:
                    articles.append({
                        "title": entry.get("title"),
                        "link": entry.get("link"),
                        "published": entry.get("published"),
                        "materiality_score": score,
                        "direction": direction,
                    })
        except Exception as e:
            logger.warning(f"RSS error: {e}")
    seen, unique = set(), []
    for a in sorted(articles, key=lambda x: x["materiality_score"], reverse=True):
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    return unique

def get_ir_feed(ticker: str, max_items: int = 10) -> list:
    feed_url = IR_FEEDS.get(ticker)
    if not feed_url:
        return []
    try:
        return [{"title": e.get("title"), "link": e.get("link"),
                 "published": e.get("published"), "source": "ir_official"}
                for e in feedparser.parse(feed_url).entries[:max_items]]
    except Exception:
        return []

def _score_materiality(title: str, summary: str) -> tuple:
    text = f"{title} {summary}".lower()
    score, direction = 0, "neutral"
    for kw in MATERIAL_KEYWORDS_NEGATIVE:
        if kw in text:
            score += 1; direction = "negative"
    for kw in MATERIAL_KEYWORDS_POSITIVE:
        if kw in text:
            score += 1
            if direction == "neutral": direction = "positive"
    return min(score, 3), direction

def collect_m2(ticker: str, company_name: str) -> dict:
    return {
        "ticker": ticker,
        "collected_at": datetime.utcnow().isoformat(),
        "earnings_calendar": get_earnings_calendar(ticker),
        "ir_feed": get_ir_feed(ticker),
        "news": get_google_news_rss(company_name, ticker),
    }
```

---

## 6. MODULE M3 — COLLECTEUR QUALITATIF

### backend/app/data_collection/m3_qualitative.py

```python
import json, logging
logger = logging.getLogger(__name__)

QUERY_TEMPLATES = {
    "post_earnings": [
        "{company} Q{quarter} {year} results revenue organic growth",
        "{company} {year} guidance outlook management CEO comments",
        "{company} analyst rating target price {month} {year}",
        "{company} {peer1} IT services sector comparison {quarter} {year}",
    ],
    "post_cmd": [
        "{company} capital markets day {year} targets guidance",
        "{company} medium term plan {year} organic growth margin",
    ],
    "ma_announcement": [
        "{company} acquisition {target} strategic rationale {year}",
        "{company} {target} synergies integration timeline",
    ],
}

M3_PROMPT = """Tu es un extracteur de données financières.
Pour chaque requête, effectue la recherche web et extrait UNIQUEMENT
les faits chiffrés et citations directes. Ne synthétise pas.

Format JSON UNIQUEMENT :
{"results": [{"query":"...","source_url":"...","publication_date":"YYYY-MM-DD",
"extracted_facts":[{"type":"number|quote|guidance","content":"...","context":"..."}]}]}"""

async def collect_m3(ticker: str, company_name: str, event_type: str,
                     context: dict, dust_client) -> dict:
    template = QUERY_TEMPLATES.get(event_type, QUERY_TEMPLATES["post_earnings"])
    queries = []
    for q in template:
        try:
            queries.append(q.format(company=company_name, ticker=ticker, **context))
        except KeyError as e:
            queries.append(q.replace("{" + str(e).strip("'") + "}", ""))

    from app.config import settings
    result = await dust_client.run_agent(
        agent_id=settings.DUST_PORTFOLIO_AGENT_ID,
        message=f"Société : {company_name} ({ticker})\nÉvénement : {event_type}\n\n"
                f"Requêtes :\n" + "\n".join(f"- {q}" for q in queries) + f"\n\n{M3_PROMPT}",
        model_override="gemini-2-5-flash-preview",
        temperature=0.1,
    )
    try:
        return json.loads(result["content"])
    except json.JSONDecodeError:
        return {"results": [], "error": "parse_error"}
```

---

## 7. ASSEMBLEUR — DATA BRIEF

### backend/app/data_collection/assembler.py

```python
from datetime import datetime
from typing import Optional

def assemble_data_brief(ticker: str, m1_data: dict, m2_data: dict,
                        m3_data: Optional[dict], thesis_data: Optional[dict],
                        sector_pulses_accumulated: Optional[list],
                        peers_m1_data: Optional[dict]) -> dict:

    brief = {
        "ticker": ticker,
        "brief_date": datetime.utcnow().isoformat(),
        "quantitative": {
            "price": m1_data.get("price", {}),
            "valuation": m1_data.get("valuation", {}),
            "financials_3y": m1_data.get("financials_3y", {}),
            "dividend": m1_data.get("dividend", {}),
            "eps_estimates": m1_data.get("eps_estimates", {}),
        },
        "events": {
            "earnings_calendar": m2_data.get("earnings_calendar", {}),
            "recent_ir_news": m2_data.get("ir_feed", [])[:5],
            "material_news": [n for n in m2_data.get("news", [])
                              if n.get("materiality_score", 0) >= 2][:8],
        },
    }

    if m3_data:
        brief["qualitative"] = m3_data

    if peers_m1_data:
        brief["peers_snapshot"] = {
            t: {"pe_ntm": d.get("valuation", {}).get("pe_ntm"),
                "fcf_yield_pct": d.get("valuation", {}).get("fcf_yield_pct"),
                "ytd_change_pct": d.get("price", {}).get("ytd_change_pct")}
            for t, d in peers_m1_data.items() if "error" not in d
        }

    if sector_pulses_accumulated:
        brief["accumulated_sector_pulses"] = sector_pulses_accumulated
        scores = [p.get("pulse_score", 0) for p in sector_pulses_accumulated
                  if p.get("pulse_score")]
        brief["sector_momentum_score"] = round(sum(scores)/len(scores), 1) if scores else 0.0

    if thesis_data:
        cp = m1_data.get("price", {}).get("current_price")
        ep = thesis_data.get("entry_price")
        brief["active_thesis"] = {
            "thesis_one_liner": thesis_data.get("thesis_one_liner"),
            "hypotheses": thesis_data.get("hypotheses", []),
            "last_recommendation": thesis_data.get("last_recommendation"),
            "entry_price": ep,
            "current_return_pct": round((cp/ep-1)*100, 2) if ep and cp else None,
        }

    return brief
```

---

## 8. CLIENT DUST API

### backend/app/agents/dust_client.py

```python
import asyncio, httpx, logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
DUST_API_BASE = "https://dust.tt/api/v1"

MODEL_COSTS = {
    "claude-sonnet-4-5":        {"input": 0.0039,   "output": 0.0195},
    "gemini-2-5-flash-preview": {"input": 0.000195, "output": 0.00078},
    "gpt-4o-mini":              {"input": 0.000195, "output": 0.00078},
}

class DustBudgetExceededError(Exception):
    pass

class DustClient:
    def __init__(self):
        from app.config import settings
        self.api_key = settings.DUST_API_KEY
        self.workspace_id = settings.DUST_WORKSPACE_ID
        self.headers = {"Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"}

    async def check_budget(self):
        from app.db.database import get_db_session
        month = datetime.utcnow().strftime("%Y-%m")
        async with get_db_session() as db:
            result = await db.fetchrow(
                "SELECT spent_usd, budget_usd FROM dust_budget WHERE month = $1", month
            )
            if result and float(result["spent_usd"]) >= float(result["budget_usd"]):
                raise DustBudgetExceededError(
                    f"Budget épuisé : ${result['spent_usd']:.2f}/${result['budget_usd']:.2f}"
                )

    async def track_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        from app.db.database import get_db_session
        from app.notifications.slack_notifier import SlackNotifier
        costs = MODEL_COSTS.get(model, {"input": 0.004, "output": 0.020})
        cost = tokens_in * costs["input"] / 1000 + tokens_out * costs["output"] / 1000
        month = datetime.utcnow().strftime("%Y-%m")
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO dust_budget (month, spent_usd, budget_usd)
                VALUES ($1, $2, 5.0)
                ON CONFLICT (month) DO UPDATE
                SET spent_usd = dust_budget.spent_usd + $2, last_updated = NOW()
            """, month, cost)
            r = await db.fetchrow(
                "SELECT spent_usd, budget_usd, alert_sent FROM dust_budget WHERE month=$1", month
            )
            if r and float(r["spent_usd"])/float(r["budget_usd"]) >= 0.8 and not r["alert_sent"]:
                await SlackNotifier().send_budget_alert(float(r["spent_usd"]), float(r["budget_usd"]))
                await db.execute("UPDATE dust_budget SET alert_sent=TRUE WHERE month=$1", month)
        return cost

    async def run_agent(self, agent_id: str, message: str,
                        model_override: Optional[str] = None,
                        temperature: float = 0.3, timeout: int = 120) -> dict:
        await self.check_budget()
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. Créer conversation
            r = await client.post(
                f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations",
                headers=self.headers,
                json={"visibility": "unlisted",
                      "title": f"portfolio-{datetime.utcnow().isoformat()}"},
            )
            r.raise_for_status()
            conv_id = r.json()["conversation"]["sId"]

            # 2. Poster message
            r2 = await client.post(
                f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}/messages",
                headers=self.headers,
                json={"content": message,
                      "mentions": [{"configurationId": agent_id}],
                      "context": {"timezone": "Europe/Paris", "username": "portfolio-tracker",
                                  "fullName": "Portfolio Tracker", "email": "bot@portfolio",
                                  "profilePictureUrl": None}},
            )
            r2.raise_for_status()

            # 3. Polling
            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < timeout:
                await asyncio.sleep(2)
                resp = await client.get(
                    f"{DUST_API_BASE}/w/{self.workspace_id}/assistant/conversations/{conv_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                for group in reversed(resp.json().get("conversation", {}).get("content", [])):
                    for msg in group:
                        if msg.get("type") == "agent_message":
                            if msg.get("status") == "succeeded":
                                content = "".join(
                                    b.get("value", "") for b in msg.get("content", [])
                                    if b.get("type") == "text"
                                )
                                ti = msg.get("usage", {}).get("promptTokens", 0)
                                to = msg.get("usage", {}).get("completionTokens", 0)
                                m = model_override or "claude-sonnet-4-5"
                                cost = await self.track_cost(m, ti, to)
                                return {"content": content, "tokens_input": ti,
                                        "tokens_output": to, "cost_usd": cost}
                            elif msg.get("status") == "failed":
                                raise Exception(f"Agent failed: {msg.get('error')}")
            raise TimeoutError(f"Timeout after {timeout}s")
```

---

## 9. CONFIGURATION

### backend/app/config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DUST_API_KEY: str
    DUST_WORKSPACE_ID: str = "plm-siege"
    DUST_RESEARCH_AGENT_ID: str
    DUST_PORTFOLIO_AGENT_ID: str
    DUST_MONTHLY_BUDGET_USD: float = 5.0
    DATABASE_URL: str
    # postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
    REDIS_URL: str = "redis://shared-redis:6379"
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str
    SLACK_PORTFOLIO_CHANNEL_ID: str
    FMP_API_KEY: str
    BASE_CURRENCY: str = "EUR"
    MAX_SECTOR_CONCENTRATION_PCT: float = 20.0
    PULSE_ESCALATION_THRESHOLD: int = -3

    class Config:
        env_file = None  # Coolify injecte les variables

settings = Settings()
```

---

## 10. FASTAPI MAIN + SCHEDULER

### backend/app/main.py

```python
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
app = FastAPI(title="Portfolio Tracker", version="1.0.0")
scheduler = AsyncIOScheduler(timezone="Europe/Paris")

@app.on_event("startup")
async def startup():
    scheduler.add_job(_daily_check,
        CronTrigger(hour=7, minute=0, timezone="Europe/Paris"),
        id="daily_check", replace_existing=True)
    scheduler.add_job(_weekly_review,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Europe/Paris"),
        id="weekly_review", replace_existing=True)
    scheduler.start()
    logger.info("Portfolio Tracker démarré")

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()

async def _daily_check():
    from app.calendar.event_router import EventRouter
    await EventRouter().process_daily_events()

async def _weekly_review():
    from app.portfolio.portfolio_view import PortfolioView
    from app.notifications.slack_notifier import SlackNotifier
    snapshot = await PortfolioView().generate_snapshot()
    await SlackNotifier().send_weekly_digest(snapshot)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

*Suite dans PART2 : Agents Dust (Régimes 1/2/3), Sector Pulse, Slack, Docker, Guide démarrage, Bootstrap Capgemini*
