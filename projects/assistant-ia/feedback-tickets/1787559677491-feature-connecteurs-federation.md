---
id: 1787559677491
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

**Connecteurs** alimentant `db_knowledge_federation` (dépend de #1787559677490).

> ✅ **Fermé le 2026-08-24 avec #1787559677490** : la couche fédérée n'est pas construite
> (charte `KNOWLEDGE_ARCHITECTURE.md` §4 — pas de construction par anticipation). Sans base
> fédérée, ces connecteurs n'ont rien à alimenter. Le contenu ci-dessous reste valable tel quel
> le jour de la réouverture : la vue d'export `knowledge_federation_export` (#1787559677488)
> est déjà livrée, donc le travail préparatoire n'est pas perdu.

Un connecteur par source, en **pull incrémental** via `content_hash` / `updated_at`
(`KNOWLEDGE_ARCHITECTURE.md` §4) :

| Source | Connecteur | Statut |
|---|---|---|
| `assistant-ia` / `vps_files` | vue `knowledge_federation_export` (#1787559677488) → copie incrémentale | prêt dès la v1 journal-kb |
| `portfolio-tracker` / `postgres` | sa propre vue d'export → copie incrémentale | à vérifier : la vue existe-t-elle déjà côté portfolio-tracker ? |

Règles :

- **Pull, jamais push** : la fédération va chercher, les projets ne poussent pas. Une source
  cassée ne casse pas la fédération.
- **Idempotent** : rejouer un connecteur ne duplique rien (clé `doc_id`, saut si `content_hash`
  inchangé).
- **Embeddings calculés au moment de l'ingestion fédérée**, pas côté source — c'est la fédération
  qui possède l'espace vectoriel.
- Planification : job périodique (patron `app/jobs/` existant), pas de temps réel.
- Ne pas écrire de connecteur Notion / Nextcloud / mailbox tant qu'aucune de ces sources n'est
  réellement en place — la charte proscrit la construction par anticipation.

Livrer aussi une **commande de resynchronisation complète** (reconstruction depuis zéro), utile si
l'espace vectoriel change de modèle.

### Notes d'implémentation
