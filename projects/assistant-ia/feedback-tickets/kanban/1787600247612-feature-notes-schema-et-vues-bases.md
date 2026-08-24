---
id: 1787600247612
type: feature
status: open
priority: high
date: 2026-08-24T19:37:27Z
project: assistant-ia
url:
milestone: kb-visualisation
---

## ✨ Feature

**Date** : 24/08/2026 19:37
**URL** : `N/A`

### Description

Écrire dans le vault les **notes-schéma** qui font de la KB une surface *explorable* dans Obsidian :
page d'accueil (MOC), note de taxonomie, et surtout les **vues base de données** (Obsidian
**Bases**, plugin cœur ; **Dataview** en repli) qui rendent le kanban filtrable/triable — la demande
centrale de la roadmap (`roadmap/kb-visualisation-obsidian.md` §1).

Ces fichiers sont **générés/maintenus par l'agent** (écrits côté host, comme le reste du vault),
versionnés, et vivent à la racine du vault (hors `tasks/` et hors dossiers d'années journal).

**1. Page d'accueil / MOC** — `vault/README.md` ou `vault/Accueil.md` :
- explique que le vault est écrit par l'agent, lecture seule ;
- liens vers les vues (Tâches, Journal) et vers la note taxonomie ;
- (compléter/aligner avec le `_README` existant de `journal_vault.py` — ne pas dupliquer, factoriser
  le message « ne pas éditer à la main »).

**2. Note taxonomie** — `vault/Taxonomie.md` :
- rend lisible `app/knowledge/categories.schema.yaml` (axes `contexte`, `nature`, tags libres) ;
- **générée depuis le YAML** (source de vérité), pas ressaisie à la main — au prochain run elle
  reflète le schéma courant.

**3. Vues base de données** (le cœur du ticket) :

- **Vue Tâches** — `vault/Tâches.base` (Bases) : liste toutes les notes `type: task`, colonnes
  `board`, `column`, `due`, `tags` ; regroupement par `column` (rendu type kanban) ; filtres
  `status != done`, tri par `due`. C'est le « kanban explorable comme une base de données ».
- **Vue Journal** — `vault/Journal.base` : notes journal, colonnes `contexte`, `nature`, `tags`,
  `created_at` ; tri chrono décroissant ; filtrable par tag/contexte.

**Bases vs Dataview** — décision : privilégier **Bases** (plugin cœur Obsidian, pas d'install
tierce, fichiers `.base` YAML). Si la version d'Obsidian embarquée dans le conteneur (ticket
`1787600247613`) ne fournit pas Bases, repli **Dataview** : mêmes vues en
blocs ```` ```dataview ```` dans des notes `.md`. **Coordonner avec le ticket conteneur** pour
savoir quels plugins sont disponibles avant de figer le format. Documenter le choix retenu.

**4. Génération** : un petit module/service (ex. `app/services/kb_schema_notes.py`) écrit ces
fichiers dans le vault. Idempotent (réécriture si le contenu change), atomique, confiné au vault,
commit git best-effort. Peut être déclenché par le même job que le miroir kanban.

### Vérification attendue

- Après génération : `vault/Accueil.md`, `vault/Taxonomie.md`, `vault/Tâches.base` (ou `.md`
  Dataview), `vault/Journal.base` présents.
- La note taxonomie reflète le contenu de `categories.schema.yaml` (changer le YAML → régénérer →
  note à jour).
- Ouverts dans Obsidian (ticket conteneur), la vue Tâches liste les notes `type: task` groupées par
  colonne et la vue Journal liste les notes journal filtrables par tag.

### Notes d'implémentation

_(à compléter à la fermeture)_
