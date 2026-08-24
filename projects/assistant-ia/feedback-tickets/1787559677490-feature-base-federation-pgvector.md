---
id: 1787559677490
type: feature
status: open
priority: medium
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: knowledge-federation
needs_clarification: true
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Couche de **recherche fédérée** (`KNOWLEDGE_ARCHITECTURE.md` §4), demandée par la roadmap
`journal-knowledge-base.md` §5 (« la fédération est construite dès maintenant ») et §8
(« il faut créer les tickets liés à la couche fédérée »).

> ⚠️ **Tension à trancher avant de démarrer.** La charte est explicite : *« Tant que le besoin
> n'est pas là, ne rien construire de la §4 »* — jamais par anticipation. La roadmap journal dit
> l'inverse. L'argument en faveur de la construction : il existe désormais **deux sources réelles**
> (la Knowledge Platform de `portfolio-tracker`, déjà en production, et la KB journal) — le besoin
> multi-source est donc matérialisé, pas anticipé. L'argument contre : personne n'a encore formulé
> de requête qui traverse les deux. **À confirmer en séance** ; en attendant, ne pas démarrer avant
> que `milestone: journal-kb` soit livré et utilisé.

Périmètre :

- Base dédiée `db_knowledge_federation` sur `shared-postgres` (image `pgvector/pgvector:pg16` —
  **aucune nouvelle brique d'infra**, l'extension est déjà disponible).
- Table `documents` : colonnes = enveloppe commune (`templates/knowledge-base/envelope.schema.json`)
  + colonne `embedding vector(…)` + `reliability` (§6 de la charte).
- Index vectoriel + index sur `project`, `source`, `visibility`, `updated_at`.
- Requêtes de référence : recherche exhaustive `ORDER BY embedding <=> :q`, recherche projet
  `WHERE project = :p`. Les agents citent via `uri`.
- **Confidentialité** : filtrage `visibility` selon le contexte d'appel — le journal est
  `private`, il ne doit jamais remonter dans un contexte public.

Décisions à prendre à l'implémentation : modèle d'embedding (cohérence avec
`portfolio-tracker/backend/app/knowledge/embeddings.py` — ne pas mélanger deux espaces vectoriels),
dimension du vecteur, et où vit le service de recherche (assistant-ia ou service dédié).

### Notes d'implémentation
