import type { FastifyInstance, FastifyRequest } from "fastify";
import type { ClientRow, Channel } from "../domain.js";
import { clientByToken } from "../domain.js";

// Récupère le client authentifié depuis le header `Authorization: Bearer <token>`.
export async function authenticate(
  app: FastifyInstance,
  request: FastifyRequest
): Promise<ClientRow | null> {
  const header = request.headers.authorization ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  const client = await clientByToken(token);
  if (!client || !client.enabled) return null;
  return client;
}

export type SendBody = {
  channel: Channel;
  to: string;
  subject?: string | null;
  body?: string | null;
  /** Corps HTML (email) — transmis au provider en plus du `text` (fallback). */
  html?: string | null;
  attachments?: Array<{ filename?: string; contentType?: string; data?: string }>;
};
