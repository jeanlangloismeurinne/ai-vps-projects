# CLAUDE.md — assistant-ia

## Rôle

Orchestrateur central de tous les services d'appui utilisateur.
Reçoit des webhooks de `tool-file-intake` et déclenche les actions appropriées selon le channel Slack source.

## Déploiement

**`docker compose` standalone depuis le 2026-09-03** (Coolify est arrêté — cf. CLAUDE.md racine).

```bash
infrastructure/compose-deploy.sh assistant-ia -m "<message>" -f "<fichiers>"
```

- Stack : `projects/assistant-ia/docker-compose.yml`
- Port interne : 8000 (pas de port publié — tout passe par Traefik)
- Domaine : `assistant.jlmvpscode.duckdns.org`
- Réseaux : **`infra-net` ET `coolify`** → d'où le label obligatoire
  `traefik.docker.network=coolify` (sans lui, Traefik peut choisir `infra-net`, qu'il ne joint
  pas, et renvoyer un gateway timeout intermittent)
- ⚠️ **Ne pas renommer le service ni le conteneur** : `tool-file-intake` joint cette app par le
  nom `assistant-ia` (`AGENT_WEBHOOK_URL` → `http://assistant-ia:8000/webhook/file-stored`).
  Le nom de service **et** `container_name` valent `assistant-ia` pour préserver l'alias DNS sur
  les deux réseaux.
- Volumes : `/storage/Documents` (**ro**), `/storage/journal-vault` (rw — vault Obsidian du
  journal), `feedback-tickets/` (rw)
- Le déploiement notifie automatiquement Slack pour `journal` et `kanban` (table `NOTIFY` de
  `compose-deploy.sh`) — c'était le `post_deployment_command` de Coolify.

