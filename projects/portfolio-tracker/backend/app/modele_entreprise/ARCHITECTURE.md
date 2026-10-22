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

## Ce qui existe (M3 bis — roadmap V3 `13-lot-M3bis-structure.md`, principe fondateur n° 4)

Traite les CAUSES des erreurs des 4 architectures à blanc du 2026-10-22, pas leurs symptômes.

- `faits_publies.py` (NOUVEAU, pur) — cause ① : ce que le CODE établit, jamais déclaré par le
  modèle. `poser_maille(blocs_proposes) -> list[Bloc]` (pose `maille`, posée à l'en-tête,
  `architecte._poser_entete`) ; `parent_publie_de`/`est_premier_niveau_publie` (l'emboîtement entre
  blocs PUBLIÉS est DÉRIVÉ de la hiérarchie relevée de la ventilation, jamais déclaré — un bloc
  publié n'a plus la forme contractuelle pour porter un `RattachementParent`) ;
  `motif_regroupement_incoherent` ([S1], un regroupement publié = membres du même axe ET des mêmes
  parents) ; `axes_sans_bloc_publie` ([S10]).
- `dimensions.py` (NOUVEAU, pur) — cause ④ : `dimension_de(formule, unites)` et
  `verifier_periode_ligne(...)` réutilisent l'ARBRE de `formule_grammaire.analyser_formule` (jamais
  une seconde grammaire) mais calculent une dimension PHYSIQUE (montant/quantité/temps) et une
  échelle propres au catalogue maison, lues dans `ReferentielModele.unites`. Un littéral MULTIPLIE
  le nombre calculé donc DIVISE l'échelle requise (et inversement en division) — c'est ce qui
  distingue `volume * prix_moyen` (échelle 1, refusé contre M$) de `volume * prix_moyen / 1000000`
  (échelle 10⁶, accepté) : voir le docstring de `_Resultat` pour la dérivation complète.
- `app/contracts/modele_entreprise_schema.py` → `architecture-1.2.0` : `RattachementPublie.membres`
  (liste, regroupement, cause ①) remplace `membre` ; `BlocPropose` (ce que le modèle produit, SANS
  `maille`) / `Bloc` (`BlocPropose` + `maille`, posée par le code) ; `Bloc.origine`
  (interne/acquisition/licence/partenariat) et `Bloc.jalon` (requis SSI `statut ==
  "en_developpement"`), avec [S12] en validateur DE L'OBJET (`BlocPropose`, jamais dans
  `structure.py` : un invariant d'un seul objet, #37) — cause ⑤ ; `Architecture.autres_axes`
  (cause ①, [S10]) et `.manques_du_dossier` (cause ③) ; `ReferentielModele.unites` + [R7] (cause ④,
  vérifié pour le catalogue dans le contrat, pour les variables propres au pont,
  `referentiel.valider_pont_architecture`).
- `app/frameworks/modele_entreprise.yaml` → `version: "1.2.0"` : table `unites:` (8 entrées) ; fiche
  `depense_de_developpement_du_bloc` (distincte de `cout_restant_de_developpement`, qui est
  désormais explicitement SANS période) ; les deux dans `patrons.pre_revenus`.
- `app/frameworks/frameworks.yaml` → question `me_7` (« que prépare l'entreprise… ») dans
  `modele_economique` — aucune montée de `schema_version` (#92, ajout d'une question). `me_7`
  devient question source de `probabilite_de_succes`, `annee_de_lancement`, `ventes_au_pic`,
  `cout_restant_de_developpement`, `depense_de_developpement_du_bloc` : la porte de l'architecte
  d'une famille industrielle se FERME tant que `me_7` n'a pas sa première réponse instruite, comme
  toute question source — effet voulu, dit dans `roadmap/V3/03-spec-frameworks.md` §4.3.
- `structure.py` — [S1] étendu (regroupement) ; [S3] SIMPLIFIÉ (ne porte plus que sur l'axe : le
  double compte entre un bloc publié et son sous-membre publié ne peut plus se déclarer, l'emboîtement
  étant dérivé — c'est [S7] qui nomme un double compte resté dans une formule, « en trop ») ;
  [S7]/[S9] lisent `faits_publies.est_premier_niveau_publie` au lieu d'un `RattachementParent`
  déclaré ; **[S10]** (NOUVEAU, cause ①) et **[S11]** (NOUVEAU, cause ④).
- `app/knowledge/ventilation.py` — cause ② : `rendre_ventilation(..., avec_identifiants=True)` gagne
  la phrase fixe (deux axes se croisent, jamais ne s'emboîtent) + la Σ par axe/période vs. le
  chiffre d'affaires des comptes + les découpages successifs. `avec_identifiants=False` (défaut,
  `montrer_ventilation.sh`) inchangé.
- `architecte.py` — prompt et exemple réécrits en conséquence (membres liste, origine/jalon,
  `autres_axes`, `manques_du_dossier`, `maille` retirée de ce que le modèle produit).
- **Écart assumé à la spec** : [S12] est posé dans le CONTRAT (`BlocPropose`), pas dans
  `structure.py` — c'est un invariant d'un seul objet (#37 : un contrat valide un objet, jamais la
  cohérence entre deux), et la numérotation [S1]-[S11] de `structure.py` ne saute donc pas de S11 à
  S13.

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

- `checks/check_modele_entreprise.py` (sans base) — référentiel (1.2.0, [R6], [R7], table `unites`),
  contrat (dont `Bloc.origine`/`jalon`, [S12]), pont [R1]-[R7]/[P1]-[P5]/[C1]-[C5], contrôles,
  `appliquer_scenario`, réplicabilité ; `Bloc.motif`/`pieces`. + `checks/negatif_modele_entreprise.sh`
  (71 mutations, 0 échec — mesuré 2026-10-22).
- `checks/check_modele_entreprise_persist.py` (avec base, migration 061 — `checks/avec_base.sh`) —
  écriture des quatre registres. + `checks/negatif_061.sh` (la migration elle-même, sur une copie).
- `checks/check_architecte.py` (sans base) — la porte (table §3.1 + interrupteur), les périodes, la
  matière, l'exemple du prompt (#121), l'en-tête, [S1]-[S11], le renvoi, le service, réplicabilité,
  les 4 architectures du 2026-10-22 rejouées sous 1.2.0 (`checks/fixtures/architecte/2026-10-22/`).
  + `checks/negatif_architecte.sh` (26 mutations, 0 échec — mesuré 2026-10-22).
- `checks/check_architecture_persist.py` (avec base, `checks/avec_base.sh`) — proposer/append-only
  sur `architectures_modele` (061, en place) ; signer/écarter/append-only sur
  `architectures_modele_decisions` (062) **non exécutés tant que 062 n'est pas appliquée** (nommé,
  jamais sauté). + `checks/negatif_062.sh` (la migration 062, sur une copie).

## Pourquoi un paquet à part de `app/valorisation/`

Le classeur de l'entreprise est le référentiel COMMUN que la valorisation (M7) lira ; il ne lui est
pas subordonné. Le référentiel (`modele_entreprise.yaml`) a sa propre version, indépendante de
`schema_version` de `frameworks.yaml` (corriger une fiche de variable ne doit invalider aucune
réponse — même logique que `types_evenement_version`).
