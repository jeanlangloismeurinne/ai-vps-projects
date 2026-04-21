-- F6: User-defined classification rules (keyword → category).
-- Keyword matching is case-insensitive partial match (ILIKE '%keyword%').

CREATE TABLE IF NOT EXISTS classification_rules (
    id         SERIAL PRIMARY KEY,
    keyword    TEXT NOT NULL,
    category   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_keyword_lower ON classification_rules (lower(keyword));
