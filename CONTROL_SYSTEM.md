# Système de contrôle — Chantiers · Sprints · Tickets

> Instructions pour Claude Code **et** l'outil de pilotage du Hub (`projects/hub/`).
> Lire ce fichier au démarrage de toute session de travail sur un projet.

---

## Principe — un seul document utilisateur, deux vannes indépendantes

L'erreur à ne jamais refaire : mélanger les artefacts destinés à **l'utilisateur** et ceux
destinés à **l'orchestrateur**. Ils n'ont pas le même public.

```
CHANTIER (doc vivant)  → UTILISATEUR : direction + décisions + statut. Le SEUL qu'il lit.
SPRINT                 → regroupement nommé DANS le chantier, segmenté par contexte partagé.
                         C'est l'unité que l'utilisateur choisit d'exécuter en priorité.
TICKET                 → outil ORCHESTRATEUR ↔ WORKER. Décomposition d'un sprint. L'utilisateur
                         ne le cure jamais — sauf l'inbox (un bug/idée qu'il remonte).
ORDRE DE SPRINT        → document de passage Hub → Claude Code. Généré par le Hub, JETABLE,
                         écrasé à chaque génération. Déclencheur, pas tableau de bord.
DECISIONS.md           → faits durables (le « pourquoi » d'une décision + les gotchas). Système de
                         référence, versionné, greppable.
Mémoire agent          → cache de rappel, pointeurs. PAS un système de référence.
```

**Conséquence pratique** : l'utilisateur pointe un **chantier** et choisit un **sprint** par son
nom. Il ne lit pas `TICKETS.md`, ne sélectionne pas de numéros de tickets, ne peut pas « oublier »
un ticket : la checklist du sprint (dans le chantier) est la liste exhaustive, et c'est le même
document qu'il a validé. Le lien chantier↔ticket est porté par **l'orchestrateur**, pas par lui.

---

## Les deux vannes (indépendantes, pas une séquence)

« Roadmap » et « tickets » répondent à deux questions distinctes. Une demande peut ouvrir l'une
sans l'autre.

- **Vanne direction** — « est-ce que ça engage le jugement de l'utilisateur ? » (ambiguïté, choix
  structurant, sécurité / données sensibles). Si oui → écrire un **chantier** court et dense en
  décisions, que l'utilisateur amende/valide. Sinon → sauter cette vanne.
- **Vanne délégation** — « est-ce assez gros pour que déléguer économise le contexte d'Opus ? »
  Si oui → décomposer en sprints + tickets. Sinon → Opus exécute inline.

**Trois vitesses** qui en découlent :

