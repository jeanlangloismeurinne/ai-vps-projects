---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-13 (évaluation d'architecture rendue, phases 1-2 ; « Prochain pas » réécrit, récit du 21/10 au 13/11 sorti à l'archive ; historique des mises à jour : archive)
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

**ARBITRER L'ÉVALUATION D'ARCHITECTURE (2026-11-13).** Phases 1-2 rendues, RIEN n'est arbitré, phase 3 non
commencée (autre séance, plafond de dépense à fixer). Doc à commenter :
https://claude.ai/artifact/DiTMznggexcwavdtkHk8VA ; copie versionnée : `EVALUATION-ARCHITECTURE-2026-11-13.md`.
Verdict : **adapter** la proposition du 24/10 (`PROPOSITION-PROCESSUS-INSTRUCTION-2026-10-24.md`, doc
https://claude.ai/artifact/FrEvaCnM7py8ZTeJB8DRCn) — son ordre est bon (le modèle de l'entreprise devient la
colonne vertébrale), avec cinq amendements : chef de dossier automatique, mesure du sens (étalons, relecteur,
deux passages), contrats entre blocs gardés, point d'extension « émetteur et sources », gel de ce qui est en
avance. Huit questions posées à l'utilisateur (fin du doc) ; aucun point fermé n'est rouvert.
À la reprise : lire les commentaires du doc, consigner les arbitrages, PUIS réécrire `07-avant-comite.md` en
conséquence (il reste l'unique plan d'action jusqu'au premier comité, cible **NVDA**) et annoncer le lot.

**État du chantier « découpage » (B4g), EN PAUSE jusqu'à l'arbitrage** — récit complet : journal de
`07-avant-comite.md` et archive, section « 2026-11-13 — sorti de la reprise ». Lots M1, M2, M3, M3 bis, P1 déployés ;
B4d (`7d08a6d`), #143 (`f4a5872`), B4f, B4g étapes 0-3 et maillon 1 (inventaire) commités, **NON déployés**.
Réorientation du 2026-10-24 : trois maillons — 1 INVENTAIRE (tâche séparée de `me_7`, V4.1 Flash, construit et
mesuré : cœur relevé 3/3, périphérie fluctuante), 2 CLASSER selon l'arbre (un modèle, à construire), 3 CONSTRUIRE
l'architecture (code, à construire). La proposition du 24/10 en fait ses étapes 3 et 4.

## Reste ouvert (ne s'archive pas)

- Question 3 de l'arbre mal posée (« déjà vendu » sur l'élément au lieu de l'élément × marché) : correctif à valider.
- Recouvrement clients × produit sous `data_center` (NVDA) ; RMC-5127 / RM-055 sans marché visé ; RM-055 manquant
  à l'inventaire = PÉRIMÈTRE des pièces — à trancher.
- `me_7` sur V4-Pro : à décider ; Rubin / IA souveraine instables sur V4-Pro.
- Orientations de l'utilisateur NON arbitrées : une ligne par source de cash-flow (non-recoupement avant
  granularité) ; finesse selon la maturité ; probabilité de succès hors du découpage ; vocabulaire standard dans
  tous les prompts ; molécules précoces → plateforme sauf marché chiffrable.
- Interrupteur `porte_admet_reponses_refusees` à basculer à `false` AVANT le premier comité réel. Portes : NVDA
  ouverte ; RVMD fermée par se_3 (`--hors-porte`). ma_3/ma_4/A1 restent dans D1.
