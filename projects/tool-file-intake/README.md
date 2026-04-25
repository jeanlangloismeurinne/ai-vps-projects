# tool-file-intake

Micro-service FastAPI + Slack Bolt : réceptionne les fichiers envoyés dans Slack, les stocke dans `/storage/Documents/`, les indexe en SQLite, et notifie l'agent IA.

## Architecture

```
adapters/slack.py       — événements Slack, actions Block Kit, modals
services/storage.py     — écriture disque, validation, déduplication SHA256
services/indexer.py     — index SQLite (SQLAlchemy sync)
services/explorer.py    — parcours de l'arborescence Documents/
utils/tree_formatter.py — rendu ASCII de l'arborescence pour Slack
main.py                 — FastAPI + montage Slack handler
```

## Prérequis sur le VPS

### 1. Créer les volumes Docker

```bash
# Dossier de stockage des fichiers
sudo mkdir -p /storage/Documents
sudo chown 1000:1000 /storage/Documents

# Dossier de la base SQLite
sudo mkdir -p /data/intake-db
sudo chown 1000:1000 /data/intake-db
```

### 2. Réseau Docker

Le réseau `infra-net` doit exister (partagé avec les autres services) :

```bash
docker network create infra-net 2>/dev/null || true
```

### 3. Application Slack

Le service utilise le **Socket Mode** : il se connecte à Slack via WebSocket sortant.
Aucune URL webhook à exposer, aucun signing secret requis.

Dans l'interface Slack API (api.slack.com) :

1. **Socket Mode** → activer
2. **Basic Information → App-Level Tokens** → "Generate Token and Scopes"
   - Nom : `socket-mode` (ou autre)
   - Scope : `connections:write`
   - Copier le token `xapp-...` → `SLACK_APP_TOKEN` dans `.env`
3. **Event Subscriptions** → activer, **Subscribe to bot events** :
   - `message.channels`, `message.groups`, `message.im`
4. **Interactivity & Shortcuts** → activer (requis pour les boutons et modals)
5. **OAuth Scopes** (Bot Token) :
   - `channels:history`, `groups:history`, `im:history`
   - `files:read`
   - `chat:write`
   - `views:open`

## Démarrage

```bash
cp .env.example .env
# Remplir SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

docker compose up -d
```

## Déploiement Coolify

- Base Directory : `projects/tool-file-intake`
- Port exposé : `8020` (mappé sur `0.0.0.0:8020` via le reverse proxy Coolify)
- Après chaque mise à jour : **Rebuild** (pas Restart)

## Flux utilisateur

```
Utilisateur envoie un fichier dans Slack
        ↓
Bot propose : Documents/2026/04/25/  [Confirmer] [Autre dossier]
        ↓
[Confirmer] → stockage immédiat + confirmation avec arborescence
[Autre dossier] → modal avec arborescence actuelle + saisie chemin
        ↓
Confirmation + notification POST vers AGENT_WEBHOOK_URL
```

## Variables d'environnement

| Variable            | Obligatoire | Description                                      |
|---------------------|-------------|--------------------------------------------------|
| `SLACK_BOT_TOKEN`   | ✅           | Token xoxb- du bot Slack                        |
| `SLACK_APP_TOKEN`   | ✅           | Token xapp- pour Socket Mode (scope `connections:write`) |
| `STORAGE_BASE`      |             | Chemin de stockage (défaut : `/storage/Documents`) |
| `DB_PATH`           |             | Chemin SQLite (défaut : `/data/intake-db/intake.db`) |
| `AGENT_WEBHOOK_URL` |             | URL webhook agent IA (optionnel)                |
| `MAX_FILE_SIZE_MB`  |             | Taille max en Mo (défaut : 50)                  |

## Types MIME autorisés

PDF, Word, Excel, PowerPoint, texte brut, CSV, Markdown, JPEG, PNG, GIF, WebP, ZIP, JSON.
