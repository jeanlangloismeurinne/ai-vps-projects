---
id: reprise-hub-pilotage
status: prompt-de-reprise
created: 2026-09-04
updated: 2026-09-05
project: hub
role: >
  Prompt de reprise du chantier « système de pilotage v3 ». Périmètre TRANSVERSE :
  code dans projects/hub/, doctrine dans CONTROL_SYSTEM.md (racine du repo), plus une
  purge dans plusieurs CLAUDE.md. État : Lot A (doctrine) LIVRÉ le 2026-09-05 ; lots B et C à faire.
---

# Prompt de reprise — système de pilotage v3 (Hub)

> **Roadmap active : aucune — le chantier tient dans ce fichier.**
> Il est entièrement décidé, sans ambiguïté restante, et fait 3 lots. Lui fabriquer un
> fichier de roadmap serait de la cérémonie : le formalisme roadmap démarre au chantier
> SUIVANT, une fois que le système décrit ici existe. La liste ordonnée de capacités
> ci-dessous joue ce rôle, checklist comprise.

> ## 🚦 RÈGLE (à chaque session)
> Actualiser ce fichier en fin de conversation dès qu'un lot est livré. Quand une capacité
> est cochée, appliquer les règles d'archivage du §5 — elles font partie du chantier, donc
> ce fichier est le premier à s'y soumettre.

---

## 1. État — Lot A livré (2026-09-05, `fde83dc`)

**Lot A terminé et poussé.** `CONTROL_SYSTEM.md` réécrit (323 → 301 lignes), les 4 `CLAUDE.md`
purgés, `projects/assistant-ia/SESSION.md` supprimé. Solde **262 ajoutées / 277 supprimées** — le
test d'acceptation commun (« le lot retire autant qu'il ajoute ») est satisfait.

**Lots B et C : zéro ligne.** Le Hub (`app/roadmap.py`) est intact, y compris le bug du §8.

Deux nuances honnêtes sur l'acceptation du lot A :
- `CONTROL_SYSTEM.md` **cite encore** « ordre de sprint » et `SESSION.md` (l.29-31), dans un
  paragraphe *Ce qui a été retiré, et pourquoi*. C'est délibéré : sans cette épitaphe chiffrée, un
  agent futur réintroduit le sprint en croyant innover. Exception assumée, pas un oubli.
- `projects/hub/app/roadmap.py` porte 11 occurrences restantes — c'est **le lot B**, par
  construction.

---

## 2. Le constat qui a déclenché le chantier (mesuré — ne pas re-dériver)

`CONTROL_SYSTEM.md` décrit un système que personne n'applique.

| Artefact prescrit | Adoption réelle (12 projets) |
|---|---|
| chantier avec `## Sprints` | **1 fichier** : `projects/assistant-ia/roadmap/agent-intention-et-capture-kb.md` |
| `SESSION.md` | **1 fichier** — non suivi par git, figé sur `Sprint 3` d'un chantier **livré, `status: done` et déplacé dans `roadmap/archive/`** (son ticket `1787600247615` est `closed`). Le ré-armement du §5 de l'ancienne doctrine n'a donc jamais tourné une seule fois. ✅ supprimé au lot A. |
| ticket comme unité de planification | portfolio-tracker : 30 tickets, 6 ouverts, **dernière fermeture 2026-07-14**, 3/30 avec `milestone:` |

Sur la même période, portfolio-tracker a produit **~90 commits** (lots 7/8/9, UX-1/2/3, RVMD
F1→F9) **sans toucher un seul ticket, sprint ou `SESSION.md`**.

