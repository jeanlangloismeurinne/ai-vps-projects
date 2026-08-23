-- Migration 024 — V2 Knowledge Platform (Lot 1, socle couche 3)
--
-- Fondation données de l'Architecture V2 (spec 01-spec-v2-unifiee.md §14, §18-1).
-- Matérialise la couche 3 « pure » : knowledge_documents + knowledge_entries VERSIONNÉES
-- (append-only, A1), table de jointure snapshot figé analysis_knowledge_refs (A1/A2),
-- eu_ir_scrapers, knowledge_curator_reports (mvdd|readiness|lint — remplace l'ex-`screenings`),
-- extension pgvector (DÉCISION #4), et la vue d'export « enveloppe document commune »
-- (KNOWLEDGE_ARCHITECTURE.md §3, contrainte federation-ready du projet de référence).
--
-- COLLISION 023 RÉSOLUE : le nom `023_v2_knowledge_platform.sql` de la spec §14 était pris
-- par `023_purchase_price_eur.sql` (déjà appliqué). Toute la séquence V2 décale de +1 :
--   024 = knowledge platform (ce fichier) · 025 = agents/provider · 026 = investment_analyses
--   + research_memos · 027 = theses_flow · 028 = exit/calibration.
-- Le FK analysis_id de analysis_knowledge_refs pointe vers investment_analyses (migration 026,
-- non encore créée) : laissé en INT nu ici (forward-reference documentée), contraint plus tard.
--
-- Rappels DB projet : asyncpg $1 (pas %s) ; JSONB auto-décodé (pas de json.dumps) ;
-- migrations appliquées MANUELLEMENT via `docker cp` + `psql -f` (pas d'auto-run au startup) ;
-- ALTER DEFAULT PRIVILEGES rend les tables créées par `admin` accessibles à portfolio_user.

-- ── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector 0.8.2 (embeddings)
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- digest() pour le content_hash de la vue federation

-- ── 1. knowledge_documents — documents bruts avant extraction ────────────────
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id                  SERIAL PRIMARY KEY,
    ticker_id           TEXT REFERENCES tickers(id),
    doc_type            TEXT NOT NULL,   -- '10-K'|'10-Q'|'8-K'|'earnings_call'|'annual_report'
                                         -- |'press_release'|'investor_day'|'news'|'investor_update'
    title               TEXT,
    source_url          TEXT,
    source_type         TEXT NOT NULL,   -- 'edgar'|'ir_scrape'|'web_search'|'user_upload'|'rss'
    content_raw         TEXT,            -- texte extrait (peut être long)
    content_hash        TEXT,            -- SHA256 pour déduplication
    published_date      DATE,
    fiscal_period       TEXT,            -- 'Q4-2025'|'FY-2025'
    is_confidential     BOOL NOT NULL DEFAULT FALSE,
    language            TEXT DEFAULT 'en',
    processing_status   TEXT DEFAULT 'pending',  -- 'pending'|'processing'|'done'|'failed'
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. knowledge_entries — entrées atomiques VERSIONNÉES / append-only (A1) ───
-- On ne MUTE jamais une entrée : on crée une nouvelle version (version+1, valid_from) et on
-- marque l'ancienne obsolète via superseded_by. DELETE = soft-delete (is_deleted). L'entrée
-- « courante » d'une lignée est celle dont superseded_by IS NULL AND NOT is_deleted.
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id                    SERIAL PRIMARY KEY,
    ticker_id             TEXT REFERENCES tickers(id),          -- null = connaissance sectorielle/macro
    document_id           INT  REFERENCES knowledge_documents(id),  -- null si source directe
    entry_type            TEXT NOT NULL,  -- 'fact_financial'|'fact_qualitative'|'event'|'quote'
                                          -- |'analysis'|'risk'|'llm_memory'|'agent_synthesis'|'lesson_learned'
    title                 TEXT,                                 -- titre court (enveloppe federation)
    content               TEXT NOT NULL,  -- le fait, formulé en Markdown (pivot lisible humain + LLM)
    content_structured    JSONB,          -- version structurée si applicable (ex: {metric, value, period})
    tags                  TEXT[] DEFAULT '{}',
    lang                  TEXT DEFAULT 'en',
    source_type           TEXT NOT NULL,  -- cf. framework fiabilité (roadmap KP §3.3)
    source_url            TEXT,
    source_date           DATE,
    fiscal_period         TEXT,           -- période couverte par cette information
    reliability_score     FLOAT NOT NULL CHECK (reliability_score BETWEEN 0.0 AND 1.0),
    reliability_tier      TEXT  NOT NULL CHECK (reliability_tier IN ('A','A-','B+','B','B-','C+','C')),
    reliability_note      TEXT,           -- pourquoi ce score
    has_conflict          BOOL DEFAULT FALSE,               -- une autre source dit le contraire (A9)
    conflict_entry_id     INT REFERENCES knowledge_entries(id),
    requires_human_review BOOL DEFAULT FALSE,               -- llm_memory etc. (P2)
    reviewed_by_user      BOOL DEFAULT FALSE,
    last_reviewed_at      TIMESTAMPTZ,
    model_cutoff          TEXT,           -- ex: '2026-01' pour les llm_memory
    -- Versionnement append-only (A1) ------------------------------------------
    version               INT  NOT NULL DEFAULT 1,
    valid_from            TIMESTAMPTZ DEFAULT NOW(),
    superseded_by         INT REFERENCES knowledge_entries(id),  -- NULL = version courante
    -- Questions ouvertes (curator : une lacune peut vivre comme entrée) --------
    question_status       TEXT,           -- 'open'|'researching'|'resolved'|'unresolvable'
    question_priority     INT,            -- 1 = haute … (null si pas une question)
    resolves_entry_id     INT REFERENCES knowledge_entries(id),  -- entrée-réponse -> question résolue
    -- Cycle de vie -------------------------------------------------------------
    embedding             vector(768),    -- calculé hors migration (nomic-embed-text / Ollama, dim 768)
    is_outdated           BOOL DEFAULT FALSE,   -- remplacé par plus récent (redondant avec superseded_by)
    is_deleted            BOOL DEFAULT FALSE,   -- soft-delete (A1 : jamais de DELETE dur)
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_entries_ticker  ON knowledge_entries(ticker_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_type    ON knowledge_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_review  ON knowledge_entries(requires_human_review) WHERE requires_human_review = TRUE;
-- entrées « courantes » (chemin chaud RAG / readiness / groundedness)
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_current ON knowledge_entries(ticker_id, entry_type) WHERE superseded_by IS NULL AND is_deleted = FALSE;
-- questions ouvertes du curator
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_open_q  ON knowledge_entries(ticker_id, question_priority) WHERE question_status = 'open';
-- ANN sémantique : HNSW (pas d'entraînement, idéal pour inserts incrémentaux ; remplace l'ivfflat
-- du roadmap KP qui exige un jeu d'entraînement et un paramètre `lists`).
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_embedding ON knowledge_entries USING hnsw (embedding vector_cosine_ops);

-- ── 3. analysis_knowledge_refs — SNAPSHOT FIGÉ au moment de la décision (A1/A2) ──
-- Remplace tout `INT[] knowledge_entry_ids` mutable : chaque analyse (bull/bear/synthèse, memo,
-- readiness) fige ici la version EXACTE et le CONTENU des entries citées. C'est le P0
-- d'auditabilité : on peut toujours reconstruire « pourquoi l'agent a dit ça ».
-- analysis_id -> investment_analyses(id) (migration 026, forward-reference : INT nu ici).
CREATE TABLE IF NOT EXISTS analysis_knowledge_refs (
    id                  SERIAL PRIMARY KEY,
    analysis_id         INT  NOT NULL,   -- FK ajoutée en 026 (investment_analyses)
    analysis_kind       TEXT NOT NULL DEFAULT 'analysis',  -- 'analysis'|'research_memo'|'readiness'|'grounding'
    entry_id            INT  NOT NULL REFERENCES knowledge_entries(id),
    entry_version       INT  NOT NULL,   -- version figée (A1)
    content_snapshot    TEXT NOT NULL,   -- copie immuable du content au moment de l'usage
    reliability_at_use  FLOAT,           -- reliability_score au moment de l'usage
    field_path          TEXT,            -- champ du JSON qui cite cette entry (groundedness, A2)
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (analysis_id, analysis_kind, entry_id, field_path)
);
CREATE INDEX IF NOT EXISTS idx_analysis_refs_analysis ON analysis_knowledge_refs(analysis_id, analysis_kind);
CREATE INDEX IF NOT EXISTS idx_analysis_refs_entry    ON analysis_knowledge_refs(entry_id);

-- ── 4. eu_ir_scrapers — config & santé des scrapers IR européens ─────────────
CREATE TABLE IF NOT EXISTS eu_ir_scrapers (
    id              SERIAL PRIMARY KEY,
    ticker_id       TEXT REFERENCES tickers(id),
    scraper_url     TEXT NOT NULL,       -- URL de la page IR à scraper
    scraper_config  JSONB,               -- sélecteurs CSS, regex, etc.
    scraper_health  TEXT DEFAULT 'ok',   -- 'ok'|'degraded'|'broken'
    last_success_at TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_eu_ir_scrapers_ticker ON eu_ir_scrapers(ticker_id);

-- ── 5. knowledge_curator_reports — MVDD | Readiness | Lint (ex-`screenings`) ──
-- Un seul artefact pour les 3 modes du curator (§7). Le readiness_report_json vit dans
-- report_json ; verdict = GO/NO-GO (readiness). context_pack_entry_id pointe l'artefact
-- distillé réutilisable (source_type='agent_synthesis') front-loadé par research/bull/bear.
CREATE TABLE IF NOT EXISTS knowledge_curator_reports (
    id                    SERIAL PRIMARY KEY,
    ticker_id             TEXT NOT NULL REFERENCES tickers(id),
    report_type           TEXT NOT NULL CHECK (report_type IN ('mvdd','readiness','lint')),
    report_json           JSONB NOT NULL,
    verdict               TEXT,   -- readiness : 'not_ready'|'researching'|'thin_qualitative'|'ready'|'too_hard'
    coverage_structuree   JSONB,  -- {ok, dimensions:{...}}
    coverage_qualitative  JSONB,
    context_pack_entry_id INT REFERENCES knowledge_entries(id),
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_curator_reports_ticker ON knowledge_curator_reports(ticker_id, report_type, created_at DESC);

-- ── 6. Vue d'export « enveloppe document commune » (federation-ready) ─────────
-- Contrat KNOWLEDGE_ARCHITECTURE.md §3. Le stockage natif reste libre ; cette vue le PROJETTE
-- vers les colonnes normalisées. Le connecteur fédéré la lira en incrémental (updated_at /
-- content_hash). N'exporte que la version courante et non soft-deleted.
CREATE OR REPLACE VIEW knowledge_federation_export AS
SELECT
    'portfolio-tracker:postgres:knowledge_entry/' || e.id                       AS doc_id,
    'portfolio-tracker'                                                          AS project,
    'postgres'                                                                   AS source,
    'https://portfolio.jlmvpscode.duckdns.org/knowledge/entry/' || e.id         AS uri,
    COALESCE(e.title, left(e.content, 80))                                       AS title,
    e.content                                                                    AS body,        -- pivot Markdown
    e.lang                                                                       AS lang,
    e.tags                                                                       AS tags,
    jsonb_build_object('tickers',
        CASE WHEN e.ticker_id IS NULL THEN '[]'::jsonb
             ELSE jsonb_build_array(e.ticker_id) END)                           AS entities,
    e.reliability_score                                                          AS reliability,
    e.reliability_tier                                                           AS reliability_tier,
    'public'                                                                     AS visibility,
    e.created_at                                                                 AS created_at,
    e.updated_at                                                                 AS updated_at,
    now()                                                                        AS ingested_at,
    'sha256:' || encode(digest(e.content, 'sha256'), 'hex')                      AS content_hash,
    jsonb_build_object(
        'source_type',   e.source_type,
        'entry_type',    e.entry_type,
        'entry_version', e.version,
        'fiscal_period', e.fiscal_period,
        'has_conflict',  e.has_conflict
    )                                                                            AS metadata
FROM knowledge_entries e
WHERE e.superseded_by IS NULL   -- version courante uniquement
  AND e.is_deleted = FALSE;

-- Permissions : filet explicite (au cas où ALTER DEFAULT PRIVILEGES ne couvre pas la vue).
GRANT SELECT, INSERT, UPDATE, DELETE ON
    knowledge_documents, knowledge_entries, analysis_knowledge_refs,
    eu_ir_scrapers, knowledge_curator_reports TO portfolio_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO portfolio_user;
GRANT SELECT ON knowledge_federation_export TO portfolio_user;
