-- Migration 011 — agent-consignes : tables de l'agent conversationnel
-- Idempotent : safe to run on every startup (CREATE … IF NOT EXISTS)
-- Ne jamais modifier les migrations 001–008 existantes.
-- 009 et 010 sont réservés au chantier journal-kb.

-- ─────────────────────────────────────────────
-- 1. agent_conversations — historique des tours
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_conversations (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  slack_ts   VARCHAR(32),
  thread_ts  VARCHAR(32),
  channel_id VARCHAR(32),
  user_id    VARCHAR(32),
  role       VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
  content    TEXT        NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_thread
  ON agent_conversations (thread_ts, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_channel
  ON agent_conversations (channel_id, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. agent_instruction_queue — consignes @admin en attente d'approbation
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_instruction_queue (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  slack_ts    VARCHAR(32),
  user_id     VARCHAR(32),
  content     TEXT        NOT NULL,   -- verbatim de la consigne soumise
  status      VARCHAR(16) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'proposed', 'approved', 'rejected')),
  proposal_id UUID,                   -- référence vers agent_audit_log si proposal générée
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_instruction_queue_status
  ON agent_instruction_queue (status, created_at DESC);

-- ──────────────────────────────────────────────────────────────────────────
-- 3. agent_system_doc — « fichier système » versionné (append-only)
--
--    Chaque nouvelle version est une NOUVELLE ligne ; on ne modifie jamais
--    une ligne existante. C'est ce qui rend le rollback possible :
--    on réactive l'ancienne version en passant active = true sur cette ligne
--    et active = false sur la version courante.
--
--    Contrainte d'unicité : l'index unique partiel garantit qu'une seule
--    ligne peut avoir active = true à la fois.
--
--    agent_system_doc.version est UNIQUE (contrainte déclarative).
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_system_doc (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  version        INTEGER     NOT NULL,  -- croissant, unique — ne jamais UPDATE
  content        TEXT        NOT NULL,  -- prompt système complet
  active         BOOLEAN     NOT NULL DEFAULT false,
  created_by     VARCHAR(64),           -- user_id ou 'system'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  parent_version INTEGER               -- version dont est issue cette révision
);

-- version doit être unique (chaque entrée append-only a son propre numéro)
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_system_doc_version
  ON agent_system_doc (version);

-- Une seule ligne active à la fois (index unique partiel sur les lignes WHERE active)
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_system_doc_active
  ON agent_system_doc (active) WHERE active;

-- ──────────────────────────────────────────────────────────────────────────
-- 4. agent_audit_log — trace immuable des opérations sur le système doc
--
--    IMPORTANT : cette table est append-only.
--    Jamais d'UPDATE ni de DELETE — ni depuis le code, ni manuellement.
--    Toute correction passe par un nouvel événement de type 'edited' ou
--    'rollback'.
-- ──────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_audit_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  event           VARCHAR(16) NOT NULL
                    CHECK (event IN ('proposed', 'approved', 'rejected', 'edited', 'rollback')),
  actor           VARCHAR(64),          -- user_id ou 'system'
  instruction_ids UUID[],               -- IDs de agent_instruction_queue concernés
  diff            TEXT,                 -- diff textuel ou description du changement
  from_version    INTEGER,              -- version source (NULL pour 'proposed' initial)
  to_version      INTEGER,              -- version cible (NULL si rejeté)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_audit_log_event
  ON agent_audit_log (event, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_audit_log_versions
  ON agent_audit_log (from_version, to_version);

-- ──────────────────────────────────────────────────────────────────────────
-- 5. Ligne initiale agent_system_doc (version 1, active = true)
--
--    Idempotente : ON CONFLICT DO NOTHING sur la contrainte uq_agent_system_doc_version
--    garantit que la ligne n'est insérée qu'une seule fois, même si la
--    migration est rejouée à chaque démarrage.
-- ──────────────────────────────────────────────────────────────────────────
INSERT INTO agent_system_doc (version, content, active, created_by, parent_version)
VALUES (
  1,
  'Tu es un assistant personnel francophone, factuel et concis. '
  'Tu réponds aux questions de l''utilisateur de façon claire et directe. '
  'Tu n''exécutes aucune action et ne disposes d''aucun outil. '
  'Si l''on te demande d''exécuter du code, de lancer un programme ou '
  'd''effectuer une action système, explique que tu n''en as pas la capacité '
  'et oriente l''utilisateur vers la commande `/feature` pour soumettre '
  'cette demande en tant que fonctionnalité.',
  true,
  'system',
  NULL
)
ON CONFLICT (version) DO NOTHING;
