import type { FastifyInstance, FastifyRequest } from "fastify";
import { config } from "../config.js";
import {
  createClient,
  listAccounts,
  accountByLabel,
  createAccount,
  setAccountEnabled,
  setClientEnabled,
  setPolicyEnabled,
  upsertPolicy,
  clientByIdStr,
  listMessages,
  type Channel,
} from "../domain.js";
import { encryptCreds } from "../lib/crypto.js";
import { generateToken } from "../lib/crypto.js";

function requireAdmin(app: FastifyInstance, request: FastifyRequest): boolean {
  const header = request.headers.authorization ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  return config.ADMIN_TOKEN !== "" && token === config.ADMIN_TOKEN;
}

interface PolicyInput {
  channel: Channel;
  action?: "send" | "receive" | "both";
  provider_account_id?: number | null;
  default_from?: string | null;
  rate_limit_per_day?: number;
  recipients?: string[];
  slack_channel_ids?: string[];
  enabled?: boolean;
}

export async function registerAdminRoutes(app: FastifyInstance): Promise<void> {
  // --- Onboarding d'un client. Renvoie le token EN CLAIR une seule fois. ---
  app.post<{ Body: { client_id: string; name?: string; webhook_url?: string | null; policies?: PolicyInput[] } }>(
    "/v1/admin/clients",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const { client_id, name, webhook_url, policies } = request.body ?? {};
      if (!client_id) return reply.code(400).send({ error: "client_id requis" });

      const token = generateToken();
      const client = await createClient(client_id, name ?? client_id, token, webhook_url ?? null);

      for (const p of policies ?? []) {
        await upsertPolicy({
          clientRef: client.id,
          channel: p.channel,
          action: p.action ?? "both",
          providerAccountId: p.provider_account_id ?? null,
          defaultFrom: p.default_from ?? null,
          rateLimitPerDay: p.rate_limit_per_day ?? 50,
          recipients: p.recipients ?? [],
          slackChannelIds: p.slack_channel_ids ?? [],
          enabled: p.enabled ?? true,
        });
      }
      return reply.send({ client_id, token, note: "token renvoyé une seule fois — stockez-le en secret du service" });
    }
  );

  // --- Coupure à chaud (effet immédiat, sans redéploiement) ---
  app.patch<{ Params: { id: string }; Body: { enabled: boolean } }>(
    "/v1/admin/clients/:id/status",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const enabled = request.body?.enabled;
      if (typeof enabled !== "boolean") return reply.code(400).send({ error: "enabled booléen requis" });
      const ok = await setClientEnabled(request.params.id, enabled);
      return reply.send({ ok });
    }
  );

  // --- Policy par canal (ajout / mise à jour) ---
  app.put<{ Params: { id: string; channel: Channel }; Body: PolicyInput }>(
    "/v1/admin/clients/:id/policies/:channel",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const client = await clientByIdStr(request.params.id);
      if (!client) return reply.code(404).send({ error: "client inconnu" });
      const b = request.body ?? {};
      await upsertPolicy({
        clientRef: client.id,
        channel: request.params.channel,
        action: b.action ?? "both",
        providerAccountId: b.provider_account_id ?? null,
        defaultFrom: b.default_from ?? null,
        rateLimitPerDay: b.rate_limit_per_day ?? 50,
        recipients: b.recipients ?? [],
        slackChannelIds: b.slack_channel_ids ?? [],
        enabled: b.enabled ?? true,
      });
      return reply.send({ ok: true });
    }
  );

  // --- Désactivation immédiate d'un canal ---
  app.patch<{ Params: { id: string; channel: Channel }; Body: { enabled: boolean } }>(
    "/v1/admin/clients/:id/policies/:channel/status",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const client = await clientByIdStr(request.params.id);
      if (!client) return reply.code(404).send({ error: "client inconnu" });
      await setPolicyEnabled(client.id, request.params.channel, request.body?.enabled ?? true);
      return reply.send({ ok: true });
    }
  );

  // --- Comptes fournisseurs (multi-account : plusieurs clés Resend / apps Slack) ---
  app.post<{ Body: { type: string; label: string; default_from?: string | null; creds?: Record<string, unknown> } }>(
    "/v1/admin/accounts",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const { type, label, default_from, creds } = request.body ?? {};
      if (!type || !label) return reply.code(400).send({ error: "type et label requis" });
      const credsPayload = creds && Object.keys(creds).length ? encryptCreds(creds) : "";
      const id = await createAccount(type, label, default_from ?? null, credsPayload);
      return reply.send({ id, ok: true });
    }
  );

  app.patch<{ Params: { id: string }; Body: { enabled: boolean } }>(
    "/v1/admin/accounts/:id/status",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      await setAccountEnabled(Number(request.params.id), request.body?.enabled ?? true);
      return reply.send({ ok: true });
    }
  );

  app.get("/v1/admin/accounts", async (request, reply) => {
    if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
    // Ne JAMAIS renvoyer les creds en clair : seule la présence est indiquée.
    const accounts = await listAccounts();
    return reply.send({ accounts: accounts.map((a) => ({ ...a, creds: a.creds ? "<encrypted>" : "" })) });
  });

  // --- Audit d'un client (admin) ---
  app.get<{ Params: { id: string }; Querystring: { limit?: string } }>(
    "/v1/admin/clients/:id/messages",
    async (request, reply) => {
      if (!requireAdmin(app, request)) return reply.code(401).send({ error: "admin requis" });
      const limit = Math.min(Number(request.query.limit ?? 100) || 100, 500);
      const rows = await listMessages(request.params.id, limit);
      return reply.send({ rows });
    }
  );
}
