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

## Ajouter un nouveau cas d'usage

1. Créer `app/handlers/mon_handler.py` avec une fonction `async def handle_file_stored(payload)`
2. Dans `app/routes/webhooks.py`, ajouter le routage par `channel_id`
3. Documenter ici

## Workflow de déploiement production

Ordre obligatoire :
1. `git push origin main`
2. Rebuild Coolify via API (voir CLAUDE.md racine pour le template curl)
