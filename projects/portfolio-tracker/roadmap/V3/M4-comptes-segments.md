---
id: m4-comptes-segments
status: ouvert le 2026-11-28 — tri et acceptation écrits AVANT la construction ; questions §4 en attente de l'utilisateur
created: 2026-11-28
project: portfolio-tracker
role: >
  Le dossier d'ouverture du module M4 « Comptes et segments » : le tri de l'ancien code, puis
  l'acceptation, écrite AVANT la construction (charte, points 6 et 7). Part dans `roadmap/archive/`
  le jour où M4 est accepté.
---

# M4 — Comptes et segments

*Ce que ferait un vrai fonds* : avant tout jugement, quelqu'un **remet les comptes au gabarit maison** —
cinq exercices et les douze derniers mois, compte de résultat, bilan, flux de trésorerie, chaque case
avec son origine (« déposé », « calculé par différence »…) et une vérification que les sous-totaux
retombent sur les totaux publiés. Puis les **ratios maison** (rentabilité du capital, conversion en
trésorerie), toujours calculés de la même façon, quelle que soit la présentation de la société. Puis la
**ventilation** publiée (secteurs, produits, géographie, grands clients) raccordée au chiffre d'affaires,
et le **périmètre** : quand la société change de découpage ou achète une autre société, la série est
rendue comparable ou la rupture est dite. Une banque ne passe pas au gabarit d'un industriel : elle a sa
propre famille de comptes, ou elle n'est pas traitée — jamais des comptes trompeurs. Personne ne juge
ici : tout est calculé.

## 0. Ce que M4 rend

Pour chaque émetteur, **un seul objet** (contrat `comptes`, version 1) :

- **Les comptes reconstitués** au gabarit de la famille de comptes de l'émetteur : exercices, douze
  derniers mois, dernier bilan ; chaque case dit son état (déposée, par différence, par somme, calculée,
  zéro déclaré, non déposée) et son origine (document de M2, concept, période) ; le bouclage de chaque
  total (écart, tolérance).
- **Les ratios maison**, recalculés à la lecture (jamais rangés), version de leurs conventions affichée.
- **La ventilation publiée** par axe, raccordée au total publié ; les faits non rattachés listés.
- **Le périmètre** : les régimes de découpage successifs, les ruptures typées (changement de
  découpage, acquisition significative), la série comparable servie et ce qu'elle exclut.
- **Ce qui manque**, nommé : famille sans gabarit, données structurées absentes, exercice non couvert
  — et la demande de collecte que M4 a faite pour le combler (« au fil du dossier », M3 §2, 1 bis).

M4 ne lit **que des données structurées** dans cette version (question 3) : il n'extrait aucun chiffre
d'un texte.

## 1. Le tri (charte, point 7)

Inventaire du 2026-11-28 (recherche déléguée, relue ; données en base relues en lecture seule). Tout
l'ancien code comptable vit dans `app/knowledge/` et `app/modele_entreprise/`, écrit dans
`knowledge_entries` (`fact_financial`), et sert encore l'ancien enchaînement par trois routes
(`parcours_v2`, `/v2/tickers/{id}/architecture`, deux POST manuels de `knowledge_v2`) et la note
flash du matin. M4 ne le débranche pas : il le remplace pour la suite, et ce qu'il remplace part quand
plus aucun lecteur ne l'appelle.

