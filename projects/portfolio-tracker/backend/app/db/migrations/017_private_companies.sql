-- Migration 017 — Support sociétés non côtées (PE/VC)

-- 1. Ajouter company_type sur tickers
ALTER TABLE tickers
    ADD COLUMN IF NOT EXISTS company_type TEXT NOT NULL DEFAULT 'public';
-- 'public' = coté en bourse, 'private' = non coté

-- 2. Table profil private companies
CREATE TABLE IF NOT EXISTS private_company_profiles (
    ticker_id               TEXT PRIMARY KEY REFERENCES tickers(id) ON DELETE CASCADE,
    stage                   TEXT,  -- 'pre-seed'|'seed'|'series-a'|'series-b'|'series-c'|'growth'|'pre-ipo'|'mature'
    country                 TEXT DEFAULT 'FR',
    last_valuation_m        NUMERIC(15,2),
    last_valuation_date     DATE,
    last_valuation_basis    TEXT,  -- 'funding_round'|'revenue_multiple'|'transaction_comparable'|'book_value'|'manual'
    arr_or_revenue_m        NUMERIC(15,2),
    ebitda_m                NUMERIC(15,2),
    key_metrics_json        JSONB DEFAULT '{}',
    notable_investors       TEXT[] DEFAULT '{}',
    projected_valuation_next_event_m NUMERIC(15,2),
    next_event_date         DATE,
    next_event_type         TEXT,  -- 'prochain_tour'|'ipo'|'ma'|'agm'|'milestone'
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- 3. Ownership tracking on portfolio_positions
ALTER TABLE portfolio_positions
    ADD COLUMN IF NOT EXISTS ownership_pct_at_entry NUMERIC(10,6),
    ADD COLUMN IF NOT EXISTS current_ownership_pct  NUMERIC(10,6);
