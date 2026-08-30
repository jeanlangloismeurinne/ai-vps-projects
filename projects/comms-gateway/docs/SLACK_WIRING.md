# Câblage Slack du comms-gateway

Le gateway possède sa **propre app Slack** (un bot distinct de celui d'assistant-ia
`ai_vps_jlm`). **On ne touche à rien d'assistant-ia.** Le gateway peut **envoyer** dans
un channel et **recevoir** les messages d'un channel (événements entrants) puis les
router vers les clients concernés.

## 1. Créer l'app Slack (🔧 utilisateur)

1. https://api.slack.com/apps → « Create New App » → **From scratch**.
2. Nom : `comms-gateway` — workspace privé.
3. Onglet **OAuth & Permissions** :
   - Scopes Bot Token : `chat:write` (envoi) et, pour la réception, `channels:history`,
     `groups:history`, `im:history`, `mpim:history`.
   - Installer dans le workspace → copier le **Bot User OAuth Token** (`xoxb-…`).
4. Onglet **Event Subscriptions** → **Enable Events** :
   - Request URL : `https://comms.jlmvpscode.duckdns.org/webhooks/slack`
   - Subscribe to bot events : `message.channels`, `message.groups`, `message.im`.
   - Sauvegarder → Slack POSTera les mises à l'événement (vérification de signature via
     le **Signing Secret** de l'onglet Basic Information).
5. Inviter le bot dans les channels que le gateway doit **recevoir** :
   `/invite @comms-gateway` dans chaque channel à écouter.

## 2. Renseigner les secrets (🔧)

Dans le `.env` (ou secrets Coolify) du gateway :

```
SLACK_BOT_TOKEN=<xoxb-...>
SLACK_SIGNING_SECRET=<...>
PUBLIC_BASE_URL=https://comms.jlmvpscode.duckdns.org
```

Puis `docker compose up -d` (re-création). Au démarrage, le compte
`provider_accounts('slack','slack-gateway-bot')` est créé.

## 3. Déclarer la réception pour un client (receive)

Via l'API admin, une policy `slack` avec `action: receive` (ou `both`) et
`slack_channel_ids: ["<channel_id>"]` pour le client concerné :

```bash
curl -X PUT $GATEWAY_URL/v1/admin/clients/<client_id>/policies/slack \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"receive","slack_channel_ids":["C0B080X2ZBK"]}'
```

Chaque message reçu sur ce channel est journalisé (`direction=in`, attribué au client)
et poussé vers le `webhook_url` du client s'il en a un.

## 4. Envoyer depuis un projet

Le client doit avoir une policy `slack` avec `action: send` (ou `both`). Envoi via le SDK :

```python
import comms_client as comms
await comms.get_client().send_slack(to="#journal", body="Bonjour")
```

(`to` = id de channel ou `#nom`.)

## Rappel de sécurité

Le bot Slack du gateway est **indépendant** : les events entrants et le signing secret
sont propres à l'app `comms-gateway`. Aucune modification côté `assistant-ia`.
