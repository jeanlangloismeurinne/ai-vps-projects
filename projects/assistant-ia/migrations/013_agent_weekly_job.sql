-- Migration 013 — agent-consignes : journal des exécutions du job hebdomadaire
-- Idempotent : safe to run on every startup (CREATE … IF NOT EXISTS)
-- Garantit un seul déclenchement par semaine même si le worker redémarre :
-- INSERT … ON CONFLICT DO NOTHING sur la contrainte UNIQUE (job_name, iso_week).

CREATE TABLE IF NOT EXISTS agent_weekly_job_log (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name   VARCHAR(64) NOT NULL,          -- nom du job (ex: 'agent_synthesis')
  iso_week   VARCHAR(8)  NOT NULL,          -- format 'YYYY-WNN' (ISO 8601)
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (job_name, iso_week)
);

CREATE INDEX IF NOT EXISTS idx_agent_weekly_job_log_name_week
  ON agent_weekly_job_log (job_name, iso_week);
