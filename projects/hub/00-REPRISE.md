---
id: reprise-hub-pilotage
status: prompt-de-reprise
created: 2026-09-04
updated: 2026-09-05
project: hub
role: >
  Prompt de reprise du chantier « système de pilotage v3 ». Périmètre TRANSVERSE : code dans
  projects/hub/, doctrine dans CONTROL_SYSTEM.md (racine du repo). État : lots A et B LIVRÉS le
  2026-09-05 ; reste le lot C (amorçage sur un projet témoin).
---

# Prompt de reprise — système de pilotage v3 (Hub)

> **Roadmap active : aucune — le chantier tient dans ce fichier.**
> Il est entièrement décidé et fait 3 lots ; lui fabriquer un fichier de roadmap serait de la
> cérémonie. Le formalisme roadmap démarre au chantier SUIVANT, une fois le système en place.

> ## 🚦 RÈGLE (à chaque session)
> Actualiser ce fichier en fin de conversation dès qu'un lot est livré, et appliquer l'archivage
> de `CONTROL_SYSTEM.md` §5 — ce fichier est le premier à s'y soumettre.

**Carte de l'archive** : le récit des lots A et B (constat mesuré d'adoption, panne du
frontmatter, panne du sélecteur de statut, inventaire de ce qui a été retiré, vérifications) est
dans **`00-REPRISE-ARCHIVE.md`**. Le seul fait réutilisable ailleurs est en **`DECISIONS.md` #1**.
La doctrine elle-même est dans **`CONTROL_SYSTEM.md`** — ce fichier ne la redit pas.

---

## 1. État

| Lot | État |
|---|---|
| **A — doctrine** (`CONTROL_SYSTEM.md`, purge des `CLAUDE.md`) | ✅ livré · `fde83dc`, `eec8fec` |
| **B — Hub** (`projects/hub/app/roadmap.py`) | ✅ livré · `907c00d` + lot B · ⚠️ **déploiement à faire** |
| **C — amorçage sur un projet témoin** | ⬜ à faire — c'est ici qu'on reprend |

⚠️ **Le conteneur `homepage` sert encore l'ancien code.** `docker-compose.yml` fait `build: .`,
donc `app/` est **dans l'image** (seul `projects/` est bind-monté) : sans rebuild, rien de ce qui
suit n'existe en prod. `compose-deploy.sh` a été **refusé par le classifieur de permissions à
trois reprises** (§4). À lancer par l'utilisateur, tel quel :

```
! infrastructure/compose-deploy.sh hub -m "Hub lot B — le fichier de reprise pilote" -f "projects/hub/app/roadmap.py projects/hub/checks/check_reprise_inscription.py"
```

---

## 2. Ce que le Hub sait faire depuis le lot B

- **Affiche le fichier de reprise** en tête de `/roadmap/{projet}` : le pointeur « Roadmap
  active » en clair, le chemin résolu (racine → `roadmap/**`), et `/roadmap/{projet}/reprise`
  pour le lire en entier. **Lecture seule** : il s'actualise au terminal.
- **Inscrit une roadmap** (`POST …/inscrire`) — c'est l'unique endroit où le Hub écrit hors de
  `roadmap/`, et il n'y touche **qu'une ligne**. Vanne re-vérifiée **côté serveur** : un bouton
  désactivé en HTML n'empêche personne de poster l'URL.
- **Crée une roadmap en `brouillon`** avec le gabarit de `CONTROL_SYSTEM.md` §1. `figée` ne se
  décrète pas depuis le Hub : ça se constate au terminal, capacité par capacité.
- **Lit l'avancement dans la checklist** (`- [x]` / `- [ ]`), seule mesure d'état qui existe.
- **Ne réécrit jamais un statut qu'il ne connaît pas** — option « inchangé » d'office.

Deux checks gardent tout ça, à lancer avant de retoucher `roadmap.py` :

```
python3 projects/hub/checks/check_frontmatter_preserved.py    # 46 documents
python3 projects/hub/checks/check_reprise_inscription.py      # 5 résolutions + 4 inscriptions
```

---

## 3. Lot C — amorçage · contexte partagé : un projet témoin

- [ ] Gabarit `00-REPRISE.md` + consigne du 360° (`CONTROL_SYSTEM.md` §4) rédigée pour être lue
      par l'agent — avec le biais à contrer explicitement : nourri de la seule constitution, un
      agent propose toujours des axes *à l'intérieur* du cadre ; lui donner le droit de dire que
      **le cadre lui-même** est l'axe à revoir.
- [ ] Amorçage sur **newsletter-summary** (tranché le 2026-09-05 : il a un `00-REPRISE.md` et un
      backlog vivant — digest HTML, Option A en repli — donc une vraie roadmap à co-écrire, alors
      que comms-gateway est bloqué sur du hors-code : domaine Resend, app Slack, téléphone).
- [ ] Vérifier le cycle complet : roadmap co-écrite → inscrite depuis le Hub → « reprends le
      projet X » → lot exécuté → capacité cochée → archivage appliqué.
- **Acceptation** : le cycle a tourné une fois de bout en bout sur un vrai projet, pas en
  dry-run — et il a tourné **contre le Hub déployé**, pas contre un uvicorn local.

**Pré-requis** : le déploiement du §1. Sans lui, l'étape « inscrite depuis le Hub » testerait
l'ancien code, celui qui détruit le frontmatter.

---

## 4. Reste à faire / dettes ouvertes

- ⚠️ **Déploiement du Hub non fait** — voir §1. Le classifieur de permissions refuse
  `compose-deploy.sh hub` (3 tentatives, formulations différentes) ; c'est un mur d'outillage,
  pas un problème de code.
- ⚠️ **Écriture concurrente dans le dépôt** — deux commits (`dd3aa1b`, `0cd7752`) sont apparus
  pendant la session du 2026-09-05, comme la fois précédente. Vraisemblablement la boucle
  autonome. **Ne jamais utiliser `git add -A` / `git add .` ici** : indexer par liste explicite,
  sinon un lot de doc emporte du code non validé.
- **`app/nuit.py:59`** dit « depuis le chantier sur disque » — vocabulaire mort du système v2.
  Non traité : hors du contexte partagé du lot B, et il faut d'abord vérifier si la boucle
  nocturne a sa propre notion de « chantier » avant de renommer.
- **`_roadmap_dir()` fait un `mkdir` à chaque visite** : ouvrir `/roadmap/{projet}` crée un
  dossier `roadmap/` vide dans les 9 projets qui n'en ont pas. Bénin, jamais nettoyé.
- **`SESSION.md` reste gitignoré, et c'est volontaire** : `/srv/auto-loop/autoloop.sh` y dépose
  son ordre de nuit. C'est un **homonyme** de l'ordre de sprint supprimé, pas un vestige — le
  retirer ferait committer un ordre de pilotage à chaque nuit (détail : `CONTROL_SYSTEM.md`, en
  tête).

---

## 5. Où démarrer

Lancer le déploiement du §1, vérifier la page `/roadmap/hub` en prod, puis **lot C** sur
**newsletter-summary**. C'est le premier lot qui ne touche presque pas de code : il produit un
gabarit, une consigne, et fait tourner le cycle en vrai. Son enjeu est de découvrir ce qui manque
au système quand un utilisateur s'en sert sans l'avoir écrit.
