-- =====================================================================
-- Schéma de référence — Tour de contrôle stratégique, spec v2
-- PostgreSQL 16 + pgvector. Base dédiée `db_strategic` sur shared-postgres.
--
-- Fichier UNIQUE et consolidé (remplace 03-SCHEMA.sql + 11-SCHEMA-ADDENDUM.sql de la v1).
-- Chaque section indique le module propriétaire : chaque table figure dans `tables`
-- du manifeste de ce module (check_schema.py). Les migrations Alembic produisent ce schéma.
--
-- Sensibilité (05-SORTIES-EXTERNES.md) : les colonnes `*_enc` portent des données `red`,
-- chiffrées applicativement (shared-postgres est partagée avec d'autres projets : un dump
-- de la base ne doit pas exposer une conviction).
-- Aucune valeur sectorielle, aucune valeur par défaut porteuse d'un choix métier.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;          -- gen_random_uuid()

-- ---------- Types STRUCTURELS (aucun sens sectoriel) ----------
CREATE TYPE sensitivity     AS ENUM ('green','amber','red');
CREATE TYPE geo_role        AS ENUM ('actor','market','jurisdiction');
CREATE TYPE source_status   AS ENUM ('pending','trial','accepted','rejected','suspended');
CREATE TYPE question_status AS ENUM ('active','paused','answered','expired');
CREATE TYPE thesis_stance   AS ENUM ('supports','contradicts','neutral');
CREATE TYPE feedback_kind   AS ENUM ('relevant','noise','already_known','critical');
CREATE TYPE function_status AS ENUM ('planned','waiting','active','disabled');
CREATE TYPE user_role       AS ENUM ('owner','analyst','reader');
CREATE TYPE date_precision  AS ENUM ('day','month','quarter','year','unknown');

-- =====================================================================
-- NOYAU
-- =====================================================================

-- ---------- Utilisateurs ----------
CREATE TABLE app_user (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT UNIQUE NOT NULL,
  display_name    TEXT,
  role            user_role NOT NULL DEFAULT 'reader',
  password_hash   TEXT NOT NULL,
  totp_secret_enc BYTEA,
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  prefs           JSONB NOT NULL DEFAULT '{}'
);

-- ---------- Configuration versionnée ----------
CREATE TABLE config_change (
  id          BIGSERIAL PRIMARY KEY,              -- = config_version
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  changed_by  TEXT NOT NULL,                      -- user:<id> | import:<fichier> | bootstrap
  object_kind TEXT NOT NULL,                      -- setting|taxonomy_term|source|source_template|module|...
  object_ref  TEXT NOT NULL,
  before      JSONB,
  after       JSONB,
  reason      TEXT
);

CREATE TABLE setting (                            -- réglages du noyau et des modules
  scope      TEXT NOT NULL,                       -- 'noyau' | <module_id>
  key        TEXT NOT NULL,
  value      JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (scope, key)
);

CREATE TABLE secret (                             -- coffre : saisi dans l'interface, jamais réaffiché
  name       TEXT PRIMARY KEY,                    -- référencé par les gabarits : secret_ref
  value_enc  BYTEA NOT NULL,                      -- chiffré par la clé maîtresse (.env)
  scope      TEXT NOT NULL DEFAULT 'collecte',    -- qui peut le lire
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rotated_at TIMESTAMPTZ
);

