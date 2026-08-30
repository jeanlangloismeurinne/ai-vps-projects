import { hashToken } from "./lib/crypto.js";
import { q, q1, pool } from "./db.js";

export type Channel =
  | "email"
  | "sms"
  | "whatsapp"
  | "signal"
  | "slack";

export type Direction = "in" | "out";
export type MessageStatus =
  | "success"
  | "failure"
  | "rejected_policy"
  | "rejected_rate_limit";

export interface ClientRow {
  id: number;
  client_id: string;
  name: string | null;
  token_hash: string;
  webhook_url: string | null;
  enabled: boolean;
}

export interface PolicyRow {
  id: number;
  client_id_ref: number;
  channel: Channel;
  action: "send" | "receive" | "both";
  provider_account_id: number | null;
  default_from: string | null;
  rate_limit_per_day: number;
  recipients: string[];
  slack_channel_ids: string[];
  enabled: boolean;
}

export interface PolicyWithAccount extends PolicyRow {
  account_type: string | null;
  account_label: string | null;
  account_default_from: string | null;
}

export interface AccountRow {
  id: number;
  type: string;
  label: string;
  default_from: string | null;
  creds: string;
  enabled: boolean;
}

// ----------------------------- Clients -----------------------------

export async function clientByToken(rawToken: string): Promise<ClientRow | undefined> {
  if (!rawToken) return undefined;
  return q1<ClientRow>(
    "SELECT * FROM clients WHERE token_hash = $1 AND enabled = true",
    [hashToken(rawToken)]
  );
}

export async function clientByIdStr(clientId: string): Promise<ClientRow | undefined> {
  return q1<ClientRow>("SELECT * FROM clients WHERE client_id = $1", [clientId]);
}

export async function createClient(
  clientId: string,
  name: string,
  rawToken: string,
  webhookUrl: string | null
): Promise<ClientRow> {
  const rows = await q<ClientRow>(
    `INSERT INTO clients (client_id, name, token_hash, webhook_url)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (client_id) DO UPDATE
       SET name = EXCLUDED.name,
           webhook_url = EXCLUDED.webhook_url,
           token_hash = EXCLUDED.token_hash,
           enabled = true
     RETURNING *`,
    [clientId, name, hashToken(rawToken), webhookUrl]
  );
  return rows[0]!;
}

export async function setClientEnabled(clientId: string, enabled: boolean): Promise<boolean> {
  const res = await pool.query(
    "UPDATE clients SET enabled = $2 WHERE client_id = $1",
    [clientId, enabled]
  );
  return (res.rowCount ?? 0) > 0;
}

// ----------------------------- Policies -----------------------------

export async function policyFor(
  clientRef: number,
  channel: Channel
): Promise<PolicyWithAccount | undefined> {
  return q1<PolicyWithAccount>(
    `SELECT
       p.id, p.client_id_ref, p.channel, p.action, p.provider_account_id,
       p.default_from, p.rate_limit_per_day, p.recipients, p.slack_channel_ids,
       p.enabled,
       a.type AS account_type, a.label AS account_label, a.default_from AS account_default_from
     FROM client_policies p
     LEFT JOIN provider_accounts a ON a.id = p.provider_account_id
     WHERE p.client_id_ref = $1 AND p.channel = $2`,
    [clientRef, channel]
  );
}

export async function policiesForClient(clientRef: number): Promise<PolicyRow[]> {
  return q<PolicyRow>("SELECT * FROM client_policies WHERE client_id_ref = $1", [clientRef]);
}

