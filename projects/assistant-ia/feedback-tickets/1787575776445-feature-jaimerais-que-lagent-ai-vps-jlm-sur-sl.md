---
id: 1787575776445
type: feature
status: closed
closed_at: 2026-08-24T13:30:00+00:00
priority: medium
date: 2026-08-24T12:49:36.445510
project: assistant-ia
url: 
---

## ✨ Feature

**Date** : 24/08/2026 12:49
**URL** : `N/A`

### Description

J'aimerais que l'agent AI VPS JLM sur Slack affiche ... quand il est en attente de la réponse de l'API de DeepInfra ou tout autre signe qui montrerait qu'il est en train de réfléchir / de répondre

### Notes d'implémentation

Livré le 2026-08-24. `handle_conversation_turn` poste `_⏳ je réfléchis…_` **avant** tout appel
réseau, puis remplace ce message par la réponse via `chat.update` (nouveau
`slack_client.update_text`). Le fil ne contient donc qu'**un seul** message, pas un message
d'attente suivi d'une réponse.

Choix : `chat.update` plutôt qu'une réaction emoji sur le message de l'utilisateur — la réaction
est discrète et ne dit pas *où* la réponse va apparaître.

Bornes de sécurité (un indicateur d'attente ne doit jamais coûter une réponse) :
- si le post de l'indicateur échoue, le tour continue et la réponse est postée normalement ;
- si le `chat.update` échoue (message supprimé, droits), repli sur un post classique — jamais
  d'utilisateur laissé sur « je réfléchis… » ;
- le chemin d'erreur passe aussi par le remplacement, sinon l'indicateur resterait affiché à
  côté du message d'erreur.

Pas de risque de boucle : `slack_app.py` ignore `bot_id` et tout `subtype`, or `chat.update`
émet un événement `message_changed` (un subtype).

Vérifié de bout en bout contre Slack et DeepInfra (séquence `post` puis `update` observée,
message Slack et tours en base supprimés après le test).
