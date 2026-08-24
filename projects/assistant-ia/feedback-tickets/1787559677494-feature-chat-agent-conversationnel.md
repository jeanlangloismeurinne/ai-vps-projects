---
id: 1787559677494
type: feature
status: closed
priority: medium
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T12:05:00+00:00
project: assistant-ia
url: 
milestone: agent-consignes
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Tours de conversation avec l'agent dans `#assistant` (roadmap §2, dernière ligne du tableau).
Dépend de #1787559677482 (routage), #1787559677483 (client DeepInfra), #1787559677492 (tables).

- Un message parent dans `#assistant` **sans préfixe** = un tour de conversation.
- Charger le **doc système actif** (`agent_system_doc WHERE active`) comme prompt système —
  **au runtime, à chaque appel**, jamais mis en cache au démarrage : c'est ce qui rend l'approbation
  d'un diff immédiatement effective.
- Historique : recharger les N derniers tours de `agent_conversations` (borner la fenêtre — ne pas
  envoyer un historique illimité).
- Modèle : `DEEPINFRA_MODEL_CHAT` (roadmap §6 : « DeepSeek V4 Flash » — **vérifier l'identifiant
  exact au catalogue DeepInfra**, le nom cité n'est pas garanti d'exister).
- Réponse postée **en thread** sous le message de l'utilisateur ; les deux tours (user + assistant)
  sont enregistrés dans `agent_conversations`.
- Traitement en tâche de fond après l'ack (contrainte Slack 3 s).

**Sécurité (roadmap §5.1 — non négociable)** : le contenu utilisateur et l'historique sont des
**données**, jamais des instructions. Le prompt système vient exclusivement de `agent_system_doc`.
L'agent ne dispose d'**aucun outil** en v1 : il produit du texte, il n'exécute rien. Si l'utilisateur
demande d'exécuter du code ou une action système, l'agent l'oriente vers `/feature` (roadmap §5.2).

**Isolation (roadmap §5.6)** : `agent_system_doc` est le prompt de *cet agent*. Il n'a aucun rapport
avec les `CLAUDE.md` du repo de développement, et ce chantier ne doit jamais lire ni écrire ces
fichiers.

### Vérification attendue

Conversation réelle de 3 tours dans `#assistant` : réponses cohérentes, historique en base,
prompt système bien issu de la version active (le vérifier en changeant la version active en base
et en constatant le changement de comportement au tour suivant, sans redémarrage).

### Notes d'implémentation

`agent_chat.handle_conversation_turn` + deux services : `agent_doc` (lecture du doc actif) et
`agent_conversations` (historique). Le doc actif est relu à chaque tour, jamais mis en cache.

Identifiant du modèle vérifié au catalogue DeepInfra comme demandé : `deepseek-ai/DeepSeek-V4-Flash`
existe bien (variante datée `-0731` également disponible). `DEEPINFRA_MODEL_CHAT` est donc correct.

Deux décisions non triviales : (1) les deux tours ne sont écrits en base qu'**après** une réponse
obtenue — sinon un appel en échec laisserait un tour `user` orphelin qui polluerait l'historique du
tour suivant ; (2) sans doc actif, l'agent **refuse de répondre** au lieu de retomber sur un prompt
de secours, qui serait par construction non versionné et non audité.

Vérification : 20 assertions. Prompt système = doc actif verbatim, un seul message `system`, message
utilisateur et historique en rôles `user`/`assistant` (donnée, jamais instruction) ; historique
réinjecté dans l'ordre chronologique et borné à `AGENT_HISTORY_TURNS` = 20 en prenant bien les plus
récents ; **bascule de version active à chaud prise en compte au tour suivant sans redémarrage**
(exigence centrale du ticket, version de test créée puis supprimée, version 1 restaurée) ; échec
DeepInfra → message à l'utilisateur et zéro tour orphelin. Isolation §5.6 vérifiée par AST : aucun
appel d'accès fichier dans le code de l'agent, donc a fortiori aucune lecture des `CLAUDE.md`.

⚠️ Reste la conversation réelle de 3 tours dans `#assistant`, à faire après déploiement (dépend de
l'invitation du bot dans le channel privé et de la clef DeepInfra en variable Coolify).
