---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-22 (064+065 appliquées, M2/M3/étude déployés ; prochain lot : mise à l'étude à l'écran, K14 puis K13) — historique des mises à jour : `git log` de ce fichier
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

**Où on en est (2026-11-22)** — **M2, M3, le déclencheur et l'écran de l'étude sont EN PRODUCTION**
(migrations 064 puis 065 appliquées le 2026-11-22 ; backend et frontend reconstruits, commit `401d2a1` ;
vérifié dans les conteneurs : routes `/v2/emetteurs/{e}/etude`, `libelles_actes`, tâche planifiée
`_passage_des_etudes` enregistrée, section « Étude de la société » compilée ; GET réel NVDA/SPCX/RVMD
→ 200, « pas à l'étude »). Suite : `check_recueil_persist` et `check_connaissance_persist` désormais
verts ; seul rouge connu : `check_signature_modele_persist` (données de l'ancien enchaînement).
Détail des modules : `M2-collecte-sources.md`, `M3-base-connaissance.md` §5.

**Trois vrais dossiers TERMINÉS le 2026-11-22** (NVDA, RVMD, SpaceX ; passages 13-19) — chacun : 2
demandes (derniers comptes annuels + companyfacts, `sans_objet` à la lecture, voulu), tout depuis la
SEC, **coût 0 $** (aucun modèle, aucune recherche web ; crédit DeepInfra inchangé ≈ 2,91 $) → le coût
d'un dossier avec collecte web n'est PAS encore mesuré (aucune des trois n'en a eu besoin).
NVDA : 10-K FY2026 (1 852 lignes, CA 215 938 M$ vérifié), validé à l'écran. RVMD : 10-K FY2025
(4 259 lignes) ; fiche révision 2, cotations `RVMD` **et `RVMDW`** (bons de souscription : à exclure
quand un module lira le cours coté). SpaceX : prospectus 424B4 du 2026-06-12 (#148 ; 15 458 lignes,
CA 2025 18 674 M$) ; fiche complétée par le système en révision 2 (« SPACE EXPLORATION TECHNOLOGIES
CORP », US, NASDAQ SPCX, CIK 1181412). Ses comptes intermédiaires postérieurs à l'introduction ne sont
pas demandés (aucun besoin déclaré). 0 pièce de connaissance : normal avant M4.

**Relecture de la collecte DÉBRAYÉE le 2026-11-22** (`lecture_humaine.recueil = false`, à la demande de
l'utilisateur) : un dossier va au bout sans arrêt ; le raffinement « en cas de doute seulement » est à
la feuille de route du module (`app/modules/recueil/ARCHITECTURE.md`). Contrôles qui jouent le geste à
l'écran : relecture rétablie le temps du contrôle (`check_etude.relecture`).

**Prochain lot** : K13 (57 fiches SEC de l'ancien système retrouvées dans les dépôts recollectés —
gratuit, NVDA et RVMD désormais collectées) et les lignes « réel » de M2 (B3/B6/B10/B13). Les demandes
« au fil du dossier » (M3 §2, 1 bis) se construisent avec M4. Un dossier terminé ne repart pas quand le
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
