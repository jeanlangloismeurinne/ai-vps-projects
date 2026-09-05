# DECISIONS — assistant-ia

> Système de référence des **faits durables** : gotchas réutilisables et « pourquoi » d'architecture.
> Versionné, greppable. La mémoire agent n'en est qu'un cache. Un fait porteur vit **ici**, pas
> uniquement dans un résumé de session (qui scrolle hors de vue) ni dans la mémoire (point-in-time).

## LLM / DeepInfra

- **DeepInfra refuse `response_format: json_schema` pour Llama 3.1 8B-Turbo → HTTP 405.**
  Conséquences observées : double appel (405 puis fallback `json_object`), vocabulaire fermé non
  respecté, cardinalité non honorée. **Correctif** : utiliser un modèle qui supporte `json_schema`
  (`DeepSeek-V4-Flash`) + vocabulaire en **`enum`** (toujours dérivé de `categories.schema.yaml`).
  Garder la validation Python : seul garde-fou si l'appel retombe sur `json_object`.
- **`Meta-Llama-3.1-8B-Instruct` est déprécié chez DeepInfra depuis le 2026-07-16.** Ne pas s'y
  reposer ; préférer la variante supportée retenue ci-dessus.
- **Vérifier contre l'API réelle.** Un correctif de prompt/schéma ne tient pas tant qu'il n'a pas
  tourné contre le vrai modèle : le 405 ci-dessus était **invisible en test** et trouvé seulement en
  appelant DeepInfra. Corollaire de pilotage : front-loader un spike contre la dépendance externe
  avant de bâtir des tickets qui la présument.
- **Clé DeepInfra** : celle utilisée a été **empruntée** à portfolio-tracker (copiée chiffrée dans
  Coolify). ⚠️ En générer une propre à assistant-ia.

## Bases de connaissance

- **Fédération KB : on ne construit pas** (tickets `1787559677490/491` fermés `wont-do-for-now`).
  `KNOWLEDGE_ARCHITECTURE.md` §4 (charte transverse) l'emporte sur une roadmap projet. Aucune
  requête multi-source formelle → besoin supposé, pas constaté. L'export « enveloppe commune » étant
  livré, la décision est réversible. **Condition de réouverture** : une requête traversant deux
  sources réellement formulée.

## Miroir kanban → vault (KB visuelle, sprint Substrat)

- **`card_fields` n'est écrit nulle part** dans le code (table définie en `001_initial.sql`, jamais
  peuplée par `kanban.py`/`create_reminder`). Le miroir lit bien `key='tag'` par contrat, mais
  **`tags` est vide en pratique** tant qu'un chemin d'écriture n'existe pas. Ne pas conclure « le
  miroir perd les tags » : il n'y a rien à lire. À revisiter si les tags de carte deviennent réels.
- **Le miroir est une projection réconciliée, pas un writer append-only** (≠ `journal_vault.py`).
  Réconciliation **par `card_id`** (lu dans le frontmatter), jamais par slug : un titre/board modifié
  fait *migrer* la note (ancien chemin supprimé), une carte supprimée en base fait disparaître la
  note. Seule suppression autorisée, strictement confinée à `vault/tasks/` (double barrière
  `slugify` + `_resolve_within_vault`, réutilisées depuis `journal_vault.py`).
- **Vues Obsidian = format `.base` (plugin cœur Bases), PROVISOIRE.** Le rendu réel n'est pas
  vérifiable tant que le conteneur Obsidian (sprint Viewer, #1787600247613) n'a pas figé la version
  embarquée : dépendance croisée #612 ↔ #613. Repli documenté = Dataview (mêmes vues en blocs
  ```dataview``` dans des `.md`). Ne pas considérer le format `.base` comme acquis avant Sprint 2.

## Viewer KB (sprint Viewer, 2026-08-25)

