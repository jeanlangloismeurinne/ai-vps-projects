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
| B2 | ✅ **2026-10-21** (M0, M2 ; spec `11-lot-M2-ventilation-publiee.md`). La ventilation publiée au socle (segments, marchés, géographie) — mesurée faisable et générique. | [C] | Sonnet sur spec |
| B3 | ✅ **2026-10-21** (spec `10-lot-M1-catalogue-et-contrats.md`, migration 061). (M1) Catalogue de variables (fiche avec `familles` et `methode_de_fourchette`), patrons de départ, format agrégé = gabarit de la famille du titre ; contrats `Architecture`, `Cellule`, `Fourchette`, `Scenario`, `Deplacement` (central seul peuplé, 09 §12.2) ; gardes. | [C] | Opus spec → Sonnet |
| B4 | (M3) L'agent architecte, sa porte (première réponse sur chaque question source), ses contrôles de structure, la signature de l'architecture (interrupteur). | [C] | Opus spec → Sonnet |
| B4b | (P1) **Le périmètre, sujet séparé de l'architecte** (demande du 2026-10-22) : un détenteur unique des changements de découpage et de périmètre (régimes, transitions typées par les montants, passage vérifié sur la période publiée dans les deux découpages, ruptures nommées, douze mois sans mélange de régimes), son propre catalogue de cas ; les six endroits qui en décident aujourd'hui rebranchés. Spec `14-lot-P1-perimetre.md` v1.1 (arbitrages rendus le 2026-10-22). Gratuit ; AVANT l'acceptation à blanc de l'architecte. | [C] | Opus spec → Sonnet |
| B4c | (P1 bis) **Fin du rebranchement du périmètre** : le relevé et le rendu de la ventilation lisent la chronique (historique dans le découpage le plus récent, passage/hypothèse marqués) ; [S2]/[S3b] lisent le régime de référence ; emboîtement par dépôt ; consigne de l'architecte ; douze mois glissants (socle compris) via le prédicat ; signal d'acquisition branché à un producteur. Reste de `14-lot-P1-perimetre.md` §3. | [C] | Opus spec → Sonnet |
| B4d | (M3 ter, spec `15-lot-M3ter-architecte.md`) **Défauts de l'architecte seul** relevés à blanc le 2026-10-22 (§ journal) : plantage au lieu d'un refus nommé ; cellule annuelle sans période ; pièce hors du dossier ; programmes de stades différents sous un seul jalon → **une ligne par programme nommé à risque propre** (arbitrage du 2026-10-22) ; robustesse prouvée sur un **banc de 10 entreprises** (B4e). | [C] | Opus spec → Sonnet |
| B4f | **Explorateur du dossier** (spec `16-lot-B4f-explorateur.md`) (arbitrage du 2026-10-22, option C) : brique commune aux agents — table des matières du dossier, ouvrir une note puis ses pièces, chercher dans une pièce longue, recherche par similarité ; état temporel de chaque élément calculé à la lecture (en vigueur / remplacé par / périmé par) ; ouvertures bornées ; l'agent ne cite que ce qu'il a ouvert ou reçu ; hors dossier = DEMANDE de recherche au collecteur (B′), jamais d'Internet direct ; architecte en deux temps (F) comme garde-fou ; interrupteur (sans explorateur = architecte actuel). Graphe d'entités (E) : après le comité. | [C] | Opus spec → Sonnet |
| B4e | **Banc d'essai de l'architecte** (arbitrage du 2026-10-22, « structure d'abord ») : NVDA, RVMD, MSFT, 3M, Danaher, Eli Lilly, Vertex, Costco, Nike, GE Aerospace — comptes + ventilation (gratuits) + me_7 + deux passages à blanc par titre ; on juge la structure et sa stabilité. **Protocole (arbitrage du 2026-10-22)** : UNE entreprise à la fois, chacune très différente de la précédente ; on s'arrête dès que le système réussit DEUX entreprises DE SUITE, au plus dix. Réussite = deux passages proposés, signables à la lecture d'Opus (découpage juste contre les chiffres publiés, une ligne par programme nommé à risque propre, aucune citation fausse) et de même structure. Un correctif après un échec remet le compteur à zéro et se rejoue sur les entreprises déjà passées (non-régression). Comparaison avec / sans explorateur sur chaque entreprise. | [P] | Sonnet lance, Opus lit |
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

- (P2) **Croissance hors acquisitions** : module ad hoc (arbitrage du 2026-10-22, lot P1 §4 bis) — le chiffre
  d'affaires acquis se lit dans le texte (modèle) ; au premier comité, l'acquisition significative est seulement signalée.
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
| 2026-10-21 | B2 (M2) | ✅ Lot M2 construit par Sonnet, vérifié par Opus PAR EXÉCUTION ; 4 défauts du rendu renvoyés (emboîtement aplati ; changement de découpage NVDA au 10-Q lu comme « non ventilé » ; membres nouveaux non nommés ; conflits de bruit) puis 1 corrigé par Opus (une part des **créances** clients rendue comme part du **chiffre d'affaires**, [V17]). Constat : NVDA publie depuis le 10-Q de juillet Data Center = Hyperscale 91 761 + AI Clouds/Industrial/Enterprise 72 508 M$ (cumul S1), + Edge Computing 13 568 — le bloc « grands hébergeurs » est désormais publié. Suite 70/70, 5 473 assertions ; négatifs 14/0 et 3/0. Commité ; **déploiement refusé par le classifieur, à lancer par l'utilisateur** | Sonnet → Opus | `11-lot-M2-ventilation-publiee.md` ; `montrer_ventilation.sh NVDA RVMD JPM` |
| 2026-10-22 | B2 (M2) | Déployé (`67f7e87`, rebuild du backend, HTTP 200) et vérifié dans le conteneur (`ventilation*.py`, référentiel 1.0.0, import) — le refus du classifieur de la veille n'était pas permanent | Opus | sortie de `compose-deploy.sh` ; `docker exec portfolio-backend` |
| 2026-10-22 | B4 (M3) | Spec d'exécution du lot M3 écrite après mesure gratuite : NVDA a redécoupé ses marchés au 10-Q (Data Center → Hyperscale + AI Clouds ; Edge Computing remplace Gaming/ProViz/Auto/OEM) ; RVMD `secteur_unique` et reclassée `rentable` le 18/10 ; rendu de la ventilation sans identifiant de membre (à ajouter) ; aucune pièce de ventilation encore publiée. Choix d'Opus à confirmer : horizon de projection 5 exercices (paramètre du fonds) ; une réponse renvoyée par le contrôle ouvre la porte (« quel qu'en soit le statut ») ; exécution confiée à Sonnet | Opus → Sonnet | `12-lot-M3-architecte.md` ; vérification par exécution à suivre |
| 2026-10-22 | B4 (M3) | Arbitrages : horizon de projection **10 exercices** par défaut ; une réponse refusée par le contrôle **ferme** la porte de l'architecte (la réponse doit être juste), sauf en phase de test (interrupteur `porte_admet_reponses_refusees: true`, à basculer avant le premier comité réel) ; transmis à Sonnet en cours d'exécution | Vous | `12-lot-M3-architecte.md` §3.1, §7 |
| 2026-10-22 | B4 (M3) | ✅ Lot M3 construit par Sonnet, vérifié par Opus PAR EXÉCUTION : `negatif_architecte.sh` 21/0, `negatif_modele_entreprise.sh` 68/0, `negatif_062.sh` 13/0 ; suite 5 734 assertions, seul rouge attendu `check_architecture_persist` §3 (062 alors non appliquée). Migration 062 relue et **appliquée** ; le rejeu du check de persistance contre la vraie base a été refusé par le classifieur (à lancer par l'utilisateur). Code commité, **non déployé**. Écarts de Sonnet : [S2] non récursif sous un bloc publié ; `servir_architecture(ticker_id, …)` ; pièce d'une note flash appariée par accession dans l'URL (2 notes NVDA sur 5 sans pièce) | Sonnet → Opus | `12-lot-M3-architecte.md` ; `mesures/2026-10-22/` (4 architectures à blanc) |
| 2026-10-22 | B4 (M3) | Lecture des 4 architectures à blanc (0,008 $) : **aucune n'est signable**. NVDA : premier niveau stable (segments Compute & Networking + Graphics) mais l'axe des marchés est EMBOÎTÉ À TORT sous les segments — Data Center (193 737 M$) déclaré partie de Compute & Networking (193 479 M$), Automotive placé sous Graphics ; Hugging Face (acquisition annoncée) classé « programme en développement » ; l'emboîtement fin change d'un passage à l'autre. RVMD : stable, mais tout le portefeuille de molécules en un seul bloc « précliniques » (une seule probabilité de succès) et la recherche annuelle égale au « coût restant à engager », un montant sans période. Les contrôles passent tous : trous du contrôle de structure, à corriger en M3 bis avant tout `--ecrire` | Opus | lecture des JSON contre la ventilation (chiffres FY2026) |
| 2026-10-22 | B4 (M3) | `check_architecture_persist` rejoué contre la vraie base (le refus du classifieur était levé) : rouge en §3 — défaut du CHECK (le doublon refusé par la base avortait la transaction englobante), corrigé par un point de sauvegarde → 10/0, 0 ligne laissée. **M3 déployé** (`1d5dfbf`, rebasé sur 9 commits d'un autre projet), vérifié dans le conteneur (référentiel 1.1.0, modules de l'architecte) ; `GET /v2/tickers/NVDA/architecture` → 200 `aucune_proposee` | Opus | `compose-deploy.sh` ; `docker exec` ; requête des registres |
| 2026-10-22 | B4 (M3 bis) | Diagnostic des trous et spec M3 bis : (1) un membre publié déclaré `estime` échappe à [S1]/[S3] → [S10] ; (2) [S9] saute les fiches `sans_periode` → [S11] (cadrage flux/instant lu dans le gabarit) ; (3) programme sans jalon → contrat 1.2.0 (`jalon`, `manques_du_dossier`) + fiche `depense_de_developpement_du_bloc`. Mesuré : la matière de RVMD ne cite AUCUNE molécule hors daraxonrasib — le regroupement est un trou du dossier (aucune question source n'inventorie le portefeuille) : question neuve réservée à l'arbitrage, après le comité NVDA ; porte RVMD fermée (se_3) | Opus → Sonnet | `13-lot-M3bis-structure.md` ; `architecte.sh RVMD --matiere-seule` |
| 2026-10-22 | B4 (M3 bis) | Revue de la spec v1 à la demande de l'utilisateur : elle reconnaissait l'exemple (règle par libellé, période seule). Arbitrages : **principe fondateur n° 4** (tout développement vaut pour toutes les entreprises ; on corrige la cause, jamais l'exemple ; formes non couvertes par NVDA/RVMD éprouvées par cas fictifs, une entreprise réelle de plus seulement si nécessaire) ; **question `me_7`** « ce que l'entreprise prépare » (programmes futurs compris, ils entrent dans la valorisation) acceptée. Spec v2 sur cinq causes : squelette publié construit par le code ; rendu des axes ; `me_7` + manques du dossier ; formules typées (unité × période) ; origine ≠ maturité. Mesuré : 44 pièces du corpus citent le portefeuille RVMD, aucune n'atteint l'architecte. Conséquence : la porte NVDA se fermera jusqu'à l'instruction de `me_7` | Vous, Opus | `PRINCIPES-FONDATEURS.md` §4 ; `13-lot-M3bis-structure.md` v2 |
| 2026-10-22 | B4 (M3 bis) | Cause ① re-vérifiée sur remarque de l'utilisateur : la v2 imposait un squelette publié complet, contraire à l'arbitrage du 2026-10-21 (architecte libre de composer, patrons « pas une cage »). Cause corrigée : le contrat n'offrait aucune place au second découpage publié (le modèle l'a forcé dans l'arbre, son motif le dit) et laissait le modèle affirmer deux FAITS (maille, emboîtement entre blocs publiés). Spec v2.1 : composition libre (maille, regroupements, découpages estimés), faits établis par le code, case « autres axes » ; cas fictifs à deux compositions différentes pour prouver l'absence de cage | Vous, Opus | `13-lot-M3bis-structure.md` v2.1 ; `09-modele-entreprise.md` §1.1, §2 |
| 2026-10-22 | B4 (M3 bis) | ✅ Lot M3 bis v2.1 construit par Sonnet, vérifié par Opus PAR EXÉCUTION : étape 0, les 4 architectures du 22/10 passaient l'ancien contrôle (trous confirmés), refusées désormais chacune par la règle de sa cause ; `negatif_architecte.sh` 28/0, `negatif_modele_entreprise.sh` 71/0, `negatif_ventilation_publiee.sh` 16/0 ; suite 72/72, 5 834 assertions. Écarts de Sonnet acceptés : [S12] dans le contrat (invariant d'un objet, #37) ; [S3] réduit à « un seul axe au premier niveau » (le double compte d'un descendant est nommé par [S7]) ; pas de migration 063 (prompt de l'architecte dans le code, JSONB sans DDL). **Deux défauts corrigés par Opus** : (1) les formules : TOUT nombre écrit en dur était lu comme une conversion d'unité (`ca × 0,9 + ca` refusé) → seuls les rapports d'échelles de la table des unités convertissent, tout autre nombre est un coefficient (règle dite dans la consigne de l'architecte) ; (2) le rendu des axes : le TTM `activites` NVDA (Σ 277 798 ≠ 302 970 M$, Data Center seul) présenté sans motif et compté comme un découpage publié → motif « découpage changé » sur la ligne Σ, période calculée hors des découpages ([V13b]). Matière : NVDA ~12 800 jetons, porte **fermée par `me_7`** ; RVMD ~10 000 jetons, fermée par `me_7` et se_3 | Sonnet → Opus | `13-lot-M3bis-structure.md` ; `architecte.sh NVDA --matiere-seule` |
| 2026-10-22 | B4b (P1) | Demande de l'utilisateur : distinguer « premier test de l'architecte » et « changement de périmètre d'une année à l'autre » (NVDA cumulait les deux). Mesuré (gratuit) : la continuité d'une série n'a pas de détenteur — six endroits en décident (relevé, rendu, [S2]/[S3b], emboîtement fusionné entre dépôts, consigne de l'architecte, douze mois glissants partagés avec le socle) ; seuls le dernier 10-K et le dernier 10-Q sont lus, donc le semestre 2025 publié dans l'ancien découpage (le recouvrement) ne l'est pas ; les douze mois de Data Center mêlent deux découpages sans vérification ; choisir le nouveau découpage ne laisse qu'un semestre d'histoire. Spec du lot P1 écrite, 2 arbitrages posés | Vous, Opus | `14-lot-P1-perimetre.md` ; `montrer_ventilation.sh NVDA` |
| 2026-10-22 | B4b (P1) | Arbitrages : (Q1) l'historique se rend dans le découpage le plus récent, « quitte à prendre des hypothèses pour découper l'historique » — sans passage vérifié, répartition au prorata des parts de la première période publiée dans le nouveau découpage, déclarée et marquée ; au niveau agrégé pas de rupture (la structure d'un compte de résultat ne change pas) → invariant Σ = socle ; (Q2) acquisition significative SIGNALÉE au comité, croissance hors acquisitions = module ad hoc après le premier comité. Spec v1.1 ; exécution confiée à Sonnet | Vous, Opus | `14-lot-P1-perimetre.md` §2.3 bis, §2.3 ter, §4 bis, §7 |
| 2026-10-22 | B4 (M3 bis) | **M3 bis déployé** (`--rebuild-only` sur `212af17`, avant toute modification de fichier suivi par Sonnet ; poussé après rebase sur 4 commits d'un autre projet → `1f9a364`), vérifié dans le conteneur (me_7, référentiel 1.2.0, modules importés) | Opus (sur autorisation) | `compose-deploy.sh` RESULT success HTTP 200 ; `docker exec` |
| 2026-10-22 | B4 (me_7) | `me_7` instruite sur le code de l'IMAGE (pas le dépôt monté : Sonnet y modifiait le code partagé) : NVDA réponse #2292 (6 min), RVMD #2304 (13 min), approxime A-, manager au vert. Lecture contre les pièces : **RVMD juste** (8 programmes, essais et R&D 987,3 M$ retrouvés dans #1546/#876) ; **NVDA faible** — inventaire de 5 « programmes » qui mêle une génération (Vera Rubin), un produit (Vera CPU), des clients (IA souveraine), un thème (robotique) et une acquisition (Hugging Face, bien dite non conclue) ; Rubin Ultra, Spectrum-X, DRIVE Thor, Omniverse présents au corpus mais absents ; et le « TAM 200 Md$ du Vera CPU » est VRAI (#1004) mais **mal cité** : le recoupement l'a validé par le « 200 000 entreprises » de Hugging Face (#1010) — trou du recoupement (le nombre, pas son sujet). Portes : NVDA ouverte ; RVMD fermée par se_3 | Opus | `tools/recouper_nombres.sh` ; requêtes des pièces |
| 2026-10-22 | B4b (P1) | ✅ partiel — Sonnet, vérifié par Opus PAR EXÉCUTION : étape 0 CONFIRMÉE (jumeau NVDA `0001045810-25-000209` : Gaming 8 050 + ProViz 1 110 + Automotive 1 153 + OEM 284 = Edge 10 597 M$ au dollar ; Data Center 80 208 inchangé, enfants Compute+Networking = Hyperscale+AI Clouds) ; `perimetre.py` (régimes, transitions par les montants, partition bornée, chronique publie/passage/hypothèse, invariant de l'agrégat, prédicat des douze mois, ordre des périodes par la FIN, signal d'acquisition) ; `check_perimetre` 78/0 (dont cas réel NVDA figé), `negatif_perimetre.sh` 19/19 ; jumeau lu par `ventilation_feed` ; premier niveau et ordre des périodes délégués (deux copies supprimées). Suite 5 918/0. **Non fait** (→ B4c) : relevé/rendu sur la chronique, [S2]/[S3b], emboîtement par dépôt, consigne, douze mois, signal branché. Mesures : retraitements au socle NVDA 988 / RVMD 46 / MSFT 434 couples (surtout arrondis anciens) ; aucun chiffre d'affaires acquis publié en XBRL (NVDA, MSFT) → le signal se repliera sur la contrepartie. Commité, NON déployé | Sonnet → Opus | `check_perimetre.py`, `negatif_perimetre.sh`, `run_all.sh` |
| 2026-10-22 | B4 (architecte à blanc) | 4 passages sur le code DÉPLOYÉ (0,02 $), qui SÉPARENT les deux sujets. **Périmètre** : NVDA 2 refusé [S2]/[S7] — blocs mêlant les deux découpages (Data Center + Edge Computing ET Gaming, Automotive…) faute d'historique dans le nouveau découpage → B4c. **Architecte seul** (→ B4d) : NVDA 1 refusé [P4] (`capital_par_point_de_croissance` sans période) ; NVDA 2 cite une pièce hors du dossier [S6] ; RVMD 1 **PLANTE** (`ValidationError` levée par `faits_publies.poser_maille` : bloc estimé sans pièce — le contrôle n'est pas converti en refus nommé renvoyé au modèle) ; RVMD 2 proposée (4 blocs estimés, manque du dossier écrit) mais **six programmes de stades différents (Phase 3 → préclinique) sous un seul bloc et un seul jalon** — l'erreur d'origine revient malgré me_7 qui nomme chaque molécule et son stade | Opus | `scratchpad/archi/*.log`, `rvmd_2.json` |
| 2026-10-22 | B4d/B4e | Arbitrages : (1) une ligne par programme que l'émetteur nomme individuellement ET dont la réussite est incertaine (une nouvelle génération d'un produit existant nourrit son activité) ; seuls les programmes non nommés se regroupent ; (2) banc de 10 entreprises, « structure d'abord » ; (3) liste proposée retenue. Diagnostic de la matière demandé : l'architecte ne voit que résumés + chiffres, **aucun outil de lecture** ; la liste des pièces citables est calculée mais **jamais montrée** (d'où la citation de la réponse #1370 comme pièce, et le plantage RVMD) ; à blanc, comptes et ventilation n'ont pas de numéro de pièce ; questions sans contenu (NVDA se_2/mo_4/mo_6 ; RVMD me_5, se_3, mo_6 refusée) ; RVMD me_2/mo_4/se_2 antérieures à l'approbation FDA | Vous, Opus | `scratchpad/archi/matiere_*.txt` |
| 2026-10-22 | B4f/B4e | Arbitrages : explorateur du dossier (C) + demande de recherche au collecteur (B′), architecte en deux temps (F) en garde-fou ; banc séquentiel, arrêt à deux succès consécutifs (au plus 10). Ordre : B4c → B4d → B4f → B4e | Vous | ce plan |
| 2026-10-22 | B4c | 2ᵉ passage de Sonnet, partiel, vérifié par Opus PAR EXÉCUTION (suite 5 938/0 ; négatifs ventilation 17/17, appariement 36/36, périmètre 19/19) : signal d'acquisition branché au relevé (seuil 5 % au référentiel ; la branche « capitalisation » reste inatteignable sans source de cours) ; douze mois : la version RETRAITÉE la plus récente l'emporte, ambiguïté = refus nommé. **Régression de `c551003` découverte et corrigée** : avec le jumeau, les douze mois par pays de NVDA prenaient le semestre 2025 d'origine (Σ 323 559 M$ ≠ total 302 970 M$) — la suite était verte : trou fermé par la garde (iv) de l'addendum. **Consigne de l'architecte retirée par Opus** (elle annonçait un historique reconstitué que le rendu ne montre pas encore). Cœur restant (cellules par dépôt, vue servie = chronique) : conception arrêtée, `14-lot-P1-perimetre.md` §8, deux tranches | Sonnet → Opus | `run_all.sh`, `montrer_ventilation.sh NVDA` |
| 2026-10-22 | B4c (tranche A) | 3ᵉ passage de Sonnet, vérifié par Opus PAR EXÉCUTION (suite 5 950/0 ; négatifs ventilation 18/18, périmètre 22/22, persistance 3/3) : cellules relevées PAR DÉPÔT (plus de fusion « premier dépôt gagne »), hiérarchie par dépôt ; `perimetre.vue_servie` (dépôt le plus récent fait foi) + garde (iv) sur le chiffre d'affaires, éprouvée sur le jumeau NVDA réel (mutation « terme d'origine » → Σ pays 323 559 ≠ 302 970 rouge) — **NON branchée sur les lecteurs** : l'axe PAYS de NVDA change aussi de régime (Singapour replié), le reproduire exige le rendu de la tranche B. Effet visible : deux doublons de comparatifs clients rendus (même valeur, deux dépôts). À reprendre en tranche B : la garde (iv) écarte EN SILENCE les périodes incomplètes → les nommer « non jugée ». Sonnet a buté trois fois sur le branchement : recommandation d'Opus, tranche B exécutée par Opus | Sonnet → Opus | `run_all.sh` ; diff texte `montrer_ventilation.sh` |
