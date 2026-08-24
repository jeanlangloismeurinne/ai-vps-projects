-- 009_journal_kb.sql
-- Index requêtable de la KB journal (enveloppe document commune).
-- Markdown reste le pivot ; Postgres est l'index dérivé.
-- Idempotent : CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS journal_kb_entries (
    doc_id          text PRIMARY KEY,                          -- assistant-ia:vps_files:journal/<slug>
    project         text NOT NULL DEFAULT 'assistant-ia',
    source          text NOT NULL DEFAULT 'vps_files',
    uri             text NOT NULL,                             -- chemin canonique du .md dans le vault
    title           text,                                      -- généré par le classifieur
    body            text NOT NULL,                             -- verbatim Markdown
    contexte        text,                                      -- axe fixe : personnel / professionnel (0..1)
    nature          text[],                                    -- axe fixe : idee / apprentissage / … (0..n)
    tags            text[] NOT NULL DEFAULT '{}',             -- tags libres
    visibility      text NOT NULL DEFAULT 'private',           -- journal personnel
    content_hash    text NOT NULL,                             -- hash du body — dédup + sync incrémentale
    slack_ts        text,                                      -- message d'origine (traçabilité)
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Déduplication et sync incrémentale
CREATE INDEX IF NOT EXISTS journal_kb_entries_content_hash_idx
    ON journal_kb_entries (content_hash);

-- Recherche par tags (tableau)
CREATE INDEX IF NOT EXISTS journal_kb_entries_tags_idx
    ON journal_kb_entries USING GIN (tags);

-- Tri chronologique
CREATE INDEX IF NOT EXISTS journal_kb_entries_created_at_idx
    ON journal_kb_entries (created_at DESC);

-- Filtrage par axe contexte (mono-valeur)
CREATE INDEX IF NOT EXISTS journal_kb_entries_contexte_idx
    ON journal_kb_entries (contexte);

-- Filtrage par axe nature (multi-valeur → GIN, comme tags)
CREATE INDEX IF NOT EXISTS journal_kb_entries_nature_idx
    ON journal_kb_entries USING GIN (nature);
