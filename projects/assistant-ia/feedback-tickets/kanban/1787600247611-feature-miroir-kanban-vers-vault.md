---
id: 1787600247611
type: feature
status: closed
priority: high
date: 2026-08-24T19:37:27Z
closed_at: 2026-08-25T00:00:00Z
project: assistant-ia
url:
milestone: kb-visualisation
---

## ✨ Feature

**Date** : 24/08/2026 19:37
**URL** : `N/A`

### Description

Miroir **one-way** du kanban (Postgres `boards`/`columns`/`cards`/`card_fields`, source de vérité)
vers le vault Markdown, pour que les tâches deviennent des nœuds explorables du graphe de
connaissance (roadmap `roadmap/kb-visualisation-obsidian.md` §5).

**Sens de la synchro** : **DB → MD uniquement**. Postgres reste la vérité (l'app kanban et l'outil
`create_reminder` y écrivent). Le vault reçoit une **projection dérivée read-only**. Ce n'est **pas**
un writer append-only comme `journal_vault.py` : c'est un miroir **réconcilié** (une carte
supprimée en base → sa note disparaît du vault).

**1. Emplacement** — `vault/tasks/<board-slug>/<card-slug>.md` dans le **même** vault que le journal
(`/storage/journal-vault`, `JOURNAL_VAULT_PATH`). Un seul substrat, un seul graphe.

**2. Frontmatter** (contrat roadmap §5) :

```markdown
---
type: task
card_id: <uuid>              # clé de réconciliation stable
board: Perso
column: En cours
position: 2
due: 2026-08-30              # depuis cards.due_date ; null → clé absente
status: open                 # dérivé de la colonne (mapping ci-dessous)
tags: [management]           # depuis card_fields où key='tag' ; sinon []
created_at: <cards.created_at ISO>
updated_at: <cards.updated_at ISO>
source: kanban
---

<cards.description, verbatim ; vide si NULL>
```

- `doc_id` logique (non écrit en frontmatter si non nécessaire) : `assistant-ia:kanban:card/<uuid>`.
- **Mapping `status`** : proposition — colonnes `Terminé`/`Done` → `done` ; `Rappels` → `reminder` ;
  toute autre → `open`. À figer dans une petite table de correspondance en tête de module (pas de
  magie dispersée). Documenter le mapping choisi dans les Notes d'implémentation.
- `tags` : lire `card_fields` avec `key='tag'` (0..n). Si le schéma des champs libres diffère,
  prendre la décision la plus simple et la noter.

**3. Réconciliation** (différence clé avec le writer journal) :

- Indexer les notes existantes de `vault/tasks/` par `card_id` (lecture du frontmatter).
- Cartes en base absentes du vault → **créer** la note.
- Cartes présentes des deux côtés → **réécrire** si `updated_at` ou contenu a changé (comparer un
  hash ou l'`updated_at`).
- Notes dont le `card_id` n'existe plus en base → **supprimer** la note (et son dossier board si
  vide). C'est la seule suppression autorisée, strictement confinée à `vault/tasks/`.

**4. Déclenchement** :

- **Réconciliation périodique** (job, ex. toutes les 5-15 min ou via le scheduler existant type
  `check_objectif_reminders`) : source de vérité du miroir, robuste aux écritures manquées.
- **Best-effort à l'écriture** (optionnel v1) : après une mutation de carte (`kanban.py`
  create/update/move/delete, `create_reminder`), déclencher une resync de la carte concernée. Si
  trop couplant, s'en tenir au job périodique pour la v1 et le noter.

**5. Garde-fous** (repris de `journal_vault.py`, non négociables) :

- Chemin **toujours** dérivé d'un slug ASCII borné généré côté serveur (réutiliser `slugify` /
  `_resolve_within_vault` de `journal_vault.py`, ou factoriser un helper commun). Jamais de chemin
  dérivé d'un `title`/`board` brut.
- **Écriture atomique** (tmp + `os.replace`). **Aucune** écriture ni suppression hors
  `vault/tasks/` — ne jamais toucher les notes journal ni la racine du vault.
- Commit git best-effort du vault après resync (comme le journal), message `sync kanban`.

### Vérification attendue

- 1 board, 2 colonnes, 3 cartes → 3 notes sous `vault/tasks/<board>/`, frontmatter conforme,
  `due` absent quand `due_date` NULL.
- Déplacer une carte de colonne → la note reflète la nouvelle `column`/`status` au prochain run,
  sans doublon (réconciliation par `card_id`, pas par slug).
- Supprimer une carte en base → sa note disparaît ; les autres intactes ; dossier board retiré si
  vide.
- Tentative de board/title piégé (`../`, `/etc/...`) → neutralisé en slug, écriture confinée.
- `git log` du vault montre les commits de sync.

### Notes d'implémentation

Livré dans `app/services/kanban_vault.py` (`sync_kanban_vault()`), déclenché par le job
`app/jobs/kb_sync.py` (scheduler `CronTrigger(minute="*/10")` dans `main.py`).

**Décisions prises :**
- **Mapping `status`** : tables `_STATUS_DONE` / `_STATUS_REMINDER` en tête de module, comparaison
  sur le **nom de colonne slugifié** (insensible aux accents/casse). `Terminé/Done/Fait/Clôturé →
  done`, `Rappels/Reminder → reminder`, reste → `open`.
- **`tags`** : lecture de `card_fields WHERE key='tag'`. ⚠️ La table `card_fields` n'est **écrite
  nulle part** dans le code actuel → `tags` est **vide en pratique**. Implémenté par contrat, noté
  dans `DECISIONS.md` (à revisiter si les tags de carte deviennent réels).
- **Réconciliation par `card_id`** (lu dans le frontmatter des notes existantes) : titre/board
  modifié → la note **migre** (ancien chemin supprimé) sans doublon ; carte supprimée en base →
  note retirée + dossier board vidé nettoyé. Seule suppression autorisée, confinée à `tasks/`.
- **Collision de slug** entre cartes distinctes du même board → suffixe court `-<card_id[:8]>`.
- **Déclenchement** : job périodique uniquement (source de vérité, robuste aux écritures manquées).
  Le hook best-effort à la mutation de carte est laissé pour plus tard (couplant, non requis en v1).
- Garde-fous `slugify` + `_resolve_within_vault` + écriture atomique **factorisés** (importés de
  `journal_vault.py`, pas dupliqués). Commit git best-effort `sync kanban`.

**Vérification** : `/tmp/test_kb_sync.py` (stubs config/db, vault temporaire git) — 26 checks verts
couvrant create / move / rename / delete / collision / **traversée `../` neutralisée** / commits git.
Réconciliation réelle contre Postgres vérifiée après déploiement (le vault vit sur le VPS).
