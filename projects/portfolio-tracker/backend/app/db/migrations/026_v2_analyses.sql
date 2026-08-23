-- Migration 026 — V2 Analyses (Lot 3, couche 2 : sorties d'analyse persistées)
--
-- Spec 01-spec-v2-unifiee.md §14 (y nommée "025_v2_analyses" ; la COLLISION 023 a décalé toute
-- la séquence V2 de +1 → cette migration est la 026). Matérialise le stockage des sorties de la
-- chaîne d'analyse : research_memo (base neutre §8.0), bull/bear (§8.1-8.3), synthèse = risk_matrix
-- + hypotheses[] (§8.4-8.5). Les result_json/memo_json portent EXACTEMENT les contrats Pydantic
-- figés (roadmap/provenance-cards/analysis_v2_schemas.py, SCHEMA_VERSION v2.0.0).
--
-- AUDITABILITÉ (P0) : chaque ligne fige provider_used/model_used/prompt_snapshot + grounding_report
-- (A2) + coût/tokens. Les entries citées sont figées à part dans analysis_knowledge_refs (024, A1/A2)
-- via un snapshot immuable — jamais un INT[] mutable.
--
-- A7 (édition utilisateur tracée) : result_json = état courant (potentiellement édité) ;
-- result_json_original = sortie brute de l'agent, jamais mutée. Idem memo_json / memo_json_original.
--
-- POLYMORPHISME DE analysis_knowledge_refs.analysis_id (amende la note "FK ajoutée en 026" du 024) :
-- la colonne analysis_id est POLYMORPHE, discriminée par analysis_kind
-- ('analysis'|'research_memo'|'readiness'|'grounding') → elle pointe selon le cas vers
-- investment_analyses | research_memos | knowledge_curator_reports. Une FK dure vers une seule table
-- serait donc FAUSSE pour les autres kinds. On garde l'association polymorphe (intégrité validée en
-- applicatif par le service knowledge, qui écrit toujours (analysis_id, analysis_kind) de façon
-- cohérente). On ajoute seulement un CHECK sur le domaine de analysis_kind + un index d'accès.
--
-- Rappels DB projet : asyncpg $1 (pas %s) ; JSONB auto-décodé (pas de json.dumps) ; migration
-- appliquée MANUELLEMENT via `docker cp` + `psql -f` (pas d'auto-run au startup) ;
-- ALTER DEFAULT PRIVILEGES rend la table accessible à portfolio_user (filet GRANT explicite en fin).

-- ── 1. research_memos — base NEUTRE (§8.0, contrat ResearchMemo) ─────────────
CREATE TABLE IF NOT EXISTS research_memos (
    id                    SERIAL PRIMARY KEY,
    ticker_id             TEXT NOT NULL REFERENCES tickers(id),
    schema_version        TEXT NOT NULL DEFAULT 'v2.0.0',
    memo_json             JSONB NOT NULL,          -- ResearchMemo (état courant, A7)
    memo_json_original    JSONB NOT NULL,          -- sortie brute de l'agent, jamais mutée (A7)
    -- provenance de l'analyse -------------------------------------------------
    context_pack_entry_id INT REFERENCES knowledge_entries(id),          -- base front-loadée (§7)
    readiness_report_id   INT REFERENCES knowledge_curator_reports(id),  -- le gate qui l'a autorisée
    -- auditabilité de l'appel (P0) --------------------------------------------
    provider_used         TEXT,
    model_used            TEXT,
    prompt_snapshot       TEXT,                    -- system prompt exact utilisé
    grounding_report      JSONB,                   -- sortie du groundedness-checker (A2)
    tokens_in             INT   DEFAULT 0,
    tokens_out            INT   DEFAULT 0,
    cost_usd              NUMERIC(12,6) DEFAULT 0,
    -- cycle de vie ------------------------------------------------------------
    status                TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft','validated','superseded')),
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_research_memos_ticker ON research_memos(ticker_id, created_at DESC);

-- ── 2. research_messages — dialogue utilisateur ↔ research-agent (§8.0) ──────
CREATE TABLE IF NOT EXISTS research_messages (
    id          SERIAL PRIMARY KEY,
    memo_id     INT NOT NULL REFERENCES research_memos(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_research_messages_memo ON research_messages(memo_id, created_at);

-- ── 3. investment_analyses — bull | bear | synthesis (§8.1-8.5) ──────────────
-- result_json porte le contrat correspondant au type :
--   'bull'      -> BullCase           'bear' -> BearCase (refutation_du_bull peuplé au round A6)
--   'synthesis' -> {risk_matrix: RiskMatrix, hypotheses: [Hypothese]}  (SEUL verdict du flux, Q2)
CREATE TABLE IF NOT EXISTS investment_analyses (
    id                    SERIAL PRIMARY KEY,
    ticker_id             TEXT NOT NULL REFERENCES tickers(id),
    analysis_type         TEXT NOT NULL CHECK (analysis_type IN ('bull','bear','synthesis')),
    schema_version        TEXT NOT NULL DEFAULT 'v2.0.0',
    result_json           JSONB NOT NULL,          -- état courant (potentiellement édité, A7)
    result_json_original  JSONB NOT NULL,          -- sortie brute de l'agent, jamais mutée (A7)
    -- provenance & liens de la chaîne d'analyse -------------------------------
    context_pack_entry_id INT REFERENCES knowledge_entries(id),   -- base front-loadée commune (§5.3)
    research_memo_id      INT REFERENCES research_memos(id),       -- memo neutre dont dérive l'analyse
    bull_analysis_id      INT REFERENCES investment_analyses(id),  -- synthèse : cas POUR consommé
    bear_analysis_id      INT REFERENCES investment_analyses(id),  -- synthèse : cas CONTRE consommé
    -- réfutation (A6) & versionnement d'analyse (append-only pour l'audit) -----
    round                 INT NOT NULL DEFAULT 1,                  -- 1 = initial, 2 = post-réfutation
    supersedes_id         INT REFERENCES investment_analyses(id),  -- version précédente remplacée
    -- auditabilité de l'appel (P0) --------------------------------------------
    provider_used         TEXT,
    model_used            TEXT,
    prompt_snapshot       TEXT,
    grounding_report      JSONB,                   -- groundedness-checker (A2) ; rempli après bull/bear
    tokens_in             INT   DEFAULT 0,
    tokens_out            INT   DEFAULT 0,
    cost_usd              NUMERIC(12,6) DEFAULT 0,
    -- cycle de vie ------------------------------------------------------------
    status                TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft','final','superseded')),
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_investment_analyses_ticker ON investment_analyses(ticker_id, analysis_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_investment_analyses_memo   ON investment_analyses(research_memo_id);

-- ── 4. analysis_knowledge_refs (024) — resserrage : FK + domaine polymorphe ──
-- analysis_id reste POLYMORPHE (voir en-tête). On ajoute la FK vers research_memos SEULEMENT via le
-- garde-fou applicatif ; en DB on borne le domaine de analysis_kind et on garantit un index d'accès.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'analysis_refs_kind_domain') THEN
    ALTER TABLE analysis_knowledge_refs
      ADD CONSTRAINT analysis_refs_kind_domain
      CHECK (analysis_kind IN ('analysis','research_memo','readiness','grounding'));
  END IF;
END$$;

-- ── Permissions ──────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON
    research_memos, research_messages, investment_analyses TO portfolio_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO portfolio_user;
