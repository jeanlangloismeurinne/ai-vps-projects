import type { Channel, PolicyWithAccount } from "../domain.js";
import type { Connector, SendOptions, SendResult } from "./types.js";

/**
 * Connecteur MOCK — même interface que les vrais connecteurs.
 * Utilisé tant que le matériel Phase 0 (téléphone Free + eSIM + Tailscale) n'est
 * pas en place pour SMS / WhatsApp / Signal. Logge l'envoi, ne part JAMAIS à
 * l'extérieur. Remplacement par le vrai connecteur derrière la même interface.
 */
export class MockConnector implements Connector {
  constructor(readonly channel: Channel) {}

  async resolveCreds(): Promise<Record<string, unknown>> {
    return { mock: true };
  }

  resolveFrom(_p: PolicyWithAccount): string {
    return "mock";
  }

  async send(opts: SendOptions, _creds: Record<string, unknown>, from: string): Promise<SendResult> {
    console.log(
      `[MOCK:${this.channel}] from=${from} to=${opts.to} subject=${opts.subject ?? ""} ` +
        `body=${(opts.body ?? "").slice(0, 80)}`
    );
    return { ok: true, providerMessageId: `mock-${this.channel}-${Date.now()}` };
  }
}
