-- 036 — V2 : archivage de la grappe V2 et dévocabularisation (lot 2b, spec §5.1-§5.3).
--       GÉNÉRÉ par `_gen_036.py` / `_gen_036.sh`, NE PAS ÉDITER À LA MAIN : le DDL des
--       tables recréées est celui de `pg_dump --schema-only`, détenteur unique (#46).
--
-- RIEN N'EST DÉTRUIT. `CREATE SCHEMA archive_v2` + `ALTER TABLE … SET SCHEMA` déplacent
-- le graphe EN BLOC : index, contraintes et séquences possédées suivent leur table. Le
-- corpus reste interrogeable comme fixture, et le retour est une commande.
--
-- POURQUOI PAS UN BACKFILL des `covers` vers les `question_id` : une correspondance
-- relue à la main est une correspondance construite pour tomber juste sur les données
-- d'hier. Elle rendrait T1 bon PAR CONSTRUCTION et le défaut indétectable (spec §5.3).
--
-- Grappe archivée : 15 tables · analysis_knowledge_refs, calibration_registry, conviction_debates_v2, eu_ir_scrapers, exit_executions, exit_plans, investment_analyses, knowledge_curator_reports, knowledge_documents, knowledge_entries, monitoring_sessions_v2, post_mortems_v2, research_memos, research_messages, theses_v2
-- Arêtes FK entrantes traitées : 4
-- Colonnes retirées de `knowledge_entries` : 8 · question_status, question_priority, resolves_entry_id, conflict_entry_id, has_conflict, reviewed_by_user, is_deleted, covers
--
-- ⚠️ INDEX SUPPRIMÉS avec leur colonne — listés parce qu'un index qui disparaît en
--    silence est une performance qu'on perd sans jamais l'apprendre :
--      · idx_knowledge_entries_covers_gin (portait covers)
--      · idx_knowledge_entries_open_q (portait question_status, question_priority)
-- ⚠️ CLEFS ÉTRANGÈRES supprimées avec leur colonne :
--      · knowledge_entries knowledge_entries_conflict_entry_id_fkey (sur conflict_entry_id)
--      · knowledge_entries knowledge_entries_resolves_entry_id_fkey (sur resolves_entry_id)
-- Les index dont le prédicat portait `is_deleted = false` sont CONSERVÉS, le conjoint
-- retiré : sans la colonne, toute ligne est « non supprimée », le retrait préserve donc
-- exactement la sémantique.
--
-- Vocabulaire `entry_type` FERMÉ (il ne l'était pas) : ['agent_synthesis', 'analysis', 'fact_financial', 'fact_qualitative', 'fact_statistical']
-- Substitutions (écart V6, arbitrage métier du 2026-09-10) : {'base_rate': 'fact_statistical', 'risk': 'fact_qualitative'}
-- Vocabulaire `report_type` (écart V7, `mvdd` retiré) : ['readiness', 'lint']

BEGIN;

-- ══ A. Le schéma d'archive ══
CREATE SCHEMA archive_v2;

-- ══ B. Les vues adossées à la grappe ══
-- Une vue NE SUIT PAS sa table : elle reste dans `public` et pointe sur la table
-- archivée par OID, donc EN SILENCE. Mesuré sur base sonde le 2026-09-10 : après le
-- déplacement, `public.vv` rendait encore la ligne archivée (v=7) pendant que la table
-- neuve en portait une autre (v=99). Elles sont donc coupées ICI, avant l'archivage,
-- et recréées en §I sur les tables neuves.
DROP VIEW public.knowledge_federation_export;

-- ══ C. Les arêtes FK ENTRANTES ══
-- Ce sont les SEULES que l'archivage casse : un `SET SCHEMA` emporte la contrainte avec
-- la table, donc une FK venue du dehors continuerait de pointer sur l'archive et la
-- table recréée serait inatteignable par ses référents.
-- Spec §5.3 : les lignes derrière ces arêtes (1 position MSFT, 2 `calendar_events`) sont
-- des artefacts de recette du lot 7 — le système n'est en usage réel sur aucun périmètre,
-- il n'y a donc AUCUN fait du monde (#34) à préserver. Elles partent à l'archive avec le
-- reste. La convention #34 redeviendra contraignante le jour où une position réelle
-- existera : d'où la trace, plutôt qu'un simple NULL.
CREATE TABLE archive_v2.liens_entrants (
    table_source text        NOT NULL,
    colonne      text        NOT NULL,
    id_source    integer     NOT NULL,
    valeur       integer     NOT NULL,
    table_cible  text        NOT NULL,
    archive_le   timestamptz NOT NULL DEFAULT now()
);
INSERT INTO archive_v2.liens_entrants (table_source, colonne, id_source, valeur, table_cible)
SELECT 'calendar_events', 'session_v2_id', id, session_v2_id, 'monitoring_sessions_v2' FROM public.calendar_events WHERE session_v2_id IS NOT NULL;
UPDATE public.calendar_events SET session_v2_id = NULL WHERE session_v2_id IS NOT NULL;
ALTER TABLE public.calendar_events DROP CONSTRAINT calendar_events_session_v2_id_fkey;
INSERT INTO archive_v2.liens_entrants (table_source, colonne, id_source, valeur, table_cible)
SELECT 'calendar_events', 'thesis_v2_id', id, thesis_v2_id, 'theses_v2' FROM public.calendar_events WHERE thesis_v2_id IS NOT NULL;
UPDATE public.calendar_events SET thesis_v2_id = NULL WHERE thesis_v2_id IS NOT NULL;
ALTER TABLE public.calendar_events DROP CONSTRAINT calendar_events_thesis_v2_id_fkey;
INSERT INTO archive_v2.liens_entrants (table_source, colonne, id_source, valeur, table_cible)
SELECT 'portfolio_positions', 'thesis_v2_id', id, thesis_v2_id, 'theses_v2' FROM public.portfolio_positions WHERE thesis_v2_id IS NOT NULL;
UPDATE public.portfolio_positions SET thesis_v2_id = NULL WHERE thesis_v2_id IS NOT NULL;
ALTER TABLE public.portfolio_positions DROP CONSTRAINT portfolio_positions_thesis_v2_id_fkey;
INSERT INTO archive_v2.liens_entrants (table_source, colonne, id_source, valeur, table_cible)
SELECT 'price_alerts', 'exit_plan_id', id, exit_plan_id, 'exit_plans' FROM public.price_alerts WHERE exit_plan_id IS NOT NULL;
UPDATE public.price_alerts SET exit_plan_id = NULL WHERE exit_plan_id IS NOT NULL;
ALTER TABLE public.price_alerts DROP CONSTRAINT price_alerts_exit_plan_id_fkey;

-- ══ D. L'archivage lui-même ══
ALTER TABLE public.analysis_knowledge_refs SET SCHEMA archive_v2;
ALTER TABLE public.calibration_registry SET SCHEMA archive_v2;
ALTER TABLE public.conviction_debates_v2 SET SCHEMA archive_v2;
ALTER TABLE public.eu_ir_scrapers SET SCHEMA archive_v2;
ALTER TABLE public.exit_executions SET SCHEMA archive_v2;
ALTER TABLE public.exit_plans SET SCHEMA archive_v2;
ALTER TABLE public.investment_analyses SET SCHEMA archive_v2;
ALTER TABLE public.knowledge_curator_reports SET SCHEMA archive_v2;
ALTER TABLE public.knowledge_documents SET SCHEMA archive_v2;
ALTER TABLE public.knowledge_entries SET SCHEMA archive_v2;
ALTER TABLE public.monitoring_sessions_v2 SET SCHEMA archive_v2;
ALTER TABLE public.post_mortems_v2 SET SCHEMA archive_v2;
ALTER TABLE public.research_memos SET SCHEMA archive_v2;
ALTER TABLE public.research_messages SET SCHEMA archive_v2;
ALTER TABLE public.theses_v2 SET SCHEMA archive_v2;

-- ══ E. Les tables recréées VIDES ══
-- DDL de `pg_dump --schema-only`, modifié par des règles qui portent toutes sur un NOM.
-- Les noms d'index, de contraintes et de séquences sont ceux d'avant : ils ont été
-- libérés dans `public` par le déplacement de leur table.

CREATE TABLE public.analysis_knowledge_refs (
    id integer NOT NULL,
    analysis_id integer NOT NULL,
    analysis_kind text DEFAULT 'analysis'::text NOT NULL,
    entry_id integer NOT NULL,
    entry_version integer NOT NULL,
    content_snapshot text NOT NULL,
    reliability_at_use double precision,
    field_path text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT analysis_refs_kind_domain CHECK ((analysis_kind = ANY (ARRAY['analysis'::text, 'research_memo'::text, 'readiness'::text, 'grounding'::text, 'monitoring'::text, 'debate'::text])))
);

CREATE SEQUENCE public.analysis_knowledge_refs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.analysis_knowledge_refs_id_seq OWNED BY public.analysis_knowledge_refs.id;

CREATE TABLE public.calibration_registry (
    id integer NOT NULL,
    thesis_v2_id integer NOT NULL,
    ticker_id text NOT NULL,
    post_mortem_id integer,
    metric text NOT NULL,
    predite double precision NOT NULL,
    realisee double precision NOT NULL,
    ecart double precision GENERATED ALWAYS AS ((realisee - predite)) STORED,
    created_at timestamp with time zone DEFAULT now()
);

CREATE SEQUENCE public.calibration_registry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.calibration_registry_id_seq OWNED BY public.calibration_registry.id;

CREATE TABLE public.conviction_debates_v2 (
    id integer NOT NULL,
    thesis_v2_id integer NOT NULL,
    ticker_id text NOT NULL,
    monitoring_session_v2_id integer,
    challenge_json jsonb,
    context_sent text,
    raw_content text,
    resolution_suggeree text,
    escalade_recommandee boolean DEFAULT false NOT NULL,
    invalidation_franchie boolean DEFAULT false NOT NULL,
    status text DEFAULT 'open'::text NOT NULL,
    closure_note text,
    closed_at timestamp with time zone,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT cd_v2_anti_complaisance CHECK (((NOT invalidation_franchie) OR (resolution_suggeree IS NULL) OR (resolution_suggeree = 'closed_pass'::text) OR ((resolution_suggeree = 'closed_monitor'::text) AND escalade_recommandee))),
    CONSTRAINT cd_v2_resolution_domaine CHECK (((resolution_suggeree IS NULL) OR (resolution_suggeree = ANY (ARRAY['closed_pass'::text, 'closed_monitor'::text, 'closed_proceed'::text])))),
    CONSTRAINT cd_v2_status_domaine CHECK ((status = ANY (ARRAY['open'::text, 'closed_pass'::text, 'closed_monitor'::text, 'closed_proceed'::text, 'failed'::text])))
);

CREATE SEQUENCE public.conviction_debates_v2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.conviction_debates_v2_id_seq OWNED BY public.conviction_debates_v2.id;

CREATE TABLE public.eu_ir_scrapers (
    id integer NOT NULL,
    ticker_id text,
    scraper_url text NOT NULL,
    scraper_config jsonb,
    scraper_health text DEFAULT 'ok'::text,
    last_success_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE SEQUENCE public.eu_ir_scrapers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.eu_ir_scrapers_id_seq OWNED BY public.eu_ir_scrapers.id;

CREATE TABLE public.exit_executions (
    id integer NOT NULL,
    exit_plan_id integer NOT NULL,
    ordre integer NOT NULL,
    pct_a_vendre numeric(7,4) NOT NULL,
    declencheur text DEFAULT ''::text NOT NULL,
    shares_sold numeric(15,4) NOT NULL,
    sell_price_native numeric(15,4) NOT NULL,
    sell_currency text DEFAULT 'EUR'::text NOT NULL,
    fx_rate numeric(18,8),
    sell_price_eur numeric(15,4) NOT NULL,
    proceeds_eur numeric(15,4) GENERATED ALWAYS AS ((shares_sold * sell_price_eur)) STORED,
    executed_at date DEFAULT CURRENT_DATE NOT NULL,
    cash_movement_id integer,
    note text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ee_quantites_positives CHECK (((ordre >= 1) AND (shares_sold > (0)::numeric) AND (sell_price_native > (0)::numeric) AND (sell_price_eur > (0)::numeric) AND (pct_a_vendre > (0)::numeric) AND (pct_a_vendre <= (100)::numeric)))
);

CREATE SEQUENCE public.exit_executions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.exit_executions_id_seq OWNED BY public.exit_executions.id;

CREATE TABLE public.exit_plans (
    id integer NOT NULL,
    thesis_v2_id integer NOT NULL,
    ticker_id text NOT NULL,
    position_id integer,
    monitoring_session_v2_id integer,
    origine text NOT NULL,
    exit_status text,
    plan_json jsonb,
    context_sent text,
    raw_content text,
    status text DEFAULT 'completed'::text NOT NULL,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    closed_at timestamp with time zone,
    CONSTRAINT ep_exit_status_domaine CHECK (((exit_status IS NULL) OR (exit_status = ANY (ARRAY['plan_created'::text, 'partially_exited'::text, 'closed'::text, 'accelerated_exit'::text])))),
    CONSTRAINT ep_exit_status_si_complet CHECK (((status <> 'completed'::text) OR (exit_status IS NOT NULL))),
    CONSTRAINT ep_origine_domaine CHECK ((origine = ANY (ARRAY['thesis_degradation'::text, 'rendement_insuffisant'::text, 'hypothese_invalidee'::text, 'reallocation'::text]))),
    CONSTRAINT ep_status_domaine CHECK ((status = ANY (ARRAY['completed'::text, 'failed'::text])))
);

CREATE SEQUENCE public.exit_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.exit_plans_id_seq OWNED BY public.exit_plans.id;

CREATE TABLE public.investment_analyses (
    id integer NOT NULL,
    ticker_id text NOT NULL,
    analysis_type text NOT NULL,
    schema_version text DEFAULT 'v2.0.0'::text NOT NULL,
    result_json jsonb NOT NULL,
    result_json_original jsonb NOT NULL,
    context_pack_entry_id integer,
    research_memo_id integer,
    bull_analysis_id integer,
    bear_analysis_id integer,
    round integer DEFAULT 1 NOT NULL,
    supersedes_id integer,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    grounding_report jsonb,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT investment_analyses_analysis_type_check CHECK ((analysis_type = ANY (ARRAY['bull'::text, 'bear'::text, 'synthesis'::text]))),
    CONSTRAINT investment_analyses_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'final'::text, 'superseded'::text])))
);

