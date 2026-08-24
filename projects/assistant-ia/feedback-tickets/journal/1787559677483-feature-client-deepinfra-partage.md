---
id: 1787559677483
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: journal-kb
closed_at: 2026-08-24T09:12:00+00:00
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Brique **commune aux deux chantiers** (`journal-kb` classification, `agent-consignes` conversation
et synthèse) — à livrer en premier, **une seule fois**.

Créer `app/services/deepinfra_client.py`. **Ne pas repartir de zéro** : porter l'implémentation
déjà en production dans
`projects/portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py`
(endpoint OpenAI-compatible, gestion d'erreurs, timeouts). Copier le patron — pas d'import
inter-projets, ce sont deux apps Coolify distinctes.

Périmètre :

- `chat(messages, model, temperature, max_tokens)` → texte.
- `chat_json(messages, model, schema)` → dict validé contre un schéma JSON ; lève si la sortie
  n'est pas du JSON conforme (utilisé par le classifieur du journal).
- Timeout explicite + **1 retry** sur erreur réseau/5xx ; jamais de retry sur 4xx.
- Aucun secret loggé ; en cas d'échec, log du code HTTP et de la raison, pas du payload.

Config (`app/config.py`) :

- `DEEPINFRA_API_KEY: str = ""`
- `DEEPINFRA_API_BASE: str = "https://api.deepinfra.com/v1/openai"`
- `DEEPINFRA_MODEL_CLASSIF: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"`
- `DEEPINFRA_MODEL_CHAT` / `DEEPINFRA_MODEL_SYSTEM` — modèles de conversation et de rédaction
  de consignes (roadmap agent §6 : « DeepSeek V4 Flash » / « DeepSeek V4 Pro » — **vérifier les
  identifiants exacts au catalogue DeepInfra au moment de l'implémentation**, les noms cités
  dans la roadmap ne sont pas garantis d'exister).

Nommer les variables comme portfolio-tracker (`DEEPINFRA_API_BASE`, pas `DEEPINFRA_BASE_URL`
comme écrit dans la roadmap) pour rester cohérent d'un projet à l'autre.

`DEEPINFRA_API_KEY` doit être ajoutée aux variables d'env Coolify d'assistant-ia au déploiement.

### Vérification attendue

Un appel réel minimal (`chat` sur le modèle de classification) qui renvoie une réponse, et un
`chat_json` dont la sortie est validée. Si la clé n'est pas encore provisionnée, le client doit
échouer proprement (message explicite) sans casser le démarrage de l'app.

### Notes d'implémentation

`app/services/deepinfra_client.py` porté depuis
`portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py` (copie adaptée, pas
d'import inter-projets). `chat()` + `chat_json()`, timeout explicite, 1 retry réseau/5xx et
jamais sur 4xx, aucun secret loggé, échec propre à l'appel si la clé est absente (l'app démarre).

**Identifiants de modèles vérifiés au catalogue DeepInfra ce jour** (le ticket l'exigeait) :
`meta-llama/Meta-Llama-3.1-8B-Instruct` (classif), `deepseek-ai/DeepSeek-V4-Flash` (chat),
`deepseek-ai/DeepSeek-V4-Pro` (système) existent bien. Défauts posés dans `app/config.py`.

⚠️ **Écart de spec assumé** : le ticket demandait `response_format: json_schema` avec
`strict: true`. Llama 3.1 8B renvoie **HTTP 405** sur `json_schema` → repli automatique sur
`json_object` + validation stricte côté Python (json.loads + vérification des clés). La garantie
« sortie conforme » vient donc du code, pas du modèle. Sans conséquence pour le classifieur
(#1787559677485) qui a de toute façon un fallback « à classer ».

**Vérifié** : appels réels facturés sur DeepInfra — `chat` HTTP 200 (contenu renvoyé) et
`chat_json` HTTP 200 avec sortie validée contre un schéma.
