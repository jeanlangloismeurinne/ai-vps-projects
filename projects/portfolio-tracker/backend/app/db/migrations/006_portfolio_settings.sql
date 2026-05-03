CREATE TABLE IF NOT EXISTS portfolio_settings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_capital_eur   DECIMAL(14,2) NOT NULL DEFAULT 0,
    cash_balance_eur    DECIMAL(14,2) NOT NULL DEFAULT 0,
    updated_at          TIMESTAMP DEFAULT NOW()
);
INSERT INTO portfolio_settings (total_capital_eur, cash_balance_eur)
VALUES (0, 0) ON CONFLICT DO NOTHING;
