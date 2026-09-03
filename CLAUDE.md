# CLAUDE.md — ai-vps-projects

## Contexte global
Repo multi-projets sur VPS Hetzner (204.168.250.110).
Domaine : jlmvpscode.duckdns.org
Déploiement : **`docker compose` standalone** — chaque projet a son `docker-compose.yml` et son
`.env` local (chmod 600, hors git). Migration depuis Coolify le **2026-09-03** (§ ci-dessous).

## Règle — fichier `00-REPRISE.md` (obligatoire en fin de conversation)

Après avoir **implémenté une nouvelle version / un nouveau sprint** d'un projet, je dois
**actualiser le `00-REPRISE.md` de ce projet** (à la racine du dossier du projet) avant de
clôturer la conversation : maj de l'état atteint, du prochain jalon, des blocages et des
commandes de reprise. Toute nouvelle session du projet démarre en **relisant ce fichier**
(bouton « reprendre là où on s'était arrêté »).

## Règle — fichier `00-REPRISE.md` par projet
Chaque projet garde un `00-REPRISE.md` (racine du projet) qui sert de **prompt de reprise**
pour retrouver l'état exact. **RÈGLE : l'actualiser OBLIGATOIREMENT en fin de conversation,
dès qu'une nouvelle version/état a été implémenté** (préfixer un bloc `> ## ⚡ MàJ <date>` en
haut du fichier avec ce qui a changé, ce qui a été vérifié, et ce qui reste). Ne jamais laisser
un « fin de session » sans `00-REPRISE.md` à jour : c'est lui qui permet de reprendre sans
ré-explorer.

## Déploiement — autonomie obligatoire

**Je déploie moi-même, sans demander à l'utilisateur.** Un seul appel :

```bash
infrastructure/compose-deploy.sh <app> -m "<message>" -f "<fichiers>" [-e KEY=VALUE …]
```

Le script commite, pousse, écrit les variables dans le `.env`, build, **attend que le conteneur
soit sain, sonde l'app et exige le code HTTP attendu**, puis notifie Slack. Il renvoie une seule
ligne `RESULT: success — …` / `RESULT: failure — …`. Protocole complet et fallback : **`DEPLOY.md`**.

