import type { Channel, PolicyWithAccount } from "../domain.js";
import { accountById } from "../domain.js";
import type { Connector } from "./types.js";
import { EmailConnector, emailCredsFromAccount } from "./email.js";
import { SlackConnector } from "./slack.js";
import { MockConnector } from "./mock.js";

const email = new EmailConnector();
const slack = new SlackConnector();
const mocks: Record<"sms" | "whatsapp" | "signal", MockConnector> = {
  sms: new MockConnector("sms"),
  whatsapp: new MockConnector("whatsapp"),
  signal: new MockConnector("signal"),
};

function connectorFor(channel: Channel): Connector {
  switch (channel) {
    case "email":
      return email;
    case "slack":
      return slack;
    case "sms":
      return mocks.sms;
    case "whatsapp":
      return mocks.whatsapp;
    case "signal":
      return mocks.signal;
  }
}

export interface ResolvedChannel {
  connector: Connector;
  creds: Record<string, unknown>;
  from: string;
}

/**
 * Résout le connecteur effectif pour une policy donnée, en tenant compte d'un
 * éventuel compte fournisseur dédié (multi-account : plusieurs clés Resend, etc.).
 */
export async function resolveChannel(policy: PolicyWithAccount): Promise<ResolvedChannel> {
  const connector = connectorFor(policy.channel);
  let creds = await connector.resolveCreds(policy);

  // Compte fournisseur dédié : ses credentials chiffrées priment sur l'env du gateway
  if (policy.provider_account_id && policy.channel === "email") {
    const acc = await accountById(policy.provider_account_id);
    if (acc?.creds) {
      const accCreds = emailCredsFromAccount(acc.creds);
      if (accCreds.apiKey) creds = accCreds;
    }
  }

  const from = connector.resolveFrom(policy);
  return { connector, creds, from };
}
