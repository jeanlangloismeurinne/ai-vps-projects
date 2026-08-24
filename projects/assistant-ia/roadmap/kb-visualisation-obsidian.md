---
status: tickets-created
milestone: kb-visualisation
---

# Roadmap — Visualisation de la base de connaissance (Obsidian déployé + miroir kanban)

> Origine : séance du 2026-08-24 (« construire la visualisation de la KB que le modèle alimente »).
> Charte de référence : `KNOWLEDGE_ARCHITECTURE.md` (racine) + roadmap sœur
> `roadmap/journal-knowledge-base.md` (la KB journal, déjà livrée : vault + index + export).
> Statut : **direction validée, tickets créés**. Rien n'est déployé avant feu vert explicite.

---

## 1. Besoin (reformulé avec l'utilisateur)

Une **interface de visualisation** de la base de connaissance que l'agent alimente au fil de l'eau,
reposant sur **Obsidian déployé** (hébergé sur le VPS, pas seulement cloné en local). Elle doit
**absorber d'autres outils** : le **kanban** doit s'y visualiser comme une **base de données
explorable** (filtrable / triable), et les tâches devenir des nœuds du graphe de connaissance,
reliées aux notes journal par les tags.

## 2. Le reframe qui structure tout — substrat vs viewer

On sépare **le substrat** (invariant) du **viewer** (interchangeable). Le format du vault ne change
pas selon qu'on l'ouvre en Obsidian hébergé, en Quartz, ou en local (déjà noté par
`journal-knowledge-base.md` §6).

```
Sources (ce que le modèle alimente)          Substrat = LE vault Markdown           Viewer
─────────────────────────────────           ────────────────────────────           ──────
#journal → notes .md (déjà en place) ─┐
                                      ├──►  vault/  (source unique explorable) ──►  Obsidian déployé
kanban Postgres (boards/columns/cards)┘      • notes journal .md                     graphe · Bases · Dataview
   └ miroir one-way DB→MD                     • 1 carte = 1 note .md (frontmatter)     (viewer read-only + scale-to-zero)
                                              • notes-schéma : taxonomie, MOC, vues
```

## 3. Décisions verrouillées (séance 2026-08-24)

