---
id: 1787579840506
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

Outil `web_search` (`taints_context: true`, `effect: read`). C'est le livrable utilisateur du ticket
ombrelle `#1787575860968`.

> **Révisé le 2026-08-24.** Deux changements par rapport à la version initiale :
> 1. **`fetch_url` sort de ce ticket** et part en v1.1 avec son contrôle d'egress → nouveau ticket
>    `#1787600000000`. Motif : c'est `fetch_url`, pas la recherche, qui ouvre une surface SSRF
>    (roadmap §4). `web_search` ne fait jamais émettre au VPS une requête vers une URL choisie par
>    le modèle.
> 2. **Plus « à faire en dernier »** : passe en v1, parallélisable avec `#1787579840505`. Le cadre à
>    éprouver (manifeste + `policy` + audit) est livré et testé par `#1787579840503` et
>    `#1787579840504`, indépendamment de tout outil réel.

**Dépend de** `#1787579840503` (manifeste + `policy`) et `#1787579840504` (audit).

### Périmètre — portage, pas écriture

`portfolio-tracker/backend/app/knowledge/websearch.py` (555 lignes) est **agnostique du
fournisseur** : `SEARCH_PROVIDER = exa | serper | none` sélectionne le backend, le contrat de sortie
(`SearchHit`) est identique. Copie adaptée, pas d'import inter-projets.

Ne porter que le chemin `search` — laisser `_fetch_url_direct` et `fetch_url` de côté (voir
`#1787600000000`, qui les reprendra avec la validation d'adresse manquante).

S’il existe un outil de recherche web qui fonctionne hébergé par DeepInfra, je souhaite l’utiliser. Sinon on pourra configurer Exa avec une nouvelle clef API comme nous l’avons fait pour le projet portfolio-tracker.

### Contraintes

- **Échec explicite, jamais silencieux** : sans clé, ou si le backend répond mal, lever
  `SearchUnavailable`. L'erreur remonte au modèle en `{"error": …}`. C'est la raison pour laquelle
  SearXNG auto-hébergé est écarté : depuis une IP captchaée il renvoyait des **résultats vides sans
  erreur**, et l'agent conclut alors à l'absence de source. Ne pas rouvrir cette piste sans traiter
  d'abord le problème d'IP.
- Plafond de caractères sur le contenu réinjecté (roadmap §3.5).
- Les extraits réinjectés sont encadrés d'un délimiteur explicite les désignant comme données
  citées, jamais comme instructions.
- Tout appel journalisé dans `agent_tool_calls` ; l'appel alimente `taint_sources` du tour avec les
  domaines effectivement rapportés (`web:exemple.com`), pas un booléen global.

### Vérification attendue

- Backend absent / clé absente → `SearchUnavailable`, **pas** une liste vide.
- Après un `web_search`, une tentative de `create_reminder` dans le **même tour** est **autorisée**
  mais bascule en régime `ConfirmerAvant` : Slack affiche le payload résolu et le domaine source,
  et rien n'est écrit avant le clic. C'est le test de bout en bout du modèle de taint
  (chaînage avec `#1787579840505`, à faire une fois les deux livrés).
- `taint_sources` contient bien les domaines rapportés par la recherche.
- Un appel réel au backend retenu, lancé dans le container (la clé n'est pas sur l'hôte).

### Notes d'implémentation
