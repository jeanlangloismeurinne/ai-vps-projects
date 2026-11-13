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

## Les quatre arrêts

| Arrêt | Quand | Se lève par |
|---|---|---|
| Acte de votre part | pas humain ; sortie de module à relire ; acte demandé par un pas | `enregistrer_acte` (l'acte attendu, lui seul) |
| Pause de dépense | 1 $ consommé depuis la dernière pause levée | `lever_pause` |
| Échec répété | un pas échoue deux fois de suite | `relancer` |
| Parcours terminé | plus aucun pas | — |

La **lecture humaine** de chaque sortie de module est la règle par défaut ; elle se lève module par
module (table `lecture_humaine`), quand le taux d'erreur du module est mesuré (principe 3).

## Invariant → assert garant

Contrôle : `check_chef_de_dossier.py` (68 vérifications) ; test négatif : `negatif_chef_de_dossier.sh`
(14 mutations, toutes détectées sur leur assert — exécuté sur l'hôte le 2026-11-13, le module étant pur
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

## Ce qui n'existe pas encore (dit, pas caché)

- **Le rangement en base** : `contrat.Depot` est une interface, seul `DepotMemoire` existe. La table
  (préfixe `chef_`) et sa migration arrivent avec le premier module réel (M1), sans changer le contrat.
- **L'écran** : `automate.afficher` rend l'état en texte. L'écran web arrive avec le rangement en base.
- **Le déclencheur** : rien n'appelle encore `automate.conduire` (ni tâche planifiée, ni route).
- **L'estimation** du coût restant est la somme de ce que les modules déclarent : elle ne vaut que ce
  que valent leurs estimations. L'arrêt donne l'écart constaté, il ne corrige pas le chiffre.
- Un pas ne s'interrompt pas en cours d'exécution : la pause tombe après le pas qui franchit le palier.
