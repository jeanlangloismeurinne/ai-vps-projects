---
id: plan-avant-comite
status: plan-d-action-2026-11-13 — CONFIRMÉ par l'utilisateur le 2026-11-13 (ordre M0-M11, kit de spécialité, contradicteur après le premier comité)
created: 2026-10-16
updated: 2026-11-13 (réécrit après les arbitrages de l'évaluation d'architecture : reconstruction module par module)
project: portfolio-tracker
role: >
  LE plan d'action jusqu'au premier passage de NVDA en comité. Une seule version : ce fichier.
  Il remplace le plan du 2026-10-21 (tâches A1-F2 et leur journal), archivé tel quel dans
  `roadmap/archive/V3-07-avant-comite-plan-2026-10-21.md`. Les arbitrages qui le fondent :
  `EVALUATION-ARCHITECTURE-2026-11-13.md`, section « Arbitrages rendus ».
---

# Avant le comité — plan d'action

## Cible et méthode

**Cible inchangée** : premier passage de NVDA en comité, dossier complet, décision au procès-verbal.
RVMD reste le témoin (carte et squelette), sans viser son comité.

**Méthode changée** (arbitrage du 2026-11-13) : on ne finit plus l'ancien enchaînement, on **reconstruit
module par module sur une base propre**. Un module marche — seul, sur NVDA et sur RVMD — avant qu'on
ouvre le suivant. Le code existant est une carrière : on y reprend ce qui tient dans le contrat du
module, on laisse le reste, et ce qu'un module remplace est supprimé le jour où ce module est accepté.

*Ce que ferait un vrai fonds* : on ne recrute pas le modélisateur avant que la documentation sache
fournir un rapport annuel fiable ; chaque poste est rodé avant qu'un autre s'appuie sur lui.

## La charte d'un module (vaut pour tous)

1. Il **possède ses tables** ; personne d'autre ne les lit.
2. Il rend **un seul objet de sortie**, versionné, lu par une seule fonction. Un contrôle refuse tout
   autre accès (et vire au rouge quand on le casse).
3. Il se livre **avec son écran** : on voit ce qu'il produit.
4. Il se teste **seul**, sur une société fictive et des modèles simulés, sans dépense.
5. Rien de propre à une société, à un pays ou à une place de cotation n'est écrit dans son code :
   c'est une donnée des référentiels (principe 4 ; entreprises de l'UE et non coté à venir).
6. Son **acceptation est écrite avant** sa construction, et passée sur NVDA **et** RVMD.
7. Il s'ouvre par un **tri** de l'ancien code et des données déjà en base : repris tel quel / repris
   derrière le contrat / laissé. Les pièces déjà collectées se gardent si elles satisfont le contrat ;
   les réponses des anciens chapitres ne sont pas reprises (elles servent de contrôle, gratuitement).
8. Il déclare son pas au chef de dossier et **compte ce qu'il dépense** (modèles ET recherches web).

Tant que le taux d'erreur d'un module n'est pas mesuré, sa sortie est **lue par un humain** avant que le
suivant s'en serve (interrupteur par module, levé un à un — principe 3 : la lecture humaine est la
règle simple, l'automatisation son raffinement).

## Les modules, dans l'ordre

| # | Module | Rend | Acceptation (résumé) | Dépense |
|---|---|---|---|---|
| M0 | **Fondations** | Documents de cadre à jour (une constitution, un schéma des blocs, une seule ligne de base de la suite) ; documents inutiles supprimés ou archivés ; charte et garde des accès entre modules ; squelette du chef de dossier (état → pas suivant, pause tous les 1 $) ; NASDAQ sorti du chantier | Aucun document ne décrit un mécanisme supprimé ; le contrôle d'accès rougit sur un accès interdit ; le chef de dossier conduit une société fictive à travers des modules simulés et s'arrête à 1 $ | 0 |
| M1 | **Fiche de l'émetteur et sources** | Identité maison (numéro SEC facultatif), où la société publie, sa spécialité ; registre des sources : le système évalue et admet, chaque admission datée et motivée, vous suivez et corrigez | Ajouter un titre ne modifie aucun fichier de code ; une société sans numéro SEC a une fiche valide ; une source révoquée signale les pièces qui s'y appuient | 0 |
| M2 | **Collecte de sources** | À une demande (quoi, pour qui, depuis quand) : des documents bruts avec leur origine, ou « source indisponible » nommée. Adaptateurs : dépôts SEC, site de l'émetteur, web. Prévus, interface écrite : documents fournis, autre régulateur | Le cœur ne nomme aucun formulaire ; la société fictive sans numéro SEC traverse sans plantage | faible |
| M3 | **Base de connaissance** | Pièces datées, à extraits vérifiés, jamais modifiées | Chaque pièce se cite par sa ligne ; rien n'y entre sans origine | 0 |
| M4 | **Comptes et segments** | Comptes reconstitués, ratios maison, ventilation, périmètre, par famille de comptes | Les comptes de NVDA et RVMD bouclent avec les totaux publiés ; deux découpages superposés (Apple, cas fictif) sont séparés | 0 |
| M5 | **Filtres** | Alertes motivées au gérant (dette, autonomie, clauses, qui décide, hors compétence) ; jamais d'arrêt automatique | Sur RVMD l'autonomie de trésorerie est signalée avec sa pièce | faible |
| M6 | **Carte des sources de profit** | Inventaire élément × marché, classé, contrôlé contre les listes de l'émetteur ; débats de la thèse proposés, que vous complétez et validez en un lot | Chaque élément listé par l'émetteur est dans la carte **à chaque passage** ; deux passages donnent la même carte ; le relecteur retrouve les erreurs connues (étalons) | **première mesure payante** |
| M7 | **Modèle de l'entreprise** | Classeur : une ligne par source de profit, ses moteurs, cellules avec origine ; liste des cellules vides. Squelette construit par le code | Le total des lignes de la première année égale le chiffre d'affaires publié | 0 |
| M8 | **Recherche ciblée** | Pour une cellule vide : valeur, fourchette, pièce ou méthode ; effort selon le poids et les débats | Aucune cellule de poids sans pièce ; petites lignes sur leur tendance tant que leur somme reste sous 10 % | payant |
| M9 | **Jugements** | Pour chaque jugement : l'hypothèse qu'il déplace, le sens, la pièce | Chaque jugement nomme une cellule du classeur | payant |
| M10 | **Valorisation** | Valeur centrale, fourchette, ce que le prix suppose, marge de sécurité au cours daté | Changer une hypothèse recalcule sans appel de modèle | 0 |
| M11 | **Mémo et comité** | Mémo organisé autour de la thèse et des débats ; **décision du comité** au procès-verbal : décision, conviction, fourchette signée, marge de sécurité, conditions, indicateurs de suivi, date de revue | La décision NVDA se lit sans ouvrir aucune table de l'ancien système ; le comité ne voit que les exceptions | 0 |

