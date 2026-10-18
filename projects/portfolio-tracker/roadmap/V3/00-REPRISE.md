---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-10-18 (demandes de recherche closes à la livraison, point 14, `8af6f4a` ; causes du point 13) ; 2026-10-18 (fraîcheur sujet par sujet, point 15, `331aa7c`) ; 2026-10-18 (changement de stade + classement par le comité, #139) ; 2026-10-18 (« pas encore observable », #138) ; 2026-10-17 (relance bornée + réinitialisation, `c2bc1af`) ; 2026-10-17 (séance d'arbitrages #137) ; 2026-10-16 (allègement : état complet copié dans 00-REPRISE-ARCHIVE.md, section « 2026-10-16 — COPIE CONFORME »)
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

Ordre de `07-avant-comite.md` : (1) la matière — **close** ; (2) arbitrages — **rendus** (#137) ; (3) **tenue du
dossier — EN COURS**, ordre validé par l'utilisateur le 2026-10-17 :
(a) ✅ **relance bornée + réinitialisation** (fait le 2026-10-17, `c2bc1af`, migration 058 — CONVENTIONS #137
« CONSTRUIT ») ; (b) ✅ **fraîcheur sujet par sujet (15)** (fait le 2026-10-18, `331aa7c` — CONVENTIONS #137
« CONSTRUIT le 2026-10-18 ») ; (c) ✅ **mandats clos à la livraison (14)** (fait le 2026-10-18, `8af6f4a`) ; **ré-analyse qui dégrade (13) — EN COURS** ; (d) données : ma_2 reformulée
(12), taux exigé 10 % (10), me_5 → liste des marchés visés (9) ; (e) mesurer « répondu sans le chiffre-objet »
(11, cas qf_6) ; puis (4) valorisation, (5) test. **Jalon 1 = NVDA + RVMD** ; code générique. Modèle : Opus pour
la conception, Sonnet délégué pour les mesures et l'exécution bien spécifiée.
**Relancer un chapitre** : `executer_chaine.sh` ne refait plus que l'ouvert (imprime ouvertes/closes et pourquoi) ;
la reconstruction du test (#127) = remise à zéro du chapitre (niveau 2, bouton, tracée au PV) PUIS relance.
RVMD reclassée « commerciale » (pièce #944), qualité financière RVMD 8/8 à jour ; les autres chapitres RVMD
attendent le 10-Q du T3. Récit #138/#139 et point 15 : archive, section « 2026-10-18 — sortis à la clôture du point 14 ».
**Point 14 CONSTRUIT le 2026-10-18** (`8af6f4a`, CONVENTIONS #137) : une réponse écrite sert la demande
ouverte de sa question ; un refus d'agent n'en ouvre plus ; rattrapage 983-986, 2849 appliqué (2918 RVMD se_3
reste ouvert à bon droit). **PROCHAIN PAS : point 13** — causes établies (07 §3.13 : NVDA = titre de pièce qui
promet 5 ans pour 1 exercice, défaut ACTIF ; RVMD = bug #100 corrigé par #101) ; à faire : (i) corriger le titre
des fiches du relevé (période mesurée, jamais le libellé demandé) ; (ii) arbitrage de la règle de gouvernance
(options posées : signaler + rétablir / même pièces = en attente / geste seul) — réponse de l'utilisateur attendue. Dettes
nommées : l'outil d'acceptation ne remet pas le socle ni les lectures (n'est pas la chaîne) ; autres
questions dont le verdict lit un seul chiffre à recenser (`sens_lu_sur`, seuls qf_3/qf_5 déclarés).
⚠️ Les lanceurs `acceptation_analyste.sh`, `executer_chaine.sh`, `boucler_renvois.sh`, `montrer_dossier.sh`
ne transmettaient PAS leurs variables d'environnement au conteneur avant le 2026-10-18.

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
- **Suite** `bash backend/checks/run_all.sh` verte (2026-10-18, après le point 14 : 65 checks, 4973 assertions ; négatifs framework_persist 8/0, bouclage 12/0, executer_chaine 3/0).
- **Périmètre d'une relance** (2026-10-17, `questions_a_relancer`, lecture seule) : NVDA 22 ouvertes (qualité
  financière : 0, tout est à jour), RVMD 27. **RVMD qualité financière : ses 4 réponses sont désormais
  PÉRIMÉES** (fait publié depuis — à regarder avec le point 15). PV du comité : **0 décision** en base.
- **Chiffres sans pièce (#136)** : 19 sur les réponses en vigueur NVDA+RVMD (`montrer_parcours.sh`, colonne
  « sans pièce ») ; NVDA me_6 refaite (#1597, 0 sans pièce — mais comptes clients cités sur la mauvaise pièce).
- **Production** : dernier déploiement `8af6f4a` (point 14), vérifié dans le conteneur (un seul conteneur) et au dossier RVMD (plus de « repartie en recherche » sur mo_1/mo_3/mo_4). Mandats : 5 servis, 1 manager ouvert (2918).
- **Prochaine migration : 060** (059 = classement décidé par le comité ; 058 = geste `reinitialiser` au PV ; 056/057 = prompt search-worker v5/v6). Catalogue d'événements **1.7.0** ; notes flash 1.7.0 : RVMD #730-#739,
  NVDA #740-#745, MSFT #746-#750.
- **Réglage `v2_auto_enabled` = FALSE** (le matin ne fait que recenser). Crédit DeepInfra : vérifier par
  un appel minimal avant toute grosse dépense.

## Arbitrages récents (le détail : `CONVENTIONS.md` #129-#139 ; #129/#130 : fraîcheur par durée de vie, causes de révision, `06-regle-fraicheur.md` §8-§14)

- **2026-10-18** — **changement de stade** (#139) : le système détecte et RECOMMANDE, le comité reclasse
  ou maintient ; table de réouverture validée ; les pairs : même marché ou analogue, un changement de stade
  pose la question sans la trancher. Seule la qualité financière RVMD se relance avant le 10-Q du T3.
- **2026-10-17** — séance groupée (#137) : marchés visés listés, **estimation interne d'abord** (bac à
  calcul) ; **taux exigé unique 10 %**, sensibilité ±1 pt, risque propre dans les scénarios ; défaut du comité
  annoté, repris à la reconstruction ; ma_2 sur indices observables ; fraîcheur = pièce la plus récente par
  sujet ; relance bornée + réinitialisation par l'utilisateur ; RVMD reclassée au 1er trimestre de ventes.

- **2026-10-16** — tout chiffre renvoie à une pièce (#136) ; ma_4 scindée, mo_5/se_3 hors dérapage (#131) :
  détail dans `CONVENTIONS.md` et l'archive (section du 2026-10-18).
- Arbitrages plus anciens (périmètre EDGAR seul, « on rachète tout » en test, ajouter une méthodologie =
  opération de données, valorisation option (c), encadré de chiffres clés, signature du comité…) :
  archive, section COPIE CONFORME, « Arbitrages de l'utilisateur qui commandent la suite ».

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

`05-frameworks-complets.md` (roadmap active) · `07-avant-comite.md` (inventaire) · `03-spec-frameworks.md`
§1/§2/§4 (spec, tableaux des questions) · `06-regle-fraicheur.md` (fraîcheur) · `04-taxonomie-evenements.md`
· `principe-directeur.md` · `doctrine-trois-axes.md` · `METHODE-TEST.md` · `ARCHITECTURE-CIBLE.md` + les
`ARCHITECTURE.md` de module · `00-REPRISE-ARCHIVE.md` quand le *pourquoi* manque.
