-- Migration 020 — Toggle mode automatique Dust
-- Ajoute dust_auto_enabled à portfolio_settings (défaut TRUE = comportement actuel inchangé)

ALTER TABLE portfolio_settings
  ADD COLUMN IF NOT EXISTS dust_auto_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- Ajoute 'pending_manual' comme statut valide dans monitoring_sessions
-- (TEXT, pas d'ENUM — aucune contrainte à modifier, le statut est libre)
COMMENT ON COLUMN monitoring_sessions.status IS
  'pending | running | completed | blocked_sync | pending_manual | archived';