CREATE SEQUENCE public.investment_analyses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.investment_analyses_id_seq OWNED BY public.investment_analyses.id;

CREATE TABLE public.knowledge_curator_reports (
    id integer NOT NULL,
    ticker_id text NOT NULL,
    report_type text NOT NULL,
    report_json jsonb NOT NULL,
    verdict text,
    coverage_structuree jsonb,
    coverage_qualitative jsonb,
    context_pack_entry_id integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT knowledge_curator_reports_report_type_check CHECK ((report_type = ANY (ARRAY['readiness'::text, 'lint'::text])))
);

CREATE SEQUENCE public.knowledge_curator_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.knowledge_curator_reports_id_seq OWNED BY public.knowledge_curator_reports.id;

CREATE TABLE public.knowledge_documents (
    id integer NOT NULL,
    ticker_id text,
    doc_type text NOT NULL,
    title text,
    source_url text,
    source_type text NOT NULL,
    content_raw text,
    content_hash text,
    published_date date,
    fiscal_period text,
    is_confidential boolean DEFAULT false NOT NULL,
    language text DEFAULT 'en'::text,
    processing_status text DEFAULT 'pending'::text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE SEQUENCE public.knowledge_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.knowledge_documents_id_seq OWNED BY public.knowledge_documents.id;

CREATE TABLE public.knowledge_entries (
    id integer NOT NULL,
    ticker_id text,
    document_id integer,
    entry_type text NOT NULL,
    title text,
    content text NOT NULL,
    content_structured jsonb,
    tags text[] DEFAULT '{}'::text[],
    lang text DEFAULT 'en'::text,
    source_type text NOT NULL,
    source_url text,
    source_date date,
    fiscal_period text,
    reliability_score double precision NOT NULL,
    reliability_tier text NOT NULL,
    reliability_note text,
    requires_human_review boolean DEFAULT false,
    last_reviewed_at timestamp with time zone,
    model_cutoff text,
    version integer DEFAULT 1 NOT NULL,
    valid_from timestamp with time zone DEFAULT now(),
    superseded_by integer,
    embedding public.vector(1024),
    is_outdated boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    nature text NOT NULL,
    CONSTRAINT knowledge_entries_nature_check CHECK ((nature = ANY (ARRAY['evenement'::text, 'interpretation'::text, 'mesure'::text]))),
    CONSTRAINT knowledge_entries_reliability_score_check CHECK (((reliability_score >= (0.0)::double precision) AND (reliability_score <= (1.0)::double precision))),
    CONSTRAINT knowledge_entries_reliability_tier_check CHECK ((reliability_tier = ANY (ARRAY['A'::text, 'A-'::text, 'B+'::text, 'B'::text, 'B-'::text, 'C+'::text, 'C'::text])))
);

CREATE SEQUENCE public.knowledge_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.knowledge_entries_id_seq OWNED BY public.knowledge_entries.id;

CREATE TABLE public.monitoring_sessions_v2 (
    id integer NOT NULL,
    thesis_v2_id integer NOT NULL,
    ticker_id text NOT NULL,
    mode integer NOT NULL,
    trigger_type text DEFAULT 'manual'::text NOT NULL,
    trigger_label text DEFAULT ''::text NOT NULL,
    calendar_event_id integer,
    result_json jsonb,
    context_sent text,
    raw_content text,
    alert_level text,
    verdict text,
    routing_suggestion text,
    status text DEFAULT 'completed'::text NOT NULL,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ms_v2_alert_level_mode2 CHECK (((alert_level IS NULL) OR ((mode = 2) AND (alert_level = ANY (ARRAY['RAS'::text, 'REVIEW_REQUIRED'::text, 'CRITICAL'::text]))))),
    CONSTRAINT ms_v2_mode_domaine CHECK (((mode >= 1) AND (mode <= 6))),
    CONSTRAINT ms_v2_status_domaine CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'pending_manual'::text]))),
    CONSTRAINT ms_v2_verdict_par_mode CHECK (((verdict IS NULL) OR ((mode = 6) AND (verdict = ANY (ARRAY['CONFIRMER'::text, 'RENFORCER'::text, 'REDUIRE'::text, 'SORTIR'::text]))) OR ((mode = 3) AND (verdict = ANY (ARRAY['MAINTENIR'::text, 'REDUIRE'::text, 'SORTIR'::text, 'RE_SYNTHESE'::text])))))
);

