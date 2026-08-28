# newsletter-summary

Reçoit les newsletters transférées vers `*@oozeenaru.resend.app` (inbound Resend), les stocke
dans PostgreSQL, et envoie chaque matin à **8h (Europe/Paris)** un digest récapitulant toutes
les mails reçues depuis la veille, à `jean.langlois-meurinne@mailbox.org`.

Le résumé de chaque mail est généré par DeepInfra (DeepSeek-V4) depuis un prompt configurable
(`SUMMARIZATION_PROMPT`) qui demande de **suivre la structure du mail d'origine**.

## Flux

```
Mail transféré → Resend inbound (*@oozeenaru.resend.app)
  └─ webhook POST https://mails.jlmvpscode.duckdns.org/webhook/resend?token=…
       └─ app:8000 → stocke dans db_newsletter_summary (dédup par message_id, status=new)
Job quotidien 8h Europe/Paris (APScheduler)
  └─ résume chaque mail new (DeepInfra) → compose le digest → envoie via Resend API
       └─ marque les mails summarized
```

## Déploiement

Stack **standalone docker compose** (pas une app Coolify), sur le réseau `coolify` — routée par
le coolify-proxy (TLS Let's Encrypt), comme `kb-viewer`.

```bash
cd projects/newsletter-summary
# 1. Créer la base (une fois) :
#    docker exec shared-postgres psql -U admin -c "CREATE USER newsletter WITH PASSWORD '<pw>';"
#    docker exec shared-postgres psql -U admin -c "CREATE DATABASE db_newsletter_summary OWNER newsletter;"
# 2. Créer .env (hors git) avec les vraies valeurs — cf. .env.example
# 3. Déployer / redéployer :
docker compose up -d --build
```
Puis configurer le webhook inbound Resend : mails vers `*@oozeenaru.resend.app`
→ `https://mails.jlmvpscode.duckdns.org/webhook/resend?token=$WEBHOOK_TOKEN`.

## Variables d'environnement (.env, non commité)

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://newsletter:<pw>@shared-postgres:5432/db_newsletter_summary` |
| `RESEND_API_KEY` | Clé API Resend (réception + envoi digest) |
| `SENDER_EMAIL` | `newsletter@oozeenaru.resend.app` |
| `RECIPIENT_EMAIL` | `jean.langlois-meurinne@mailbox.org` |
| `DEEPINFRA_API_KEY` | Clé DeepInfra pour les résumés |
| `DEEPINFRA_MODEL` | `deepseek-ai/DeepSeek-V4-Flash` |
| `SUMMARIZATION_PROMPT` | Prompt du résumé (suit la structure du mail) — configurable |
| `SUMMARY_HOUR` / `SUMMARY_MINUTE` | Horaire du digest (défaut 8h00) |
| `WEBHOOK_TOKEN` | Secret requis en `?token=` sur `/webhook/resend` |

## Endpoints

- `GET /health` — liveness
- `POST /webhook/resend?token=…` — réception inbound Resend
- `POST /webhook/resend/test` — test de routage (no auth, liste les clés du payload)
