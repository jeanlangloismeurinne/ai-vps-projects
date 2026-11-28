---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-28 (M2 et M3 ACCEPTÉS — B6 et les pièces réelles à l'écran reportées ; M4 ouvert, 3a tranchée, questions 1-2 en discussion) — historique des mises à jour : `git log` de ce fichier
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3. Ne porte que l'ÉTAT, le PROCHAIN PAS et les pointeurs. Récit →
  `00-REPRISE-ARCHIVE.md` ; règles durables → `CONVENTIONS.md` (index dans `CLAUDE.md`) ; preuve →
  `backend/checks/`. CE FICHIER NE S'EMPILE PAS : garder sous ~8 Ko, sortir le récit à chaque fin de lot.
---

# Prompt de reprise — portfolio-tracker V3

> **Lire d'abord `roadmap/V3/PRINCIPES-FONDATEURS.md`** (arbitrages en termes MÉTIER ; chaque décision
> éclairée par la pratique d'un VRAI fonds ; un raffinement se débraye vers la règle simple ; **tout
> développement vaut pour toutes les entreprises : on corrige la cause, jamais l'exemple**).

## ➜ Prochain pas

**M3 ACCEPTÉ le 2026-11-28** (utilisateur) : **l'affichage de pièces RÉELLES à l'écran (K12, K14) reste
À FAIRE**, ligne d'acceptation du premier module qui cite (M6, ou le lot de ressaisie de M4 s'il vient
avant) ; dossier archivé : `roadmap/archive/V3-M3-base-connaissance.md`.

**M2 ACCEPTÉ le 2026-11-28** (utilisateur) ; l'évaluation réelle d'une source (B6, payante) est une
ligne d'acceptation de M6 (`07-avant-comite.md` § « À l'ouverture de M6 ») ; dossier archivé :
`roadmap/archive/V3-M2-collecte-sources.md`. **M4 « Comptes et segments » OUVERT le 2026-11-28** : `M4-comptes-segments.md` (tri, acceptation
C1-C12, **question 3 tranchée (a)** le 2026-11-28 : données structurées seulement, SpaceX reçoit son
trimestre et le manque nommé ; **questions 1 (famille de comptes : la déclarer ou laisser le système
décider de la structure ?) et 2 (reclassements par émetteur) en discussion**). Prochain pas : arbitrages, puis construction hors ligne (société fictive) ; la suite de B13 et l'option C y sont
reprises (C8).

**Où on en est (2026-11-22)** — **M2, M3, le déclencheur et l'écran de l'étude sont EN PRODUCTION**
(migrations 064 puis 065 appliquées le 2026-11-22 ; backend et frontend reconstruits, commit `401d2a1` ;
vérifié dans les conteneurs : routes `/v2/emetteurs/{e}/etude`, `libelles_actes`, tâche planifiée
`_passage_des_etudes` enregistrée, section « Étude de la société » compilée ; GET réel NVDA/SPCX/RVMD
→ 200, « pas à l'étude »). Suite : `check_recueil_persist` et `check_connaissance_persist` désormais
verts ; seul rouge connu : `check_signature_modele_persist` (données de l'ancien enchaînement).
Détail des modules : `roadmap/archive/V3-M2-collecte-sources.md`, `roadmap/archive/V3-M3-base-connaissance.md` §5.

**Trois vrais dossiers terminés le 2026-11-22** (NVDA, RVMD, SpaceX : comptes annuels + companyfacts,
tout SEC, 0 $ ; le coût d'un dossier avec collecte web n'est PAS encore mesuré ; RVMD a aussi la cotation
`RVMDW`, bons de souscription à exclure quand un module lira le cours). Relecture de la collecte
débrayée (`lecture_humaine.recueil = false`). Détail : archive, « 2026-11-22 — sorti de la reprise ».

**K13 FAIT le 2026-11-22** (gratuit ; `tools/controle_ancien_systeme.sh --en-memoire`) : 57 fiches de
l'ancien système → 43 retrouvées, 12 écarts expliqués (l'ancien lecteur collait cellules et blocs), 0
inexpliqué, 2 d'une autre société (#87). Il a révélé un **défaut du lecteur** : les retours à la ligne du
code source HTML coupaient les lignes (procurations et 8-K Donnelley : une cellule par ligne), masqué par
les 10-K Workiva → **lecteur 1.2.0** (déployé ; la tâche de fond relit les 6 documents à son passage
suivant, les lectures 1.1.0 restent). Détail : `roadmap/archive/V3-M3-base-connaissance.md` § « K13 ».

**B13** (besoin initial seul, constatée le 2026-11-22) : la suite — intermédiaires et annonces
demandés au fil du dossier — est une ligne d'acceptation de M4 ; **option C en réserve** (élargir le
besoin initial dans le `referentiel.json` de `comptes`), décision à la clôture de M4. Les demandes « au
fil du dossier » (M3 §2, 1 bis) se construisent avec M4 ; un dossier terminé ne repart pas quand le
parcours s'allonge : à traiter avec M4.

