# CLAUDE.md — ai-vps-projects

## Contexte global
Repo multi-projets sur VPS Hetzner (204.168.250.110).
Domaine : jlmvpscode.duckdns.org
Déploiement : Coolify — chaque projet est une application séparée.

## Agent de sécurité

Rapports générés par `/opt/cyber-agent/` — structure :
- `/opt/cyber-agent/reports/parsed/YYYY-MM-DD_HH-MM_merged.json` — rapport fusionné (le plus récent = dernier trié par date)
- `data['all_vulns']['critical']` / `['high']` — listes de vulnérabilités par sévérité
- `data['counts']` — compteurs par niveau, `data['risk_score']` — score global /100

Chaque vuln contient : `id`, `package`, `installed_version`, `fixed_version`, `description`, `target`, `fix`.

## Infrastructure partagée
- PostgreSQL 16 : shared-postgres (port 5432)
  Bases : db_assistant (réservée pour assistant-ia, pas encore utilisée)

## Clés API inter-services
- `INTERNAL_API_KEY` (bank-review ↔ assistant-ia) : `a09e3fce7a11df086a317458e4f15bf9f96ee57e7a0837f85d96905723d58585`
  — Header : `X-Internal-Api-Key`
  — Endpoint protégé : `POST /api/import/direct` sur bank-review
- Redis 7 : shared-redis (port 6379)
- Réseau Docker : infra-net

## Projets actifs
- projects/assistant-ia/ : orchestrateur Slack — reçoit webhooks de tool-file-intake et déclenche les actions par service (bank-review, etc.) — FastAPI, port 8030
- projects/bank-review/ : analyse de relevés bancaires (upload Excel/CSV + analyse Claude) — Python 3.12, FastAPI, pandas
- projects/feature-module/ : microservice feedback (port 3333) — widget flottant + API + stockage Markdown
- projects/tool-file-intake/ : réception fichiers Slack → stockage /storage/Documents/ + index SQLite — Python 3.12, FastAPI, Slack Bolt (port 8020)

## Slack bot partagé

