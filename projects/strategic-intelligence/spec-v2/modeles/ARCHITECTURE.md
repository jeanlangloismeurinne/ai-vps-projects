# ARCHITECTURE — strategic-intelligence (cible)

> **Ce document décrit l'architecture CIBLE** (dérivée de `spec-v2/02-ARCHITECTURE.md`). Il est le
> point d'entrée pour toute session de développement.
>
> **L'architecture RÉALISÉE n'est pas décrite en prose** : elle est prouvée par la suite
> `checks/` (`bash checks/run_all.sh`, ligne de base : *à renseigner au premier run vert*).
> Chaque module a son `ARCHITECTURE.md` qui mappe *invariant cible → check garant*. Un invariant
> sans check est une **dette**, marquée ⚠️.
>
> **Cette organisation est elle-même gardée** par `check_architecture.py` (+ `negatif_architecture.sh`) :
> bijection registre ↔ modules ↔ manifestes ↔ docs, pointeurs de checks vivants, aucune garde
> orpheline. Ajouter un module = sa ligne ci-dessous **et** son dossier, son `module.yml`, son
> `ARCHITECTURE.md` — le check refuse l'un sans les autres.

## Reprendre le contexte

1. Ce fichier. 2. `00-REPRISE.md`. 3. L'`ARCHITECTURE.md` du module concerné. 4. Lecture
**ciblée** du code touché (recherche, puis extrait). Jamais un dossier entier.

## Invariants

| # | Invariant | Garant |
|---|---|---|
| I1 | Aucune valeur sectorielle dans le code | `check_agnosticite.py` |
| I2 | Toute sortie par `noyau.sorties`, toute collecte HTTP par `noyau.http` | `check_sorties.py` |
| I3 | Rien de `red` ne sort ; `amber` seulement segmenté | `check_sensibilite.py` |
| I4 | Toute affirmation générée a une evidence | ⚠️ `check_evidence.py` (lot 1) |
| I5 | Brut immuable, rejeu possible | ⚠️ `check_brut_immuable.py` (lot 0.5) |
| I6 | Prérequis déclarés, pas de dégradation silencieuse | `check_manifestes.py` |
| I7 | noyau ← socle ← métier ← web ; pas d'import entre modules métier | `check_dependances.py` |
| I8 | Registre ↔ modules ↔ manifestes ↔ docs | `check_architecture.py` |
| I9 | Chaque table appartient à un module | ⚠️ `check_schema.py` (lot 0.5) |
| I10 | Gratuit avant payant dans la chaîne | `check_manifestes.py` |

## Registre des modules

`check_architecture.py` lit ce tableau : c'est le **détenteur unique** de la liste des modules.

| Module | Niveau | Rôle | Doc |
|---|---|---|---|
| `noyau` | noyau | registre, bus, sorties, budget, maturité, référentiel, configuration, ordonnanceur, http | `app/noyau/ARCHITECTURE.md` |
| `collecte` | socle | familles, gabarits, instances, exécution, santé des sources | `app/modules/collecte/ARCHITECTURE.md` |
| `signaux` | socle | chaîne de traitement, scoring, corroboration | `app/modules/signaux/ARCHITECTURE.md` |
| `diffusion` | socle | brief, alertes, revue du vendredi | `app/modules/diffusion/ARCHITECTURE.md` |

Les modules métier (`questions_cles`, `terrain`, `livrables`, `connaissance`, `observations`,
`concurrence`, `commande_publique`, `reglementaire`, `technologie`, `capital`, `calendrier`,
`scenarios`, `theses`, `calibration`, `radar`) sont ajoutés à ce registre **au lot où ils sont
créés**, pas avant (un module déclaré sans dossier fait rougir le check).

## Points d'extension

Voir `spec-v2/02-ARCHITECTURE.md` §6 (E1 à E13). Toute évolution qui n'y entre pas impose de
réviser ce fichier d'abord.

## Checks

| Check | Base | Négatif |
|---|---|---|
| `check_architecture.py` | non | `negatif_architecture.sh` |
| `check_manifestes.py` | non | `negatif_manifestes.sh` |
| `check_dependances.py` | non | `negatif_dependances.sh` |
| `check_sorties.py` | non | `negatif_sorties.sh` |
| `check_agnosticite.py` | non | `negatif_agnosticite.sh` |
| `check_sensibilite.py` | oui | `negatif_sensibilite.sh` |
