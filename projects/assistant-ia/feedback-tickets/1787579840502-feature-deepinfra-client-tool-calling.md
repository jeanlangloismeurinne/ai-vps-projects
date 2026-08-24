---
id: 1787579840502
type: feature
status: open
priority: high
date: 2026-08-24T13:57:20+00:00
project: assistant-ia
url: 
milestone: agent-outillage
---

## ✨ Feature

**Date** : 24/08/2026 13:57
**URL** : `N/A`

### Description

Ajouter le support du tool-calling à `app/services/deepinfra_client.py` (qui expose aujourd'hui
`chat()` et `chat_json()` seulement, `deepinfra_client.py:131`), puis une **boucle bornée**
d'exécution d'outils.

**Dépend de `#1787579840501`** — ne pas démarrer avant que le support `tools` soit confirmé contre
l'API réelle.

### Périmètre

Portage, pas écriture — les deux briques existent en production :

- `portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py` — gestion des `tool_calls`
  dans la réponse.
- `portfolio-tracker/backend/app/agents/v2/runner.py:147` (`_tool_loop`) — boucle « tant que le
  modèle émet des `tool_calls` : exécuter, réinjecter en `role=tool`, reboucler ».

Comme pour le client DeepInfra initial : **copie adaptée, pas d'import inter-projets**.

### Bornes obligatoires (roadmap §3.4)

- `max_iterations` (défaut **4**). À l'épuisement alors que le modèle appelle encore des outils :
  sortie **explicite et tracée**, jamais un abandon silencieux (`runner.py` a déjà un flag
  `exhausted` — le reprendre).
- Plafond de caractères sur tout résultat d'outil réinjecté dans le contexte.
- Un échec d'outil est réinjecté comme `{"error": …}` en `role=tool` — **jamais** un résultat vide.
  C'est la leçon SearXNG (roadmap §5) et elle vaut pour tous les outils, pas seulement la recherche.

### Vérification attendue

Boucle testable **sans réseau** : un outil factice en mémoire suffit pour couvrir l'épuisement du
compteur, la troncature, et le chemin d'erreur. Réserver l'appel réel au ticket `#1787579840501`.

### Notes d'implémentation