-- ---------- Modules et fonctions (miroir des manifestes, état d'exécution) ----------
CREATE TABLE module_state (
  module_id   TEXT PRIMARY KEY,
  enabled     BOOLEAN NOT NULL DEFAULT true,
  version     TEXT NOT NULL,
  manifest    JSONB NOT NULL,                     -- copie du module.yml chargé
  loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE capability_state (                   -- une ligne par fonction
  module_id      TEXT NOT NULL REFERENCES module_state(module_id) ON DELETE CASCADE,
  function_id    TEXT NOT NULL,
  status         function_status NOT NULL,
  requirements   JSONB NOT NULL DEFAULT '{}',
  current_values JSONB NOT NULL DEFAULT '{}',
  missing        TEXT,                            -- ce qu'il manque, en clair
  user_disabled  BOOLEAN NOT NULL DEFAULT false,
  evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (module_id, function_id)
);

-- ---------- Bus d'événements ----------
CREATE TABLE event_outbox (
  id              BIGSERIAL PRIMARY KEY,
  event_type      TEXT NOT NULL,                  -- signal.resolved, ...
  payload         JSONB NOT NULL,                 -- identifiants seulement, jamais de texte red
  idempotency_key TEXT UNIQUE NOT NULL,
  emitted_by      TEXT NOT NULL,                  -- module_id
  emitted_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON event_outbox (event_type, id);

CREATE TABLE event_consumption (
  event_id     BIGINT NOT NULL REFERENCES event_outbox(id) ON DELETE CASCADE,
  consumer     TEXT NOT NULL,                     -- <module_id>.<function_id>
  status       TEXT NOT NULL DEFAULT 'pending',   -- pending|running|done|failed|skipped
  attempts     SMALLINT NOT NULL DEFAULT 0,
  last_error   TEXT,
  locked_until TIMESTAMPTZ,
  done_at      TIMESTAMPTZ,
  PRIMARY KEY (event_id, consumer)
);
CREATE INDEX ON event_consumption (consumer, status);

CREATE TABLE job_run (
  id          BIGSERIAL PRIMARY KEY,
  job_name    TEXT NOT NULL,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'running',    -- running|ok|partial|error
  items_in    INT NOT NULL DEFAULT 0,
  items_out   INT NOT NULL DEFAULT 0,
  cost_eur    NUMERIC NOT NULL DEFAULT 0,
  error       TEXT
);

-- ---------- Taxonomies (tous les axes métier) ----------
CREATE TABLE taxonomy (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code        TEXT UNIQUE NOT NULL,   -- watch_domain, event_type, horizon, watch_angle, relation_kind,
                                      -- link_kind, reliability_scale, maturity_scale, market_segment,
                                      -- tech_domain, geo_zone, metric, entity_kind, content_type, ...
  label       TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('flat','hierarchical','scale')),
  is_core     BOOLEAN NOT NULL DEFAULT false,     -- le moteur exige sa présence (jamais son contenu)
  cardinality TEXT NOT NULL DEFAULT 'single' CHECK (cardinality IN ('single','multi')),
  owner       TEXT NOT NULL DEFAULT 'noyau'       -- 'noyau' | 'pack:<code>' | <module_id>
);

CREATE TABLE taxonomy_term (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  taxonomy_id UUID NOT NULL REFERENCES taxonomy(id) ON DELETE CASCADE,
  code        TEXT NOT NULL,
  label       TEXT NOT NULL,
  parent_id   UUID REFERENCES taxonomy_term(id),
  ordinal     INT,
  aliases     TEXT[] NOT NULL DEFAULT '{}',
  attributes  JSONB NOT NULL DEFAULT '{}',        -- ex. event_type : {extraction_schema, roles} ;
                                                  -- geo_zone : {iso, dynamics} ; metric : {unit, period}
                                                  -- entity_kind : {attributes_schema}
  active      BOOLEAN NOT NULL DEFAULT true,
  UNIQUE (taxonomy_id, code)
);
CREATE INDEX ON taxonomy_term (taxonomy_id, parent_id);

-- ---------- Périmètre ----------
CREATE TABLE perimeter (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code               TEXT UNIQUE NOT NULL,
  label              TEXT NOT NULL,
  pack_code          TEXT NOT NULL,              -- pack sectoriel d'origine
  domestic_zone_id   UUID REFERENCES taxonomy_term(id),
  reference_currency CHAR(3) NOT NULL,           -- fourni par le pack, pas de défaut
  description        TEXT,                       -- green : description publique du périmètre
  active             BOOLEAN NOT NULL DEFAULT true,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Registre d'identité ----------
CREATE TABLE entity (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind          TEXT NOT NULL,                   -- code d'un terme de la taxonomie entity_kind
  code          TEXT UNIQUE NOT NULL,
  label         TEXT NOT NULL,
  aliases       TEXT[] NOT NULL DEFAULT '{}',
  external_ids  JSONB NOT NULL DEFAULT '{}',     -- identifiants de registres, LEI, ...
  attributes    JSONB NOT NULL DEFAULT '{}',     -- validés par le JSON Schema du type
  web_domains   TEXT[] NOT NULL DEFAULT '{}',    -- aide à la résolution et aux sources dérivées
  status        TEXT NOT NULL DEFAULT 'validated'
                CHECK (status IN ('validated','pending','merged','rejected')),
  merged_into   UUID REFERENCES entity(id),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ,
  mention_count INT NOT NULL DEFAULT 0
);
CREATE INDEX ON entity USING gin (label gin_trgm_ops);
CREATE INDEX ON entity USING gin (aliases);
CREATE INDEX ON entity (kind, status);

-- Seul type d'entité à table typée : le moteur raisonne dessus en SQL.
CREATE TABLE actor (
  entity_id    UUID PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
  actor_type   TEXT,                            -- terme de taxonomie actor_type (pack)
  hq_zone_id   UUID REFERENCES taxonomy_term(id),
  founded_year SMALLINT,
  is_listed    BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE actor_relation (                   -- rôle RELATIF au périmètre (amber)
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id     UUID NOT NULL REFERENCES actor(entity_id) ON DELETE CASCADE,
  perimeter_id UUID NOT NULL REFERENCES perimeter(id) ON DELETE CASCADE,
  kind_term_id UUID NOT NULL REFERENCES taxonomy_term(id),   -- relation_kind
  segment_ids  UUID[] NOT NULL DEFAULT '{}',
  intensity    SMALLINT NOT NULL DEFAULT 2 CHECK (intensity BETWEEN 1 AND 3),
  note         TEXT,
  UNIQUE (actor_id, perimeter_id, kind_term_id)
);

CREATE TABLE actor_edge (                       -- graphe entre acteurs (green)
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_actor_id UUID NOT NULL REFERENCES actor(entity_id) ON DELETE CASCADE,
  to_actor_id   UUID NOT NULL REFERENCES actor(entity_id) ON DELETE CASCADE,
  kind_term_id  UUID NOT NULL REFERENCES taxonomy_term(id),
  since DATE, until DATE,
  evidence_id   UUID,                           -- FK ajoutée après evidence
  UNIQUE (from_actor_id, to_actor_id, kind_term_id)
);

CREATE TABLE entity_milestone (                 -- alimente le calendrier prospectif
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id   UUID NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL,                    -- deadline|effective|closing|launch|award|...
  due_on      DATE NOT NULL,
  precision   date_precision NOT NULL DEFAULT 'day',
  label       TEXT,
  evidence_id UUID,                             -- FK ajoutée après evidence
  superseded_by UUID REFERENCES entity_milestone(id)
);
CREATE INDEX ON entity_milestone (due_on);

CREATE TABLE entity_alias_candidate (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  surface_form       TEXT NOT NULL,
  proposed_entity_id UUID REFERENCES entity(id),
  proposed_kind      TEXT,
  confidence         NUMERIC,
  occurrences        INT NOT NULL DEFAULT 1,
  first_raw_item_id  UUID,                      -- FK ajoutée après raw_item
  status             TEXT NOT NULL DEFAULT 'pending',  -- pending|accepted|rejected|merged
  decided_at         TIMESTAMPTZ,
  UNIQUE (surface_form, proposed_kind)
);

CREATE TABLE entity_merge_candidate (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_a   UUID NOT NULL REFERENCES entity(id),
  entity_b   UUID NOT NULL REFERENCES entity(id),
  similarity NUMERIC NOT NULL,
  reason     TEXT,
  status     TEXT NOT NULL DEFAULT 'pending',
  UNIQUE (entity_a, entity_b)
);

-- ---------- Embeddings (modèle remplaçable) ----------
CREATE TABLE embedding (
  object_kind TEXT NOT NULL,                    -- signal|entity|key_question|indicator|cluster|raw_item
  object_id   UUID NOT NULL,
  model       TEXT NOT NULL,                    -- ex. 'BAAI/bge-m3'
  dim         SMALLINT NOT NULL,
  vec         vector NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (object_kind, object_id, model)
);
-- Index vectoriel créé par migration paramétrée, une fois le modèle choisi :
--   CREATE INDEX ON embedding USING hnsw ((vec::vector(1024)) vector_cosine_ops)
--     WHERE model = 'BAAI/bge-m3';

-- ---------- Sorties externes et coûts (05-SORTIES-EXTERNES.md) ----------
CREATE TABLE prompt_template (
  code             TEXT NOT NULL,
  version          INT NOT NULL,
  purpose          TEXT NOT NULL,               -- extraction|so_what|indicator_check|probe|pack_assistant|...
  max_sensitivity  sensitivity NOT NULL,        -- plus haut niveau de donnée que le gabarit accepte
  body             TEXT NOT NULL,
  validated_at     TIMESTAMPTZ,                 -- exigé si max_sensitivity = amber (validation utilisateur)
  validated_by     UUID REFERENCES app_user(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (code, version),
  CHECK (max_sensitivity <> 'red')              -- aucun gabarit ne peut accepter du red
);

CREATE TABLE egress_log (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  channel         TEXT NOT NULL,                -- llm|embedding|search|email|slack
  destination     TEXT NOT NULL,                -- fournisseur ou service
  purpose         TEXT NOT NULL,
  prompt_code     TEXT,
  prompt_version  INT,
  max_sensitivity sensitivity NOT NULL,
  amber_refs      JSONB NOT NULL DEFAULT '[]',  -- objets amber présents (type, id), pour la revue
  payload_hash    TEXT NOT NULL,
  payload_bytes   INT NOT NULL,
  payload_preview TEXT,                         -- contenu exact, purgé après 30 jours
  allowed         BOOLEAN NOT NULL,
  refusal_reason  TEXT,
  reviewed_at     TIMESTAMPTZ                   -- revue hebdomadaire
);
CREATE INDEX ON egress_log (occurred_at DESC);
CREATE INDEX ON egress_log (max_sensitivity, reviewed_at);

CREATE TABLE api_usage (
  id          BIGSERIAL PRIMARY KEY,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  provider    TEXT NOT NULL,
  purpose     TEXT NOT NULL,
  module_id   TEXT,
  function_id TEXT,
  units       NUMERIC NOT NULL,
  unit_kind   TEXT NOT NULL,                    -- tokens_in|tokens_out|calls|searches
  cost_eur    NUMERIC NOT NULL,
  egress_id   BIGINT REFERENCES egress_log(id)
);
CREATE INDEX ON api_usage (occurred_at);

-- ---------- Transverse ----------
CREATE TABLE annotation (                       -- red
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES app_user(id),
  target_kind TEXT NOT NULL,
  target_id   UUID NOT NULL,
  body_enc    BYTEA NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE coverage_review (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_start        DATE NOT NULL,
  period_end          DATE NOT NULL,
  event_label         TEXT NOT NULL,
  event_date          DATE NOT NULL,
  was_detected        BOOLEAN NOT NULL,
  detected_signal_id  UUID,                     -- FK ajoutée après signal
  learned_from        TEXT,
  missing_source_hint TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- MODULE SOCLE : collecte
-- =====================================================================
CREATE TABLE source_template (
  code        TEXT NOT NULL,
  version     INT NOT NULL,
  family      TEXT NOT NULL,                    -- rss|http_json|http_xml|html_list|html_diff|sitemap|search|email|file
  provided_by TEXT NOT NULL,                    -- module_id | 'pack:<code>' | 'user'
  definition  JSONB NOT NULL,                   -- requête, paramètres typés, mappage, pagination, ...
  params_schema JSONB NOT NULL DEFAULT '{}',    -- JSON Schema des paramètres d'instance (formulaire UI)
  bound_entity_kind TEXT,                       -- gabarit dérivable du référentiel (04 §6)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (code, version)
);

CREATE TABLE source (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code               TEXT UNIQUE NOT NULL,
  label              TEXT NOT NULL,
  template_code      TEXT NOT NULL,
  template_version   INT NOT NULL,
  params             JSONB NOT NULL DEFAULT '{}',
  bound_entity_id    UUID REFERENCES entity(id), -- source dérivée d'une entité
  language           TEXT,                       -- code ISO ou 'multi'
  zone_id            UUID REFERENCES taxonomy_term(id),
  domain_codes       TEXT[] NOT NULL DEFAULT '{}',
  content_type       TEXT,                       -- terme de la taxonomie content_type
  default_sensitivity sensitivity NOT NULL DEFAULT 'green',  -- terrain@ : red
  is_primary         BOOLEAN NOT NULL DEFAULT false,
  independence_group TEXT,                       -- même groupe = pas de corroboration mutuelle
  schedule_cron      TEXT,                       -- NULL = poussée (email, fichier)
  next_run_at        TIMESTAMPTZ,
  cost_per_call_eur  NUMERIC NOT NULL DEFAULT 0,
  status             source_status NOT NULL DEFAULT 'pending',
  health             TEXT NOT NULL DEFAULT 'unknown',   -- unknown|ok|degraded|broken
  health_note        TEXT,
  last_success_at    TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (template_code, template_version) REFERENCES source_template(code, version)
);
CREATE INDEX ON source (next_run_at) WHERE status IN ('trial','accepted');

CREATE TABLE source_qualification (
  source_id               UUID PRIMARY KEY REFERENCES source(id) ON DELETE CASCADE,
  reliability_scale       TEXT NOT NULL,        -- code de taxonomie d'échelle
  reliability_source_code TEXT,
  reliability_info_code   TEXT,
  originality             NUMERIC,
  independence_note       TEXT,
  dossier                 JSONB NOT NULL DEFAULT '{}',
  decided_at              TIMESTAMPTZ,
  decided_by              UUID REFERENCES app_user(id),
  trial_until             DATE,
  relevance_rate          NUMERIC
);

CREATE TABLE source_cursor (
  source_id  UUID NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  key        TEXT NOT NULL,                     -- watermark|page|etag|last_id|...
  value      JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_id, key)
);

CREATE TABLE source_run (
  id              BIGSERIAL PRIMARY KEY,
  source_id       UUID NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  run_key         TEXT UNIQUE,                  -- idempotence du déclenchement
  mode            TEXT NOT NULL DEFAULT 'live', -- live|preview (aperçu : rien n'est écrit en raw_item)
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  status          TEXT NOT NULL DEFAULT 'running',  -- running|ok|partial|error
  http_calls      INT NOT NULL DEFAULT 0,
  items_fetched   INT NOT NULL DEFAULT 0,
  items_new       INT NOT NULL DEFAULT 0,
  items_duplicate INT NOT NULL DEFAULT 0,
  cursor_before   JSONB,
  cursor_after    JSONB,
  error           TEXT
);
CREATE INDEX ON source_run (source_id, started_at DESC);

CREATE TABLE source_sample (                    -- échantillon réel figé : non-régression du mappage
  id          BIGSERIAL PRIMARY KEY,
  source_id   UUID NOT NULL REFERENCES source(id) ON DELETE CASCADE,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  response    JSONB NOT NULL,                   -- réponse brute (ou texte encapsulé)
  expected    JSONB NOT NULL                    -- RawItem produits à la capture
);

CREATE TABLE raw_item (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id          UUID NOT NULL REFERENCES source(id),
  source_run_id      BIGINT REFERENCES source_run(id),
  probe_id           UUID,                      -- FK ajoutée après probe
  source_native_id   TEXT,
  revision           SMALLINT NOT NULL DEFAULT 1,   -- page modifiée = nouvelle révision
  parent_raw_item_id UUID REFERENCES raw_item(id),  -- newsletter découpée en articles
  url                TEXT,
  canonical_url      TEXT,
  title              TEXT,
  content            TEXT,                      -- vide pour red : voir content_enc
  content_enc        BYTEA,
  content_hash       TEXT NOT NULL,
  simhash            BIGINT,
  language           TEXT,
  authors            TEXT[] NOT NULL DEFAULT '{}',
  content_type       TEXT,
  sensitivity        sensitivity NOT NULL DEFAULT 'green',
  published_at       TIMESTAMPTZ,
  fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_payload     JSONB,                     -- réponse structurée d'origine : rejeu sans recollecte
  http_status        SMALLINT,
  etag               TEXT,
  http_last_modified TIMESTAMPTZ,
  paywalled          BOOLEAN NOT NULL DEFAULT false,
  status             TEXT NOT NULL DEFAULT 'new',   -- new|processed|discarded (seules colonnes mutables)
  discard_reason     TEXT,
  UNIQUE (source_id, content_hash),
  CHECK (sensitivity <> 'red' OR (content IS NULL AND content_enc IS NOT NULL))
);
CREATE UNIQUE INDEX ON raw_item (source_id, source_native_id, revision) WHERE source_native_id IS NOT NULL;
CREATE INDEX ON raw_item (status, fetched_at);
CREATE INDEX ON raw_item (simhash);

ALTER TABLE entity_alias_candidate
  ADD FOREIGN KEY (first_raw_item_id) REFERENCES raw_item(id);

-- =====================================================================
-- MODULE SOCLE : signaux
-- =====================================================================
CREATE TABLE signal (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  perimeter_id        UUID NOT NULL REFERENCES perimeter(id),
  title               TEXT NOT NULL,            -- factuel, neutre
  statement           TEXT NOT NULL,            -- le fait, 2-3 phrases
  so_what             TEXT,
  event_type_term_id  UUID REFERENCES taxonomy_term(id),
  event_fields        JSONB NOT NULL DEFAULT '{}',   -- champs du schéma d'extraction du type
  event_date          DATE,
  event_date_precision date_precision NOT NULL DEFAULT 'unknown',
  sensitivity         sensitivity NOT NULL DEFAULT 'green',
  importance          NUMERIC NOT NULL DEFAULT 0,
  credibility         NUMERIC NOT NULL DEFAULT 0,
  score_breakdown     JSONB NOT NULL DEFAULT '{}',
  score_components_disabled TEXT[] NOT NULL DEFAULT '{}',
  extraction_confidence NUMERIC,
  corroboration_count SMALLINT NOT NULL DEFAULT 1,
  independent_sources SMALLINT NOT NULL DEFAULT 1,
  unconfirmed_until   TIMESTAMPTZ,              -- « important mais non confirmé »
  is_orphan           BOOLEAN NOT NULL DEFAULT false,
  cluster_id          UUID,
  first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  detection_latency_h NUMERIC,
  pipeline_version    TEXT NOT NULL,
  prompt_code         TEXT,
  prompt_version      INT,
  config_version      BIGINT REFERENCES config_change(id),
  extractor_model     TEXT,
  replay_of_signal_id UUID REFERENCES signal(id),
  replay_batch_id     UUID,                     -- FK ajoutée après replay_batch ; NULL = production
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON signal (first_seen_at DESC) WHERE replay_batch_id IS NULL;
CREATE INDEX ON signal (event_date DESC);
CREATE INDEX ON signal (importance DESC, credibility DESC);

CREATE TABLE evidence (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id           UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  raw_item_id         UUID NOT NULL REFERENCES raw_item(id),
  quote               TEXT NOT NULL,            -- citation exacte
  offset_start INT, offset_end INT,
  is_primary_source   BOOLEAN NOT NULL DEFAULT false,
  echo_of_evidence_id UUID REFERENCES evidence(id),   -- reprise d'une autre source
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (signal_id, raw_item_id)
);

ALTER TABLE actor_edge       ADD FOREIGN KEY (evidence_id) REFERENCES evidence(id);
ALTER TABLE entity_milestone ADD FOREIGN KEY (evidence_id) REFERENCES evidence(id);
ALTER TABLE coverage_review  ADD FOREIGN KEY (detected_signal_id) REFERENCES signal(id);

CREATE TABLE signal_term (                      -- domaines, angles, horizon, segments, technologies...
  signal_id   UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  term_id     UUID NOT NULL REFERENCES taxonomy_term(id),
  is_primary  BOOLEAN NOT NULL DEFAULT false,
  confidence  NUMERIC,
  assigned_by TEXT NOT NULL DEFAULT 'pipeline', -- pipeline|user
  PRIMARY KEY (signal_id, term_id)
);
CREATE INDEX ON signal_term (term_id, is_primary);

CREATE TABLE signal_entity (
  signal_id UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  entity_id UUID NOT NULL REFERENCES entity(id),
  role      TEXT NOT NULL DEFAULT 'mentioned',  -- subject|object|counterpart|mentioned
  salience  NUMERIC,
  PRIMARY KEY (signal_id, entity_id, role)
);

CREATE TABLE signal_geo (
  signal_id UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  zone_id   UUID NOT NULL REFERENCES taxonomy_term(id),
  role      geo_role NOT NULL,
  PRIMARY KEY (signal_id, zone_id, role)
);

CREATE TABLE signal_link (
  from_signal_id UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  to_signal_id   UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  kind_term_id   UUID NOT NULL REFERENCES taxonomy_term(id),   -- link_kind
  note           TEXT,
  PRIMARY KEY (from_signal_id, to_signal_id, kind_term_id)
);

CREATE TABLE signal_revision (
  id         BIGSERIAL PRIMARY KEY,
  signal_id  UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  changed_by TEXT NOT NULL,                     -- pipeline|user|<module_id>
  diff       JSONB NOT NULL,
  reason     TEXT
);

CREATE TABLE observation (                      -- fait chiffré
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id    UUID NOT NULL REFERENCES entity(id),
  metric_term_id UUID NOT NULL REFERENCES taxonomy_term(id),   -- taxonomie metric
  value        NUMERIC NOT NULL,
  unit         TEXT NOT NULL,
  currency     CHAR(3),
  period_start DATE,
  period_end   DATE,
  as_of        DATE,
  evidence_id  UUID NOT NULL REFERENCES evidence(id),
  superseded_by UUID REFERENCES observation(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON observation (entity_id, metric_term_id, period_end);

CREATE TABLE feedback (
  id         BIGSERIAL PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES app_user(id),
  signal_id  UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  kind       feedback_kind NOT NULL,
  note       TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE replay_batch (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  label            TEXT NOT NULL,
  pipeline_version TEXT NOT NULL,
  raw_item_filter  JSONB NOT NULL,
  is_shadow        BOOLEAN NOT NULL DEFAULT true,   -- n'écrase rien, sert à comparer
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at      TIMESTAMPTZ,
  metrics          JSONB
);
ALTER TABLE signal ADD FOREIGN KEY (replay_batch_id) REFERENCES replay_batch(id);

-- =====================================================================
-- MODULE SOCLE : diffusion
-- =====================================================================
CREATE TABLE digest (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         TEXT NOT NULL,                   -- daily|weekly|alert
  period_start TIMESTAMPTZ,
  period_end   TIMESTAMPTZ,
  composition  JSONB NOT NULL,                  -- sections, cartes, décomptes amber/red masqués
  signal_ids   UUID[] NOT NULL DEFAULT '{}',
  channel      TEXT,                            -- email|slack|web
  egress_id    BIGINT REFERENCES egress_log(id),
  sent_at      TIMESTAMPTZ
);

-- =====================================================================
-- MODULE : questions_cles
-- =====================================================================
CREATE TABLE mandate (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  perimeter_id           UUID NOT NULL REFERENCES perimeter(id),
  code                   TEXT UNIQUE NOT NULL,
  label                  TEXT NOT NULL,         -- amber
  decision_supported_enc BYTEA NOT NULL,        -- red : la décision éclairée
  review_due_on          DATE NOT NULL,
  active                 BOOLEAN NOT NULL DEFAULT true,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE key_question (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mandate_id         UUID NOT NULL REFERENCES mandate(id) ON DELETE CASCADE,
  code               TEXT UNIQUE NOT NULL,
  statement          TEXT NOT NULL,             -- amber, falsifiable
  question_type      TEXT NOT NULL,             -- factual|prospective|comparative|causal
  answer_horizon     DATE,
  status             question_status NOT NULL DEFAULT 'active',
  cadence            TEXT NOT NULL DEFAULT 'daily',
  alert_threshold    NUMERIC,
  scope              JSONB NOT NULL DEFAULT '{}',   -- entités, segments, technologies, zones
  current_answer     TEXT,
  current_confidence NUMERIC,                   -- estimation système (amber) ; la probabilité de
                                                -- l'utilisateur est un forecast (red)
  answer_updated_at  TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE indicator (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key_question_id UUID REFERENCES key_question(id) ON DELETE CASCADE,
  statement       TEXT NOT NULL,                -- amber
  direction       TEXT NOT NULL CHECK (direction IN ('confirms','refutes')),
  weight          NUMERIC NOT NULL DEFAULT 1,
  match_rule      JSONB,                        -- règle déclarative (01 §6), NULL = question vérifiable
  check_question  TEXT,                         -- question fermée posée au LLM (segmentée)
  observed_count  INT NOT NULL DEFAULT 0,
  active          BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE indicator_observation (
  indicator_id UUID NOT NULL REFERENCES indicator(id) ON DELETE CASCADE,
  signal_id    UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  matched_by   TEXT NOT NULL,                   -- rule|llm|user
  confidence   NUMERIC,
  confirmed_by_user BOOLEAN,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (indicator_id, signal_id)
);

CREATE TABLE probe (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key_question_id UUID NOT NULL REFERENCES key_question(id) ON DELETE CASCADE,
  source_id       UUID REFERENCES source(id),   -- instance du gabarit de recherche
  query           TEXT NOT NULL,                -- amber, éditable
  is_generated    BOOLEAN NOT NULL DEFAULT true,
  last_run_at     TIMESTAMPTZ,
  yield_count     INT NOT NULL DEFAULT 0,
  cost_to_date    NUMERIC NOT NULL DEFAULT 0,
  active          BOOLEAN NOT NULL DEFAULT true
);
ALTER TABLE raw_item ADD FOREIGN KEY (probe_id) REFERENCES probe(id);

CREATE TABLE signal_question (
  signal_id       UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  key_question_id UUID NOT NULL REFERENCES key_question(id) ON DELETE CASCADE,
  relevance       NUMERIC NOT NULL,
  PRIMARY KEY (signal_id, key_question_id)
);

-- =====================================================================
-- MODULE : scenarios
-- =====================================================================
CREATE TABLE scenario_set (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  perimeter_id UUID NOT NULL REFERENCES perimeter(id),
  code         TEXT UNIQUE NOT NULL,
  uncertainty  TEXT NOT NULL,                   -- amber : l'incertitude majeure
  horizon_date DATE,
  active       BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE scenario (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_set_id UUID NOT NULL REFERENCES scenario_set(id) ON DELETE CASCADE,
  code            TEXT NOT NULL,
  statement       TEXT NOT NULL,                -- amber
  UNIQUE (scenario_set_id, code)
);

CREATE TABLE scenario_indicator (               -- signes avant-coureurs
  scenario_id  UUID NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
  indicator_id UUID NOT NULL REFERENCES indicator(id) ON DELETE CASCADE,
  likelihood_ratio NUMERIC NOT NULL DEFAULT 1,  -- effet d'une observation sur la vraisemblance
  PRIMARY KEY (scenario_id, indicator_id)
);

CREATE TABLE scenario_likelihood (              -- red : répartition de vraisemblance historisée
  id              BIGSERIAL PRIMARY KEY,
  scenario_set_id UUID NOT NULL REFERENCES scenario_set(id) ON DELETE CASCADE,
  distribution_enc BYTEA NOT NULL,              -- {scenario_code: probabilité}
  cause           TEXT NOT NULL,                -- indicator|user
  cause_ref       UUID,
  recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- MODULE : theses (red)
-- =====================================================================
CREATE TABLE thesis (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  perimeter_id  UUID NOT NULL REFERENCES perimeter(id),
  code          TEXT UNIQUE NOT NULL,
  statement_enc BYTEA NOT NULL,
  rationale_enc BYTEA,
  scenario_id   UUID REFERENCES scenario(id),   -- le scénario sur lequel on parie
  horizon_date  DATE,
  status        TEXT NOT NULL DEFAULT 'active', -- active|validated|invalidated|retired
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE thesis_indicator (                 -- la thèse se rapproche des signaux PAR ses indicateurs
  thesis_id    UUID NOT NULL REFERENCES thesis(id) ON DELETE CASCADE,
  indicator_id UUID NOT NULL REFERENCES indicator(id) ON DELETE CASCADE,
  PRIMARY KEY (thesis_id, indicator_id)
);

CREATE TABLE thesis_link (
  thesis_id     UUID NOT NULL REFERENCES thesis(id) ON DELETE CASCADE,
  signal_id     UUID NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  stance        thesis_stance NOT NULL,
  weight        NUMERIC NOT NULL DEFAULT 1,
  rationale_enc BYTEA,
  proposed_by   TEXT NOT NULL DEFAULT 'indicator',  -- indicator|user
  confirmed_at  TIMESTAMPTZ,                    -- validation utilisateur
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (thesis_id, signal_id)
);

CREATE TABLE thesis_confidence_history (
  id             BIGSERIAL PRIMARY KEY,
  thesis_id      UUID NOT NULL REFERENCES thesis(id) ON DELETE CASCADE,
  confidence_enc BYTEA NOT NULL,
  reason_enc     BYTEA,
  recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- MODULE : calibration (red)
-- =====================================================================
CREATE TABLE forecast (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target_kind   TEXT NOT NULL,                  -- key_question|scenario|thesis
  target_id     UUID NOT NULL,
  probability_enc BYTEA NOT NULL,
  resolves_on   DATE,
  outcome       BOOLEAN,                        -- renseigné à l'échéance
  resolved_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- MODULE : terrain (red)
-- =====================================================================
CREATE TABLE field_note (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_item_id  UUID REFERENCES raw_item(id),    -- note reçue par terrain@ (contenu chiffré dans raw_item)
  author_id    UUID REFERENCES app_user(id),    -- note saisie dans l'outil
  body_enc     BYTEA,
  occurred_on  DATE,
  context      TEXT,                            -- salon|rendez-vous|appel|autre (libre, non sensible)
  reliability_source_code TEXT,
  reliability_info_code   TEXT,
  entity_ids   UUID[] NOT NULL DEFAULT '{}',    -- rattachement par dictionnaire puis manuel
  key_question_ids UUID[] NOT NULL DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (raw_item_id IS NOT NULL OR body_enc IS NOT NULL)
);

-- =====================================================================
-- MODULE : livrables
-- =====================================================================
CREATE TABLE deliverable (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_code    TEXT NOT NULL,
  title            TEXT NOT NULL,
  audience_role    user_role NOT NULL,          -- filtre de sensibilité appliqué
  params           JSONB NOT NULL DEFAULT '{}',
  body_md          TEXT NOT NULL,               -- red présent seulement si audience_role = owner
  signal_ids       UUID[] NOT NULL DEFAULT '{}',
  created_by       UUID REFERENCES app_user(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- MODULE : radar
-- =====================================================================
CREATE TABLE radar_trend_observation (
  id          BIGSERIAL PRIMARY KEY,
  observed_on DATE NOT NULL,
  dimension   TEXT NOT NULL,                    -- term|entity|event_type|metric
  key         TEXT NOT NULL,
  zone_id     UUID REFERENCES taxonomy_term(id),
  count       INT NOT NULL,
  UNIQUE (observed_on, dimension, key, zone_id)
);

CREATE TABLE radar_finding (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detector   TEXT NOT NULL,                     -- orphan_cluster|burst|lexical_drift|geo_lag|scout
  title      TEXT NOT NULL,
  body       TEXT NOT NULL,
  signal_ids UUID[] NOT NULL DEFAULT '{}',
  zone_from  UUID REFERENCES taxonomy_term(id),
  zone_to    UUID REFERENCES taxonomy_term(id),
  strength   NUMERIC,
  status     TEXT NOT NULL DEFAULT 'new',       -- new|promoted|dismissed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- Vues de commodité (lecture)
-- =====================================================================
CREATE VIEW v_signal_domain AS
  SELECT st.signal_id, tt.code AS domain_code, st.is_primary
  FROM signal_term st
  JOIN taxonomy_term tt ON tt.id = st.term_id
  JOIN taxonomy tx ON tx.id = tt.taxonomy_id
  WHERE tx.code = 'watch_domain';

CREATE VIEW v_calendar_upcoming AS
  SELECT m.id, m.due_on, m.precision, m.kind, m.label, e.id AS entity_id, e.kind AS entity_kind, e.label AS entity_label
  FROM entity_milestone m JOIN entity e ON e.id = m.entity_id
  WHERE m.superseded_by IS NULL AND m.due_on >= current_date;
