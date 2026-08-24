---
id: 1787579840504
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

Piste d'audit des appels d'outils — migration `015_agent_tool_calls.sql` + écriture depuis la boucle
(`roadmap/agent-outillage.md` §4).

**Pourquoi c'est un ticket à part entière et non une ligne de log.** La v1 du chantier
`agent-consignes` est auditable parce que *tout* le comportement de l'agent tient dans des versions
de doc relues et versionnées (`agent_versioning.py`). Les outils créent un chemin d'effet **hors**
de cette piste : un rappel apparaît en base sans qu'aucune version de doc n'ait changé. Sans
journalisation dédiée, on ne peut pas répondre après coup à « pourquoi ce rappel existe-t-il ? ».

### Colonnes

| Colonne | Rôle |
|---|---|
| `tool_name` | outil appelé |
| `arguments` | JSONB — arguments produits par le modèle, verbatim |
| `verdict` | `ok` / `refused` + motif (refus de la règle de composition, schema invalide, borne dépassée…) |
| `result_excerpt` | résultat tronqué (plafond du §3.4) |
| `slack_ts`, `thread_ts`, `channel_id`, `user_id` | rattachement au fil d'origine |
| `doc_version` | **version du doc système active au moment de l'appel** |
| `external_content_seen` | booléen — le flag de la règle de composition |
| `created_at` | horodatage |

`doc_version` et `external_content_seen` sont les deux colonnes qui font la valeur de cette table.
La première rattache l'appel au comportement audité en vigueur ; la seconde répond, en cas
d'incident, à la seule question qui compte : **est-ce que du contenu web était dans le contexte au
moment de cette écriture ?**

Les appels **refusés** sont journalisés au même titre que les autres : un refus répété est le
signal d'une tentative d'injection, et c'est précisément ce qu'on veut pouvoir constater.

### Contraintes

- Migration numérotée `015` — vérifier le dernier numéro présent (`014_agent_proposals.sql`) avant
  de créer, ne jamais modifier une migration existante (CLAUDE.md du projet).
- Idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
- **Un échec d'écriture d'audit ne doit pas faire perdre la réponse à l'utilisateur** — best-effort
  + `logger.exception`, comme `ensure_vault()` après le correctif de `#1787559677486`.

### Notes d'implémentation
