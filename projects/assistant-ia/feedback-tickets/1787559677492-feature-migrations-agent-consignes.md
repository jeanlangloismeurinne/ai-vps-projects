---
id: 1787559677492
type: feature
status: closed
priority: medium
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: agent-consignes
closed_at: 2026-08-24T09:12:00+00:00
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Migration des 4 tables de l'agent conversationnel (roadmap `agent-consignes-systeme.md` §3).

Fichier : **`migrations/011_agent_consignes.sql`** (la roadmap n'était pas numérotée ; le dossier
va jusqu'à 008, +`009`/`010` pris par le chantier `journal-kb`). Idempotent (`IF NOT EXISTS`),
ne jamais modifier une migration existante.

| Table | Rôle | Colonnes clés |
|---|---|---|
| `agent_conversations` | historique des tours | `id`, `slack_ts`, `thread_ts`, `channel_id`, `user_id`, `role` (`user`/`assistant`), `content`, `created_at` |
| `agent_instruction_queue` | consignes `@admin` en attente | `id`, `slack_ts`, `user_id`, `content` (verbatim), `status` (`pending`/`proposed`/`approved`/`rejected`), `proposal_id`, `created_at` |
| `agent_system_doc` | « fichier système » **versionné** | `id`, `version` (int croissant), `content` (texte), `active` (bool), `created_by`, `created_at`, `parent_version` |
| `agent_audit_log` | trace **immuable** | `id`, `event` (`proposed`/`approved`/`rejected`/`edited`/`rollback`), `actor`, `instruction_ids`, `diff`, `from_version`, `to_version`, `created_at` |

Contraintes à poser en base, pas seulement en code :

- `agent_system_doc` : **index unique partiel** garantissant **une seule ligne `active = true`**
  (`CREATE UNIQUE INDEX … ON agent_system_doc (active) WHERE active`).
- `agent_system_doc.version` unique et croissant ; une nouvelle version ne modifie jamais une
  ligne existante (append-only) — c'est ce qui rend le **rollback** possible (§5.5).
- `agent_audit_log` : **jamais d'UPDATE ni de DELETE** dans le code. Le noter en commentaire SQL.
- `agent_instruction_queue.status` : contrainte `CHECK` sur les 4 valeurs.

Prévoir une **ligne initiale** de `agent_system_doc` (version 1, `active = true`) contenant le
prompt système de base de l'agent, pour que le chat ait toujours un doc actif à charger.

### Vérification attendue

Migration rejouée deux fois sans erreur. Tentative d'insertion d'une 2e ligne `active = true` →
rejetée par l'index unique.

### Notes d'implémentation

`migrations/011_agent_consignes.sql` — les 4 tables (`agent_conversations`,
`agent_instruction_queue`, `agent_system_doc`, `agent_audit_log`), PK UUID partout, ligne
initiale `agent_system_doc` v1 active insérée de façon idempotente (`ON CONFLICT (version)
DO NOTHING`).

**Vérifié en réel sur `db_assistant`**, contraintes mises en défaut et pas seulement déclarées :
migration rejouée 2 fois (toujours **une seule** ligne dans `agent_system_doc`) ; insertion d'une
2e ligne `active = true` → rejetée par `uq_agent_system_doc_active` ; `status` hors vocabulaire
→ rejeté par la contrainte CHECK. Commentaires SQL posés sur l'append-only de `agent_system_doc`
et l'interdiction d'UPDATE/DELETE sur `agent_audit_log`.
