-- Migration 007 : heure de relance configurable, multi-réponses, entry_index
ALTER TABLE journal_objectifs
  ADD COLUMN IF NOT EXISTS heure_relance TIME DEFAULT NULL;

ALTER TABLE journal_questions
  ADD COLUMN IF NOT EXISTS multi_reponses BOOLEAN DEFAULT FALSE;

ALTER TABLE journal_reponses
  DROP CONSTRAINT IF EXISTS journal_reponses_question_id_objectif_id_session_date_key;

ALTER TABLE journal_reponses
  ADD COLUMN IF NOT EXISTS entry_index SMALLINT DEFAULT 0;

UPDATE journal_reponses SET entry_index = 0 WHERE entry_index IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS journal_reponses_unique
  ON journal_reponses (question_id, objectif_id, session_date, entry_index);
