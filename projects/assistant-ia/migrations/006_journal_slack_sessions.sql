-- Migration 006 — Ticket #1778099921788 : sessions Slack pour le remplissage du journal

CREATE TABLE IF NOT EXISTS journal_slack_sessions (
    id           SERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL,
    objectif_id  UUID NOT NULL REFERENCES journal_objectifs(id) ON DELETE CASCADE,
    thread_ts    TEXT NOT NULL,
    question_index INTEGER NOT NULL DEFAULT 0,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, objectif_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_jss_thread ON journal_slack_sessions(thread_ts);
