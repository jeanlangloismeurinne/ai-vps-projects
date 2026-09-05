---
id: reprise-comms-gateway
status: prompt-de-reprise
created: 2026-08-30
updated: 2026-09-03
project: comms-gateway
role: >
  Prompt à coller pour reprendre le chantier du gateway de communication externe. État : gateway
  multi-tenant DÉPLOYÉ en prod, désormais en `docker compose` standalone (migration Coolify ->
  compose du 2026-09-03), secrets dans un `.env` local 600 hors repo, /webhooks/* seuls exposés
  publiquement ; reste les 3 blocages utilisateur (domaine Resend, app Slack, téléphone
  SMS/WhatsApp/Signal) avant envois réels.
---

# 🚦 RÈGLE (s'applique à chaque session)

> **En fin de conversation, après avoir implémenté une nouvelle version / un nouveau
> sprint, ACTUALISER ce fichier** : état atteint, prochain jalon, blocages, commandes de
> reprise. La session suivante démarre en relisant ce fichier — ne jamais repartir d'un
> état périmé.

---

> ## ⚡ MàJ 2026-09-03 — le gateway ne dépend plus de Coolify
>
> **Ce qui a changé** : Coolify a été arrêté sur le VPS ; toutes les apps, dont ce gateway,
> tournent en `docker compose` standalone. Le code du gateway n'a pas bougé d'une ligne — seule
> la façon de le déployer et de lui injecter ses secrets a changé.
>
> - Déploiement : `infrastructure/compose-deploy.sh comms-gateway -m "…" -f "…"`
>   (remplace `deploy.sh`, neutralisé). Plus de rebuild via l'API Coolify.
> - Secrets : `projects/comms-gateway/.env` (chmod 600, gitignored) au lieu des secrets chiffrés
>   de Coolify. Les 10 valeurs ont été rapatriées **à l'identique** (aucune régénérée). Copie de
>   référence : `/root/secrets/coolify-env-backup/comms-gateway.env`.
> - `docker-compose.yml` a de nouveau un `env_file: [.env]` (la consigne inverse « env_file
>   interdit » datait de Coolify et ne vaut plus).
> - L'UUID `commsgateway00000000000` ne désigne plus rien d'actif.
>
> **Ce qui a été vérifié** : `/health` répond 200 (sonde interne, le service n'expose pas `/health`
> publiquement) ; `/webhooks/*` toujours routé par Traefik ; `/v1` toujours NON routé publiquement
> — la frontière de sécurité du chantier est intacte. Les deux volumes étaient vides : aucun risque
> de perte de données à la bascule.
>
> **Ce qui NE change pas** : les 3 blocages utilisateur ci-dessous sont inchangés.

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

# ⚡ MàJ 2026-09-01 — DÉPLOIEMENT : /v1/send accepte `html` (digest HTML newsletter)

✅ Merge du support du champ `html` dans `/v1/send` (en plus du fallback `text`) :
`send.ts` déstructure `html` (audit conserve `body ?? html` pour la traçabilité,
le HTML complet part au connecteur), `connectors/email.ts` l'envoie tel quel à Resend
via `payload.html`. Voir [[project-newsletter-roadmap-optiona]] (Option B).
- Rebuild **#334 → `finished`**, mono-conteneur (pas d'orphelin Traefik). Commit `1d994ae`.
- Vérif prod : `POST /webhooks/resend` répond `400` applicatif (service vivant),
  seul conteneur `comms-gateway-commsgateway00000000000-085814*` sur l'image `1d994ae`.
- Le champ `html` est donc **actif** : `newsletter-summary` peut envoyer son digest HTML.
  Avant ce déploiement, Resend ne recevait que le `text` (email partant en texte).

---

# ⚡ MàJ 2026-08-31 — MODE DEV RESEND ACTIF (envoi email réel OK)

✅ Le mode développement Resend est activé sur l'app Coolify (lignes **preview + production**,
chiffrées Laravel, méthode `deploy.sh`) :
`RESEND_API_KEY` = clé réelle `re_…` fournie par l'utilisateur (jamais affichée/committée),
`RESEND_DEV_MODE=1`, `RESEND_DEV_TO=jean.langlois.meurinne@gmail.com`.

- Rebuild **#332 → `finished`**, mono-conteneur (pas d'orphelin Traefik).
- Mode dev (TEMPORAIRE) : force `from=onboarding@resend.dev` et `to=RESEND_DEV_TO` — seule
  adresse livrable de `resend.dev` tant qu'aucun domaine d'envoi n'est vérifié.
- **Test réel réussi** : `POST /v1/send` (client `newsletter-summary`, canal `email`) →
  `{"status":"sent","provider_message_id":"260cf699-bc41-4eed-8253-49558f4fd26e"}` ; audit
  `success`. Les 2 entrées `failure` antérieures = essais avant injection (clé absente, 403).
- Fichier secrets off-repo `/root/secrets/comms-gateway.env` aligné (clé réelle + dev vars),
  backup `.bak.<ts>`.

🔻 **Prochain blocage utilisateur** : vérifier/ajouter un **domaine d'envoi réel** dans
resend.com/domains (+ DNS) → ensuite retirer `RESEND_DEV_MODE` pour envoyer vers les
destinataires réels (avec `RESEND_DEFAULT_FROM=newsletter@oozeenaru.resend.app`).

---

# ⚡ MàJ 2026-09-01 — Endpoint inbound `GET /v1/inbound/email/:id`

✅ Ajout d'un endpoint authentifié qui **proxy l'API Resend « Received emails »** :
`GET https://api.resend.com/emails/inbound/{email_id}` → renvoie `text`/`html` + métadonnées.
Motif : le webhook Resend `email.received` ne délivre **que des métadonnées** (jamais le
corps) ; `newsletter-summary` rapatrie désormais le corps via cet endpoint à la réception.
Clé Resend **restée au gateway** (aucun secret en clair dans les projets clients).
- Déployé via `infrastructure/deploy.sh comms-gateway` — build **#333** (commit `82272d6`).
- Vérifié en prod : HTTP 200 sur le vrai `email_id` avec `text` 48 KB / `html` 59 KB.

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
| email (Resend) | ✅ réel + livrable en **mode dev** | **domaine d'envoi réel non vérifié** (le mode dev `resend.dev` force vers `RESEND_DEV_TO` ; à retirer dès domaine vérifié) |
| slack | ⏳ prêt côté gateway, app à créer | **app Slack `comms-gateway` à créer** (`docs/SLACK_WIRING.md`) + secrets + invitation du bot |
| sms / whatsapp / signal | 🧪 mock | **téléphone Free + eSIM + Tailscale** (`docs/PHONE_PART2_CHECKLIST.md`) |

## RESTE À FAIRE

### Bloquants utilisateur 🔧 (aucun code nécessaire)
**(a)** Vérifier/ajouter un **domaine d'envoi Resend** (resend.com/domains + DNS) → **sortir du
      mode dev** (retirer `RESEND_DEV_MODE`, réel `to`/`from`) pour les envois vers les
      destinataires réels. Le mode dev actuel livra déjà vers `RESEND_DEV_TO` (test du 2026-08-31 ok).
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