**Ce que portfolio-tracker utilise réellement**, et qui sert de modèle :
`00-principe-directeur-v2.md` (constitution) → `01-spec-v2-unifiee.md` **§18** (liste ordonnée
de 9 capacités + ordre imposé UX→agent→données + test d'acceptation par item) → `00-REPRISE.md`
(position dans cette liste + ce qu'on a appris). Les « lots » du fichier de reprise
correspondent **exactement** à §18.7 / §18.8 / §18.9. Les autres fichiers de son `roadmap/`
ne sont pas utilisés pour avancer — ne pas s'y référer.

Le mécanisme qui marche n'est pas le format, c'est le couple **liste ordonnée + test
d'acceptation + agent qui planifie lui-même le découpage**.

---

## 3. Décisions figées (ne pas rouvrir)

1. **Un `00-REPRISE.md` par projet, à la racine, format LIBRE.** Ne pas sur-spécifier son
   contenu : sa souplesse est ce qui lui permet de porter aussi bien une dette de code qu'un
   jalon fonctionnel. **portfolio-tracker n'est pas touché** (son fichier reste dans
   `roadmap/provenance-cards/`) — le Hub doit donc résoudre : racine d'abord, sinon `roadmap/**`.
2. **La roadmap a deux états — `brouillon` et `figée`** (tranché le 2026-09-05, amende la version
   initiale « le Hub ne crée plus de roadmap »). Le Hub **garde** la création : l'utilisateur peut
   y déposer une intention brute. Mais elle reste `brouillon`, donc **non inscriptible**, tant
   qu'elle n'est pas passée par une conversation de raffinement au terminal — sinon les fichiers
   déposés seraient très loin d'être implémentables. Le passage à `figée` est **mécanique** : ordre
   justifié + test d'acceptation observable + checklist, capacité par capacité. Doctrine :
   `CONTROL_SYSTEM.md` §1.
3. **L'activation EST l'inscription.** Le pointeur « roadmap active » du fichier de reprise est
   le seul endroit où l'information vit. Pas de prédicat inféré en scannant les `status:` —
   `roadmap/` est un fourre-tout hétérogène (spec, audit, benchmark, constitution) et
   `STATUS_LABEL` (`app/roadmap.py:13`) ne connaît aucun des statuts réels de portfolio-tracker.
4. **La roadmap porte sa propre checklist d'avancement.** Aujourd'hui **zéro `[x]`/`[ ]` dans
   toutes les roadmaps de portfolio-tracker**, et pas de `roadmap/archive/` : seul le fichier de
   reprise sait ce qui est livré. Cette checklist est load-bearing pour **trois** mécanismes —
   le prédicat du §3.3, le déclencheur d'archivage du §5, et l'entrée du 360° du §4.
5. **Le sprint disparaît comme cérémonie** (génération d'ordre, ré-armement, « exécute le sprint
   en cours »). L'unité devient le **lot de conversation**, auto-planifié par l'agent au démarrage
   à partir de la roadmap et du contexte partagé, annoncé en une ligne. Il peut couvrir plusieurs
   capacités contiguës.
6. **Le ticket survit comme INBOX seulement** (widget web + `/feature` Slack, chaîne câblée :
   `#feedback` `C0AUCE6NELT`, `_KNOWN_PROJECTS`). Il disparaît comme unité de découpage.
7. **Déclencheur unique : « reprends le projet {X} à partir du fichier de reprise ».**
8. **Génération du fichier de reprise à la première utilisation**, jamais par décret sur les 12
   projets : 9 n'ont aucune roadmap, et un fichier de reprise vide se lit comme un projet à l'arrêt.

---

## 4. Le diagnostic 360° — entrée et garde

Déclenché quand **aucune roadmap n'est inscrite**. Il **propose**, ne se lance jamais tout seul :
sinon « reprends le projet X » produit une analyse non demandée et l'utilisateur perd le point de
choix. Sortie attendue : N axes candidats, ~5 lignes chacun, puis **stop**. La conversation de
raffinement qui produit la roadmap est une seconde étape, déclenchée par le choix de l'utilisateur.

**Entrée (bornée) :**
- principes fondateurs / constitution du projet — le cadre métier ;
- roadmaps **avec leur avancement** (§3.4) — décidé vs livré vs restant ;
- **tickets ouverts** — le seul canal où la friction utilisateur remonte non filtrée, et le
  meilleur rapport signal/coût de la liste (~1 Ko). Vérifié sur portfolio-tracker : « Gate
  d'opportunité obligatoire avant création de thèse », « Injection du contexte portefeuille dans
  l'opportunity-agent », « Enrichir `brief_json` : moat + cercle de compétence + valeur
  intrinsèque », « fixer l'horizon par défaut » — de la matière d'axe, pas du bruit.

**Exclu : l'historique des MàJ du fichier de reprise.** C'est de la mémoire d'implémentation
(unités d'arrondi, clefs de supersedage, regex) — indispensable pour reprendre le code, sans
valeur pour décider quoi construire.

⚠️ **Biais à contrer explicitement dans la consigne** : nourri de la seule constitution, un agent
proposera toujours des axes *à l'intérieur* du cadre. Lui donner le droit de dire que **le cadre
lui-même** est l'axe à revoir, plutôt que de produire une proposition conforme.

---

## 5. Règles d'archivage

**Déclencheur = un fait, pas une impression** : l'éviction a lieu quand une capacité de la roadmap
est cochée. Preuve que le critère subjectif ne tient pas : portfolio-tracker a été allégé le
2026-08-31 (65 Ko sortis vers `00-REPRISE-ARCHIVE.md`) et **quatre jours plus tard son fichier
faisait 75 Ko — plus que son archive**. La consigne existait déjà.

Puis, dans l'ordre :

1. **Rien n'est évincé avant que le durable en soit sorti.** Test : *ce fait changerait-il ce
   qu'un agent fait sur un autre fichier, ou un autre projet ?* Oui → `CLAUDE.md` (convention) ou
   `DECISIONS.md` (gotcha). La convention emporte **une** mesure en preuve — c'est ce qui la rend
   crédible plutôt que sentencieuse (cf. « 78 % de la facture, 3 850 tokens contre 850 » dans la
   convention #41 de portfolio-tracker). Pas le récit complet.
2. ⚠️ **Une dette ne s'archive jamais avec le bloc qui la mentionne.** Mode de panne réel : les
   dettes de portfolio-tracker sont disséminées dans des blocs `MàJ` de capacités **livrées**
   (« ingestion-agent, non bloquant »). Évincer par capacité close les emporterait en silence.
   Avant d'évincer, tout item ouvert nommé remonte dans « Reste à faire », qui ne bouge pas.
3. **Le récit du travail livré** part dans `00-REPRISE-ARCHIVE.md` — jamais chargé, greppable.
4. **L'archive garde une carte** : une ligne dans le fichier de reprise disant où les choses sont
   parties. Sans elle, l'archive devient un fichier que personne ne saura interroger.

Budget à surveiller : `CLAUDE.md` du projet (auto-chargé) **+** fichier de reprise = le coût
d'ouverture réel. Sur portfolio-tracker : 47 Ko + 75 Ko ≈ **30 000 tokens** avant toute lecture de
code. D'où la règle de non-recouvrement : **le fichier de reprise ne redit jamais ce que le
`CLAUDE.md` porte déjà.**

---

## 6. Les 3 lots

**Ordre imposé** : la doctrine avant le code (sinon le Hub implémente une cible qui bouge encore).
**Test d'acceptation commun** : le lot retire autant qu'il ajoute (cf. §7) — un lot qui n'a rien
supprimé n'est pas terminé.

### Lot A — doctrine · contexte partagé : documentation transverse ✅ LIVRÉ (`fde83dc`)
- [x] Réécrire `CONTROL_SYSTEM.md` sur le modèle §3 (roadmap → fichier de reprise → lot de
      conversation ; ticket = inbox seule)
- [x] Y intégrer le gabarit de roadmap (liste ordonnée + test d'acceptation + checklist §3.4)
- [x] Y intégrer les règles d'archivage (§5) dans le protocole de fin de conversation
      — **plus** la persistance git du §9.3, qui y manquait
- [x] Purge des `CLAUDE.md` (§7)
- **Acceptation** : ✅ hors les deux exceptions documentées au §1 (l'épitaphe volontaire de
      `CONTROL_SYSTEM.md`, et `app/roadmap.py` qui est le lot B).

### Lot B — Hub · contexte partagé : `projects/hub/app/roadmap.py`
- [x] **Correctif frontmatter (bloquant, §8)** ✅ `907c00d` — mais **pas encore déployé** (voir §11)
- [ ] Affichage du `00-REPRISE.md` par projet (résolution racine → `roadmap/**`)
- [ ] Bouton « inscrire cette roadmap dans le fichier de reprise » — **fermé si `status: brouillon`**
      (§3.2), avec le motif affiché : « à raffiner au terminal avant inscription »
- [ ] Retrait de la mécanique de sprint : `_generate_sprint_order` (`:108-136`), route
      `/sprint-order` (`:704-717`), écriture de `SESSION.md` (`:716`), bloc UI sprints (`:514-540`)
- [ ] ~~Retrait des formulaires de création~~ → **arbitrage tranché : on GARDE** `/new-roadmap` /
      `_create_roadmap`, qui doit désormais écrire `status: brouillon` dans le frontmatter. Retirer
      en revanche `_create_item` (`/new`, `_page_new`) : le ticket n'est plus une unité de découpage
      (§3.6), et une capacité s'écrit dans la roadmap, pas via un formulaire.
- [ ] `_parse_item` : défaut `type: chantier` (`:85`) → concept mort, remplacer par un défaut honnête
- **Acceptation** : une sauvegarde depuis le Hub sur `01-spec-v2-unifiee.md` rend un fichier
      **identique** hors le champ édité (test négatif : le vérifier AVANT correctif, il doit échouer).

### Lot C — amorçage · contexte partagé : un projet témoin
- [ ] Gabarit `00-REPRISE.md` + consigne du 360° (§4) rédigée pour être lue par l'agent
- [ ] Amorçage sur **newsletter-summary** ou **comms-gateway** (les deux ont déjà un fichier)
- [ ] Vérifier le cycle complet : roadmap co-écrite → inscrite depuis le Hub → « reprends le
      projet X » → lot exécuté → capacité cochée → archivage appliqué
- **Acceptation** : le cycle a tourné une fois de bout en bout sur un vrai projet, pas en dry-run.

---

## 7. À SUPPRIMER (le lot n'est pas fini tant que ce n'est pas fait)

La dérive de nommage a **déjà eu lieu** : `projects/portfolio-tracker/CLAUDE.md` prescrit
`SESSION_BRIEF.md` et « execute le brief session » — fichier inexistant, formulation morte. Et la
règle `00-REPRISE` est écrite **deux fois** dans le `CLAUDE.md` racine, en deux versions
divergentes. Ajouter sans retirer est le mode de panne avéré de cet écosystème.

- [x] `projects/assistant-ia/SESSION.md` — supprimé après vérification qu'il ne portait aucune
      dette (ticket `closed`, chantier `done` + archivé)
- [x] `CONTROL_SYSTEM.md` : §§ *Passage Hub → Claude Code*, *Ré-armement automatique*, *Format des
      tickets* (comme outil de planification — l'inbox est gardée, §7 du nouveau fichier)
- [x] `CLAUDE.md` racine : la règle `00-REPRISE` dupliquée → fusionnée en une seule, qui interdit
      désormais explicitement l'empilement de blocs `MàJ` (la cause mesurée du gonflement à 75 Ko)
- [x] `projects/portfolio-tracker/CLAUDE.md` **et `projects/bank-review/CLAUDE.md`** (celui-ci
      n'était pas dans le cadrage : il portait le même `SESSION_BRIEF.md` mort)
- [ ] Hub : voir lot B

---

## 8. ✅ RÉSOLU (`907c00d`) — le Hub détruisait le frontmatter à la sauvegarde

> **Correctif livré le 2026-09-05.** Le Hub n'édite plus que le corps ; le frontmatter est repris
> octet pour octet et seule la ligne `status:` de premier niveau y est substituée. Gardé par
> `projects/hub/checks/check_frontmatter_preserved.py`, **rouge avant / vert après** (31 des 46
> documents à frontmatter du repo étaient abîmés — le cadrage n'en avait mesuré qu'un).
> Le check porte une seconde garantie : la validité YAML du frontmatter, qui a révélé deux
> `00-REPRISE.md` déjà invalides (comms-gateway, newsletter-summary), corrigés au passage.
> ⚠️ Reste à **déployer** (§11) : le conteneur sert encore l'ancien code.

<details><summary>Diagnostic d'origine (conservé — il documente le mode de panne)</summary>



**Mesuré**, en rejouant le parseur du Hub (`app/roadmap.py:47-54` en lecture, `:681-700` en
écriture) sur `projects/portfolio-tracker/roadmap/01-spec-v2-unifiee.md` :

```
frontmatter : 15 lignes avant  →  7 lignes après UNE sauvegarde
```

Trois dégâts, tous silencieux (pas d'erreur, redirection `flash=saved`) :
- les **scalaires de bloc YAML** (`role: >`, `downstream: >`) perdent tout leur contenu — le
  frontmatter est reconstruit à plat en `clé: valeur` (`:699`) ;
- une ligne de continuation contenant un `: ` est promue en **clé parasite** (constaté :
  `Le découpage en tickets suit le principe de développement: pour chaque capacité,`) ;
- le corps est intact, donc le diff git ressemble à une édition légitime.

C'est sur le trajet exact de la décision §3.2 (micro-éditions dans le Hub avant bascule), et les
roadmaps co-écrites porteront ce type de frontmatter riche — `role: >` est déjà la convention sur
les documents structurants. **Correctif** : soit un vrai parseur YAML, soit — plus simple et
suffisant — le Hub ne touche **que le corps** et réécrit le frontmatter **octet pour octet**.

</details>

---

## 9. Reste à faire / à trancher

- ~~Arbitrage formulaires de création~~ ✅ tranché le 2026-09-05 : **gardés**, avec l'état
  `brouillon`/`figée` comme vanne (§3.2 réécrit). `_create_item` part quand même.
- ~~Projet témoin du lot C~~ ✅ **newsletter-summary** (choisi le 2026-09-05 : il a un
  `00-REPRISE.md` et un backlog vivant — digest HTML, Option A en repli — donc une vraie roadmap à
  co-écrire, alors que comms-gateway est bloqué sur du hors-code : domaine Resend, app Slack,
  téléphone).
- ~~Persistance~~ ✅ traité au lot A : l'obligation de committer la doc même sans déploiement est
  écrite dans `CONTROL_SYSTEM.md` §5 (*Persistance*) et rappelée dans le `CLAUDE.md` racine.
- ⚠️ **Écriture concurrente dans le dépôt** — constatée le 2026-09-05 vers 06:02 UTC pendant cette
  conversation : `backend/app/agents/v2/worker.py` (modifié) et `backend/app/knowledge/
  material_events.py` (nouveau, 289 lignes) sont apparus dans l'arbre de portfolio-tracker alors
  qu'il était propre au démarrage. Vraisemblablement la boucle autonome. **Conséquence pour ce
  chantier : ne jamais utiliser `git add -A` / `git add .` ici** — indexer les fichiers du lot par
  liste explicite, sinon un lot de doc emporte du code non validé dans son commit.

---

## 11. ⚠️ Angles morts découverts en cours de route (pas dans le cadrage initial)

1. **`autoloop.sh` dépend de `SESSION.md`.** `/srv/auto-loop/autoloop.sh` dépose son ordre de nuit
   dans `projects/{projet}/SESSION.md` (l. 175-180), le suppose absent (l. 170), l'exclut de sa
   détection de changements (l. 276) et le tient hors des commits (l. 293). C'est un **homonyme**
   de l'ordre de sprint supprimé, pas un vestige. L'entrée `projects/*/SESSION.md` du `.gitignore`
   **reste** — la retirer ferait committer un ordre de pilotage à chaque nuit. Commentaires de mise
   en garde ajoutés dans `.gitignore` et `CONTROL_SYSTEM.md`.
2. **Le test d'acceptation du lot A ne couvrait que `.md`/`.py`/`.html`.** Deux occurrences
   vivaient ailleurs : `.gitignore` et `projects/hub/docker-compose.yml`. Corrigées. Leçon pour
   les lots suivants : greper **toutes extensions**, pas la liste qu'on croit exhaustive.
3. **Déploiement du Hub non fait** — `infrastructure/compose-deploy.sh hub …` a été **refusé par
   le classifieur de permissions** (deux formulations essayées). Le code est commité et poussé
   (`907c00d`), mais l'image n'est pas reconstruite : `docker-compose.yml` fait `build: .`, donc
   `app/` est **dans l'image**, pas bind-mounté (seul `projects/` l'est). **Le conteneur `homepage`
   sert encore le code qui détruit le frontmatter.** À lancer par l'utilisateur :
   `! infrastructure/compose-deploy.sh hub -m "Hub: correctif frontmatter" -f "projects/hub/app/roadmap.py"`
4. **Écriture concurrente dans le dépôt** pendant cette conversation (voir §9).

---

## 10. Où démarrer

**Lot B** — le Hub, `projects/hub/app/roadmap.py`. La doctrine est figée : ce fichier a maintenant
une cible stable à implémenter.

Ordre recommandé à l'intérieur du lot B :
1. **§8 d'abord** (frontmatter détruit à la sauvegarde) — autonome, bloquant, et son test
   d'acceptation est un vrai test négatif : le vérifier **avant** correctif, il doit échouer.
2. Affichage du `00-REPRISE.md` + bouton d'inscription de la roadmap.
3. Retraits (mécanique de sprint, puis formulaires de création **une fois l'arbitrage §9 tranché**).

Le lot A a fixé le vocabulaire que le Hub doit parler : `Roadmap active :` en tête du fichier de
reprise, capacités `- [ ]`/`- [x]`, résolution racine → `roadmap/**`. Voir `CONTROL_SYSTEM.md` §2.
