---
id: m3-base-connaissance
status: ouvert le 2026-11-21 ; K0-K9 construits hors ligne le même jour (check_connaissance 49/0, négatif 30/30) ; besoins et déclencheur (K10, K11 sur société fictive) construits hors ligne le même jour (check_etude 39/0, négatif 31/31) ; rangement en base (migration 065, K5 et K10 « base ») et tâche planifiée construits le 2026-11-21 (check_connaissance_persist 73/0 sur base jetable, négatif 10/10 + 9/9 ; 065 NON appliquée) ; restent écran, réel
created: 2026-11-21
project: portfolio-tracker
role: >
  Le dossier d'ouverture du module M3 « Base de connaissance » : le tri de l'ancien code, l'interface
  commune entre les modules qui ont besoin de documents et la collecte, puis l'acceptation, écrite AVANT
  la construction (charte, points 6 et 7). Part dans `roadmap/archive/` le jour où M3 est accepté.
---

# M3 — Base de connaissance (le lecteur commun)

*Ce que ferait un vrai fonds* : la documentation range le rapport annuel tel qu'il est arrivé ; quelqu'un
le **met en lecture** — pages et lignes numérotées, une fois pour toutes — et chaque analyste cite ensuite
« rapport annuel 2025, ligne 4 512 » plutôt que de recopier ce qu'il croit y avoir lu. Une citation qui ne
se retrouve pas mot pour mot dans le document n'entre pas au dossier. Le comité peut toujours ouvrir la
pièce et la ligne. Et ce n'est pas la documentation qui décide quoi collecter : c'est l'analyste qui en a
besoin (le modélisateur demande les comptes parce qu'il doit modéliser).

**Pourquoi M3 s'ouvre avant l'acceptation de M2** (décidé par l'utilisateur le 2026-11-21) : tester la
collecte sur un besoin réel plutôt que sur une liste de demandes figée. Les lignes « réel » de M2
(SpaceX, NVDA, RVMD) seront passées avec M3 branché derrière.

## 0. Ce que M3 rend

Deux choses, pour chaque émetteur :

- **La lecture d'un document** : pour chaque document brut rangé par M2, son texte en **lignes
  numérotées** (une ligne = un paragraphe, un titre, ou une ligne de tableau dont les cellules sont jointes
  — on cite la ligne du tableau, pas la cellule, #141), produit par le code, sans modèle, toujours le même
  pour le même document. Ou une lecture **impossible**, nommée (vide, binaire illisible), ou **sans objet**
  (données structurées : lues par le module qui les comprend, M4).
- **Les pièces** : un extrait d'une lecture, **vérifié mot pour mot** (règles #126 et #141, inchangées),
  rattaché à son document et à ses lignes, avec la provenance et les dates du document, et l'auteur qui l'a
  cité (un module, un rôle). Une pièce n'est jamais modifiée ; rien n'y entre sans document d'origine.

Ce que la pièce vaut (admise, révoquée, niveau) n'est **pas rangé avec elle** : c'est M1 qui le dit, et
M3 le redemande **à la lecture** — une source révoquée demain se voit sur les pièces d'hier.

## 1. Le tri (charte, point 7)

Inventaire du 2026-11-21 (recherche déléguée ; décomptes relus en base en lecture seule).

| Ce que l'ancien système contient | Où | Décision |
|---|---|---|
| La vérification mot pour mot d'un extrait, et le remplacement d'un extrait court par sa ligne s'il est unique | `knowledge/citation.py` (`normaliser`, `extrait_introuvable`, `etablir_extraits`) | **Repris tel quel derrière le contrat** (au registre, `reprises`) : il reste le détenteur unique, partagé avec la note flash et le collecteur de l'ancien code tant qu'ils vivent (#46). Il partira dans M3 le jour où ces deux lecteurs seront retirés. |
| Le texte contre lequel on vérifiait un extrait | `agents/v2/tools.py` `RetrievalLog.textes_de` | **Remplacé** : ce texte n'existait qu'en mémoire, le temps d'un passage, souvent déjà réduit à quelques passages (`_finalise`) ; une pièce ne pouvait donc plus jamais être revérifiée. M3 vérifie contre la **lecture rangée du document entier**, et la garde. |
| La table des documents bruts | `knowledge_documents` (migration 024) | **Laissé** : jamais écrite (0 ligne), aucun code ne la lit. Les documents bruts sont désormais ceux de M2. |
| La table des fiches | `knowledge_entries` (1 257 lignes, 969 courantes ; 0 rattachée à un document) | **Laissé** à l'ancien code, qui continue de la lire (une trentaine de lecteurs). Les fiches ne sont pas reprises (charte 7) ; **les 215 fiches à extraits vérifiés servent de contrôle** : 57 citent un dépôt SEC (NVDA 25, RVMD 32), que M2 recollecte gratuitement → ligne K13. Les 158 autres citent des pages web : les recollecter coûterait, elles ne sont pas rejouées. |
| Une fiche « remplacée » par une plus récente (`superseded_by`, mise à jour en place) | `service.store_knowledge`, cinq flux | **Laissé** : une pièce de M3 n'est jamais remplacée ; quel fait est le plus récent, c'est le module qui cite qui le juge (#111). L'ancien « ajout seul » n'était qu'une convention (aucune protection en base) : M3 le fait tenir par la base. |
| Le découpage en passages (~1 200 caractères) et le classement par plongements (bge-m3, DeepInfra) | `document_search.py`, `embeddings.py`, `websearch._finalise` | **Laissé pour l'instant** (question 3) : M3 rend une recherche par les mots, gratuite, qui renvoie document et lignes. Le classement par le sens se reprendra quand un module qui cherche (M6, M8) en aura besoin. |
| Le niveau d'une source par type de source, abaissé avec l'âge | `service.compute_reliability` | **Laissé** : le niveau d'une source est celui que M1 rend (#144, #145) ; l'âge d'une pièce est jugé par celui qui la cite. |
| La nature d'une fiche (mesure, interprétation, événement) | `common.derive_nature`, colonne `nature` | **Laissé** : c'est une propriété de l'AFFIRMATION, pas du document ; elle appartient au module qui affirme (M8, M9). |
| Les deux dates d'une fiche : date du fait, date du document (#79) | `knowledge/datation.py` | **Repris en idée** : la pièce porte les dates du document (de M2) et, quand l'auteur la dit, la période du fait cité (question 1). Le code est réécrit (il vivait avec les colonnes de `knowledge_entries`). |
| La fraîcheur d'une pièce selon ce qu'elle fonde, et son actualité depuis le dernier événement important | `duree_de_vie.py`, `actualite.py`, `staleness.py` | **Laissé** : c'est un jugement sur l'usage (#129), trié avec M8-M9. |
| Le fichier figé de ce qu'une analyse a cité | `analysis_knowledge_refs` | **Laissé** : sans objet, une pièce de M3 ne bouge pas. |

Préfixe des tables : `connaissance_` (0 occurrence dans `app/` et `tools/` le 2026-11-21 ; `pieces_` écarté :
109 occurrences, dont `pieces_ecartees` ; `lecture_` écarté : 59).

## 2. L'interface entre les besoins et la collecte (demandée par l'utilisateur le 2026-11-21)

Un seul chemin pour tous les modules qui ont besoin de documents (M4 comptes, M6 carte, M8 recherche
ciblée, et ceux d'après) :

1. **Chaque module déclare ses besoins, en donnée**, dans son référentiel : une liste de genres de
   document (le vocabulaire de M2 : « derniers comptes annuels », « comptes intermédiaires »…) et, pour
   les genres qui s'étendent dans le temps, depuis quand. Rien d'autre : ni formulaire, ni registre, ni
   adresse. C'est le besoin **initial**, celui qui ouvre le dossier.
1 bis. **Un module demande aussi au fil du dossier** (arbitrage du 2026-11-21, question 2) : on remonte
   jusqu'à ce qui est nécessaire pour construire le modèle de l'entreprise, pas plus. Un module qui, en
   travaillant, constate qu'il lui manque quelque chose (les comptes annuels de l'exercice d'avant pour
   lire une tendance, les trimestriels depuis la clôture) le demande par le même vocabulaire ; sa demande
   devient une collecte suivie par le chef de dossier, et ce qui en dépend l'attend (#146).
2. **Le chef de dossier rassemble** les besoins des modules du parcours et en fait le pas de collecte.
   Deux modules qui demandent le même genre ne le font collecter qu'une fois.
3. **M2 collecte**, comme aujourd'hui ; **M3 lit** chaque document arrivé ; le module qui en avait besoin
   cite ses pièces par M3.

Ajouter un module consommateur ne touche ni la collecte, ni la lecture, ni le chef de dossier : il
déclare ses besoins, c'est tout (ligne K11).

**Le premier besoin réel** : celui des comptes (M4), écrit dès maintenant tel que M4 l'utilisera. Pour
initialiser un dossier : **les derniers comptes annuels** (et les données comptables structurées qui les
accompagnent) ; le reste (trimestriels depuis la clôture, exercices antérieurs) sera demandé par M4 au
fil de son travail, quand il saura ce qui lui manque. Le module `comptes`
est ouvert au registre avec ce seul besoin dans son référentiel ; il ne fait rien d'autre tant que M4
n'est pas ouvert.

**Le déclencheur** se construit dans le même lot (arbitré le 2026-11-21) : vous mettez une société à
l'étude depuis sa page ; ensuite, toutes les quelques minutes, une tâche de fond relève les documents
arrivés, les lit et fait avancer le dossier, qui s'arrête sur vos actes ou à la pause de 1 $. La
migration de M2 (064) est appliquée en production après les contrôles (accord du 2026-11-21).

## 3. L'acceptation (charte, point 6) — écrite avant la construction

« Société fictive » : sans base, sans réseau, sans dépense (`check_connaissance.py`, rougi par
`negatif_connaissance.sh`) ; « base » : sur une base jetable ; « réel » : sur le VPS.

| # | Acceptation | Preuve |
|---|---|---|
| K1 | **Rien n'entre sans origine** : une lecture nomme le document de M2 dont elle vient ; une pièce nomme sa lecture et ses lignes ; une pièce sur un document inconnu est refusée, motif nommé. | société fictive |
| K2 | **La lecture est reproductible** : le même document lu deux fois donne le même texte, octet pour octet, et les mêmes numéros de ligne. Un lecteur amélioré produit une lecture nouvelle, à côté ; les pièces déjà citées gardent la leur. | société fictive |
| K3 | **Les formes de document réelles se lisent** : page HTML, rapport réglementaire en HTML (balises de données structurées masquées retirées, tableaux en lignes), texte brut. Données structurées : « sans objet », pas « impossible ». Vide ou illisible : lecture impossible nommée, aucune pièce possible. Fixtures copiées de documents réels (10-K, 8-K et communiqué, page de relations investisseurs). | société fictive |
| K4 | **Une pièce ne dit que ce que son document écrit** : extrait vérifié mot pour mot (#126) ; court et unique → remplacé par sa ligne (#141) ; ambigu ou introuvable → refusé, motif nommé. La pièce porte le texte du DOCUMENT, jamais celui proposé par l'auteur. | société fictive |
| K5 | **Une pièce ne se modifie jamais** : la base refuse modification et suppression ; la même pièce citée deux fois n'est rangée qu'une fois. | base |
| K6 | **Chaque pièce se date sans deviner** : dates de publication et des faits du document ; période du fait cité quand l'auteur la dit (question 1) ; une date absente est dite absente. | société fictive |
| K7 | **Ce que vaut une pièce se lit au jour de la lecture** : une source révoquée après la citation se voit sur la pièce ; on peut lister les pièces qui s'appuient sur une source (acceptation de M1 : « une source révoquée signale les pièces »). Un document d'une source non admise donne des pièces marquées comme telles, jamais présentées comme admises. | société fictive |
| K8 | **Retrouver un passage** : une recherche par les mots rend document, lignes et texte ; deux recherches identiques donnent le même résultat ; aucun appel payant. | société fictive |
| K9 | **Un pas au chef de dossier** : après la collecte, il attend que chaque document arrivé ait sa lecture (ou une lecture impossible nommée) ; dépense 0 ; ce qui ne dépend pas de lui avance. | société fictive |
| K10 | **Le déclencheur** : mettre une société à l'étude crée son dossier ; la tâche de fond relève, lit et fait avancer sans geste de votre part ; l'état du dossier et ce qu'il a lancé sont rangés ensemble ou pas du tout ; deux passages simultanés sur un dossier : le second ne fait rien ; un dossier non mis à l'étude n'avance jamais. | société fictive ; base |
| K11 | **Les besoins** : deux modules consommateurs fictifs déclarent des besoins initiaux qui se recoupent ; le pas de collecte demande chaque genre une fois ; en ajouter un troisième ne modifie aucun fichier de code. Un module qui demande en cours de dossier (un exercice antérieur) obtient une collecte suivie ; ce qui dépend de sa demande l'attend, le reste avance ; la même demande faite deux fois n'est collectée qu'une fois. | société fictive |
| K12 | **L'écran** montre, par émetteur, les documents lus (nombre de lignes, lectures impossibles et pourquoi), les pièces avec leur extrait, leurs lignes et ce que vaut leur source aujourd'hui ; l'état du dossier et le bouton « mettre à l'étude ». | réel |
| K13 | **Contrôle par l'ancien système** : pour NVDA et RVMD, chacune des 57 fiches à extraits vérifiés qui cite un dépôt SEC voit ses extraits retrouvés dans la lecture du même dépôt recollecté par M2 ; chaque écart listé et expliqué (un dépôt non recollecté, une différence de lecture). Gratuit. | réel |
| K14 | **Bout en bout sur trois sociétés** : NVDA, RVMD et SpaceX mises à l'étude ; le besoin des comptes est collecté (SpaceX : le prospectus) et lu ; les lignes « réel » de M2 (B3, B6, B10, B12, B13) passent dans ce même parcours. Rien d'autre ne casse (suite complète). | réel |

## 4. Questions pour l'utilisateur — tranchées le 2026-11-21

1. **La date d'une pièce qui cite un chiffre ancien** (les comptes 2025 contiennent la colonne 2024) :
   **celui qui cite dit la période du fait** ; la pièce garde aussi les dates du document ; sans période
   dite, la pièce l'affiche (« période non précisée, document du … »), jamais devinée. *Logique de fonds* :
   on date le fait et on garde la référence du document (#79).
2. **Jusqu'où remonter** : **jusqu'à ce qui est nécessaire pour construire le modèle de l'entreprise** ; un
   peu de recul historique aide parfois à projeter la croissance. Le système va chercher au fur et à mesure
   ce dont il a besoin ; **pour initialiser un dossier, le dernier rapport annuel** (réponse de
   l'utilisateur, qui remplace les deux options proposées — fenêtre depuis la clôture, ou 18 mois fixes).
   Conséquence : §2, point 1 bis, et K11.
3. **Retrouver un passage** : **par les mots maintenant** (gratuit) ; par le sens quand M6 ou M8 en aura
   besoin, en reprenant l'outil de l'ancien système.

### Tranché ensuite (2026-11-21) : la relecture humaine des sorties de module

Question posée pour le déclencheur (la charte : tout est relu tant que le taux d'erreur d'un poste n'est
pas mesuré). *Logique de fonds* : on fait relire les premiers dossiers d'un analyste, puis par sondage
une fois qu'il est fiable. **Réponse : le dossier s'arrête une fois, après la collecte** — vous validez
les documents trouvés ou introuvables ; la fiche (M1, acceptée) et la mise en lecture (M3, code sans
modèle, contrôlée par K13) ne s'arrêtent pas. Les interrupteurs par module sont une donnée (principe 3 :
on rétablit la relecture d'un module en basculant une valeur).

## 5. Construit hors ligne (2026-11-21)

Module `app/modules/connaissance/` (contrat 1.0.0), détail dans son `ARCHITECTURE.md`. K0-K9 sur
société fictive, communiqué réel NVIDIA copié tel quel : `check_connaissance.py` **49/0**,
`negatif_connaissance.sh` **30/30**. Ce que la construction a appris :
- **`app/knowledge/` charge tout l'ancien paquet** (base, plongements) dès qu'on importe `citation.py` :
  la vérification est passée dans M3 (détenteur unique, exposé par le contrat), l'ancien chemin n'est
  plus qu'un ré-export ; ses deux anciens lecteurs restent verts (collecteur 145/0, note flash 113/0,
  négatifs 51/51 et 54/54, mutations retargetées).
- **Sur le communiqué réel, « 20 » et « % » sont dans deux cellules** ; le lecteur recolle une cellule
  sans lettre ni chiffre comme elle est imprimée (« $ » et « ( » au nombre qui suit, le reste à la
  cellule d'avant).
- **La même ligne de chiffre d'affaires figure deux fois mot pour mot** (tableau comptable, tableau
  retraité) : la pièce retient la première et nomme les autres lignes.
- Le test négatif a trouvé deux faux verts, corrigés : un script placé dans l'en-tête de page (déjà
  muet) n'éprouvait pas la règle « script muet » ; une seconde garde du cœur masquait le refus du
  détenteur (l'assert exige désormais le motif du détenteur).
- **Les demandes au fil du dossier** (§2, 1 bis ; deuxième moitié de K11) se construisent avec M4, le
  premier module qui en aura besoin : aucun code sans appelant.

### Le déclencheur et les besoins, construits hors ligne (2026-11-21, suite)

Module `app/modules/etude/` (contrat 1.0.0, détail dans son `ARCHITECTURE.md`) et module `comptes`
ouvert au registre avec son seul besoin (`referentiel.json` : le dernier annuel et ses données
structurées). K10 et K11 sur société fictive : `check_etude.py` **39/0**, `negatif_etude.sh` **31/31**.
- **Mettre à l'étude** exige une fiche (on n'ouvre pas de dossier sur une société non identifiée) ; une
  seule étude par société.
- **Un passage** : relever (payant, sauf dossier en pause ou terminé — ni par le passage d'un autre
  dossier : l'évaluation des sources de M2 prend désormais le dossier en paramètre), lire (gratuit),
  puis avancer et ranger l'état et ce qu'il lance dans une seule transaction ; un verrou par dossier
  (le second passage ne fait rien).
- **La relecture humaine en donnée**, un interrupteur par pas possible (le chef de dossier l'accepte
  désormais, « module:pas » prime sur le module) : sans lui, le suivi de l'évaluation des sources,
  du même module que la collecte, aurait imposé un second arrêt contre l'arbitrage. Sur la société
  fictive, le seul acte demandé de bout en bout est la validation des documents collectés.
- **Le chef de dossier expose ses gestes par son contrat** (le déclencheur n'a pas le droit d'importer
  son automate) ; chef 108/0, négatif 27/27.
- Appris en lisant le parcours en texte : le libellé de l'acte (« relire la sortie du module
  recueil ») est du jargon ; il se dira en mots de gérant à l'écran (K12).
- Reste : écran, lignes « réel » (le rangement en base et la tâche planifiée : ci-dessous).

### Le rangement en base et la tâche planifiée (2026-11-21, suite)

Migration **065** (`connaissance_lectures`, `_lignes`, `_pieces`, `etude_etudes`, `etude_passages`, toutes
en ajout seul ; une lecture nomme son document de M2 et une pièce sa lecture par clé étrangère — « rien
sans origine » tenu par la base elle-même). Le verrou par dossier est un verrou de session de la base,
relâché si la connexion meurt. `check_connaissance_persist.py` **73/0** sur base jetable (063 → 064 →
065) : le même parcours en mémoire et TOUS les dépôts en base donne les mêmes lectures (études,
connaissance, collecte, état du dossier) ; ensemble ou pas du tout prouvé par vrai ROLLBACK ; deux
passages sur deux connexions. Négatif : code 10/10, migration 9/9. La tâche (`app/main.py`, toutes les
5 minutes) a été exécutée sur la base jetable avec le pool du service : dossier ouvert, collecte lancée,
sans clef de recherche rien de payant et le passage le dit. Appris en route :
- **Un caractère nul dans un document** passait le lecteur mais la base refuse de le ranger : la mise en
  lecture aurait échoué à chaque passage, sans fin. Le lecteur le lit « � » comme un navigateur
  (lecteur 1.1.0 ; K3 et [P2]).
- **Un passage pouvait bloquer sans bruit** (réseau qui ne répond plus) et retenir la tâche entière :
  durée bornée par dossier (référentiel, 10 min), passage arrêté et noté « interrompu », les autres
  dossiers passent (contrat `etude` 1.1.0).
- **La langue de la base trie autrement que le code** (« AB » avant « A-C ») : les études se lisent
  octet par octet.
- **Le test négatif a trouvé un trou** : des lignes rangées à l'envers ne se voyaient pas (la ligne citée
  était au milieu d'un texte de trois lignes) ; les lignes de chaque lecture sont désormais comparées.
- La mise en lecture tourne hors de la boucle principale (un rapport annuel de plusieurs Mo ne fige plus
  les écrans).

## 6. Ce que M3 ne fait pas (dit, pas caché)

- **Choisir quoi citer** : c'est l'analyste qui choisit ses extraits (un module, un modèle) ; M3 vérifie
  et range. Une pièce exacte sortie de son contexte (une négation dans la phrase voisine) passe : elle se
  voit à la relecture (coût d'erreur déjà nommé par #126).
- **Juger** si une pièce est périmée, ce qu'elle prouve, ou laquelle de deux pièces fait foi : modules
  M8-M9.
- **Lire les PDF** : M2 ne les range pas aujourd'hui (indisponibilité nommée). Ils deviendront un format de
  plus le jour où M2 les rangera.
- **Lire les données comptables structurées** : M4.
