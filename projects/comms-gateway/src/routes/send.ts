import type { FastifyInstance, FastifyRequest } from "fastify";
import {
  clientByToken,
  policyFor,
  logMessage,
} from "../domain.js";
import { checkRateLimit } from "../lib/rateLimit.js";
import { resolveChannel } from "../connectors/index.js";
import { authenticate, type SendBody } from "./auth.js";

type SendReply =
  | { status: "sent"; provider_message_id?: string | null; used?: number }
  | { status: "rejected"; reason: string };

export async function registerSendRoute(app: FastifyInstance): Promise<void> {
  app.post<{ Body: SendBody }>("/v1/send", async (request, reply): Promise<SendReply> => {
    const client = await authenticate(app, request);
    if (!client) {
      return reply.code(401).send({ error: "authentification requise (client inconnu ou désactivé)" }) as unknown as SendReply;
    }

    const { channel, to, subject, body, attachments } = request.body ?? {};
    if (!channel || !to) {
      return reply.code(400).send({ error: "`channel` et `to` requis" }) as unknown as SendReply;
    }

    const policy = await policyFor(client.id, channel);
    if (!policy || !policy.enabled) {
      await logMessage({
        clientId: client.client_id,
        channel,
        direction: "out",
        to,
        subject,
        body,
        status: "rejected_policy",
        reason: "aucune policy active sur ce canal",
      });
      return { status: "rejected", reason: `canal ${channel} non autorisé pour ce client` };
    }
    if (policy.action !== "send" && policy.action !== "both") {
      await logMessage({
        clientId: client.client_id,
        channel,
        direction: "out",
        to,
        subject,
        body,
        status: "rejected_policy",
        reason: "action d'envoi non autorisée",
      });
      return { status: "rejected", reason: "envoi non autorisé sur ce canal" };
    }

    // Rate limit quotidien (shared-redis)
    const rl = await checkRateLimit(client.client_id, channel, policy.rate_limit_per_day);
    if (!rl.allowed) {
      await logMessage({
        clientId: client.client_id,
        channel,
        direction: "out",
        to,
        subject,
        body,
        status: "rejected_rate_limit",
        reason: `quota quotidien dépassé (${policy.rate_limit_per_day}/jour)`,
      });
      return {
        status: "rejected",
        reason: `rate limit dépassé (${rl.used}/${policy.rate_limit_per_day})`,
      };
    }

    // Envoi effectif via le connecteur du canal
    const { connector, creds, from } = await resolveChannel(policy);
    const result = await connector.send({ to, subject, body, attachments }, creds, from);

    if (!result.ok) {
      await logMessage({
        clientId: client.client_id,
        channel,
        direction: "out",
        to,
        subject,
        body,
        status: "failure",
        reason: result.error ?? "échec inconnu",
      });
      return reply
        .code(502)
        .send({ status: "rejected", reason: `échec ${channel}: ${result.error}` }) as unknown as SendReply;
    }

    await logMessage({
      clientId: client.client_id,
      channel,
      direction: "out",
      to,
      subject,
      body,
      status: "success",
      providerMessageId: result.providerMessageId,
    });
    return { status: "sent", provider_message_id: result.providerMessageId, used: rl.used };
  });
}
