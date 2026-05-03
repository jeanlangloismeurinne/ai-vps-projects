ALTER TABLE watchlist
    ADD COLUMN IF NOT EXISTS schema_json_draft      JSONB,
    ADD COLUMN IF NOT EXISTS conviction_signal      VARCHAR(10),
    ADD COLUMN IF NOT EXISTS peer_snapshot_json     JSONB,
    ADD COLUMN IF NOT EXISTS scout_job_id           VARCHAR(50),
    ADD COLUMN IF NOT EXISTS scout_run_at           TIMESTAMP,
    ADD COLUMN IF NOT EXISTS scout_agent_version    INTEGER,
    ADD COLUMN IF NOT EXISTS scout_cost_usd         DECIMAL(8,6),
    ADD COLUMN IF NOT EXISTS dust_conversation_id   VARCHAR(50),
    ADD COLUMN IF NOT EXISTS validated_thesis_json  JSONB,
    ADD COLUMN IF NOT EXISTS validated_at           TIMESTAMP,
    ADD COLUMN IF NOT EXISTS thesis_status          VARCHAR(20) DEFAULT 'draft';
