# CLAUDE.md — ai-vps-projects

## Contexte global
Repo multi-projets sur VPS Hetzner (204.168.250.110).
Domaine : jlmvpscode.duckdns.org
Déploiement : Coolify — chaque projet est une application séparée.

## Accès Coolify — autonomie obligatoire

**J'ai accès direct à Coolify via son API (localhost:8000). Je dois l'utiliser sans demander à l'utilisateur.**

Quand un redéploiement, un restart, ou un diagnostic Coolify est nécessaire :
1. Générer un token (procédure dans `COOLIFY_PLAYBOOK.md` — ou méthode PHP sans token, préférée)
2. Déclencher le déploiement via l'API
3. Surveiller jusqu'à `status: finished`

Ne jamais demander à l'utilisateur de "cliquer dans Coolify" ou "me donner le token" — je peux le faire moi-même.

## Agent de sécurité

Rapports générés par `/opt/cyber-agent/` — structure :
- `/opt/cyber-agent/reports/parsed/YYYY-MM-DD_HH-MM_merged.json` — rapport fusionné (le plus récent = dernier trié par date)
- `data['all_vulns']['critical']` / `['high']` — listes de vulnérabilités par sévérité
- `data['counts']` — compteurs par niveau, `data['risk_score']` — score global /100

Chaque vuln contient : `id`, `package`, `installed_version`, `fixed_version`, `description`, `target`, `fix`.

## Infrastructure partagée
Réseau Docker : `infra-net` (+ `coolify`).
- PostgreSQL 16 : shared-postgres (port 5432) — réseaux : infra-net + coolify
  Bases : db_assistant (réservée pour assistant-ia, pas encore utilisée) · db_ev_prices (ev-prices)
- Redis 7 : shared-redis (port 6379) — réseaux : infra-net + coolify (2026-05-03)
  Les apps Coolify (réseau `coolify`) accèdent à Redis directement — pas besoin de `docker network connect infra-net`.

## Clés API inter-services
- `INTERNAL_API_KEY` (bank-review ↔ assistant-ia) : stockée dans les variables d'env Coolify (`BANK_REVIEW_API_KEY` sur assistant-ia, `INTERNAL_API_KEY` sur bank-review) — ne pas documenter la valeur ici
  — Header : `X-Internal-Api-Key`
  — Endpoint protégé : `POST /api/import/direct` sur bank-review

## Projets actifs
- projects/assistant-ia/ : orchestrateur Slack — reçoit webhooks de tool-file-intake et déclenche les actions par service (bank-review, etc.) — FastAPI, port 8030
- projects/bank-review/ : analyse de relevés bancaires (upload Excel/CSV + analyse Claude) — Python 3.12, FastAPI, pandas
- projects/feedback-module/ : microservice feedback (port 3333) — widget flottant + API + stockage Markdown
- projects/tool-file-intake/ : réception fichiers Slack → stockage /storage/Documents/ + index SQLite — Python 3.12, FastAPI, Slack Bolt (port 8020)
- projects/ev-prices/ : suivi des prix véhicules électriques (14 constructeurs, scraping hebdomadaire) — Python 3.12, FastAPI, Playwright, PostgreSQL (port 8040) · URL : ev.jlmvpscode.duckdns.org
- projects/portfolio-tracker/ : suivi investissement long terme, agents IA Dust, 3 régimes d'analyse — **deux apps Coolify distinctes** (dockerfile) : portfolio-backend (port 8050) + portfolio-frontend (port 8051) · URL : portfolio.jlmvpscode.duckdns.org

## Slack bot partagé

Le bot utilise l'**HTTP Events API** (Slack POST vers une Request URL publique, validée par
signing secret) — **pas** Socket Mode. La Request URL et l'Interactivity Request URL pointent sur
`POST /slack/events` d'assistant-ia (`AsyncSlackRequestHandler` + Bolt), qui proxie les payloads
liés aux fichiers vers `/slack/events` de tool-file-intake. Les boutons, modales (`views_open` /
`view_submission`) et slash commands passent tous par cette URL.

Tokens / secrets stockés dans `/opt/cyber-agent/.env` :
- `SLACK_BOT_TOKEN` = `xoxb-619072475858-...`
- `SLACK_SIGNING_SECRET` — **requis** (validation des requêtes HTTP Events API)
- `SLACK_APP_TOKEN` = `xapp-1-A0ATSM6JECA-...` (scope `connections:write`) — **conservé pour
  rollback Socket Mode uniquement**, non utilisé par le flux HTTP actuel.