CREATE SEQUENCE public.monitoring_sessions_v2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.monitoring_sessions_v2_id_seq OWNED BY public.monitoring_sessions_v2.id;

CREATE TABLE public.post_mortems_v2 (
    id integer NOT NULL,
    thesis_v2_id integer NOT NULL,
    ticker_id text NOT NULL,
    exit_plan_id integer,
    position_id integer,
    duree_jours integer,
    performance_pct numeric(12,4),
    result_json jsonb,
    context_sent text,
    raw_content text,
    lesson_entry_ids integer[] DEFAULT '{}'::integer[] NOT NULL,
    status text DEFAULT 'completed'::text NOT NULL,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    calibration_json jsonb,
    calibration_raw text,
    calibration_tokens_in integer DEFAULT 0,
    calibration_tokens_out integer DEFAULT 0,
    calibration_cost_usd numeric(12,6) DEFAULT 0,
    calibration_at timestamp with time zone,
    CONSTRAINT pm_v2_status_domaine CHECK ((status = ANY (ARRAY['completed'::text, 'failed'::text])))
);

CREATE SEQUENCE public.post_mortems_v2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.post_mortems_v2_id_seq OWNED BY public.post_mortems_v2.id;

CREATE TABLE public.research_memos (
    id integer NOT NULL,
    ticker_id text NOT NULL,
    schema_version text DEFAULT 'v2.0.0'::text NOT NULL,
    memo_json jsonb NOT NULL,
    memo_json_original jsonb NOT NULL,
    context_pack_entry_id integer,
    readiness_report_id integer,
    provider_used text,
    model_used text,
    prompt_snapshot text,
    grounding_report jsonb,
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    cost_usd numeric(12,6) DEFAULT 0,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT research_memos_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'validated'::text, 'superseded'::text])))
);

