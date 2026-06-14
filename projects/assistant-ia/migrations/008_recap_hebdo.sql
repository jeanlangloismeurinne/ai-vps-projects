-- Migration 008 : récapitulatif hebdomadaire
ALTER TABLE journal_objectifs
  ADD COLUMN IF NOT EXISTS recap_actif  BOOLEAN  DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS recap_jour   SMALLINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS recap_heure  TIME     DEFAULT '08:00:00';

CREATE TABLE IF NOT EXISTS journal_recap_envois (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  objectif_id  UUID        NOT NULL REFERENCES journal_objectifs(id),
  semaine_iso  VARCHAR(8)  NOT NULL,
  sent_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (objectif_id, semaine_iso)
);
