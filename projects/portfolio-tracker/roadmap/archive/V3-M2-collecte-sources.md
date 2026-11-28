---
id: m2-collecte-sources
status: construit hors ligne (B1-B11, base 064 non appliquée, moteur/modèle/évaluateur réels le 2026-11-18) ; reste arbitrage de la grille d'évaluation, déclencheur, écran, lignes « réel »
created: 2026-11-16
project: portfolio-tracker
role: >
  Le dossier d'ouverture du module M2 « Collecte de sources » : le tri de l'ancien code, puis
  l'acceptation, écrite AVANT la construction (charte, points 6 et 7). Part dans `roadmap/archive/`
  le jour où M2 est accepté.
---

# M2 — Collecte de sources

*Ce que ferait un vrai fonds* : la documentation (le « centre de documentation » ou l'équipe de
données) reçoit une demande de l'analyste — « les derniers comptes annuels de SpaceX », « les
communiqués importants de NVDA depuis le 1er août » — et rend les documents eux-mêmes, avec leur
provenance, ou répond « ça n'existe pas encore » en disant pourquoi. Elle sait où chaque société
publie (la fiche, M1) et ne fait pas confiance à une source qu'elle ne connaît pas sans la faire agréer
(l'évaluateur, M1 A17). Elle ne lit pas les documents pour l'analyste : elle les trouve, les date, les
range tels quels.

## 0. Le cas qui ouvre le module : SpaceX (ajouté par l'utilisateur le 2026-11-16)

Premier émetteur entré par l'écran, et premier qui ne ressemble pas aux trois titres de départ :

- **Introduite au Nasdaq en juin 2026** (symbole SPCX ; numéro SEC 1181412, vérifié sur le registre
  SEC le 2026-11-16). **Aucun rapport annuel n'a encore été déposé.** Les derniers comptes annuels
  audités (exercice 2025) ne se trouvent que dans le **prospectus d'introduction** (déposé le
  2026-06-12) ; depuis : deux rapports trimestriels (août, octobre) et onze annonces importantes.
- Les données comptables structurées de la SEC ne contiennent que les trimestres : **aucune ligne
  annuelle**. Un système qui ne cherche les comptes annuels que dans les rapports annuels conclurait à
  tort « rien » — ou prendrait un cumul de neuf mois pour une année.