Channel Slack principal : `C0AUFGZNBGT`

Le bot doit être **invité explicitement** dans chaque channel pour recevoir ses événements :
`/invite @ai_vps_jlm`

## Feedback utilisateur

Les tickets (bugs, suggestions, features) sont stockés dans le dossier
`feedback-tickets/` de chaque projet concerné, au format Markdown.

Pour bank-review : `projects/bank-review/feedback-tickets/`
Pour journal/kanban : `projects/assistant-ia/feedback-tickets/{journal|kanban}/`

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
Utilisable dans n'importe quel channel. La commande doit être enregistrée dans api.slack.com →
Slash Commands (Request URL = `/slack/events` d'assistant-ia, comme les events et l'interactivity).
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
6. **Si le projet a une base de connaissance** : suivre `KNOWLEDGE_ARCHITECTURE.md` et partir de `templates/knowledge-base/`. La KB doit savoir exporter l'« enveloppe document commune » (federation-ready) dès sa conception.

## Déploiement — protocole obligatoire

En fin de session, une fois une feature livrée (session en direct **ou** via tickets), suivre
**`DEPLOY.md`** (racine du repo). Chemin nominal : un seul appel `infrastructure/deploy.sh <app>
-m "<msg>" -f "<fichiers>" [-e KEY=VALUE …]` (commit index seul → push → env vars auto → rebuild
PHP → monitor). En cas d'échec (exit ≠ 0), basculer sur le sous-agent Sonnet décrit dans DEPLOY.md.
But : préserver le contexte/quota Opus en gardant le verbeux (diff, logs de build) hors session.

## Système de contrôle — tickets, roadmap, session brief

Protocole complet dans **`CONTROL_SYSTEM.md`** à la racine du repo. Lire ce fichier au démarrage
de toute session de travail sur un projet.

Commande de déclenchement : **"execute le brief session pour {projet}"**
→ Lire `SESSION_BRIEF.md` dans le répertoire du projet, puis suivre le protocole CONTROL_SYSTEM.md.

## Bases de connaissance — architecture commune

Toute KB de projet suit la charte **`KNOWLEDGE_ARCHITECTURE.md`** (racine du repo). À lire avant
de concevoir ou d'implémenter une base de connaissance.

Principe : on ne centralise **jamais** le stockage. Chaque projet garde sa connaissance dans son
backend naturel (Postgres/pgvector, Notion, Nextcloud, mails mailbox.org, fichiers Markdown), en
suivant le *LLM Wiki Pattern* Karpathy (pivot Markdown + index requêtable + Lint + schema file).
La seule chose mutualisée est une **couche de recherche fédérée** (base `db_knowledge_federation`
sur `shared-postgres` + pgvector) — à construire **uniquement** quand un besoin multi-source réel
apparaît, jamais par anticipation.

La seule contrainte imposée à chaque projet **dès le départ** : savoir exporter l'**« enveloppe
document commune »** (vue SQL, script ou connecteur). C'est ce qui rend l'interconnexion future
triviale. Squelette à copier : **`templates/knowledge-base/`**.

- Implémentation de référence : `projects/portfolio-tracker/` (Knowledge Platform, `roadmap/…-knowledge-platform.md`).
- Checklist « federation-ready » : `KNOWLEDGE_ARCHITECTURE.md` §5.

## Stack commune
Node.js 20, TypeScript strict, Fastify, Docker

## Coolify — déploiement, dépannage & sécurité infra

Tout le playbook Coolify (rebuild PHP sans token, génération de token API, labels Traefik,
volumes bind-mount, création d'app dockercompose via DB, Playwright Trixie, **table des UUIDs**,
monitoring de la file de déploiement) et les procédures de sécurité infra (patches Coolify,
`post_deployment_command`) sont dans **`COOLIFY_PLAYBOOK.md`** (racine du repo).
→ À lire **uniquement** au moment d'un déploiement ou d'un diagnostic Coolify.

## Sécurité — règles permanentes
- Services internes (BDD, cache, queues) : **JAMAIS** publiés sur `0.0.0.0` — toujours `127.0.0.1:` dans docker-compose.
- Redis démarré avec `--requirepass` ; PostgreSQL sans mot de passe placeholder.
- Ne jamais committer de credentials réels (`.env` hors git).
- UFW : après tout ajout de service réseau, vérifier que le port interne est en `DENY`.
- Checklist complète avant déploiement d'un service réseau : `COOLIFY_PLAYBOOK.md` § Sécurité.
