---
id: 1787559677482
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: slack-routing
closed_at: 2026-08-24T09:12:00+00:00
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

**Prérequis partagé aux deux chantiers** (`journal-kb` et `agent-consignes`) : aujourd'hui
`app/slack_app.py:42` fait `if not thread_ts: return` — tout message **parent** de channel est
ignoré. Or les deux roadmaps supposent de capter précisément ces messages :

- KB journal : une « note libre » écrite dans `#journal` est un message parent.
- Agent : `@admin …` / `@update` / un tour de conversation sont des messages parents.

Refactorer `on_message` en **dispatcher explicite**, sans régresser le journal v2.

Ordre de routage imposé (le premier qui matche gagne) :

1. `bot_id` ou `subtype` présent → ignorer (inchangé).
2. `thread_ts` présent → chaîne actuelle : session journal v2, puis ancien journal libre.
3. Message parent + préfixe `@admin` / `@update` détecté → chantier agent (déterministe).
4. Message parent dans `#journal` (`JOURNAL_CHANNEL_ID`) → ingest note libre KB.
5. Message parent dans `#assistant` (`C0ATLALRZL3`) → tour de conversation agent.
6. Sinon → log `debug`, aucun effet.

Contraintes :

- Le dispatcher expose des **points d'accroche vides** (no-op + log) tant que les chantiers
  aval ne sont pas livrés — ce ticket ne livre aucune fonctionnalité métier, seulement le routage.
- **Anti-boucle** : ne jamais réagir à ses propres messages (garde `bot_id` déjà en place) et
  ignorer les messages postés par l'app elle-même via `slack_client`.
- **Idempotence** : Slack peut redélivrer un événement. Dédupliquer sur `client_msg_id` / `ts`
  avant tout effet de bord (les branches 3 à 5 écrivent en base).
- Répondre `200` sous 3 s : tout traitement lourd part en `asyncio.create_task` (patron déjà
  utilisé pour l'import bank-review).
- Les channels `#assistant` et `#feedback-assistant` sont **privés** → vérifier que le bot
  `@ai_vps_jlm` y est invité, sinon aucun événement ne sera reçu.

### Vérification attendue

- Réponse en thread sur un parcours journal v2 → comportement identique à aujourd'hui (non-régression).
- Message parent dans `#journal` → log de la branche 4, pas d'erreur.
- Événement redélivré deux fois → un seul traitement.

### Notes d'implémentation

`on_message` est devenu un dispatcher à 6 branches (`app/slack_app.py`) ; la chaîne thread
existante a été extraite telle quelle dans `_handle_thread_message` — aucune ligne modifiée,
c'est ce qui garantit la non-régression du journal v2. Points d'accroche vides créés :
`app/handlers/journal_kb.py` (branche 4) et `app/handlers/agent_chat.py` (branches 3 et 5).

**Idempotence en base plutôt qu'en mémoire** : table `slack_event_dedup`
(`migrations/012_slack_event_dedup.sql`, numéro 012 car 009-011 étaient pris par les tickets
parallèles) + `app/services/slack_dedup.py`. Un cache mémoire aurait perdu la garde à chaque
redéploiement Coolify. `claim_event` n'est appelé **que** sur les branches 3 à 5, jamais sur la
branche 2. En cas d'erreur base, il laisse passer : mieux vaut un doublon qu'une note perdue.

**Vérifié** : (1) compilation des 4 fichiers ; (2) test des 10 cas de routage exécuté dans le
container (deps présentes) → les 6 branches correctes, `claim_event` appelé sur 3/4/5 uniquement
et jamais sur la branche 2 ni les messages ignorés ; (3) détection des directives sur 9 cas dont
les collisions annoncées au ticket — `<@U123ABC>` (vrai handle Slack), `@updates`,
`@administrateur`, `admin@update.com` ne matchent pas ; (4) `INSERT … ON CONFLICT DO NOTHING
RETURNING` rejoué en réel sur `db_assistant` : 1re fois 1 ligne, 2e fois 0 ligne.

⚠️ Non vérifié en conditions réelles Slack (aucun message n'a été envoyé dans les channels) —
à confirmer après déploiement.
