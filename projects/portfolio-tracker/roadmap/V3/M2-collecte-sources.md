---
id: m2-collecte-sources
status: module ouvert (tri fait, acceptation écrite le 2026-11-16, AVANT le code ; à confirmer par l'utilisateur)
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

SpaceX devient donc le **troisième cas d'acceptation de M2**, à côté de NVDA et RVMD (proposition, § 3).

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

Les lignes « société fictive » se prouvent sans base, sans réseau et sans dépense (`check_collecte.py`,
rougi par `negatif_collecte.sh`) ; « base » sur une vraie base ; « réel » sur le VPS.

| # | Acceptation | Preuve |
|---|---|---|
| B1 | **Le cœur ne nomme aucun formulaire, aucun registre, aucune société** : il demande un genre de document ; l'adaptateur traduit par le référentiel. Ajouter un genre ou un formulaire ne touche que le référentiel. | garde des accès [C7] étendue aux noms de formulaires ; société fictive |
| B2 | **Une société sans numéro SEC traverse sans plantage** : chaque demande rend des documents (site, web) ou une indisponibilité nommée — jamais une exception. Idem pour une société non cotée, et pour une société sans fiche (indisponibilité « fiche absente », et le chef de dossier attend l'acte). | société fictive |
| B3 | **Une société récemment introduite** : « derniers comptes annuels » rend le prospectus d'introduction quand aucun rapport annuel n'existe encore, et le dit dans l'origine ; jamais un cumul trimestriel présenté comme une année. Dès qu'un rapport annuel est déposé, c'est lui. | société fictive ; **réel : SpaceX** |
| B4 | **Le document est gardé brut et jamais modifié** : le même document collecté deux fois n'est rangé qu'une fois (empreinte) ; une nouvelle version d'un document (amendement) est un document nouveau qui cite l'ancien. | société fictive ; base (table sans modification ni suppression) |
| B5 | **Chaque document dit d'où il vient et ce qu'il vaut** : son origine, et la qualification que M1 rend pour son adresse au jour de la collecte ; un document d'une source non admise est gardé mais marqué comme tel, il ne passe jamais pour admis. | société fictive |
| B6 | **Une source inconnue rencontrée part à l'évaluateur** (rôle distinct de celui qui collecte, A17 de M1) : il lit trois publications au moins, répond à la grille ; le système admet au seuil, met en suspens dessous. La collecte n'attend pas son verdict pour rendre les autres documents. | société fictive (évaluateur simulé) ; réel : une évaluation sur une vraie source |
| B7 | **Une page de relations investisseurs d'une autre société, rencontrée en collectant, est admise au fil de l'eau** (`admettre_pages_investisseurs`, A16 de M1). | société fictive |
| B8 | **La collecte est un travail suivi** : le pas de collecte rend « en cours », le chef de dossier le suit à chaque passage jusqu'à « fait » ou « indisponible » ; ce qui ne dépend pas d'elle avance (#146). Une collecte interrompue (redémarrage) reprend sans recollecter ce qui est déjà rangé. | société fictive ; base |
| B9 | **La dépense est comptée** : chaque recherche web et chaque appel de modèle (évaluateur) est déclaré au chef de dossier, qui fait sa pause à 1 $. Dépôts officiels et sites : 0. | société fictive |
| B10 | **Une fiche incomplète se complète depuis le registre officiel** : quand l'adaptateur des dépôts trouve l'émetteur au registre (par son symbole ou sa raison sociale), il propose une révision de la fiche (raison sociale, numéro, place, symbole, pays) avec le registre cité en motif. *Qui la signe : à arbitrer (§ 3, question 1).* Un homonyme (deux sociétés pour un nom) n'est jamais tranché par le système : indisponibilité nommée, acte attendu de l'utilisateur. | société fictive ; **réel : SpaceX** |
| B11 | **Dans le doute, indisponible** : document illisible (PDF non lu, page vide, erreur du registre après une seconde tentative) → indisponibilité nommée avec la raison ; jamais un document vide rangé comme bon. | société fictive |
| B12 | **L'écran** montre, par émetteur, les demandes, les documents rangés (origine, qualification, date), les indisponibilités et leur raison, la dépense. | réel |
| B13 | **NVDA et RVMD** : les derniers comptes annuels, les comptes intermédiaires et les annonces importantes depuis le 1er janvier 2026 sont collectés ; chaque document que l'ancien système a déjà lu pour ces genres est retrouvé (par son numéro de dépôt), chaque écart listé et expliqué. | réel |
| B14 | **Rien d'autre ne casse** : suite complète verte ; l'ancien code continue de tourner tel quel (M2 ne le rebranche pas : c'est M3 qui lira les documents de M2). | réel |

## 3. Questions pour l'utilisateur

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
