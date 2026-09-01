import type { PolicyWithAccount } from "../domain.js";
import { config } from "../config.js";
import { decryptCreds } from "../lib/crypto.js";
import type { Connector, SendOptions, SendResult } from "./types.js";

const RESEND_ENDPOINT = "https://api.resend.com/emails";

export class EmailConnector implements Connector {
  readonly channel = "email" as const;

  async resolveCreds(policy: PolicyWithAccount): Promise<Record<string, unknown>> {
    // Compte dédié (chiffré en BDD) s'il porte une clé, sinon la clé env du gateway.
    if (policy.account_label) {
      // account creds sont résolues par le registry ; on y accède via l'account déjà chargé
      return {};
    }
    return { apiKey: config.RESEND_API_KEY };
  }

  resolveFrom(policy: PolicyWithAccount): string {
    return (
      policy.account_default_from ?? policy.default_from ?? config.RESEND_DEFAULT_FROM ?? ""
    );
  }

  async send(opts: SendOptions, creds: Record<string, unknown>, from: string): Promise<SendResult> {
    const apiKey = String(creds.apiKey ?? config.RESEND_API_KEY ?? "");
    if (!apiKey) {
      return { ok: false, error: "RESEND_API_KEY absente (gateway non configuré)" };
    }

    // Mode développement Resend (TEMPORAIRE) : tant qu'aucun domaine d'envoi n'est
    // vérifié, resend.dev n'est livrable que sur l'adresse du compte Resend. On écrase
    // `from` et `to` quoi que demande le client. Retirer dès qu'un domaine est vérifié.
    const devMode = config.RESEND_DEV_MODE === "1" || config.RESEND_DEV_MODE === "true";
    let toAddr = opts.to;
    if (devMode) {
      from = "onboarding@resend.dev";
      toAddr = config.RESEND_DEV_TO || opts.to;
    }

    if (!toAddr || !from) {
      return { ok: false, error: "`to` et `from` requis pour l'email" };
    }
    const payload: Record<string, unknown> = {
      from,
      to: [toAddr],
      subject: opts.subject ?? "",
    };
    if (opts.body) payload.text = opts.body;
    if (opts.html) payload.html = opts.html;
    if (opts.attachments?.length) {
      payload.attachments = opts.attachments
        .filter((a) => a.data)
        .map((a) => ({ filename: a.filename, content: a.data }));
    }

    const res = await fetch(RESEND_ENDPOINT, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    if (res.status >= 300) {
      return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 300)}` };
    }
    let id: string | null = null;
    try {
      id = JSON.parse(text).id ?? null;
    } catch {
      /* ignore */
    }
    return { ok: true, providerMessageId: id };
  }
}

// Helper utilisé par le registry pour déchiffrer les creds d'un compte Resend
export function emailCredsFromAccount(credsPayload: string): Record<string, unknown> {
  if (!credsPayload) return {};
  try {
    return decryptCreds(credsPayload);
  } catch {
    return {};
  }
}
