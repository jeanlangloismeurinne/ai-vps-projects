---
id: 1787579840505
type: feature
status: closed
priority: high
date: 2026-08-24T13:57:20+00:00
project: assistant-ia
url: 
milestone: agent-outillage
closed_at: 2026-08-24T19:12:25+00:00
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

La résolution de date se fait à partir d'un `now` **fourni par le code** (pas deviné par le modèle),
dans `AGENT_TIMEZONE`. Une date dans le passé ou au-delà d'une borne raisonnable est refusée avec un
message clair, jamais silencieusement corrigée.

### Deux régimes de confirmation (roadmap §3.2, révisé le 2026-08-24)

Le régime se décide à l'exécution, via `policy()` de `#1787579840503` :

| Contexte du tour | Régime |
|---|---|
| `taint_sources` vide (aucune lecture taintante) | **création immédiate** + confirmation a posteriori |
| `taint_sources` non vide (ex. un `web_search` a eu lieu) | **écriture suspendue** : Slack affiche le payload résolu + la source du taint + boutons `Confirmer` / `Annuler`. Rien n'est écrit sans clic. |

Le second cas est ce qui remplace l'ancienne « règle de composition » : « cherche X et crée-moi un
rappel là-dessus » **fonctionne en un tour**, mais l'écriture passe devant l'utilisateur avec sa
provenance affichée. Une injection depuis une page web produit un rappel non demandé, visible, que
l'utilisateur ne confirme pas.

Une suspension non confirmée expire sans rien écrire — pas de carte fantôme, pas de relance.

### Confirmation a posteriori (contexte propre)

Création immédiate, puis message court dans le fil : titre retenu + **date affichée dans le fuseau
de l'utilisateur** + bouton « annuler » (qui supprime la carte) + bouton « éditer » qui permet de modifier le titre et/ou la date. L'`id` de la carte est transporté
dans la `value` du bouton — même mécanique que `bank_import_novac` (`app/slack_app.py`).

Afficher la date résolue est la partie qui compte : c'est ce qui rend une mauvaise interprétation
(« mardi » = lequel ?) immédiatement visible par l'utilisateur, ce qui est l'hypothèse sur laquelle
repose tout le régime « a posteriori » (roadmap §3.3).

### Destination dans le kanban

Proposition retenue par défaut, à confirmer à l'usage : colonne **`Rappels`** sur le board par
défaut, **créée à la volée si absente**. L'utilisateur réorganise ensuite depuis `/kanban`, qui est
déjà la page d'édition demandée par le ticket ombrelle (`app/routes/kanban.py:47` — rien à
construire de ce côté pour l’instant).

Le nom de la colonne est une constante de code, jamais un argument du modèle.

### Vérification attendue

- Le quota vient du `rate_limit` du manifeste (3 par tour, 20 par jour) — « crée-moi trois
  rappels » doit fonctionner ; le 4e du même tour est refusé avec un motif explicite.
- Une expression de date ambiguë ou passée → refus explicite, aucune carte créée.
- Le bouton « annuler » supprime bien la carte et le confirme. Le bouton « éditer » confirme le changement réalisé.
- Un rappel créé est effectivement envoyé par le job (chaînage avec `#1787579840500`).
- **Contexte propre** : l'appel apparaît dans `agent_tool_calls` avec `taint_sources = []` et
  `user_confirmed = false`.
- **Contexte tainté** (testable avec un outil `taints_context` simulé, sans attendre
  `#1787579840506`) : aucune carte n'existe avant le clic sur `Confirmer` ; après clic, la ligne
  d'audit porte `taint_sources` renseigné et `user_confirmed = true`.
- Restaurer l'état Slack et la base après le test (pratique établie sur ce projet).

### Notes d'implémentation