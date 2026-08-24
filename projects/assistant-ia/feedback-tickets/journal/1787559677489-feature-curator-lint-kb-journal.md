---
id: 1787559677489
type: feature
status: open
priority: low
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: journal-kb-v2
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

**Phase ultérieure — hors v1.** Ticket créé pour ne pas perdre l'intention (roadmap §2, ligne
« Curator / Lint : health-check périodique — phase ultérieure avec fichier ticket à créer pour
s'en souvenir »).

Quatrième artefact du LLM Wiki Pattern (`KNOWLEDGE_ARCHITECTURE.md` §2) : un **Curator / Lint**
périodique sur la KB journal, qui détecte et signale (sans corriger seul) :

- **contradictions** entre entrées ;
- **doublons** sémantiques que le `content_hash` ne voit pas (formulations différentes, même idée) ;
- **dérive de taxonomie** : tags libres quasi-identiques (`management` / `manageent` / `Management`),
  tags orphelins utilisés une seule fois, valeurs d'axe hors vocabulaire ;
- **désynchronisation** vault ↔ index Postgres (fichier `.md` sans ligne en base, ou l'inverse).

Sortie : un rapport hebdomadaire posté dans `#journal`, avec propositions de fusion/renommage.
Comme pour l'agent de consignes, **aucune modification automatique** — l'utilisateur valide.

C'est aussi le point d'entrée naturel du rôle « agent d'organisation de la base de connaissance »
évoqué en roadmap §3 (créer de nouveaux tags, réorganiser les notes) : à cadrer dans un doc
roadmap dédié avant implémentation, pas à improviser dans ce ticket.

Prérequis : la v1 (`milestone: journal-kb`) doit tourner et avoir accumulé assez d'entrées pour
que le lint ait du sens. La recherche sémantique (pgvector) est probablement nécessaire pour la
détection de doublons → dépend de la couche fédérée.

### Notes d'implémentation
