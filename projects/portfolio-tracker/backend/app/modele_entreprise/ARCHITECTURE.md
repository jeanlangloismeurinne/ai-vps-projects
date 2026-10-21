# `app/modele_entreprise/` — le classeur de l'entreprise

Spec métier : `roadmap/V3/09-modele-entreprise.md`. Spec d'exécution de ce lot :
`roadmap/V3/10-lot-M1-catalogue-et-contrats.md`.

## Ce qui existe (M1)

- `referentiel.py` — charge et valide `app/frameworks/modele_entreprise.yaml`
  (`load_referentiel`), et tient le PONT : `_valider_pont_referentiel` ([R1]-[R5], contre
  `frameworks.yaml` et le socle des comptes), `valider_pont_architecture` ([P1]-[P5], une
  architecture contre le référentiel), `valider_cellule` ([C1]-[C5], une cellule contre
  l'architecture). `variables_de_la_famille` et `questions_sources_applicables` sont les deux
  fonctions de lecture que l'architecte (M3) consommera.
- `controles.py` — les six contrôles déterministes nommés par le référentiel (`positif`,
  `positif_ou_nul`, `proportion`, `probabilite`, `annee`, `part_calculee`), chacun
  `(Cellule, ContexteControle) -> Optional[str]`.
- `scenarios.py` — `appliquer_scenario(centrales, scenario, fourchettes)`, fonction PURE qui
  projette un scénario (central ou un déplacement) sur des valeurs centrales. **Rien ne l'appelle
  encore hors des checks** : M7 la branchera sur `evaluer_modele`. Ne pas la croire branchée.
- `registre.py` — écriture des quatre registres de la migration 061 (`proposer_architecture`,
  `inscrire_fourchette`, `inscrire_scenario`), même geste que `valorisation/signature.py` : append-
  only, transaction explicite (#35), refuse `SCENARIO_CENTRAL` (jamais une ligne).

## Ce qui n'existe PAS encore (lots suivants)

- **M2** : la ventilation publiée (B2) au socle des comptes.
- **M2 bis** : le gabarit bancaire du socle — tant qu'il n'existe pas, `familles_de_comptes.bancaire`
  n'a pas de format agrégé (`gabarit: null`), et l'architecte ne passe pas pour une financière (§11.2
  de la spec métier) : `valider_pont_architecture` refuse en [P1] avec le motif du référentiel.
- **M3** : l'agent architecte lui-même (contexte = matière du dossier), les contrôles de structure
  complets, et la signature de l'architecture au PV (migration 062, interrupteur débrayable).
  Le point **[P6]** (« un bloc `en_developpement`/`extension_annoncee` ne porte jamais
  `part_de_marche` calculée sur une période passée ») est NOMMÉ dans la spec M1 (§3) mais
  délibérément **pas codé** ici : aucune cellule n'existe encore en M1 pour l'exercer. À coder en M5.
- **M4** : les demandes ciblées par cellule, la projection des encadrés existants en cellules, les
  relances.
- **M5** : l'agrégé au format du socle (historique + projection), les contrôles de raccord, et [P6].
- **M6** : le calcul réel des fourchettes par les méthodes du catalogue, l'inventaire des variables
  de scénario écrit par les chapitres de jugement, la matérialité, le constructeur de scénarios et
  son repli — c'est lui qui appellera `scenarios.appliquer_scenario`.
- **M7** : l'agent de valorisation sur le classeur.

## Gardé par

- `checks/check_modele_entreprise.py` (sans base) — référentiel, contrat, pont [R1]-[R5]/[P1]-[P5]/
  [C1]-[C5], contrôles, `appliquer_scenario`, réplicabilité. + `checks/negatif_modele_entreprise.sh`.
- `checks/check_modele_entreprise_persist.py` (avec base, migration 061 — `checks/avec_base.sh`) —
  écriture des quatre registres. + `checks/negatif_061.sh` (la migration elle-même, sur une copie).

## Pourquoi un paquet à part de `app/valorisation/`

Le classeur de l'entreprise est le référentiel COMMUN que la valorisation (M7) lira ; il ne lui est
pas subordonné. Le référentiel (`modele_entreprise.yaml`) a sa propre version, indépendante de
`schema_version` de `frameworks.yaml` (corriger une fiche de variable ne doit invalider aucune
réponse — même logique que `types_evenement_version`).
