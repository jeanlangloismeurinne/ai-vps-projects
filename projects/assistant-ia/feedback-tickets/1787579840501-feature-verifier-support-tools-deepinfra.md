---
id: 1787579840501
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

**Ticket bloquant — à faire en premier.** Vérifier, **par un appel réel à DeepInfra**, que le modèle
de conversation (`DEEPINFRA_MODEL_CHAT`, aujourd'hui `DeepSeek-V4-Flash`) accepte le paramètre
`tools` et renvoie bien des `tool_calls` exploitables.

**Pourquoi ce ticket existe.** Précédent exact et récent sur ce même projet : DeepInfra a renvoyé
**HTTP 405 sur `response_format: json_schema`** pour Llama 3.1 8B-Turbo. Le code partait alors en
fallback silencieux `json_object`, ce qui a produit trois effets tous observés — double appel API,
vocabulaire fermé dégradé en simple consigne de prose, cardinalité jamais honorée. Le défaut n'a été
trouvé qu'en testant **contre l'API réelle**, après avoir été considéré comme corrigé (session du
2026-08-24 13:12, commit `a574a75`).

Toute la roadmap `agent-outillage.md` suppose une boucle de tool-calling. Si le modèle ne supporte
pas `tools`, ou le supporte mal, **c'est l'ordre des tickets suivants qui change** — pas un détail
d'implémentation. Donc on vérifie avant de construire, pas après.

### Périmètre

- Script figé dans `checks/` (modèle : `checks/check_classifier_live.py`), lancé **dans le
  container** — la clé DeepInfra n'est pas sur l'hôte.
- Vérifier au minimum : (1) un appel avec un outil déclaré ne renvoie pas d'erreur HTTP ;
  (2) une question qui appelle clairement l'outil produit un `tool_calls` avec des arguments JSON
  parsables ; (3) une question qui ne l'appelle pas produit une réponse texte normale, sans
  `tool_calls` fantôme ; (4) le réinjection d'un `role=tool` est acceptée et donne une réponse finale.
- Consigner le résultat dans `roadmap/agent-outillage.md` §6 (le tableau d'inventaire).

**Si le support est absent ou instable** : ne pas contourner par un fallback silencieux — c'est
précisément l'erreur du précédent. Documenter, et remonter le choix du modèle en décision de
roadmap.

### Notes d'implémentation
