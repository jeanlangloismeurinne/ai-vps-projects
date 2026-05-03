CREATE TABLE IF NOT EXISTS market_indicators (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fetched_at      TIMESTAMP DEFAULT NOW(),
    buffett_ratio   DECIMAL(8,4),
    buffett_trend   VARCHAR(10),
    cape_ratio      DECIMAL(8,4),
    cape_trend      VARCHAR(10),
    temperature     VARCHAR(10),
    cash_target_pct DECIMAL(5,2),
    raw_data_json   JSONB
);