Deux fonctions **transverses** grandissent avec les modules :

- **Chef de dossier** (automate sans modèle de langage, squelette en M0) : chaque module accepté lui
  ajoute un pas. Il avance seul jusqu'à « prêt pour le comité », ne s'arrête que pour un acte qui vous
  revient, et **fait une pause tous les 1 $ consommés sur un dossier, avec une estimation du coût
  restant jusqu'au comité**. On ne plafonne pas la qualité : on mesure le coût, et vous décidez.
- **Mesure de la qualité** (à partir de M6, premier module qui produit du sens) : dossiers étalons que
  vous relisez une fois (carte + une douzaine de réponses, NVDA et RVMD) ; relecteur indépendant (ne
  voit que la réponse et ses pièces) ; deux passages comparés. Le relecteur signale, il ne bloque pas.

**Spécialité** (ajout issu de la vérification « comme un fonds », confirmé le 2026-11-13) : un fonds a des
analystes par secteur, chacun avec ses sources, ses indicateurs et ses gabarits de modèle. Ici, UN
analyste générique reçoit un **kit de spécialité** tenu en donnée dans les référentiels (sources du
secteur, famille de comptes, moteurs types, questions propres, étalons). Ajouter un secteur — ou l'UE,
ou le non coté — ajoute un kit et un adaptateur, sans toucher aux modules. **Une entreprise sans kit
suit le parcours généraliste, qui doit rester assez souple pour bien l'analyser** : le kit affine, il
n'est jamais une condition d'entrée (acceptation de chaque module : il passe aussi SANS kit).

## Après le premier comité (prévu, non construit)

Sélection des titres : **c'est vous qui dites quoi analyser** ; un module de sélection pourra venir
plus tard · suivi d'une position (ce qu'un fait nouveau rouvre) · construction de portefeuille (lit la décision du
comité et elle seule) · contradicteur avant comité (défend la thèse inverse — confirmé : après le
premier comité) · sélection de titres à l'entrée (le sous-projet NASDAQ pourra en devenir une partie) · scénarios et probabilités (préalable au
comité de RVMD) · famille de comptes bancaire · émetteurs de l'UE · non coté (documents fournis et/ou
web : les deux cas arriveront) · MSFT de zéro, banc de dix entreprises.

## Ce qui ne change pas

La liste « Ce qui est fermé » de la reprise ; DeepInfra comme fournisseur unique (le modèle de chaque
rôle devient une donnée, et un changement de modèle rejoue les étalons) ; aucune mesure payante avant
M6 — la carte se mesurera quand sa collecte sera enregistrée sous le nouveau contrat, pour ne jamais
avoir à refaire une recherche complète.

## Dettes reprises de l'ancien plan

Elles sont rattachées au module qui les soldera, au moment de son tri : question 3 de l'arbre mal posée
et recouvrement clients × produit (M6) ; deux découpages superposés (M4) ; cours au moment des rachats,
chiffre relevé sans garde, datation d'une note de synthèse (M8-M9) ; passage au standard des anciennes
réponses : **sans objet** (elles ne sont pas reprises). Détail : plan archivé, sections C et « Dettes ».

## Journal

| Date | Module | Action | Preuve |
|---|---|---|---|
| 2026-11-13 | — | Arbitrages de l'évaluation consignés (26 commentaires du doc) ; plan réécrit par modules ; ancien plan archivé | `EVALUATION-ARCHITECTURE-2026-11-13.md` § Arbitrages rendus |
