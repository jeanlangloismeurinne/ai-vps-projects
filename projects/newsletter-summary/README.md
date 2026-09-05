# newsletter-summary

Reçoit les newsletters transférées vers `*@oozeenaru.resend.app` (inbound Resend), les stocke
dans PostgreSQL, et envoie chaque matin à **8h (Europe/Paris)** un digest récapitulant toutes
les mails reçues depuis la veille, à `jean.langlois-meurinne@mailbox.org`.

Le résumé de chaque mail est généré par DeepInfra (DeepSeek-V4), **un appel par mail** avec un
prompt unique et **éditable** depuis le Hub (voir ci-dessous). Le **système** (côté code, appliqué
à chaque appel) garantit : **rédaction en français** et **exclusion des publicités** — quelles que
soient les éditions du prompt.

Le digest est envoyé en **email HTML lisible** : chaque newsletter est rendue par DeepSeek sous
forme d'un **bloc HTML autonome** (styles inline, cf. `SUMMARIZE_HTML_PROMPT`), assemblé dans
une enveloppe HTML minimale côté code. Chaque bloc est enveloppé dans un **conteneur contrôle par
le code** qui garantit une séparation lisible entre les mails (corrige la mise en forme où deux
cartes pouvaient se coller). Un corps **texte brut** reste envoyé en parallèle comme fallback. Le
gateway accepte un champ `html` en plus du `text`.

## KB + éditeur de prompt (via le Hub)

Deux nouveautés intégrées à l'app « homepage » (Hub) :

- **Base de connaissance (résumés)** : chaque nouveau résumé est persisté dans la table
  `kb_documents`, au format **enveloppe KNOWLEDGE_ARCHITECTURE.md §3** (pivot Markdown +
  métadonnées), `visibility=private`. Exportable en JSON via `GET /api/kb` — prêt pour la future
  fédération pgvector. Affichage dans le Hub : `/newsletter`.
- **Éditeur de prompt versionné** : le prompt actif (`SUMMARIZE_HTML_PROMPT`) est éditable dans le
  Hub (`/newsletter/prompt`), **chaque enregistrement crée une nouvelle version** (append-only) et
  un **menu déroulant** permet de revenir à une version antérieure. Le digest relit le prompt actif
  **à chaque exécution** → une édition s'applique sans redémarrage. Endpoints : `GET /api/prompt`,
  `POST /api/prompt/versions`, `POST /api/prompt/activate`.

Sécurité : les endpoints `/api/*` sont protégés par le header `X-Hub-Token` (= `HUB_API_TOKEN`,
identique à `NEWSLETTER_API_TOKEN` du Hub), car ils sont aussi atteignables publiquement via le
sous-domaine `mails.*`.

## Flux

```
Mail transféré → Resend inbound (*@oozeenaru.resend.app)
  └─ webhook POST https://mails.jlmvpscode.duckdns.org/webhook/resend?token=…
       └─ app:8000 → stocke dans db_newsletter_summary (dédup par message_id, status=new)
Job quotidien 8h Europe/Paris (APScheduler)
  └─ résume chaque mail new (DeepInfra) → compose le digest → envoie via comms-gateway
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
| `GATEWAY_URL` | `http://comms-gateway:8000` (réseau interne) — envoi du digest ET rapatriement du corps inbound |
| `GATEWAY_TOKEN` | Jeton scoped du client auprès du gateway. **Le projet ne détient aucune clé Resend** : les secrets des providers restent au gateway |
| `RECIPIENT_EMAIL` | `jean.langlois-meurinne@mailbox.org` |
| `DEEPINFRA_API_KEY` | Clé DeepInfra pour les résumés |
| `DEEPINFRA_MODEL` | `deepseek-ai/DeepSeek-V4-Flash` |
| `SUMMARIZE_HTML_PROMPT` | Défaut du prompt de résumé (HTML) — la **version active** est éditée via le Hub |
| `HUB_API_TOKEN` | Jeton partagé avec le Hub (header `X-Hub-Token` sur `/api/*`) |
| `SUMMARY_HOUR` / `SUMMARY_MINUTE` | Horaire du digest (défaut 8h00) |
| `WEBHOOK_TOKEN` | Secret requis en `?token=` sur `/webhook/resend` |

## Endpoints

- `GET /health` — liveness
- `POST /webhook/resend?token=…` — réception inbound Resend
- `POST /webhook/resend/test` — test de routage (no auth, liste les clés du payload)
- `GET /api/prompt` — version active + historique du prompt (header `X-Hub-Token`)
- `POST /api/prompt/versions` — enregistrer une nouvelle version (header `X-Hub-Token`)
- `POST /api/prompt/activate` — revenir à une version antérieure (header `X-Hub-Token`)
- `GET /api/kb` — enveloppes KB §3 des résumés (header `X-Hub-Token`)
