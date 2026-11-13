---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-13 (M0 « Fondations » accepté hors ligne ; prochain pas : M1 ; historique : archive)
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

**OUVRIR LE MODULE M1 « FICHE DE L'ÉMETTEUR ET SOURCES »** (plan `07-avant-comite.md`). Dans l'ordre de la
charte (`principe-directeur.md` §2) : (1) le **tri** de l'ancien code — identité de l'émetteur, domaines des
sites, registre des sources, toute constante par société (une recherche déléguée a été coupée le 2026-11-13
par la limite de dépense du compte : à relancer) ; (2) l'**acceptation écrite avant** (ajouter un titre ne
modifie aucun fichier de code ; une société sans numéro SEC a une fiche valide ; une source révoquée signale
les pièces qui s'y appuient ; le module passe aussi SANS kit de spécialité) ; (3) la construction dans
`backend/app/modules/`, déclarée dans `registre.py`, avec son pas au chef de dossier. M1 a besoin d'une
table : prévoir la **migration 063** et, avec elle, le rangement en base de l'état du chef de dossier.

**À faire une fois sur le VPS avant M1** (M0 a été prouvé sur l'hôte d'un bac à sable, sans Docker ni base) :
`bash backend/checks/run_all.sh` (réécrit `checks/LIGNE_DE_BASE.md`), puis depuis `backend/` :
`bash checks/negatif_chef_de_dossier.sh`, `bash checks/negatif_charte_modules.sh`, `bash checks/negatif_architecture.sh`.
Rien n'est à déployer : M0 n'est appelé par rien en production.

**M0 « Fondations » : ACCEPTÉ hors ligne le 2026-11-13.** Chef de dossier (`app/modules/chef_de_dossier/`,
automate sans modèle : arrêt aux actes humains, pause tous les 1 $ avec coût restant, lecture humaine de
chaque sortie de module par défaut) ; charte et garde des accès (`app/modules/registre.py`,
`check_charte_modules.py`) ; constitution réécrite ; schéma des blocs ; documents de lots archivés ; une
seule ligne de base ; NASDAQ sorti du chantier. Récit : archive, « 2026-11-13 — M0 ».

**Direction** (arbitrée et CONFIRMÉE le 2026-11-13 ; tableau : `EVALUATION-ARCHITECTURE-2026-11-13.md`
§ « Arbitrages rendus ») : reconstruction module par module sur une base propre, l'ancien code est une
carrière ; ordre M0-M11 accepté ; kit de spécialité accepté (sans kit : parcours généraliste, assez souple
pour bien analyser l'entreprise) ; contradicteur après le premier comité ; c'est l'utilisateur qui dit quoi
analyser. **Aucune mesure payante avant le module M6 (carte).** Retenus sans objection exprimée : le contenu
du procès-verbal et les garde-fous de l'admission des sources.

## Reste ouvert (ne s'archive pas)

- L'ancien chantier « découpage » (B4g) est **clos sans suite** : ses acquis (inventaire, arbre, premier niveau
  par les segments) seront triés à l'ouverture de M6-M7. Lots B4d, #143, B4f, B4g commités, jamais déployés :
  **ne pas les déployer** (remplacés par la reconstruction). Récit : archive, « 2026-11-13 — arbitrages ».
- Dettes de l'ancien plan rattachées à leur module : plan 07, « Dettes reprises ».
- Orientations de l'utilisateur à reprendre en M6 : une ligne par source de cash-flow ; finesse selon la
  maturité ; probabilité de succès hors du découpage ; vocabulaire standard dans tous les prompts ; molécules
  précoces → plateforme sauf marché chiffrable.
