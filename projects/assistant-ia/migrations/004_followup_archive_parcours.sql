ALTER TABLE journal_notifications ADD COLUMN IF NOT EXISTS followup_sent_at TIMESTAMPTZ;
ALTER TABLE journal_parcours ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
