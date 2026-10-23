---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-23 (B4d livré : architecte NVDA 2/2, RVMD 1/2 acceptés à blanc ; sens NVDA à arbitrer) ; 2026-10-23 (ventilation NVDA publiée, correctif DEF 14A d504d96) ; 2026-10-23 (P1 terminé et déployé, arbitrage Q1 révisé, #142) ; 2026-10-22 soir (M3 bis déployé, me_7 instruite, P1 partiel, architecte à blanc) ; 2026-10-22 (M3 bis v2.1 livré, vérifié, commité, NON déployé) ; 2026-10-22 (M3 déployé ; spec M3 bis écrite) ; 2026-10-22 (M2 déployé ; spec M3 écrite) ; 2026-10-21 (M2 livré, commité, non déployé ; porte NVDA ouverte) ; 2026-10-21 (commentaires sur la page de lecture → spec v2.1 §12 ; C1 livré, #141) ; 2026-10-21 (plan d'action unique avant comité, cible NVDA ; spec du modèle de l'entreprise validée, #140) ; 2026-10-19 (points 10 et 12 construits ; point 9 en arbitrage ; mesure (e)) ; 2026-10-19 (ré-analyse qui dégrade, point 13, `6760090`) ; 2026-10-18 (demandes de recherche closes à la livraison, point 14, `8af6f4a` ; causes du point 13) ; 2026-10-18 (fraîcheur sujet par sujet, point 15, `331aa7c`) ; 2026-10-18 (changement de stade + classement par le comité, #139) ; 2026-10-18 (« pas encore observable », #138) ; 2026-10-17 (relance bornée + réinitialisation, `c2bc1af`) ; 2026-10-17 (séance d'arbitrages #137) ; 2026-10-16 (allègement : état complet copié dans 00-REPRISE-ARCHIVE.md, section « 2026-10-16 — COPIE CONFORME »)
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

**`07-avant-comite.md` est L'UNIQUE plan d'action** jusqu'au premier comité réussi (cible **NVDA** : six
chapitres + classeur signé + décision au PV) ; son **journal** consigne chaque action. Réplicabilité exigée
(principe n° 4). Spec du modèle : `09-modele-entreprise.md` (v2.1, #140). Lots M1, M2, M3, M3 bis déployés ;
`me_7` instruite (NVDA #2292 faible, RVMD #2304 juste).
**Fait le 2026-10-23 — lot B4d (M3 ter, architecte) LIVRÉ** (journal du plan, ligne B4d) : contrat 1.3.0 (une
ligne par programme nommé, plateforme pour les non nommés, inventaire), [S13]-[S15], pièces citables visibles,
péremption au pied du verbatim, jamais de plantage. À blanc : **NVDA accepté 2/2, RVMD 1/2** (`mesures/2026-10-23/
b4d-apres3/`, `b4d-apres4/`). Avant : P1 terminé et déployé (#142, `f6b5659`) ; ventilation NVDA publiée (#1770).
**⚠ ARBITRAGE EN ATTENTE (sens, pas structure)** : sur NVDA, Vera Rubin (déjà expédiée) et Vera CPU sont traités en
paris de développement sans chiffre d'affaires, « l'IA souveraine » (un segment de clients) en programme — la règle
« génération suivante → rattachée à son activité » n'est pas appliquée et aucun contrôle de structure ne la voit
(#68). Piste : changer la FORME de l'inventaire (pour chaque ligne propre, écrire le produit vendu dont elle serait
la suite, ou « aucun », et ce qui rend la réussite incertaine). RVMD : les essais d'extension d'indication
(RASolute 303/304, RASolve 301) sont tantôt rattachés à RASONQUE, tantôt une ligne chacun — à trancher.
**DIAGNOSTIC du 2026-10-23** (journal, ligne « B4d (diagnostic) », `mesures/2026-10-23/banc-modeles/`) : Vera
Rubin = capacité du modèle (V4-Pro réussit, même anonymisé) ; IA souveraine, Vera CPU et le « 8 programmes » RVMD =
information (me_7 mal formée, comptage faux, pièces invisibles à l'architecte) ; [S15] contournable par une
plateforme inventée. **Arbitré** : V4-Pro en architecte (accord sous réserve de qualité, mesurée) ; extension
d'indication = ligne propre, critère « faut-il des données de marché et de concurrence ad hoc ? » (#143). **Construit**
`f4a5872`, NON déployé ; me_7 réémise (#2625 NVDA, #2624 RVMD incomplète) ; architecte à blanc `apres-143/` : pas encore
acquis (journal, ligne « #143 (construit, éprouvé) »). Prochain : formulation du critère (sans probabilité de succès),
nom = avant « — », une extension d'indication = un élément de me_7 ; question à l'utilisateur : analyste de me_7 sur V4-Pro ?
**PROCHAIN PAS** : (1) poser ces deux questions à l'utilisateur ; (2) **B4f** `16-lot-B4f-explorateur.md` ;
(3) **B4e** banc séquentiel (arrêt à 2 succès consécutifs, ≤ 10 entreprises) — un succès s'y juge À LA LECTURE.
Portes : NVDA ouverte ; RVMD fermée par se_3 (`--hors-porte`). Interrupteur `porte_admet_reponses_refusees`
à basculer à `false` AVANT le premier comité réel. ma_3/ma_4/A1 restent dans D1.
Dettes : voir la section « Dettes hors du chemin » du plan. Historique de l'ancien ordre : archive.

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
- **Suite** `bash backend/checks/run_all.sh` verte (2026-10-23, après B4d : 6 027 assertions ; négatifs architecte 45/45, modèle 71/71, architecture 6/6, périmètre 32/32, ventilation 19/19 — les négatifs se lancent DEPUIS `backend/`).
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

`05-frameworks-complets.md` (roadmap active) · `07-avant-comite.md` (LE plan d'action avant comité) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