- Deux découpages superposés sur un même axe (AAPL, MSFT) : dette périmètre. Jargon des titres du dossier : non traité.
- Déploiement des lots commités (refusé par le classifieur le 2026-10-23 — à lancer par l'utilisateur) ; migrations
  `nasdaq_01` / `nasdaq_02` à appliquer à la main (module NASDAQ livré le 2026-10-31, hors chantier V3).
- Constats de l'évaluation sans propriétaire tant que non arbitrés : 26 contrôles sans test négatif à leur nom ;
  identité de l'émetteur = numéro SEC ; site et secteur des émetteurs écrits dans le code ; deux modèles épinglés
  dans le code ; constitution et `ARCHITECTURE-CIBLE.md` périmées.
- Autres dettes : section « Dettes hors du chemin » du plan 07.

## Où on en est (mesuré le 2026-10-16/17 — RE-REQUÊTER avant de s'en servir)

- **Jalon** (réduit le 2026-10-17 : **NVDA + RVMD** d'abord, puis financière US, puis étranger, MSFT en
  contrôle de reproduction) : note d'initiation (6 chapitres + fourchette), fonctionnement
  ET reproductibilité ; roadmap active `05-frameworks-complets.md` (A1-A3 cochés, A4 en cours).
- **Chapitres instruits** (`bash backend/tools/montrer_parcours.sh <TICKER>`, gratuit) :
  NVDA qualité financière 1,00 · défendabilité 0,17 · modèle économique 0,83 · secteur 0,50 ·
  management **2/7** (ma_6, ma_7 répondues — plan #270, réponses #1499-#1505 ; ma_4 #1506) · valorisation :
  rien. RVMD : qualité financière 1,00, défendabilité/modèle économique/secteur/management partiels.
  **MSFT : aucune réponse en vigueur.** Beaucoup de réponses sont « standard antérieur » (#127) : refaites
  à la reconstruction (premier passage du test), pas relues d'ici là.
- **Suite** `bash backend/checks/run_all.sh` verte (2026-10-23, après B4f : 6 082 assertions ; négatifs explorateur 5/5, architecte 51/51, modèle 71/71, architecture 6/6, périmètre 32/32, ventilation 19/19 — les négatifs se lancent DEPUIS `backend/`).
- **Production** : B4d COMMITÉ (`7d08a6d`) mais NON DÉPLOYÉ (déploiement refusé par le classifieur le 2026-10-23 — à lancer par l’utilisateur, puis `docker exec portfolio-backend grep -c "architecture-1.3.0" /app/app/contracts/modele_entreprise_schema.py`) ; dernier déploiement `d504d96` (correctif DEF 14A) ; avant, P1 complet (`f6b5659`) ; avant, M3 bis (`1f9a364`) ; avant, `1d5dfbf` (M3) ; avant, `67f7e87` (M2) ; `4c6d37e` (M1), vérifié dans le conteneur (référentiel 1.0.0 chargé, 21 fiches, seuil 10). Migration 061 appliquée. Mandats : 1 manager ouvert (2918).
- **Porte de l'architecte NVDA — mesurée le 2026-10-21** (`montrer_parcours.sh NVDA`) : les 12 questions sources d'une rentable (me_2-me_5, mo_4, mo_6, qf_1, qf_3, qf_7, se_2-se_4) ont toutes une première réponse instruite (mo_4 recherche épuisée, mo_6/se_2 pièces insuffisantes = information, 09 §11.2) → ouverte ; 22 manques au total, inchangés.
- **Prochaine migration : 063** (062 = PV de l'architecture, appliquée le 2026-10-22 ; 061 = registres du classeur : architectures, fourchettes, scénarios, déplacements ; 060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
  NVDA #740-#745, MSFT #746-#750.
- **Réglage `v2_auto_enabled` = FALSE** (le matin ne fait que recenser). Crédit DeepInfra : vérifier par
  un appel minimal avant toute grosse dépense.

## Arbitrages récents

Le détail : `CONVENTIONS.md` #129-#139 ; séance du 2026-10-17 : `08-seance-arbitrages.md` ; liste du 2026-10-16
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

`EVALUATION-ARCHITECTURE-2026-11-13.md` (à arbitrer) · `05-frameworks-complets.md` (roadmap active) · `07-avant-comite.md` (LE plan d'action avant comité) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