M1 accepté sur le VPS le 2026-11-16 (reste à l'écran : admettre, révoquer, corriger sur de vraies
décisions ; puis archiver `M1-fiche-emetteur.md`). Modèles : Sonnet pour les rangements en base, Opus
pour ce qui demande du jugement (évaluateur, consignes).

**M0 « Fondations » : ACCEPTÉ** (hors ligne le 2026-11-13, rejoué sur le VPS le 2026-11-16).

**Direction** (arbitrée et CONFIRMÉE le 2026-11-13 ; tableau : `EVALUATION-ARCHITECTURE-2026-11-13.md`
§ « Arbitrages rendus ») : reconstruction module par module sur une base propre, l'ancien code est une
carrière ; ordre M0-M11 accepté ; kit de spécialité accepté (sans kit : parcours généraliste) ;
contradicteur après le premier comité ; c'est l'utilisateur qui dit quoi analyser. **Aucune mesure
payante avant le module M6 (carte).**

## Reste ouvert (ne s'archive pas)

- **À FAIRE : pièces réelles à l'écran de l'étude** (M3 accepté sans, 2026-11-28) — premier module qui cite ;
  **B6 réelle** (évaluation d'une source rencontrée) — M6. Les deux : `07-avant-comite.md` § « À l'ouverture de M6 ».

- L'ancien chantier « découpage » (B4g) est **clos sans suite** : ses acquis (inventaire, arbre, premier niveau
  par les segments) seront triés à l'ouverture de M6-M7. Lots B4d, #143, B4f, B4g en production depuis le
  rebuild du 31/10 (vérifié le 2026-11-16) ; sans importance : remplacés par la reconstruction. Récit : archive, « 2026-11-13 — arbitrages ».
- Dettes de l'ancien plan rattachées à leur module : plan 07, « Dettes reprises ».
- Orientations de l'utilisateur à reprendre en M6 : une ligne par source de cash-flow ; finesse selon la
  maturité ; probabilité de succès hors du découpage ; vocabulaire standard dans tous les prompts ; molécules
  précoces → plateforme sauf marché chiffrable.
- Interrupteur `porte_admet_reponses_refusees` : devient sans objet avec l'ancien architecte (à retirer à son tri).
- NASDAQ : sous-projet indépendant, hors chantier V3 — sa reprise : `backend/app/nasdaq/00-REPRISE-NASDAQ.md`.
- 26 contrôles sans test négatif à leur nom ; deux modèles épinglés dans le code : soldés module par module.
- `backend/tools/mesure_gate_capacite4.py` ne compile pas (erreur d'indentation, relevée par la garde des
  accès le 2026-11-13) : outil de l'ancien enchaînement, à supprimer ou réparer au tri de M6.
- Chef de dossier : rangement en base (migration 063, appliquée le 2026-11-16) ; déclencheur (module
  `etude`) et gestes à l'écran en production depuis le 2026-11-22.

## Où on en est (mesuré le 2026-10-16/17 — RE-REQUÊTER avant de s'en servir)

- **Jalon** (réduit le 2026-10-17 : **NVDA + RVMD** d'abord, puis financière US, puis étranger, MSFT en
  contrôle de reproduction) : note d'initiation (6 chapitres + fourchette), fonctionnement
  ET reproductibilité ; **roadmap active : `07-avant-comite.md`** (modules M0-M11) ; `roadmap/archive/V3-05-frameworks-complets.md` = ancien détail (archivé).
