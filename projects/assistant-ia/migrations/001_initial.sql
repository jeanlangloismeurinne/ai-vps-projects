-- Migration 001 — assistant-ia initial schema
-- Idempotent : safe to run on every startup

-- Feature 1 : Journal d'apprentissage
CREATE TABLE IF NOT EXISTS journal_prompts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slack_ts    VARCHAR(32) UNIQUE NOT NULL,
  prompt_date DATE NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS journal_entries (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content    TEXT NOT NULL,
  slack_ts   VARCHAR(32) UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Feature 2 : Kanban
CREATE TABLE IF NOT EXISTS boards (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       VARCHAR(128) NOT NULL,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS columns (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id   UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  name       VARCHAR(128) NOT NULL,
  position   INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cards (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  column_id        UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
  title            TEXT NOT NULL,
  description      TEXT,
  due_date         TIMESTAMPTZ,
  reminder_sent_at TIMESTAMPTZ,
  position         INTEGER NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS card_fields (
  id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  key     VARCHAR(64) NOT NULL,
  value   TEXT,
  UNIQUE(card_id, key)
);

CREATE TABLE IF NOT EXISTS grouping_configs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id    UUID REFERENCES boards(id) ON DELETE CASCADE,
  name        VARCHAR(128) NOT NULL,
  group_by    VARCHAR(64) NOT NULL,
  group_order JSONB,
  is_active   BOOLEAN DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Feature 3 : Suivi des déploiements (pour les notifications feedback)
CREATE TABLE IF NOT EXISTS service_deploys (
  service        VARCHAR(100) PRIMARY KEY,
  last_deploy_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_journal_entries_created ON journal_entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cards_column ON cards(column_id);
CREATE INDEX IF NOT EXISTS idx_cards_due_date ON cards(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_columns_board ON columns(board_id);
