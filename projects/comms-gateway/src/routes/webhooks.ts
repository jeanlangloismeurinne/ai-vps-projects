import type { FastifyInstance, FastifyRequest } from "fastify";
import { config } from "../config.js";
import { q, q1 } from "../db.js";
import { logMessage, type Channel } from "../domain.js";
import { verifySvix, verifySlackSignature } from "../lib/crypto.js";

interface InboundCandRow {
  client_id: string;
  webhook_url: string | null;
  recipients: string[];
  slack_channel_ids: string[];
}

async function candidatesForChannel(channel: Channel): Promise<InboundCandRow[]> {
  return q<InboundCandRow>(
    `SELECT c.client_id, c.webhook_url, p.recipients, p.slack_channel_ids
     FROM clients c
     JOIN client_policies p ON p.client_id_ref = c.id
     WHERE c.enabled AND p.channel = $1 AND p.enabled
       AND p.action IN ('receive','both')`,
    [channel]
  );
}

// Correspondance d'une valeur (adresse/n° tel) contre la whitelist d'une policy.
// La whitelist contient des motifs : adresse exacte, ou domaine préfixé "@".
function matchesRecipients(whitelist: string[], value: string): boolean {
  const v = (value ?? "").toLowerCase();
  if (!v) return false;
  return whitelist.some((pat) => {
    const p = (pat ?? "").toLowerCase();
    if (!p) return false;
    if (p === "*") return true;
    if (p.startsWith("@")) return v.endsWith(p);
    return v === p;
  });
}

async function deliverInbound(
  channel: Channel,
  candidates: InboundCandRow[],
  from: string,
  to: string,
  subject: string,
  body: string,
  providerMessageId: string,
  raw: unknown
): Promise<void> {
  for (const c of candidates) {
    const ok =
      channel === "slack"
        ? (c.slack_channel_ids ?? []).includes(to)
        : matchesRecipients(c.recipients, from) || matchesRecipients(c.recipients, to);

    if (!ok) continue;

    await logMessage({
      clientId: c.client_id,
      channel,
      direction: "in",
      from,
      to,
      subject,
      body,
      status: "success",
      providerMessageId,
    });

    if (c.webhook_url) {
      try {
        await fetch(c.webhook_url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ channel, id: providerMessageId, from, to, subject, text: body, raw }),
        });
      } catch {
        /* la BDD garde la trace ; l'échec de push webhook n'est pas bloquant */
      }
    }
  }
}

// ----------------------------- Email entrant (Resend) -----------------------------
export async function registerWebhooks(app: FastifyInstance): Promise<void> {
  app.post("/webhooks/resend", async (request, reply) => {
    let payload: Buffer;
    try {
      const parts = [];
      for await (const chunk of request.raw) parts.push(Buffer.from(chunk));
      payload = Buffer.concat(parts);
    } catch {
      return reply.code(400).send({ error: "payload illisible" });
    }

    // Vérification de signature Svix si configurée ; sinon repli sur ?token=.
    if (config.RESEND_WEBHOOK_SECRET) {
      const signed = verifySvix(
        payload,
        request.headers as Record<string, string | string[] | undefined>,
        config.RESEND_WEBHOOK_SECRET
      );
      if (!signed) return reply.code(401).send({ error: "signature invalide" });
    } else if (config.WEBHOOK_TOKEN && !request.url.includes(`token=${config.WEBHOOK_TOKEN}`)) {
      return reply.code(401).send({ error: "token invalide" });
    }

    let data: Record<string, unknown>;
    try {
      data = JSON.parse(payload.toString("utf8"));
    } catch {
      return reply.code(400).send({ error: "json invalide" });
    }

    const messageId = String(data["Message-ID"] ?? data.message_id ?? data.id ?? "");
    const from = String(data.from ?? "");
    const to = Array.isArray(data.to) ? data.to.join(", ") : String(data.to ?? "");
    const subject = String(data.subject ?? "");
    const text = String(data.text ?? "");

    const candidates = await candidatesForChannel("email");
    await deliverInbound("email", candidates, from, to, subject, text, messageId, data);

    return reply.code(200).send({ ok: true });
  });

  // ----------------------------- Slack entrant (HTTP Events API) -----------------------------
  app.post("/webhooks/slack", async (request, reply) => {
    let rawBody = "";
    const parts = [];
    for await (const chunk of request.raw) parts.push(Buffer.from(chunk));
    rawBody = Buffer.concat(parts).toString("utf8");

    if (!verifySlackSignature(rawBody, request.headers, config.SLACK_SIGNING_SECRET)) {
      return reply.code(401).send({ error: "signature slack invalide" });
    }

    let data: Record<string, unknown>;
    try {
      data = JSON.parse(rawBody);
    } catch {
      return reply.code(400).send({ error: "json invalide" });
    }

    // Handshake URL verification
    if (data.type === "url_verification") {
      return reply.code(200).send({ challenge: data.challenge });
    }

    const event = (data.event ?? {}) as Record<string, unknown>;
    // On ne traite que les messages texte émis par des humains (pas les messages du bot)
    if (data.type === "event_callback" && event.type === "message" && event.subtype !== "bot_message") {
      const channel = String(event.channel ?? "");
      const text = String(event.text ?? "");
      const user = String(event.user ?? "");
      const ts = String(event.ts ?? "");

      const candidates = await candidatesForChannel("slack");
      await deliverInbound("slack", candidates, user, channel, "", text, ts, data);
    }

    return reply.code(200).send({ ok: true });
  });

  // Healthcheck public
  app.get("/health", async (_request, reply) => reply.send({ status: "ok" }));
}
