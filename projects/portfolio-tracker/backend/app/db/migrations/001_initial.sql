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
