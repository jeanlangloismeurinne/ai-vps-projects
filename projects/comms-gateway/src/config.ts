// Chargement centralisé des variables d'environnement, sans lib externe.
// Les secrets proviennent des secrets Coolify du service comms-gateway (env).
const env = process.env;

export const config = {
  DATABASE_URL: env.DATABASE_URL ?? "",
  REDIS_URL: env.REDIS_URL ?? "redis://localhost:6379/0",

  // Secret maître : chiffre les credentials providers stockés en BDD (provider_accounts).
  // 32 octets base64 → openssl rand -base64 32
  MASTER_KEY: env.MASTER_KEY ?? "",

  // Token admin protégeant POST/PATCH /v1/admin/* (onboarding, coupure à chaud)
  ADMIN_TOKEN: env.ADMIN_TOKEN ?? "",

  // --- Email (Resend) ---
  RESEND_API_KEY: env.RESEND_API_KEY ?? "",
  RESEND_DEFAULT_FROM: env.RESEND_DEFAULT_FROM ?? "",
  RESEND_WEBHOOK_SECRET: env.RESEND_WEBHOOK_SECRET ?? "",
  WEBHOOK_TOKEN: env.WEBHOOK_TOKEN ?? "",

  // --- Slack (bot PROPRE au gateway, distinct d'assistant-ia) ---
  SLACK_BOT_TOKEN: env.SLACK_BOT_TOKEN ?? "",
  SLACK_SIGNING_SECRET: env.SLACK_SIGNING_SECRET ?? "",

  // URL publique du gateway (base utilisée pour composer les URLs de webhook)
  PUBLIC_BASE_URL: env.PUBLIC_BASE_URL ?? "https://comms.jlmvpscode.duckdns.org",

  // Hook technique : limites de l'API (octets)
  MAX_BODY_BYTES: 1_000_000,
  PORT: Number(env.PORT ?? 8000),
  HOST: env.HOST ?? "0.0.0.0",
} as const;

export function assertConfig(keys: string[]): void {
  const missing = keys.filter((k) => !(env[k] ?? ""));
  if (missing.length > 0) {
    throw new Error(`Variables manquantes : ${missing.join(", ")}`);
  }
}
