---
id: 1787579840503
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

**Cœur sécurité du chantier** (`roadmap/agent-outillage.md` §2 et §3). Ce ticket ne livre aucun
outil utile à l'utilisateur : il livre le cadre dans lequel tous les outils suivants seront branchés.
Il doit être livré **avant** `#1787579840505` et `#1787579840506`.

> **Révisé le 2026-08-24** (point « à discuter » de la version initiale, tranché).
> La « règle de composition » (latch au niveau du tour) est **abandonnée**. Motifs en roadmap §2.4 :
> elle ne traitait pas le risque majeur (SSRF, roadmap §4), sur-bloquait les compositions légitimes,
> et ne raisonnait qu'entre « exécuter en silence » et « refuser ». Remplacée par un modèle de
> *taint* + confirmation proportionnée.

### 1. Registre d'outils codé en dur

Module `app/services/agent_tools/registry.py`. La liste des outils exposés au modèle (`tools_json`)
est construite **exclusivement** depuis ce module Python. Aucun chemin de code ne dérive un outil du
contenu de `agent_system_doc`.

Le doc système peut décrire **quand** utiliser un outil (c'est une façon de répondre, autorisée par
le §5.2 de `agent-consignes-systeme.md`). Il ne peut pas en **faire exister** un.

Ce ticket est la première entrée concrète du registre annoncé par `#1787559677498`, qui reste
ouvert pour son autre volet (déclencheurs `@bidule` définis par consigne).

### 2. Manifeste par outil

C'est ce qui rend le catalogue extensible : ajouter un outil doit être de la **donnée**, pas du
raisonnement sécurité neuf. Chaque outil déclare :

| Champ | Rôle |
|---|---|
| `name`, `description`, `schema` | contrat envoyé au modèle (JSON schema strict) |
| `effect` | `read` \| `write` \| `outbound` (sort du système) |
| `taints_context` | l'outil fait-il entrer du contenu non authentifié par l'utilisateur ? |
| `reversible` | l'effet s'annule-t-il en un clic ? |
| `scope` | sur les données de qui l'outil agit-il ? |
| `visibility` | l'utilisateur voit-il l'effet immédiatement dans le fil ? |
| `rate_limit` | appels max par tour et par jour |
| `egress` | politique réseau applicable (roadmap §4) — `None` pour les outils internes |

`taints_context` n'est **pas** un synonyme de « sort du VPS » : un futur `read_file` sur
`/storage/Documents` ou un `read_thread` Slack taintent le contexte sans rien appeler à l'extérieur
(roadmap §2.2). Classer les outils en `read_external` / `side_effect` était le défaut de la version
précédente — fausse complétude.

### 3. Fonction `policy` — une seule, testée

`policy(manifeste, état_du_tour) -> Exécuter | ConfirmerAvant | Refuser(motif)`.

Règle de dérivation : **confirmation avant écriture** si `effect == outbound`, ou
`reversible == false`, ou `visibility == false`, ou `taint_sources` du tour non vide.
Sinon exécution immédiate + confirmation a posteriori.

L'état du tour porte `taint_sources: list[str]` (ex. `["web:exemple.com"]`), alimenté par tout appel
d'outil dont le manifeste a `taints_context = true`. Il n'est jamais rabaissé pendant le tour, mais
il **n'interdit rien** : il change le régime de confirmation.

Un seul endroit à relire pour auditer la politique, un seul jeu de tests. Un nouvel outil remplit
son manifeste et ne touche pas à `policy`.

### 4. Bornes d'exécution (roadmap §3.5)

- `max_iterations` par défaut **8** (pas 4), plus un budget de temps mural et de tokens.
  Épuisement = sortie explicite, jamais un abandon silencieux.
- Plafond de caractères sur tout résultat d'outil réinjecté.
- Les quotas viennent du champ `rate_limit`, pas de constantes dispersées.
- Tout contenu tainté réinjecté est encadré d'un délimiteur explicite le désignant comme données
  citées. Mitigation faible mais gratuite — elle ne remplace pas la frontière modèle/code
  (roadmap §2.3, qui reste le garde-fou principal).
- Échec d'outil = erreur explicite en `role=tool`, jamais un résultat vide.

### Vérification attendue

- **Test d'isolation du registre** : construire `tools_json` en présence d'un doc système contenant
  des définitions d'outils inventées → la liste produite est **inchangée**.
- **Tests de `policy` en table**, indépendants de tout outil réel : les 4 conditions de confirmation
  préalable sont couvertes une par une, plus le cas nominal (exécution immédiate).
- Après un appel d'outil `taints_context = true` simulé, un outil `write` réversible et visible est
  **autorisé mais en régime `ConfirmerAvant`** — pas refusé.
- Le sens inverse (`write` puis lecture taintante) ne déclenche aucune restriction rétroactive.
- `taint_sources` accumule bien plusieurs sources distinctes dans un même tour.

### Notes d'implémentation