CREATE SEQUENCE public.research_memos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.research_memos_id_seq OWNED BY public.research_memos.id;

CREATE TABLE public.research_messages (
    id integer NOT NULL,
    memo_id integer NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT research_messages_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text])))
);

CREATE SEQUENCE public.research_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.research_messages_id_seq OWNED BY public.research_messages.id;

CREATE TABLE public.theses_v2 (
    id integer NOT NULL,
    ticker_id text NOT NULL,
    schema_version text DEFAULT 'v2.0.0'::text NOT NULL,
    validation_json jsonb,
    research_memo_id integer,
    synthesis_analysis_id integer,
    pre_mortem_acked boolean DEFAULT false NOT NULL,
    risk_matrix_acked boolean DEFAULT false NOT NULL,
    risk_acks jsonb,
    verdict text,
    position_sizing_pct numeric(7,4),
    valuation_range jsonb,
    conditions_entree text[] DEFAULT '{}'::text[] NOT NULL,
    hypotheses jsonb,
    status text DEFAULT 'draft'::text NOT NULL,
    validated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT theses_v2_active_complete CHECK (((status <> 'active'::text) OR ((validation_json IS NOT NULL) AND (synthesis_analysis_id IS NOT NULL) AND (verdict IS NOT NULL) AND (position_sizing_pct IS NOT NULL) AND (valuation_range IS NOT NULL) AND (hypotheses IS NOT NULL) AND (pre_mortem_acked IS TRUE) AND (risk_matrix_acked IS TRUE) AND ((verdict <> 'PROCEED_AVEC_CONDITIONS'::text) OR (cardinality(conditions_entree) > 0))))),
    CONSTRAINT theses_v2_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'under_review'::text, 'superseded'::text, 'invalidated'::text, 'closed'::text]))),
    CONSTRAINT theses_v2_verdict_check CHECK ((verdict = ANY (ARRAY['PROCEED'::text, 'PROCEED_AVEC_CONDITIONS'::text])))
);

CREATE SEQUENCE public.theses_v2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.theses_v2_id_seq OWNED BY public.theses_v2.id;

ALTER TABLE ONLY public.analysis_knowledge_refs ALTER COLUMN id SET DEFAULT nextval('public.analysis_knowledge_refs_id_seq'::regclass);

ALTER TABLE ONLY public.calibration_registry ALTER COLUMN id SET DEFAULT nextval('public.calibration_registry_id_seq'::regclass);

ALTER TABLE ONLY public.conviction_debates_v2 ALTER COLUMN id SET DEFAULT nextval('public.conviction_debates_v2_id_seq'::regclass);

ALTER TABLE ONLY public.eu_ir_scrapers ALTER COLUMN id SET DEFAULT nextval('public.eu_ir_scrapers_id_seq'::regclass);

ALTER TABLE ONLY public.exit_executions ALTER COLUMN id SET DEFAULT nextval('public.exit_executions_id_seq'::regclass);

ALTER TABLE ONLY public.exit_plans ALTER COLUMN id SET DEFAULT nextval('public.exit_plans_id_seq'::regclass);

ALTER TABLE ONLY public.investment_analyses ALTER COLUMN id SET DEFAULT nextval('public.investment_analyses_id_seq'::regclass);

ALTER TABLE ONLY public.knowledge_curator_reports ALTER COLUMN id SET DEFAULT nextval('public.knowledge_curator_reports_id_seq'::regclass);

ALTER TABLE ONLY public.knowledge_documents ALTER COLUMN id SET DEFAULT nextval('public.knowledge_documents_id_seq'::regclass);

ALTER TABLE ONLY public.knowledge_entries ALTER COLUMN id SET DEFAULT nextval('public.knowledge_entries_id_seq'::regclass);

ALTER TABLE ONLY public.monitoring_sessions_v2 ALTER COLUMN id SET DEFAULT nextval('public.monitoring_sessions_v2_id_seq'::regclass);

ALTER TABLE ONLY public.post_mortems_v2 ALTER COLUMN id SET DEFAULT nextval('public.post_mortems_v2_id_seq'::regclass);

ALTER TABLE ONLY public.research_memos ALTER COLUMN id SET DEFAULT nextval('public.research_memos_id_seq'::regclass);

ALTER TABLE ONLY public.research_messages ALTER COLUMN id SET DEFAULT nextval('public.research_messages_id_seq'::regclass);

ALTER TABLE ONLY public.theses_v2 ALTER COLUMN id SET DEFAULT nextval('public.theses_v2_id_seq'::regclass);

ALTER TABLE ONLY public.analysis_knowledge_refs
    ADD CONSTRAINT analysis_knowledge_refs_analysis_id_analysis_kind_entry_id__key UNIQUE (analysis_id, analysis_kind, entry_id, field_path);

