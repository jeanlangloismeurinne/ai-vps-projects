---
id: 1787575860968
type: feature
status: closed
priority: medium
date: 2026-08-24T12:51:00.968571
project: assistant-ia
url: 
closed_at: 2026-08-24T19:12:25+00:00
---

## ✨ Feature

**Date** : 24/08/2026 12:51
**URL** : `N/A`

### Description

Je veux que l'agent ait accès à internet si ce n'est pas déjà le cas pour répondre à des questions en s'appuyant sur des recherches web. Tu peux t'inspirer de ce qui a été fait pour le projet portfolio-tracker avec Exa. si c'est possible sans Exa alors faisons sans pour économiser mes crédits pour l'autre projet.

### Analyse préalable (2026-08-24) — à lire avant d'implémenter

**Sur « faisons sans Exa » : la question des crédits est déjà résolue, sans arbitrage à faire.**
`portfolio-tracker/backend/app/knowledge/websearch.py` est **agnostique du fournisseur** :
`SEARCH_PROVIDER` (`exa | serper | none`) sélectionne le backend et le contrat de sortie
(`SearchHit`) est identique. assistant-ia peut donc utiliser **sa propre clé** — Serper ou Exa —
pendant que portfolio-tracker garde la sienne : les crédits ne sont jamais partagés, quel que
soit le choix. Le backend est un réglage d'environnement, pas une décision d'architecture, et
il reste réversible après coup.

**SearXNG auto-hébergé est déjà écarté, sur preuve.** Documenté côté portfolio-tracker et
rappelé en tête de `websearch.py` : depuis une IP unique captchaée, SearXNG renvoyait **des
résultats vides sans lever d'erreur**. L'agent croit alors avoir cherché et conclut à l'absence
de source — échec silencieux, le pire mode de défaillance ici. Ne pas relancer cette piste sans
traiter d'abord le problème d'IP.

**Le vrai coût n'est pas la recherche, c'est le tool-calling.** L'agent d'assistant-ia n'a
**aucun outil** en v1, et c'est structurant, pas accidentel : le modèle de sécurité (roadmap
`agent-consignes-systeme.md` §5, docstring de `handlers/agent_chat.py`) pose que le refus
d'exécuter est porté par le **doc système versionné et audité**, pas par du code. Donner un
outil à l'agent franchit cette limite et rouvre des questions tranchées : qui autorise un appel
sortant, que devient la piste d'audit, et une consigne approuvée via `@admin`/`@update`
peut-elle élargir l'accès réseau de l'agent ?

➡️ **Ce ticket demande une roadmap** (étape 1 du CONTROL_SYSTEM), pas une implémentation
directe. Le portage de `websearch.py` en est la partie facile et déjà écrite ; la boucle de
tool-calling et son modèle d'autorisation sont le vrai sujet.

### Notes d'implémentation

- **2026-08-24 — roadmap écrite, ticket décomposé.** Ce ticket devient l'**ombrelle** du volet
  « accès web » ; il se ferme quand son dérivé est livré.
- Roadmap : **`roadmap/agent-outillage.md`**, commune avec `#1787563980743` (rappels). Les deux
  tickets demandaient la même chose — donner un premier outil à l'agent — et les traiter séparément
  aurait fait trancher deux fois la question d'autorisation.
- **Contrainte nouvelle qui sort de l'analyse** : la lecture web et l'écriture en base sont deux
  risques *orthogonaux*, et c'est leur **composition** qui est dangereuse (une page récupérée par
  `fetch_url` peut contenir une instruction d'écriture, que le modèle ne distingue pas d'une demande
  de l'utilisateur).
- **2026-08-24 (révision)** — la « règle de composition » qui en découlait (un tour ayant lu du
  contenu externe ne peut plus écrire) est **abandonnée** : elle sur-bloquait les usages légitimes
  et laissait passer le risque majeur. Remplacée par un modèle de **taint + confirmation
  proportionnée** — l'écriture reste possible dans le même tour, mais passe devant l'utilisateur
  avec son payload résolu et sa source affichée (roadmap §2.4 et §3.2).
- **Risque dominant identifié à la révision** : le SSRF de `fetch_url` (aucune validation d'adresse
  dans le code à porter) vers l'API Coolify en `localhost:8000`. D'où la scission du dérivé.
- **Ordre révisé** : `web_search` remonte en **v1**, parallèle aux rappels. `fetch_url` part seul en
  v1.1, conditionné à son contrôle d'egress — roadmap §8.
- Dérivés : `1787579840506` (`web_search`, v1) et `1787600000000` (`fetch_url` + egress, v1.1).
  Prérequis communs : `1787579840501` → `1787579840502` → `1787579840503` → `1787579840504`.