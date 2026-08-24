---
id: 1787559677486
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
project: assistant-ia
url: 
milestone: journal-kb
closed_at: 2026-08-24T09:35:00+00:00
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Le **vault Obsidian** (pivot Markdown lisible) et son exposition à l'utilisateur.

> **Décision révisée le 2026-08-24** : la roadmap §6 retenait l'option A (Nextcloud WebDAV), mais
> **il n'y a aucun Nextcloud sur le VPS** (`docker ps` : rien). Plutôt que d'ajouter un chantier
> d'infra en amont, on part sur l'**option B — dépôt git** pour la v1. Le vault reste un simple
> dossier de `.md` : un passage ultérieur vers Nextcloud/WebDAV ne changerait que la couche de
> synchronisation, pas le format ni le code d'écriture.

**1. Arborescence du vault**

```
/storage/journal-vault/          ← volume bind-mount, hors image Docker
  .obsidian/                     ← config Obsidian versionnée (facultatif)
  2026/
    2026-08-24-reunion-equipe-produit.md
  README.md                      ← « vault écrit par l'agent, ne pas éditer à la main »
```

Le chemin est configurable : `JOURNAL_VAULT_PATH` (défaut `/storage/journal-vault`). Monter le
volume dans `docker-compose.yml` (en **écriture** — contrairement à `/storage/Documents` qui est
en lecture seule).

**2. Writer Markdown** — `app/services/journal_vault.py`

Un fichier par entrée, front-matter YAML + corps verbatim :

```markdown
---
doc_id: assistant-ia:vps_files:journal/2026-08-24-reunion-equipe-produit
contexte: professionnel
nature: [apprentissage]
tags: [management]
created_at: 2026-08-24T08:21:17Z
slack_ts: "1787559677.482"
---

<verbatim de l'utilisateur>
```

Garde-fous (repris de la roadmap §6.1, valables quel que soit le backend) :

- Chemin **toujours dérivé du slug généré côté serveur**, jamais d'un input utilisateur brut :
  slugifier, ASCII, longueur bornée, et **vérifier que le chemin résolu reste sous le vault**
  (protection contre `../`).
- **Append-only** : on n'écrase jamais un fichier existant (suffixe `-2`, `-3` en cas de collision
  de slug le même jour). **Aucune suppression**, jamais de suppression récursive.
- Écriture atomique (fichier temporaire + `os.replace`).

**3. Exposition à l'utilisateur**

- Le vault est un **repo git local** sur le VPS (`git init` dans le dossier).
- Après chaque écriture : `git add` + `git commit` automatique (message = titre de l'entrée).
  Commit local uniquement — **pas de push vers un remote** en v1 (le vault est privé, `visibility:
  private`, et un push nécessiterait un dépôt distinct de `ai-vps-projects`).
- L'utilisateur récupère le vault en le clonant depuis le VPS (ssh) et l'ouvre dans Obsidian ;
  `git pull` pour rafraîchir. Documenter la commande exacte dans le `README.md` du vault.

⚠️ Le vault ne doit **pas** être committé dans `ai-vps-projects` (contenu personnel) → ajouter
`/storage/journal-vault` au `.gitignore` si le chemin devait tomber dans le repo.

### Vérification attendue

Écriture de 3 entrées dont deux avec le même slug le même jour → 3 fichiers, aucun écrasement.
Tentative d'écriture avec un slug contenant `../` → refusée. `git log` dans le vault montre les
commits.

### Notes d'implémentation

`app/services/journal_vault.py` — `write_entry()` + `ensure_vault()`. Vault créé sur le VPS
(`/storage/journal-vault`) et monté **en écriture** dans `docker-compose.yml`.

**Deux prérequis d'infra découverts et corrigés** :
- `git` n'était **pas installé dans l'image** (python:3.12-slim + curl seulement) → ajouté au
  `Dockerfile`. Sans ça, tout le versionnage du vault était silencieusement mort.
- `PyYAML` n'était qu'une dépendance transitive → épinglé dans `requirements.txt` (utilisé ici
  pour le frontmatter et par le classifieur #1787559677485).

**Deux barrières de chemin, pas une** : `slugify()` produit un slug ASCII borné sans séparateur,
et `_resolve_within_vault()` revérifie que le chemin résolu est sous le vault. Aucune suppression
nulle part, sauf le fichier temporaire de l'écriture atomique. Commit git best-effort : une note
écrite mais non committée reste lisible, donc un échec git ne fait pas échouer l'ingestion.

**Vérifié** (18 assertions, toutes passées) : 3 entrées dont 2 de même slug le même jour → 3
fichiers, suffixe `-2`, corps de la 1re intact ; corps verbatim préservé (y compris un faux `---`
et l'indentation) ; `../../etc/passwd`, `/etc/passwd`, `..` et
`../../../root/.ssh/authorized_keys` neutralisés en slug, écriture confinée au vault ;
`_resolve_within_vault` lève sur `../` ; aucun `.tmp` résiduel ; `git log` = 5 commits, arbre
propre ; frontmatter relu par `yaml.safe_load` et conforme.

Le vault est hors du repo (`/storage/journal-vault`), il ne peut donc pas tomber dans
`ai-vps-projects` — pas de `.gitignore` nécessaire.