- **Chapitres instruits de l'ancien enchaînement** (NVDA, RVMD, MSFT, mesurés le 2026-10-16/17) : archive, « 2026-11-21 — sorti de la reprise » ; ils ne sont pas repris (charte 7).
- **Suite** `bash backend/checks/run_all.sh` (rouge connu : `check_signature_modele_persist`, données de l'ancien enchaînement) : total, date et commit du dernier passage dans `backend/checks/LIGNE_DE_BASE.md` (écrit par le lanceur — seule source du chiffre, ne pas le recopier ici). Négatifs (2026-10-23, après B4f : explorateur 5/5, architecte 51/51, modèle 71/71, architecture 6/6, périmètre 32/32, ventilation 19/19 — les négatifs se lancent DEPUIS `backend/`).
- **Production** : rebuild de sécurité du 31/10 (`46a663f`) — embarque B4d, #143, B4f, B4g et le maillon 1 (vérifié fichier par fichier le 2026-11-16) ; M1 pas encore déployé. Migration 062 appliquée. Détail des déploiements et porte de l'architecte NVDA : archive, « 2026-11-13 — sortis de la reprise ».
- **Migration 063 APPLIQUÉE le 2026-11-16** (fiches des émetteurs, journal des sources avec évaluations et mises en suspens, état des dossiers) ; **064** (`recueil_*`) et **065** (`connaissance_*`, `etude_*`) APPLIQUÉES le 2026-11-22 ; prochaine : 066 (062 = PV de l'architecture, appliquée le 2026-10-22 ; 061 = registres du classeur : architectures, fourchettes, scénarios, déplacements ; 060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
  NVDA #740-#745, MSFT #746-#750.
- **Réglage `v2_auto_enabled` = FALSE** (le matin ne fait que recenser). Crédit DeepInfra : vérifier par
  un appel minimal avant toute grosse dépense.

## Arbitrages récents

Le détail : `CONVENTIONS.md` #129-#139 ; séance du 2026-10-17 : `roadmap/archive/V3-08-seance-arbitrages.md` ; liste du 2026-10-16
au 2026-10-18 : archive, section « 2026-10-19 — sortis de la reprise (arbitrages récents) ».

## Outils (tous dans `backend/tools/`, gratuits sauf mention)

- `montrer_parcours.sh TICKER` (dossier, manques, notes de qualité) · `montrer_socle.sh TICKER…` (comptes
  reconstitués) · `recouper_nombres.sh TICKER framework` (chaque nombre d'une réponse retrouvé dans ses
  pièces ; même règle que le contrôle #136) · `acceptation_analyste.sh --admissibilite` avec `ACCEPTATION_CAS=TICKER:framework:archetype`
  (ce que le corpus permet, sans appel modèle).
- Payants : `executer_chaine.sh TICKER framework archetype [--questions=…] [--sans-collecte]` (ÉCRIT en
  prod, ~1 h par chapitre, imprime l'inventaire de ses écrits) · `mesurer_ligne_web.sh PLAN LIGNE…`
  (rejoue une ligne de collecte à blanc, ~0,01 $) · `acceptation_traducteur.sh TICKER:framework:archetype`.
- Retraits en base : `tools/retraits/*.sql` (un fichier daté par retrait, avec sa trace).

## Pièges à ne pas re-découvrir

- Producteurs déterministes exécutés et lus **en texte** avant toute dépense ; `LE VERDICT EST À LA
  LECTURE` : relire chaque réponse contre ses pièces (les contrôles gardent la structure, jamais le sens).
- `ps aux` / `docker ps` avant toute relance ; lancer en arrière-plan avec l'outil, jamais `nohup … &`.
- Un check neuf n'est livrable qu'après avoir viré au rouge pour la bonne raison (`negatif_*.sh`) ;
  fixtures copiées du réel ; une garde déléguée se mute chez son détenteur.
- Ne jamais induire les frameworks de la base ; une question se pose en substance économique.

## Ce qui est fermé (ne pas rouvrir)

Grille MVDD / `SYNTHESIS_TARGETS` supprimés · hybridation RRF interdite · tout levier du modèle sur
l'exigence (plancher, nature, champs requis) · dégrader le tier d'une source selon l'émetteur ·
« capacité 5 barreau 4 » (l'agent propose une méthode d'approximation).

## À lire selon le besoin

`07-avant-comite.md` (LE plan : modules M0-M11) · `M1-fiche-emetteur.md` (tri et acceptation de M1) · `EVALUATION-ARCHITECTURE-2026-11-13.md` (audit, cible en blocs, arbitrages rendus) · `roadmap/archive/V3-05-frameworks-complets.md` (ancien détail) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
