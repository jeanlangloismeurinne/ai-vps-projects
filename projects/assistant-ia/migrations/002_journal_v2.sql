-- Migration 002 — Journal v2 : parcours de progression, questions structurées

CREATE TABLE IF NOT EXISTS journal_parcours (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nom         VARCHAR(200) NOT NULL,
  description TEXT,
  is_active   BOOLEAN NOT NULL DEFAULT true,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS journal_objectifs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parcours_id  UUID NOT NULL REFERENCES journal_parcours(id) ON DELETE CASCADE,
  nom          VARCHAR(200) NOT NULL,
  description  TEXT,
  is_active    BOOLEAN NOT NULL DEFAULT true,
  frequence    VARCHAR(20) NOT NULL DEFAULT 'daily',
  jours        JSONB NOT NULL DEFAULT '[]',
  heure_rappel TIME NOT NULL DEFAULT '09:00:00',
  sort_order   INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS journal_questions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  objectif_id   UUID NOT NULL REFERENCES journal_objectifs(id) ON DELETE CASCADE,
  texte         TEXT NOT NULL,
  type          VARCHAR(30) NOT NULL,
  config        JSONB NOT NULL DEFAULT '{}',
  is_active     BOOLEAN NOT NULL DEFAULT true,
  deprecated_at TIMESTAMPTZ,
  sort_order    INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS journal_reponses (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id  UUID NOT NULL REFERENCES journal_questions(id) ON DELETE CASCADE,
  objectif_id  UUID NOT NULL REFERENCES journal_objectifs(id) ON DELETE CASCADE,
  valeur       JSONB NOT NULL,
  session_date DATE NOT NULL DEFAULT CURRENT_DATE,
  answered_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS journal_notifications (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  objectif_id  UUID NOT NULL REFERENCES journal_objectifs(id) ON DELETE CASCADE,
  session_date DATE NOT NULL,
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(objectif_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_jr_question ON journal_reponses(question_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_jr_objectif ON journal_reponses(objectif_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_jo_parcours ON journal_objectifs(parcours_id);
CREATE INDEX IF NOT EXISTS idx_jq_objectif ON journal_questions(objectif_id);
