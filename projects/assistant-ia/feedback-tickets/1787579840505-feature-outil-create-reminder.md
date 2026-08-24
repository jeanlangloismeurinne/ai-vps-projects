---
id: 1787579840505
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

Premier outil à effet de bord : `create_reminder`. C'est le livrable utilisateur du ticket ombrelle
`#1787563980743` — « écrire en langage naturel dans le fil et voir le rappel programmé, avec
confirmation succincte ».

**Dépend de** `#1787579840500` (fenêtre de rattrapage + fuseau), `#1787579840503` (registre + règle
de composition) et `#1787579840504` (audit).

### Frontière modèle / code (roadmap §3.2 — non négociable)

| Le modèle fait | Le code fait |
|---|---|
| Extraire `title` et une expression de date, sous JSON schema strict | Résoudre l'expression en `TIMESTAMPTZ` avec `AGENT_TIMEZONE` |
| Rien d'autre | Valider les bornes, choisir la destination, écrire, confirmer, journaliser |

Le modèle ne choisit **ni** le board, **ni** la colonne, **ni** l'auteur, **ni** le canal de
notification : tout cela est fixé en Python. La surface d'attaque se réduit à deux chaînes validées.

La résolution de date se fait à partir d'un `now` **fourni par le code** (pas deviné par le modèle),
dans `AGENT_TIMEZONE`. Une date dans le passé ou au-delà d'une borne raisonnable est refusée avec un
message clair, jamais silencieusement corrigée.

### Confirmation a posteriori (décision utilisateur du 2026-08-24)

Création immédiate, puis message court dans le fil : titre retenu + **date affichée dans le fuseau
de l'utilisateur** + bouton « annuler » (qui supprime la carte). L'`id` de la carte est transporté
dans la `value` du bouton — même mécanique que `bank_import_novac` (`app/slack_app.py`).

Afficher la date résolue est la partie qui compte : c'est ce qui rend une mauvaise interprétation
(« mardi » = lequel ?) immédiatement visible par l'utilisateur, ce qui est l'hypothèse sur laquelle
repose tout le régime « a posteriori » (roadmap §3.3).

### Destination dans le kanban

Proposition retenue par défaut, à confirmer à l'usage : colonne **`Rappels`** sur le board par
défaut, **créée à la volée si absente**. L'utilisateur réorganise ensuite depuis `/kanban`, qui est
déjà la page d'édition demandée par le ticket ombrelle (`app/routes/kanban.py:47` — rien à
construire de ce côté).

Le nom de la colonne est une constante de code, jamais un argument du modèle.

### Vérification attendue

- Un seul appel `create_reminder` par tour (borne du §3.4).
- Une expression de date ambiguë ou passée → refus explicite, aucune carte créée.
- Le bouton « annuler » supprime bien la carte et le confirme.
- Un rappel créé est effectivement envoyé par le job (chaînage avec `#1787579840500`).
- L'appel apparaît dans `agent_tool_calls` avec `external_content_seen = false`.
- Restaurer l'état Slack et la base après le test (pratique établie sur ce projet).

### Notes d'implémentation
