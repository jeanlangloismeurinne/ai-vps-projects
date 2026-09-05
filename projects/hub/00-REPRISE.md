---
id: reprise-hub-pilotage
status: prompt-de-reprise
created: 2026-09-04
updated: 2026-09-05
project: hub
role: >
  Prompt de reprise du chantier « système de pilotage v3 ». Périmètre TRANSVERSE : code dans
  projects/hub/, doctrine dans CONTROL_SYSTEM.md (racine du repo). État : lots A et B LIVRÉS et
  DÉPLOYÉS ; lot C entamé — il reste la roadmap à co-écrire avec l'utilisateur.
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
| **B — Hub** (`projects/hub/app/roadmap.py`) | ✅ livré **et déployé** · `e9ea104` |
| **C — amorçage sur newsletter-summary** | 🟡 entamé · gabarit + consigne 360° écrits, projet témoin remis au format · reste la roadmap à co-écrire |

**Le Hub déployé sert bien le code du lot B**, vérifié en prod et pas sur la seule fin de build :
`/roadmap/hub` et `/roadmap/newsletter-summary` répondent 200 et affichent le bloc « Fichier de
reprise » avec le pointeur en clair et le chemin résolu.

Le refus du classifieur sur `compose-deploy.sh hub` (3 tentatives la session précédente) **n'était
pas permanent** : la même commande, inchangée, est passée du premier coup le 2026-09-05. Re-tester
le chemin nominal avant de dérouler un repli.

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

- [x] Gabarit `00-REPRISE.md` (`CONTROL_SYSTEM.md` §2) — deux éléments seulement marqués
      *load-bearing* (le pointeur, « Reste à faire »), le reste libre, et **aucun bloc « MàJ »**
      dans le gabarit : c'est par là que le fichier gonfle.
- [x] Consigne du 360° (§4) rendue **exécutable** plutôt que décrite. Le biais est contré par un
      **mécanisme, pas une autorisation** : l'axe 0 est réservé au cadre lui-même et il est
      obligatoire ; la seule sortie est de citer un fait qui a éprouvé le cadre. « Tu as le droit
      de remettre le cadre en cause » produisait des axes conformes quand même.
- [x] Projet témoin remis au format : `newsletter-summary/00-REPRISE.md` passé de 8185 à 3205 o
      (−61 %), récit sorti en archive, `DECISIONS.md` #2 extrait. Le Hub déployé le lit.
- [ ] **Roadmap co-écrite avec l'utilisateur** — bloqué sur son choix d'axe, pas sur du code.
- [ ] Inscrite depuis le Hub → « reprends le projet newsletter-summary » → lot exécuté → capacité
      cochée → archivage appliqué.
- **Acceptation** : le cycle a tourné une fois de bout en bout sur un vrai projet, pas en
  dry-run — et il a tourné **contre le Hub déployé**, pas contre un uvicorn local.

**Ce que l'amorçage a déjà appris** (le but du lot : découvrir ce qui manque quand quelqu'un se
sert du système sans l'avoir écrit) :

- **Là où le fichier de reprise doublonnait le `README.md`, c'est le `README.md` qui était
  périmé** — il annonçait `RESEND_API_KEY` / `SENDER_EMAIL`, absents du `.env` réel depuis le
  passage par comms-gateway. La règle « une information, un seul endroit » ne fait pas que réduire
  la taille : le doublon **cache** lequel des deux ment.
- **Une consigne juste peut reposer sur un raisonnement faux et survivre.** « Rebuild, jamais
  restart » était motivé par « le Hub est un Next.js, les variables sont figées dans le bundle » —
  le Hub est en FastAPI/uvicorn et lit son `.env` au runtime. La conclusion tenait (`build: .`
  met `app/` dans l'image), donc personne n'a jamais eu de raison de la tester.
- **L'entrée du 360° peut être quasi vide** : newsletter-summary n'a ni roadmap ni ticket ouvert.
  D'où l'exigence ajoutée au §4 d'**annoncer l'entrée réellement lue** plutôt que de compenser.

---

## 4. Reste à faire / dettes ouvertes

- ⚠️ **Écriture concurrente dans le dépôt** — deux commits (`dd3aa1b`, `0cd7752`) sont apparus
  pendant la session du 2026-09-05, comme la fois précédente. Vraisemblablement la boucle
  autonome. **Ne jamais utiliser `git add -A` / `git add .` ici** : indexer par liste explicite,
  sinon un lot de doc emporte du code non validé.
- **`app/nuit.py:59`** dit « depuis le chantier sur disque » — vocabulaire mort du système v2.
  Non traité : hors du contexte partagé du lot B, et il faut d'abord vérifier si la boucle
  nocturne a sa propre notion de « chantier » avant de renommer.
- **`SESSION.md` reste gitignoré, et c'est volontaire** : `/srv/auto-loop/autoloop.sh` y dépose
  son ordre de nuit. C'est un **homonyme** de l'ordre de sprint supprimé, pas un vestige — le
  retirer ferait committer un ordre de pilotage à chaque nuit (détail : `CONTROL_SYSTEM.md`, en
  tête).

---

## 5. Où démarrer

Le lot C reprend **au choix d'un axe par l'utilisateur** sur newsletter-summary. Le diagnostic 360°
lui a été proposé le 2026-09-05 ; il n'est **pas** à relancer de soi-même (§4). Une fois l'axe
choisi : conversation de raffinement → roadmap `figée` → inscription **depuis le Hub** (c'est ce
geste-là qui reste à éprouver contre le code déployé) → « reprends le projet newsletter-summary à
partir du fichier de reprise ».

Attention en reprenant : la roadmap de newsletter-summary est **le premier vrai fichier
`roadmap/*.md` du système v3**. Les 4 dossiers `roadmap/` existants sont un fourre-tout hérité
(spec, audit, constitution) avec 13 vocabulaires de statut — n'y chercher aucun modèle.
