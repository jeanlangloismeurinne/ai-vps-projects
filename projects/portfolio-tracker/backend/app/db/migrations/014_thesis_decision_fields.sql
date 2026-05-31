-- Migration 014 — champs pour le flux décision sur les thèses

ALTER TABLE theses
  ADD COLUMN IF NOT EXISTS decision_delay_used BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS reevaluation_date DATE;