Ne jamais conclure au succès d'un déploiement sur la seule fin du build : c'est la réponse HTTP
qui fait foi (le script s'en charge — ne pas la court-circuiter).

### Architecture de déploiement (état 2026-09-03)

- Chaque projet : `projects/<app>/docker-compose.yml` + `.env` local (600, gitignored).
- Le proxy reste **`coolify-proxy`** (Traefik v3.6) : il a survécu à la migration et route par
  labels Docker sur le réseau `coolify`, avec Let's Encrypt. Il n'est PAS géré par Coolify au
  quotidien — ne pas l'arrêter, c'est lui qui sert tous les domaines.
- Les labels Traefik sont **explicites** dans chaque compose (routers http+https, middlewares,
  service, port). Coolify ne les injecte plus.
- ⚠️ **Middlewares : pas d'héritage.** Les middlewares `gzip` / `redirect-to-https` étaient
  déclarés par des conteneurs Coolify et seulement *référencés* ailleurs. Chaque stack déclare
  désormais les siens, préfixés par l'app (`hubgzip`, `asgzip`, `pfgzip`…). Un nouveau projet doit
  déclarer les siens — référencer un middleware qu'aucun conteneur ne définit casse le routeur.
- ⚠️ **Conteneur sur plusieurs réseaux → `traefik.docker.network=coolify` obligatoire.** Sinon
  Traefik peut choisir `infra-net`, qu'il ne joint pas → gateway timeout intermittent.
- ⚠️ **Jamais deux conteneurs avec les mêmes labels Traefik** : le proxy répartirait le trafic
  entre ancien et nouveau code, silencieusement. `compose-deploy.sh` le vérifie à chaque déploiement.

### Revenir à Coolify

`infrastructure/coolify-restore.sh` (voir son en-tête). **Rien n'a été détruit** : la base
`coolify-db`, `/data/coolify` (dont l'`APP_KEY` sans laquelle les variables chiffrées seraient
illisibles) et les sauvegardes `/root/secrets/coolify-rollback-2026-09-03/` sont intacts. Seuls
des conteneurs et des images ont été supprimés. Le retour = un `docker compose up -d` sur les
fichiers d'installation de Coolify, avec les images **épinglées** sur ce qui tournait.

Outils associés :
- `infrastructure/coolify-export-env.sh` — déchiffre les variables d'env d'une app depuis la base
  Coolify (nécessite Coolify démarré). Copies de référence : `/root/secrets/coolify-env-backup/`.
- `infrastructure/deploy.sh` — l'ancien script Coolify, **neutralisé mais conservé** : il redevient
  le bon outil après un restore.

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
  Les apps sur le réseau `coolify` accèdent à Redis directement — pas besoin de `docker network connect infra-net`.
  (Le réseau s'appelle toujours `coolify` : c'est celui du proxy Traefik, conservé tel quel par la
  migration pour ne pas avoir à refaire tout le routage. Le nom est historique, pas fonctionnel.)

## Clés API inter-services
- `INTERNAL_API_KEY` (bank-review ↔ assistant-ia) : dans le `.env` de chaque projet (`BANK_REVIEW_API_KEY` sur assistant-ia, `INTERNAL_API_KEY` sur bank-review) — ne pas documenter la valeur ici
  — Header : `X-Internal-Api-Key`
  — Endpoint protégé : `POST /api/import/direct` sur bank-review

## Secrets — comms-gateway (état 2026-09-03)

Chantier gateway de communication multi-tenant (email Resend / Slack / SMS / WhatsApp / Signal).
Règle inchangée : **les secrets des providers ne sont jamais committés.** Ce qui a changé le
2026-09-03, c'est seulement *où* ils sont injectés — plus les secrets chiffrés de Coolify, mais
un `.env` local en `chmod 600`, gitignored, hors image.

- `projects/comms-gateway/.env` (600, gitignored) porte `DATABASE_URL`, `REDIS_URL`,
  `MASTER_KEY`, `ADMIN_TOKEN`, `RESEND_API_KEY`, `RESEND_DEFAULT_FROM`, `SLACK_BOT_TOKEN`,
  `SLACK_SIGNING_SECRET`, `PUBLIC_BASE_URL`, `WEBHOOK_TOKEN`. Copie de référence :
  `/root/secrets/coolify-env-backup/comms-gateway.env` (valeurs rapatriées de Coolify sans
  qu'aucune ne change).
- `docker-compose.yml` du gateway a de nouveau un `env_file: [.env]`.
- Périmètre d'exposition **inchangé** par la migration et re-vérifié après : seuls `/webhooks/*`
  sont routés publiquement (label `PathPrefix`) ; `/v1` n'est joignable que depuis le réseau
  interne `coolify`. Vérifications OK : `/health` (200 en interne), `/v1` non routé,
  refus `rejected_policy` / `rejected_rate_limit`.
- Blocages actés hors code : compte Resend du projet = **compte de test, aucun domaine
  d'envoi vérifié** (→ livraison réelle impossible tant qu'un domaine n'est pas vérifié dans
  resend.com/domains, avec DNS ; le gateway journalise bien l'échec 403) ; app Slack
  `comms-gateway` à créer (envoi+reception, bot dédié — ne pas toucher à assistant-ia) ;
  connecteurs SMS/WhatsApp/Signal en **mock** tant que le téléphone Free+eSIM+Tailscale
  n'est pas prêt.
- Détaillé dans : `projects/comms-gateway/README.md`, `projects/comms-gateway/docs/SLACK_WIRING.md`,
  `projects/comms-gateway/docs/PHONE_PART2_CHECKLIST.md`, SDK `templates/comms-client/` (un
  projet = env `GATEWAY_URL` + `GATEWAY_TOKEN`, sans détenir de secret provider).

## Projets actifs
- projects/assistant-ia/ : orchestrateur Slack — reçoit webhooks de tool-file-intake et déclenche les actions par service (bank-review, etc.) — FastAPI, port 8030
- projects/bank-review/ : analyse de relevés bancaires (upload Excel/CSV + analyse Claude) — Python 3.12, FastAPI, pandas
- projects/feedback-module/ : microservice feedback (port 3333) — widget flottant + API + stockage Markdown
- projects/tool-file-intake/ : réception fichiers Slack → stockage /storage/Documents/ + index SQLite — Python 3.12, FastAPI, Slack Bolt (port 8020)
- projects/ev-prices/ : suivi des prix véhicules électriques (14 constructeurs, scraping hebdomadaire) — Python 3.12, FastAPI, Playwright, PostgreSQL (port 8040) · URL : ev.jlmvpscode.duckdns.org
- projects/portfolio-tracker/ : suivi investissement long terme, agents IA Dust, 3 régimes d'analyse — **une seule stack compose à deux services** : backend `portfolio-backend` (8050, routé sur `/api` avec `stripprefix`) + frontend `portfolio-frontend` (8051, catch-all) · URL : portfolio.jlmvpscode.duckdns.org · c'étaient deux apps Coolify séparées jusqu'au 2026-09-03, réunies parce que le routage par chemin n'a de sens qu'à deux
- projects/hub/ : portail interne (page d'accueil + outil de pilotage chantiers/sprints/tickets/roadmap) — FastAPI, port 8000, bind-mount `projects/` en lecture/écriture · URL : jlmvpscode.duckdns.org (conteneur « homepage »)
- projects/kb-viewer/ : viewer statique de la base de connaissance (Quartz build depuis `/storage/journal-vault` → nginx:alpine) — basic-auth + TLS via coolify-proxy · URL : kb.jlmvpscode.duckdns.org · rebuild événementiel par path unit systemd `kb-viewer-build.path` (watch `.git/logs/HEAD` du vault, non exposé) · **non géré par `compose-deploy.sh`**
- projects/comms-gateway/ : **gateway central multi-tenant de communication externe** — email (Resend), Slack, puis SMS/WhatsApp/Signal — Node 20/TS/Fastify, standalone `docker compose` sur réseau `coolify` (pattern newsletter-summary/kb-viewer) · base `db_comms_gateway` sur shared-postgres, rate-limit sur shared-redis · API interne `/v1` (Bearer token scoped), seuls `/webhooks/*` exposés (Traefik PathPrefix, `comms.jlmvpscode.duckdns.org`) · les projets consommateurs embarquent le SDK `templates/comms-client/` (GATEWAY_URL + GATEWAY_TOKEN) · câbler les connecteurs réels SMS/WhatsApp/Signal une fois le téléphone prêt (`docs/PHONE_PART2_CHECKLIST.md`) · doc : `projects/comms-gateway/README.md`

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
C'était le `post_deployment_command` de Coolify ; c'est désormais **`compose-deploy.sh` § 6**
(table `NOTIFY`), qui poste après avoir vérifié que l'app répond :

```bash
curl -sf -X POST https://assistant.jlmvpscode.duckdns.org/webhook/deploy-complete \
  -H 'Content-Type: application/json' -d '{"service":"<service>"}'
```

- `bank-review` → service `bank-review`
- `assistant-ia` → services `journal` **et** `kanban` (deux appels)

Endpoint : `POST /webhook/deploy-complete` sur assistant-ia — accepte `{"service":"nom"}` ou
`{"application_uuid":"..."}`. Pour brancher un nouveau service, ajouter une entrée à `NOTIFY`
dans `compose-deploy.sh` — une notif non délivrée est signalée mais ne fait pas échouer le
déploiement (le code est livré, c'est le message qui manque).

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

La variable `FEEDBACK_CHANNEL_ID` a `C0AUCE6NELT` en valeur par défaut — aucune config nécessaire.

## Ajouter un projet
1. Créer projects/nouveau-projet/
2. Créer la base : docker exec shared-postgres psql -U admin -c 'CREATE DATABASE db_nouveau;'
3. Écrire `projects/nouveau-projet/docker-compose.yml` (partir de `projects/hub/` comme modèle) :
   `name:` du projet, réseau `coolify` externe, `env_file: [.env]`, labels Traefik explicites avec
   **ses propres middlewares** (`<app>gzip`, `<app>redirect`) — ne jamais référencer un middleware
   défini ailleurs. Créer le `.env` en `chmod 600` (il est gitignored).
   Puis ajouter l'app aux tables de `infrastructure/compose-deploy.sh` (`STACK_DIR`, `SERVICE`,
   `ENV_FILE`, `PROBE`, `EXPECT`, `CONTAINERS`, `DOMAIN`) — sinon elle n'est pas déployable.
4. Documenter ici
5. **Ajouter le nom du dossier dans `_KNOWN_PROJECTS`** dans `projects/assistant-ia/app/slack_app.py` — cette liste est la source de vérité pour la commande `/feature` (sélecteur de projet Block Kit)
6. **Si le projet a une base de connaissance** : suivre `KNOWLEDGE_ARCHITECTURE.md` et partir de `templates/knowledge-base/`. La KB doit savoir exporter l'« enveloppe document commune » (federation-ready) dès sa conception.

## Déploiement — protocole obligatoire

En fin de session, une fois une feature livrée (session en direct **ou** via tickets), suivre
**`DEPLOY.md`** (racine du repo). Chemin nominal : un seul appel
`infrastructure/compose-deploy.sh <app> -m "<msg>" -f "<fichiers>" [-e KEY=VALUE …]`
(commit index seul → push → `.env` → build → attente de santé → sonde HTTP → notif Slack).
En cas d'échec (exit ≠ 0), basculer sur le sous-agent Sonnet décrit dans DEPLOY.md.
But : préserver le contexte/quota Opus en gardant le verbeux (diff, logs de build) hors session.

Les frictions de ce chemin relevées jusqu'au 2026-09-03 (permissions manquantes, rebuild sans
commit, captures de vérification) sont **traitées** — inutile de rouvrir le sujet. En cas de
nouvelle friction, la noter dans **`CHANTIER_OUTILLAGE_DEV.md`** (tampon : on y écrit le constat,
on supprime la section une fois appliquée). Ne le lire que pour y ajouter un point.

## Système de contrôle — chantiers, sprints, tickets

Protocole complet dans **`CONTROL_SYSTEM.md`** à la racine du repo. Lire ce fichier au démarrage
de toute session de travail sur un projet.

Modèle : un **chantier** (`roadmap/{nom}.md`) = doc vivant que l'utilisateur valide (direction +
décisions + sprints = statut). Le Hub génère un **ordre de sprint** (`SESSION.md`, jetable) — le
pont vers Claude Code, car le Hub ne peut pas lancer l'exécution lui-même.

Commande de déclenchement : **"execute le sprint en cours pour {projet}"**
→ Lire `SESSION.md` **et** le chantier qu'il pointe (source de vérité), exécuter le sprint, cocher
la checklist dans le chantier. À la clôture : gotchas → `DECISIONS.md`, chantier fini → `roadmap/archive/`.

**Fin de sprint = ré-armement.** Réécrire `SESSION.md` sur le prochain sprint non terminé du
chantier (l'utilisateur ne repasse pas par le Hub entre deux sprints), puis conclure par
« Sprint N terminé, SESSION.md est actualisé pour lancer le Sprint N+1. Recommandation :
nouvelle conversation / poursuivre ici — {justification} ». Détail : `CONTROL_SYSTEM.md`
§ *Ré-armement automatique*.

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

## Coolify — playbook DORMANT

**Coolify est arrêté depuis le 2026-09-03.** `COOLIFY_PLAYBOOK.md` (rebuild PHP sans token,
token API, création d'app via DB, table des UUIDs, monitoring de la file, patches) ne décrit plus
le fonctionnement courant du VPS. → À lire **uniquement** après un `coolify-restore.sh`, ou pour
comprendre comment une app était configurée avant la migration.

Ce qui reste vrai et utile au quotidien (labels Traefik, volumes bind-mount, Playwright Trixie,
sécurité réseau) a été repris ci-dessus et dans les compose de chaque projet.

## Sécurité — règles permanentes
- Services internes (BDD, cache, queues) : **JAMAIS** publiés sur `0.0.0.0` — toujours `127.0.0.1:` dans docker-compose.
- Redis démarré avec `--requirepass` ; PostgreSQL sans mot de passe placeholder.
- Ne jamais committer de credentials réels (`.env` hors git).
- UFW : après tout ajout de service réseau, vérifier que le port interne est en `DENY`.
- Checklist complète avant déploiement d'un service réseau : `COOLIFY_PLAYBOOK.md` § Sécurité
  (toujours valable — elle ne dépend pas de Coolify).
- Un `.env` de projet est en `chmod 600`, gitignored, et n'entre jamais dans une image. Les
  copies de référence vivent dans `/root/secrets/` (dir 700), jamais dans le repo.