| Vitesse | Vanne direction | Vanne délégation | Qui fait |
|---|---|---|---|
| **Trivial** (bug d'une ligne, libellé) | fermée | fermée | Opus corrige direct, 1 ligne de trace. Si c'est déjà un ticket d'inbox → le fermer avec une note. |
| **Moyen** (non-ambigu, mais plusieurs morceaux) | fermée | ouverte | décomposer + exécuter, sans chantier |
| **Complexe** (ambigu / structurant / sécurité) | ouverte | ouverte | chantier → validation → sprints → exécution |

---

## Segmentation des sprints — par contexte partagé

**Un sprint regroupe le travail qui partage le même contexte** (mêmes fichiers, même modèle mental,
même contrat de données). Le critère de découpe n'est pas « la taille » ni « le thème » : c'est le
**contexte que le modèle doit charger**. Exécuter un sprint ne doit pas recharger dix fois du
contexte qui se recouvre.

Exemple (chantier kb-visualisation, 5 tickets → 3 sprints) :
- *Substrat* (contexte : écriture du vault, contrat frontmatter) = miroir kanban→vault + notes-schéma.
- *Viewer* (contexte : Docker / Traefik / KasmVNC) = conteneur Obsidian + Sablier.
- *Finition* (contexte : doc / UI) = README + landing.

---

## Le plancher de délégation

**On ne délègue un item que si ça coûte moins qu'une exécution inline par Opus.** La délégation a
une taxe fixe : re-énoncer le contexte au worker + lire son compte-rendu + revérifier. Elle ne
rapporte que sur des unités **indépendantes, auto-suffisantes, à faible couplage**, lancées en
parallèle.

- Travail **couplé** (partage un contrat/schéma) → la taxe dépasse le gain → **Opus inline**.
- On délègue au plus à la granularité du **sprint** (un worker qui tient le contexte partagé du
  sprint), **jamais par ticket** à l'intérieur d'un sprint couplé.
- Si un chantier est du design/doc/code fortement couplé et à fort jugement, la bonne réponse est
  souvent **zéro délégation**. Ce n'est pas un échec du système : c'est le plancher qui joue.

---

## Cycle de vie d'un chantier

1. **Demande** (utilisateur, direct ou via l'inbox).
2. **Vanne direction** : si elle s'ouvre, Opus écrit le chantier (court, dense en décisions ;
   contrat exhaustif en annexe, pas dans la surface de validation).
3. **Validation** : l'utilisateur amende/valide le chantier. Un seul document.
4. **Vanne délégation** : Opus décompose en **sprints nommés dans le chantier** (segmentés par
   contexte partagé), et marque, sprint par sprint, ce qui est délégable (test du plancher). Les
   tickets sous-jacents sont dérivés ici.
5. **Exécution** : dans le Hub, l'utilisateur choisit **un sprint** par son nom → le Hub génère
   l'**ordre de sprint** (le Hub ne peut pas lancer Claude Code lui-même). Dans Claude Code,
   l'utilisateur déclenche ; Opus lit le chantier + l'ordre, exécute (inline ou workers selon le
   plancher), et met à jour le **statut dans le chantier**. En fin de sprint, Opus **ré-arme
   `SESSION.md` sur le sprint suivant** : les sprints s'enchaînent sans repasser par le Hub.
6. **Clôture** : ranger l'info durable (section dédiée ci-dessous).

---

## Passage Hub → Claude Code — l'ordre de sprint

Le Hub est une UI de pilotage ; il **ne peut pas exécuter une consigne dans Claude Code**. Le seul
pont est un **document** que le Hub génère et que l'utilisateur déclenche dans le terminal.

Cet **ordre de sprint** (`SESSION.md` à la racine du projet) est **mince, prospectif, jetable** :
il est écrasé à chaque génération, ne contient **aucun résumé accumulé**. Son rôle est de déclencher
l'exécution d'**un** sprint. Contenu :

```markdown
# Ordre de sprint — {projet}
Chantier : roadmap/{nom}.md
Sprint   : {nom du sprint}

## Items
- [ ] {item} → #{ticket_id si délégué}
- [ ] …

## Pré-actions utilisateur (si besoin)
- {action manuelle : inviter un bot, provisionner une variable d'env…}
```

Déclencheur côté terminal : **« exécute le sprint en cours pour {projet} »** → Opus lit `SESSION.md`
**et** le chantier pointé (source de vérité), exécute, coche la checklist **dans le chantier**.
Le statut ne vit **jamais** dans `SESSION.md` (qui sera écrasé) — toujours dans le chantier.

### Ré-armement automatique — un seul passage par le Hub

L'utilisateur ne clique « Générer l'ordre » **qu'une fois**, au démarrage du chantier. Ensuite,
**c'est Opus qui réécrit `SESSION.md` en fin de sprint**, sans repasser par le Hub. Règle par
défaut, appliquée à la clôture de **chaque** sprint :

1. Cocher les items dans le chantier (source de vérité).
2. Déterminer le **prochain sprint non terminé** du chantier = le premier `###` de la section
   `## Sprints` qui garde au moins un `- [ ]`.
3. **Réécrire `SESSION.md`** (même gabarit, écrasement complet) sur ce sprint.
   - Sprint courant **incomplet** (items abandonnés/bloqués) → `SESSION.md` reste sur **le sprint
     courant**, avec les seuls items restants. Le pointeur ne saute pas un travail non fait.
   - **Plus aucun sprint en attente** → écrire un `SESSION.md` de fin (`Sprint : — (chantier
     terminé)`, aucun item) pour qu'un « exécute le sprint en cours » lancé par réflexe ne
     re-déclenche pas le dernier sprint ; puis appliquer la clôture de chantier (`status: done`,
     `roadmap/archive/`).
4. **Clore la session par ce message** (format fixe) :

```
Sprint {N} — {nom} : terminé. SESSION.md est actualisé pour lancer le Sprint {N+1} — {nom}.
Recommandation : {nouvelle conversation | poursuivre ici} — {une ligne de justification}.
```

La recommandation n'est jamais implicite : arbitrer **contexte chaud réutilisable** (prochain
sprint petit et dépendant des gotchas fraîchement découverts → *poursuivre ici*) contre **coût
tokens** (sprint suivant gros, autonome, état déjà consigné dans le chantier → *nouvelle
conversation*). Le Hub reste le point d'entrée pour **changer** de sprint ou de chantier hors
séquence : y retourner écrase le `SESSION.md` ré-armé, ce qui est le comportement voulu.

