-- Migration 018 : séparation id interne / symbole boursier
-- ticker_symbol = symbole yfinance (ex. "CAP.PA", "MSFT") — nullable pour les sociétés ajoutées par nom seul
-- id reste la PK stable (peut être PUB-XXXXXXXX pour les cotées ajoutées sans symbole)

ALTER TABLE tickers ADD COLUMN IF NOT EXISTS ticker_symbol TEXT;

-- Backfill : les tickers existants (non-PRIV-) ont leur id comme symbole boursier
UPDATE tickers SET ticker_symbol = id WHERE id NOT LIKE 'PRIV-%' AND ticker_symbol IS NULL;
