# Étude — `app/modules/etude/` (le déclencheur du chef de dossier)

Contrat **1.1.0**. Construit avec M3 (`roadmap/V3/M3-base-connaissance.md` §2, « Le déclencheur » ;
acceptation K10, K11). **État (2026-11-21) : construit et prouvé hors ligne sur société fictive
; rangement en base (migration 065) prouvé sur base jetable, tâche planifiée câblée (`app/main.py`,
toutes les `intervalle_min` minutes) et exécutée sur base jetable — 064/065 PAS ENCORE APPLIQUÉES en
production. À construire : l'écran (bouton « mettre à l'étude », gestes), les lignes « réel ».**

*Ce que ferait un vrai fonds* : c'est le gérant qui dit quoi analyser ; une fois un titre mis à
l'étude, l'analyste fait avancer son dossier sans qu'on le relance — il relève le courrier, lit ce qui
est arrivé, avance ce qui peut l'être — et ne revient vers le gérant que pour une décision. Il ne
dépense rien sur un dossier que le gérant a mis en pause.

## Ce qu'il rend

Les **sociétés mises à l'étude** (`contrat.EtudeLue`), lues par une seule fonction :
`contrat.lire_etudes(monde)` — l'étude (par qui, quand, pourquoi), le dernier passage qui a fait
quelque chose, l'état du dossier en clair.

## Un passage (`contrat.passer`, `contrat.traiter_les_dossiers`)

1. Non mis à l'étude → rien (`non_etudie`). Un autre passage tient le dossier → rien (`deja_en_cours`).
2. **Relever** (payant) — sauf dossier en pause de dépense ou terminé : les collectes lancées pour CE
   dossier (M2), le jugement des sources inconnues rencontrées pour CE dossier (M2 → M1).
3. **Lire** (gratuit, même en pause) : les documents arrivés sont mis en lecture (M3).
4. **Avancer et ranger dans UNE transaction** : l'état du dossier (chef de dossier) et ce que ses pas
   ont décidé (demandes à lancer, dépense déclarée) ensemble ou pas du tout.

Une panne en 2 ou 3 se dit dans le passage (`Passage.detail`) et n'empêche pas la 4. Seuls les
passages qui ont fait quelque chose sont notés. **Un passage qui dépasse sa durée** (référentiel,
`passage.delai_par_dossier_s`) est arrêté et noté `interrompu` (contrat 1.1.0) : ce qui était en
transaction est annulé, le verrou rendu, les autres dossiers passent, le suivant reprend — un blocage
ne reste jamais muet.

**La tâche planifiée** (`app/main.py`, `_passage_des_etudes`) construit le monde par
`contrat.monde_en_base` (tous les dépôts sur une connexion, les outils et l'évaluateur avec les clefs du
service ; sans clef de recherche, rien de payant et le passage le dit). Une seule instance à la fois.

**Le parcours** (`coeur.parcours`) : fiche → collecte des besoins → suivi de l'évaluation des sources
(après la collecte) → mise en lecture (après la collecte). Chaque module accepté y ajoutera son pas.

**Les besoins** (M3 §2) : chaque module consommateur les déclare dans son référentiel et les rend par
son contrat ; `coeur.rassembler` en fait les demandes (le même genre une fois ; genre inconnu, champ
inconnu, date « depuis » qui ne va pas : refusés avec le module qui l'a déclaré). Aujourd'hui un seul
consommateur : `comptes` (le dernier annuel et ses données structurées). Un consommateur de plus = une
ligne dans `coeur.besoins_des_consommateurs` et son entrée au registre ; ni la collecte, ni la
lecture, ni le chef de dossier, ni le rassemblement ne changent.

**La relecture humaine** (arbitrage du 2026-11-21) : en donnée dans `referentiel.json`
(`lecture_humaine`) ; un interrupteur propre à un pas (« module:pas ») prime sur celui du module. Le
dossier s'arrête une fois, après la collecte ; rétablir une relecture = basculer une valeur.

## Comment c'est construit

```
contrat.py        objets, dépôt (interface + mémoire), Monde (ce qui est injecté), lecture, gestes
coeur.py          besoins, parcours, passage, gestes, lecture
referentiel.json  relecture humaine, noms des pas, durée d'un passage et intervalle de la tâche
depot_base.py     le rangement en base (`etude_etudes`, `etude_passages`, migration 065, ajout seul) et le
                  verrou par dossier : `pg_try_advisory_lock` de SESSION (tient entre connexions, relâché
                  par la base si la connexion meurt ; la même connexion ne le reprend pas)
```

Le `Monde` injecte les dépôts des modules, le rangement de l'état des dossiers, les outils de
collecte, l'évaluateur et la transaction : en mémoire pour les contrôles, une même connexion pour la
tâche planifiée.

## Invariant → assert garant

Contrôle : `checks/check_etude.py` (43) ; test négatif : `checks/negatif_etude.sh` (33 mutations).
En base : `checks/check_connaissance_persist.py` (mêmes gestes en mémoire et en base ; ensemble ou pas
du tout par vrai ROLLBACK ; verrou entre deux connexions ; ordre des études octet par octet) ; test
négatif : `checks/negatif_connaissance_persist.sh`.

| Invariant | Assert |
|---|---|
| Ni réseau, ni base, ni modèle dans le module | [T0] |
| Besoins : chaque genre une fois ; un troisième module ne change que la donnée ; mal formé → refusé avec son module ; besoin réel des comptes | [K11] |
| Mise à l'étude : refusée sans fiche, une seule étude par société | [K10] |
| Non mis à l'étude : n'avance jamais | [K10] |
| Bout en bout sans geste sauf la relecture de la collecte ; dépense déclarée | [K10] [L1] |
| État et demandes lancées : ensemble ou pas du tout ; le refus se dit | [K10] |
| Deux passages simultanés : le second ne fait rien | [K10] |
| Un passage trop long : arrêté, noté, verrou rendu ; les autres dossiers passent | [K10] |
| Rien de payant sur un dossier en pause, ni par le passage d'un autre dossier | [K10] |
| Gestes : refus nommés | [T1] |
| Journal : seuls les passages utiles ; une panne se dit et n'arrête pas | [T2] |

## Ce qui n'existe pas encore (dit, pas caché)

- **L'écran** : ni bouton « mettre à l'étude », ni gestes (acte, pause, relance) à l'écran.
- **Le libellé de l'acte** de relecture est celui, générique, du chef de dossier (« relire la sortie
  du module « recueil » ») : à dire en mots de gérant à l'écran (« valider les documents trouvés ou
  introuvables »).
- **Un dossier terminé** ne repart pas quand le parcours s'allonge (un module accepté de plus) : à
  traiter avec le premier module qui ajoutera un pas (M4).
- **L'évaluation des sources** se paie dès que la collecte a rencontré une source, avant que son pas
  soit lancé ; sa dépense est déclarée au dossier quand le pas la suit (bornée : une évaluation par
  source).
