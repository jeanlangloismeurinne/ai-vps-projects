import type { PolicyWithAccount } from "../domain.js";
import { config } from "../config.js";
import type { Connector, SendOptions, SendResult } from "./types.js";

const CHAT_POST = "https://slack.com/api/chat.postMessage";

export class SlackConnector implements Connector {
  readonly channel = "slack" as const;

  async resolveCreds(): Promise<Record<string, unknown>> {
    return { botToken: config.SLACK_BOT_TOKEN };
  }

  resolveFrom(policy: PolicyWithAccount): string {
    // Slack : « identité » = premier channel autorisé par la policy, sinon env
    return policy.account_default_from ?? config.SLACK_BOT_TOKEN ? "gateway-bot" : "";
  }

  async send(opts: SendOptions, creds: Record<string, unknown>): Promise<SendResult> {
    const botToken = String(creds.botToken ?? config.SLACK_BOT_TOKEN ?? "");
    if (!botToken) {
      return { ok: false, error: "SLACK_BOT_TOKEN absent (gateway non configuré)" };
    }
    const channel = opts.to; // `to` = channel id ou #channel
    if (!channel) {
      return { ok: false, error: "`to` (channel) requis pour Slack" };
    }
    const res = await fetch(CHAT_POST, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${botToken}`,
        "Content-Type": "application/json; charset=utf-8",
      },
      body: JSON.stringify({ channel, text: opts.body ?? opts.subject ?? "" }),
    });
    const json = (await res.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      ts?: string;
    };
    if (!json.ok) {
      return { ok: false, error: json.error ?? `HTTP ${res.status}` };
    }
    return { ok: true, providerMessageId: json.ts ?? null };
  }
}
