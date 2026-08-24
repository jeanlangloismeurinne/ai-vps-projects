---
id: 1787211986144
type: feature
status: closed
priority: high
date: 2026-08-20T07:46:26.144728
closed_at: 2026-08-24T13:57:20+00:00
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
- **2026-08-24 — fermé.** Les six dérivés v1 sont livrés (`1787559677483` → `1787559677488`), plus
  le prérequis de routage `1787559677482` sans lequel une note libre — qui est un message *parent* —
  n'était jamais reçue. Le chantier tourne bout en bout : note écrite dans `#journal` → classée →
  écrite dans le vault git → indexée en Postgres → exportable en enveloppe commune.
- **Vérifié contre l'API réelle**, pas seulement en test : `checks/check_classifier_live.py` fige
  3 cas de classification (aucun fallback, vocabulaire respecté, cardinalité `0..n` honorée,
  4/4 tirages conformes). C'est cette vérification qui a révélé que le correctif `0..n` de la passe
  précédente ne tenait pas — DeepInfra renvoyait **HTTP 405 sur `json_schema`** pour Llama 3.1
  8B-Turbo, d'où un fallback silencieux. Corrigé en basculant sur `DeepSeek-V4-Flash` + vocabulaire
  en `enum` dérivé de `categories.schema.yaml` (commit `a574a75`).
- **Écarts au ticket d'origine, assumés** : Notion abandonné au profit d'Obsidian + index Postgres
  (charte `KNOWLEDGE_ARCHITECTURE.md`) ; vault en dépôt git et non Nextcloud (aucun Nextcloud sur le
  VPS) ; modèle de classification `DeepSeek-V4-Flash` et non Llama 3.1 8B (405 ci-dessus).
- **Reste ouvert, hors v1** : `1787559677489` (Curator / Lint) — attend d'avoir assez d'entrées pour
  que le lint ait du sens. La fédération (`1787559677490` / `1787559677491`) est fermée
  `wont-do-for-now` : aucune requête multi-source réelle n'a été formulée, et la charte §4 interdit
  de la construire par anticipation. L'export « enveloppe commune » étant livré, c'est réversible.
