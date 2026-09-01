import type { FastifyInstance, FastifyRequest } from "fastify";
import { config } from "../config.js";
import { authenticate } from "./auth.js";

const RESEND_INBOUND_ENDPOINT = "https://api.resend.com/emails/inbound";

// Endpoint = retour d'un mail entrant reçu par Resend.
// Contexte : le webhook Resend (`email.received`) ne livre QUE des métadonnées
// (pas de text/html). Pour résumer la newsletter, le client doit rapatrier le corps
// via l'API Received-emails de Resend. La clé Resend reste au gateway : on proxy ici.
export async function registerInboundRoute(app: FastifyInstance): Promise<void> {
  app.get<{ Params: { id: string } }>(
    "/v1/inbound/email/:id",
    async (request, reply) => {
      const client = await authenticate(app, request);
      if (!client) {
        return reply.code(401).send({ error: "authentification requise" });
      }

      const { id } = request.params;
      if (!id) {
        return reply.code(400).send({ error: "`id` (email_id) requis" });
      }

      const apiKey = config.RESEND_API_KEY;
      if (!apiKey) {
        return reply.code(503).send({ error: "RESEND_API_KEY absente (gateway non configuré)" });
      }

      let res: Response;
      try {
        res = await fetch(`${RESEND_INBOUND_ENDPOINT}/${encodeURIComponent(id)}`, {
          headers: { Authorization: `Bearer ${apiKey}` },
        });
      } catch {
        return reply.code(502).send({ error: "échec réseau vers l'API Resend" });
      }

      if (res.status === 404) {
        return reply.code(404).send({ error: "email entrant introuvable" });
      }
      if (res.status >= 400) {
        const t = await res.text();
        return reply.code(502).send({ error: `Resend HTTP ${res.status}: ${t.slice(0, 300)}` });
      }

      const full = (await res.json()) as Record<string, unknown>;
      // On ne renvoie que ce qui sert au résumé + métadonnées utiles.
      const pick = [
        "id", "created_at", "from", "subject", "to", "message_id",
        "received_for", "text", "html", "headers", "attachments",
      ];
      const out: Record<string, unknown> = {};
      for (const k of pick) out[k] = full[k];
      return reply.send(out);
    }
  );
}
