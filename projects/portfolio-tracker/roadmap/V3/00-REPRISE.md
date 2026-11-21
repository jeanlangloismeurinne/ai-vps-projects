---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-21 nuit (déclencheur `etude` et besoins `comptes` construits hors ligne ; prochain lot : bases 065, tâche planifiée, écran) — historique des mises à jour : `git log` de ce fichier
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

**Où on en est (2026-11-21 soir)** — rien de M2, M3 ni du déclencheur n'est déployé ; tout est prouvé
hors ligne sur société fictive :
- **M2 collecte** (`app/modules/recueil/`) : `check_recueil` 63/0, négatif 43/43 ; moteur Exa, modèle
  DeepInfra, évaluateur réel (`check_recueil_evaluateur` 101/0, négatif 80/80) ; migration **064 NON
  appliquée**. Détail : `M2-collecte-sources.md`.
- **M3 lecture et pièces** (`app/modules/connaissance/`) : `check_connaissance` 49/0, négatif 30/30.
- **Déclencheur** (`app/modules/etude/`, construit ce soir) et **besoins** (`app/modules/comptes/`,
  ouvert au registre avec son seul besoin : dernier annuel + données structurées) : `check_etude`
  39/0, négatif 31/31. Mettre à l'étude (fiche exigée) ; passage = relever (payant, jamais sur un
  dossier en pause) → lire → avancer et ranger l'état et ce qu'il lance dans UNE transaction ; verrou
  par dossier ; relecture humaine en donnée (`etude/referentiel.json`) : **un seul arrêt, valider les
  documents collectés** (arbitrage du 2026-11-21). Le chef de dossier expose ses gestes par son
  contrat et accepte un interrupteur par pas (chef 108/0, négatif 27/27). Détail : M3 §5.

**Prochain lot (Sonnet suffit : le modèle existe en M1/M2, critère énonçable)** : (1) rangement en base
de M3 (tables `connaissance_*`, migration **065**) et du déclencheur (tables `etude_*` : études en ajout
seul, passages, verrou par dossier = `pg_try_advisory_lock` de session ; même migration 065 ou 066) —
prouvés sur base jetable avec ROLLBACK (K5, K10 « base »), comme `check_recueil_persist` ; (2) la tâche
planifiée (APScheduler de `app/main.py`, toutes les quelques minutes) qui construit le `Monde` (une
connexion, `outils_reels`, `evaluateur_reel`, clefs du service) et appelle
`etude.traiter_les_dossiers` ; (3) écran (B12/K12 : bouton « mettre à l'étude » sur la page de
l'émetteur, documents, pièces, état du dossier, gestes acte / pause / relance — libellé de l'acte en
mots de gérant : « valider les documents trouvés ou introuvables ») ; (4) appliquer 064+065(+066),
déployer, lignes « réel » (K13 : 57 fiches SEC de l'ancien système retrouvées ; K14 : NVDA, RVMD,
SpaceX ; M2 B3/B6/B10/B13). Les demandes « au fil du dossier » (M3 §2, 1 bis) se construisent avec
M4. Un dossier terminé ne repart pas quand le parcours s'allonge : à traiter avec M4.

**SpaceX** (fiche en production : révision 1, « SPCX », rien d'autre) : NE PAS la compléter à la main ;
le vrai passage l'écrira, signé du système (passage à blanc du 2026-11-16 : identité complète,
prospectus 424B4 du 2026-06-12 pour « derniers comptes annuels »).

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
- Chef de dossier : rangement en base (migration 063, appliquée le 2026-11-16) ; toujours ni déclencheur ni
  geste à l'écran (lever une pause, enregistrer un acte, relancer). Le déclencheur se construit avec M2
  (il range l'`Envoi` des pas de collecte dans la même transaction que l'état du dossier).

## Où on en est (mesuré le 2026-10-16/17 — RE-REQUÊTER avant de s'en servir)

- **Jalon** (réduit le 2026-10-17 : **NVDA + RVMD** d'abord, puis financière US, puis étranger, MSFT en
  contrôle de reproduction) : note d'initiation (6 chapitres + fourchette), fonctionnement
  ET reproductibilité ; **roadmap active : `07-avant-comite.md`** (modules M0-M11) ; `roadmap/archive/V3-05-frameworks-complets.md` = ancien détail (archivé).
- **Chapitres instruits de l'ancien enchaînement** (NVDA, RVMD, MSFT, mesurés le 2026-10-16/17) : archive, « 2026-11-21 — sorti de la reprise » ; ils ne sont pas repris (charte 7).
- **Suite** `bash backend/checks/run_all.sh` : total, date et commit du dernier passage dans `backend/checks/LIGNE_DE_BASE.md` (écrit par le lanceur — seule source du chiffre, ne pas le recopier ici). Négatifs (2026-10-23, après B4f : explorateur 5/5, architecte 51/51, modèle 71/71, architecture 6/6, périmètre 32/32, ventilation 19/19 — les négatifs se lancent DEPUIS `backend/`).
- **Production** : rebuild de sécurité du 31/10 (`46a663f`) — embarque B4d, #143, B4f, B4g et le maillon 1 (vérifié fichier par fichier le 2026-11-16) ; M1 pas encore déployé. Migration 062 appliquée. Détail des déploiements et porte de l'architecte NVDA : archive, « 2026-11-13 — sortis de la reprise ».
- **Migration 063 APPLIQUÉE le 2026-11-16** (fiches des émetteurs, journal des sources avec évaluations et mises en suspens, état des dossiers) ; la suivante sera 064, réservée aux tables `recueil_*` de M2 (062 = PV de l'architecture, appliquée le 2026-10-22 ; 061 = registres du classeur : architectures, fourchettes, scénarios, déplacements ; 060 = geste `retablir` au PV ; 059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
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