- Sa fiche (révision 1) est minimale : raison sociale « SPCX » (c'est le symbole), ni pays, ni cotation,
  ni numéro, ni lieu de publication. Selon la règle de M1 (A10), **aucune source n'est donc admise pour
  elle**, pas même les dépôts officiels.
- **L'ancien code s'arrête dès la première étape** sur un émetteur que le registre ne connaît pas par son
  symbole (`traducteur.py:580`, sans rattrapage) et refuse toute recherche web sans raison sociale
  officielle (`collecte_executor.py:530`) : c'est le défaut que M2 doit supprimer.

SpaceX est le **troisième cas d'acceptation de M2**, à côté de NVDA et RVMD (arbitré le 2026-11-16, § 3).

Ce que M2 ne fait pas pour SpaceX : l'analyser. Une société de lancement et de télécommunications par
satellite, avec une activité d'intelligence artificielle, n'a pas de kit de spécialité : elle suivra le
parcours généraliste (plan 07, « Spécialité »).

## 1. Le tri (charte, point 7)

Inventaire fait le 2026-11-16 par une recherche déléguée, deux affirmations relues dans le code
(`traducteur.py:580`, `collecte_executor.py:526-533`).

| Ce que l'ancien système contient | Où | Décision |
|---|---|---|
| Symbole → numéro SEC et raison sociale, par le registre des symboles de la SEC, gardés en mémoire du processus | `knowledge/edgar_feed.py` `resolve_cik`, `identite_de_l_emetteur` | **Repris derrière le contrat**, dans l'adaptateur « dépôts SEC » : il sert à **proposer** une fiche complétée (A10 ci-dessous), jamais à décider qui est l'émetteur. Le cœur ne le voit pas. |
| Liste des dépôts d'un émetteur (flux « submissions » de la SEC), gardée une heure | `knowledge/material_events.py` `_submissions` | **Repris** dans l'adaptateur « dépôts SEC » : c'est le catalogue qu'il interroge. |
| Téléchargement d'un dépôt complet et découpage en documents | `agents/v2/note_flash.py` `telecharger_soumission`, `extraire_documents` | **Repris** dans l'adaptateur (le texte brut est gardé tel quel, voir A4). Le choix des types lus (`_TYPES_LUS`) part au référentiel. |
| Les **noms de formulaires** dans le code : formes annuelles, périodiques, importantes (`_ANNUAL_FORMS`, `FORMES_RAPPORT_PERIODIQUE`, `MATERIAL_FORMS`, `PERIODIC_FORMS`, `ANNUAL_FORMS`, `_FORMS_10K/10Q`, l'expression `_FORME_SEC`, le défaut `'10-K'`) | `edgar_facts.py`, `material_events.py`, `ventilation_feed.py`, `collecte_executor.py`, `edgar_feed.py` | **Repris en donnée** : un référentiel « genre de document → formulaires, par registre », dans l'adaptateur. Le prospectus y entre (absent aujourd'hui). Les constantes de l'ancien code restent tant que l'ancien code s'en sert ; elles sont supprimées avec les modules qui les remplacent (M3, M4). |
| Données comptables structurées de la SEC (un concept, ou l'inventaire complet) | `knowledge/edgar_facts.py` | **Repris** dans l'adaptateur comme un genre de document (« données comptables structurées »), rendu brut. Leur lecture en postes comptables (`edgar_feed.POSTES`, choix du concept, devises) **n'est pas M2** : trié avec M4. |
| Fiches comptables écrites en base (`run_edgar_feed`, `build_edgar_entries`) | `edgar_feed.py` | **Laissé** : c'est de la lecture et du rangement (M3, M4). |
| Recherche web (Exa, Serper), domaines de l'émetteur d'abord | `knowledge/websearch.py` `web_search`, backends | **Repris derrière le contrat**, adaptateur « web ». Les domaines viennent de la fiche (déjà le cas depuis A15). |
| Lecture directe d'une adresse, repli sur la copie d'Exa ; HTML → texte ; PDF refusé | `websearch.py` `fetch_url`, `html_to_text` | **Repris** (adaptateurs « site » et « web »). Le PDF refusé devient un « indisponible » nommé, pas un silence. |
| Choix des passages pertinents d'un long document (plongements) | `websearch.py` `_finalise` → `document_search` | **Laissé** : M2 rend le document entier ; choisir les passages, c'est lire (M3). |
| Qualification d'une adresse par la fiche | `knowledge/fiche_emetteur.py` | **Remplacé** : M2 appelle `emetteurs.qualifier` (contrat de M1) ; ce lecteur provisoire reste pour l'ancien code. |
| Routage SEC / web d'une ligne de plan selon un texte libre (« source attendue ») | `collecte_executor.py` `router_source`, `_MOTS_DERIVATION` | **Laissé** : la demande à M2 nomme un **genre de document**, pas un formulaire ni une phrase ; c'est l'adaptateur qui sait où le chercher. |
| L'agent de recherche (modèle + outils, budget 360 s par ligne) qui cherche ET écrit des faits | `agents/v2/worker.py`, `collecter_un` | **Laissé** : il mêle collecte et lecture. Sa recherche web est reprise (ligne ci-dessus) ; l'extraction de faits ira à M3/M8. |
| Plans de collecte, liens aux questions, mandats ; carte d'appariement | `collection_plans`, `question_coverage`, `framework_mandates`, `appariement_cartes` | **Laissé** : propres à l'ancien enchaînement par questions. |
| En-tête d'identification envoyé à la SEC (une adresse de contact), pause de 0,3 s entre téléchargements, aucune reprise sur erreur | `edgar_facts._UA`, `note_flash._PAUSE_EDGAR_S` | **Repris et durci** : un seul détenteur, cadence bornée (règle publique de la SEC : 10 demandes/s), une seconde tentative sur erreur passagère, puis « indisponible » nommé. |

Ce que l'ancien système **n'a pas** et que M2 apporte : le document **brut** gardé (aujourd'hui seul
un extrait de texte survit dans `knowledge_entries`) ; le prospectus ; une réponse « indisponible »
toujours nommée ; une collecte suivie par le chef de dossier ; l'évaluateur réel des sources inconnues ;
une identité proposée depuis le registre officiel.

Préfixe des tables du module : `recueil_` (0 occurrence dans `app/` et `tools/` le 2026-11-16 ;
`collecte_` écarté : 58 occurrences dans l'ancien code).

## 2. L'acceptation (charte, point 6) — écrite avant la construction

Vocabulaire. Une **demande** : un genre de document (au référentiel : « derniers comptes annuels »,
« comptes intermédiaires », « annonces importantes », « document de convocation », « présentation aux
investisseurs », « page web »…), un émetteur, une date de départ. Une **réponse** : des documents bruts,
chacun avec son origine (adresse, registre, date de publication, date des faits couverts, empreinte),
ou une indisponibilité nommée (genre, émetteur, raison, adaptateurs essayés).

Les lignes « société fictive » se prouvent sans base, sans réseau et sans dépense (`check_recueil.py`,
rougi par `negatif_recueil.sh`) ; « base » sur une vraie base ; « réel » sur le VPS.

| # | Acceptation | Preuve |
|---|---|---|
| B1 | **Le cœur ne nomme aucun formulaire, aucun registre, aucune société** : il demande un genre de document ; l'adaptateur traduit par le référentiel. Ajouter un genre ou un formulaire ne touche que le référentiel. | garde des accès [C7] étendue aux noms de formulaires ; société fictive |
| B2 | **Une société sans numéro SEC traverse sans plantage** : chaque demande rend des documents (site, web) ou une indisponibilité nommée — jamais une exception. Idem pour une société non cotée, et pour une société sans fiche (indisponibilité « fiche absente », et le chef de dossier attend l'acte). | société fictive |
| B3 | **Une société récemment introduite** : « derniers comptes annuels » rend le prospectus d'introduction quand aucun rapport annuel n'existe encore, et le dit dans l'origine ; jamais un cumul trimestriel présenté comme une année. Dès qu'un rapport annuel est déposé, c'est lui. | société fictive ; **réel : SpaceX, constaté le 2026-11-22** (relu en base) : seul document du genre, le prospectus 424B4 n° 0001628280-26-042639 publié le 2026-06-12, mention « aucun rapport annuel n'est encore déposé… (#148) » dans l'origine ; aucun trimestriel rangé comme annuel. Date des faits vide : la pièce l'affichera « période non précisée » (M3 §4 q.1) |
| B4 | **Le document est gardé brut et jamais modifié** : le même document collecté deux fois n'est rangé qu'une fois (empreinte) ; une nouvelle version d'un document (amendement) est un document nouveau qui cite l'ancien. | société fictive ; base (table sans modification ni suppression) |
| B5 | **Chaque document dit d'où il vient et ce qu'il vaut** : son origine, et la qualification que M1 rend pour son adresse au jour de la collecte ; un document d'une source non admise est gardé mais marqué comme tel, il ne passe jamais pour admis. | société fictive |
| B6 | **Une source inconnue rencontrée part à l'évaluateur** (rôle distinct de celui qui collecte, A17 de M1) : il lit trois publications au moins, répond à la grille ; le système admet au seuil, met en suspens dessous. La collecte n'attend pas son verdict pour rendre les autres documents. | société fictive (évaluateur simulé) ; réel : une évaluation sur une vraie source |
| B7 | **Une page de relations investisseurs d'une autre société, rencontrée en collectant, est admise au fil de l'eau** (`admettre_pages_investisseurs`, A16 de M1). | société fictive |
| B8 | **La collecte est un travail suivi** : le pas de collecte rend « en cours », le chef de dossier le suit à chaque passage jusqu'à « fait » ou « indisponible » ; ce qui ne dépend pas d'elle avance (#146). Une collecte interrompue (redémarrage) reprend sans recollecter ce qui est déjà rangé. | société fictive ; base |
| B9 | **La dépense est comptée** : chaque recherche web et chaque appel de modèle (évaluateur) est déclaré au chef de dossier, qui fait sa pause à 1 $. Dépôts officiels et sites : 0. | société fictive |
| B10 | **Une fiche incomplète se complète depuis le registre officiel** : quand l'adaptateur des dépôts trouve l'émetteur au registre (par son symbole ou sa raison sociale), il propose une révision de la fiche (raison sociale, numéro, place, symbole, pays) avec le registre cité en motif. Le système la signe ; votre correction d'un champ l'emporte (#147). Un homonyme (deux sociétés pour un nom) n'est jamais tranché par le système : indisponibilité nommée, acte attendu de l'utilisateur. | société fictive ; **réel : SpaceX, constaté le 2026-11-22** : révision 2 de la fiche signée `systeme:documentation`, motif « identité lue au registre de la SEC (États-Unis), consulté le 2026-11-22 » ; SPACE EXPLORATION TECHNOLOGIES CORP, US, NASDAQ SPCX, numéro 1181412 ; la révision 1 de l'utilisateur (« SPCX ») reste à l'historique. La correction par l'utilisateur qui l'emporte n'est prouvée que sur société fictive |
| B11 | **Dans le doute, indisponible** : document illisible (PDF non lu, page vide, erreur du registre après une seconde tentative) → indisponibilité nommée avec la raison ; jamais un document vide rangé comme bon. | société fictive |
| B12 | **L'écran** montre, par émetteur, les demandes, les documents rangés (origine, qualification, date), les indisponibilités et leur raison, la dépense. | **réel, constaté le 2026-11-22** : `GET /v2/emetteurs/{NVDA,RVMD,SpaceX}/etude` → 200 ; par émetteur, les demandes (statut, dépense déclarée et constatée, 0 $), les documents (origine, qualification « sec.gov » niveau A, date de collecte) et leur lecture (lecteur 1.2.0). Aucune indisponibilité réelle encore : son affichage n'est prouvé que hors ligne (K12) |
| B13 | **NVDA et RVMD, le besoin initial** (reformulée le 2026-11-22 : un dossier s'initialise avec le dernier rapport annuel, M3 §4 q.2) : les derniers comptes annuels et leurs données comptables structurées sont collectés ; chaque fiche de l'ancien système qui cite ces dépôts est retrouvée (par son numéro de dépôt), chaque écart listé et expliqué. Les comptes intermédiaires et les annonces ne sont plus demandés ici : ils le seront par M4 au fil du dossier, et leur preuve est une ligne d'acceptation de M4 (`07-avant-comite.md` § « À l'ouverture de M4 »). | **réel** : dossiers du 2026-11-22 ; `tools/controle_ancien_systeme.sh` sans `--en-memoire` : 14 fiches sur les dépôts collectés → 12 retrouvées, 2 écarts expliqués, 0 inexpliqué (41 dépôts non demandés, 2 d'une autre société) |
| B14 | **Rien d'autre ne casse** : suite complète verte ; l'ancien code continue de tourner tel quel (M2 ne le rebranche pas : c'est M3 qui lira les documents de M2). | **réel, constaté le 2026-11-22** (commit `c41a5cf`) : 92 scripts, 7 107 assertions, seul rouge `check_signature_modele_persist` (rouge connu, données de l'ancien enchaînement, hors M2) ; chiffre dans `checks/LIGNE_DE_BASE.md` |

## 3. Questions pour l'utilisateur — tranchées le 2026-11-16 (les trois recommandations retenues)

> (1) a : le système complète l'identité, signé, révocable (#147) ; (2) oui, le prospectus (#148) ;
> (3) oui, SpaceX troisième cas.

1. **Qui complète la fiche d'une société quand le registre officiel la connaît ?** Cas réel : SpaceX
   a été saisie avec « SPCX » comme raison sociale ; le registre de la SEC dit « Space Exploration
   Technologies Corp », numéro 1181412, Nasdaq, SPCX. *Ce que ferait un vrai fonds* : l'identité d'une
   société cotée est remplie par l'équipe de données depuis la source officielle (registre du
   régulateur, fournisseur de référentiel), pas tapée par l'analyste ; l'analyste corrige si c'est faux.
   - (a, recommandé) Le système complète lui-même, signé, registre cité en motif ; vous corrigez par
     une révision qui l'emporte (même logique que les sources, #144). Les lieux de publication (site,
     relations investisseurs) restent à vous ou à la collecte web, jamais devinés.
   - (b) Le système propose, la révision n'entre qu'après votre clic.
2. **Une société récemment introduite** : tant qu'aucun rapport annuel n'existe, son prospectus
   d'introduction tient lieu de « derniers comptes annuels » (B3) — c'est la pratique : il contient
   les comptes audités et c'est le document de référence jusqu'au premier rapport annuel. À confirmer.
3. **SpaceX comme troisième cas d'acceptation de M2** (à côté de NVDA et RVMD), parce qu'il est le
   seul à exercer B3 et B10 sur du réel. Elle ne vise pas le comité.

## 4. Ce que M2 ne fait pas (dit, pas caché)

- **Lire** : extraire un chiffre, choisir un passage, écrire une pièce citable — c'est M3.
- **Décider quoi collecter** : c'est le module qui a besoin de l'information (M4, M6, M8) qui demande.
- **Les documents fournis à la main** et **les autres régulateurs** : interface écrite (un adaptateur
  de plus, B1), pas construits.

## 5. Construit hors ligne (2026-11-16)

Module `app/modules/recueil/` (contrat 1.0.0, préfixe `recueil_`), détail et limites dans son
`ARCHITECTURE.md`. Lignes « société fictive » B1-B11 : `check_recueil.py` **63/0**,
`negatif_recueil.sh` **43/43** ; garde des accès [C7] étendue aux formulaires, registres et places
(`negatif_charte_modules.sh` 27/27) ; M1 gagne le geste `completer_identite` (#147 ; `negatif_emetteurs.sh`
49/49). Suite **6 700**, seul rouge : les données RVMD de l'ancien enchaînement (connu).

Ce que la construction a appris (et corrigé avant d'écrire la suite) :
- **Le registre ne remplit pas `isForeignLocation`** pour une société domestique (nul pour NVIDIA et
  SpaceX, mesuré) : le pays se déduit de l'État de l'adresse d'affaires, liste en donnée.
- **La dépense de l'évaluateur arrive après la collecte** : déclarée par le pas de collecte, elle
  n'aurait jamais été comptée (le pas est déjà fait). Elle a son pas, `pas_evaluation`, dont personne
  ne dépend : le dossier avance, la dépense est déclarée quand le jugement est rendu.
- **Une réponse qui aboutit garde la trace des sources essayées avant** (un PDF non lu sur le site,
  trouvé ensuite sur le web) : sans elle, l'échec du site disparaissait.
- **La raison principale d'une indisponibilité est la plus précise** : un document trouvé mais
  illisible passe devant un site injoignable (tous les essais restent énumérés).
- **La collecte vient toujours après la fiche**, garanti par le pas lui-même, pas par l'appelant.

**Passage à blanc réel** (2026-11-16, en mémoire, aucune écriture, registre gratuit) sur la fiche
SpaceX telle qu'en production (« SPCX », rien d'autre) : identité complétée — « SPACE EXPLORATION
TECHNOLOGIES CORP », 1181412, NASDAQ, US, signée `systeme:documentation` ; « derniers comptes
annuels » → le prospectus 424B4 du 2026-06-12 (11,9 Mo), mention à l'appui ; deux 10-Q ; trois 8-K
d'octobre-novembre avec le communiqué EX-99.1. Hors fiche admise en mémoire, tous marqués non admis
(en production, `sec.gov` est admis).

**Rangement en base construit le 2026-11-16** (migration 064, NON appliquée en production ;
`recueil/depot_base.py`) : `check_recueil_persist.py` **59/0** sur base jetable (063 puis 064), zéro
résidu ; `negatif_recueil_persist.sh` 7 mutations + 9 sur la migration. Trois mutations du dépôt sont
arrêtées par la base avant leur assert (droit UPDATE retiré, contrainte de cohérence) : l'assert R5
lancé SEUL sous mutation rougit bien (3 échecs nommés), il n'est que masqué dans la suite. Tant que
064 n'est pas appliquée, `check_recueil_persist` est rouge (R0, nommé) dans `run_all.sh` au VPS.

**Moteur, modèle et évaluateur réels construits le 2026-11-18** (`adaptateurs/exa.py`,
`adaptateurs/deepinfra.py`, `evaluateur.py`, leurs référentiels) : `check_recueil_evaluateur.py`
**53/0**, `negatif_recueil_evaluateur.sh` **38/38**. Essais réels EN MÉMOIRE (`tools/essai_evaluateur.sh`,
aucune écriture au journal des sources), ~0,01 $ par source :
- Reuters : lecture directe refusée (401), texte rendu par le moteur ; 15/15, admise sous « presse
  financière », stable sur trois passes.
- MarketBeat (alertes boursières générées, « Written by MarketBeat », encart d'abonnement) : **15/15,
  admise aussi**, stable. La grille ne voit pas la différence. Grille resserrée mesurée (auteur = une
  personne nommée ou un organisme public ; un encart d'abonnement = promotionnel) : Reuters 14/15
  (admise), MarketBeat 9/15 (en suspens). **Appliquée le 2026-11-18 sur accord de l'utilisateur**
  (référentiel de M1 1.3.0).
- Appris en chemin (corrigé avant d'écrire le contrôle) : une recherche limitée à un site rend ses pages
  de rubrique (listes, plan du site) — pages datées d'abord, requête rédigée comme un sujet d'article,
  catégorie actualités ; ne relire par le moteur que ce qui manque ; le fournisseur répond souvent
  « occupé » (429) — reprises écrites au référentiel ; un essai manqué garde ce qu'il a payé.
- Modèle : ~~DeepSeek-V4-Flash-0731 retenu ; V4.1-Flash écarté, verdict instable~~ — **diagnostic
  faux, corrigé le 2026-11-18** (5 passages par source, grille 1.3.0, mêmes textes) : V4.1 n'était pas
  instable, il était exigeant sur des APERÇUS. Deux des trois articles Reuters ne sont lus que par
  le moteur, ~1 000 caractères coupés avant le corps (Reuters 401) ; V4.1 y répond « non » (la
  consigne le demande) et Reuters tombe pile au seuil (12-13/15), où une réponse qui bascule change le
  verdict. V4-Flash accordait 15/15 à ces aperçus et rangeait MarketBeat sous « rédaction
  spécialisée » (9/15) ; V4.1 : MarketBeat 3/15, aucun critère. **V4.1-Flash retenu** (utilisateur).
- **Un aperçu n'est pas une publication** (arbitrage de l'utilisateur, 2026-11-18) : le modèle dit
  d'abord si chaque texte est complet ; un aperçu ne compte pas ; s'il en manque, échec nommé.
  `check_recueil_evaluateur` 60/0, négatif 44/44. Réel : Reuters → « 1 publication complète sur 3,
  lues incomplètes : … » (stable) ; MarketBeat 3/15, en suspens (stable sur 3 passes). Appris : le
  modèle prenait d'abord NOTRE coupe à 6 000 caractères pour un aperçu — elle est maintenant
  annoncée en tête de la publication.

Reste, dans l'ordre proposé : (1) ~~rangement en base~~ ; (2) ~~moteur réel (Exa) et évaluateur réel~~ — reste l'arbitrage de la grille ; (3) ~~le déclencheur et la tâche de fond qui rangent l'`Envoi`~~ (M3 §5) ; (4) ~~l'écran (B12)~~ (construit avec K12, M3 §5) ; (5) les
lignes « réel » : SpaceX (B3, B10), une évaluation réelle (B6), NVDA et RVMD (B13, reformulée et constatée le 2026-11-22 : besoin initial seul), suite (B14).

## 6. Lire la presse payante — mesures et proposition (2026-11-18, question ouverte)

Demande de l'utilisateur : « ce cas va se reproduire souvent avec les sources de bonne qualité ;
trouver la meilleure façon de les exploiter ». L'admission n'est pas le problème : les 15 titres de
presse financière de l'ancienne liste sont admis en production (reprise A14). Le problème est la
**lecture** de leurs articles pendant la collecte.

**Mesuré** (5 articles de résultats par titre, recherche Exa limitée au domaine + lecture directe
depuis le VPS, ~0,13 $) :
- **Lisibles en entier** : fool.com, latribune.fr, cnbc.com (par le moteur ; direct 403).
  handelsblatt.com : 1 sur 5 en entier, le reste ~1 500 caractères (probables aperçus « H+ »).
- **Aperçu seulement** : reuters.com (1 000 car., 4 sur 5 en 401 direct), bloomberg.com (~900),
  wsj.com (~700), barrons.com (~200), marketwatch.com (700-2 600), nikkei.com (300-770),
  seekingalpha.com (300-500), economist.com (1 000-2 000).
- ft.com, lesechos.fr, morningstar.com : la recherche rend surtout des COMMUNIQUÉS d'émetteurs
  rediffusés (markets.ft.com, lesechos-comfi, pr-newswire) — complets, mais c'est l'émetteur qui parle.
- **La même dépêche existe ailleurs en entier** : une recherche par le titre de l'aperçu (hors
  domaines payants, ~0,007 $) rend, pour 4 dépêches sur 4, le communiqué d'origine de la société
  (nu.com, conocophillips.com, berkshirehathaway.com, ti.com) ET des reprises sous licence créditées
  « Reuters » en entier (channelnewsasia, bnnbloomberg.ca, cnbc.com, investing.com, uol.com.br).

**Proposition (en attente de l'utilisateur)** — trois étages, du gratuit au payant :
1. **L'aperçu est un signal, pas une pièce.** Titre, date, signature et puces de résumé d'un titre
   admis disent qu'un événement a eu lieu : la collecte s'en sert pour aller chercher la pièce
   d'origine (communiqué, 8-K, page IR), déjà dans son ordre d'autorité. Aucun chiffre n'est tiré
   d'un aperçu. C'est ce que fait un analyste avec un fil d'agence.
2. **Reprise sous licence reconnue à son empreinte.** Le texte complet d'une dépêche peut être pris
   chez un diffuseur si (a) il crédite l'agence admise et (b) il contient mot pour mot le chapeau de
   l'aperçu lu chez l'agence. La pièce garde l'agence comme source et le diffuseur comme lieu de
   lecture. Règle générale, vérifiable par le code, aucune liste de diffuseurs.
3. **Abonnement** (si l'utilisateur en a un) : lecture avec ses accès, ou API sous licence — coût,
   conditions d'utilisation et rangement des identifiants à trancher.

Ce que la presse apporte en plus de la pièce d'origine — citations de dirigeants, consensus des
analystes, contexte, informations pas encore publiées par la société — se trouve en partie dans
d'autres pièces (transcription de la conférence de résultats, base de consensus) : à voir à M3+.

## 7. Lire la presse payante — construction des étages 1 et 2 (accord de l'utilisateur, 2026-11-19)

Accord : « ok avec tes propositions sur les sources reprises » ; consigne : optimiser la dépense
DeepInfra. L'étage 3 (abonnement) n'est pas construit (aucun abonnement déclaré).

**Mesuré avant d'écrire** (2026-11-19, 0,035 $ Exa, 0 $ DeepInfra) : 4 dépêches Reuters lues par le
moteur (Exa en rend 1 000 caractères au plus) ; une recherche par leur titre, hors reuters.com, avec
le texte. Les reprises sous licence contiennent mot pour mot 2 à 5 phrases entières de l'aperçu
(phrase = au moins 8 mots) et nomment Reuters ; les autres textes (8-K, page IR, AP, transcription)
n'en contiennent AUCUNE. La même recherche rend la pièce d'origine (sec.gov, broadridge-ir.com,
ir.sqm.com) dans 3 cas sur 4 : UNE recherche sert les deux étages, et la reconnaissance est du code,
sans modèle.

**Mesuré côté DeepInfra** (une évaluation réelle, fool.com, deux passes) : 6 372 jetons d'entrée,
1 327 de sortie, 0,0010 $ ; la seconde passe identique : 6 272 jetons servis par le cache, 0,0004 $
(prix lus à l'API : remise de 51 %, cache à 3 % du prix d'entrée, niveau « flex » −20 %, accepté et
mesuré). La sortie fait 39 % d'un appel neuf, 93 % d'un appel servi par le cache. Exa coûte 7 fois
plus que le modèle par source évaluée.

Acceptation (écrite avant le code) :

| Ligne | Ce qui doit être vrai |
|---|---|
| P1 | Un aperçu n'est jamais rangé comme pièce : une page web refusée en lecture directe (accès refusé) n'est rangée ni telle quelle ni par le texte du moteur |
| P2 | Étage 1 : son titre sert à UNE recherche hors du domaine de l'agence ; un résultat sur un lieu de la fiche de l'émetteur, lisible, est rangé comme pièce d'origine, mention « signalée par » l'aperçu ; il passe devant une reprise |
| P3 | Étage 2 : une reprise est reconnue si elle nomme l'agence, contient mot pour mot une phrase entière de l'aperçu et est plus longue que lui ; rangée sous l'adresse de l'aperçu (la source reste l'agence, M1 la qualifie), lue chez le diffuseur (identifiant, mention) ; aucune liste de diffuseurs |
| P4 | Le diffuseur n'est jamais une source rencontrée : ni évaluation, ni admission de pages |
| P5 | Rien de reconnu, ou un aperçu sans titre : indisponibilité nommée « aperçu » qui désigne l'aperçu ; chaque suivi est payé et compté ; au plus `suivis_max` suivis par demande |
| P6 | Évaluateur : une publication déclarée aperçu est remplacée par sa reprise reconnue, le modèle rejuge UNE fois en sachant où elle a été lue ; sinon l'échec nommé de V8, qui dit ce qui a été cherché |
| P7 | DeepInfra : niveau de service et prix (cache compris) au référentiel ; la partie fixe du message (grille, critères, format) précède tout ce qui varie, pour que le cache la serve d'une source à l'autre ; aucun appel au modèle dans les étages 1 et 2 |

**Construit le 2026-11-19** (hors ligne, puis essais réels EN MÉMOIRE ; convention #149) :
`recueil/adaptateurs/apercus.py` + `apercus.json`, branchés dans `web.py` (collecte) et
`evaluateur.py`. `check_recueil_evaluateur.py` **92/0** (fixture copiée du réel :
`checks/fixtures/recueil/apercu_reuters.json`), `negatif_recueil_evaluateur.sh` **71/71** ;
`check_recueil` 63/0, `negatif_recueil` 43/43 (mutation B11 recalée sur la nouvelle raison
« apercu »), charte 22/0 et 27/27.

Essais réels (2026-11-19, ~0,06 $ Exa, ~0,003 $ DeepInfra au total) :
- **Collecte, étage 1** : dépêche Reuters Broadridge (401) avec une fiche dont le lieu est
  broadridge-ir.com → le communiqué d'origine est rangé, « signalée par » l'aperçu. Appris : le site
  IR refuse la lecture directe (403) ; le texte rendu par la recherche (déjà payé) est rangé en texte
  brut — corrigé avant d'écrire le contrôle ([P2]).
- **Collecte, étage 2** : même dépêche, fiche sans lieu → reprise lue chez investing.com, rangée sous
  l'adresse Reuters, motif « nomme reuters, contient … » ; 0,008 $, 0 $ de modèle.
- **Évaluateur** : reuters.com avec les quatre dépêches mesurées le matin → premier jugement : deux
  aperçus ; reprises reconnues chez spokesman.com et investing.com ; second jugement : **admise**
  (presse financière, 5/5 par publication). Modèle 0,0008 $ pour deux jugements, Exa 0,017 $.

Côté DeepInfra (consigne de l'utilisateur), ce qui a changé et ce que ça vaut :
- **Niveau de service « flex »** : −20 % sur tous les appels de M2 (tâches de fond).
- **Partie fixe du message en tête** (critères, échelle, questions, format, puis la source) : servie
  par le cache d'une source à l'autre (relevé : 896 à 1 280 jetons en cache dès le premier appel
  d'une nouvelle source, 2 816 au second jugement ; le cache coûte 3 % du prix d'entrée).
- **Numéro au lieu de l'adresse** : le modèle recopiait l'adresse de chaque publication ; une coquille
  (« tecnology ») a fait rejeter une réponse payée le 2026-11-19. Il écrit maintenant 1, 2, 3 : moins
  de jetons de sortie, et ce mode d'échec disparaît. Appris en chemin : un gabarit qui montrait le
  numéro entre guillemets a fait écrire « "1" » — le format le montre désormais comme un entier ([V5]).
- **Aucun modèle dans les étages 1 et 2** ; un second jugement seulement si TOUS les aperçus ont une
  reprise (les recherches s'arrêtent au premier manque).
- Le poste dominant d'une évaluation reste Exa (~0,007-0,017 $ contre ~0,0004-0,0008 $ de modèle).

**Ouvert — à arbitrer par l'utilisateur** : le modèle a jugé COMPLÈTE la dépêche Visa que le moteur
coupe à 1 000 caractères en plein mot (« … We did n ») ; Reuters a donc été admise avec un aperçu
compté comme publication (les deux autres étaient de vraies reprises, le verdict ne change pas ici).
Proposition : un texte lu par le moteur après un accès refusé et qui s'arrête en plein mot est
suivi AVANT le modèle (code, ~0,008 $ Exa par page) ; sa reprise, si elle existe, le remplace, sinon
le modèle juge comme aujourd'hui. Coût Exa contre rigueur : à trancher.

## 8. Texte coupé en cours de phrase : suivi avant le modèle (accord de l'utilisateur, 2026-11-21)

Accord : « ok pour ta proposition sur les sources tronquées » (§7, fin).

**Précisé avant d'écrire** : la proposition disait « en plein mot ». L'aperçu Visa réel de la fixture
(copié le 2026-11-19, 1 000 caractères) finit sur « … jumped 9% in the » : des mots entiers, une phrase
interrompue. Une règle « en plein mot » l'aurait laissé passer. Règle construite : **un texte relu par
le moteur après un accès refusé qui ne finit pas sur une fin de phrase** (`.!?…`, après guillemets,
parenthèses et emphase fermants ; `apercus.json` 1.1.0) est interrompu — le mot coupé en est un cas.
Un texte qui atteint le plafond demandé au moteur (12 000 caractères) a été coupé par nous : pas suspect.
Les textes lus en direct ne sont pas concernés (aucune mesure ne les montre coupés).

Ce que fait l'évaluateur : le texte interrompu est suivi (`apercus.suivre`, une recherche, aucun
modèle) AVANT le jugement ; sa reprise reconnue le remplace (le modèle ne voit jamais l'aperçu, un seul
jugement). Sans reprise, le modèle juge le texte comme avant ; s'il le déclare aperçu, l'échec nommé dit
ce qui a été cherché et la recherche n'est pas repayée. Une reprise elle-même déclarée incomplète n'est
pas suivie à nouveau.

Preuve : `check_recueil_evaluateur.py` **101/0** ([P8], sept lignes ; [P6] passe désormais sur un aperçu
qui finit sur une phrase entière, le cas que seul le modèle peut signaler), `negatif_recueil_evaluateur.sh`
**80/80** (neuf mutations [P8], dont « la règle en plein mot seulement » : rouge sur l'aperçu réel) ;
`check_recueil` 63/0, `negatif_recueil` 43/43, charte 22/0.

**Essai réel en mémoire (2026-11-21, reuters.com, la dépêche Visa rencontrée)** : deux passages,
~0,033 $ Exa et ~0,0011 $ de modèle au total. Au second (outil d'essai qui imprime désormais chaque
publication lue, son lieu de lecture et sa fin) : la dépêche **Lennar** relue par le moteur était
interrompue → suivie avant le modèle → reprise reconnue chez marketscreener.com → un seul jugement
(0,0003 $), Reuters admise (presse financière, 15/15). La dépêche Visa a été lue en entier ce jour-là
(6 000 caractères, coupe de l'équipe) : le cas du 2026-11-19 ne s'est pas reproduit, la règle l'est
par la fixture copiée du réel.

Reste ouvert (dit) : un aperçu qui finit sur une phrase entière et que le modèle juge complet.