ALTER TABLE ONLY public.analysis_knowledge_refs
    ADD CONSTRAINT analysis_knowledge_refs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.calibration_registry
    ADD CONSTRAINT calibration_registry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.conviction_debates_v2
    ADD CONSTRAINT conviction_debates_v2_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.eu_ir_scrapers
    ADD CONSTRAINT eu_ir_scrapers_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.exit_executions
    ADD CONSTRAINT exit_executions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.exit_plans
    ADD CONSTRAINT exit_plans_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.knowledge_curator_reports
    ADD CONSTRAINT knowledge_curator_reports_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.knowledge_entries
    ADD CONSTRAINT knowledge_entries_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.monitoring_sessions_v2
    ADD CONSTRAINT monitoring_sessions_v2_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.post_mortems_v2
    ADD CONSTRAINT post_mortems_v2_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.research_memos
    ADD CONSTRAINT research_memos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.research_messages
    ADD CONSTRAINT research_messages_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.theses_v2
    ADD CONSTRAINT theses_v2_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.calibration_registry
    ADD CONSTRAINT uq_calibration_metric UNIQUE (thesis_v2_id, metric);

ALTER TABLE ONLY public.exit_executions
    ADD CONSTRAINT uq_exit_execution_tranche UNIQUE (exit_plan_id, ordre);

CREATE INDEX idx_analysis_refs_analysis ON public.analysis_knowledge_refs USING btree (analysis_id, analysis_kind);

CREATE INDEX idx_analysis_refs_entry ON public.analysis_knowledge_refs USING btree (entry_id);

CREATE INDEX idx_calibration_metric ON public.calibration_registry USING btree (metric);

CREATE INDEX idx_calibration_ticker ON public.calibration_registry USING btree (ticker_id);

CREATE INDEX idx_cd_v2_ouverts ON public.conviction_debates_v2 USING btree (thesis_v2_id) WHERE (status = 'open'::text);

CREATE INDEX idx_cd_v2_thesis ON public.conviction_debates_v2 USING btree (thesis_v2_id);

CREATE INDEX idx_cd_v2_ticker ON public.conviction_debates_v2 USING btree (ticker_id);

CREATE INDEX idx_curator_reports_ticker ON public.knowledge_curator_reports USING btree (ticker_id, report_type, created_at DESC);

CREATE INDEX idx_eu_ir_scrapers_ticker ON public.eu_ir_scrapers USING btree (ticker_id);

CREATE INDEX idx_exit_exec_plan ON public.exit_executions USING btree (exit_plan_id);

CREATE INDEX idx_exit_plans_position ON public.exit_plans USING btree (position_id) WHERE (position_id IS NOT NULL);

CREATE INDEX idx_exit_plans_thesis ON public.exit_plans USING btree (thesis_v2_id);

CREATE INDEX idx_exit_plans_ticker ON public.exit_plans USING btree (ticker_id);

CREATE INDEX idx_investment_analyses_memo ON public.investment_analyses USING btree (research_memo_id);

CREATE INDEX idx_investment_analyses_ticker ON public.investment_analyses USING btree (ticker_id, analysis_type, created_at DESC);

CREATE INDEX idx_knowledge_entries_current ON public.knowledge_entries USING btree (ticker_id, entry_type) WHERE ((superseded_by IS NULL));

CREATE INDEX idx_knowledge_entries_embedding ON public.knowledge_entries USING hnsw (embedding public.vector_cosine_ops);

CREATE INDEX idx_knowledge_entries_nature ON public.knowledge_entries USING btree (ticker_id, nature) WHERE ((superseded_by IS NULL));

CREATE INDEX idx_knowledge_entries_review ON public.knowledge_entries USING btree (requires_human_review) WHERE (requires_human_review = true);

CREATE INDEX idx_knowledge_entries_ticker ON public.knowledge_entries USING btree (ticker_id);

CREATE INDEX idx_knowledge_entries_type ON public.knowledge_entries USING btree (entry_type);

CREATE INDEX idx_knowledge_entries_unembedded ON public.knowledge_entries USING btree (ticker_id) WHERE ((embedding IS NULL) AND (superseded_by IS NULL));

CREATE INDEX idx_ms_v2_event ON public.monitoring_sessions_v2 USING btree (calendar_event_id) WHERE (calendar_event_id IS NOT NULL);

CREATE INDEX idx_ms_v2_thesis ON public.monitoring_sessions_v2 USING btree (thesis_v2_id);

CREATE INDEX idx_ms_v2_ticker ON public.monitoring_sessions_v2 USING btree (ticker_id);

CREATE INDEX idx_pm_v2_ticker ON public.post_mortems_v2 USING btree (ticker_id);

CREATE INDEX idx_research_memos_ticker ON public.research_memos USING btree (ticker_id, created_at DESC);

CREATE INDEX idx_research_messages_memo ON public.research_messages USING btree (memo_id, created_at);

CREATE INDEX idx_theses_v2_status ON public.theses_v2 USING btree (status);

CREATE INDEX idx_theses_v2_ticker ON public.theses_v2 USING btree (ticker_id, created_at DESC);

CREATE UNIQUE INDEX uq_exit_plan_actif ON public.exit_plans USING btree (thesis_v2_id) WHERE ((status = 'completed'::text) AND (exit_status <> 'closed'::text));

CREATE UNIQUE INDEX uq_post_mortem_v2_thesis ON public.post_mortems_v2 USING btree (thesis_v2_id) WHERE (status = 'completed'::text);

ALTER TABLE ONLY public.analysis_knowledge_refs
    ADD CONSTRAINT analysis_knowledge_refs_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.knowledge_entries(id);

ALTER TABLE ONLY public.calibration_registry
    ADD CONSTRAINT calibration_registry_post_mortem_id_fkey FOREIGN KEY (post_mortem_id) REFERENCES public.post_mortems_v2(id);

ALTER TABLE ONLY public.calibration_registry
    ADD CONSTRAINT calibration_registry_thesis_v2_id_fkey FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);

ALTER TABLE ONLY public.calibration_registry
    ADD CONSTRAINT calibration_registry_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.conviction_debates_v2
    ADD CONSTRAINT conviction_debates_v2_monitoring_session_v2_id_fkey FOREIGN KEY (monitoring_session_v2_id) REFERENCES public.monitoring_sessions_v2(id);

ALTER TABLE ONLY public.conviction_debates_v2
    ADD CONSTRAINT conviction_debates_v2_thesis_v2_id_fkey FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);

ALTER TABLE ONLY public.conviction_debates_v2
    ADD CONSTRAINT conviction_debates_v2_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.eu_ir_scrapers
    ADD CONSTRAINT eu_ir_scrapers_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.exit_executions
    ADD CONSTRAINT exit_executions_cash_movement_id_fkey FOREIGN KEY (cash_movement_id) REFERENCES public.cash_movements(id);

