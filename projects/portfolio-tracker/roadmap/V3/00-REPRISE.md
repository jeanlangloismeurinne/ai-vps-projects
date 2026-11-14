---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-14 (M1 construit et prouvé hors ligne, à accepter sur le VPS ; puis M2)
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

**PASSER L'ACCEPTATION DE M1 SUR LE VPS, PUIS OUVRIR M2 « COLLECTE DE SOURCES ».** M1 « Fiche de
l'émetteur et sources » est construit (`backend/app/modules/emetteurs/`, son `ARCHITECTURE.md` dit ce
qu'il fait et ce qui manque) et prouvé hors ligne et sur une base PostgreSQL locale, **pas accepté** :
les lignes A13-A15 de `M1-fiche-emetteur.md` exigent NVDA, RVMD et la vraie base.

### À vérifier sur le VPS (dans cet ordre ; rien n'a été déployé ni appliqué)

1. **Suite de référence avant tout** : `bash backend/checks/run_all.sh` (réécrit `checks/LIGNE_DE_BASE.md` ;
   `check_emetteurs_persist` y sort en ÉCHEC NOMMÉ tant que la 063 n'est pas appliquée : attendu).
   Puis depuis `backend/` : `bash checks/negatif_chef_de_dossier.sh`, `negatif_charte_modules.sh`,
   `negatif_architecture.sh` (ce dernier exige le conteneur : jamais joué hors VPS), `negatif_emetteurs.sh`.
2. **Migration 063, d'abord en négatif** : `bash checks/negatif_emetteurs_persist.sh` (partie 2 : base
   jetable `db_063_neg`, la 063 n'est pas appliquée à la vraie base par ce script ; la partie 1 exige la
   063 appliquée : la rejouer après). Vérifier que le rôle `portfolio_user` et les droits par défaut
   (#15) se comportent comme en local. Puis appliquer (convention #17) :
   `docker cp backend/app/db/migrations/063_v3_emetteurs_et_chef_de_dossier.sql shared-postgres:/tmp/ &&
   docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/063_v3_emetteurs_et_chef_de_dossier.sql`,
   puis `bash checks/avec_base.sh check_emetteurs_persist` et de nouveau le négatif.
3. **Reprise des données** : relire `backend/app/db/seeds/emetteurs_reprise_2026-11-13.json` — **saisis à
   la main, à confirmer** : les trois raisons sociales (comparer à `tickers.name` et au registre de la
   SEC), les trois numéros (MSFT 789019 n'a aucune trace dans le dépôt), les pages de relations
   investisseurs (`investor.nvidia.com`, `microsoft.com/investor`, `ir.revmed.com`, `revmed.com/investors`).
   Puis `bash tools/emetteurs.sh importer app/db/seeds/emetteurs_reprise_2026-11-13.json --a-blanc`,
   lire la sortie, rejouer sans `--a-blanc`, `bash tools/emetteurs.sh montrer`.
4. **A14** : `bash tools/emetteurs.sh comparer NVDA NVDA` et `… comparer RVMD RVMD` (lecture seule) —
   chaque écart de niveau entre l'ancien code et la fiche, sur les adresses des pièces réelles, est à
   expliquer (deux écarts sont voulus : `check_emetteurs_reprise.py` [R4], [R5]). L'outil suppose les
   colonnes `source_url`, `nature`, `ticker_id` de `knowledge_entries` : jamais exécuté sur la vraie base.
5. **A13, l'écran** : déployer backend puis frontend (`infrastructure/compose-deploy.sh portfolio-backend …`
   — ⚠️ le dépôt porte aussi les lots B4d, #143, B4f, B4g « à ne pas déployer » : vérifier ce que le
   déploiement embarquerait avant de le lancer, et arbitrer avec l'utilisateur s'il les embarque).
   Ouvrir `/v2/emetteurs` et `/v2/emetteurs/RVMD` ; essayer une admission, une révocation, « tester une
   adresse ». L'écran n'a été ouvert qu'ici, contre une base locale (rendu correct, lignes du journal hautes).
6. **A15, le jour de l'acceptation** : faire lire la fiche à l'ancien code (`websearch`, `source_registry`,
   `service.store_knowledge`, `worker`), supprimer `_ISSUER_DOMAINS`, les quatre listes de domaines,
   `_ADMISES`, `_TICKER_SECTEURS`, `qualify` et `check_emetteurs_reprise.py` ; suite complète verte ;
   cocher M1 au plan, archiver `M1-fiche-emetteur.md`.

### À trancher avec l'utilisateur (en termes de fonds, avant ou pendant l'acceptation)

- **Qui signe la reprise ?** Les 33 sources que l'ancien système tenait pour fiables sans date ni motif
  (régulateurs, presse financière, cabinets d'études) entrent au journal comme admises « par le système,
  reprise de l'ancien code » : l'utilisateur peut donc les révoquer, et le système ne pourra pas les
  rétablir. Les 4 publications de biotechnologie du 2026-09-05 y entrent à son nom. Est-ce la bonne lecture ?
- **Une page « investisseurs » d'une autre société** (un concurrent, un client) valait le niveau le plus
  haut dans l'ancien système par la seule forme de son adresse ; avec la fiche, elle n'est admise que si
  on l'inscrit. Plus prudent, mais des pièces déjà collectées chez des concurrents redescendraient.
- **Le pays** est repris « US » pour les trois titres : l'ancien système ne le portait nulle part.

### Ensuite : M2 « Collecte de sources »

Tri de `knowledge/edgar_feed.py`, `websearch.py`, `agents/v2/collecte_executor.py` ; acceptation écrite
avant. Deux questions arrivent avec lui : **l'évaluateur de sources inconnues** (M1 tient la porte :
critère écrit, rôle distinct du collecteur, journal ; aucun évaluateur n'existe) et **les pas
asynchrones** (l'automate du chef de dossier est synchrone : `chef_de_dossier/ARCHITECTURE.md`).

**M0 « Fondations » : ACCEPTÉ hors ligne le 2026-11-13** (récit : archive, « 2026-11-13 — M0 »).

**Direction** (arbitrée et CONFIRMÉE le 2026-11-13 ; tableau : `EVALUATION-ARCHITECTURE-2026-11-13.md`
§ « Arbitrages rendus ») : reconstruction module par module sur une base propre, l'ancien code est une
carrière ; ordre M0-M11 accepté ; kit de spécialité accepté (sans kit : parcours généraliste) ;
contradicteur après le premier comité ; c'est l'utilisateur qui dit quoi analyser. **Aucune mesure
payante avant le module M6 (carte).**

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
- Chef de dossier : rangement en base écrit (migration 063, non appliquée) ; toujours ni déclencheur ni
  geste à l'écran (lever une pause, enregistrer un acte) ; automate synchrone, à trancher à M2.
- L'écran de M1 n'a pas de test négatif (`check_emetteurs_api.py`) : à écrire avant l'acceptation.

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
- **Production** : dernier déploiement `d504d96` ; lots B4d, #143, B4f, B4g commités et **à ne pas déployer** (remplacés par la reconstruction). Migration 062 appliquée. Détail des déploiements et porte de l'architecte NVDA : archive, « 2026-11-13 — sortis de la reprise ».
- **Migration 063 ÉCRITE, NON APPLIQUÉE** (fiches des émetteurs, journal des sources, état des dossiers) ; la suivante sera 064 (062 = PV de l'architecture, appliquée le 2026-10-22 ; 061 = registres du classeur : architectures, fourchettes, scénarios, déplacements ; 060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
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
