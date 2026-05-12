-- Snapshots M1 capturés aux moments clés (régimes, hebdomadaire, warmup)
CREATE TABLE IF NOT EXISTS market_snapshots (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker       TEXT NOT NULL,
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    context      TEXT NOT NULL,  -- 'regime1' | 'regime2' | 'regime3' | 'weekly' | 'warmup' | 'api'
    raw_json     JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_ticker_date
    ON market_snapshots(ticker, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_context
    ON market_snapshots(ticker, context, captured_at DESC);

-- Cache persistant des dates earnings (survit aux redémarrages Redis)
CREATE TABLE IF NOT EXISTS earnings_calendar_cache (
    ticker               TEXT PRIMARY KEY,
    next_earnings_date   DATE,
    trigger_brief_date   DATE,
    trigger_review_date  DATE,
    source               TEXT DEFAULT 'yfinance',
    fetched_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