---

## Modèle d'exécution — Opus orchestrateur + workers Sonnet

La session tourne sur **Opus**. Il n'implémente pas tout lui-même :

```
Opus (orchestrateur)
  ├─ lit le chantier + le sprint choisi
  ├─ item COUPLÉ / à jugement → Opus l'implémente lui-même
  └─ item DÉLÉGABLE (plancher OK) → worker Sonnet 4.6
                                      └─ implémente + COMPTE-RENDU structuré
       Opus vérifie le compte-rendu contre la spec du sprint :
         · conforme      → coche l'item, avance le statut
         · écart détecté → lit le code de CET item uniquement, corrige, coche
```

But de la délégation (on est en abonnement, pas facturé au token) : préserver le contexte/quota
d'Opus et paralléliser — **uniquement quand le plancher est franchi**.

---

## Contrat du sous-agent worker

Lancé via l'outil `Agent` avec `model: sonnet`. Accès outils complet. Entrée : le périmètre du
sprint (ou de l'item) + « implémente et renvoie le compte-rendu ci-dessous ». Le worker **vérifie
son travail** (compile / tests / run) avant de rendre la main, puis renvoie **exactement** :

```
1. Interprétation : ce que j'ai compris (1-2 phrases)
2. Fichiers modifiés : chemin + une ligne de « pourquoi »
3. Décisions / hypothèses prises
4. Vérification : ce que j'ai lancé (test / compile / run) et le résultat
5. Ambiguïtés que j'ai tranchées seul
```

Ce que ça attrape : ✅ contre-sens / dérive de spec (points 1 et 5). ❌ bugs de correctness — le
filet reste le point 4 ; s'il est absent ou faible, Opus lit le code de l'item.

---

## Format du chantier (doc vivant) — `roadmap/{nom}.md`

Le chantier est le **tableau de bord** : direction + décisions + statut, tout au même endroit.

```markdown
---
status: draft | spec-ready | en-cours | done
milestone: {nom}
---

# Chantier — {titre}

## Direction (utilisateur)
{ce que veut l'utilisateur, verbatim reformulé}

## Décisions
{ce qui est tranché ET ce qui reste à trancher — la surface de validation, courte et dense}

## Sprints
### Sprint 1 — {nom} · contexte partagé : {quoi}
- [ ] {item} → #{ticket_id si délégué}
- [x] {item fait} · note : {compte-rendu 1 ligne}
### Sprint 2 — {nom} · contexte partagé : {quoi}
- [ ] …

## Annexe — contrats / specs détaillés
{le contrat exhaustif vit ICI, pas dans la surface de validation}
```

La checklist des sprints **est** le statut. Opus la coche au fil de l'exécution. L'utilisateur ne
regarde que ce document pour savoir où on en est.

---

## Format des tickets (outil orchestrateur ↔ worker) — `feedback-tickets/`

Le ticket n'est plus un artefact utilisateur (sauf inbox). Il porte le **delta actionnable + les
critères d'acceptation + un pointeur vers le sprint/annexe** — jamais la re-argumentation des
décisions (elles sont dans le chantier).

Frontmatter :
```yaml
id: {timestamp_ms}
type: bug | feature | suggestion | error
status: open | blocked | closed
priority: high | medium | low
date: {ISO 8601}
project: {nom_projet}
milestone: {nom du chantier}          # relie le ticket à son chantier
closed_at: {ISO 8601 UTC}             # à la fermeture
```

Corps : `## {label}` · `### Description` (delta + acceptation + pointeur) · `### Notes
d'implémentation` (compte-rendu vérifié ajouté à la clôture). Un contrat lourd partagé par
plusieurs tickets → **fichier spec unique** `{id}-spec-*.md` référencé, jamais recopié.

---

## Inbox — bugs / idées remontés par l'utilisateur

Seul cas où l'utilisateur touche un ticket : il **dépose** un one-liner (widget web, `/feature`
Slack). Il ne cure pas, ne priorise pas, n'ordonne pas. L'orchestrateur **trie** : trivial → corrige
et ferme ; sinon → rattache à un chantier (existant ou nouveau) via `milestone`.

