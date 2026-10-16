---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-16 (allègement : état complet copié dans 00-REPRISE-ARCHIVE.md, section « 2026-10-16 — COPIE CONFORME »)
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

Ordre de l'inventaire `07-avant-comite.md` **validé le 2026-10-16** (il remplace la checklist A4-A11 de
`05-frameworks-complets.md`) : (1) la matière — 1.1 ✅ (#133), 1.2 ✅ (#134, ce n'était pas la langue),
**1.4 instabilité du collecteur (PROCHAIN — mesurer d'abord)**, 1.6 « tout chiffre renvoie à une pièce » ;
(2) arbitrages groupés en une séance (9, 10, 11, 12, 15, 17, 20, 21) ; (3) tenue du dossier ; (4) valorisation ;
(5) test. Modèle : Opus pour la conception, Sonnet délégué pour les mesures et l'exécution bien spécifiée.

## Où on en est (mesuré le 2026-10-16 — RE-REQUÊTER avant de s'en servir)

- **Jalon** : note d'initiation (6 chapitres + fourchette) sur 3-4 titres très différents, fonctionnement
  ET reproductibilité ; roadmap active `05-frameworks-complets.md` (A1-A3 cochés, A4 en cours).
- **Chapitres instruits** (`bash backend/tools/montrer_parcours.sh <TICKER>`, gratuit) :
  NVDA qualité financière 1,00 · défendabilité 0,17 · modèle économique 0,83 · secteur 0,50 ·
  management **2/7** (ma_6, ma_7 répondues — plan #270, réponses #1499-#1505 ; ma_4 #1506) · valorisation :
  rien. RVMD : qualité financière 1,00, défendabilité/modèle économique/secteur/management partiels.
  **MSFT : aucune réponse en vigueur.** Beaucoup de réponses sont « standard antérieur » (#127) : refaites
  à la reconstruction (premier passage du test), pas relues d'ici là.
- **Suite** `bash backend/checks/run_all.sh` = **4712/0** (2026-10-16, après #134).
- **Production** : dernier déploiement (#134), vérifié dans le conteneur.
- **Prochaine migration : 058** (056/057 = prompt search-worker v5/v6 : source d'origine, `chercher`). Catalogue d'événements **1.6.0** ; notes flash 1.6.0 : RVMD #613-#622,
  NVDA #623-#628, MSFT #629-#633.
- **Réglage `v2_auto_enabled` = FALSE** (le matin ne fait que recenser). Crédit DeepInfra : vérifier par
  un appel minimal avant toute grosse dépense.

## Arbitrages récents (le détail : `CONVENTIONS.md` #129-#132, `06-regle-fraicheur.md` §8-§14)

- **2026-10-16** — mo_5/se_3 ne sont plus rouvertes par un dérapage d'exécution ; ma_4 scindée (argent en
  jeu des dirigeants = mesure / ma_7 critères de rémunération = jugement à plancher A) (#131) ; source :
  **d'abord le site de l'émetteur, à défaut ailleurs** (à construire) ; **la règle « une ré-analyse
  n'entre en vigueur que si au moins aussi fondée » est ÉCARTÉE** — la dégradation par ré-analyse reste
  une dette, à repenser (07 §3.13).
- **2026-10-16** — fraîcheur par durée de vie des ingrédients (#129) ; table des causes de révision
  (#130) ; lecture fiabilisée des communiqués de résultats (vote de 3 lectures).
- Arbitrages plus anciens (périmètre EDGAR seul, « on rachète tout » en test, ajouter une méthodologie =
  opération de données, valorisation option (c), encadré de chiffres clés, signature du comité…) :
  archive, section COPIE CONFORME, « Arbitrages de l'utilisateur qui commandent la suite ».

## Outils (tous dans `backend/tools/`, gratuits sauf mention)

- `montrer_parcours.sh TICKER` (dossier, manques, notes de qualité) · `montrer_socle.sh TICKER…` (comptes
  reconstitués) · `recouper_nombres.sh TICKER framework` (chaque nombre d'une réponse retrouvé dans ses
  pièces) · `acceptation_analyste.sh --admissibilite` avec `ACCEPTATION_CAS=TICKER:framework:archetype`
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

`05-frameworks-complets.md` (roadmap active) · `07-avant-comite.md` (inventaire) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
