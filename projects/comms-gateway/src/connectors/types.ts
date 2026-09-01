import type { Channel, PolicyWithAccount } from "../domain.js";

export interface Attachment {
  filename?: string;
  contentType?: string;
  /** base64 */
  data?: string;
  href?: string;
}

export interface SendOptions {
  to: string;
  subject?: string | null;
  /** Corps texte brut — utilisé comme `text`/fallback chez le provider. */
  body?: string | null;
  /** Corps HTML (email) — envoyé tel quel chez Resend, `text` reste le fallback. */
  html?: string | null;
  attachments?: Attachment[];
}

export interface SendResult {
  ok: boolean;
  providerMessageId?: string | null;
  error?: string | null;
}

/**
 * Un connecteur encapsule UN provider externe derrière une interface uniforme.
 * Le gateway est le seul composant qui possède les secrets du provider (=creds).
 */
export interface Connector {
  readonly channel: Channel;
  /** Credentials effectifs pour ce provider (env du gateway ou compte chiffré en BDD). */
  resolveCreds(policy: PolicyWithAccount): Promise<Record<string, unknown>>;
  /** Adresse/identité de départ effective (surcharge par compte > policy > env). */
  resolveFrom(policy: PolicyWithAccount): string;
  send(opts: SendOptions, creds: Record<string, unknown>, from: string): Promise<SendResult>;
}
