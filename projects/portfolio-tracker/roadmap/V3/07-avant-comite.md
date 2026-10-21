---
id: plan-avant-comite
status: plan-d-action-2026-10-21
created: 2026-10-16
updated: 2026-10-21 (devient l'UNIQUE plan d'action avant comité ; cible : premier passage de NVDA ; réplicabilité posée en exigence ; passage au standard repoussé en ultime étape)
project: portfolio-tracker
role: >
  LE plan d'action avant le premier passage en comité d'un titre complet. Une seule version : ce
  fichier. Il remplace l'inventaire du 2026-10-16 (sujets 1-23), dont chaque sujet est soit soldé
  (section « Soldé »), soit repris ci-dessous sous un identifiant neuf (ex-n° entre parenthèses).
  La roadmap `05-frameworks-complets.md` garde le détail des capacités ; l'ORDRE se lit ici.
---

# Avant le comité — plan d'action

## Cible (arbitrage de l'utilisateur, 2026-10-21)

**Premier passage en comité de NVDA, dossier complet** : les six chapitres instruits et lus, une
fourchette de valeur signée, une décision consignée au procès-verbal. RVMD, MSFT, une financière et
un émetteur étranger suivent (section « Après le premier comité »).

**Exigence de réplicabilité** (posée le 2026-10-21) : « on construit un système qui doit s'appliquer
ensuite à des entreprises très différentes ». Donc, pour CHAQUE lot :
- ce qui change d'une entreprise à l'autre est une **donnée** (méthodologie, onglets du modèle,
  découpage en activités, sources), jamais du code propre à NVDA ;