ALTER TABLE ONLY public.exit_executions
    ADD CONSTRAINT exit_executions_exit_plan_id_fkey FOREIGN KEY (exit_plan_id) REFERENCES public.exit_plans(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.exit_plans
    ADD CONSTRAINT exit_plans_monitoring_session_v2_id_fkey FOREIGN KEY (monitoring_session_v2_id) REFERENCES public.monitoring_sessions_v2(id);

ALTER TABLE ONLY public.exit_plans
    ADD CONSTRAINT exit_plans_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.portfolio_positions(id);

ALTER TABLE ONLY public.exit_plans
    ADD CONSTRAINT exit_plans_thesis_v2_id_fkey FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);

ALTER TABLE ONLY public.exit_plans
    ADD CONSTRAINT exit_plans_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_bear_analysis_id_fkey FOREIGN KEY (bear_analysis_id) REFERENCES public.investment_analyses(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_bull_analysis_id_fkey FOREIGN KEY (bull_analysis_id) REFERENCES public.investment_analyses(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_context_pack_entry_id_fkey FOREIGN KEY (context_pack_entry_id) REFERENCES public.knowledge_entries(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_research_memo_id_fkey FOREIGN KEY (research_memo_id) REFERENCES public.research_memos(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_supersedes_id_fkey FOREIGN KEY (supersedes_id) REFERENCES public.investment_analyses(id);

ALTER TABLE ONLY public.investment_analyses
    ADD CONSTRAINT investment_analyses_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.knowledge_curator_reports
    ADD CONSTRAINT knowledge_curator_reports_context_pack_entry_id_fkey FOREIGN KEY (context_pack_entry_id) REFERENCES public.knowledge_entries(id);

ALTER TABLE ONLY public.knowledge_curator_reports
    ADD CONSTRAINT knowledge_curator_reports_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.knowledge_entries
    ADD CONSTRAINT knowledge_entries_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id);

ALTER TABLE ONLY public.knowledge_entries
    ADD CONSTRAINT knowledge_entries_superseded_by_fkey FOREIGN KEY (superseded_by) REFERENCES public.knowledge_entries(id);

ALTER TABLE ONLY public.knowledge_entries
    ADD CONSTRAINT knowledge_entries_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.monitoring_sessions_v2
    ADD CONSTRAINT monitoring_sessions_v2_calendar_event_id_fkey FOREIGN KEY (calendar_event_id) REFERENCES public.calendar_events(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.monitoring_sessions_v2
    ADD CONSTRAINT monitoring_sessions_v2_thesis_v2_id_fkey FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);

ALTER TABLE ONLY public.monitoring_sessions_v2
    ADD CONSTRAINT monitoring_sessions_v2_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.post_mortems_v2
    ADD CONSTRAINT post_mortems_v2_exit_plan_id_fkey FOREIGN KEY (exit_plan_id) REFERENCES public.exit_plans(id);

ALTER TABLE ONLY public.post_mortems_v2
    ADD CONSTRAINT post_mortems_v2_position_id_fkey FOREIGN KEY (position_id) REFERENCES public.portfolio_positions(id);

ALTER TABLE ONLY public.post_mortems_v2
    ADD CONSTRAINT post_mortems_v2_thesis_v2_id_fkey FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);

ALTER TABLE ONLY public.post_mortems_v2
    ADD CONSTRAINT post_mortems_v2_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.research_memos
    ADD CONSTRAINT research_memos_context_pack_entry_id_fkey FOREIGN KEY (context_pack_entry_id) REFERENCES public.knowledge_entries(id);

ALTER TABLE ONLY public.research_memos
    ADD CONSTRAINT research_memos_readiness_report_id_fkey FOREIGN KEY (readiness_report_id) REFERENCES public.knowledge_curator_reports(id);

ALTER TABLE ONLY public.research_memos
    ADD CONSTRAINT research_memos_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

ALTER TABLE ONLY public.research_messages
    ADD CONSTRAINT research_messages_memo_id_fkey FOREIGN KEY (memo_id) REFERENCES public.research_memos(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.theses_v2
    ADD CONSTRAINT theses_v2_research_memo_id_fkey FOREIGN KEY (research_memo_id) REFERENCES public.research_memos(id);

ALTER TABLE ONLY public.theses_v2
    ADD CONSTRAINT theses_v2_synthesis_analysis_id_fkey FOREIGN KEY (synthesis_analysis_id) REFERENCES public.investment_analyses(id);

ALTER TABLE ONLY public.theses_v2
    ADD CONSTRAINT theses_v2_ticker_id_fkey FOREIGN KEY (ticker_id) REFERENCES public.tickers(id);

-- ══ F. Les séquences reprennent où l'archive s'arrête ══
-- Pas de redémarrage à 1 : le corpus neuf et le corpus archivé seront LUS CÔTE À CÔTE
-- (comparaison avec la ligne de base du 2026-09-09). Deux entries #42 rendraient toute
-- citation ambiguë, et l'ambiguïté ne se découvre qu'au moment où elle a déjà trompé.
SELECT setval('public.analysis_knowledge_refs_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.analysis_knowledge_refs), false);
SELECT setval('public.calibration_registry_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.calibration_registry), false);
SELECT setval('public.conviction_debates_v2_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.conviction_debates_v2), false);
SELECT setval('public.eu_ir_scrapers_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.eu_ir_scrapers), false);
SELECT setval('public.exit_executions_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.exit_executions), false);
SELECT setval('public.exit_plans_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.exit_plans), false);
SELECT setval('public.investment_analyses_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.investment_analyses), false);
SELECT setval('public.knowledge_curator_reports_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.knowledge_curator_reports), false);
SELECT setval('public.knowledge_documents_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.knowledge_documents), false);
SELECT setval('public.knowledge_entries_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.knowledge_entries), false);
SELECT setval('public.monitoring_sessions_v2_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.monitoring_sessions_v2), false);
SELECT setval('public.post_mortems_v2_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.post_mortems_v2), false);
SELECT setval('public.research_memos_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.research_memos), false);
SELECT setval('public.research_messages_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.research_messages), false);
SELECT setval('public.theses_v2_id_seq',
       (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.theses_v2), false);

-- ══ G. Les arêtes entrantes, rebranchées sur les tables NEUVES ══
ALTER TABLE public.calendar_events ADD CONSTRAINT calendar_events_session_v2_id_fkey
    FOREIGN KEY (session_v2_id) REFERENCES public.monitoring_sessions_v2(id);
ALTER TABLE public.calendar_events ADD CONSTRAINT calendar_events_thesis_v2_id_fkey
    FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);
ALTER TABLE public.portfolio_positions ADD CONSTRAINT portfolio_positions_thesis_v2_id_fkey
    FOREIGN KEY (thesis_v2_id) REFERENCES public.theses_v2(id);
ALTER TABLE public.price_alerts ADD CONSTRAINT price_alerts_exit_plan_id_fkey
    FOREIGN KEY (exit_plan_id) REFERENCES public.exit_plans(id);

-- ══ H. `question_coverage` — la couverture est une RELATION ══
-- 4ᵉ axe de la doctrine (#50/#51/#53/#57) : la fiabilité est une propriété de la SOURCE,
-- la nature une propriété de l'ASSERTION, l'actualité une propriété de la RELATION
-- fait ↔ ancre, et la couverture une propriété de la RELATION entry ↔ question. Les deux
-- dernières dépendent d'un second terme que l'entry ne connaît pas ; les stocker sur
-- l'entry fige un verdict qui a changé depuis.
--
-- ⚠️ `framework_version` n'est pas décoratif : sans lui, réécrire l'énoncé de `qf_1`
-- rendrait rétroactivement « couvertes » des entries collectées pour une AUTRE question.
--
-- ⚠️ Aucun ON DELETE CASCADE sur `entry_id`, et c'est délibéré : une entry ne se supprime
-- pas (append-only + supersede — c'est même pourquoi `is_deleted` s'en va). Un CASCADE
-- serait un chemin de suppression silencieux d'une FONDATION. Supprimer une entry citée
-- doit ÉCHOUER bruyamment.
--
-- ⚠️ L'ABSENCE de ligne n'est pas une erreur : c'est le cas par DÉFAUT. Une entry sans
-- lien est stockée, embeddée, retrouvée et citable — elle ne compte simplement pas comme
-- fondation (spec §5.1, conséquence 2). C'est la latitude ticker par ticker.
--
-- `question_id` / `ingredient_id` n'ont PAS de clef étrangère : leur détenteur est
-- `app/frameworks/frameworks.yaml`, données inertes et versionnées avec le code (§5.2).
-- La validation vit donc en Python, au SITE D'ÉCRITURE UNIQUE de l'aiguilleur (§3.6), et
-- elle LÈVE sur un inconnu. C'est le silence qui était le défaut de `covers`, pas
-- l'absence de contrainte.
CREATE TABLE public.question_coverage (
    id                integer     GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    framework_id      text        NOT NULL,
    framework_version text        NOT NULL,
    question_id       text        NOT NULL,
    ingredient_id     text        NOT NULL,
    entry_id          integer     NOT NULL REFERENCES public.knowledge_entries(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT question_coverage_unique
        UNIQUE (framework_id, framework_version, question_id, ingredient_id, entry_id)
);
CREATE INDEX idx_question_coverage_entry ON public.question_coverage (entry_id);
CREATE INDEX idx_question_coverage_question
    ON public.question_coverage (framework_id, framework_version, question_id);

-- ══ I. Les vues recréées sur les tables neuves ══
-- Leur corps est REPRIS de l'instantané, amputé des colonnes retirées. `is_deleted` dans
-- un `WHERE` disparaît (toute ligne est « non supprimée ») ; `has_conflict` dans un
-- `jsonb_build_object` disparaît de la clef exportée — un consommateur de fédération qui
-- la lisait lisait `false` depuis toujours.
CREATE VIEW public.knowledge_federation_export AS SELECT 'portfolio-tracker:postgres:knowledge_entry/'::text || id AS doc_id,     'portfolio-tracker'::text AS project,     'postgres'::text AS source,     'https://portfolio.jlmvpscode.duckdns.org/knowledge/entry/'::text || id AS uri,     COALESCE(title, "left"(content, 80)) AS title,     content AS body,     lang,     tags,     jsonb_build_object('tickers',         CASE             WHEN ticker_id IS NULL THEN '[]'::jsonb             ELSE jsonb_build_array(ticker_id)         END) AS entities,     reliability_score AS reliability,     reliability_tier,     'public'::text AS visibility,     created_at,     updated_at,     now() AS ingested_at,     'sha256:'::text || encode(digest(content, 'sha256'::text), 'hex'::text) AS content_hash,     jsonb_build_object('source_type', source_type, 'entry_type', entry_type, 'entry_version', version, 'fiscal_period', fiscal_period) AS metadata    FROM knowledge_entries e   WHERE superseded_by IS NULL;

-- ══ J. Dévocabularisation (écarts V6 / V7) ══
-- `entry_type` n'avait AUCUN CHECK : c'était du texte libre écrit par les producteurs,
-- ce qui rendait `base_rate` et `risk` indétectables par une lecture du schéma. Le
-- vocabulaire est fermé sur ce que les producteurs ÉCRIVENT — pas sur ce que du code
-- LIT : `quote` et `lesson_learned` sont nommés par des filtres de lecture sans qu'aucun
-- producteur ne les émette, les admettre serait rouvrir une option que personne
-- n'exerce.
ALTER TABLE public.knowledge_entries
    ADD CONSTRAINT knowledge_entries_entry_type_check
    CHECK (entry_type IN ('agent_synthesis', 'analysis', 'fact_financial', 'fact_qualitative', 'fact_statistical'));

-- ══ K. Gardes NOMMÉES, dans la transaction ══
-- Une garde qui sort en `RAISE NOTICE` laisse le trou se refermer sur un COMMIT vert.
-- Chacune dit QUOI, pas seulement OÙ. Éprouvées EN NÉGATIF avant application (spec §12,
-- piège 11 ; `feedback_test_negatif_obligatoire`).
DO $$
DECLARE n INT; v TEXT;
BEGIN
  -- K1 — la grappe est bien PARTIE de `public` et bien ARRIVÉE dans l'archive.
  SELECT count(*) INTO n FROM pg_class c JOIN pg_namespace ns ON ns.oid = c.relnamespace
   WHERE ns.nspname = 'archive_v2' AND c.relkind = 'r' AND c.relname = ANY(ARRAY['analysis_knowledge_refs', 'calibration_registry', 'conviction_debates_v2', 'eu_ir_scrapers', 'exit_executions', 'exit_plans', 'investment_analyses', 'knowledge_curator_reports', 'knowledge_documents', 'knowledge_entries', 'monitoring_sessions_v2', 'post_mortems_v2', 'research_memos', 'research_messages', 'theses_v2']);
  IF n <> 15 THEN
    RAISE EXCEPTION '036/K1 : % tables sur 15 dans archive_v2', n;
  END IF;

  -- K2 — les tables recréées sont VIDES. Une table non vide signifierait que le
  --      `SET SCHEMA` n'a pas eu lieu et qu'on est en train d'écrire un CHECK sur le
  --      corpus qu'on croyait avoir archivé.
  SELECT count(*) INTO n FROM public.analysis_knowledge_refs;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.analysis_knowledge_refs porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.calibration_registry;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.calibration_registry porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.conviction_debates_v2;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.conviction_debates_v2 porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.eu_ir_scrapers;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.eu_ir_scrapers porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.exit_executions;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.exit_executions porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.exit_plans;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.exit_plans porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.investment_analyses;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.investment_analyses porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_curator_reports;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.knowledge_curator_reports porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_documents;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.knowledge_documents porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.knowledge_entries porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.monitoring_sessions_v2;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.monitoring_sessions_v2 porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.post_mortems_v2;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.post_mortems_v2 porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.research_memos;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.research_memos porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.research_messages;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.research_messages porte % lignes', n; END IF;
  SELECT count(*) INTO n FROM public.theses_v2;
  IF n <> 0 THEN RAISE EXCEPTION '036/K2 : public.theses_v2 porte % lignes', n; END IF;

  -- K3 — les 8 colonnes ont disparu de `knowledge_entries`.
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'knowledge_entries'
     AND column_name = ANY(ARRAY['question_status', 'question_priority', 'resolves_entry_id', 'conflict_entry_id', 'has_conflict', 'reviewed_by_user', 'is_deleted', 'covers']);
  IF n <> 0 THEN RAISE EXCEPTION '036/K3 : % colonne(s) retirée(s) encore présente(s)', n; END IF;

  -- K4 — la garde MIROIR de K3 : ce qui DEVAIT rester est resté. Sans elle, une règle
  --      trop gourmande (un `\b` mal placé) viderait la table et K3 serait VERTE.
  --      C'est le 1er faux vert : un assert satisfait par une mesure dégénérée.
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'knowledge_entries';
  IF n <> 27 THEN
    RAISE EXCEPTION '036/K4 : knowledge_entries porte % colonnes, 27 attendues (35 avant moins 8)', n;
  END IF;

  -- K5 — `question_coverage` existe ET sa FK sur `entry_id` MORD. Une table de liaison
  --      sans clef étrangère réelle serait `covers` avec un nom neuf (#57).
  SELECT count(*) INTO n FROM pg_constraint
   WHERE conrelid = 'public.question_coverage'::regclass AND contype = 'f'
     AND confrelid = 'public.knowledge_entries'::regclass;
  IF n <> 1 THEN RAISE EXCEPTION '036/K5 : question_coverage sans FK réelle vers knowledge_entries'; END IF;

  -- K6 — les deux vocabulaires ne portent plus de jeton méthodologique. Le CHECK est lu
  --      dans son TEXTE : c'est lui le point de lecture, pas la liste qu'on a écrite.
  SELECT string_agg(conname, ', ') INTO v FROM pg_constraint
   WHERE contype = 'c' AND connamespace = 'public'::regnamespace
     AND pg_get_constraintdef(oid) ~ '''base_rate'''
     AND conrelid IN ('public.knowledge_entries'::regclass,
                      'public.knowledge_curator_reports'::regclass);
  IF v IS NOT NULL THEN
    RAISE EXCEPTION '036/K6 : le jeton ''base_rate'' survit dans %', v;
  END IF;
  SELECT string_agg(conname, ', ') INTO v FROM pg_constraint
   WHERE contype = 'c' AND connamespace = 'public'::regnamespace
     AND pg_get_constraintdef(oid) ~ '''mvdd'''
     AND conrelid IN ('public.knowledge_entries'::regclass,
                      'public.knowledge_curator_reports'::regclass);
  IF v IS NOT NULL THEN
    RAISE EXCEPTION '036/K6 : le jeton ''mvdd'' survit dans %', v;
  END IF;
  SELECT string_agg(conname, ', ') INTO v FROM pg_constraint
   WHERE contype = 'c' AND connamespace = 'public'::regnamespace
     AND pg_get_constraintdef(oid) ~ '''risk'''
     AND conrelid IN ('public.knowledge_entries'::regclass,
                      'public.knowledge_curator_reports'::regclass);
  IF v IS NOT NULL THEN
    RAISE EXCEPTION '036/K6 : le jeton ''risk'' survit dans %', v;
  END IF;

  -- K7 — le CHECK `entry_type` MORD vraiment. Vérifier qu'il EXISTE ne prouve rien : un
  --      CHECK peut exister et ne rien refuser. On lui présente une valeur du
  --      vocabulaire retiré et on exige qu'il la rejette — test négatif inclus dans la
  --      migration (`feedback_test_negatif_obligatoire`).
  BEGIN
    INSERT INTO public.knowledge_entries
           (entry_type, content, source_type, reliability_score, reliability_tier, nature)
    VALUES ('base_rate', 'sonde 036/K7', 'edgar_official', 1.0, 'A', 'mesure');
    RAISE EXCEPTION '036/K7 : le CHECK entry_type a ACCEPTÉ un jeton retiré — il existe mais ne mord pas';
  EXCEPTION WHEN check_violation THEN
    NULL;  -- attendu : c'est la preuve que la contrainte est vivante
  END;
  -- Le miroir : le vocabulaire retenu passe. Un CHECK qui refuse TOUT serait vert en K7.
  BEGIN
    INSERT INTO public.knowledge_entries
           (entry_type, content, source_type, reliability_score, reliability_tier, nature)
    VALUES ('fact_statistical', 'sonde 036/K7', 'edgar_official', 1.0, 'A', 'mesure');
  EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION '036/K7 : le CHECK entry_type REFUSE le vocabulaire retenu (%)', SQLERRM;
  END;
  DELETE FROM public.knowledge_entries WHERE content = 'sonde 036/K7';
  PERFORM setval('public.knowledge_entries_id_seq',
         (SELECT coalesce(max(id), 0) + 1 FROM archive_v2.knowledge_entries), false);
END $$;

COMMIT;
