import type { FastifyInstance, FastifyRequest } from "fastify";
import { listMessages } from "../domain.js";
import { authenticate } from "./auth.js";

export async function registerMessagesRoute(app: FastifyInstance): Promise<void> {
  // Historique strictement borné aux messages du client authentifié (audit/debug).
  app.get<{ Querystring: { limit?: string; after?: string } }>(
    "/v1/messages",
    async (request, reply) => {
      const client = await authenticate(app, request);
      if (!client) {
        return reply.code(401).send({ error: "authentification requise" });
      }
      const limit = Math.min(Number(request.query.limit ?? 100) || 100, 500);
      const after = request.query.after ? Number(request.query.after) : undefined;
      const rows = await listMessages(client.client_id, limit, after);
      return reply.send({ rows });
    }
  );
}
