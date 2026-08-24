---
id: 1787252691603
type: feature
status: closed
priority: medium
milestone: agent-consignes
date: 2026-08-20T19:04:51.603968
closed_at: 2026-08-24T11:58:00+00:00
project: assistant-ia
url: 
needs_clarification: false
---

## ✨ Feature

**Date** : 20/08/2026 19:04
**URL** : `N/A`

### Description

J’aimerais pouvoir discuter avec l’agent IA qui fait appel à une API et pouvoir écrire au fur et à mesure son prompt système. 

Par exemple quand l’utilisateur écrit @admin le système enregistre le message dans une base de données et une fois par semaine (ou à la demande de l’utilisateur avec @update) le système fait tourner l’API pour ajouter la consigne au prompt système ou équivalent de CLAUDE.md de l’assistant. 

Il faut que la consigne qui déclenche une logique système soit compatible avec les contraintes de Slack par exemple si possible sans utiliser les slash qui nécessitent une configuration manuelle dans l’outil. 

Il peut y avoir des feedbacks qui vont ajouter des consignes de type « quand l’utilisateur tape @bidule alors fait ceci » qui seront gérées par l’API. En revanche, certaines consignes doivent être gérées par un script déterministe notamment pour éviter le risque d’injection (voir point suivant)

Je veux que le système soit le plus robuste possible, en particulier valider ce qui va être ajouté dans le fichier système une fois que l’agent le soumet en revoyant et approuvant les diff par exemple.

### Notes d'implémentation

- **2026-08-20** — Chantier sensible (auto-modification de prompt, risque d'injection) → mis en
  **conception** avant tout code (choix utilisateur : « doc roadmap d'abord »).
- Doc de conception : `roadmap/agent-consignes-systeme.md` — déclencheurs Slack **sans slash**
  (`@admin`/`@update` parsés dans `on_message`), modèle de données, cycle proposition→approbation
  de diff (human-in-the-loop), **modèle de sécurité** (donnée≠instruction, liste blanche
  déterministe, audit, rollback). API : **DeepInfra** (fournisseur unique avec le ticket #1).
- ~~**Bloqué sur validation** du modèle de sécurité (§5) + décisions ouvertes (§7).~~
- **2026-08-24 — débloqué et décomposé.** Modèle de sécurité §5 validé et décisions §7 tranchées
  (channels relevés : `#assistant` = `C0ATLALRZL3`, `#feedback-assistant` = `C0BSB9S9HHS`, tous
  deux **privés** → inviter `@ai_vps_jlm`). Ce ticket devient l'**ombrelle** du chantier ; il se
  ferme quand les tickets dérivés sont livrés.
  - Prérequis partagés : `1787559677482` (routage `on_message`), `1787559677483` (client DeepInfra)
  - v1 : `1787559677492` → `1787559677493` → `1787559677494` → `1787559677495` →
    `1787559677496` (sécurité) → `1787559677497`
  - v2 : `1787559677498` (registre `@bidule`)
- **Découverte bloquante intégrée aux tickets** : `app/slack_app.py:42` (`if not thread_ts: return`)
  ignore tout message parent — `@admin`, `@update` et les tours de conversation n'arrivaient donc
  jamais. Corrigé par `1787559677482`, à livrer en premier.
- **2026-08-24 — ombrelle fermée : la v1 est livrée.** Les six tickets dérivés (`492` → `497`) sont
  clos, prérequis `482`/`483` inclus. Le chantier répond à la demande d'origine : conversation dans
  `#assistant` avec historique, `@admin` met une consigne en file, `@update` (ou la synthèse
  hebdomadaire) produit une proposition de doc système, et **le diff est approuvé à la main** dans
  `#feedback-assistant` avant toute activation.
- Le point de robustesse demandé est tenu par trois mécanismes distincts : le parsing de
  `@admin`/`@update` est **100 % code, jamais un appel LLM** ; le contenu utilisateur est passé au
  modèle comme **donnée délimitée, jamais comme instruction** ; et `agent_versioning` est le **seul**
  module qui écrit `active = true`, ce qui rend structurellement impossible une activation sans clic
  humain. Rollback et audit immuable complètent le dispositif.
- Reste hors v1 : `1787559677498` (registre `@bidule`) et le chantier knowledge-federation
  (`1787559677490`/`491`).
- ⚠️ Vérifications réelles à faire après déploiement : bot invité dans `#assistant` et
  `#feedback-assistant`, `AGENT_APPROVERS` renseigné, puis un aller-retour complet
  consigne → `@update` → approbation.
