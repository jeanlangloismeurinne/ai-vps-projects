---
id: 1787559677488
type: feature
status: closed
priority: medium
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: journal-kb
closed_at: 2026-08-24T09:40:00+00:00
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Contrat **federation-ready** obligatoire dès la v1 (`KNOWLEDGE_ARCHITECTURE.md` §5, roadmap §5) :
la KB journal doit savoir s'exporter en **enveloppe document commune**, même sans couche fédérée
active.

Livrer une **vue SQL** `knowledge_federation_export` dans la migration
`migrations/010_kb_export_view.sql`, projetant `journal_kb_entries` sur les champs de
`templates/knowledge-base/envelope.schema.json` :

`doc_id`, `project`, `source`, `uri`, `title`, `body`, `tags`, `visibility`, `created_at`,
`updated_at`, `content_hash`.

⚠️ La checklist `KNOWLEDGE_ARCHITECTURE.md` §5 impose aussi de **déclarer une `reliability` par
défaut** (framework de fiabilité §6) — champ absent du mapping de la roadmap §5. L'ajouter :
constante de la vue pour une KB journal (contenu de première main saisi par l'utilisateur).

- `tags` de l'enveloppe = tags libres **+ les axes** (`contexte`, `nature`) aplatis, conformément
  au mapping roadmap §5.
- Modèle à suivre : `templates/knowledge-base/federation_export.example.sql` et l'implémentation
  de référence `projects/portfolio-tracker/backend/app/knowledge/`.
- Valider la sortie contre `envelope.schema.json` (script de check, à l'image de
  `portfolio-tracker/backend/checks/check_provenance.py`).

La vue est **en lecture seule** et ne doit exposer aucun champ absent de l'enveloppe.

### Vérification attendue

`SELECT * FROM knowledge_federation_export LIMIT 5` sur des entrées réelles, sortie validée contre
`envelope.schema.json` par le script de check.

### Notes d'implémentation

`migrations/010_kb_export_view.sql` (vue `knowledge_federation_export`, `CREATE OR REPLACE`) +
`checks/check_kb_export.py` (stdlib seule, pas de dépendance à installer).

`reliability = 0.80`, tier `B+` — valeur reprise du référentiel `KNOWLEDGE_ARCHITECTURE.md` §6,
ligne « Document confidentiel fourni par l'utilisateur », pas une valeur inventée.

⚠️ **La liste de 11 champs de ce ticket était incomplète** face au contrat normatif
`envelope.schema.json`, qui exige aussi `ingested_at` et définit 18 propriétés avec
`additionalProperties: false`. La vue en expose 16 (tout sauf `embedding` et `entities`) —
contrôlé colonne par colonne contre le schéma : aucun champ hors enveloppe. `slack_ts`,
`contexte` et `nature` sont rangés dans `metadata` plutôt que fuités en colonnes racine.
`title` retombe sur `doc_id` quand il est NULL (entrée « à classer »), car l'enveloppe impose
`minLength: 1`.

**Vérifié** : vue appliquée deux fois (idempotente) ; 3 lignes de test réalistes dont une
« à classer » (contexte/nature NULL) et une multi-natures → aplatissement des axes dans `tags`
correct ; script de check 77 assertions OK / 0 KO ; lignes de test supprimées, table revenue à 0.
