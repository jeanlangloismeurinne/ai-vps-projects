---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-11-21 soir (M3 ouvert et construit hors ligne : lecteur, pièces, recherche ; question à l'utilisateur sur la lecture humaine) ; 2026-11-21 (texte du moteur coupé en cours de phrase : suivi avant le modèle, M2 §8, accord de l'utilisateur) ; 2026-11-19 (presse payante : étages 1 et 2 construits, #149 ; DeepInfra : flex, cache, numéros ; question ouverte : aperçu jugé complet) ; 2026-11-18 soir (grille 1.3.0 appliquée ; V4.1-Flash retenu ; règle « un aperçu n'est pas une publication » ; question ouverte : lire la presse payante) ; 2026-11-18 (M2 MOTEUR, MODÈLE ET ÉVALUATEUR RÉELS construits ; question à l'utilisateur sur la grille d'évaluation) ; 2026-11-16 (M2 RANGEMENT EN BASE construit, 064 non appliquée ; A15 « sans fiche » clos sans objet) ; 2026-11-16 (M2 CONSTRUIT HORS LIGNE : module recueil, B1-B11, passage à blanc SpaceX ; prochain pas : base, migration 064) ; 2026-11-16 (M2 OUVERT : tri + acceptation B1-B14, SpaceX cas réel ; questions à l'utilisateur) ; 2026-11-16 (M1 ACCEPTÉ sur le VPS : 063, reprise, A14, A15 — l'ancien code lit la fiche ; prochain pas M2) ; 2026-11-14 (deux arbitrages de M2 construits hors ligne : sources inconnues en suspens sous le seuil, dossier qui avance pendant une collecte ; reste l'acceptation de M1 sur le VPS, puis M2)
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

**M2 « COLLECTE DE SOURCES » : CONSTRUIT HORS LIGNE le 2026-11-16** — module `app/modules/recueil/`
(B1-B11 : `check_recueil.py` 63/0, `negatif_recueil.sh` 43/43 ; détail : `M2-collecte-sources.md` §5).
Rangement en base construit (migration **064 NON appliquée** ; `check_recueil_persist` rouge nommé au
VPS tant qu'elle ne l'est pas). **Moteur Exa, modèle DeepInfra et évaluateur réel construits le
2026-11-18** (`check_recueil_evaluateur.py` 53/0, négatif 38/38 ; essais réels en mémoire :
`tools/essai_evaluateur.sh <domaine>`).

Le 2026-11-19 (#149, presse payante : pièce d'origine ou reprise sous licence) : archive, « 2026-11-21 ».

**Fait le 2026-11-21** (accord de l'utilisateur) : un texte relu par le moteur qui s'arrête en cours de
phrase (pas seulement « en plein mot » : l'aperçu Visa réel finit sur « in the ») est suivi AVANT le
modèle ; sa reprise le remplace, sinon le modèle juge comme avant. `check_recueil_evaluateur` 101/0,
négatif 80/80. Essai réel : Lennar (Reuters) → reprise marketscreener avant le jugement. Détail : M2 §8.

**M3 OUVERT le 2026-11-21** (décision de l'utilisateur : tester la collecte sur un besoin réel) :
`M3-base-connaissance.md` (tri, interface « besoins → collecte », acceptation K1-K14, 3 questions
tranchées). **Construit hors ligne le même jour** : module `app/modules/connaissance/` — lecteur,
pièces, recherche par les mots, pas de lecture (`check_connaissance` 49/0, négatif 30/30). La
vérification d'un extrait (`citation.py`) vit désormais dans M3 (l'ancien chemin est un ré-export).

**Prochain pas (Opus)** : (1) ~~relecture humaine~~ **tranché le 2026-11-21** : le dossier
s'arrête une fois, après la collecte (l'utilisateur valide les documents trouvés ou introuvables) ; la
fiche (M1, acceptée) et la mise en lecture (M3, code sans modèle, contrôlée par K13) ne s'arrêtent
pas — interrupteurs par module (principe 3), à tenir en donnée ; (2) module `etude` : mettre à l'étude
(geste + table), passage du dossier (relever, lire, avancer, ranger dans une transaction ; rien de
payant sur un dossier en pause), tâche planifiée, besoins initiaux déclarés en donnée (module
`comptes` ouvert avec son seul besoin : le dernier annuel + données structurées) ; (3) rangement en
base de M3 (065) — Sonnet suffit, le modèle existe (M1/M2) ; (4) écran (B12/K12 : documents, pièces,
état du dossier, gestes acte / pause / relance) ; (5) appliquer 064+065, déployer, lignes « réel »
(K13 : 57 fiches SEC de l'ancien système retrouvées ; K14 : NVDA, RVMD, SpaceX ; M2 B3/B6/B10/B13).
Les demandes « au fil du dossier » (§2, 1 bis) se construisent avec M4, premier module qui en aura
besoin (pas de code sans appelant).

**SpaceX** (fiche en production : révision 1, « SPCX », rien d'autre) : NE PAS la compléter à la main.
Le passage à blanc en mémoire (2026-11-16, registre gratuit, aucune écriture) l'a complétée
correctement (« SPACE EXPLORATION TECHNOLOGIES CORP », 1181412, NASDAQ, US) et a rendu le prospectus
424B4 du 2026-06-12 pour « derniers comptes annuels ». Le vrai passage l'écrira, signé du système.

M1 accepté sur le VPS le 2026-11-16 (reste à l'écran : admettre, révoquer, corriger sur de vraies
décisions ; puis archiver `M1-fiche-emetteur.md`). M1 a gagné `completer_identite` (#147) — contrat
inchangé en 1.1.0 (la forme de la fiche ne change pas : monter la version rendrait illisibles les
fiches rangées). **Rien de M2 n'est déployé** : le module n'est appelé par aucune route ni tâche.

Écart « émetteur sans fiche = aucune source admise » (A15) : **sans objet, clos le 2026-11-16 par
l'utilisateur** — une société sans fiche n'est pas étudiée (le chef de dossier attend l'acte, A11 ; la
collecte M2 aussi, B2) ; seul l'ancien code pouvait le rencontrer, et il est remplacé. Les sources sur
les concurrents passent par la fiche de la société étudiée (`service.py`, `charger(conn, ticker_id)`).

Modèles pour M2 (utilisateur, 2026-11-16) : **Sonnet** pour le rangement en base (le modèle existe en
M1, critère en trois lignes) ; **Opus** pour l'évaluateur réel (sa consigne demande du jugement).

### Tranché le 2026-11-14 : sorti vers l'archive (« 2026-11-16 — sortis de la reprise ») ; règles : conventions #144-#146.

### M2 : le détail (tri, acceptation, ce qui reste ouvert) est dans `M2-collecte-sources.md`.

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
- **Chapitres instruits** (`bash backend/tools/montrer_parcours.sh <TICKER>`, gratuit) :
  NVDA qualité financière 1,00 · défendabilité 0,17 · modèle économique 0,83 · secteur 0,50 ·
  management **2/7** (ma_6, ma_7 répondues — plan #270, réponses #1499-#1505 ; ma_4 #1506) · valorisation :
  rien. RVMD : qualité financière 1,00, défendabilité/modèle économique/secteur/management partiels.
  **MSFT : aucune réponse en vigueur.** Beaucoup de réponses sont « standard antérieur » (#127) : refaites
  à la reconstruction (premier passage du test), pas relues d'ici là.
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
