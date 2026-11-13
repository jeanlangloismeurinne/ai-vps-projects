---
id: spec-lot-m1
status: spec-2026-10-21 (Opus) — à exécuter par Sonnet
created: 2026-10-21
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M1 (B3 du plan `07-avant-comite.md`) : le référentiel du classeur de l'entreprise
  (catalogue de variables, familles de comptes, patrons par archétype), les contrats `Architecture`,
  `Cellule`, `Fourchette`, `Scenario`, `Deplacement`, la fonction d'application des déplacements, la
  migration 061 et les gardes. La spec métier est `09-modele-entreprise.md` (v2.1) ; ici, seulement le comment.
---

# Lot M1 — catalogue de variables et contrats du classeur

> Ce que ferait un vrai fonds : le directeur de la recherche tient UNE fiche par hypothèse maison (définition,
> unité, période, d'où peut venir le chiffre, comment on le contrôle, comment on en borne l'incertitude) et
> des feuilles de départ par type d'entreprise ; chaque classeur d'analyste s'y réfère. M1 écrit ces fiches
> et la forme du classeur ; il n'écrit AUCUN classeur (l'architecte, c'est M3).

## 0. Périmètre et interdits

- **Livré** : un fichier de référentiel, un contrat, un pont relationnel, une fonction pure, une migration
  écrite et éprouvée en négatif, des checks et leurs négatifs, la ligne `seuil_de_materialite`.
- **Pas livré** (lots suivants) : l'agent architecte, la porte calculée sur la base, la signature au PV (M3,
  migration 062) ; les demandes ciblées (M4) ; la ventilation au socle (M2) ; le gabarit bancaire (M2 bis) ;
  le calcul des fourchettes et le constructeur de scénarios (M6) ; la valorisation sur le classeur (M7).
