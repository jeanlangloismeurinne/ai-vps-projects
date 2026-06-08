-- Migration 016 — Devise native du prix d'achat sur portfolio_positions
-- Le prix d'achat est désormais stocké dans la devise native du ticker (USD pour NVDA, etc.)
-- purchase_currency = code devise (USD, EUR, GBP…)
-- Les positions existantes gardent leur valeur avec purchase_currency = 'EUR' (comportement d'avant)

ALTER TABLE portfolio_positions
    ADD COLUMN IF NOT EXISTS purchase_currency TEXT NOT NULL DEFAULT 'EUR';
