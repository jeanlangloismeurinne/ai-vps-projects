ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS dust_conversation_id    VARCHAR(50),
    ADD COLUMN IF NOT EXISTS agent_version_research  INTEGER,
    ADD COLUMN IF NOT EXISTS agent_version_portfolio INTEGER,
    ADD COLUMN IF NOT EXISTS data_sources_json       JSONB,
    ADD COLUMN IF NOT EXISTS data_quality_flags      TEXT[];
