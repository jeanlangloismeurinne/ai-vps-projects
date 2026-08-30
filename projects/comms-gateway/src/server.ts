import Fastify from "fastify";
import { config, assertConfig } from "./config.js";
import { pool } from "./db.js";
import { redisReady } from "./redis.js";
import { ensureSchema } from "./schema.js";
import { registerSendRoute } from "./routes/send.js";
import { registerMessagesRoute } from "./routes/messages.js";
import { registerAdminRoutes } from "./routes/admin.js";
import { registerWebhooks } from "./routes/webhooks.js";

async function main(): Promise<void> {
  // Secrets indispensables — échec rapide et explicite au démarrage.
  assertConfig(["DATABASE_URL", "ADMIN_TOKEN", "MASTER_KEY"]);

  // Le webhook Slack exige le signing secret.
  if (config.SLACK_SIGNING_SECRET) assertConfig(["SLACK_BOT_TOKEN"]);

  const app = Fastify({ logger: true, bodyLimit: config.MAX_BODY_BYTES });

  // Vérification connexions partagées
  await pool.query("SELECT 1");
  await redisReady();

  // Schéma idempotent + comptes fournisseurs de référence
  const seeds: Array<{ type: string; label: string; default_from: string }> = [];
  if (config.RESEND_DEFAULT_FROM) {
    seeds.push({ type: "resend", label: "resend-oozeenaru", default_from: config.RESEND_DEFAULT_FROM });
  }
  if (config.SLACK_BOT_TOKEN) {
    seeds.push({ type: "slack", label: "slack-gateway-bot", default_from: "" });
  }
  await ensureSchema(seeds);

  // Routes
  await registerSendRoute(app);
  await registerMessagesRoute(app);
  await registerAdminRoutes(app);
  await registerWebhooks(app);

  await app.listen({ host: config.HOST, port: config.PORT });
}

main().catch((err) => {
  console.error("FATAL comms-gateway:", err);
  process.exit(1);
});
