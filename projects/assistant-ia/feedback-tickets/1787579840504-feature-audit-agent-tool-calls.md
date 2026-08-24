---
id: 1787579840504
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

Piste d'audit des appels d'outils — migration `015_agent_tool_calls.sql` + écriture depuis la boucle
(`roadmap/agent-outillage.md` §4).

**Pourquoi c'est un ticket à part entière et non une ligne de log.** La v1 du chantier
`agent-consignes` est auditable parce que *tout* le comportement de l'agent tient dans des versions
de doc relues et versionnées (`agent_versioning.py`). Les outils créent un chemin d'effet **hors**
de cette piste : un rappel apparaît en base sans qu'aucune version de doc n'ait changé. Sans
journalisation dédiée, on ne peut pas répondre après coup à « pourquoi ce rappel existe-t-il ? ».

Évalue l’opportunité de recourir à Logfire plutôt que de tout recoder.

### Colonnes

| Colonne | Rôle |
|---|---|
| `tool_name` | outil appelé |
| `arguments` | JSONB — arguments produits par le modèle, verbatim |
| `verdict` | `ok` / `confirmation_requise` / `refused` + motif (schema invalide, `rate_limit` dépassé, egress refusé…) |
| `result_excerpt` | résultat tronqué (plafond du §3.5) |
| `slack_ts`, `thread_ts`, `channel_id`, `user_id` | rattachement au fil d'origine |
| `doc_version` | **version du doc système active au moment de l'appel** |
| `taint_sources` | JSONB — **tableau** des sources non fiables présentes dans le contexte (`["web:exemple.com", "file:rapport.pdf"]`) |
| `user_confirmed` | booléen — l'utilisateur a-t-il cliqué `Confirmer` avant l'écriture |
| `created_at` | horodatage |

`doc_version` et `taint_sources` sont les deux colonnes qui font la valeur de cette table. La
première rattache l'appel au comportement audité en vigueur ; la seconde répond, en cas d'incident,
à la seule question qui compte : **quelle source non fiable était dans le contexte au moment de
cette écriture ?**

> **Révisé le 2026-08-24** : `external_content_seen` (booléen) devient `taint_sources` (tableau).
> Un booléen ne dit pas *laquelle* des sources était présente — inexploitable en incident dès qu'il
> y a plus d'un outil taintant — et ne couvrait que le web, alors que fichiers, messages de tiers et
> payloads de services taintent tout autant (roadmap §2.2). Le tableau se généralise sans migration.

Les appels **refusés** sont journalisés au même titre que les autres : un refus répété est le
signal d'une tentative d'injection, et c'est précisément ce qu'on veut pouvoir constater.

### Contraintes

- Migration numérotée `015` — vérifier le dernier numéro présent (`014_agent_proposals.sql`) avant
  de créer, ne jamais modifier une migration existante (CLAUDE.md du projet).
- Idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
- **Un échec d'écriture d'audit ne doit pas faire perdre la réponse à l'utilisateur** — best-effort
  + `logger.exception`, comme `ensure_vault()` après le correctif de `#1787559677486`.

### Notes d'implémentation