- la spec dit comment le lot s'appliquerait à **RVMD** (somme des programmes pondérés par leur
  probabilité de succès) et à une **financière** (bilan qui est l'outil de production), au moins sur
  le papier ; l'acceptation du modèle de l'entreprise porte sur NVDA ET RVMD (05 §4 bis) ;
- contrôle : aucune constante propre à un titre dans le code livré (grep du ticker, des noms de
  segments).

*Ce que ferait un vrai fonds* : des gabarits maison communs à tout le portefeuille, que l'analyste
remplit avec les feuilles propres à l'entreprise ; le directeur de la recherche refuse un modèle qui
ne vaut que pour un titre.

**Passage au standard (ex-8, #127) repoussé en ultime étape** (arbitrage du 2026-10-21) : les
nouvelles collectes sont faites au nouveau standard, elles suffisent à valider le fonctionnement ;
les 11 réponses NVDA au standard antérieur sont refaites juste avant la séance (F1).

Légende — **Qui** : *Opus* conçoit et juge ; *Sonnet* exécute une spec écrite ou mesure ;
*Vous* arbitrez ou siégez. **Nature** : [A] arbitrage · [C] construction · [P] passage payant.

## État mesuré le 2026-10-21 (gratuit, `montrer_parcours.sh`, `recouper_nombres.sh`, admissibilité à blanc)

NVDA : 22 questions applicables sans réponse qui tienne — défendabilité 5 (mo_1-3 périmées par le
8-K du 2026-09-02, mo_4, mo_6), modèle économique 1 (me_6), secteur 3 (se_2, se_5, se_6), management
7/7, valorisation 6/6. Pour les 15 hors valorisation et hors ma_1/ma_3/ma_4, le corpus permet une
réponse. 12 chiffres non recoupés à leurs pièces (me 6, qf 2, mo 2). 11 réponses au standard
antérieur. Le socle ne connaît que le consolidé (aucun chiffre par activité). 9 questions sur 33
seulement ont un encadré de chiffres clés ; la valorisation n'en a aucun. L'atelier de valorisation
n'a pas d'écran ; la page « décision » lit encore l'ancienne thèse V2.

## A. Arbitrage restant

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| A1 | (ex-5) **Le cours au moment des rachats** (ma_3) : un fonds le prend dans sa base de marché. Le système doit-il avoir une source d'historique de cours, ou le web suffit-il ? Mesuré le 2026-10-21 : le collecteur TROUVE le cours au web (« $198.89 »), c'est la règle de C1 qui le refuse. | [A] | Vous |

## B. La valorisation — le modèle de l'entreprise (ex-9, ex-18 ; 05 A6 et §4 bis ; spec `09-modele-entreprise.md`)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| B1 | ✅ **Spec v2 le 2026-10-21** après arbitrages : architecte dédié, modèle vivant, deux signatures (interrupteur, cible : une seule), scénarios construits sur un inventaire de variables, détail plus fin que la publication mais agrégé au format des comptes. Arbitrages de la v2 rendus le même jour : seuil de matérialité 10 % de la valeur centrale (décision du fonds) ; l'architecte passe dès que chaque question liée à une variable du classeur a une première réponse (porte calculée, §11). | [C] | Opus → Vous |
| B2 | (M0 ✅, M2) La ventilation publiée au socle (segments, marchés, géographie) — mesurée faisable et générique. | [C] | Sonnet sur spec |
| B3 | ✅ **2026-10-21** (spec `10-lot-M1-catalogue-et-contrats.md`, migration 061). (M1) Catalogue de variables (fiche avec `familles` et `methode_de_fourchette`), patrons de départ, format agrégé = gabarit de la famille du titre ; contrats `Architecture`, `Cellule`, `Fourchette`, `Scenario`, `Deplacement` (central seul peuplé, 09 §12.2) ; gardes. | [C] | Opus spec → Sonnet |
| B4 | (M3) L'agent architecte, sa porte (première réponse sur chaque question source), ses contrôles de structure, la signature de l'architecture (interrupteur). | [C] | Opus spec → Sonnet |
| B5 | (M4, M5) Demandes ciblées par cellule ; projection des encadrés existants ; agrégé historique + projection au format du socle. | [C] | Opus spec → Sonnet |
| B6 | (M6) **Reporté après le premier comité** (commentaire du 2026-10-21, 09 §12.2) : fourchettes bas/central/haut par méthode du catalogue, inventaire, matérialité, constructeur de scénarios et son repli. Au premier comité : scénario central + ±1 pt du taux exigé (à confirmer). | [C] | Opus spec → Sonnet |
| B7 | (M7) L'agent de valorisation sur le classeur ; va_4-6 au dernier cours coté (#81) ; Greenwald ; ±1 pt du taux ; alerte d'échéance du taux (2027-10-17) ; rouvrir va_1/va_2 rouvre va_6. | [C] | Opus → Sonnet |
| B8 | (M8) Acceptation : NVDA (activités) et RVMD (programmes) donnent chacun une fourchette ; changer une hypothèse recalcule sans appel modèle ; au cours du jour, va_6 bouge sans va_2. | [P] | Sonnet lance, Opus lit |

## C. Correctifs avant les relances (tous génériques)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| C1 | ✅ **2026-10-21** (#141) : l'extrait court est remplacé par son passage du document s'il y est unique (sa ligne de tableau, sa phrase), refusé s'il est ambigu ; « $ 198.89 » = « $198.89 ». ⚠️ Les échecs de ma_3/ma_4 (16/10, 14:43-14:49) précédaient #135 (17:36) : depuis, l'extrait court ne faisait plus que retirer la fiche porteuse. Ancien énoncé : un cours ou un intitulé (« $198.89 », « X Director ») fait tomber ma_3 et ma_4. | [C] | Opus |
| C2 | ✅ **2026-10-21 — sans objet** : le plafond ne coupe plus rien depuis #108 (`dossier.py:343-345`, l'alerte n'est qu'un signal) ; l'analyste reçoit les 51/66/51 pièces, à blanc comme en réel. Ancien énoncé : **Plafond de 40 pièces dépassé** pour la qualité financière (51), le secteur (66) et le management (51) : relever ce que l'analyste reçoit réellement au-delà, puis trancher (relever le plafond ou trier). | [C] | Sonnet mesure, Opus tranche |
| C3 | Garde après rédaction sur un chiffre RELEVÉ (pas seulement ceux du socle) : NVDA qf_6 #1289 « part faible » sans chiffre ; RVMD qf_6 #1679 rend absents des retraitements qui valent zéro. | [C] | Opus spec, Sonnet code |
| C4 | (ex-21 b) Datation d'une note de synthèse : la date du fait rapporté, pas une date voisine (#1057 daté du 5 août pour une note du 14/10). | [C] | Sonnet sur spec |
| C5 | ✅ **2026-10-21** : DeepInfra répond (modèle des agents `DeepSeek-V4-Flash-0731`) ; crédit ≈ 5,55 $ sur une limite de 10 $, 3,21 $ consommés en octobre. ⚠️ À re-mesurer avant B8 et F1 (les relances D1 entament ce solde). | — | Sonnet |

## D. Relances NVDA (au nouveau standard)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| D1 | Relancer les chapitres ouverts : management (7), défendabilité (5), secteur (3), modèle économique (me_6). Ne refait que l'ouvert (#137 point 17). Après C1, C2, C5 ; ma_3 après A1. | [P] | Sonnet lance et mesure, sur accord |
| D2 | Relire chaque réponse neuve contre ses pièces ; `recouper_nombres` sur les 12 chiffres non recoupés. | — | Opus |
| D3 | Relances ciblées cellule par cellule une fois l'architecture signée (B5), y compris sur des questions déjà répondues. | [P] | Sonnet lance, Opus lit |

## E. Ce que le comité verra

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| E1 | L'écran de l'atelier de valorisation (onglets, hypothèses et leur origine, sensibilité, signer / écarter — l'API existe). | [C] | Opus maquette, Sonnet page |
| E2 | La décision raccordée au dossier V3 (ex-T6/T7, 05 §9, #95) : la page lit les six chapitres et la fourchette signée, et consigne la décision au PV — plus l'ancienne thèse V2. | [C] | Opus conçoit, Sonnet exécute |
| E3 | La note d'initiation telle qu'elle se lit en séance : six chapitres + fourchette, une pièce. | [C] | Sonnet sur maquette validée |

## F. Ultime étape, puis la séance

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| F1 | (ex-8, #127) Passage au standard : les 11 réponses NVDA « standard antérieur » et les pièces d'héritage sans datation. Critère : `n_standard_anterieur` = 0 sur NVDA. | [P] | Sonnet lance, Opus lit |
| F2 | Séance : lire la baisse ma_1 (#1499 juste, #1475 fondée sur une pièce mal titrée) ; relire les réponses signalées (ex-11 : NVDA qf_6, qf_1 normalisé = déposé, me_6 #1597 citée sur la mauvaise pièce) ; acquitter les chapitres ; signer le modèle ; décider. | — | Vous |

**Ordre** : B1 ✅ ‖ C1 ✅ ‖ B3 ✅ → B2 → B4 (porte de NVDA ouverte au catalogue 1.0.0, mesuré le 2026-10-21 : plus de relance préalable) (architecte, signature) → D1 restant + D3 + B5 → B7 (sur le scénario central) → B8 → E1-E3 → F1 → F2 ; C3, C4 en parallèle.

## Après le premier comité (jalon élargi, 05 A8-A11)

- (ex-7) Le veilleur d'événements extérieurs : les annonces d'un concurrent rouvrent les questions
  concernées (RVMD : revue FDA d'un concurrent le 07/10, non vue). À l'initiation, se_6 collecte
  elle-même les mouvements des concurrents ; la veille sert le suivi.
- (ex-16) Calendrier et revue trimestrielle ; position détenue sous revue ; dette #95 : le suivi
  réestime la fourchette, contraire à l'option 1 (05 §8).
- RVMD : ses 26 questions ouvertes (la plupart après le 10-Q du T3) ; ex-11 RVMD (mo_4 « 19 ans »,
  qf_8, mo_5 pancréas).
- (09 §12.2, ex-B6) Fourchettes, inventaire, matérialité, constructeur de scénarios — préalable à RVMD (arbre de programmes).
- (09 §12.1, M2 bis) Gabarit bancaire du socle — préalable à l'entrée d'une financière.
- (ex-19) MSFT de zéro (et ex-11 MSFT : note flash, nouveaux segments lus comme routine) ; (ex-20) un
  4ᵉ titre financier ; décider si un émetteur étranger (20-F) entre dans le jalon.
- (ex-22) L'outil du test : table titre × chapitre et comparaison de deux passages identiques ;
  (ex-23) le test sur 3-4 titres, deux passages ; puis où vit l'adaptation (05 §6).

## Dettes hors du chemin (connues, non bloquantes)

`negatif_collecte_executor.sh` 43/44 (`FormuleInexecutable` non capturée autour de
`recette_retenue`) · témoin de `tools/acceptation_frameworks.py` à remplacer (`qf_1.cout_du_capital`
retiré) · l'outil d'acceptation ne remet pas le socle ni les lectures · `synthesis_feed` titré par
le modèle (sans appelant V3) · (ex-1) transcription officielle NVDA chez le prestataire IR
(`q4cdn`, domaine partagé) · estimations d'analystes (FMP 403) · coût web non instrumenté ; lignes
web en série (~1 h par chapitre) · résidus #115/#116 (MSFT) · socle d'une banque TROMPEUR au gabarit industriel (JPM : charges d'intérêts « 0 » en 2024-2025, 09 §12.1) — ne pas le publier comme pièce avant M2 bis · modèles de décision DeepInfra.

## Soldé (inventaire du 2026-10-16)

1 copies au lieu de l'original (#133) · 2 passages selon la langue (#134) · 3 tableaux (#132) ·
4 instabilité du collecteur (#135) · 6 chiffre sans sa pièce (#136) · 9 marché adressable → absorbé
par B1 · 10 coût du capital, taux exigé 10 % (#137, 2026-10-19) · 12 acquisitions passées (#137,
2026-10-19) · 13 ré-analyse qui dégrade (`6760090`) · 14 demandes de recherche closes (`8af6f4a`) ·
15 fraîcheur par sujet (`331aa7c`) · 17 relance bornée, remise à zéro (`c2bc1af`) · 21 a
changement de stade (#138, #139) · 05 A7 (ré-analyse sans danger) soldé par 13, 14 et 17. Le détail
de chaque sujet soldé : `00-REPRISE-ARCHIVE.md` et `CONVENTIONS.md` #132-#139.

## Journal des actions jusqu'au premier comité réussi

> Fichier de référence (arbitrage du 2026-10-21) : chaque action menée vers le comité s'inscrit ICI,
> datée, avec son Id du plan, qui l'a faite, la preuve (commit, mesure, fichier) et son effet sur le
> plan. Une ligne par action ; le récit long va à l'archive. Le plan ci-dessus reste la seule liste des
> tâches : une tâche close y est marquée ✅ avec la date, sans être retirée.

| Date | Id | Action | Qui | Preuve / effet |
|---|---|---|---|---|
| 2026-10-21 | — | Mesure de l'état NVDA / RVMD (parcours, recoupement, admissibilité à blanc) | Opus + Sonnet | 22 questions NVDA ouvertes ; état reporté en tête du plan |
| 2026-10-21 | B1 | Inventaire de l'existant pour la spec du modèle (contrat, bac à calcul, encadrés, socle, écrans) | Sonnet (vérifié par Opus : 39 encadrés, 30 vides) | `mesures/2026-10-21/inventaire_modele_entreprise.md` ; ajout de B2 (aucun chiffre par activité) et de l'encadré des 24 questions dans B1 ; E1/E2 confirmés |
| 2026-10-21 | C1, C2 | Mesure des échecs ma_3/ma_4 et du plafond de pièces | Sonnet (vérifié par Opus) | `mesures/2026-10-21/mesure_nvda_relance.md` ; C1 : règle #126 stable, pas une panne ; C2 : 51/66/51 pièces pour 40 |
| 2026-10-21 | — | Arbitrages : NVDA seule d'abord ; réplicabilité exigée ; passage au standard en ultime étape (F1) ; plan unique = ce fichier | Vous | plan réécrit, reprise et 05 raccordées |
| 2026-10-21 | C2, C5 | Plafond de pièces lu dans le code ; crédit DeepInfra interrogé | Sonnet (C2 vérifié par Opus dans `dossier.py`) | `mesures/2026-10-21/mesure_c2_c5.md` ; C2 sans objet, C5 ✅ |
| 2026-10-21 | B1 | Spec du modèle de l'entreprise rédigée et soumise : 6 onglets, gabarit par type d'entreprise, contrôles par étape, deux signatures ; 4 arbitrages posés | Opus | `09-modele-entreprise.md` ; page https://claude.ai/artifact/Dx7LBBpsNAWAYzXroPiDiC ; mesure M0 (ventilation publiée) lancée |
| 2026-10-21 | B2 (M0) | Mesure de la ventilation publiée : NVDA, RVMD, JPM | Sonnet (NVDA calcul + réseau = centres de données vérifié par Opus) | `mesures/2026-10-21/mesure_m0_ventilation.md` ; B2 faisable sans analyser d'instance XBRL ; RVMD sans ventilation (gabarit pré-revenus en jugements ancrés) |
| 2026-10-21 | B1 | Arbitrages rendus sur la spec v1 (architecte dédié ; deux signatures, cible une ; scénarios sur inventaire ; détail fin, agrégé au format du socle) ; spec v2 | Vous, Opus | `09-modele-entreprise.md` v2 ; 2 points résiduels §11 |
| 2026-10-21 | B1 | Arbitrages sur la v2 : seuil de matérialité 10 % ; porte de l'architecte = première réponse sur chaque question source. Spec validée ; convention #140 | Vous, Opus | `09-modele-entreprise.md` §11 ; `CONVENTIONS.md` #140 |
| 2026-10-21 | B1 | Deux commentaires sur la page de lecture intégrés (spec v2.1, §12) : gabarit des comptes par famille, mesuré (JPM : 74 cellules non déposées, lignes clés vides, intérêts « 0 ») ; fourchettes bas/central/haut avec méthode, scénarios = déplacements d'un sous-ensemble, v1 = central seul, schéma prêt dès M1 ; B6 après le premier comité | Vous, Opus | `09-modele-entreprise.md` §12 ; `CONVENTIONS.md` #140 |
| 2026-10-21 | B3 (M1) | Spec d'exécution du lot M1 écrite (référentiel à part de `frameworks.yaml` pour ne pas invalider les réponses ; 21 fiches ; 4ᵉ origine `calcul` ; central = constante, jamais une ligne ; migration 061 = 4 registres append-only) ; exécution confiée à Sonnet | Opus → Sonnet | `10-lot-M1-catalogue-et-contrats.md` ; vérification par exécution à suivre |
| 2026-10-21 | B6, B7 | Fourchette du premier comité NVDA = central ± 1 pt du taux exigé, étiquetée « sensibilité au taux » ; scénarios sur risques après le comité (M6) | Vous | `09-modele-entreprise.md` §12.2 ; reprise |
| 2026-10-21 | B3 (M1) | ✅ Lot M1 construit par Sonnet (interrompu par la limite de consommation, repris), vérifié par Opus PAR EXÉCUTION : `negatif_modele_entreprise.sh` 66/0, `negatif_061.sh` 39/0 ; migration 061 relue et appliquée (4 registres, 0 ligne) ; suite après 061 : 68/68 verts, 5400 assertions, aucune ligne persistée par le check de persistance | Sonnet → Opus | `10-lot-M1-catalogue-et-contrats.md` ; écarts de Sonnet : boucle de cycle bornée (le négatif avait révélé une boucle infinie), `valider_cellule(…, ctx)`, `sans_periode` admis en fourchette, grep de réplicabilité sans dépouillement sur le YAML |
| 2026-10-21 | B3 (M1) | Déployé `4c6d37e` (rebasé sur 6 commits d'un autre projet, sans fichier commun), vérifié dans le conteneur. Constat : les questions sources d'une rentable n'incluent pas ma_3/ma_4 → la porte de NVDA ne dépend plus du management ; décompte à refaire avant M3 | Opus | reprise § « Où on en est » |
| 2026-10-21 | B4 (porte) | Décompte refait au catalogue 1.0.0 (`montrer_parcours.sh NVDA`, gratuit) : les 12 questions sources d'une rentable ont toutes une première réponse instruite (mo_4 « recherche épuisée », mo_6 et se_2 « pièces insuffisantes » comptent, 09 §11.2) → **la porte de l'architecte est ouverte pour NVDA** ; l'étape « relance des questions sources sans première réponse » est vide ; ma_3/ma_4 (et A1) sortent du chemin de l'architecte, restent dans D1 | Opus | sortie de `montrer_parcours.sh NVDA` lue en texte ; ordre : B2 → B4 directement |
| 2026-10-21 | B2 (M2) | Spec d'exécution du lot M2 écrite ; méthode remesurée : l'instance XBRL du dépôt (+ étiquettes + définitions) au lieu des pages rendues `R#.htm` (NVDA identique à M0, hiérarchie Data Center → Compute/Networking lue, JPM 15 Mo lu en 0,24 s) ; aucune jointure aux chapitres en M2 (pas de changement de `frameworks.yaml`) ; exécution confiée à Sonnet | Opus → Sonnet | `11-lot-M2-ventilation-publiee.md` ; vérification par exécution à suivre |
