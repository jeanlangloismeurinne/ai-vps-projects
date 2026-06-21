-- Migration 023 — Stockage du PRU en € sur portfolio_positions
-- Le prix de revient unitaire saisi par l'utilisateur (en €, frais inclus) est maintenant
-- conservé séparément du prix en devise native (purchase_price).
-- Permet d'afficher : PRU €, équivalent en devise au cours du jour, cours actuel.

ALTER TABLE portfolio_positions
    ADD COLUMN IF NOT EXISTS purchase_price_eur NUMERIC;

-- Backfill : pour les positions déjà en EUR, le PRU € = prix stocké
UPDATE portfolio_positions
SET purchase_price_eur = purchase_price
WHERE purchase_currency = 'EUR' AND purchase_price_eur IS NULL;
