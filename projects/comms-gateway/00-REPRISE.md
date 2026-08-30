---
id: reprise-comms-gateway
status: prompt-de-reprise
created: 2026-08-30
updated: 2026-08-30
project: comms-gateway
role: Prompt à coller pour reprendre le chantier du gateway de communication externe. État : gateway multi-tenant DÉPLOYÉ en prod Coolify (app `dockercompose`, UUID `commsgateway00000000000`), secrets chiffrés hors repo, /webhooks/* seuls exposés publiquement ; reste les 3 blocages utilisateur (domaine Resend, app Slack, téléphone SMS/WhatsApp/Signal) avant envois réels.
---

# 🚦 RÈGLE (s'applique à chaque session)

> **En fin de conversation, après avoir implémenté une nouvelle version / un nouveau
> sprint, ACTUALISER ce fichier** : état atteint, prochain jalon, blocages, commandes de
> reprise. La session suivante démarre en relisant ce fichier — ne jamais repartir d'un
> état périmé.

---

# Prompt de reprise

Reprends le chantier du gateway de communication externe **`comms-gateway`**.

CONTEXTE (déjà acté — ne pas tout ré-explorer) :
- Consigne : lis `CLAUDE.md` (§ « Secrets — comms-gateway ») + `README.md` +
  `docs/SLACK_WIRING.md` + `docs/PHONE_PART2_CHECKLIST.md` + `templates/comms-client/README.md`
  + `COOLIFY_PLAYBOOK.md` (au moment d'un déploiement).
- **Le service est DÉJÀ en production** : app Coolify `dockercompose`, conteneur
  `comms-gateway-commsgateway00000000000-*` sur le réseau `coolify`, routage Traefik sur
  `https://comms.jlmvpscode.duckdns.org/webhooks/*` (PathPrefix) — `/v1` reste interne.
- Les **10 secrets** sont chiffrés dans l'env Coolify (jamais committés) ; copie 600 de
  référence hors repo dans `/root/secrets/comms-gateway.env`.
- Le **SDK client** est `templates/comms-client/` (un projet = `GATEWAY_URL`
  `http://comms-gateway:8000` + `GATEWAY_TOKEN`).

INVARIANTS : ne JAMAIS committer de secrets / pas de `.env` en clair · pas de service
systemd · seuls `/webhooks/*` exposés publiquement · **ne pas toucher à assistant-ia** ·
autonomie Coolify complète (playbook, méthode PHP sans token).

PROCHAIN JALON (le seul reste du développement) : quand l'utilisateur a prêté le matériel
et les comptes, **câbler les connecteurs réels** (Resend domaine vérifié / app Slack
`comms-gateway` / SMS+WhatsApp+Signal via téléphone Free+eSIM+Tailscale) derrière la même
interface — puis déclarer les policies des clients. Demander son feu vert avant.

RESTE À FAIRE côté utilisateur (bloquant pour la prod réelle, cf. sections ci-dessous) :
**(a)** domaine d'envoi Resend (compte de test → envoi réel impossible) ; **(b)** app Slack
`comms-gateway` à créer (`SLACK_WIRING.md`) ; **(c)** téléphone Free+eSIM+Tailscale
(`PHONE_PART2_CHECKLIST.md`) pour SMS/WhatsApp/Signal.

---

# ⚡ MàJ 2026-08-30 — MIS EN PRODUCTION (Coolify)

✅ **Le gateway est déployé et vérifié en prod.** Cette MàJ clôt le chantier « mise en
service » : le code était prêt, il reste le câblage des providers réels (blocages
utilisateur, sections plus bas).

## Ce qui a été fait (et vérifié)

**Commits** (poussés sur `main`, aucun secret) :
- `80e0f25` — source comms-gateway + SDK `templates/comms-client/` + migration
  `newsletter-summary` (35 files : gateway TS + compose + docs, SDK, newsletter).
- `3450466` — enregistrement de l'app Coolify (UUID) dans `COOLIFY_PLAYBOOK.md`,
  `infrastructure/deploy.sh`, `DEPLOY.md` + état dans `CLAUDE.md`.

**Conversion en app Coolify** (méthode DB + PHP du playbook, sans token API) :
- App : build_pack `dockercompose`, Base Directory `/projects/comms-gateway`, compose
  `/docker-compose.yml`, **UUID `commsgateway00000000000`**, fqdn
  `https://comms.jlmvpscode.duckdns.org`, deployment **#314 → `finished`**.
- **10 secrets chiffrés** en env Coolify : `DATABASE_URL`, `REDIS_URL`, `MASTER_KEY`,
  `ADMIN_TOKEN`, `RESEND_API_KEY`, `RESEND_DEFAULT_FROM`, `SLACK_BOT_TOKEN`,
  `SLACK_SIGNING_SECRET`, `PUBLIC_BASE_URL`, `WEBHOOK_TOKEN` (source dérivée de
  `/root/secrets/comms-gateway.env`, fichier 600 jamais committé).
- **Ancien conteneur standalone `comms-gateway` supprimé** (`docker rm -f`) → plus de
  double routage Traefik. `docker ps` ne montre plus que le conteneur géré Coolify.

**Vérification post-déploiement** (depuis le réseau interne, `http://comms-gateway:8000`) :
- `GET /health` → 200 `{"status":"ok"}`.
- envoi sur **canal non autorisé** → `status:'rejected'`, audit **`rejected_policy`** ;
- **client sans policy** → refusé (audit `rejected_policy`) ;
- **quota dépassé** (sms mock, limit=1/jour) → audit **`rejected_rate_limit`**.
- Clients de test e2e supprimés ; les 3 messages réels de `newsletter-summary` **préservés**.

## Commandes utiles (reprise)

```bash
# Santé (depuis un conteneur sur le réseau coolify)
curl -s http://comms-gateway:8000/health

# Déployer une nouvelle version (depuis la racine du repo, après commit+push)
infrastructure/deploy.sh comms-gateway -m "<message>" -f "<chemins>"
# (UUID dans COOLIFY_PLAYBOOK.md § UUIDs ; après deploy, vérifier docker ps = 1 conteneur)

# Onboarding d'un nouveau projet consommateur (côté gateway, ADMIN_TOKEN)
curl -X POST $GATEWAY_URL/v1/admin/clients -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"<projet>","policies":[{"channel":"email","action":"send","rate_limit_per_day":50}]}'

# Utilisation SDK (projet consommateur)
cp templates/comms-client/comms_client.py <projet>/app/
# env : GATEWAY_URL=http://comms-gateway:8000 / GATEWAY_TOKEN=<token une seule fois>
```

---

# État du projet

## Architecture (rappel)

- **API v1 (interne)** : `POST /v1/send`, `GET /v1/messages`, `POST|PATCH /v1/admin/*` —
  accessible uniquement sur le réseau interne `coolify` (jamais exposée par Traefik).
- **Webhooks publics** : `/webhooks/resend` (email entrant), `/webhooks/slack`
  (événements Slack) — seuls ces chemins sont routés (label Traefik `PathPrefix(/webhooks)`).
- Connecteurs derrière une interface uniforme : `email` (Resend) et `slack` réels ;
  `sms`/`whatsapp`/`signal` en **mock** (interface `send`/`receive` identique, remplaçable
  sans toucher aux clients ni aux permissions).
- Base `db_comms_gateway` (shared-postgres) : `provider_accounts`, `clients`,
  `client_policies`, `messages` (audit append-only). Rate-limit sur shared-redis.

## Table des connecteurs

| Canal | Statut | Blocage pour la prod réelle |
|---|---|---|
| email (Resend) | ⚠️ réel mais non livrable | **domaine d'envoi non vérifié** dans resend.com/domains (compte de test → 403) |
| slack | ⏳ prêt côté gateway, app à créer | **app Slack `comms-gateway` à créer** (`docs/SLACK_WIRING.md`) + secrets + invitation du bot |
| sms / whatsapp / signal | 🧪 mock | **téléphone Free + eSIM + Tailscale** (`docs/PHONE_PART2_CHECKLIST.md`) |

## RESTE À FAIRE

### Bloquants utilisateur 🔧 (aucun code nécessaire)
**(a)** Vérifier/ajouter un **domaine d'envoi Resend** (resend.com/domains + DNS) → envoi email réel.
**(b)** Créer l'**app Slack `comms-gateway`** (bot dédié, envoi+reception ; `docs/SLACK_WIRING.md`) →
      renseigner `SLACK_BOT_TOKEN`/`SLACK_SIGNING_SECRET` en secrets Coolify, inviter le bot,
      déclarer une policy `slack` `receive`/`send` pour les clients via l'API admin.
**(c)** Préparer le **téléphone Free + eSIM + Tailscale** (`docs/PHONE_PART2_CHECKLIST.md`) →
      puis demander à l'utilisateur son feu vert avant de câbler SMS/WhatsApp/Signal.

### Une fois les blocages levés
1. Remplacer les connecteurs mock par les vrais (interface `send`/`receive` inchangée).
2. Déclarer les policies des clients (canaux + quotas + destinataires autorisés).
3. Tester un envoi positif + un refus + l'audit — sur le **chemin réel** (pas seulement
   hors-ligne).

## Rappels techniques
- Ne jamais committer de secret ; les secrets du gateway vivent en **env Coolify** (chiffrés).
  Copie 600 hors repo : `/root/secrets/comms-gateway.env` (à régénérer/supprimer en prod).
- `newsletter-summary` est un **conteneur standalone** (pas une app Coolify gérée par
  deploy.sh) — cf. `DEPLOY.md`.
- `docker compose` du gateway : **pas de `env_file`** (l'env est injecté par Coolify).
- Modèle de permissions : refus par défaut. Coupure à chaud :
  `PATCH /v1/admin/clients/<id>/status {"enabled":false}` (sans rebuild).
