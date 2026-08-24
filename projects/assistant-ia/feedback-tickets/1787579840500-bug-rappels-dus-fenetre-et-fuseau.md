---
id: 1787579840500
type: bug
status: open
priority: high
date: 2026-08-24T13:57:20+00:00
project: assistant-ia
url: 
milestone: agent-outillage
---

## 🐛 Bug

**Date** : 24/08/2026 13:57
**URL** : `N/A`

### Description

Deux défauts de la brique de rappel existante, trouvés en préparant `roadmap/agent-outillage.md`
(§6). **Indépendants du reste du chantier** — peuvent être corrigés seuls, et doivent l'être avant
`#1787579840505` qui bâtit dessus.

**a. Un rappel dû est perdu si le job saute une minute.**
`get_cards_due_now()` (`app/services/kanban.py:156`) ne sélectionne que les cartes dont `due_date`
tombe **dans la minute courante** (`>= date_trunc('minute', now())` et `< +1 minute`). Le job tourne
en `CronTrigger(minute="*")` (`app/main.py:32`). Si le container redémarre, si un déploiement tombe
pendant cette minute, ou si le job est simplement lent, la carte n'est jamais reprise :
`reminder_sent_at` reste `NULL` mais la fenêtre est passée. Le rappel est perdu **définitivement et
sans trace**. Les déploiements sont fréquents sur ce projet — ce n'est pas un cas théorique.

Correctif attendu : sélectionner `due_date <= now() AND reminder_sent_at IS NULL`, avec une **borne
de rattrapage** pour ne pas déverser d'un coup des rappels vieux de plusieurs jours au redémarrage
(proposition : ignorer au-delà de 24 h, mais marquer `reminder_sent_at` malgré tout afin qu'ils ne
soient pas rejoués à chaque tick — et le tracer en log).

**b. Aucun fuseau horaire.**
Le scheduler tourne en UTC (`app/main.py:25`) et rien ne définit le fuseau de l'utilisateur.
« demain 9h » est aujourd'hui ambigu, et tomberait à 11h en heure d'été. Introduire
`AGENT_TIMEZONE` dans `config.py` (défaut `Europe/Paris`), utilisée pour résoudre les expressions de
date **et** pour afficher les heures dans les messages Slack.

### Vérification attendue

- Une carte dont `due_date` est dans le passé (fenêtre manquée) est bien envoyée au tick suivant.
- Une carte `due_date` très ancienne n'est pas envoyée mais n'est plus resélectionnée ensuite.
- Une carte déjà notifiée (`reminder_sent_at` non nul) n'est jamais renvoyée.
- Test de non-régression : deux ticks consécutifs ne produisent pas deux envois pour la même carte.

### Notes d'implémentation
