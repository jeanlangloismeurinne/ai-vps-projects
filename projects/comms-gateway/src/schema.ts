import { pool, q1 } from "./db.js";

// Schéma de la base `db_comms_gateway` (créée une fois via psql — cf. README).
// Idempotent : peut être relancé à chaque démarrage (CREATE ... IF NOT EXISTS).
const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS provider_accounts (
  id            SERIAL PRIMARY KEY,
  type          TEXT NOT NULL CHECK (type IN ('resend','slack','sms','whatsapp','signal')),
  label         TEXT NOT NULL UNIQUE,
  default_from  TEXT,
  creds         TEXT NOT NULL DEFAULT '',        -- JSON chiffré AES-GCM (MASTER_KEY)
  enabled       BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clients (
  id            SERIAL PRIMARY KEY,
  client_id     TEXT NOT NULL UNIQUE,
  name          TEXT,
  token_hash    TEXT NOT NULL,
  webhook_url   TEXT,
  enabled       BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS client_policies (
  id                  SERIAL PRIMARY KEY,
  client_id_ref       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  channel             TEXT NOT NULL CHECK (channel IN ('email','sms','whatsapp','signal','slack')),
  action              TEXT NOT NULL DEFAULT 'both' CHECK (action IN ('send','receive','both')),
  provider_account_id INTEGER REFERENCES provider_accounts(id),
  default_from        TEXT,
  rate_limit_per_day  INTEGER NOT NULL DEFAULT 50,
  recipients          JSONB NOT NULL DEFAULT '[]'::jsonb,
  slack_channel_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,
  enabled             BOOLEAN NOT NULL DEFAULT true,
  UNIQUE (client_id_ref, channel)
);

-- Journal d'audit append-only : jamais de DELETE applicatif.
CREATE TABLE IF NOT EXISTS messages (
  id                  BIGSERIAL PRIMARY KEY,
  client_id           TEXT NOT NULL,
  channel             TEXT NOT NULL,
  direction           TEXT NOT NULL CHECK (direction IN ('in','out')),
  from_addr           TEXT,
  to_addr             TEXT,
  subject             TEXT,
  body_txt            TEXT,
  status              TEXT NOT NULL,   -- success | failure | rejected_policy | rejected_rate_limit
  reason              TEXT,
  provider_message_id TEXT,
  ts                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_client ON messages (client_id, ts DESC);
`;

type AccountsSeeds = Array<{
  type: string;
  label: string;
  default_from: string;
}>;

export async function ensureSchema(accountSeeds: AccountsSeeds = []): Promise<void> {
  await pool.query(SCHEMA_SQL);

  for (const a of accountSeeds) {
    const exists = await q1<{ id: number }>(
      "SELECT id FROM provider_accounts WHERE label = $1",
      [a.label]
    );
    if (exists) continue;
    await pool.query(
      `INSERT INTO provider_accounts (type, label, default_from)
       VALUES ($1, $2, $3)`,
      [a.type, a.label, a.default_from]
    );
  }
}
