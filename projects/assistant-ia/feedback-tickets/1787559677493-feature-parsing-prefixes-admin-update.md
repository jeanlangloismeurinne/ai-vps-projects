---
id: 1787559677493
type: feature
status: closed
priority: medium
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T11:20:00+00:00
project: assistant-ia
url: 
milestone: agent-consignes
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Parsing **déterministe** des préfixes `@admin` et `@update` (roadmap §2). Dépend de
#1787559677482 (routage `on_message`) et #1787559677492 (tables).

**Aucune slash command** — c'est la contrainte du ticket parent : les slash commands exigent une
config manuelle dans api.slack.com. On parse du texte brut dans l'événement `message`.

| Mot-clef | Effet | Traitement |
|---|---|---|
| `@admin <consigne>` | enfile la consigne | INSERT dans `agent_instruction_queue` (`status: pending`), **aucun effet immédiat** |
| `@update` | déclenche la synthèse | lance le job de proposition (#1787559677495) |

Règles de parsing :

- Détection **n'importe où** dans le message (début, milieu, fin) — comme spécifié en roadmap §2.
- Le parsing est **100 % code**, jamais un appel LLM : c'est la première ligne de défense
  anti-injection (§5.1). Le contenu de la consigne est stocké **verbatim comme donnée**, jamais
  interprété à ce stade.
- `@admin` sans texte utile → réponse d'aide, rien en base.
- **Vérifier l'absence de collision** avec un handle réel du workspace avant de figer les mots-clefs
  (roadmap §2 : un `@nom` qui correspond à un vrai utilisateur arrive comme mention, pas comme
  texte brut). Tester en conditions réelles.
- Accusé de réception en thread : « Consigne enregistrée (n° X, en attente de synthèse) ».

**Config des channels** (roadmap §7, IDs relevés le 2026-08-24) — à ajouter dans `app/config.py` :

```python
ASSISTANT_CHANNEL_ID: str = "C0ATLALRZL3"           # #assistant — conversation agent
ASSISTANT_FEEDBACK_CHANNEL_ID: str = "C0BSB9S9HHS"  # #feedback-assistant — approbation des diffs
```

⚠️ Les deux channels sont **privés** : le bot `@ai_vps_jlm` doit y être invité explicitement
(`/invite @ai_vps_jlm`), sinon aucun événement n'arrive. À vérifier en premier — c'est la cause
d'échec la plus probable.

**Job hebdomadaire** : en plus de `@update`, planifier la synthèse une fois par semaine
(patron `app/jobs/` existant, cf. `check_objectif_reminders`). Garantir un seul déclenchement par
semaine même si le worker redémarre.

### Vérification attendue

`@admin note ceci` dans `#assistant` → ligne `pending` en base + accusé en thread. `@update` →
job déclenché. Un message sans préfixe → aucun effet sur la queue.

### Notes d'implémentation

Parsing 100 % regex dans `app/handlers/agent_chat.py` (`_DIRECTIVE_RE`, `_ADMIN_PAYLOAD_RE`) — aucun
appel LLM sur ce chemin ; la consigne est insérée verbatim dans `agent_instruction_queue`. Le
lookbehind `(?<![\w<])` écarte les mentions Slack réelles (`<@U123ABC>`) et les mots contenant
`@admin` : les 9 cas de collision listés au ticket ont été testés et passent.

Job hebdomadaire `app/jobs/agent_weekly_synthesis.py` : la fenêtre a été élargie de « lundi 08:00
pile » à « lundi, à partir de 08:00 ». Un redéploiement Coolify tombant sur cette minute aurait fait
sauter la semaine entière ; c'est `claim_weekly_job` (UNIQUE `job_name, iso_week`) qui garantit
l'unicité, pas l'étroitesse de la fenêtre. 5 cas de fenêtre vérifiés (lundi 07:59 → non, lundi
08:00/08:01/23:59 → oui, mardi 08:00 → non).

⚠️ Reste à vérifier en conditions réelles après déploiement : que le bot est bien invité dans les
channels privés `#assistant` et `#feedback-assistant` (cause d'échec la plus probable, cf. ticket).
