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
  Bases : db_assistant (projet assistant-ia)
- Redis 7 : shared-redis (port 6379)
- Réseau Docker : infra-net

## Projets actifs
- projects/assistant-ia/ : bot Slack + résumé newsletters
- projects/bank-review/ : analyse de relevés bancaires (upload Excel/CSV + analyse Claude) — Python 3.12, FastAPI, pandas
- projects/feedback-module/ : microservice feedback (port 3333) — widget flottant + API + stockage Markdown
- projects/tool-file-intake/ : réception fichiers Slack → stockage /storage/Documents/ + index SQLite — Python 3.12, FastAPI, Slack Bolt (port 8020)

## Slack bot partagé

Token `xoxb-619072475858-...` utilisé par `/opt/cyber-agent/` et `tool-file-intake`.
Signing secret à récupérer sur api.slack.com → Basic Information → Signing Secret.
Channel Slack principal : `C0AUFGZNBGT`

## Feedback utilisateur

Les tickets (bugs, suggestions, features) sont stockés dans le dossier
`feedback-tickets/` de chaque projet concerné, au format Markdown.

Pour bank-review : `projects/bank-review/feedback-tickets/`

Chaque fichier = un ticket. Champ `status: open` = en attente de traitement.
Marquer `status: closed` une fois résolu.

## Ajouter un projet
1. Créer projects/nouveau-projet/
2. Créer la base : docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_nouveau;'
3. Créer une app Coolify avec Base Directory = projects/nouveau-projet
4. Documenter ici

## Stack commune
Node.js 20, TypeScript strict, Fastify, Docker

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

### Checklist avant déploiement d'un service réseau
- [ ] Port bindé sur `127.0.0.1` si usage interne uniquement
- [ ] Authentification configurée
- [ ] UFW : port bloqué ou justification documentée si ouvert
- [ ] Pas de mot de passe placeholder dans les fichiers committés
