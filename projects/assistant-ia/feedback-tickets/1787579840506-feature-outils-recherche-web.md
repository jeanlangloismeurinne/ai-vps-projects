---
id: 1787579840506
type: feature
status: open
priority: medium
date: 2026-08-24T13:57:20+00:00
project: assistant-ia
url: 
milestone: agent-outillage-v1.1
---

## ✨ Feature

**Date** : 24/08/2026 13:57
**URL** : `N/A`

### Description

Outils `web_search` et `fetch_url` de classe `read_external`. C'est le livrable utilisateur du
ticket ombrelle `#1787575860968`.

**À faire en dernier** (roadmap §7) : cet ordre est délibérément l'inverse de l'ordre d'arrivée des
tickets. On outille d'abord le cas **sans contenu hostile** (`create_reminder`), on éprouve la
boucle, le registre et l'audit, puis seulement on ouvre l'entrée externe.

**Dépend de** `#1787579840503` — la règle de composition doit être en place et testée **avant** que
le premier octet de contenu web entre dans le contexte de l'agent.

### Périmètre — portage, pas écriture

`portfolio-tracker/backend/app/knowledge/websearch.py` (555 lignes) est **agnostique du
fournisseur** : `SEARCH_PROVIDER = exa | serper | none` sélectionne le backend, le contrat de sortie
(`SearchHit`) est identique. Copie adaptée, pas d'import inter-projets.

Conséquence déjà actée (roadmap §5) : la question « éviter Exa pour économiser mes crédits » du
ticket d'origine **n'a pas à être arbitrée**. assistant-ia aura sa propre clé quel que soit le
backend ; les crédits ne sont jamais partagés. Le choix Exa/Serper est un réglage d'environnement,
réversible après coup — à trancher au moment de l'implémentation.

### Contraintes reprises telles quelles

- **Échec explicite, jamais silencieux** : sans clé, ou si le backend répond mal, lever
  `SearchUnavailable`. L'erreur remonte au modèle en `{"error": …}`. C'est la raison pour laquelle
  SearXNG auto-hébergé est écarté : depuis une IP captchaée il renvoyait des **résultats vides sans
  erreur**, et l'agent conclut alors à l'absence de source. Ne pas rouvrir cette piste sans traiter
  d'abord le problème d'IP.
- Plafond de caractères sur le contenu réinjecté (§3.4).
- Tout appel journalisé dans `agent_tool_calls` avec `external_content_seen = true`.

### Vérification attendue

- Backend absent / clé absente → `SearchUnavailable`, **pas** une liste vide.
- Après un `web_search` dans un tour, une tentative de `create_reminder` est **refusée** et tracée
  (test de bout en bout de la règle de composition, le vrai enjeu de ce ticket).
- Un appel réel au backend retenu, lancé dans le container (la clé n'est pas sur l'hôte).

### Notes d'implémentation
