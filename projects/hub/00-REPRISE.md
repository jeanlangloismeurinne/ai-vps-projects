---
id: reprise-hub-pilotage
status: prompt-de-reprise
created: 2026-09-04
updated: 2026-09-04
project: hub
role: >
  Prompt de reprise du chantier « système de pilotage v3 ». Périmètre TRANSVERSE :
  code dans projects/hub/, doctrine dans CONTROL_SYSTEM.md (racine du repo), plus une
  purge dans plusieurs CLAUDE.md. État : cadrage TERMINÉ et figé, ZÉRO ligne écrite.
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

## 1. État — rien n'est commencé

**Aucun code écrit, aucun fichier de doc modifié, aucune migration.** Ce qui existe est le
cadrage ci-dessous, issu d'une conversation de conception du 2026-09-04. Le point de départ
de demain est un dépôt intact.

---

## 2. Le constat qui a déclenché le chantier (mesuré — ne pas re-dériver)

`CONTROL_SYSTEM.md` décrit un système que personne n'applique.

| Artefact prescrit | Adoption réelle (12 projets) |
|---|---|
| chantier avec `## Sprints` | **1 fichier** : `projects/assistant-ia/roadmap/agent-intention-et-capture-kb.md` |
| `SESSION.md` | **1 fichier** — pointe sur `roadmap/kb-visualisation-obsidian.md`, **qui n'existe pas**. Non suivi par git. |
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
2. **La roadmap est co-écrite avec Opus dans le terminal.** L'utilisateur décrit un besoin, on
   raffine, on fige. Le Hub ne crée plus de roadmap : il **visualise**, permet des
   **micro-éditions finales**, puis **bascule** la roadmap dans le fichier de reprise.
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

### Lot A — doctrine · contexte partagé : documentation transverse
- [ ] Réécrire `CONTROL_SYSTEM.md` sur le modèle §3 (roadmap → fichier de reprise → lot de
      conversation ; ticket = inbox seule)
- [ ] Y intégrer le gabarit de roadmap (liste ordonnée + test d'acceptation + checklist §3.4)
- [ ] Y intégrer les règles d'archivage (§5) dans le protocole de fin de conversation
- [ ] Purge des `CLAUDE.md` (§7)
- **Acceptation** : plus aucune occurrence de « ordre de sprint », « ré-armement »,
      « exécute le sprint en cours », `SESSION.md`, `SESSION_BRIEF.md` dans le repo.

### Lot B — Hub · contexte partagé : `projects/hub/app/roadmap.py`
- [ ] **Correctif frontmatter (bloquant, §8)**
- [ ] Affichage du `00-REPRISE.md` par projet (résolution racine → `roadmap/**`)
- [ ] Bouton « inscrire cette roadmap dans le fichier de reprise »
- [ ] Retrait de la mécanique de sprint : `_generate_sprint_order` (`:108-136`), route
      `/sprint-order` (`:704-717`), écriture de `SESSION.md` (`:716`), bloc UI sprints (`:514-540`)
- [ ] Retrait des formulaires de création (`/new`, `/new-roadmap`, `_page_new`,
      `_page_new_roadmap`, `_create_roadmap`, `_create_item`) — la roadmap naît dans le terminal
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

- `projects/assistant-ia/SESSION.md` (non suivi par git, pointe dans le vide)
- `CONTROL_SYSTEM.md` : §§ *Passage Hub → Claude Code*, *Ré-armement automatique*, *Format des
  tickets* (comme outil de planification — garder l'inbox)
- `CLAUDE.md` racine : la règle `00-REPRISE` dupliquée
- `projects/portfolio-tracker/CLAUDE.md` : dernière section, `SESSION_BRIEF.md` / « execute le
  brief session » → remplacer par le déclencheur §3.7
- Hub : voir lot B

---

## 8. ⚠️ Bloquant — le Hub détruit le frontmatter à la sauvegarde

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

---

## 9. Reste à faire / à trancher

- **Arbitrage ouvert** : retirer les formulaires de création du Hub (lot B) découle de la décision
  §3.2, mais n'a pas été confirmé explicitement. À valider avant de supprimer du code.
- **Projet témoin du lot C** non choisi (newsletter-summary vs comms-gateway).
- **Persistance** : `compose-deploy.sh` ne commite que la liste `-f` fournie. Sur une conversation
  sans déploiement (doc, cadrage, roadmap), **rien ne commite le fichier de reprise**. À rendre
  explicite dans le protocole de fin de conversation du lot A, sinon la mémoire du système ne vit
  que sur le disque du VPS. (État constaté : les trois `00-REPRISE.md` existants **sont** suivis,
  arbre propre.)

---

## 10. Où démarrer demain

**Lot A**, et dans cet ordre : le Hub du lot B implémente une doctrine qui doit être figée d'abord.
Point d'entrée : relire `CONTROL_SYSTEM.md` (racine du repo, 323 lignes) en regard du §3 ci-dessus,
puis le réécrire — il n'y a pas de conception restante à faire, seulement de la rédaction et de la
purge.

Si tu préfères attaquer par le code, le **§8** est autonome et se traite sans dépendre du lot A.