export async function upsertPolicy(p: {
  clientRef: number;
  channel: Channel;
  action: "send" | "receive" | "both";
  providerAccountId?: number | null;
  defaultFrom?: string | null;
  rateLimitPerDay: number;
  recipients: string[];
  slackChannelIds: string[];
  enabled: boolean;
}): Promise<void> {
  await q(
    `INSERT INTO client_policies
       (client_id_ref, channel, action, provider_account_id, default_from,
        rate_limit_per_day, recipients, slack_channel_ids, enabled)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
     ON CONFLICT (client_id_ref, channel) DO UPDATE
       SET action = EXCLUDED.action,
           provider_account_id = EXCLUDED.provider_account_id,
           default_from = EXCLUDED.default_from,
           rate_limit_per_day = EXCLUDED.rate_limit_per_day,
           recipients = EXCLUDED.recipients,
           slack_channel_ids = EXCLUDED.slack_channel_ids,
           enabled = EXCLUDED.enabled`,
    [
      p.clientRef,
      p.channel,
      p.action,
      p.providerAccountId ?? null,
      p.defaultFrom ?? null,
      p.rateLimitPerDay,
      JSON.stringify(p.recipients),
      JSON.stringify(p.slackChannelIds),
      p.enabled,
    ]
  );
}

export async function setPolicyEnabled(
  clientRef: number,
  channel: Channel,
  enabled: boolean
): Promise<void> {
  await q(
    "UPDATE client_policies SET enabled = $3 WHERE client_id_ref = $1 AND channel = $2",
    [clientRef, channel, enabled]
  );
}

// ----------------------------- Comptes -----------------------------

export async function accountById(id: number): Promise<AccountRow | undefined> {
  return q1<AccountRow>("SELECT * FROM provider_accounts WHERE id = $1", [id]);
}

export async function accountByLabel(label: string): Promise<AccountRow | undefined> {
  return q1<AccountRow>("SELECT * FROM provider_accounts WHERE label = $1", [label]);
}

export async function listAccounts(): Promise<AccountRow[]> {
  return q<AccountRow>("SELECT * FROM provider_accounts ORDER BY type, label");
}

export async function createAccount(
  type: string,
  label: string,
  defaultFrom: string | null,
  creds: string
): Promise<number> {
  const rows = await q<{ id: number }>(
    `INSERT INTO provider_accounts (type, label, default_from, creds)
     VALUES ($1,$2,$3,$4)
     ON CONFLICT (label) DO UPDATE
       SET default_from = EXCLUDED.default_from, creds = EXCLUDED.creds
     RETURNING id`,
    [type, label, defaultFrom, creds]
  );
  return rows[0]!.id;
}

export async function setAccountEnabled(id: number, enabled: boolean): Promise<void> {
  await q("UPDATE provider_accounts SET enabled = $2 WHERE id = $1", [id, enabled]);
}

// ----------------------------- Journal (append-only) -----------------------------

export interface MessageRow {
  id: string;
  client_id: string;
  channel: string;
  direction: Direction;
  from_addr: string | null;
  to_addr: string | null;
  subject: string | null;
  body_txt: string | null;
  status: MessageStatus;
  reason: string | null;
  provider_message_id: string | null;
  ts: Date;
}

export async function logMessage(m: {
  clientId: string;
  channel: Channel;
  direction: Direction;
  from?: string | null;
  to?: string | null;
  subject?: string | null;
  body?: string | null;
  status: MessageStatus;
  reason?: string | null;
  providerMessageId?: string | null;
}): Promise<void> {
  await q(
    `INSERT INTO messages
       (client_id, channel, direction, from_addr, to_addr, subject, body_txt,
        status, reason, provider_message_id)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
    [
      m.clientId,
      m.channel,
      m.direction,
      m.from ?? null,
      m.to ?? null,
      m.subject ?? null,
      m.body ?? null,
      m.status,
      m.reason ?? null,
      m.providerMessageId ?? null,
    ]
  );
}

export async function listMessages(
  clientId: string,
  limit = 100,
  after?: number
): Promise<MessageRow[]> {
  if (after) {
    return q<MessageRow>(
      `SELECT * FROM messages WHERE client_id = $1 AND id < $2
       ORDER BY id DESC LIMIT $3`,
      [clientId, after, limit]
    );
  }
  return q<MessageRow>(
    `SELECT * FROM messages WHERE client_id = $1 ORDER BY id DESC LIMIT $2`,
    [clientId, limit]
  );
}
