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

## Ce qui existe (M3 — roadmap V3 `12-lot-M3-architecte.md`)

- `porte.py` — `porte_de_l_architecte(etat, ref) -> Porte` : pure, lit le diagnostic existant
  (`parcours.manque_pour_question`, détenteur unique des arguments de `manque_de_la_question`,
  jamais recopié) question par question. L'interrupteur `porte_admet_reponses_refusees` (référentiel
  1.1.0) décide si une réponse `renvoyee` OUVRE (phase de test, marquée) ou FERME (cible).
- `periodes.py` — `periode_du_classeur`/`periodes_du_classeur` : détenteur unique des ids `FY####`
  du classeur, distincts des ids du socle (`FY2026-01-25`). Collision de deux exercices → refus nommé.
- `matiere.py` — `charger_matiere(conn, ticker_id, *, publier)` (la SEULE moitié qui lit) /
  `rendre_matiere(m)` (PURE) : tout ce que l'architecte voit, assemblé dans l'ordre de la spec §3.3.
  `publier=False` (à blanc) ne publie rien ; le socle/la ventilation sont relevés en mémoire si
  absents, sans id de pièce.
- `app/knowledge/ventilation.rendre_ventilation(…, avec_identifiants=True)` — adresses
  `[axe=… membre=…]`, nouveau paramètre, défaut `False` (rendu M2 inchangé).
- `structure.py` — `valider_structure(arch, ref, matiere) -> list[str]` (signaux) ; [S1]-[S9], lève
  `ArchitectureRefusee` (ce module) avec TOUS les motifs réunis. Vérifie la structure et la
  ventilation publiée, jamais le sens (#68) ; le raccord CHIFFRÉ est M5.
- `architecte.py` — l'agent (patron : `agents/v2/traducteur.py`) : `ArchitecteSortie` (sortie du
  modèle, sans en-tête), `_ARCHITECTE_SYSTEM_PROMPT`/`_EXEMPLE_ARCHITECTURE` (société fictive, point
  de contrat #121), `proposer_architecture_du_titre` (porte → matière → appel → en-tête posé par le
  code → pont+structure → renvoi UNE fois → écriture si `ecrire=True`).
- `signature.py` — `servir_architecture` (pure, `juger` injecté) / `signer` / `ecarter` /
  `lire_registre` : le PV de l'architecture (migration 062), même geste que
  `valorisation/signature.py`. L'interrupteur `signature_de_l_architecture` décide ce qui est EN
  VIGUEUR (la signée si elle tient, sinon aucune ; ou la dernière proposée qui tient, signée ou non).
- `app/contracts/architecture_signature_schema.py` — calqué sur `signature_modele_schema.py`.
- Migration `062_v3_signature_architecture.sql` (ÉCRITE, NON APPLIQUÉE) — `architectures_modele_decisions`,
  append-only, éprouvée par `checks/negatif_062.sh` sur une copie de `db_portfolio`.
- `app/api/modele_entreprise_v2.py` — `GET/POST .../architecture[/v/{n}/signer|ecarter]`, calqué sur
  `valorisation_v2.py`.
- `tools/architecte.sh` (+ `.py`) et `tools/montrer_architecture.sh` (+ `.py`).

**Écart assumé à la spec (§5, [S2])** : la couverture ne rejoue l'emboîtement QUE pour l'axe du
premier niveau — « même règle sous chaque bloc publié qui a des enfants-blocs » n'est pas rejouée
récursivement (le raccord chiffré de l'emboîtement est de toute façon M5). `servir_architecture`
prend `ticker_id` en paramètre explicite (la spec ne le liste pas dans la signature ; sans lui, un
titre sans AUCUNE architecture proposée ne pourrait pas être nommé dans la réponse servie).

## Ce qui n'existe PAS encore (lots suivants)

- **M2 bis** : le gabarit bancaire du socle — tant qu'il n'existe pas, `familles_de_comptes.bancaire`
  n'a pas de format agrégé (`gabarit: null`), et l'architecte ne passe pas pour une financière (§11.2
  de la spec métier) : `valider_pont_architecture` refuse en [P1] avec le motif du référentiel.
- Le point **[P6]** (« un bloc `en_developpement`/`extension_annoncee` ne porte jamais
  `part_de_marche` calculée sur une période passée ») reste délibérément **pas codé** : aucune
  cellule n'existe encore pour l'exercer. À coder en M5.
- **M4** : les demandes ciblées par cellule, la projection des encadrés existants en cellules, les
  relances.
- **M5** : l'agrégé au format du socle (historique + projection), les contrôles de raccord, et [P6].
- **M6** : le calcul réel des fourchettes par les méthodes du catalogue, l'inventaire des variables
  de scénario écrit par les chapitres de jugement, la matérialité, le constructeur de scénarios et
  son repli — c'est lui qui appellera `scenarios.appliquer_scenario`.
- **M7** : l'agent de valorisation sur le classeur.

## Gardé par

- `checks/check_modele_entreprise.py` (sans base) — référentiel (1.1.0, [R6]), contrat,
  pont [R1]-[R6]/[P1]-[P5]/[C1]-[C5], contrôles, `appliquer_scenario`, réplicabilité ; `Bloc.motif`/
  `pieces`. + `checks/negatif_modele_entreprise.sh`.
- `checks/check_modele_entreprise_persist.py` (avec base, migration 061 — `checks/avec_base.sh`) —
  écriture des quatre registres. + `checks/negatif_061.sh` (la migration elle-même, sur une copie).
- `checks/check_architecte.py` (sans base) — la porte (table §3.1 + interrupteur), les périodes, la
  matière, l'exemple du prompt (#121), l'en-tête, [S1]-[S9], le renvoi, le service, réplicabilité.
  + `checks/negatif_architecte.sh`.
- `checks/check_architecture_persist.py` (avec base, `checks/avec_base.sh`) — proposer/append-only
  sur `architectures_modele` (061, en place) ; signer/écarter/append-only sur
  `architectures_modele_decisions` (062) **non exécutés tant que 062 n'est pas appliquée** (nommé,
  jamais sauté). + `checks/negatif_062.sh` (la migration 062, sur une copie).

## Pourquoi un paquet à part de `app/valorisation/`

Le classeur de l'entreprise est le référentiel COMMUN que la valorisation (M7) lira ; il ne lui est
pas subordonné. Le référentiel (`modele_entreprise.yaml`) a sa propre version, indépendante de
`schema_version` de `frameworks.yaml` (corriger une fiche de variable ne doit invalider aucune
réponse — même logique que `types_evenement_version`).
