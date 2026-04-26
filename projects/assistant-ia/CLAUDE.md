# CLAUDE.md — assistant-ia

## Rôle

Orchestrateur central de tous les services d'appui utilisateur.
Reçoit des webhooks de `tool-file-intake` et déclenche les actions appropriées selon le channel Slack source.

## Déploiement

- Plateforme : Coolify
- Base Directory : `projects/assistant-ia`
- docker-compose : `/docker-compose.yml`
- Port interne : 8030 → 8000
- Domaine : `assistant.jlmvpscode.duckdns.org`
- Réseau Docker : `infra-net`
- Volume monté : `/storage/Documents` (lecture seule)

Variables d'environnement Coolify :
- `SLACK_BOT_TOKEN` — token bot Slack (xoxb-...)
- `BANK_REVIEW_CHANNEL_ID` — ID du channel Slack #bank-review
- `BANK_REVIEW_BASE_URL` — URL de bank-review (défaut : https://bank.jlmvpscode.duckdns.org)
- `BANK_REVIEW_API_KEY` — clé API partagée avec bank-review

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
4. Lit le fichier depuis le chemin reçu dans le payload
5. POST `/api/import/direct` sur bank-review avec `X-Internal-Api-Key`
6. Reçoit `{session_id, added, date_min, date_max}`
7. Envoie un message Block Kit dans le channel avec :
   - Bouton *"Voir les dépenses"* → `https://bank.jlmvpscode.duckdns.org/import/history/{session_id}`
   - Bouton *"Suivi budget"* → `https://bank.jlmvpscode.duckdns.org/budget`

## Intégrations actives

| Service | Endpoint appelé | Auth |
|---------|----------------|------|
| bank-review | `POST /api/import/direct` | `X-Internal-Api-Key` header |
| tool-file-intake | reçoit `POST /webhook/file-stored` | aucune (réseau interne) |
| Slack | `chat.postMessage` | Bearer SLACK_BOT_TOKEN |

## Registre des services — feedback et déploiement

Le fichier central est `app/services/registry.py`.
C'est le seul endroit à modifier pour brancher un nouveau service sur le système feedback/déploiement.

### Ajouter un service externe (sa propre app Coolify)
1. Implémenter sur le service : `GET /api/feedback/closed-since?since=` (protégé par `X-Internal-Api-Key`) et `POST /api/feedback`
2. Ajouter une entrée dans `_build_registry()` (voir modèle commenté dans le fichier)
3. Ajouter les variables d'env dans `config.py`
4. Configurer `post_deployment_command` dans Coolify (voir CLAUDE.md racine)

### Ajouter un service interne (hébergé dans assistant-ia)
1. Ajouter le nom dans `VALID_PROJECTS` dans `app/routes/feedback.py`
2. Ajouter une entrée dans `_build_registry()` avec `base_url = ASSISTANT_BASE_URL` et `coolify_uuid = "gayg5mw9jikbio2le75olq8b"`

### UUID Coolify des apps
- `bank-review` : `ji9jg7ngkva7j4d2uic05d3v`
- `assistant-ia` : `gayg5mw9jikbio2le75olq8b`

### Endpoints feedback (cette session)
| Endpoint | Rôle |
|---|---|
| `POST /webhook/deploy-complete` | Notification déploiement (Coolify ou manuel) |
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

Avant tout déploiement d'une nouvelle fonctionnalité :
- Mettre à jour la **landing page** (`_LANDING_HTML` dans `app/main.py`) : hero subtitle, liens, description de la section concernée.

Ordre obligatoire :
1. `git push origin main`
2. Rebuild Coolify via API (voir CLAUDE.md racine pour le template curl)
