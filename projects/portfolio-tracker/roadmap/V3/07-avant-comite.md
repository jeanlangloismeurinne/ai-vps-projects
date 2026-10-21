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

## B. La valorisation — le modèle de l'entreprise (ex-9, ex-18 ; 05 A6 et §4 bis)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| B1 | **Spec du modèle de l'entreprise, soumise avant tout code** : onglets et ordre de remplissage (structuration → données par activité → transverse) DÉCRITS EN DONNÉES par méthodologie (segments pour NVDA, programmes pour RVMD, bilan pour une financière) ; ce que chaque question écrit / lit, dont un encadré pour les 24 questions qui n'en ont pas et pour va_1-va_6 ; garde qualité par étape ; raccord au socle et à `parametres_du_fonds` ; signature globale ; sensibilité. Absorbe me_5 / marché adressable (ex-9). Réutilise le contrat `ModeleValorisation`, le bac à calcul et ses 13 calculs fermés, la signature #98. | [C] | Opus → Vous |
| B2 | **Les chiffres par activité** : relever la note sectorielle des comptes (exigée de tout émetteur : ASC 280 aux États-Unis, IFRS 8 ailleurs — donc générique) dans un gabarit commun ; NVDA en premier cas. | [C] | Sonnet sur spec B1 |
| B3 | L'agent qui écrit le modèle à partir du dossier (méthodologie, activités, tableau d'hypothèses, mécanique). | [C] | Opus conçoit, Sonnet exécute |
| B4 | va_4-6 recalculés à la lecture au dernier cours coté, daté (option 1, #81). | [C] | Sonnet |
| B5 | Règle de Greenwald : la croissance ne vaut que si le capital rapporte plus que le taux exigé et que la barrière tient. | [C] | Sonnet sur spec |
| B6 | Ordonnancement : la valorisation après les chapitres dont elle reprend ; rouvrir va_1/va_2 rouvre va_6. | [C] | Sonnet sur spec |
| B7 | Sensibilité ±1 pt du taux exigé ; alerte quand la décision du fonds sur le taux est échue (2027-10-17). | [C] | Sonnet |
| B8 | Acceptation (05 §4 bis) : NVDA (activités) et RVMD (programmes) donnent chacun une fourchette ; changer une hypothèse recalcule sans appel modèle ; au cours du jour, va_6 bouge sans va_2. | [P] | Sonnet lance, Opus lit |

## C. Correctifs avant les relances (tous génériques)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| C1 | **Un extrait court légitime est refusé** (#126, ≥ 20 caractères) : un cours ou un intitulé de fonction (« $198.89 », « X Director ») fait tomber ma_3 et ma_4. Admettre une valeur ou un intitulé court sans rouvrir les citations vides que la règle visait. Stable, pas une panne. | [C] | Opus règle, Sonnet code |
| C2 | **Plafond de 40 pièces dépassé** pour la qualité financière (51), le secteur (66) et le management (51) : relever ce que l'analyste reçoit réellement au-delà, puis trancher (relever le plafond ou trier). | [C] | Sonnet mesure, Opus tranche |
| C3 | Garde après rédaction sur un chiffre RELEVÉ (pas seulement ceux du socle) : NVDA qf_6 #1289 « part faible » sans chiffre ; RVMD qf_6 #1679 rend absents des retraitements qui valent zéro. | [C] | Opus spec, Sonnet code |
| C4 | (ex-21 b) Datation d'une note de synthèse : la date du fait rapporté, pas une date voisine (#1057 daté du 5 août pour une note du 14/10). | [C] | Sonnet sur spec |
| C5 | Crédit DeepInfra vérifié par un appel minimal avant les relances. | — | Sonnet |

## D. Relances NVDA (au nouveau standard)

| Id | Tâche | Nature | Qui |
|---|---|---|---|
| D1 | Relancer les chapitres ouverts : management (7), défendabilité (5), secteur (3), modèle économique (me_6). Ne refait que l'ouvert (#137 point 17). Après C1, C2, C5 ; ma_3 après A1. | [P] | Sonnet lance et mesure, sur accord |
| D2 | Relire chaque réponse neuve contre ses pièces ; `recouper_nombres` sur les 12 chiffres non recoupés. | — | Opus |

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

**Ordre** : B1 (spec, à valider) ‖ C1-C5 → A1 → D1-D2 → B2-B7 → B8 → E1-E3 → F1 → F2.

## Après le premier comité (jalon élargi, 05 A8-A11)

- (ex-7) Le veilleur d'événements extérieurs : les annonces d'un concurrent rouvrent les questions
  concernées (RVMD : revue FDA d'un concurrent le 07/10, non vue). À l'initiation, se_6 collecte
  elle-même les mouvements des concurrents ; la veille sert le suivi.
- (ex-16) Calendrier et revue trimestrielle ; position détenue sous revue ; dette #95 : le suivi
  réestime la fourchette, contraire à l'option 1 (05 §8).
- RVMD : ses 26 questions ouvertes (la plupart après le 10-Q du T3) ; ex-11 RVMD (mo_4 « 19 ans »,
  qf_8, mo_5 pancréas).
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
web en série (~1 h par chapitre) · résidus #115/#116 (MSFT) · modèles de décision DeepInfra.

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
