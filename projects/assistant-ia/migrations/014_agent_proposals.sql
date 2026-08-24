-- Migration 014 — propositions de révision du doc système (#1787559677495 / #1787559677496)
-- Idempotent : rejouée à chaque démarrage par app/db.py.
--
-- Pourquoi une table dédiée plutôt que agent_audit_log :
--   agent_audit_log est immuable et ne porte que le *diff*. Pour appliquer une proposition il faut
--   conserver le **texte complet** proposé, et pour garantir l'idempotence il faut un **statut**
--   mutable (une proposition se tranche une seule fois). Ces deux besoins sont incompatibles avec
--   une table append-only : ils vivent donc ici, l'audit restant la trace immuable de ce qui s'est
--   passé.

CREATE TABLE IF NOT EXISTS agent_proposals (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  content         TEXT        NOT NULL,   -- texte complet de la version proposée
  diff            TEXT        NOT NULL,   -- diff unifié calculé par difflib (jamais par le modèle)
  from_version    INTEGER,                -- version active au moment de la proposition
  to_version      INTEGER,                -- renseignée seulement si approuvée
  instruction_ids UUID[]      NOT NULL DEFAULT '{}',
  status          VARCHAR(16) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
  triggered_by    VARCHAR(32),            -- 'slack_update' | 'weekly_job' | 'manual'
  channel_id      VARCHAR(32),
  slack_ts        VARCHAR(32),            -- message d'approbation dans #feedback-assistant
  decided_by      VARCHAR(64),
  decided_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_proposals_status
  ON agent_proposals (status, created_at DESC);

-- Une seule proposition en attente à la fois : deux propositions concurrentes porteraient sur la
-- même version de base et la seconde écraserait silencieusement la première à l'approbation.
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_proposals_single_pending
  ON agent_proposals ((status)) WHERE status = 'pending';