| Décision | Choix retenu | Motif |
|---|---|---|
| **Viewer** | **Obsidian réel en conteneur** (KasmVNC web) **+ Sablier scale-to-zero** | Seul chemin qui rend le kanban interactivement filtrable comme une base (Bases/Dataview). Le scale-to-zero neutralise l'objection RAM : conteneur arrêté (~0 RAM) au repos, réveillé à la demande (~15-30 s de latence au 1er accès). |
| **Kanban → visu** | **Miroir one-way DB→MD** (1 carte = 1 note `.md`) | Postgres `cards` reste la source de vérité (l'app et les rappels y écrivent). Le vault en reçoit une projection dérivée read-only. Tâches = nœuds du graphe. |
| **Édition** | **Lecture seule** (l'agent écrit, l'utilisateur lit) | Cohérent avec `journal_vault.py` et l'index dérivé. Aucun conflit vault↔index. Le conteneur monte le vault en RO. |
| ~~Obsidian Publish (SaaS)~~ | **écarté** | Synchroniserait un journal `visibility: private` sur les serveurs d'Obsidian — contre le principe « tout reste sur le VPS ». |
| Quartz (repli) | **repli documenté, non retenu en v1** | Toujours allumé ~0 RAM mais read-only figé, pas de vue base de données interactive. Réversible : même vault. |

## 4. Architecture cible

```
┌─ VPS ────────────────────────────────────────────────────────────────────┐
│                                                                            │
│  Postgres (cards/columns/boards) ──► job miroir ──► /storage/journal-vault │
│  (source de vérité tâches)          (one-way DB→MD)   (vault unique, RO     │
│                                                        pour le viewer)      │
│                                                                            │
│  Traefik + Sablier ──(docker start/stop à la demande)──► conteneur Obsidian │
│     │  auth devant                                        (KasmVNC + vault   │
│     ▼                                                       monté en RO)     │
│  obsidian.jlmvpscode.duckdns.org                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Vault partagé** : le miroir kanban écrit dans le **même** vault que les notes journal
  (`/storage/journal-vault`), sous un sous-dossier `tasks/`. Un seul substrat, un seul graphe.
- **Montage RO** : le conteneur Obsidian monte le vault en lecture seule → l'utilisateur consulte,
  n'édite pas (décision §3). L'agent (host) reste seul à écrire.
- **Scale-to-zero** : Sablier (middleware Traefik) démarre le conteneur à la première requête,
  affiche une page d'attente pendant le boot, l'arrête après N min d'inactivité. Le WebSocket
  KasmVNC maintient la session vivante tant que l'onglet est ouvert.

## 5. Frontmatter du miroir kanban (contrat)

Schéma source (migration `001_initial.sql`) : `boards(id,name,is_default)`,
`columns(id,board_id,name,position)`, `cards(id,column_id,title,description,due_date,
reminder_sent_at,position,created_at,updated_at)`, `card_fields(card_id,key,value)`.

Chaque carte → `vault/tasks/<board-slug>/<card-slug>.md` :

```markdown
---
type: task
card_id: <uuid>              # clé de réconciliation (stable)
board: Perso
column: En cours
position: 2
due: 2026-08-30              # depuis due_date (null → absent)
status: open                 # dérivé de la colonne (voir ticket miroir)
tags: [management]           # depuis card_fields 'tag' si présent, sinon []
created_at: 2026-08-24T…Z
updated_at: 2026-08-24T…Z
source: kanban
---

<description de la carte, verbatim>
```

- **doc_id fédération** : `assistant-ia:kanban:card/<uuid>` (aligné sur l'enveloppe commune, même
  logique que la KB journal — export possible plus tard, non requis en v1).
- Réconciliation par `card_id` : une carte supprimée en base → sa note est **retirée du vault**
  (le miroir est une projection, pas un journal append-only — c'est la différence avec le writer
  journal, à traiter explicitement dans le ticket).

## 6. Tickets d'implémentation — créés le 2026-08-24 (`milestone: kb-visualisation`)

| ID | Ticket | Complexité | Dépend de |
|---|---|---|---|
| `1787600247611` | **Miroir kanban → vault** — job one-way DB→MD, writer + trigger + réconciliation | complexe | — |
| `1787600247612` | **Notes-schéma + vues Bases/Dataview** — taxonomie, MOC/accueil, vues Tâches & Journal | moyen | T1 (pour la vue Tâches) |
| `1787600247613` | **Conteneur Obsidian read-only** — image KasmVNC + plugins + montage vault RO | complexe (infra) | — |
| `1787600247614` | **Sablier scale-to-zero + Traefik + auth** | complexe (infra) | T3 |
| `1787600247615` | **Doc d'accès + landing** — README vault, section landing page, URL | simple | T3, T4 |

Ordre conseillé : **T1 + T3 en parallèle** (substrat / infra, indépendants) → **T2** (vues, a
besoin des notes tâches) et **T4** (dépend du conteneur) → **T5** (doc, en dernier).

## 7. Points d'attention transverses

- **Sablier a besoin du socket Docker** (start/stop) — composant de confiance, privilège à assumer.
  Isoler autant que possible (socket proxy en lecture/action limitée si dispo).
- **Auth obligatoire devant Obsidian** : le vault contient un journal `private`. Ne jamais exposer
  l'URL sans authentification (basic auth Traefik au minimum). Vérifier UFW/Traefik comme pour tout
  service réseau (checklist `COOLIFY_PLAYBOOK.md`).
- **Le miroir ne doit jamais écrire hors `vault/tasks/`** ni toucher les notes journal — mêmes
  garde-fous de chemin que `journal_vault.py` (`_resolve_within_vault`, slug ASCII borné).
- **Cohérence avec la charte** : pas de nouvelle couche fédérée (tranché caduc dans
  `journal-knowledge-base.md` §8). Le miroir est un viewer, pas un second silo de vérité.
- **Réversibilité viewer** : si Obsidian conteneur + Sablier se révèle trop lourd à l'usage, bascule
  vers Quartz sans toucher au substrat (même vault).
