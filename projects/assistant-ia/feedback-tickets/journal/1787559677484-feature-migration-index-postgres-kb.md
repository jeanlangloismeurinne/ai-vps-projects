---
id: 1787559677484
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

Créer la migration de l'**index requêtable** de la KB journal (le Markdown reste le pivot ;
Postgres est l'index dérivé — roadmap §2).

⚠️ La roadmap annonce `migrations/003_journal_kb.sql`, mais le dossier va **déjà jusqu'à 008**.
Le fichier à créer est donc **`migrations/009_journal_kb.sql`**. Ne pas modifier les migrations
existantes (`db.py` rejoue tous les `.sql` par ordre alphabétique au démarrage — tout doit être
idempotent : `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

Table `journal_kb_entries` — colonnes de l'**enveloppe document commune** (roadmap §5 +
`KNOWLEDGE_ARCHITECTURE.md`, schéma de référence `templates/knowledge-base/envelope.schema.json`) :

| Colonne | Type | Note |
|---|---|---|
| `doc_id` | `text PRIMARY KEY` | `assistant-ia:vps_files:journal/<slug>` |
| `project` | `text NOT NULL DEFAULT 'assistant-ia'` | |
| `source` | `text NOT NULL DEFAULT 'vps_files'` | |
| `uri` | `text NOT NULL` | chemin canonique du `.md` dans le vault |
| `title` | `text` | généré (cf. ticket classifieur) |
| `body` | `text NOT NULL` | verbatim Markdown |
| `contexte` | `text` | axe fixe : personnel / professionnel |
| `nature` | `text` | axe fixe : idee / apprentissage / … |
| `tags` | `text[] NOT NULL DEFAULT '{}'` | tags libres |
| `visibility` | `text NOT NULL DEFAULT 'private'` | journal personnel |
| `content_hash` | `text NOT NULL` | hash du `body` — dédup + sync incrémentale |
| `slack_ts` | `text` | message d'origine (traçabilité) |
| `created_at` / `updated_at` | `timestamptz NOT NULL DEFAULT now()` | |

Index : `content_hash` (dédup), `tags` en GIN, `created_at DESC`, `(contexte, nature)`.

Pas de `pgvector` à ce stade (phase ultérieure, cf. roadmap §8) — mais l'extension est déjà
disponible sur `shared-postgres` (image `pgvector/pgvector:pg16`), donc rien à prévoir maintenant.

La base cible est `db_assistant` (déjà réservée, `DATABASE_URL` existante).

### Vérification attendue

Redémarrage de l'app → migration appliquée sans erreur, rejouée une seconde fois sans erreur
(idempotence). `\d journal_kb_entries` conforme au tableau.

### Notes d'implémentation

`migrations/009_journal_kb.sql` — table `journal_kb_entries`, enveloppe document commune.

⚠️ **Correction d'une erreur de ce ticket** : le tableau des colonnes déclarait `nature | text`
(mono-valeur), alors que la roadmap `journal-knowledge-base.md:72` spécifie `nature` en
**0..n vocabulaire fermé**, et que #1787559677485 attend `nature[]`. La colonne est donc
`text[]`, et l'index composite `(contexte, nature)` prévu au ticket a été remplacé par un btree
sur `contexte` + un **GIN sur `nature`** — un btree sur colonne tableau ne sert qu'à l'égalité
stricte, inutile pour filtrer par axe. La table étant vide et la migration ni committée ni
déployée, elle a été corrigée sur place plutôt que rattrapée par une 010.

**Vérifié** : migration appliquée puis rejouée sur `db_assistant` (idempotente, 6 NOTICE
« already exists » au 2e passage), `\d journal_kb_entries` conforme, table vide avant recréation.
