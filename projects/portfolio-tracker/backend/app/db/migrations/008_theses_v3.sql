ALTER TABLE theses
    ADD COLUMN IF NOT EXISTS dust_conversation_id    VARCHAR(50),
    ADD COLUMN IF NOT EXISTS agent_version_research  INTEGER,
    ADD COLUMN IF NOT EXISTS agent_version_portfolio INTEGER,
    ADD COLUMN IF NOT EXISTS validated_at            TIMESTAMP,
    ADD COLUMN IF NOT EXISTS validated_by            VARCHAR(50) DEFAULT 'user';
