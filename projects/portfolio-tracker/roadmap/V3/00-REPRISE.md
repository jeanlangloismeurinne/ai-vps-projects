---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-22 (M3 déployé ; spec M3 bis écrite) ; 2026-10-22 (M2 déployé ; spec M3 écrite) ; 2026-10-21 (M2 livré, commité, non déployé ; porte NVDA ouverte) ; 2026-10-21 (commentaires sur la page de lecture → spec v2.1 §12 ; C1 livré, #141) ; 2026-10-21 (plan d'action unique avant comité, cible NVDA ; spec du modèle de l'entreprise validée, #140) ; 2026-10-19 (points 10 et 12 construits ; point 9 en arbitrage ; mesure (e)) ; 2026-10-19 (ré-analyse qui dégrade, point 13, `6760090`) ; 2026-10-18 (demandes de recherche closes à la livraison, point 14, `8af6f4a` ; causes du point 13) ; 2026-10-18 (fraîcheur sujet par sujet, point 15, `331aa7c`) ; 2026-10-18 (changement de stade + classement par le comité, #139) ; 2026-10-18 (« pas encore observable », #138) ; 2026-10-17 (relance bornée + réinitialisation, `c2bc1af`) ; 2026-10-17 (séance d'arbitrages #137) ; 2026-10-16 (allègement : état complet copié dans 00-REPRISE-ARCHIVE.md, section « 2026-10-16 — COPIE CONFORME »)
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3. Ne porte que l'ÉTAT, le PROCHAIN PAS et les pointeurs. Récit →
  `00-REPRISE-ARCHIVE.md` ; règles durables → `CONVENTIONS.md` (index dans `CLAUDE.md`) ; preuve →
  `backend/checks/`. CE FICHIER NE S'EMPILE PAS : garder sous ~8 Ko, sortir le récit à chaque fin de lot.
---

# Prompt de reprise — portfolio-tracker V3

> **Lire d'abord `roadmap/V3/PRINCIPES-FONDATEURS.md`** (arbitrages en termes MÉTIER ; chaque décision
> éclairée par la pratique d'un VRAI fonds ; un raffinement se débraye vers la règle simple).

## ➜ Prochain pas

**`07-avant-comite.md` est L'UNIQUE plan d'action** jusqu'au premier comité réussi (cible : **NVDA**, six
chapitres + classeur signé + décision au PV) ; son **journal** en fin de fichier consigne CHAQUE action (date, Id,
qui, preuve). Réplicabilité exigée (aucun code propre à un titre). Passage au standard repoussé en ultime étape (F1).
**Spec du modèle de l'entreprise VALIDÉE le 2026-10-21** : `09-modele-entreprise.md` (v2, arbitrages §1 et §11,
CONVENTIONS #140) ; page de lecture https://claude.ai/artifact/Dx7LBBpsNAWAYzXroPiDiC. Mesures du jour :
`mesures/2026-10-21/` (inventaire de l'existant, NVDA à blanc, plafond + crédit, ventilation publiée).
**Fait le 2026-10-21 (après-midi)** : deux commentaires de l'utilisateur sur la page intégrés (spec **v2.1, §12**,
#140 complété) — (a) gabarit des comptes **par famille** (industrielle = rentable + pré-revenus ; bancaire à
écrire, lot M2 bis ; mesuré : le socle de JPM est TROMPEUR, intérêts « 0 » en 2024-2025) ; (b) chaque variable
de l'inventaire porte bas/central/haut par une méthode déclarée, un scénario = des DÉPLACEMENTS d'un
sous-ensemble ; **v1 = central seul**, tables `Fourchette`/`Scenario`/`Deplacement` créées dès M1 ; B6 après le
premier comité. **C1 livré** (#141 : l'extrait court remplacé par son passage unique ; « $ 198.89 »).
**Confirmé le 2026-10-21** : au premier comité NVDA, la fourchette = central ± 1 pt du taux exigé, étiquetée « sensibilité au taux » (scénarios sur risques après le comité, M6).
**PROCHAIN PAS — lots de construction, Opus spécifie, Sonnet exécute** :
(1) ✅ **B3/M1 livré le 2026-10-21** (spec `10-lot-M1-catalogue-et-contrats.md`) : référentiel
`app/frameworks/modele_entreprise.yaml` (version propre, 21 fiches, 2 familles, 3 patrons), contrat
`modele_entreprise_schema.py`, module `app/modele_entreprise/` (pont, contrôles, `appliquer_scenario` NON
branchée — M7), migration 061 appliquée, `seuil_de_materialite` au référentiel ;
`questions_sources_applicables()` = l'entrée de la porte (M3) ; (2) ✅ **B2/M2 livré le 2026-10-21** (`11-lot-M2-ventilation-publiee.md`) : `knowledge/ventilation*.py` + `ventilation_publiee.yaml`,
pièce `ventilation_publiee` SANS appelant en production (son lecteur = l'architecte), outil `montrer_ventilation.sh` ;
**déployé le 2026-10-22** (`67f7e87`, vérifié dans le conteneur). NVDA a redécoupé ses
marchés au 10-Q (Data Center = Hyperscale + AI Clouds/Industrial/Enterprise ; Edge Computing) : matière directe pour M3 ;
(3) ✅ **B4/M3 livré et DÉPLOYÉ le 2026-10-22** (`12-lot-M3-architecte.md`, `1d5dfbf` ; migration 062 appliquée ; `check_architecture_persist` 10/0 contre la vraie base). **PROCHAIN PAS = exécuter M3 bis** (`13-lot-M3bis-structure.md`, Sonnet exécute, Opus vérifie par exécution) : [S10] membre publié déguisé en estimé, [S11] cadrage des formules, contrat 1.2.0 (jalon des programmes, manques du dossier) ; arbitrage réservé §6 (question « inventaire des programmes », après le comité NVDA) (architecte ; arbitrés le 22/10 : horizon 10 exercices ; réponse refusée = porte fermée, sauf phase de test — interrupteur `porte_admet_reponses_refusees` à basculer à `false` AVANT le premier comité réel) — porte de NVDA **ouverte** au catalogue 1.0.0 (mesuré, voir ci-dessous) : plus de relance
préalable ; ma_3/ma_4/A1 restent dans D1. C2 sans objet, C5 vérifié (≈ 5,55 $, à re-mesurer).
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
- **Suite** `bash backend/checks/run_all.sh` verte (2026-10-21, après M2 : 70 checks, 5473 assertions ; `negatif_ventilation_publiee.sh` 14/0, `negatif_ventilation_persist.sh` 3/0).
- **Production** : dernier déploiement `1d5dfbf` (M3, backend, 2026-10-22) ; avant, `67f7e87` (M2) ; `4c6d37e` (M1), vérifié dans le conteneur (référentiel 1.0.0 chargé, 21 fiches, seuil 10). Migration 061 appliquée. Mandats : 1 manager ouvert (2918).
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
