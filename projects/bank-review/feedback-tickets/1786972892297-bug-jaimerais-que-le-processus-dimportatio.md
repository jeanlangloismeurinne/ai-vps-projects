---
id: 1786972892297
type: bug
status: closed
closed_at: 2026-08-19T10:40:00Z
priority: medium
date: 2026-08-17T13:21:32.298185
project: bank-review
url: 
---

## 🐛 Bug

**Date** : 17/08/2026 13:21
**URL** : `N/A`

### Description

J’aimerais que le processus d’importation d’un fichier par Slack permette aussi d’indiquer s’il y a eu des vacances pendant la période comme lors de l’importation via le site web.

### Notes d'implémentation

UX retenue avec l'utilisateur : **boutons + modale avant import** (le dépôt de fichier ne lance plus l'import automatiquement).

- **bank-review** `POST /api/import/direct` accepte désormais un champ `vacation_ranges` (JSON `[["YYYY-MM-DD","YYYY-MM-DD"], ...]`), parsé en périodes passées au `run_import_pipeline` — même format que l'import web. Rétrocompatible (défaut `""` → aucune période).
- **assistant-ia** : au dépôt d'un CSV/XLSX dans `#bank-review`, on poste une question « Y a-t-il eu des vacances ? » avec 2 boutons. *Non* → import direct ; *Oui* → modale (`bank_vac_modal`) jusqu'à 3 plages de dates (période 1 requise). L'import réel tourne en tâche de fond après l'`ack()` Slack. Handlers Bolt dans `slack_app.py` ; logique dans `handlers/bank_review.py` ; `bank_review_client.import_file` transmet `vacation_ranges`.

Vérifié : `py_compile` OK sur les 4 fichiers modifiés. Routage `/slack/events` confirmé (action_ids/callback_id hors `_FILE_ACTIONS`/`folder_selection` → atteignent bien Bolt). Test fonctionnel end-to-end (dépôt réel + clic modale) à faire en prod après déploiement des deux apps.