- **Aucun appel modèle, aucune dépense.** Aucun prompt ne change (donc pas de règle #19/#39 à appliquer).
- **Réplicabilité** : aucun ticker, aucun nom de segment ou de produit dans le code ni dans le référentiel
  livrés (les fixtures de test, elles, sont copiées du réel et nomment NVDA/RVMD/JPM).
- **Ne pas appliquer la migration, ne pas committer, ne pas déployer** : Opus vérifie d'abord.

## 1. Le référentiel : `backend/app/frameworks/modele_entreprise.yaml` (NOUVEAU)

**Pourquoi un fichier à part de `frameworks.yaml`** : `schema_version` de `frameworks.yaml` clefe les réponses
(#64, #90) ; corriger une fiche de variable ne doit invalider aucune réponse. Même logique que
`types_evenement_version`. Le fichier porte donc sa propre `version: 1.0.0`. Le lien aux questions se vérifie
par un pont (§3), pas par une copie.

En-tête de commentaire dans le style de `frameworks.yaml` (pourquoi YAML : texte inerte, écrit à la main,
lisible au diff ; détenteur unique ; contrat qui le valide ; checks qui le gardent).

```yaml
version: 1.0.0

# Les FAMILLES DE COMPTES (09 §12.1). Le format agrégé du classeur EST le gabarit de la famille du titre.
familles_de_comptes:
  industrielle:
    gabarit: socle_comptes.yaml          # fichier de knowledge/, lu par le pont
    lignes_du_business_plan:             # renvoi aux ids de lignes du gabarit, jamais une copie
      [chiffre_affaires, cout_des_ventes, marge_brute, recherche_developpement,
       frais_commerciaux_administratifs, autres_charges_exploitation, resultat_exploitation, impot,
       amortissements, investissements_corporels, flux_exploitation, flux_de_tresorerie_disponible,
       capital_employe]
  bancaire:
    gabarit: null                        # À ÉCRIRE (lot M2 bis) — tant qu'il est null, une financière n'a
    motif_absence: >-                    # pas de format agrégé : l'architecte ne passera pas (M3 lira ceci)
      Le gabarit 1.1.0 est trompeur pour une banque (JPM : charges d'intérêts « 0 » en 2024-2025,
      résultat d'exploitation non déposé) ; gabarit bancaire à écrire avant l'entrée d'une financière.
    lignes_du_business_plan: []

famille_par_archetype:                   # chaque archétype de frameworks.yaml en déclare UNE
  rentable: industrielle
  pre_revenus: industrielle
  financiere: bancaire

controles:                               # vocabulaire FERMÉ ; chaque nom a sa fonction dans le code (§4)
  [positif, positif_ou_nul, proportion, probabilite, annee, part_calculee]

methodes_de_fourchette:                  # vocabulaire FERMÉ (09 §12.2), l'ordre d'une fiche = sa préférence
  [fourchette_publiee, dispersion_observee, classe_de_reference, recit_chiffre]

variables:
  - id: taille_du_marche
    libelle: Taille du marché adressable par le bloc
    definition: >-
      Dépense annuelle des clients que l'offre du bloc peut servir telle qu'elle existe, à la période dite ;
      un marché d'extension (offre non encore vendue) est un AUTRE bloc, de statut extension, jamais un
      plafond du bloc actuel.
    unite: M$
    periode: exercice                    # exercice | instant | sans_periode
    origines_admises: [piece, jugement]
    controle: positif
    questions_sources: [me_5, se_2]
    familles: [industrielle, bancaire]
    methode_de_fourchette: [fourchette_publiee, classe_de_reference, recit_chiffre]
  # … (liste complète au §1.1)
```

### 1.1 Les variables de la version 1.0.0

Écrire exactement celles-ci (ids, unités, origines, contrôles, questions sources, familles, méthodes) ; les
libellés et définitions sont à rédiger en substance économique, une à trois phrases, sans nom d'entreprise.

| id | unité | période | origines | contrôle | questions sources | familles | méthodes |
|---|---|---|---|---|---|---|---|
| taille_du_marche | M$ | exercice | piece, jugement | positif | me_5, se_2 | ind, banc | publiee, classe, recit |
| croissance_du_marche | %/an | exercice | piece, jugement | — | se_4, se_2, me_5 | ind, banc | publiee, dispersion, recit |
| part_de_marche | % | exercice | calcul | part_calculee | me_5, se_2 | ind, banc | dispersion, recit |
| chiffre_affaires_du_bloc | M$ | exercice | piece, calcul | positif_ou_nul | me_2, me_4 | ind | publiee, dispersion, recit |
| volume | unités | exercice | piece, jugement | positif_ou_nul | me_4 | ind | dispersion, recit |
| prix_moyen | $/unité | exercice | piece, jugement | positif | me_4, me_3, mo_6 | ind | dispersion, recit |
| part_recurrente | % | exercice | piece, jugement | proportion | me_2 | ind, banc | dispersion, recit |
| marge_contributive | % | exercice | piece, jugement, calcul | proportion | me_3, se_3 | ind | dispersion, recit |
| couts_communs | M$ | exercice | piece, calcul | positif_ou_nul | — | ind | dispersion, recit |
| taux_d_impot | % | exercice | piece, calcul | proportion | qf_1 | ind, banc | dispersion |
| capital_par_point_de_croissance | M$ | exercice | reponse_reprise, jugement | — | qf_3 | ind | dispersion, recit |
| probabilite_de_succes | (0-1) | sans_periode | jugement | probabilite | se_2, mo_4 | ind | classe_de_reference |
| annee_de_lancement | année | sans_periode | piece, jugement | annee | se_2, me_5 | ind | publiee, classe |
| ventes_au_pic | M$ | exercice | jugement | positif | me_5, me_4 | ind | classe, recit |
| duree_d_exclusivite | années | sans_periode | piece, jugement | positif | mo_4 | ind | publiee, classe |
| cout_restant_de_developpement | M$ | sans_periode | piece, jugement | positif_ou_nul | qf_7 | ind | publiee, classe |
| encours | M$ | instant | piece, jugement | positif | me_4, me_5 | banc | dispersion, recit |
| marge_d_interet | % | exercice | piece, calcul | — | me_3, me_4, mo_6 | banc | dispersion, recit |
| cout_du_risque | % | exercice | piece, jugement | — | me_3, me_4, se_4 | banc | dispersion, recit |
| coefficient_d_exploitation | % | exercice | piece, calcul | positif | se_3 | banc | dispersion, recit |
| fonds_propres_alloues | M$ | instant | piece, calcul | positif | qf_1, qf_3 | banc | dispersion |

(« ind » = industrielle, « banc » = bancaire ; méthodes abrégées : publiee = fourchette_publiee, dispersion =
dispersion_observee, classe = classe_de_reference, recit = recit_chiffre.)

- `couts_communs` sans question source : elle se lit au socle. `questions_sources: []` est admis ; la porte de
  l'architecte (M3) se calcule sur l'union des listes non vides.
- `capital_par_point_de_croissance` reprend l'encadré de qf_3 (`reponse_reprise`), déjà au contrat de
  valorisation (`OrigineReprise.chiffre`).
- `calcul` est une **4ᵉ origine**, propre au classeur (§2.2) : une cellule calculée à partir d'autres cellules.

### 1.2 Les patrons de départ (suggestions à l'architecte, 09 §2)

```yaml
patrons:
  rentable:
    blocs:
      - role: activite                   # un bloc par activité publiée ; l'architecte nomme et découpe
        variables: [chiffre_affaires_du_bloc, taille_du_marche, croissance_du_marche, part_de_marche,
                    volume, prix_moyen, part_recurrente, marge_contributive]
      - role: commun
        variables: [couts_communs, taux_d_impot, capital_par_point_de_croissance]
  pre_revenus:
    blocs:
      - role: programme                  # un bloc par programme en développement
        variables: [probabilite_de_succes, annee_de_lancement, ventes_au_pic, duree_d_exclusivite,
                    cout_restant_de_developpement, taille_du_marche, part_de_marche, marge_contributive]
      - role: commun
        variables: [couts_communs]
  financiere:
    blocs:
      - role: metier
        variables: [encours, marge_d_interet, cout_du_risque, coefficient_d_exploitation,
                    fonds_propres_alloues, part_recurrente]
      - role: commun
        variables: [taux_d_impot]
```

`role` est un vocabulaire fermé du contrat : `activite`, `programme`, `metier`, `commun`.

## 2. Le contrat : `backend/app/contracts/modele_entreprise_schema.py` (NOUVEAU)

Module PUR, pydantic v2, `Strict` de `analysis_v2_schemas` (extra interdit), docstring d'en-tête au style de
`modele_valorisation_schema.py` (ce que ferait un fonds, ce que le fichier vérifie et ce qu'il NE PEUT PAS
vérifier — #37). `__all__` explicite. Constante `ARCHITECTURE_SCHEMA_VERSION = "architecture-1.0.0"`.

### 2.1 Le référentiel

- `FicheVariable` : `id` (identifiant `^[a-z][a-z0-9_]*$`, ≤ 60), `libelle` (≥ 10), `definition` (≥ 40),
  `unite` (≥ 1), `periode: Literal["exercice","instant","sans_periode"]`, `origines_admises:
  list[Literal["piece","reponse_reprise","jugement","calcul"]]` (≥ 1, sans doublon), `controle:
  Optional[str]`, `questions_sources: list[id de question ^[a-z]{2}_[0-9]+$]` (sans doublon),
  `familles: list[str]` (≥ 1, sans doublon), `methode_de_fourchette: list[str]` (≥ 1, sans doublon).
- `FamilleDeComptes` : `gabarit: Optional[str]`, `motif_absence: Optional[str]` (≥ 20),
  `lignes_du_business_plan: list[id]` ; validateur : `gabarit` null ⟺ `motif_absence` présent ⟺ lignes vides.
- `BlocDePatron` : `role: Literal[...]`, `variables: list[id]` (≥ 1). `Patron` : `blocs` (≥ 1).
- `ReferentielModele` (le fichier) : `version`, `familles_de_comptes: dict[id, FamilleDeComptes]`,
  `famille_par_archetype: dict[str, str]`, `controles: list[id]`, `methodes_de_fourchette: list[id]`,
  `variables: list[FicheVariable]`, `patrons: dict[str, Patron]`.
  Cohérence INTERNE (validateur) : ids de variables uniques ; chaque `familles` d'une fiche ∈
  `familles_de_comptes` ; chaque `controle` ∈ `controles` ; chaque méthode ∈ `methodes_de_fourchette` ;
  `famille_par_archetype` vise une famille déclarée ; chaque variable d'un patron est une fiche ET a un sens
  dans la famille de l'archétype du patron ; `calcul` absent de `origines_admises` ⟹ contrôle ≠
  `part_calculee` ; `part_calculee` ⟹ `origines_admises == ["calcul"]`.

### 2.2 Les origines d'une cellule

Réutiliser `Origine` de `modele_valorisation_schema.py` (pièce, réponse reprise, jugement ancré) — **ne pas
la recopier** (#46, détenteur unique) — et ajouter `OrigineCalcul` :
`type: Literal["calcul"]`, `formule: str` validée par `formule_grammaire.analyser_formule` (grammaire fermée
existante ; les noms sont des ids de VARIABLE du même bloc et de la même période, `Nom[k]` = exercice décalé),
et `OrigineCellule = Annotated[Union[OriginePiece, OrigineReprise, OrigineJugement, OrigineCalcul],
Field(discriminator="type")]`.

### 2.3 L'architecture (sortie de l'architecte, M3 ; M1 en fixe la forme)

- `VariablePropre(FicheVariable)` + `motif: str (≥ 30)` — une variable déclarée par l'architecte hors
  catalogue, marquée « propre au titre ».
- `RattachementPublie` : `type: "publie"`, `axe: str`, `membre: str` (axe et membre XBRL en clair, M0 ; le
  pont contre la ventilation au socle arrive avec M2/M3).
- `RattachementParent` : `type: "parent"`, `bloc: id`.
- `RattachementAgrege` : `type: "agrege"`, `ligne: id` (une ligne du business plan de la famille) — le cas
  RVMD : tous ses blocs sont estimés et se raccordent à une ligne des comptes.
- `Bloc` : `id`, `libelle`, `role`, `statut: Literal["metier_actuel","extension_annoncee","en_developpement"]`,
  `maille: Literal["publie","estime"]`, `rattachement` (union discriminée des trois), `variables: list[id]`
  (≥ 1). Validateur : `maille == "publie"` ⟺ rattachement `publie`.
- `PassageAgrege` : `ligne: id`, `formule: str` (grammaire fermée ; noms de la forme `bloc__variable`,
  double tiret bas comme séparateur — un id ne contient jamais `__`, à garder par le motif d'identifiant).
- `AuteurQuestion` : `type: "question"`, `question_id`. `AuteurDemande` : `type: "demande_ciblee"`.
- `CelluleAttendue` : `bloc`, `variable`, `periodes: list[str]` (≥ 1 ; motif `^FY[0-9]{4}$` ou
  `"sans_periode"`), `auteur` (union des deux).
- `Architecture` : `schema_version: Literal["architecture-1.0.0"]`, `ticker_id`, `version: int ≥ 1`,
  `archetype`, `famille`, `version_referentiel`, `blocs` (≥ 1), `variables_propres`, `passage_a_l_agrege`
  (≥ 1), `cellules_attendues` (≥ 1).
  Cohérence INTERNE : ids de blocs uniques ; un `parent` vise un bloc déclaré, sans cycle, et ne se vise pas ;
  ids des variables propres uniques ; chaque `PassageAgrege.ligne` unique ; chaque nom d'une formule de
  passage = `bloc__variable` d'un bloc déclaré qui retient cette variable ; **une seule cellule attendue par
  (bloc, variable, période)** — un seul auteur (#99 généralisé) ; une cellule attendue vise un bloc déclaré et
  une variable que ce bloc retient ; variable `sans_periode` ⟹ `periodes == ["sans_periode"]` (vérifié au
  pont, car la période d'une variable de catalogue est au référentiel — #37).

### 2.4 La cellule

`Cellule` : `bloc`, `variable`, `periode` (même motif), `valeur: float`, `unite`, `origine: OrigineCellule`,
`auteur` (`AuteurQuestion` + `answer_id: int`, ou `AuteurDemande` + `demande_id: int`). Rien de stocké en M1 :
la cellule est la forme que liront M4/M5 (vue recalculée à la lecture, 09 §9).

### 2.5 Fourchette, scénario, déplacement (09 §12.2 — tables dès M1, central seul peuplé en v1)

- `Fourchette` : `bloc`, `variable`, `periode_debut`, `periode_fin`, `bas: float`, `haut: float`,
  `methode` (id), `origine_bas: OrigineCellule`, `origine_haut: OrigineCellule`. Validateur : `bas ≤ haut` ;
  `periode_debut ≤ periode_fin` (ordre des exercices).
- `Scenario` : `nom` (identifiant), `recit` (≥ 20), `nature: Literal["central","nomme","branche"]`,
  `probabilite: Optional[float]`, `deplacements: list[Deplacement]`. Validateur : `central` ⟹ aucun
  déplacement, aucune probabilité ; `nomme` ⟹ ≥ 1 déplacement, pas de probabilité ; `branche` ⟹ ≥ 1
  déplacement et probabilité ∈ [0, 1] ; deux déplacements d'un même scénario ne visent jamais la même
  (bloc, variable) sur des périodes qui se chevauchent.
- `Deplacement` : `bloc`, `variable`, `periode_debut`, `periode_fin`, `cible:
  Literal["borne_basse","borne_haute","valeur_dite"]`, `valeur_dite: Optional[float]`, `motif` (≥ 20),
  `source_entry_refs: list[int]` (peut être vide pour une borne : la pièce est celle de la fourchette).
  Validateur : `valeur_dite` présente ⟺ `cible == "valeur_dite"` ; une `valeur_dite` exige ≥ 1 pièce.
- Constante `SCENARIO_CENTRAL = Scenario(nom="central", recit=…, nature="central", deplacements=[])` : le
  central n'est PAS une ligne en base (il ne pourrait que diverger de sa définition) ; c'est cette constante.

## 3. Le pont relationnel : `backend/app/modele_entreprise/referentiel.py` (NOUVEAU module)

Nouveau paquet `backend/app/modele_entreprise/` (avec `__init__.py` et un `ARCHITECTURE.md` court : ce qui
existe, ce qui arrive en M2-M7). Fonctions :

- `load_referentiel(chemin=None) -> ReferentielModele` : lit le YAML, valide le contrat, puis
  `_valider_pont_referentiel(ref, frameworks)` (frameworks = `agents.v2.frameworks.load_frameworks()`), qui
  lève `ReferentielRefuse(code, motif)` — un code lettre par règle, comme `[S]` de `frameworks.py` :
  - [R1] chaque archétype de `frameworks.yaml` a une famille, et `famille_par_archetype` n'en nomme pas
    d'autre ; chaque clé de `patrons` est un archétype ;
  - [R2] chaque `questions_sources` existe dans `frameworks.yaml` ;
  - [R3] chaque `lignes_du_business_plan` d'une famille à gabarit existe dans ce gabarit (charger via
    `knowledge/socle_comptes.py`, détenteur de la lecture du gabarit — ne pas re-parser le YAML) ;
  - [R4] chaque nom de `controles` a une fonction dans `CONTROLES` (§4), et réciproquement ;
  - [R5] une variable d'origine `reponse_reprise` a au moins une question source qui déclare un encadré
    (`chiffres_cles` non vide).
- `variables_de_la_famille(ref, famille) -> list[FicheVariable]` (ce que l'architecte recevra).
- `questions_sources_applicables(ref, frameworks, archetype) -> list[str]` : l'union des questions sources
  des variables de la famille de l'archétype, moins les questions `sans_objet` pour cet archétype
  (`variables_par_archetype[archetype].mode`), triée. C'est l'entrée de la porte de l'architecte (M3).
- `valider_pont_architecture(arch, ref) -> None`, lève `ArchitectureRefusee(code, motif)` :
  - [P1] `arch.famille == famille_par_archetype[arch.archetype]`, et cette famille a un gabarit (sinon motif =
    `motif_absence`) ; `arch.version_referentiel == ref.version` ;
  - [P2] chaque variable retenue par un bloc est une fiche de la famille OU une variable propre ; une variable
    propre ne porte pas l'id d'une fiche du catalogue ;
  - [P3] chaque `PassageAgrege.ligne` ∈ `lignes_du_business_plan` de la famille ;
  - [P4] chaque cellule attendue respecte la période de sa variable (`sans_periode` ⟺ `["sans_periode"]`) ;
  - [P5] une cellule attendue dont l'auteur est une question : cette question est une question source de la
    variable (sinon c'est une demande ciblée) ;
  - [P6] un bloc `en_developpement` ou `extension_annoncee` ne porte jamais `part_de_marche` calculée sur une
    période passée — reporté : noter en TODO M5, ne pas coder (pas de cellule en M1).
- `valider_cellule(cellule, ref, arch) -> None`, lève `CelluleRefusee(code, motif)` :
  - [C1] la cellule est attendue par l'architecture (bloc, variable, période) ;
  - [C2] son origine ∈ `origines_admises` de la fiche ;
  - [C3] unité = celle de la fiche ;
  - [C4] le contrôle de la fiche passe (§4) ;
  - [C5] origine `calcul` : chaque nom de la formule est une variable du même bloc (le contrôle de
    `part_calculee` est au §4).

## 4. Les contrôles : `backend/app/modele_entreprise/controles.py` (NOUVEAU)

`CONTROLES: dict[str, Callable[[Cellule, ContexteControle], Optional[str]]]` — rend `None` si la cellule
tient, sinon le motif. `ContexteControle` (dataclass) : `dernier_exercice_publie: Optional[str]`.
- `positif` (> 0), `positif_ou_nul` (≥ 0), `proportion` (0 ≤ v ≤ 100), `probabilite` (0 ≤ v ≤ 1),
  `annee` (entier entre 1900 et 2100) ;
- `part_calculee` : origine `calcul` ; la formule nomme `chiffre_affaires_du_bloc` au numérateur et
  `taille_du_marche` au dénominateur (`denominateurs_de_la_formule` existe dans `formule_grammaire`) ; la
  période de la cellule ≤ `dernier_exercice_publie` — **la part prise se mesure sur des revenus publiés,
  jamais sur des revenus futurs** (09 §6, cas NVDA me_5 #1370). `dernier_exercice_publie` absent ⟹ motif
  « exercice publié inconnu » (jamais un vert par défaut : `feedback_check_degrade_en_sortant_a_zero`).

## 5. L'application des déplacements : `backend/app/modele_entreprise/scenarios.py` (NOUVEAU)

`appliquer_scenario(centrales: Mapping[tuple[bloc, variable, periode], float], scenario: Scenario,
fourchettes: Sequence[Fourchette]) -> dict[...]` — fonction PURE, la charnière de 09 §12.2 :
- `SCENARIO_CENTRAL` ⟹ copie des centrales, à l'identique ;
- pour chaque déplacement, chaque période de `[periode_debut, periode_fin]` présente dans les centrales prend
  la `valeur_dite`, ou la borne de la fourchette qui couvre (bloc, variable, période) ; aucune fourchette qui
  couvre ⟹ `ScenarioInapplicable(motif nommé)` ; un déplacement qui ne touche AUCUNE cellule centrale ⟹
  `ScenarioInapplicable` (« un risque cité qui ne bouge rien », 09 §6) ;
- les clés non visées restent au central (une histoire ne déplace que ce qu'elle touche).
Rien n'appelle encore cette fonction hors des checks (M7 la branchera sur `evaluer_modele`) : le dire dans
l'`ARCHITECTURE.md` du module, pour qu'aucun lecteur ne la croie branchée.

## 6. Le paramètre du fonds

Dans `frameworks.yaml`, `parametres_du_fonds`, ajouter :

```yaml
  seuil_de_materialite:
    valeur: 10
    unite: "% de la valeur centrale"
    decide_le: 2026-10-21
    revoir_avant: 2027-10-21
    decision: >-
      Arbitrage du 2026-10-21 (spec du modèle de l'entreprise, §11.1, #140) : une variable dont l'effet
      isolé, à sa borne basse ou haute, dépasse 10 % de la valeur centrale figure dans un scénario ou est
      écartée avec motif ; revu une fois l'an, comme le taux exigé.
```

Ne PAS bumper `schema_version`. Si un check existant refuse un paramètre du fonds qu'aucun encadré ne lit
(orphelin), ne pas l'affaiblir : le lire, et rapporter le refus exact à Opus (c'est une décision).

## 7. La migration 061 : `backend/app/db/migrations/061_v3_classeur_entreprise.sql` (ÉCRITE, NON APPLIQUÉE)

Projection du contrat (l'agent dicte la table, en-tête au style de `051_v3_modeles_valorisation.sql`).
ADDITIVE, `BEGIN; … COMMIT;`, quatre registres APPEND-ONLY (trigger qui refuse UPDATE et DELETE même au
propriétaire, privilèges du rôle applicatif : SELECT, INSERT seulement — copier exactement le motif de 051) :
- `architectures_modele` (id, ticker_id → tickers, version, schema_version, version_referentiel, auteur,
  `contenu jsonb` = l'`Architecture` entière, propose_le) ; UNIQUE (ticker_id, version) ; CHECK que
  `contenu` dit le même ticker, la même version, le même schema_version (comme 051). Les décisions de
  signature = M3 (062), pas ici.
- `modele_fourchettes` (id, architecture_id → architectures_modele, bloc, variable, periode_debut,
  periode_fin, bas, haut, methode, contenu jsonb (la `Fourchette`), auteur, inscrite_le) ; CHECK bas ≤ haut ;
  CHECK cohérence contenu/colonnes.
- `modele_scenarios` (id, architecture_id, nom, nature, probabilite, contenu jsonb (le `Scenario` sans ses
  déplacements), auteur, inscrit_le) ; CHECK `nature IN ('nomme','branche')` (**le central n'est jamais une
  ligne**, §2.5) ; CHECK `(nature='branche') = (probabilite IS NOT NULL)` et probabilité ∈ [0,1].
- `modele_deplacements` (id, scenario_id → modele_scenarios, bloc, variable, periode_debut, periode_fin,
  cible, valeur_dite, motif, source_entry_refs integer[]) ; CHECK `(cible='valeur_dite') = (valeur_dite IS
  NOT NULL)`.
Révision = nouvelle ligne datée (09 §12.2). Pas de `superseded_by`.

Module d'écriture `backend/app/modele_entreprise/registre.py` : `proposer_architecture(conn, arch, auteur)`
(valide contrat + pont avant INSERT ; numéro de version = max + 1 sous verrou du titre, comme
`valorisation/signature.py`), `inscrire_fourchette`, `inscrire_scenario` (scénario + ses déplacements dans une
transaction explicite — #35 ; refuse `SCENARIO_CENTRAL`). asyncpg, `$1…`, JSONB passé en dict (#1).

## 8. Les gardes (une brique n'est faite que gardée ET éprouvée en négatif)

- `backend/checks/check_modele_entreprise.py` (sans base) :
  - le référentiel livré se charge, contrat + pont verts ; nombre de fiches = 21, patrons = 3 archétypes ;
  - un cas par règle de contrat (§2) et de pont ([R1]-[R5], [P1]-[P5], [C1]-[C5]) : objet valide accepté,
    objet muté refusé AVEC LE BON CODE (asserter le code, pas seulement l'exception) ;
  - fixtures d'architecture **copiées du réel** dans `checks/fixtures/modele_entreprise/` : NVDA (blocs
    centres de données publié → calcul 162 361 / réseau 31 376 = 193 737 M$ FY2025 ; jeux, visualisation,
    automobile publiés ; « grands hébergeurs » estimé sous calcul ; un bloc commun), RVMD (trois programmes
    estimés rattachés à la ligne `recherche_developpement`, un commun), JPM (4 métiers publiés) — chiffres et
    noms tirés de `roadmap/V3/mesures/2026-10-21/mesure_m0_ventilation.md`, jamais inventés. NVDA et RVMD
    passent le pont ; JPM est refusé en [P1] avec le motif du gabarit bancaire absent (c'est la vérité
    d'aujourd'hui, la fixture le fige) ;
  - `questions_sources_applicables` : rentable et pre_revenus rendent des listes non vides, et pour
    `pre_revenus` aucune question `sans_objet` à cet archétype n'y figure (qf_1, qf_3, mo_6 — vérifier
    contre `frameworks.yaml`, ne pas les écrire en dur dans l'assert : les lire) ;
  - `appliquer_scenario` : central = identité ; borne basse appliquée sur la plage seulement ; valeur dite ;
    déplacement sans fourchette ⟹ refus ; déplacement qui ne touche rien ⟹ refus ; branche à probabilité ;
  - `part_calculee` : refusée sur un exercice postérieur au dernier publié, refusée sans exercice publié connu.
- **Réplicabilité** : `check_modele_entreprise.py` greppe `app/modele_entreprise/`,
  `app/contracts/modele_entreprise_schema.py` et `app/frameworks/modele_entreprise.yaml` contre
  `NVDA|RVMD|JPM|MSFT|NVIDIA|Revolution|JPMorgan|Microsoft` et les noms de blocs des fixtures (lus DANS les
  fixtures, pas recopiés), en dépouillant d'abord les commentaires et docstrings
  (`feedback_grep_interdit_lit_sa_propre_enonciation`) — puis asserte en POSITIF qu'au moins un fichier a été
  lu (pas de vert sur liste vide).
- `backend/checks/check_modele_entreprise_persist.py` (avec base, motif `avec_base.sh` /
  `check_signature_modele_persist.py`) : contre la migration appliquée dans une transaction **ROLLBACK** —
  proposer une architecture NVDA (fixture), inscrire une fourchette, un scénario nommé à deux déplacements ;
  relire ; puis prouver l'append-only PAR LES REFUS (UPDATE refusé, DELETE refusé, scénario `central` refusé
  par le CHECK, branche sans probabilité refusée). Jamais d'écriture qui survit (`feedback_append_only_verif_par_refus`).
  Tant que 061 n'est pas appliquée, ce check doit **sortir ≠ 0** en nommant « migration 061 absente », jamais
  sauter (`feedback_check_degrade_en_sortant_a_zero`).
- `backend/checks/negatif_modele_entreprise.sh` : sur le harnais existant (`_harness.py`, détenteur unique,
  #65) — une mutation par garde du contrat, du pont, des contrôles et de `appliquer_scenario`, chaque
  mutation devant faire rougir **l'assert nommé** attendu (`feedback_test_negatif_trois_faux_verts` : motif de
  mutation unique dans le fichier, garde déléguée mutée chez son détenteur). Inclure une mutation qui ajoute
  « NVDA » dans le YAML livré (la garde de réplicabilité doit rougir).
- `backend/checks/negatif_061.sh` sur le motif de `negatif_051.sh` (la migration éprouvée en négatif avant
  application).
- Ajouter les nouveaux checks à `run_all.sh` ; la suite ENTIÈRE doit rester verte (66 checks, 5093
  assertions avant ce lot) — sauf `check_modele_entreprise_persist.py`, rouge « migration 061 absente » tant
  qu'Opus ne l'a pas appliquée : le rapporter tel quel.

## 9. Ce que Sonnet rend à Opus

1. La liste des fichiers créés/modifiés.
2. La sortie brute (bilan, par `grep -E` sur les motifs de bilan, pas `tail -1`) de : `run_all.sh`,
   `negatif_modele_entreprise.sh`, `negatif_061.sh`, et de `check_modele_entreprise.py` seul.
3. Tout écart à cette spec, et pourquoi (une règle intenable, un conflit avec un check existant) — sans
   l'avoir contourné en affaiblissant une garde.
