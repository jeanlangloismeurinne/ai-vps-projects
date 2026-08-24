---
id: 1787559677498
type: feature
status: open
priority: low
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: agent-consignes-v2
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

**Hors v1** (roadmap §8, marqué « v2 »). Ticket créé pour garder la trace de l'intention.

Registre en **liste blanche codée** pour les déclencheurs personnalisés du type
« quand l'utilisateur tape `@bidule`, fais X » (roadmap §2 et §5.2).

Cadre imposé par le modèle de sécurité, à ne pas assouplir :

- Une règle `@bidule` définie par une consigne système ne peut produire qu'une **façon de répondre
  en langage naturel** — c'est un raccourci vers une instruction standard, jamais l'exécution de
  code (§5.2).
- Toute action ayant un **effet de bord** (écrire quelque part, appeler un service, lancer un job)
  doit être une entrée **codée en dur** dans le registre, jamais quelque chose que le LLM peut
  inventer ou qu'une consigne peut introduire.
- Si l'utilisateur demande d'exécuter du code, l'agent répond en l'orientant vers `/feature`
  (§5.2) — c'est le comportement déjà exigé du chat en v1 (#1787559677494).

Prérequis : la v1 (`milestone: agent-consignes`) livrée et le cycle proposition/approbation éprouvé
en usage réel. Ne pas démarrer avant.

### Notes d'implémentation
