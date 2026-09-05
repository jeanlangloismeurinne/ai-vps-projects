# Système de pilotage — roadmap · fichier de reprise · lot de conversation

> Instructions pour Claude Code **et** pour l'outil de pilotage du Hub (`projects/hub/`).
> Lire ce fichier au démarrage de toute session de travail sur un projet.

---

## Principe — trois artefacts, pas un de plus

```
ROADMAP (roadmap/{nom}.md)  → CE QU'ON VEUT CONSTRUIRE. Liste ORDONNÉE de capacités, chacune
                              avec son test d'acceptation et sa case à cocher. Co-écrite avec
                              l'utilisateur dans le terminal, puis figée. Porte son avancement.
00-REPRISE.md (racine)      → OÙ ON EN EST. Pointeur vers la roadmap active + ce qu'on a appris
                              en chemin (dettes, gotchas d'implémentation). Format LIBRE.
                              C'est le fichier qu'on relit pour reprendre. Un par projet.
LOT DE CONVERSATION         → CE QU'ON FAIT MAINTENANT. Auto-planifié par l'agent au démarrage,
                              annoncé en UNE ligne. Jamais écrit dans un fichier.
DECISIONS.md                → faits durables, réutilisables ailleurs. Versionné, greppable.
Inbox (feedback-tickets/)   → ce que l'utilisateur remonte. Entrée seulement, pas planification.
Mémoire agent               → cache de rappel, pointeurs. JAMAIS l'unique domicile d'un fait.
```

**La règle qui tient tout** : une information vit à **un seul endroit**. Le fichier de reprise ne
redit jamais ce que le `CLAUDE.md` du projet porte déjà — ces deux fichiers sont le coût
d'ouverture réel de toute session (sur portfolio-tracker : 47 Ko + 75 Ko ≈ **30 000 tokens** avant
d'avoir lu une ligne de code).

**Ce qui a été retiré, et pourquoi** : le sprint, l'ordre de sprint (`SESSION.md`), le ré-armement
et le ticket-comme-unité-de-découpage ont été supprimés le 2026-09-05. Ils n'étaient pas appliqués :
sur 12 projets, **un seul** fichier avec `## Sprints`, **un seul** `SESSION.md` — non suivi par git,
resté figé sur un chantier livré et archivé depuis. Sur la même période, portfolio-tracker a produit
**~90 commits** sans toucher un sprint ni un ticket. Ne pas les réintroduire sous un autre nom.

---

## 1. La roadmap — deux états : brouillon, puis figée

Une roadmap peut **naître** n'importe où : l'utilisateur peut la déposer depuis le Hub, en jetant
une intention brute. Mais elle n'est **jamais implémentable en l'état** — une intention déposée
sans raffinement produit des capacités qu'aucun agent ne peut exécuter.

D'où **deux états, et une vanne entre les deux** :

```
BROUILLON  ── conversation de raffinement (terminal, avec l'utilisateur) ──▶  FIGÉE
créé au Hub          on découpe, on ordonne, on écrit les tests             inscriptible
ou au terminal       d'acceptation, on tranche les ambiguïtés               dans le 00-REPRISE
```

**La vanne est mécanique, pas déclarative.** Une roadmap passe à `figée` quand — et seulement
quand — les trois exigences ci-dessous sont vérifiées, capacité par capacité. C'est l'agent qui
constate le passage à la fin de la conversation de raffinement ; il ne se décrète pas depuis le Hub.

**Tant qu'une roadmap est en brouillon, elle ne peut pas être inscrite comme roadmap active** :
le bouton d'inscription du Hub reste fermé. Un brouillon inscrit serait un « reprends le projet X »
qui lance un agent sur une liste de vœux.

Marqueur, dans le frontmatter de la roadmap :

```yaml
status: brouillon | figée
```

Le mécanisme qui marche n'est pas le format, c'est le triplet **liste ordonnée + test d'acceptation
par item + agent qui planifie lui-même son découpage**. Gabarit minimal :

```markdown
---
status: brouillon | figée
role: >
  Une phrase : ce que ce document décide.
---

# {Titre}

## Principe directeur
{le cadre : ce qui est vrai quoi qu'il arrive, et ce qu'on refuse de faire}

## Capacités (ordre imposé)
### 1. {capacité} · contexte partagé : {fichiers / modèle mental}
- [ ] {ce qu'il faut faire}
- [ ] {…}
- **Acceptation** : {fait observable qui prouve que c'est livré — pas « ça marche »}

### 2. {capacité suivante}
…
```