- **« Obsidian réel en conteneur » est intenable sur cette box.** L'image KasmVNC
  `linuxserver/obsidian` pèse **5,18 GB** (bureau distant complet — Obsidian est Electron, aucun
  « Obsidian réel » plus léger n'existe : le servir au navigateur impose un desktop distant). La
  tirer a mis `/` à **100 %** (38 GB, ~5,6 GB libres) → **risque de corruption Postgres/Coolify**.
  RAM aussi tendue (3,7 GB total, ~770 MB libres, 0 swap). **Décision utilisateur** : basculer sur
  le repli documenté **Quartz** (site statique, même vault). Trade-off accepté : perte du filtrage
  interactif Bases/Dataview ; conservation graphe/backlinks/recherche. Réversible (substrat intact).
  **Leçon de pilotage** : front-loader un check `df -h` + taille d'image AVANT de tirer une image
  lourde sur une box de prod partagée (le même réflexe que « vérifier contre l'API réelle »).
- **Ne jamais laisser `/` atteindre 100 %** : `docker pull` d'une grosse image peut saturer et
  faire tomber les bases. Récupération à chaud : `swapoff/rm /swapfile` (2 GB instantanés),
  `docker rm -f <conteneur>` puis `docker rmi <image>` (l'image reste référencée par son conteneur
  arrêté). `docker image prune -f` ne libère QUE le dangling (pas les images taguées non utilisées).
- **Build d'un site statique depuis du code externe (Quartz)** : le faire dans un conteneur
  `node:22` **éphémère** (scripts npm sandboxés, jamais sur l'hôte), pas `npm install` sur l'hôte.
  Quartz `rmdir` son dossier de sortie → builder vers un dossier local puis copier le CONTENU dans
  le volume (jamais le point de montage = EBUSY). Quartz 4.5.1 exige **Node ≥ 22**. Détails et
  exploitation : `projects/kb-viewer/README.md`.

## Doc système et capture KB (chantier intention/capture, 2026-09-05)

- **`@admin`/`@update` est l'outil de l'utilisateur, pas le canal de livraison.** Ce cycle existe
  pour que l'utilisateur *coache* l'agent depuis Slack, sans ouvrir autre chose — « adopte
  durablement tel comportement ». Le **contenu livré** du doc système, lui, passe par une migration,
  comme la v1 semée par `011_agent_consignes.sql`. Ne pas confondre les deux : faire passer une
  livraison par `@update`, c'est faire réécrire son propre texte par DeepSeek et demander à
  l'utilisateur d'approuver un diff qu'il n'a pas commandé. *(Tranché par l'utilisateur.)*
- **Une migration qui sème du contenu doit se garder contre les décisions humaines postérieures.**
  Le runner rejoue tous les `.sql` à chaque démarrage. Garde correcte : « aucune version ≥ N
  n'existe » — jamais « la version N n'existe pas », qui ressusciterait le contenu semé par-dessus
  un rollback ou une version approuvée dans Slack. Vérifié par test négatif sur base jetable :
  rollback simulé vers v1, ré-application, v1 reste active.
- **Piège SQL : `E'…' '\n' '…'` ne fait pas ce qu'on croit.** Le préfixe `E` ne s'applique qu'au
  littéral qui le porte ; les fragments concaténés suivants insèrent un antislash-n **littéral**.
  Pour du texte multi-ligne, dollar-quoting (`$doc$…$doc$`) — vérifié par
  `position('\n' in content) = 0`.
- **`journal_vault.py` ne sait pas ajouter une ligne à un fichier existant.** `write_entry` est
  « append-only » au sens *ne jamais écraser* : elle crée `{année}/{AAAA-MM-JJ}-{slug}.md` et
  suffixe en cas de collision. Le mode `append` des listes nommées (D5) exige donc une **fonction
  neuve**, pas une réutilisation — et l'arborescence `notes/{slug}.md` de la roadmap ne correspond
  pas à ce que le writer produit aujourd'hui. La roadmap annonçait « zéro brique neuve » : c'est
  faux, et ça recalibre la capacité 2.

---
_Historique détaillé des sessions : `git log` + `roadmap/archive/`._
