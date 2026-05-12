-- Élargit current_price pour supporter les actions à prix élevé (ex: NVDA, BRK.A)
-- DECIMAL(12,4) max = 99 999 999 → overflow sur market cap retourné par yfinance
ALTER TABLE watchlist
    ALTER COLUMN current_price TYPE DECIMAL(20,4);