Le bot utilise le **Socket Mode** (pas de signing secret, pas d'URL webhook à exposer).
Tokens stockés dans `/opt/cyber-agent/.env` :
- `SLACK_BOT_TOKEN` = `xoxb-619072475858-...`
- `SLACK_APP_TOKEN` = `xapp-1-A0ATSM6JECA-...` (scope `connections:write`)

Channel Slack principal : `C0AUFGZNBGT`

Le bot doit être **invité explicitement** dans chaque channel pour recevoir ses événements :
`/invite @ai_vps_jlm`

## Feedback utilisateur

Les tickets (bugs, suggestions, features) sont stockés dans le dossier
`feedback-tickets/` de chaque projet concerné, au format Markdown.

Pour bank-review : `projects/bank-review/feature-tickets/`
Pour journal/kanban : `projects/assistant-ia/feature-tickets/{project}/`

Chaque fichier = un ticket. Champ `status: open` = en attente de traitement.

### Système feedback — Slack & déploiement

Architecture en deux temps :
- **Nouveau ticket** (widget web ou `/feature` Slack) → notifie le channel `#features-{service}`
- **Déploiement** → notifie le channel principal du service avec la liste des tickets fermés

### Fermeture d'un ticket
Passer `status: open` → `status: closed` **et ajouter** `closed_at: {datetime ISO}` dans le frontmatter.
Ne déclenche aucune notification Slack immédiate.

### Notification de déploiement
Coolify exécute automatiquement après chaque build via `post_deployment_command` :
```bash
# bank-review
curl -sf -X POST https://assistant.jlmvpscode.duckdns.org/webhook/deploy-complete \
  -H 'Content-Type: application/json' -d '{"service":"bank-review"}' || true

# assistant-ia (journal + kanban)
curl -sf -X POST https://assistant.jlmvpscode.duckdns.org/webhook/deploy-complete \
  -H 'Content-Type: application/json' -d '{"service":"journal"}' || true && \
curl -sf -X POST https://assistant.jlmvpscode.duckdns.org/webhook/deploy-complete \
  -H 'Content-Type: application/json' -d '{"service":"kanban"}' || true
```
Endpoint : `POST /webhook/deploy-complete` sur assistant-ia — accepte `{"service":"nom"}` ou `{"application_uuid":"..."}`.

### Channels Slack (IDs fixes)
| Channel | ID | Rôle |
|---|---|---|
| `#bank-review` | `C0AV2EJHR5H` | déploiement bank-review |
| `#journal` | `C0B080X2ZBK` | déploiement journal |
| `#tasks` | `C0AV5M6385T` | déploiement kanban |
| `#feedback` | `C0AUCE6NELT` | nouveaux tickets tous projets (ex #features-ai-assistant) |

### Commande Slack `/feature`
Utilisable dans n'importe quel channel. Socket Mode = pas d'URL publique, mais la commande doit être enregistrée dans api.slack.com → Slash Commands.
- Depuis un channel lié à un projet (`#bank-review`, `#journal`, `#tasks`) → feedback enregistré directement
- Depuis tout autre channel → sélecteur Block Kit avec la liste des projets + « ➕ Nouveau projet »
Syntaxe : `/feature votre message`

La variable `FEEDBACK_CHANNEL_ID` a `C0AUCE6NELT` en valeur par défaut — aucune config Coolify nécessaire.

## Ajouter un projet
1. Créer projects/nouveau-projet/
2. Créer la base : docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_nouveau;'
3. Créer une app Coolify avec Base Directory = projects/nouveau-projet
4. Documenter ici
5. **Ajouter le nom du dossier dans `_KNOWN_PROJECTS`** dans `projects/assistant-ia/app/slack_app.py` — cette liste est la source de vérité pour la commande `/feature` (sélecteur de projet Block Kit)

## Stack commune
Node.js 20, TypeScript strict, Fastify, Docker

## Pièges Coolify

### Volumes bind-mount : une seule option `-v` dans `custom_docker_run_options`
Coolify n'applique pas plusieurs flags `-v` dans `custom_docker_run_options`.
Pour plusieurs volumes, utiliser le mode `dockercompose` (build_pack = dockercompose) —
les volumes définis dans `docker-compose.yml` sont alors tous montés correctement.

### Mode `dockercompose` : chemin du fichier compose
`docker_compose_location` est relatif à `base_directory`. Mettre `/docker-compose.yml`,
pas le chemin complet — Coolify les concatène et double le chemin sinon.

### `env_file` dans docker-compose.yml
En mode `dockercompose`, ne pas mettre `env_file: .env` — le fichier `.env` est gitignored
et absent du build. Coolify injecte ses variables directement dans le service.

### UUIDs des applications Coolify

| Application | UUID |
|---|---|
| assistant-ia | `gayg5mw9jikbio2le75olq8b` |
| bank-review | `ji9jg7ngkva7j4d2uic05d3v` |
| homepage | `h7dyrhas03di7jqq2wl2j72z` |
| tool-file-intake | `c57oryka5cw4scy02fi1gfzz` |

### Déclencher un rebuild via l'API Coolify

**Seul endpoint qui fonctionne pour un rebuild complet : `/start`**

```bash
curl -s -X POST "http://localhost:8000/api/v1/applications/{uuid}/start" \
  -H "Authorization: Bearer {token}"
```

- `/restart` → échoue avec "No such container" pour les apps `dockercompose`, même quand elles tournent
- `/deploy` → 404, n'existe pas dans cette version de Coolify
- `/start` → déclenche un build Docker + deploy complet, retourne `{"deployment_uuid":"..."}`

Vérifier le statut du déploiement :
```bash
curl -s "http://localhost:8000/api/v1/deployments/{deployment_uuid}" \
  -H "Authorization: Bearer {token}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status'))"
# "finished" = OK | "failed" = voir les logs dans d.get('logs')
```

Vérifier que l'app est bien up :
```bash
curl -s "http://localhost:8000/api/v1/applications/{uuid}" \
  -H "Authorization: Bearer {token}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('status'))"
# Attendu : "running:healthy"
```

### Générer un token API Coolify
Le token en base est un hash SHA-256 inutilisable directement. Pour créer un token valide :
```bash
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
NEW_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$NEW_TOKEN'.encode()).hexdigest())")
docker exec coolify-db sh -c "psql -U coolify coolify -c \"INSERT INTO personal_access_tokens (tokenable_type, tokenable_id, name, token, abilities, team_id, created_at, updated_at) SELECT 'App\\\\Models\\\\User', tokenable_id, 'script', '$NEW_HASH', '[\\\"*\\\"]', 0, NOW(), NOW() FROM personal_access_tokens WHERE id=1;\""
NEW_ID=$(docker exec coolify-db sh -c "psql -U coolify coolify -t -c \"SELECT id FROM personal_access_tokens ORDER BY id DESC LIMIT 1;\"" | tr -d ' ')
echo "Bearer ${NEW_ID}|${NEW_TOKEN}"
```

## Sécurité — règles obligatoires

### Docker : exposition des ports
Les services internes (BDD, cache, queues) ne doivent JAMAIS être publiés sur `0.0.0.0`.
Toujours préfixer par `127.0.0.1` dans docker-compose.yml :
```yaml
ports:
  - '127.0.0.1:6379:6379'   # ✅ localhost uniquement
  - '6379:6379'              # ❌ exposé sur Internet
```

### Authentification obligatoire
- Redis : toujours démarrer avec `command: redis-server --requirepass ${REDIS_PASSWORD}`
- PostgreSQL : remplacer `CHANGE_ME_STRONG_PASSWORD` avant tout déploiement
- Ne jamais committer de credentials réels — utiliser `.env` (hors git)

### Pare-feu (UFW)
Après tout ajout de service réseau, vérifier que le port n'est pas ouvert :
```bash
ufw status | grep <PORT>
```
Les ports internes (5432, 6379, etc.) doivent avoir une règle `DENY` explicite.

### `coolify-realtime` — image patchée manuellement

L'image `coolify-realtime` (soketi) contient des vulnérabilités npm (mysql2, basic-ftp,
form-data, systeminformation). Elle a été patchée le 2026-04-23 :
- Image committée : `ghcr.io/coollabsio/coolify-realtime:1.0.13-patched`
- Référencée dans `/data/coolify/source/docker-compose.prod.yml`

**Risque** : Une mise à jour de Coolify écrase `docker-compose.prod.yml` et rétablit
l'image originale vulnérable. Après toute update Coolify, vérifier :
```bash
grep "coolify-realtime" /data/coolify/source/docker-compose.prod.yml
```
Si l'image est repassée à `1.0.13` (sans `-patched`), relancer le patch ou attendre
une image upstream corrigée.

### Modifier `post_deployment_command` via l'API

Toujours utiliser Python pour construire le payload JSON — curl échoue silencieusement
si la commande contient des guillemets (le JSON est tronqué sans erreur) :

```python
import urllib.request, json

TOKEN = "..."
payload = json.dumps({"post_deployment_command": "ma commande ici"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/v1/applications/{uuid}",
    data=payload,
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    method="PATCH",
)
with urllib.request.urlopen(req) as r:
    print(json.loads(r.read()))
```

### Checklist avant déploiement d'un service réseau
- [ ] Port bindé sur `127.0.0.1` si usage interne uniquement
- [ ] Authentification configurée
- [ ] UFW : port bloqué ou justification documentée si ouvert
- [ ] Pas de mot de passe placeholder dans les fichiers committés
