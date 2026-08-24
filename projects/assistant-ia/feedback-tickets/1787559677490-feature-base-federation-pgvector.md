---
id: 1787559677490
type: feature
status: closed
closed_at: 2026-08-24T13:20:00+00:00
closed_reason: wont-do-for-now
priority: medium
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: knowledge-federation
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Couche de **recherche fédérée** (`KNOWLEDGE_ARCHITECTURE.md` §4), demandée par la roadmap
`journal-knowledge-base.md` §5 (« la fédération est construite dès maintenant ») et §8
(« il faut créer les tickets liés à la couche fédérée »).

> ✅ **Tranché le 2026-08-24 : on ne construit pas.** La charte
> `KNOWLEDGE_ARCHITECTURE.md` §4 l'emporte sur la roadmap `journal-knowledge-base.md` §5 —
> la charte est **transverse à tous les projets**, la roadmap ne couvre que le journal ; en cas
> de contradiction, le document de plus grande portée fait foi.
>
> Le besoin invoqué (« deux sources réelles ») n'en est pas un : **personne n'a encore formulé
> de requête traversant portfolio-tracker et la KB journal**. Construire maintenant, c'est
> façonner le schéma fédéré à partir d'une seule source réellement exploitée — précisément
> l'anticipation que la charte interdit.
>
> Ce qui rend la décision réversible à faible coût : l'**enveloppe document commune** est déjà
> exportable (contrainte « federation-ready », charte §5). Le jour où une requête multi-source
> apparaît, il ne restera qu'à créer la base et les connecteurs.
>
> **Condition de réouverture** : une requête réelle et formulée qui traverse au moins deux
> sources. Rouvrir alors ce ticket puis `1787559677491`.

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