| Ce que l'ancien système contient | Où | Décision |
|---|---|---|
| La reconstitution des comptes au gabarit (fonction pure, `companyfacts` → cinq exercices, douze mois, bilan, états des cases, bouclage, tolérance en un seul endroit) | `knowledge/socle_comptes.py` + gabarit `socle_comptes.yaml` 1.1.0 | **Repris derrière le contrat** (au registre, `reprises`) : déjà pur, sans base ni réseau, sans nom de société dans le code, éprouvé (`check_socle_comptes`, négatif, fixtures réelles NVDA, RVMD, MSFT, JPM). Le gabarit devient le référentiel de M4. Il part dans le module quand l'ancien enchaînement ne l'appelle plus (22 importeurs). |
| Les reclassements propres à un émetteur (trois concepts, NVDA et RVMD, rangés par numéro SEC) | `knowledge/socle_comptes_emetteurs.yaml` | **À trancher** (question 2) : donnée par émetteur, rangée par l'identité maison et motivée, ou règle générale. |
| Les ratios maison (capital employé, résultat d'exploitation après impôt, rentabilité du capital, conversion sur trois ans, capital par point de croissance, pente des rendements), recalculés à chaque lecture | `knowledge/ratios_maison.py` | **Repris tel quel derrière le contrat** : pur, conventions écrites en tête, version entrée dans l'empreinte. |
| Les quatre ratios de l'ancien flux (rentabilité, conversion, intensité des investissements, levier) écrits en base | `knowledge/financials_feed.py` (POST manuel `knowledge_v2`) | **Laissé, puis supprimé** : chemin parallèle et plus ancien que les ratios maison ; deux définitions d'un même ratio, c'est une de trop. Supprimé avec sa route à l'acceptation de M4 si plus aucun lecteur (à vérifier par grep à ce moment). |
| Le catalogue de 33 postes US-GAAP écrit dans le code, le choix du concept le plus frais, l'écriture des faits bruts | `knowledge/edgar_feed.py` | **Laissé** : remplacé par le gabarit de M4 (en donnée) et par la collecte de M2 (le document `companyfacts` est déjà rangé brut pour les trois dossiers). Sa résolution symbole → numéro SEC sert la note flash : elle reste à l'ancien code (M2 a la sienne, B10). |
| Le client du registre et les lecteurs purs de `companyfacts` (points annuels, instantanés, point pour une période) | `knowledge/edgar_facts.py` | **Lecteurs purs repris derrière le contrat** (le gabarit s'en sert) ; **client réseau laissé** : M4 ne va jamais au registre, il demande à M2. |
| Les douze mois glissants (identité annuel − cumul N−1 + cumul N) et la série d'un concept | `knowledge/appariement_feed.py` (`douze_mois_glissants`, `serie_du_concept`) | **Repris derrière le contrat** (déjà importés par la reconstitution). |
| L'appariement par formule avec une carte rédigée par un modèle, et sa fiche | `appariement_feed.executer_appariement`, `appariement_cartes` (migration 042) | **Laissé** : non vivant (seulement par `bouclage`, outils et contrôles) ; une formule propre à une ligne du modèle appartient à M7-M8, trié à leur ouverture. |
| La publication de la reconstitution comme document dans `knowledge_entries` | `knowledge/socle_feed.py` | **Laissé** : remplacé par les tables de M4 (préfixe `comptes_`) ; l'ancien enchaînement continue de lire sa table. |
| La ventilation publiée (relevé par axe × ligne × membre × période, raccordé au total ; axes en donnée ; seuil d'acquisition significative) et le lecteur XBRL pur | `knowledge/ventilation.py`, `ventilation_xbrl.py`, `ventilation_publiee.yaml`, `contracts/ventilation_schema.py` | **Repris derrière le contrat**. Deux noms d'axe écrits dans le code (`ventilation.py:639,642`) passent au référentiel (charte 5). |
| La récupération des fichiers XBRL d'un dépôt (index, instance, étiquettes) et la publication de la ventilation | `knowledge/ventilation_feed.py` | **Laissé** : remplacé par une demande à M2. **M2 n'a aujourd'hui aucun genre pour l'instance XBRL détaillée d'un rapport** (`companyfacts` n'a pas les dimensions) : M4 déclare le besoin, un genre s'ajoute au référentiel de M2 et à son adaptateur — donnée, pas code (B1 de M2). |
| La famille de comptes déduite de l'archétype du titre (rentable, pré-revenus → industrielle ; financière → bancaire, sans gabarit, refusée) | `ventilation_feed._famille_du_titre`, `frameworks/modele_entreprise.yaml` | **Repris en idée** ; où se déclare la famille : question 1 (l'archétype est une propriété de l'ancien enchaînement). Une famille sans gabarit est une indisponibilité nommée, comme aujourd'hui. |
| Les changements de découpage et de périmètre (régimes, transitions typées, série cohérente, acquisition significative ; règles par libellé ou symbole interdites) | `knowledge/perimetre.py` | **Repris derrière le contrat** (déjà cité en exemple au registre). |
| L'assemblage pour l'architecte, les règles de structure du modèle, unités des formules | `modele_entreprise/*` | **Laissé** : trié à l'ouverture de M6-M7. |

Préfixe des tables : `comptes_` (0 table ni identifiant de ce préfixe dans `app/` et `tools/` le 2026-11-28, hors `socle_comptes` et une clé sans rapport dans `traducteur.py`) ; migration 066.

**Données réelles en base (2026-11-28)** — `companyfacts` rangé par M2 : NVDA 627 concepts US-GAAP,
exercices 2022-2027 ; RVMD 281, 2021-2026 ; **SpaceX 182, un seul trimestre (10-Q 2026), aucun
exercice** : ses comptes annuels n'existent que dans les tableaux du prospectus, sans données
structurées. C'est le cas qui pose la question 3.

## 2. Les demandes au fil du dossier (suite de B13, `07-avant-comite.md` § « À l'ouverture de M4 »)

M4 sait ce qui lui manque à partir de ce qu'il a reçu, sans modèle : les douze derniers mois exigent les
comptes intermédiaires depuis la clôture ; cinq exercices exigent les rapports antérieurs si les données
structurées ne les couvrent pas ; la ventilation exige l'instance détaillée du dernier rapport. Chaque
manque devient une **demande en cours de dossier** (M3 §2, 1 bis : collecte suivie par le chef de
dossier ; ce qui en dépend l'attend, le reste avance ; une même demande n'est collectée qu'une fois).
Ce que M4 demande, et quand, est journalisé : c'est la matière du point de décision de l'**option C**
(élargir le besoin initial) à la clôture de M4.

## 3. L'acceptation (charte, point 6) — écrite avant la construction

« Société fictive » : sans base, sans réseau, sans dépense ; « base » : base jetable ; « réel » : VPS.
Tout est gratuit (données SEC, code).

| # | Acceptation | Preuve |
|---|---|---|
| C1 | **Le cœur ne nomme aucun concept comptable, formulaire, axe, société ni place** : gabarits, axes et familles sont des référentiels ; ajouter une ligne au gabarit ou une famille ne touche aucun fichier de code. | garde des accès [C7] étendue aux concepts et axes ; société fictive |
| C2 | **Les comptes de NVDA et de RVMD bouclent avec les totaux publiés** : cinq exercices (ou ce qui existe), douze derniers mois, dernier bilan ; chaque total retombe dans la tolérance ou l'écart est affiché ; chaque case dit son état et son origine (document de M2, concept, période). | société fictive ; **réel** NVDA, RVMD |
| C3 | **Contrôle par l'ancien système** : pour NVDA et RVMD, chaque case de la reconstitution de M4 est comparée à celle de l'ancien code sur le même `companyfacts` ; 0 écart inexpliqué. | **réel**, outil gratuit, lecture seule |
| C4 | **Les ratios maison** se recalculent à la lecture, jamais rangés ; changer de convention change la version et l'empreinte. | société fictive |
| C5 | **La ventilation** de NVDA et de RVMD : chaque axe publié est relevé et raccordé au chiffre d'affaires publié, ou l'écart est dit ; les faits non rattachés sont listés, jamais perdus. | société fictive ; **réel** NVDA, RVMD (instance détaillée demandée à M2, C8) |
| C6 | **Deux découpages superposés** (un secteur opérationnel et une ventilation par produit, comme Apple ou Microsoft) sont rendus séparément, jamais additionnés. | société fictive (dette reprise de l'ancien plan) |
| C7 | **Le périmètre** : un changement de découpage et une acquisition significative sont typés ; la série comparable servie dit ce qu'elle exclut ; aucune règle par libellé ou par symbole. | société fictive ; réel NVDA (fixture `perimetre/nvda_reel.json`) |
| C8 | **Les demandes au fil du dossier** (§2) : pour NVDA et RVMD, M4 demande les comptes intermédiaires depuis la clôture et l'instance détaillée du rapport ; la collecte est suivie par le chef de dossier ; les fiches de l'ancien système qui citent les dépôts ainsi collectés sont retrouvées par `controle_ancien_systeme.sh` sans `--en-memoire`, chaque écart expliqué (ligne de base du 2026-11-22 : 41 fiches non demandées). Ce que M4 a demandé et quand est journalisé (option C). | société fictive ; base ; **réel** |
| C9 | **Une famille sans gabarit** (une banque) : indisponibilité nommée « famille sans gabarit », jamais des comptes industriels ; **une société sans kit** suit le gabarit généraliste. | société fictive ; fixture réelle JPM |
| C10 | **Une société sans données structurées suffisantes** (SpaceX : un trimestre, pas d'exercice) traverse sans plantage : ce qui existe est reconstitué, ce qui manque est nommé avec sa raison (selon la question 3). | société fictive ; **réel** SpaceX |
| C11 | **L'écran** montre, par émetteur, les comptes (états des cases, bouclage), les ratios, la ventilation, le périmètre, ce qui manque et les demandes faites. | réel |
| C12 | **Rien d'autre ne casse** : suite complète, seul rouge connu inchangé ; l'ancien enchaînement tourne tel quel. | réel |

## 4. Questions pour l'utilisateur

1. **Où se déclare la famille de comptes d'un émetteur ?** L'ancien code la déduisait de l'archétype du
   titre (une notion de l'ancien enchaînement). *Ce que ferait un vrai fonds* : la société est rangée
   dans un secteur à son entrée, depuis la classification officielle, et c'est ce secteur qui choisit
   l'analyste et ses gabarits.
   - (a, recommandé) Sur la fiche de l'émetteur (M1, sa spécialité) : le système la propose depuis le
     code d'activité du registre (une table de correspondance en donnée), signée et motivée, vous
     corrigez par une révision qui l'emporte (même logique que l'identité, #147). Sans code, la famille
     généraliste.
   - (b) Vous la choisissez à la main à chaque entrée.
2. **Les reclassements propres à un émetteur** (aujourd'hui trois concepts, NVDA et RVMD : par exemple
   des redevances à payer de RVMD). *Ce que ferait un vrai fonds* : l'analyste note les particularités de
   présentation d'une société, avec leur raison ; c'est une donnée du dossier, pas une règle générale.
   - (a, recommandé) Gardés en donnée de M4, rangés par l'identité maison, chacun avec son motif et la
     case qu'il déplace ; affichés à l'écran ; une règle générale les remplace dès qu'elle existe
     (principe 4 : on corrige la cause d'abord — on cherche la règle avant d'écrire l'exception).
   - (b) Interdits : seule une règle générale, ou la case reste « non déposée ».
3. **Les comptes qui n'existent qu'en texte** (SpaceX : le prospectus ; plus tard les sociétés de l'UE
   hors ESEF, le non coté). *Ce que ferait un vrai fonds* : un assistant ressaisit les états financiers
   du prospectus dans le gabarit, chaque chiffre pointé sur sa page.
   - (a, recommandé) M4 version 1 : données structurées seulement ; SpaceX reçoit son trimestre et
     « comptes annuels : aucune donnée structurée, prospectus à ressaisir » nommé. La ressaisie depuis la
     lecture de M3 (chaque chiffre cité à sa ligne, donc une pièce de M3) devient un lot à part, après
     NVDA et RVMD — débrayable vers la règle simple.
   - (b) La ressaisie dans M4 dès maintenant (SpaceX complet, mais un modèle ou un relevé de tableaux
     à écrire et à éprouver avant d'avoir passé NVDA et RVMD).