**Les trois exigences qui font passer un brouillon à `figée`** — ce sont elles, et rien d'autre, qui
définissent « implémentable » :

1. **L'ordre est imposé et justifié.** « UX avant agent avant données », « la doctrine avant le
   code » — sinon on implémente une cible qui bouge encore. L'ordre est une décision, pas une mise
   en page.
2. **Chaque capacité porte un test d'acceptation observable.** Un critère qu'on peut faire virer au
   rouge. Corollaire : le vérifier **avant** le correctif, il doit échouer (test négatif).
3. **Chaque capacité porte sa checklist `- [ ]` / `- [x]`.** Elle est load-bearing pour trois
   mécanismes : l'avancement lu par le Hub, le déclencheur d'archivage (§5), et l'entrée du
   diagnostic 360° (§4). Une roadmap sans cases cochables est illisible pour tout le reste.

---

## 2. Le fichier de reprise — `00-REPRISE.md`

Un par projet, **à la racine du projet**, **format libre**. Sa souplesse est ce qui lui permet de
porter aussi bien une dette de code qu'un jalon fonctionnel : ne pas sur-spécifier son contenu.

Il est **généré à la première utilisation**, jamais par décret sur tous les projets : un fichier de
reprise vide se lit comme un projet à l'arrêt.

**L'activation EST l'inscription** — et elle est réservée aux roadmaps `figée` (§1). Le pointeur
« roadmap active » écrit dans ce fichier est le **seul** endroit où l'information vit. On n'infère jamais la roadmap active en scannant les
`status:` des fichiers de `roadmap/` — c'est un fourre-tout hétérogène (spec, audit, benchmark,
constitution) et aucun vocabulaire de statut n'y est stable.

En tête du fichier, une ligne explicite, toujours présente :

```markdown
> **Roadmap active : `roadmap/{nom}.md`** — capacité en cours : §{n}.
```

ou, quand il n'y en a pas :

```markdown
> **Roadmap active : aucune.**
```

Un chantier assez petit pour tenir **entièrement** dans le fichier de reprise n'a pas besoin d'un
fichier de roadmap séparé : lui en fabriquer un est de la cérémonie. Dans ce cas la liste ordonnée
de capacités vit directement ici, checklist comprise, et la ligne dit `Roadmap active : aucune — le
chantier tient dans ce fichier`.

**Résolution du chemin** (côté Hub comme côté agent) : `00-REPRISE.md` à la racine du projet
d'abord, sinon chercher dans `roadmap/**`. Certains projets historiques ont le leur ailleurs.

---

## 3. Le lot de conversation

L'unité de travail est le **lot de conversation** : ce que l'agent décide de traiter dans la
conversation courante. Il est **auto-planifié**, pas prescrit par un document.

Au démarrage, l'agent lit le fichier de reprise, puis la roadmap active, puis **annonce son lot en
une ligne** avant de commencer. Un lot peut couvrir plusieurs capacités contiguës si elles partagent
le même contexte.

**Critère de découpe : le contexte partagé** — mêmes fichiers, même modèle mental, même contrat de
données. Pas la taille, pas le thème. Exécuter un lot ne doit pas recharger dix fois du contexte qui
se recouvre. C'est pour ça que le gabarit de roadmap fait écrire `· contexte partagé : {quoi}` sur
chaque capacité : c'est ce champ qui rend le lot planifiable sans relire tout le code.

**Déclencheur unique, côté terminal :**

> **« reprends le projet {X} à partir du fichier de reprise »**

Il n'y en a pas d'autre. Toute autre formulation trouvée dans un `CLAUDE.md` est morte : la
corriger, pas l'honorer.

---

## 4. Diagnostic 360° — quand aucune roadmap n'est inscrite

Si le fichier de reprise ne pointe aucune roadmap, l'agent **propose** un diagnostic 360°. Il ne le
lance **jamais** de lui-même : sinon « reprends le projet X » produit une analyse non demandée et
l'utilisateur perd le point de choix.

