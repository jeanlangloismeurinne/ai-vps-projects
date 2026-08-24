---
id: 1787211986144
type: feature
status: open
priority: high
date: 2026-08-20T07:46:26.144728
project: assistant-ia
url: 
milestone: journal-kb
---

## ✨ Feature

**Date** : 20/08/2026 07:46
**URL** : `N/A`

### Description

Je veux pouvoir écrire en langage naturel dans le fil journal des idees ou apprentissages et que le système les enregistre dans une base de connaissance hébergée sur Notion en categorisant l’envoi selon plusieurs catégories (personnel/professionnel, idee/apprentissage, management/politique/vacances/et ) ou tag. 

Pour exécuter la categorisation, tu vas pouvoir appeler une API externe via DeepInfra qu’il faut configurer ensemble avec un modele simple et peu cher à choisir ensemble. 

Pour l’enregistrement Notion, on doit définir ensemble ou créer la base de connaissance liée à journal. À voir si on crée une base de connaissance en doublon sur le VPS dans une base de données pour faciliter la sauvegarde et l’exploitation par d’autres agents.

### Notes d'implémentation

- **2026-08-20** — Cadré en séance. **Reciblé** : on abandonne Notion au profit d'une KB
  **Obsidian (Markdown pivot) + index Postgres VPS** (conforme au LLM Wiki Pattern de la charte
  `KNOWLEDGE_ARCHITECTURE.md`). Modèle de catégorisation retenu : **Llama 3.1 8B via DeepInfra**.
- Doc de conception : `roadmap/journal-knowledge-base.md` (flux, taxonomie, enveloppe §3, config).
- ~~**Décision débloquée (2026-08-20)** : vault exposé via **Nextcloud WebDAV**~~ — **révisé le
  2026-08-24** : aucun Nextcloud n'existe sur le VPS. Vault en **dépôt git** (option B du doc §6),
  commit auto après chaque écriture, clone + `pull` côté Obsidian. Les garde-fous de §6.1 (chemin
  jamais dérivé d'un input, append-only, pas de suppression récursive) sont conservés.
- **2026-08-24 — décomposé.** Ce ticket devient l'**ombrelle** du chantier ; il se ferme quand les
  tickets dérivés sont livrés.
  - Prérequis partagé : `1787559677482` (routage `on_message` — sans ça une note libre, qui est un
    message **parent**, n'est jamais reçue : `app/slack_app.py:42`)
  - v1 : `1787559677483` (client DeepInfra) → `1787559677484` (migration `009`, pas `003`) →
    `1787559677485` (taxonomie + classifieur) → `1787559677486` (vault git) →
    `1787559677487` (ingest) → `1787559677488` (export enveloppe)
  - Fédération : `1787559677490`, `1787559677491` (⚠️ tension avec la charte, à arbitrer)
  - Phase ultérieure : `1787559677489` (Curator / Lint)
- **Gain de temps repéré** : le client DeepInfra n'est pas à écrire, il existe déjà en production
  dans `projects/portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py` — à porter.
