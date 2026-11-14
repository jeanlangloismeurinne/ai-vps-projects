# Chef de dossier — `app/modules/chef_de_dossier/`

Module M0 du plan `roadmap/V3/07-avant-comite.md`. **État : squelette accepté le 2026-11-13** sur une
société fictive et des modules simulés. Aucun module réel ne lui a encore déclaré de pas.

*Ce que ferait un vrai fonds* : un analyste tient son dossier ; il ne s'arrête que lorsqu'il lui faut
une décision d'un supérieur, et il dit laquelle.

## Ce qu'il rend

L'**état d'un dossier** (`contrat.EtatDossier`, version `1.0.0`), lu par une seule fonction :
`contrat.lire_etat(depot, dossier)`. Il dit : les pas faits, les réserves (« source indisponible »
nommée), les actes accomplis, la dépense (modèles et web à part, par pas), le journal, et l'**arrêt**
en cours avec le coût restant estimé jusqu'à la fin du parcours.

## Comment un module s'y inscrit (charte, point 8)

Il déclare un `contrat.Pas` : son nom, ses préalables, ce qu'il exécute, ce qu'il pense dépenser. Son
exécution rend un `contrat.Resultat` : `fait`, `indisponible` (motivé), `acte_humain` (acte nommé) ou
`echec` (motivé), avec sa `Depense`. Un acte qui vous revient (valider la carte, décider en comité) est
un pas de nature `humain` : l'automate s'y arrête, il ne l'exécute jamais.

## Pas en cours et parallélisme (contrat 1.1.0, arbitrage du 2026-11-14)

Un pas peut **lancer** un travail qui dure (une collecte) et rendre `en_cours` ; il déclare alors
`suivre`, que l'automate rappelle **une fois par passage** jusqu'à une autre issue. Pendant ce temps,
tout ce qui ne dépend pas de ce pas avance ; ce qui en dépend attend, **sans limite de temps** (un
travail qui échoue en route est relancé une fois, puis arrête le dossier). Plus généralement, un acte
attendu, une lecture ou un échec répété ne retient que les pas qui en dépendent. L'arrêt énumère toutes
les attentes (`Arret.attentes`) ; son motif principal est la première chose qui vous revient.

*Ce que ferait un vrai fonds* : l'analyste qui attend des documents avance sur ce qui ne les exige pas ;
il n'écrit pas la partie qui en a besoin avant de les avoir.

## Les cinq arrêts

| Arrêt | Quand | Se lève par |
|---|---|---|
| Acte de votre part | pas humain ; sortie de module à relire ; acte demandé par un pas | `enregistrer_acte` (l'acte attendu, lui seul) |
| Pause de dépense | 1 $ consommé depuis la dernière pause levée | `lever_pause` |
| Échec répété | un pas échoue deux fois de suite | `relancer` |
| Parcours terminé | plus aucun pas | — |
| Attente | plus rien ne peut avancer, un travail est en cours | rien : le passage suivant le reprend |

La **lecture humaine** de chaque sortie de module est la règle par défaut ; elle se lève module par
module (table `lecture_humaine`), quand le taux d'erreur du module est mesuré (principe 3).

## Invariant → assert garant

Contrôle : `check_chef_de_dossier.py` ; test négatif : `negatif_chef_de_dossier.sh`
(25 mutations, toutes détectées sur leur assert — exécuté sur l'hôte le 2026-11-14, le module étant pur
bibliothèque standard).

| Invariant | Assert |
|---|---|
| Un parcours qui ne peut pas aboutir est refusé avant toute exécution | [D1] |
| Le dossier avance seul et s'arrête exactement aux actes déclarés | [D2] |
| Pause à chaque palier, avec dépense totale, coût restant estimé, écart dépensé / estimé | [D3] |
| Deux échecs de suite arrêtent ; un plantage est un échec motivé | [D4] |
| « Source indisponible » : le dossier continue, la réserve reste | [D5] |
| Lecture humaine par défaut, levée module par module | [D6] |
| L'état se range et se relit ; interrompu puis repris = un seul passage | [D7] |
| Modèles et web comptés à part ; un essai échoué est compté | [D8] |
| Un arrêt ne se lève que par son geste | [D9] |
| Aucun modèle, aucun réseau : bibliothèque standard et son contrat | [D10] |
| Travail en cours : on avance à côté, on attend ce qui en dépend, sans limite ; relancé une fois | [D11] |
| Plusieurs attentes énumérées ; chaque geste vise l'une d'elles ; une pause reste une pause | [D12] |

## Ce qui n'existe pas encore (dit, pas caché)

- **Le rangement en base est écrit, pas encore en production** : `contrat.depot_base(connexion)` →
  `ouvrir` charge l'état dans un `DepotMemoire`, l'automate avance, `refermer` range ; deux passages
  partis de la même lecture : le second est refusé (`EcritureConcurrente`). Table `chef_etats`,
  migration 063 (non appliquée). Prouvé sur une base locale : `check_emetteurs_persist.py` [B5]-[B6],
  rougi par `negatif_emetteurs_persist.sh`.
- **L'automate reste synchrone et sans entrée-sortie** : un travail long ne se fait pas DANS un pas, il
  est lancé par lui et suivi (`en_cours` / `suivre`). Où vit ce travail (une tâche de fond de la collecte)
  et ce qui rappelle l'automate entre deux passages : à construire avec M2 et le déclencheur.
- **L'écran** : la page d'un émetteur montre l'état de son dossier en lecture seule ; aucun geste
  (lever une pause, enregistrer un acte) n'est encore offert à l'écran.
- **Le déclencheur** : rien n'appelle encore `automate.conduire` (ni tâche planifiée, ni route).
- **L'estimation** du coût restant est la somme de ce que les modules déclarent : elle ne vaut que ce
  que valent leurs estimations. L'arrêt donne l'écart constaté, il ne corrige pas le chiffre.
- Un pas ne s'interrompt pas en cours d'exécution : la pause tombe après le pas qui franchit le palier.