**Entrée (bornée — s'y tenir) :**
- les **principes fondateurs / la constitution** du projet — le cadre métier ;
- les **roadmaps avec leur avancement** — décidé vs livré vs restant ;
- les **tickets ouverts** — le seul canal où la friction utilisateur remonte non filtrée, et le
  meilleur rapport signal/coût de la liste (~1 Ko).

**Exclu : l'historique des MàJ du fichier de reprise.** C'est de la mémoire d'implémentation
(unités d'arrondi, clefs de supersedage, regex) : indispensable pour reprendre le code, sans valeur
pour décider quoi construire.

**Sortie : N axes candidats, ~5 lignes chacun, puis STOP.** La conversation de raffinement qui
produit la roadmap est une seconde étape, déclenchée par le choix de l'utilisateur.

⚠️ **Biais à contrer explicitement** : nourri de la seule constitution, un agent proposera toujours
des axes *à l'intérieur* du cadre. La consigne doit lui donner le droit de dire que **le cadre
lui-même** est l'axe à revoir, plutôt que de produire une proposition conforme.

---

## 5. Fin de conversation — le protocole d'archivage

**Déclencheur = un fait, pas une impression : l'éviction a lieu quand une capacité de la roadmap est
cochée.** Preuve que le critère subjectif ne tient pas : portfolio-tracker a été allégé le
2026-08-31 (65 Ko sortis vers `00-REPRISE-ARCHIVE.md`) et **quatre jours plus tard son fichier
faisait 75 Ko — plus que son archive**. La consigne d'alléger existait déjà.

Dans l'ordre :

1. **Cocher la capacité livrée** dans la roadmap (ou dans le fichier de reprise s'il la porte).
2. **Rien n'est évincé avant que le durable en soit sorti.** Test : *ce fait changerait-il ce qu'un
   agent fait sur un autre fichier, ou sur un autre projet ?* Oui → `CLAUDE.md` (convention) ou
   `DECISIONS.md` (gotcha). La convention emporte **une** mesure en preuve — c'est ce qui la rend
   crédible plutôt que sentencieuse. Pas le récit complet.
3. ⚠️ **Une dette ne s'archive jamais avec le bloc qui la mentionne.** Mode de panne réel : les
   dettes sont disséminées dans des blocs `MàJ` de capacités **livrées**. Évincer par capacité close
   les emporterait en silence. **Avant d'évincer, tout item ouvert nommé remonte dans « Reste à
   faire »**, section qui ne bouge pas.
4. **Le récit du travail livré** part dans `00-REPRISE-ARCHIVE.md` — jamais chargé, greppable.
5. **L'archive garde une carte** : une ligne dans le fichier de reprise disant où les choses sont
   parties. Sans elle, l'archive devient un fichier que personne ne saura interroger.
6. **Une roadmap dont toutes les capacités sont cochées** sort du chemin chaud → `roadmap/archive/`,
   et la ligne « Roadmap active » repasse à `aucune`.

### Persistance — ce qui n'est pas commité n'existe pas

`infrastructure/compose-deploy.sh` ne commite que les fichiers passés en `-f`. Sur une conversation
**sans déploiement** (doc, cadrage, roadmap), **rien ne commite le fichier de reprise** : la mémoire
du système ne vivrait alors que sur le disque du VPS. Donc, en fin de conversation :

```bash
git add <fichiers de doc touchés> && git commit -m "…" && git push
```

C'est explicitement à faire même — surtout — quand il n'y a rien à déployer.

### Message de clôture

Conclure par une recommandation explicite, jamais implicite :

```
{capacité} : livrée. {état du fichier de reprise}.
Recommandation : {nouvelle conversation | poursuivre ici} — {une ligne de justification}.
```

Arbitrer **contexte chaud réutilisable** (lot suivant petit et dépendant des gotchas fraîchement
découverts → *poursuivre ici*) contre **coût tokens** (lot suivant gros, autonome, état déjà
consigné → *nouvelle conversation*).

---

## 6. Délégation — le plancher

**On ne délègue que si ça coûte moins qu'une exécution inline.** La délégation a une taxe fixe :
re-énoncer le contexte au worker + lire son compte-rendu + revérifier. Elle ne rapporte que sur des
unités **indépendantes, auto-suffisantes, à faible couplage**, lancées en parallèle.

- Le discriminant réel est **l'énonçabilité du critère de succès en trois lignes**, pas le volume de
  sortie attendu. On délègue une **recherche** (« trouve où X est défini »), jamais un **jugement**.
- Travail **couplé** (partage un contrat/schéma) → la taxe dépasse le gain → **inline**.
- Devant un mur de sortie, le réflexe est « quel est le `tail -1` ? », pas « je délègue » : un
  filtre shell bat un sous-agent sur tout ce qui est mécanique.
- Sur un chantier de design/doc/code fortement couplé et à fort jugement, la bonne réponse est
  souvent **zéro délégation**. Ce n'est pas un échec : c'est le plancher qui joue.

### Contrat du sous-agent worker

Lancé via l'outil `Agent` avec `model: sonnet`. Entrée : le périmètre + « implémente et renvoie le
compte-rendu ci-dessous ». Le worker **vérifie son travail** (compile / tests / run) avant de rendre
la main, puis renvoie **exactement** :

```
1. Interprétation : ce que j'ai compris (1-2 phrases)
2. Fichiers modifiés : chemin + une ligne de « pourquoi »
3. Décisions / hypothèses prises
4. Vérification : ce que j'ai lancé (test / compile / run) et le résultat
5. Ambiguïtés que j'ai tranchées seul
```

Ce que ça attrape : ✅ contre-sens / dérive de spec (points 1 et 5). ❌ bugs de correctness.

⚠️ **Les sous-agents écrivent, l'orchestrateur vérifie mécaniquement — jamais sur la seule foi du
compte-rendu.** Mode de panne avéré : du code **jamais exécuté** présenté comme terminé. Un rapport
« vérifié, `node --check` OK » peut être de bonne foi et ne rien prouver (`node --check` est un
no-op sur du JSX avec `import`). Le point 4 n'est un filet que si la commande qu'il décrit exécute
vraiment le code changé.

⚠️ **Un sous-agent ne négocie jamais de permissions.** Le travail à privilège (déploiement, base,
secrets) reste chez l'orchestrateur **dès la répartition**. Si un item délégué se heurte à ce mur,
c'est qu'il n'était pas délégable.

---

## 7. Inbox — ce que l'utilisateur remonte

Le ticket survit **comme inbox uniquement** (widget web, `/feature` Slack → `#feedback`
`C0AUCE6NELT`). L'utilisateur **dépose** un one-liner ; il ne cure pas, ne priorise pas, n'ordonne
pas. L'agent **trie** : trivial → corrige et ferme ; sinon → l'item devient une entrée du prochain
diagnostic 360° ou une capacité de la roadmap active.

Fermeture : `status: open` → `status: closed` **et** ajouter `closed_at: {ISO 8601 UTC}`.

Le ticket n'est **plus** une unité de découpage du travail. Ne pas dériver de tickets depuis une
roadmap : la checklist de la roadmap est la seule liste exhaustive.

---

## 8. Effort / modèles

- Session : **Opus** par défaut.
- Worker délégué : **Sonnet 4.6** (`model: sonnet`). `Haiku` réservé au trivial (libellé, config).
- Effort par défaut (élevé) ; effort maximal réservé aux choix architecturaux.

---

## 9. Déploiement

Si la conversation a produit du code déployable, appliquer **`DEPLOY.md`** : un seul appel
`infrastructure/compose-deploy.sh <app> -m "<msg>" -f "<fichiers>" [-e KEY=VALUE …]`, fallback
sous-agent Sonnet si échec. Ne jamais conclure au succès sur la seule fin du build : c'est la
réponse HTTP qui fait foi.

---

## 10. Résumé des règles

- **Roadmap** : `brouillon` tant qu'elle n'a pas été raffinée au terminal ; `figée` quand chaque
  capacité a un ordre justifié, un test d'acceptation observable et une checklist.
- **Activation = inscription** dans le `00-REPRISE.md`, et **seulement** pour une roadmap `figée`.
  Nulle part ailleurs.
- **Lot de conversation** auto-planifié, découpé par **contexte partagé**, annoncé en une ligne.
- **Déclencheur unique** : « reprends le projet {X} à partir du fichier de reprise ».
- **Pas de roadmap inscrite** → proposer le 360°, sortir N axes, puis **stop**.
- **Archiver quand une capacité est cochée** — jamais sur une impression ; sortir le durable
  d'abord, remonter les dettes ouvertes avant d'évincer.
- **Committer la doc** en fin de conversation même sans déploiement.
- **Déléguer** une recherche, jamais un jugement ; vérifier mécaniquement ce que rend un worker.
- **Ajouter sans retirer est le mode de panne de ce repo** : un lot qui n'a rien supprimé n'est pas
  terminé.
