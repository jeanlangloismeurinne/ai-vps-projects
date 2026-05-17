-- Migration 005 — Ticket #1778099799092 : is_required + upsert journal_reponses

-- Colonne is_required : un objectif est complet quand toutes ses questions requises sont répondues
ALTER TABLE journal_questions ADD COLUMN IF NOT EXISTS is_required BOOLEAN NOT NULL DEFAULT true;

-- Dédoublonnage : garde la réponse la plus récente par (question, objectif, date)
WITH latest AS (
    SELECT DISTINCT ON (question_id, objectif_id, session_date) id
    FROM journal_reponses
    ORDER BY question_id, objectif_id, session_date, answered_at DESC
)
DELETE FROM journal_reponses WHERE id NOT IN (SELECT id FROM latest);

-- Index unique pour permettre l'upsert (ON CONFLICT)
CREATE UNIQUE INDEX IF NOT EXISTS uq_jr_q_obj_date
    ON journal_reponses(question_id, objectif_id, session_date);
