-- Suivi NASDAQ (spec du 2026-10-26), indépendant du reste du portfolio-tracker.
-- Appliquée à la main : docker cp f.sql shared-postgres:/tmp/ && docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/f.sql

CREATE TABLE IF NOT EXISTS nasdaq_prices (
    ticker      TEXT PRIMARY KEY,
    first_date  DATE NOT NULL,
    last_date   DATE NOT NULL,
    day_nums    INTEGER[] NOT NULL,           -- jours depuis 1970-01-01, croissants
    closes      DOUBLE PRECISION[] NOT NULL,  -- clôtures ajustées splits+dividendes, alignées sur day_nums
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nasdaq_runs (
    id          BIGSERIAL PRIMARY KEY,
    run_date    DATE NOT NULL,                -- dernière séance US couverte (ou date du jour si échec)
    status      TEXT NOT NULL,                -- ok | degraded | failed
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    n_universe  INTEGER,
    n_priced    INTEGER,
    n_shown     INTEGER,
    warning     TEXT,
    log         TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS nasdaq_runs_date ON nasdaq_runs (run_date, id);

CREATE TABLE IF NOT EXISTS nasdaq_indicators (
    run_date      DATE NOT NULL,
    ticker        TEXT NOT NULL,
    name          TEXT NOT NULL,
    price         DOUBLE PRECISION NOT NULL,
    age_months    INTEGER,                    -- NULL si ATL
    is_atl        BOOLEAN NOT NULL DEFAULT FALSE,
    is_ath        BOOLEAN NOT NULL DEFAULT FALSE,
    multiple_10y  DOUBLE PRECISION,
    lt_10y        BOOLEAN NOT NULL DEFAULT FALSE,
    short_history BOOLEAN NOT NULL DEFAULT FALSE,
    market_cap    DOUBLE PRECISION,           -- NULL si indisponible
    alert         BOOLEAN NOT NULL DEFAULT FALSE,
    alert_new     BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (run_date, ticker)
);
CREATE INDEX IF NOT EXISTS nasdaq_indicators_ticker ON nasdaq_indicators (ticker, run_date);
