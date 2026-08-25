---
status: done
milestone: kb-visualisation
---

# Chantier — Visualisation de la base de connaissance (Obsidian déployé + miroir kanban)

> Origine : séance du 2026-08-24. Charte : `KNOWLEDGE_ARCHITECTURE.md` (racine) + roadmap sœur
> `roadmap/journal-knowledge-base.md` (KB journal déjà livrée : vault + index + export).
> Rien n'est déployé avant feu vert explicite.

## Direction (utilisateur)

Une **interface de visualisation** de la KB que l'agent alimente au fil de l'eau, reposant sur
**Obsidian déployé** (hébergé sur le VPS, pas seulement cloné en local), et qui **absorbe d'autres
outils** : le **kanban** doit s'y visualiser comme une **base de données explorable** (filtrable /
triable), les tâches devenant des nœuds du graphe reliés aux notes journal par les tags.

## Décisions

**Tranché :**
- ~~**Viewer = Obsidian réel en conteneur** (KasmVNC + Sablier scale-to-zero)~~ → **ABANDONNÉ le
  2026-08-25 (mur matériel, décidé par l'utilisateur)**. L'image KasmVNC `linuxserver/obsidian` pèse
  **5,18 GB** (bureau distant complet — Obsidian est Electron, aucun « Obsidian réel » plus léger
  n'existe) : la tirer a saturé le disque à **100 %** (box 38 GB, ~5,6 GB libres seulement) → risque
  de corruption Postgres/Coolify. RAM aussi très tendue (3,7 GB, ~770 MB libres). Voir DECISIONS.md.
- **Viewer = Quartz (site statique, même vault)** — le repli documenté devient le choix. Build du
  vault → HTML statique servi par un `nginx:alpine` (~15 MB image, RAM/disque quasi nuls, 0 risque
  prod), derrière coolify-proxy avec **basic-auth** (journal `private`). **Trade-off accepté** : on
  perd le filtrage **interactif** Bases/Dataview (kanban explorable en direct) ; on garde graphe,
  backlinks, recherche, lecture des notes. Réversible : le substrat (vault) est intact, on peut
  revenir à Obsidian réel si la box est upgradée.
- **Kanban → visu = miroir one-way DB→MD** (1 carte = 1 note `.md`). Postgres `cards` reste la
  vérité ; le vault reçoit une projection dérivée read-only.
- **Édition = lecture seule** (l'agent écrit, l'utilisateur lit). Conteneur monte le vault en RO.
- **Écartés** : Obsidian Publish (SaaS, journal `private`) ; fédération KB (charte §4). Quartz =
  repli documenté (même vault), non retenu.

**Reste à trancher (avant exécution du sprint concerné) :**
- ~~**Mapping `status`** des colonnes kanban~~ → **tranché** (Substrat livré) : `Terminé/Done → done`,
  `Rappels → reminder`, reste → `open`. Table `_STATUS_*` en tête de `kanban_vault.py`, comparaison
  sur nom de colonne slugifié.
- ~~**Sous-domaine**~~ → **tranché** : `kb.jlmvpscode.duckdns.org` (le viewer n'est plus Obsidian).

## Sprints

### Sprint 1 — Substrat · contexte partagé : écriture du vault, contrat frontmatter ✅
- [x] Miroir kanban → vault (writer one-way + réconciliation + trigger) → #1787600247611 · note : `kanban_vault.py`, réconcilié par `card_id`, job périodique `*/10`. **`card_fields` jamais peuplé → `tags` vide en pratique** (voir DECISIONS.md).
- [x] Notes-schéma + vues Bases/Dataview (taxonomie, MOC, Tâches, Journal) → #1787600247612 · note : `kb_schema_notes.py`, Taxonomie générée depuis le YAML, vues `.base` (format **provisoire** jusqu'au Sprint 2, cf. #612↔#613).

### Sprint 2 — Viewer · contexte partagé : Docker / Traefik ✅ (pivot Quartz, 2026-08-25)
> ⚠️ Approche KasmVNC/Obsidian **abandonnée** (image 5,18 GB → disque saturé, cf. Décisions +
> DECISIONS.md). Livré : **viewer statique Quartz** (`projects/kb-viewer/`), même vault.
- [x] ~~Conteneur Obsidian RO~~ → **Viewer Quartz** : `nginx:alpine` sert le site statique généré
  depuis le vault RO (build conteneurisé, sandbox). → #1787600247613 (fermé, superseded)
  · note : `projects/kb-viewer/`, `build.sh` (node:22 éphémère) + watcher systemd événementiel
  (`kb-viewer-build.path` sur les commits du vault, non exposé).
- [x] ~~Sablier scale-to-zero + auth~~ → **Auth + TLS via coolify-proxy** : basic-auth (journal
  `private`), 401 sans auth / 200 avec, cert Let's Encrypt. Scale-to-zero **sans objet** (nginx
  ~10 MB permanent). → #1787600247614 (fermé, superseded) · note : `docker-compose.override.yml`
  (hash gitignored), `kb.jlmvpscode.duckdns.org`.

> Cross-dépendance #612↔#613 **résolue** : sous Quartz les vues `.base` ne sont pas rendues (elles
> restent le contrat Obsidian, réactivables si retour à Obsidian). Le viewer expose graphe +
> backlinks + recherche + tags à la place. Voir note #612.

### Sprint 3 — Finition · contexte partagé : doc / UI ✅
- [x] Doc d'accès + landing (README vault, landing page, URL) → #1787600247615 · note : aligné sur
  le pivot Quartz (`kb.jlmvpscode.duckdns.org`, nginx permanent = pas de cold start). Landing
  (`main.py` : bouton + note lecture seule/mdp), `_README` vault (2 voies : web + git clone),
  `Accueil.md` (pointeur), CLAUDE.md projet (section KB en ligne ; racine déjà faite au pivot).

> Délégation (plancher) : *Substrat* et *Viewer* sont chacun un contexte couplé → au plus **un
> worker par sprint**, jamais un worker par ticket. *Finition* est trivial → Opus inline.

---

## Annexe — contrats / specs détaillés

### A. État de l'existant (à ne pas refaire)

| Brique | État | Où |
|---|---|---|
| Vault Markdown (pivot, git local) | ✅ | `/storage/journal-vault`, `journal_vault.py` |
| Index Postgres KB journal | ✅ `journal_kb_entries` (009) | contexte / nature[] / tags[] / body |
| Export enveloppe commune | ✅ vue `knowledge_federation_export` (010) | federation-ready |
| Ingestion #journal → classif → MD + upsert | ✅ | DeepInfra |
| Kanban | ✅ stockage **séparé** | tables `boards`/`columns`/`cards` + UI `public/kanban` |

Reframe : **substrat** (le vault, invariant) vs **viewer** (interchangeable). Le vrai travail
d'intégration = le miroir kanban→vault ; le viewer est un choix réversible sur le même vault.

### B. Architecture cible

- **Vault partagé** : le miroir kanban écrit dans le **même** vault que le journal
  (`/storage/journal-vault`), sous `tasks/`. Un seul substrat, un seul graphe.
- **Montage RO** : le conteneur Obsidian monte le vault en lecture seule (l'agent host reste seul
  à écrire).
- **Scale-to-zero** : Sablier (middleware Traefik) démarre le conteneur à la 1re requête, page
  d'attente pendant le boot, l'arrête après N min d'inactivité. Le WebSocket KasmVNC maintient la
  session tant que l'onglet est ouvert.

### C. Contrat du miroir kanban (frontmatter)

Source (`001_initial.sql`) : `boards(id,name,is_default)`, `columns(id,board_id,name,position)`,
`cards(id,column_id,title,description,due_date,reminder_sent_at,position,created_at,updated_at)`,
`card_fields(card_id,key,value)`.

Chaque carte → `vault/tasks/<board-slug>/<card-slug>.md` :

```markdown
---
type: task
card_id: <uuid>              # clé de réconciliation stable
board: Perso
column: En cours
position: 2
due: 2026-08-30              # depuis due_date ; null → absent
status: open                 # dérivé de la colonne (mapping à trancher)
tags: [management]           # depuis card_fields key='tag' ; sinon []
created_at: <cards.created_at ISO>
updated_at: <cards.updated_at ISO>
source: kanban
---

<description de la carte, verbatim>
```

- `doc_id` fédération : `assistant-ia:kanban:card/<uuid>`.
- **Réconciliation par `card_id`** : carte supprimée en base → note retirée du vault. C'est une
  **projection**, pas un append-only (≠ writer journal). Seule suppression autorisée, confinée à
  `vault/tasks/`.

### D. Points d'attention transverses

- **Sablier a besoin du socket Docker** (start/stop) — privilège à assumer, isoler via socket-proxy.
- **Auth obligatoire devant Obsidian** (journal `private`) : ordre des middlewares = auth **avant**
  Sablier (une requête non autorisée ne réveille même pas le conteneur).
- **Le miroir n'écrit jamais hors `vault/tasks/`** ni ne touche les notes journal — garde-fous de
  `journal_vault.py` (`_resolve_within_vault`, slug ASCII borné).
- **Bases vs Dataview** : format des vues figé seulement une fois connus les plugins de l'image
  (dépendance croisée #613 ↔ #612).
- **Réversibilité viewer** : bascule vers Quartz possible sans toucher au substrat.