- Interrupteur `porte_admet_reponses_refusees` : devient sans objet avec l'ancien architecte (à retirer à son tri).
- NASDAQ : sous-projet indépendant, hors chantier V3 — sa reprise : `backend/app/nasdaq/00-REPRISE-NASDAQ.md`.
- 26 contrôles sans test négatif à leur nom ; deux modèles épinglés dans le code : soldés module par module.
- `backend/tools/mesure_gate_capacite4.py` ne compile pas (erreur d'indentation, relevée par la garde des
  accès le 2026-11-13) : outil de l'ancien enchaînement, à supprimer ou réparer au tri de M6.
- Chef de dossier : ni rangement en base, ni écran, ni déclencheur (dit dans son `ARCHITECTURE.md`) : avec M1.

## Où on en est (mesuré le 2026-10-16/17 — RE-REQUÊTER avant de s'en servir)

- **Jalon** (réduit le 2026-10-17 : **NVDA + RVMD** d'abord, puis financière US, puis étranger, MSFT en
  contrôle de reproduction) : note d'initiation (6 chapitres + fourchette), fonctionnement
  ET reproductibilité ; **roadmap active : `07-avant-comite.md`** (modules M0-M11) ; `roadmap/archive/V3-05-frameworks-complets.md` = ancien détail (archivé).
- **Chapitres instruits** (`bash backend/tools/montrer_parcours.sh <TICKER>`, gratuit) :
  NVDA qualité financière 1,00 · défendabilité 0,17 · modèle économique 0,83 · secteur 0,50 ·
  management **2/7** (ma_6, ma_7 répondues — plan #270, réponses #1499-#1505 ; ma_4 #1506) · valorisation :
  rien. RVMD : qualité financière 1,00, défendabilité/modèle économique/secteur/management partiels.
  **MSFT : aucune réponse en vigueur.** Beaucoup de réponses sont « standard antérieur » (#127) : refaites
  à la reconstruction (premier passage du test), pas relues d'ici là.
- **Suite** `bash backend/checks/run_all.sh` : total, date et commit du dernier passage dans `backend/checks/LIGNE_DE_BASE.md` (écrit par le lanceur — seule source du chiffre, ne pas le recopier ici). Négatifs (2026-10-23, après B4f : explorateur 5/5, architecte 51/51, modèle 71/71, architecture 6/6, périmètre 32/32, ventilation 19/19 — les négatifs se lancent DEPUIS `backend/`).
- **Production** : B4d COMMITÉ (`7d08a6d`) mais NON DÉPLOYÉ (déploiement refusé par le classifieur le 2026-10-23 — à lancer par l’utilisateur, puis `docker exec portfolio-backend grep -c "architecture-1.3.0" /app/app/contracts/modele_entreprise_schema.py`) ; dernier déploiement `d504d96` (correctif DEF 14A) ; avant, P1 complet (`f6b5659`) ; avant, M3 bis (`1f9a364`) ; avant, `1d5dfbf` (M3) ; avant, `67f7e87` (M2) ; `4c6d37e` (M1), vérifié dans le conteneur (référentiel 1.0.0 chargé, 21 fiches, seuil 10). Migration 061 appliquée. Mandats : 1 manager ouvert (2918).
- **Porte de l'architecte NVDA — mesurée le 2026-10-21** (`montrer_parcours.sh NVDA`) : les 12 questions sources d'une rentable (me_2-me_5, mo_4, mo_6, qf_1, qf_3, qf_7, se_2-se_4) ont toutes une première réponse instruite (mo_4 recherche épuisée, mo_6/se_2 pièces insuffisantes = information, 09 §11.2) → ouverte ; 22 manques au total, inchangés.
- **Prochaine migration : 063** (062 = PV de l'architecture, appliquée le 2026-10-22 ; 061 = registres du classeur : architectures, fourchettes, scénarios, déplacements ; 060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
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

`07-avant-comite.md` (LE plan : modules M0-M11) · `EVALUATION-ARCHITECTURE-2026-11-13.md` (audit, cible en blocs, arbitrages rendus) · `roadmap/archive/V3-05-frameworks-complets.md` (ancien détail) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