---

## Clôture — ranger l'info durable (sinon elle fuit)

À la fin d'un sprint ou d'un chantier :

1. **Gotchas → `DECISIONS.md`** (racine du projet, versionné) : tout fait durable et réutilisable
   (une API qui refuse un format, un modèle déprécié, un « pourquoi » d'architecture). C'est le
   système de référence — pas la mémoire agent (qui n'est qu'un **cache** et ne doit jamais être
   l'unique domicile d'un fait porteur).
2. **Statut** : cocher les items dans le chantier ; passer `status: done` quand tout est clos.
   Puis **ré-armer `SESSION.md`** sur le sprint suivant et rendre la main avec le message de fin
   de sprint (voir § *Ré-armement automatique*) — pas de retour au Hub entre deux sprints.
3. **Archivage** : un chantier terminé sort du chemin chaud → `roadmap/archive/` (git en garde
   l'historique). On ne re-lit pas à chaque session des chantiers finis.
4. **Mémoire agent** : y écrire au plus un **pointeur** (« gotchas DeepInfra → DECISIONS.md »).

> Le `SESSION.md` (ordre de sprint) n'accumule **rien** : il est écrasé à la génération suivante.
> Le statut vit dans le chantier ; l'historique vit dans git + `DECISIONS.md`. Le chemin chaud
> d'une session = chantiers **actifs** + tickets **ouverts** seulement.

---

## Déploiement

Si la session a produit du code déployable, appliquer **`DEPLOY.md`** : un seul appel
`infrastructure/deploy.sh <app> -m "<msg>" -f "<fichiers>" [-e KEY=VALUE …]` (option 1
déterministe), fallback sous-agent Sonnet si échec. Garde les logs de build hors du contexte Opus.

---

## Effort / modèles

- Session : **Opus** par défaut.
- Worker délégué : **Sonnet 4.6** (`model: sonnet`). `Haiku` réservé au trivial (libellé, config).
- Ticket complexe traité par Opus : effort par défaut (élevé) ; effort maximal réservé aux choix
  architecturaux.

---

## Règles de décision (résumé)

- **Ouvrir la vanne direction** : ambiguïté, choix structurant, sécurité → chantier à valider.
- **Ouvrir la vanne délégation** : plusieurs morceaux ET le plancher est franchi.
- **Segmenter les sprints** par **contexte partagé**, pas par taille ni thème.
- **Déléguer** seulement si ça coûte **moins** qu'inline ; au plus à la granularité du sprint.
- **Vérifier avant de fermer** : tests / run pour la correctness ; compte-rendu pour le contre-sens.
- **Fin de sprint** : ré-armer `SESSION.md` sur le sprint suivant + message de fin avec la
  recommandation *nouvelle conversation vs poursuivre ici*.
- **À la clôture** : gotcha → `DECISIONS.md`, chantier fini → `archive/`, mémoire = pointeur.
