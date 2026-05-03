CREATE TABLE IF NOT EXISTS portfolio_cash_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_date  TIMESTAMP DEFAULT NOW(),
    operation_type  VARCHAR(30) NOT NULL,
    amount_eur      DECIMAL(14,2) NOT NULL,
    position_id     UUID REFERENCES positions(id),
    watchlist_id    UUID REFERENCES watchlist(id),
    notes           TEXT,
    balance_after   DECIMAL(14,2) NOT NULL
);