Variables d'environnement — `projects/assistant-ia/.env` (chmod 600, gitignored ; copie de
référence dans `/root/secrets/coolify-env-backup/assistant-ia.env`) :
- `SLACK_BOT_TOKEN` — token bot Slack (xoxb-...)
- `BANK_REVIEW_CHANNEL_ID` — ID du channel Slack #bank-review
- `BANK_REVIEW_BASE_URL` — URL de bank-review (défaut : https://bank.jlmvpscode.duckdns.org)
- `BANK_REVIEW_API_KEY` — clé API partagée avec bank-review

Pour ajouter une variable : `compose-deploy.sh assistant-ia -e KEY=VALUE …` (écrit dans le `.env`,
la valeur n'est jamais journalisée) — ne pas éditer le `.env` à la main pendant un déploiement.

## Architecture

```
app/
  main.py                         # FastAPI, routes, healthcheck
  config.py                       # Settings (pydantic-settings)
  routes/
    webhooks.py                   # POST /webhook/file-stored (reçu de tool-file-intake)
  handlers/
    bank_review.py                # Logique import bancaire : lit fichier → appelle bank-review → répond Slack
  services/
    bank_review_client.py         # HTTP client → POST /api/import/direct
    slack_client.py               # chat.postMessage via API Slack
```

## Flux — cas d'usage "bank-review"

1. Utilisateur dépose un CSV/XLSX dans #bank-review sur Slack
2. `tool-file-intake` stocke le fichier dans `/storage/Documents/` et POST sur `/webhook/file-stored`
3. `assistant-ia` vérifie `channel_id == BANK_REVIEW_CHANNEL_ID` et que l'extension est CSV/XLSX
4. **Ne lance pas l'import tout de suite** : poste une question *« Y a-t-il eu des vacances ? »*
   avec deux boutons (`bank_import_novac` / `bank_import_vac`). Le chemin du fichier + métadonnées
   sont encodés dans la `value` du bouton (et la `private_metadata` de la modale).
5. Selon le clic :
   - *Non, importer* → import sans période de vacances.
   - *Oui, préciser* → ouvre une modale (`callback_id: bank_vac_modal`) avec jusqu'à 3 plages de
     dates (période 1 requise). À la soumission, les plages sont transmises comme `vacation_ranges`.
6. `run_import_and_report` (dans `handlers/bank_review.py`) lit le fichier et POST
   `/api/import/direct` sur bank-review avec `X-Internal-Api-Key` + champ `vacation_ranges`
   (JSON `[["YYYY-MM-DD","YYYY-MM-DD"], ...]`, comme l'import web).
7. Reçoit `{session_id, added, date_min, date_max}` et envoie un message Block Kit avec :
   - Bouton *"Voir les dépenses"* → `https://bank.jlmvpscode.duckdns.org/import/history/{session_id}`
   - Bouton *"Suivi budget"* → `https://bank.jlmvpscode.duckdns.org/budget`

> L'import réel tourne en tâche de fond (`asyncio.create_task`) après l'`ack()` du bouton/modale
> (contrainte Slack des 3 s). Les handlers Bolt sont dans `slack_app.py`
> (`bank_import_novac`, `bank_import_vac`, vue `bank_vac_modal`).

## Intégrations actives

| Service | Endpoint appelé | Auth |
|---------|----------------|------|
| bank-review | `POST /api/import/direct` | `X-Internal-Api-Key` header |
| tool-file-intake | reçoit `POST /webhook/file-stored` | aucune (réseau interne) |
| Slack | `chat.postMessage` | Bearer SLACK_BOT_TOKEN |

## Registre des services — feedback et déploiement

Le fichier central est `app/services/registry.py`.
C'est le seul endroit à modifier pour brancher un nouveau service sur le système feedback/déploiement.

### Ajouter un service externe (sa propre stack compose)
1. Implémenter sur le service : `GET /api/feedback/closed-since?since=` (protégé par `X-Internal-Api-Key`) et `POST /api/feedback`
2. Ajouter une entrée dans `_build_registry()` (voir modèle commenté dans le fichier)
3. Ajouter les variables d'env dans `config.py`
4. Ajouter le service à la table `NOTIFY` de `infrastructure/compose-deploy.sh` pour que le
   déploiement notifie Slack (c'était le `post_deployment_command` de Coolify)
5. Ajouter le nom dans `_KNOWN_PROJECTS` dans `app/slack_app.py` (liste des projets proposés par `/feature`)

### Ajouter un service interne (hébergé dans assistant-ia)
1. Ajouter une entrée dans `_build_registry()` avec `base_url = ASSISTANT_BASE_URL` et `coolify_uuid = "gayg5mw9jikbio2le75olq8b"`
2. Ajouter le nom dans `_KNOWN_PROJECTS` dans `app/slack_app.py` (liste des projets proposés par `/feature`)

### UUID Coolify des apps — champ conservé, plus alimenté

`registry.py` porte encore un `coolify_uuid` par service, et `POST /webhook/deploy-complete`
accepte toujours `{"application_uuid": "…"}` en plus de `{"service": "…"}`. Depuis le 2026-09-03,
**plus personne n'emprunte ce chemin** : `compose-deploy.sh` poste `{"service": "…"}`. Le code est
laissé en place (il redevient utile si Coolify est remonté) mais ne pas s'y fier pour router une
notification.

- `bank-review` : `ji9jg7ngkva7j4d2uic05d3v`
- `assistant-ia` : `gayg5mw9jikbio2le75olq8b`

### Endpoints feedback (cette session)
| Endpoint | Rôle |
|---|---|
| `POST /webhook/deploy-complete` | Notification déploiement (`compose-deploy.sh` ou manuel) |
| `POST /api/feedback/{project}` | Soumettre un ticket (journal, kanban) |
| `GET /api/feedback/{project}/closed-since?since=` | Tickets fermés depuis une date |

## Ajouter un nouveau cas d'usage (file-intake)

1. Créer `app/handlers/mon_handler.py` avec une fonction `async def handle_file_stored(payload)`
2. Dans `app/routes/webhooks.py`, ajouter le routage par `channel_id`
3. Documenter ici

## Migrations — assistant-ia

`db.py` exécute au démarrage **tous les fichiers `.sql`** du dossier `migrations/`
dans l'ordre alphabétique (001, 002, 003…). Toutes les instructions sont idempotentes
(`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

Pour ajouter une migration : créer `migrations/003_xxx.sql`, ne pas modifier les fichiers existants.

Dernière en date : `015_agent_tool_calls.sql` — piste d'audit des appels d'outils de l'agent
(`taint_sources` en tableau JSONB, pas un booléen ; `doc_version` pour joindre à `agent_system_doc`).

## Agent conversationnel — outillage (`app/services/agent_tools/`)

Roadmap : `roadmap/agent-outillage.md` (v1 livrée le 2026-08-24, tickets 0 à 6).

**Règle non négociable** : la liste d'outils exposée au modèle est construite **exclusivement**
par `agent_tools/registry.py`. Aucun chemin de code ne dérive un outil du `agent_system_doc`. Le
doc système peut dire *quand* utiliser un outil ; il ne peut pas en faire exister un. Vérifié par
`checks/check_agent_tools.py` §A (doc empoisonné → liste d'outils inchangée).

| Fichier | Rôle |
|---|---|
| `manifest.py` | `ToolManifest` (effect, taints_context, reversible, visibility, rate_limit, egress) + `TurnState` |
| `policy.py` | **Fonction pure** : manifeste + état du tour → `EXECUTE` / `CONFIRM_FIRST` / `REFUSE` |
| `base.py` | `ToolSpec`, `ToolContext`, `PreparedCall`, `ToolResult`, `ToolError` |
| `registry.py` | Seule source des outils. `tools_json()` **ne prend aucun argument**, par construction |
| `loop.py` | Boucle bornée (8 itérations, budget mur/tokens, troncature, délimiteur de taint) |
| `audit.py` | Écritures dans `agent_tool_calls` — best-effort, ne fait jamais perdre une réponse |
| `create_reminder.py` | Outil d'écriture → carte Kanban dans la colonne `Rappels` |
| `web_search.py` | Outil de lecture (Exa/Serper) — **taintant**. Pas de `fetch_url` (SSRF, §4 roadmap) |
| `capture_note.py` | Outil d'écriture → vault Obsidian. Deux modes = deux **adressages** : `note` (daté, `notes/{année}/{date}-{slug}.md`, classé + indexé) et `document` (par nom, `documents/{slug}.md`, ajout en fin de fichier). Contenu = **Markdown libre** |
| `list_documents.py` | Outil de lecture → noms des documents existants, **sans leur contenu**. Non taintant (contenu écrit par l'utilisateur lui-même). À appeler avant d'écrire dans un document |

⚠️ **L'adressage par nom exige l'outil de lecture.** Sans `list_documents`, le modèle réinvente
le nom à chaque tour : deux rejeux de la même demande ont produit `startups-spatial.md` puis
`startups-spatial-a-creuser.md`, deux fichiers pour une seule liste, sans aucune erreur levée.
Toute future primitive adressée par un libellé humain doit livrer son outil de lecture avec elle.

⚠️ **`journal_vault.append_to_document` ne relit ni ne réécrit jamais le fichier** : création par
`O_CREAT|O_EXCL`, ajout par `O_APPEND` (+ un octet lu en fin de fichier pour savoir s'il finit par
un saut de ligne). L'entête n'a **aucun champ mutable** — un `updated_at` transformerait chaque
ajout en réécriture. Le critère d'acceptation est un `git diff` du vault en `+n / -0`.

**Pour ajouter un outil** : écrire un module avec `MANIFEST` + `_execute` (+ `_resolve` si le code
doit décider quelque chose que le modèle propose), exporter un `SPEC`, l'ajouter à `_ALL` dans
`registry.py`. Le régime de confirmation en découle — ne pas le coder à la main.

**Régime de confirmation** (dérivé, jamais écrit outil par outil) : confirmation **avant** écriture
si `effect == outbound` **ou** `reversible == false` **ou** `visibility == false` **ou** le contexte
porte un *taint* (donnée non tapée par l'utilisateur : web, fichier, message tiers). Sinon exécution
immédiate + confirmation **a posteriori** avec boutons *Annuler* / *Modifier*. Les lectures ne
passent jamais par une confirmation.

**Un échec d'outil est une erreur explicite en `role=tool`, jamais un résultat vide** — leçon
SearXNG : un résultat vide silencieux fait conclure le modèle à l'absence de source.

Boutons/modales dans `app/handlers/agent_tool_actions.py`, câblés dans `slack_app.py` :
`agent_tool_confirm`, `agent_tool_cancel`, `agent_reminder_cancel`, `agent_reminder_edit`.
Une confirmation en attente **est** la ligne d'audit (`verdict='confirmation_requise'`) ; le payload
résolu y est figé, TTL 1 h, double-clic inerte.

Variables d'environnement associées :
- `AGENT_TIMEZONE` — défaut `Europe/Paris`. Résolution **et** affichage des dates de rappel.
- `SEARCH_PROVIDER` — `exa` | `serper` | `none` (défaut). À `none`, `web_search` **n'est pas
  exposé** au modèle.
- `EXA_API_KEY` / `SERPER_API_KEY` — clé propre à assistant-ia, jamais partagée avec un autre projet.

## Base de connaissance — visualisation en ligne

Le vault (`/storage/journal-vault` : journal + miroir kanban sous `tasks/`) se consulte en ligne
sur **`kb.jlmvpscode.duckdns.org`** — site statique Quartz (lecture seule, basic-auth), servi par
`projects/kb-viewer/` (rebuild événementiel par unit systemd, hors `compose-deploy.sh`). Détails : entrée
`kb-viewer` du CLAUDE.md racine + `projects/kb-viewer/README.md`.

## Journal — structure des routes

| Fichier | Rôle |
|---|---|
| `routes/journal.py` | Ancien journal libre (prompt Slack → texte) — ne pas étendre |
| `routes/journal_fill.py` | Remplissage quotidien + historique (journal v2) |
| `routes/journal_settings.py` | Paramétrage parcours / objectifs / questions |
| `services/journal_v2.py` | Couche service du journal v2 |

## Journal v2 — rappels Slack

Les rappels Slack envoient un **lien vers l'UI web** (`/journal/fill/{objectif_id}`),
pas un formulaire interactif dans Slack. Les types de questions structurés (échelle,
choix, classement…) ne sont pas gérables dans un thread Slack.

Le job `check_objectif_reminders` tourne chaque minute, compare `heure_rappel` (HH:MM)
à l'heure courante, et utilise `journal_notifications (UNIQUE objectif_id, session_date)`
pour garantir un seul envoi par objectif par jour.

## Workflow de déploiement production

Avant tout déploiement d'une nouvelle fonctionnalité, mettre à jour :
1. La **landing page** (`_LANDING_HTML` dans `app/main.py`) : hero subtitle, liens, description de la section concernée.
2. La **page dédiée du service** si elle existe (ex : `routes/journal.py` pour `/journal`) : titre, liens, description des fonctionnalités.

Ordre obligatoire — un seul appel s'en charge :
```bash
infrastructure/compose-deploy.sh assistant-ia -m "<message>" -f "<fichiers>"
```
(commit → push → build → attente de santé → sonde `/health` → notif Slack journal + kanban).
Voir `DEPLOY.md` à la racine.

## Système de pilotage

Voir `CONTROL_SYSTEM.md` à la racine du repo pour le protocole complet.
Déclencheur : **« reprends le projet assistant-ia à partir du fichier de reprise »**
→ Lire `00-REPRISE.md` (racine du projet), puis la roadmap qu'il déclare active, annoncer le lot de
conversation, exécuter, cocher les capacités livrées.
