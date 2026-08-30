# comms-gateway

Gateway central **multi-tenant** de communication externe. Point d'entrée unique pour
l'ensemble des services et agents du VPS vers les canaux **email (Resend)**, **Slack**,
puis **SMS**, **WhatsApp**, **Signal** — sans jamais exposer les identifiants des
providers aux services appelants.

## Pourquoi

- Un seul composant détient les secrets des providers (clé Resend, tokens Slack, …).
- Chaque projet = un **client** déclaré avec ses propres paramètres (adresse Resend de
  départ, canaux autorisés, quotas, destinataires, webhook), **réutilisable** : on ajoute
  un projet sans redéploiement.
- **Multi-comptes** : un client peut référencer n'importe quel compte fournisseur
  (`provider_accounts`) — p. ex. plusieurs clés Resend, plusieurs apps Slack.
- **Refus par défaut**, **audit append-only**, **rate-limit** quotidien par canal.

## Architecture

```
  Services/agents (nouveaux projets)  --Bearer token-->  comms-gateway:8000  --provider-->  Resend / Slack / (SMS/WhatsApp/Signal)
                                                        (réseau interne coolify)              secrets uniquement ici
  Providers (entrant)  --/webhooks/* (signés)-->  comms-gateway  --routing policy-->  webhook_url du client ou GET /v1/messages
```

- **API v1 (interne)** : `POST /v1/send`, `GET /v1/messages`, `POST|PATCH /v1/admin/*`.
- **Webhooks publics** : `/webhooks/resend` (email entrant), `/webhooks/slack`
  (événements Slack entrants) — seuls ces chemins sont exposés par Traefik (PathPrefix),
  le reste reste sur le réseau interne Coolify.
- **Connecteurs** derrière une interface uniforme : `email` (Resend) et `slack` réels ;
  `sms`/`whatsapp`/`signal` en **mock** tant que le matériel (téléphone Free + eSIM +
  Tailscale) n'est pas en place.

## Base de données (`db_comms_gateway` sur shared-postgres)

| Table | Rôle |
|---|---|
| `provider_accounts` | comptes fournisseurs (type, label, `default_from`, creds chiffrées AES-GCM maître) |
| `clients` | projets consommateurs (`client_id`, `token_hash`, `enabled`, `webhook_url`) |
| `client_policies` | par canal : action `send/receive/both`, quota/jour, whitelist destinataires, `default_from`, channels Slack |
| `messages` | journal append-only (audit, attribution au client, statut) |

## Déploiement

Stack **standalone docker compose** (réseau `coolify`, pattern newsletter-summary) :

```bash
cd projects/comms-gateway
# 1. Créer la base (une fois) :
docker exec shared-postgres psql -U admin -c "CREATE DATABASE db_comms_gateway;"
# 2. Créer .env (hors git) — cf. .env.example ; générer MASTER_KEY et ADMIN_TOKEN
# 3. Déployer :
docker compose up -d --build
```

Secrets : `RESEND_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` dans le `.env`
(ou secrets Coolify) du gateway. Regénérer les secrets dès que possible en production.

## Modèle de permissions & refus par défaut

Un client **sans policy active** est refusé sur tous les canaux (testé, `rejected_policy`).
Quotas appliqués via `shared-redis`. Coupe-circuit à chaud :
`PATCH /v1/admin/clients/<id>/status {"enabled":false}` (effet immédiat, sans rebuild).

## Ajouter un nouveau projet (onboarding)

1. `POST /v1/admin/clients` (`ADMIN_TOKEN`) avec `client_id` + `policies` → renvoie un
   **token une seule fois** → le copier en secret Coolify du projet (`GATEWAY_TOKEN`).
2. Pointer le projet sur `GATEWAY_URL=http://comms-gateway:8000` + `GATEWAY_TOKEN`.
3. Embarquer le SDK : `cp templates/comms-client/comms_client.py <projet>/app/`.
4. Tester un envoi positif + un refus (client sans policy / destinataire hors whitelist).
5. Vérifier l'audit : `GET /v1/messages` (scope au client).

Détails : `templates/comms-client/README.md`.

## État des connecteurs

| Canal | Statut | Notes |
|---|---|---|
| email (Resend) | ✅ réel | envoi + webhook entrant (signature Svix). **Domaine de réémission à vérifier dans Resend** pour la livraison réelle. |
| slack | ⏳ réel (envoi) / réception à câbler | nécessite une app Slack PRO PRE au gateway + Secret + invitation du bot. Voir `docs/SLACK_WIRING.md`. |
| sms / whatsapp / signal | 🧪 mock | en attente matériel — voir `docs/PHONE_PART2_CHECKLIST.md`. |

## Sécurité (respect des règles permanentes)

- Connecté à `shared-postgres` + `shared-redis` (réseaux existants), aucun mot de passe committé.
- Seuls `/webhooks/*` exposés publiquement (Traefik PathPrefix) ; `/v1` reste interne.
- Aucun service systemd — tout en Docker.
- `MASTER_KEY` chiffre les creds des comptes en BDD.
