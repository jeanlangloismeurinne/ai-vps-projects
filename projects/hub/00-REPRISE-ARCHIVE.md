---
id: reprise-hub-archive
status: archive
project: hub
role: >
  Récit du travail livré sur le chantier « système de pilotage v3 ». Jamais chargé au démarrage :
  greppable seulement. Ce qui est encore actionnable vit dans 00-REPRISE.md.
---

# Archive — système de pilotage v3 (Hub)

## Lot A — doctrine (livré le 2026-09-05, `fde83dc` + `eec8fec`)

`CONTROL_SYSTEM.md` réécrit (323 → 301 lignes), les 4 `CLAUDE.md` purgés,
`projects/assistant-ia/SESSION.md` supprimé. Solde **262 ajoutées / 277 supprimées** — le test
d'acceptation commun (« le lot retire autant qu'il ajoute ») est satisfait.

Deux exceptions assumées, documentées à l'époque :
- `CONTROL_SYSTEM.md` cite encore « ordre de sprint » et `SESSION.md` dans un paragraphe *Ce qui
  a été retiré, et pourquoi*. Sans cette épitaphe chiffrée, un agent futur réintroduit le sprint
  en croyant innover.
- `app/roadmap.py` portait 11 occurrences restantes — c'était le lot B, par construction.

### Le constat qui a déclenché le chantier (mesuré)

`CONTROL_SYSTEM.md` décrivait un système que personne n'appliquait.

| Artefact prescrit | Adoption réelle (12 projets) |
|---|---|
| chantier avec `## Sprints` | **1 fichier** : `assistant-ia/roadmap/agent-intention-et-capture-kb.md` |
| `SESSION.md` | **1 fichier** — non suivi par git, figé sur `Sprint 3` d'un chantier livré, `status: done` et archivé (ticket `1787600247615` `closed`). Le ré-armement n'a jamais tourné une seule fois. |
| ticket comme unité de planification | portfolio-tracker : 30 tickets, 6 ouverts, dernière fermeture 2026-07-14, 3/30 avec `milestone:` |

Sur la même période, portfolio-tracker a produit **~90 commits** (lots 7/8/9, UX-1/2/3, RVMD
F1→F9) **sans toucher un seul ticket, sprint ou `SESSION.md`**.

Le modèle retenu vient de ce que portfolio-tracker utilise réellement :
`00-principe-directeur-v2.md` → `01-spec-v2-unifiee.md` **§18** (liste ordonnée de 9 capacités +
ordre imposé + test d'acceptation par item) → `00-REPRISE.md`. Le mécanisme qui marche n'est pas
le format, c'est **liste ordonnée + test d'acceptation + agent qui planifie son découpage**.

### Angle mort du lot A

Le test d'acceptation ne couvrait que `.md`/`.py`/`.html` : deux occurrences vivaient dans
`.gitignore` et `projects/hub/docker-compose.yml` (corrigées par `eec8fec`). **Leçon** : greper
toutes extensions, pas la liste qu'on croit exhaustive.

---

## Lot B — le Hub (livré le 2026-09-05, `907c00d` + lot B)

### §8 — le Hub détruisait le frontmatter à la sauvegarde (`907c00d`)

**Mesuré** en rejouant le parseur sur `portfolio-tracker/roadmap/01-spec-v2-unifiee.md` :

```
frontmatter : 15 lignes avant  →  7 lignes après UNE sauvegarde
```

Trois dégâts, tous silencieux (pas d'erreur, redirection `flash=saved`) :
- les scalaires de bloc YAML (`role: >`, `downstream: >`) perdaient tout leur contenu — le
  frontmatter était reconstruit à plat en `clé: valeur` ;
- une ligne de continuation contenant un `: ` était promue en clef parasite (constaté :
  `Le découpage en tickets suit le principe de développement: pour chaque capacité,`) ;
- le corps restait intact, donc le diff git ressemblait à une édition légitime.

**Correctif** : le Hub n'édite plus que le corps ; le frontmatter est repris octet pour octet et
seule la ligne `status:` de premier niveau y est substituée. Gardé par
`checks/check_frontmatter_preserved.py`, **rouge avant / vert après** — 31 des 46 documents à
frontmatter du repo étaient abîmés, alors que le cadrage n'en avait mesuré qu'un. Le check porte
une seconde garantie, la validité YAML, qui a révélé deux `00-REPRISE.md` déjà invalides
(comms-gateway, newsletter-summary), corrigés au passage.

### La même panne, une couche plus haut : le sélecteur de statut

Le `<select>` ne connaissait que 5 statuts (`draft`, `spec-ready`, `tickets-created`, `en-cours`,
`done`) alors que **13 vocabulaires distincts** vivent dans les `roadmap/` du repo
(`carte-de-provenance` ×9, `derivation`, `cadre-fondateur`, `to-refine`…). Ouvrir puis
sauvegarder un document de portfolio-tracker le repassait donc silencieusement en `draft` :
même classe de destruction que le §8, un étage plus haut. Corrigé par une option « inchangé »
sélectionnée d'office pour tout statut hors vocabulaire — et le statut n'est jamais réécrit.

### Ce que le lot B a retiré

- `_parse_sprints` + `_generate_sprint_order` (−46 lignes), route `/sprint-order`, écriture de
  `SESSION.md`, bloc UI des sprints ;
- `_create_item` + `_page_new` + routes `/new` (−88 lignes) : le ticket n'est plus une unité de
  découpage, et une capacité s'écrit dans la roadmap, pas via un formulaire ;
- la hiérarchie axe → chantiers de `_page_list`, qui s'appuyait sur une filiation `roadmap:`
  que **zéro fichier du repo ne porte** (vérifié sur 15 documents) : elle mettait en scène une
  structure vide ;
- le compteur de tickets des cartes, remplacé par l'avancement lu dans la checklist ;
- le défaut `type: chantier`, qui faisait passer 15 documents hétérogènes (spec, audit,
  benchmark, constitution) pour des chantiers.

Solde `roadmap.py` : **+307 / −305**.

### Vérification

Le routeur a été servi par uvicorn contre une **copie** de `projects/`, et le cycle exercé en
HTTP réel : création → `status: brouillon` → inscription refusée en **400** sur un brouillon
(POST direct, bouton contourné) → passage en `figée` → inscription → pointeur unique dans le
`00-REPRISE.md`, **306 lignes avant / 306 après**, aucune autre ligne modifiée → double
inscription idempotente → badge « ★ inscrite » sur la liste. Plus les cas limites : projet sans
fichier de reprise (création à la première inscription), résolution `roadmap/**` sur
portfolio-tracker, 404 sur les routes supprimées.

**Deux faux positifs traversés en cours de route**, tous deux du même genre — une assertion qui
passe parce que la requête n'a jamais eu lieu :
1. un `curl` envoyant `status=figée` en UTF-8 brut (un navigateur pourcent-encode) : le statut ne
   changeait pas, et le code semblait fautif ;
2. un serveur arrêté par un `pkill` dans la même commande composée : `HTTP 000` et « fichier
   identique octet pour octet » côte à côte.

Le durable qui en est sorti est en `DECISIONS.md` #1 (FastAPI : `Form` vide = 422).
