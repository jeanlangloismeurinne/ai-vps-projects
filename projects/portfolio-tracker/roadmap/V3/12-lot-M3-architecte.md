---
id: spec-lot-m3
status: spec-2026-10-22 (Opus) — à exécuter par Sonnet
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M3 (B4 du plan `07-avant-comite.md`) : l'agent ARCHITECTE du classeur de
  l'entreprise — sa porte, la matière qu'il reçoit, ses contrôles de structure, la signature de son
  architecture au procès-verbal (avec interrupteur). Spec métier : `09-modele-entreprise.md` (§1.1, §1.2,
  §3 ①-③, §4, §6 ligne « Architecture », §7, §11.2) ; lots précédents : `10-lot-M1-…`, `11-lot-M2-…`.
---

# Lot M3 — l'architecte du classeur, sa porte, ses contrôles, sa signature

> **Ce que ferait un vrai fonds** : avant d'ouvrir un classeur, l'analyste relit le dossier — comptes,
> note sectorielle du dernier rapport, ses propres réponses sur les marchés et les prix, les dernières
> notes flash — puis dessine l'architecture : quelles activités, à quelle maille, avec quelles hypothèses
> maison, et qui remplira chaque case. Il ne réinvente aucun secteur publié, il ne compte pas deux fois
> la même activité, il dit pourquoi il découpe plus fin que la publication, et il garde à part ce qui
> n'est qu'annoncé. Le directeur de la recherche relit ce plan (les écarts aux comptes lui sont montrés)
> et le signe ou le renvoie. Tant que le dossier ne permet pas de dessiner (une question sur les marchés
> jamais instruite), on ne dessine pas.

## 0. Ligne de base mesurée (2026-10-22, Opus, gratuit) — à RE-MESURER en premier (§10, étape 0)

| Fait | Mesure |
|---|---|
| Registre `architectures_modele` | 0 ligne (migration 061 appliquée) |
| Pièce « ventilation publiée » en base | **aucune** (M2 déployé ce jour `67f7e87`, jamais publiée en production) |
| `montrer_ventilation.sh NVDA` | `ventilee` — 4 axes, 100 cellules, 13 bouclés / 10 non ventilés / **1 découpage changé** ; **au 10-Q du 2026-08-26, NVDA a redécoupé ses marchés** : Data Center = Hyperscale + AI Clouds, Industrial & Enterprise (membres nouveaux, cumuls S1 2025 et S1 2026 seulement), Edge Computing remplace Gaming / ProViz / Automotive / OEM (aucun exercice annuel à ce découpage) |
| `montrer_ventilation.sh RVMD` | `secteur_unique` — aucun axe : tous ses blocs seront estimés |
| Classement | NVDA `rentable` (2026-09-24) ; **RVMD reclassée `rentable` par le comité le 2026-10-18** (autorisation de mise sur le marché du 26/08) → mêmes 12 questions sources que NVDA, même patron — que l'architecte de RVMD devra DÉPASSER (un produit vendu + des programmes en développement) |
| Porte NVDA (lecture du 2026-10-21) | ouverte : les 12 questions sources ont une première réponse instruite |
| Rendu de la ventilation | libellés humains seulement (« Data Center ») — **aucun identifiant de membre** : un modèle ne peut pas citer un membre XBRL qu'on ne lui montre pas (§3.2) |

## 1. Périmètre et interdits

- **Livré** : la porte (pure) ; la matière de l'architecte (chargement + rendu pur) ; l'agent (prompt dans le
  code, exemple validé, un renvoi) ; les contrôles de structure [S1]-[S9] ; le contrat `architecture-1.1.0` et le
  référentiel `1.1.0` ; la migration 062 (procès-verbal de l'architecture) écrite et éprouvée, **non appliquée** ;
  le service « architecture en vigueur » avec interrupteur ; trois endpoints ; deux outils ; checks et négatifs.
- **Pas livré** : les demandes ciblées et la projection des encadrés en cellules (M4) ; l'agrégé et ses raccords
  chiffrés, [P6] (M5) ; fourchettes, inventaire, scénarios (M6) ; l'écran (E1) ; aucun branchement au matin.
- **Ne change pas** : `frameworks.yaml` hors `parametres_du_fonds` (§7 — `schema_version` reste `v3.0.0`, aucune
  réponse invalidée, #64) ; aucun prompt en base ; `socle_comptes.yaml`, `ventilation_publiee.yaml`.
- **Réplicabilité** (07) : aucun ticker, CIK, nom de segment, de produit ou de membre XBRL propre à un émetteur
  dans le code, le prompt, l'exemple JSON ni le référentiel. L'exemple du prompt est une **société fictive**. Les
  fixtures, elles, sont copiées du réel (NVDA, RVMD) et le disent.
- **Ne pas committer, ne pas déployer, ne pas appliquer 062, ne rien écrire en production** (pas de `--ecrire`) :
  Opus vérifie d'abord. Les appels modèle de l'acceptation (§10) sont **à blanc**.

## 2. Le référentiel et le contrat (montées de version)

### 2.1 `app/frameworks/modele_entreprise.yaml` → `version: "1.1.0"`

1. **Fiche `chiffre_affaires_du_bloc`** : champ neuf `somme_vers_ligne: chiffre_affaires`. Sens : *le chiffre
   d'affaires des blocs de premier niveau s'additionne en la ligne `chiffre_affaires` de l'agrégé*. C'est la
   donnée que lit [S7] — le code ne nomme jamais `chiffre_affaires_du_bloc` ni `chiffre_affaires` (détenteur
   unique, #46 ; une banque déclarera la sienne en M2 bis). Aucune autre fiche ne le porte en 1.1.0.
2. **Interrupteur** (principe fondateur n° 3), en tête de fichier, commenté comme `rappels_ecartes` :
   ```yaml
   # L'INTERRUPTEUR de la signature de l'architecture (09 §1.2, §7). true = deux signatures : l'architecture
   # proposée attend la signature du comité avant d'ouvrir les relances ciblées (M4). false = cible annoncée,
   # une seule signature (celle du classeur) : la dernière architecture proposée qui tient AUJOURD'HUI est en
   # vigueur sans signature. Lu à la LECTURE (`servir_architecture`) : le basculer ne réécrit rien, ne change
   # pas `version` (aucune architecture n'est invalidée) et le PV déjà écrit reste lisible.
   signature_de_l_architecture: true
   ```
   ⚠️ C'est la SEULE clef du fichier dont le changement ne monte pas `version` — le dire dans le commentaire.

### 2.2 `app/contracts/modele_entreprise_schema.py`

- `FicheVariable.somme_vers_ligne: Optional[Identifiant] = None`. `ReferentielModele` gagne
  `signature_de_l_architecture: bool` (requis).
- **`architecture-1.1.0`** (`ARCHITECTURE_SCHEMA_VERSION`, `Literal` mis à jour ; 0 ligne en base, aucune reprise) :
  `Bloc` gagne
  - `motif: str` (min 20) — pourquoi ce bloc existe, à cette maille, sous ce statut (ce que le comité lit) ;
  - `pieces: list[int]` — les pièces du dossier qui le fondent (ids de `knowledge_entries`, §3.3) ;
  - validateur : `pieces` non vide si `maille == "estime"` ou `statut != "metier_actuel"` (un découpage estimé
    ou une activité annoncée sans pièce n'est qu'une opinion).
- Ces champs sont la sortie du modèle ; l'en-tête reste posé par le code (§4.3).

### 2.3 Le pont du référentiel (`referentiel.py`)

- **[R6]** `somme_vers_ligne`, s'il est présent, est une ligne de `lignes_du_business_plan` de CHAQUE famille de la
  fiche qui a un gabarit.
- `load_referentiel` reste le seul chargeur ; `valider_pont_architecture` [P1]-[P5] inchangé.

## 3. La matière de l'architecte

### 3.1 La porte : `app/modele_entreprise/porte.py` (NOUVEAU, pur)

`porte_de_l_architecte(etat: EtatDossier, ref: ReferentielModele) -> Porte` avec
`Porte(ouverte: bool, archetype: Optional[str], questions: list[EtatQuestionSource])` et
`EtatQuestionSource(question_id, framework_id, ouvre: bool, raison: str, answer_id: Optional[int])`.

La règle (09 §11.2 — « au moins une réponse instruite, quel qu'en soit le statut ; un échec technique ou une
question jamais cherchée ferme la porte, et le manque est nommé ») se lit **sur le diagnostic existant**,
jamais recopiée : pour chaque question de `questions_sources_applicables(ref, etat.fichier, archetype)`, on
appelle `manque_de_la_question` exactement comme `parcours._lignes` (mêmes arguments — extraire au besoin un
appel commun dans `parcours.py` plutôt que dupliquer la préparation des arguments, #46) :

| Diagnostic | La question… | Raison écrite |
|---|---|---|
| aucun manque (tient, acceptée, dispensée) | ouvre | « réponse #id qui tient » / « acceptée par le comité » / « dispensée par le comité » |
| `renvoyee`, `perimee`, `pas_encore_observable` | ouvre | la réponse #id existe ; l'architecte la reçoit avec son verdict / sa date / son attente |
| `non_fondee`, cause ≠ `source_indisponible` | ouvre | « non fondable : {explication} » — l'absence de publication EST une information |
| `non_fondee`, cause `source_indisponible` | **ferme** | échec technique : relancer avant de dessiner |
| `sans_reponse` (toute cause) | **ferme** | aucune réponse instruite |
| `rouverte_comite` | **ferme** | le comité a renvoyé ou remis à zéro ; rien n'a été écrit depuis |
| question sans framework applicable (`applicables` None) | **ferme** | « émetteur non classé » |

Émetteur sans archétype → `Porte(ouverte=False, archetype=None, questions=[])` avec la raison au niveau de la
porte. **Décision d'Opus, à porter au journal** : une réponse renvoyée par le contrôle ouvre (l'arbitrage dit
« quel qu'en soit le statut ») ; l'architecte la reçoit marquée « refusée par le contrôle : motif ».

### 3.2 Le rendu de la ventilation pour l'architecte (`app/knowledge/ventilation.py`)

Le rendu d'un inventaire est un producteur (#69) : le modèle ne peut citer que ce qu'il voit. Ajouter à
`rendre_ventilation(structure, *, raison_sociale, avec_identifiants: bool = False)` : avec `True`, chaque membre
est suivi de son adresse **`[axe=<id d'axe du référentiel> membre=<qname XBRL>]`** (ex. de forme :
`[axe=activites membre=xyz:WidgetsMember]`), une fois par membre et par tableau. Défaut `False` : le rendu de
M2 et l'outil `montrer_ventilation.sh` sont inchangés (ils sont gardés — vérifier que leurs checks restent verts).
`RattachementPublie.axe` = l'id d'axe du référentiel (`activites`, `secteurs`, `geographie`), jamais un axe XBRL ;
`membre` = le qname tel que rendu.

### 3.3 Le chargement et le rendu : `app/modele_entreprise/matiere.py` (NOUVEAU)

`charger_matiere(conn, ticker_id, *, publier: bool) -> Matiere` — la SEULE moitié qui lit (et, avec
`publier=True`, publie la ventilation si elle manque) ; `rendre_matiere(m: Matiere) -> str` — PURE, déterministe
(tri stable, aucun horodatage volatil), c'est exactement ce que le modèle voit.

`Matiere` (dataclass gelée) porte, dans cet ordre de rendu :

1. **L'émetteur** : raison sociale et CIK (`identite_de_l_emetteur`, #86/#122) — jamais déduits d'une pièce.
2. **L'horloge** (#120 ; un agent n'a pas d'horloge) : date du jour, dernière clôture publiée, dernière clôture
   annuelle (`horloge_du_titre`).
3. **Le classement en vigueur** : archétype, date, motif et, s'il a été décidé par le comité, le dépôt qui l'a
   déclenché (`read_classement`). La famille de comptes du référentiel.
4. **Les périodes du classeur** (§3.4) : historiques et projetées, les seules admises dans `cellules_attendues`.
5. **Les lignes du business plan** de la famille (format agrégé).
6. **Les fiches du catalogue de la famille** (`variables_de_la_famille`) : id, libellé, définition, unité,
   période, origines admises, questions sources, `somme_vers_ligne`. Pas `methode_de_fourchette` (M6).
   Puis **le patron** de l'archétype, présenté comme une suggestion.
7. **Les comptes reconstitués** : `rendre_socle` de la structure en vigueur (`socle_en_vigueur`, sinon
   `assurer_socle` — à blanc : calculé, pas publié), avec l'id de la pièce s'il existe.
8. **La ventilation publiée** : `rendre_ventilation(…, avec_identifiants=True)` + id de la pièce. `secteur_unique` /
   `sans_ventilation` : la phrase du constat (« l'émetteur ne publie qu'un secteur : tous les blocs seront
   estimés et se raccordent à une ligne des comptes ») — **aucune pièce citable**. Famille sans gabarit : la
   matière n'est pas construite (refus nommé, [P1] dirait la même chose plus tard).
9. **Les réponses des questions sources** (une section par question, dans l'ordre de la porte) : énoncé ; la
   réponse retenue = celle qui tient, sinon la plus récente instruite ; son statut, sa date d'écriture, son
   actualité et son motif, le verdict du contrôle et son motif, le `verbatim` ENTIER (#27 : on ne tronque pas),
   les chiffres clés avec unité et période, `sens`, les ids des pièces citées. Une question qui ouvre la porte
   sans réponse (acceptée, dispensée) le dit en une ligne.
10. **Les notes flash** lues depuis la dernière clôture annuelle : date, types, résumé, accession, pièce —
    les `QualificationLue` que rend déjà `horloge_du_titre` (son 2ᵉ membre ; détenteur unique, #46 — ne pas
    relire les notes par un autre chemin).

`Matiere.pieces_citables: frozenset[int]` = pièce du socle, pièce de la ventilation, pièces citées par les
réponses rendues, pièces des notes flash rendues. C'est l'univers de [S6].

`publier=False` (à blanc) : rien n'est écrit, la ventilation est relevée en mémoire, et son id de pièce est
absent (le rendu dit « pièce non encore publiée ») ; `--ecrire` (§6) passe `publier=True`.

### 3.4 Les périodes du classeur — détenteur unique dans `app/modele_entreprise/periodes.py` (NOUVEAU, pur)

- `periode_du_classeur(fin: date) -> str` : `FY{(fin − 7 jours).year}` — la fin d'un exercice de 52/53 semaines
  qui tombe les premiers jours de janvier appartient à l'année qui s'achève. Docstring : pourquoi ce décalage.
- `periodes_du_classeur(structure_du_socle, horizon: int) -> PeriodesDuClasseur(historiques, projetees)` :
  historiques = les exercices `FY{fin}` du socle, convertis ; deux fins qui donnent le même id → refus nommé
  (jamais deux exercices sous un nom) ; projetées = les `horizon` exercices qui suivent le dernier historique.
- `horizon` = `parametres_du_fonds.horizon_de_projection.valeur` (§7).

## 4. L'agent : `app/modele_entreprise/architecte.py` (NOUVEAU)

### 4.1 Ordre d'exécution de `proposer_architecture_du_titre(ticker_id, *, agent=None, ecrire=False, hors_porte=False)`

1. Charger `etat` (`charger_etat_dossier`), la porte ; **porte fermée** → `PorteFermee` levée AVANT toute
   dépense (#40, #63), avec les questions qui ferment et leur raison — sauf `hors_porte=True`, admis **seulement
   à blanc** (`ecrire=True` + `hors_porte=True` → refus immédiat).
2. Charger la matière (`publier=ecrire`) ; rendre ; l'agent (provider de l'`ingestion-agent`, prompt système de
   l'architecte, comme `traducteur._resolve_traducteur_agent`).
3. `run_json_agent(agent, messages, ArchitecteSortie, json_object=False)` — `ArchitecteSortie(Strict)` =
   `blocs, variables_propres, passage_a_l_agrege, cellules_attendues` (rien d'autre : Strict refuse un
   `ticker_id` venu du modèle).
4. **Le code pose l'en-tête** : `ticker_id`, `version` (= dernière version du titre + 1, lue au registre ; 1 sinon),
   `archetype` et `famille` (classement en vigueur, référentiel), `version_referentiel`, `schema_version`.
5. Valider : contrat `Architecture` → `valider_pont_architecture` [P1]-[P5] → `valider_structure` [S1]-[S9]
   (§5). Refus → **renvoyé UNE fois** au modèle avec TOUS les motifs (précédent #101, `traducteur` étape 6), puis
   `ArchitectureRefusee` nommée, coût cumulé attaché (comme `AgentOutputInvalid`).
6. `ecrire=True` : `registre.proposer_architecture(conn, arch, ref, auteur=f"architecte ({modele})")`, en
   transaction (#35) ; rendre l'id. Sinon rien n'est écrit.
7. Rendre `ResultatArchitecte(porte, architecture, signaux, run)` — `signaux` = les écarts NOMMÉS de [S2] et
   [S3b] (§5), ce que le comité aura sous les yeux.

### 4.2 Le prompt (dans le code, `_ARCHITECTE_SYSTEM_PROMPT`, comme le traducteur ; #19/#39 au câblage runtime)

En termes d'analyste de fonds, pas de schéma. Il dit, au minimum :
- tu dessines l'architecture du classeur de CETTE entreprise à partir du dossier fourni, avec les fiches maison ;
  le patron est une suggestion ; une variable propre n'est déclarée que si aucune fiche ne convient, avec sa
  fiche complète et son motif ;
- un bloc publié cite son adresse **recopiée** de la ventilation (`axe`, `membre`) ; au premier niveau, un seul
  axe ; jamais un bloc et son propre sous-membre côte à côte au même niveau ; ce qu'aucun bloc publié ne couvre
  va dans un bloc estimé « reste » rattaché à la ligne des comptes ;
- un bloc plus fin que la publication est `estime`, rattaché à son bloc parent, avec motif et pièces ;
- une activité seulement annoncée est `extension_annoncee` : elle n'entre dans AUCUNE formule de passage (elle
  ira dans les scénarios) ; un programme en développement est `en_developpement` et peut y entrer (pondéré) ;
- si la publication a changé de découpage, choisis-en un, dis lequel et pourquoi dans le motif des blocs ;
- chaque cellule attendue : une question source de la variable si cette question l'instruit, sinon
  `demande_ciblee` ; périodes prises dans la liste fournie ; les variables lues par une formule de passage
  couvrent toutes les périodes projetées ;
- les identifiants : minuscules, chiffres, `_`, jamais `__` ;
- sortie : UNIQUEMENT l'objet JSON, avec **l'exemple** ci-dessous.

**L'exemple JSON** (`_EXEMPLE_ARCHITECTURE`, une société fictive à deux activités publiées, un découpage estimé,
une extension annoncée, un bloc commun) est un point de contrat (#121) : un check le valide contre
`ArchitecteSortie`, puis — en-tête posé — contre `Architecture`, [P1]-[P5] et [S1]-[S9] sur une matière fictive
écrite dans le check. Il ne contient aucun nom d'émetteur réel.

## 5. Les contrôles de structure : `app/modele_entreprise/structure.py` (NOUVEAU, pur)

`valider_structure(arch, ref, matiere) -> list[str]` (signaux) ; lève `ArchitectureRefusee` avec TOUS les motifs
réunis (un par règle en défaut, code en tête), jamais au premier. Vocabulaire : **bloc de chiffre d'affaires** =
bloc qui retient une variable portant `somme_vers_ligne` ; **premier niveau** = bloc sans parent déclaré ET dont
le membre n'a aucun ancêtre (hiérarchie de la ventilation) parmi les membres des autres blocs publiés.

| Code | Règle | Le cas qu'elle arrête |
|---|---|---|
| [S1] | tout bloc publié cite un (axe, membre) présent dans la ventilation du titre (cellules ou membres nouveaux) ; ventilation `secteur_unique`/`sans_ventilation` → aucun bloc publié | un segment inventé, un membre mal recopié |
| [S2] | **couverture** : pour l'axe du premier niveau, la période de référence est la plus récente où TOUS les membres des blocs publiés de premier niveau ont une cellule `chiffre_affaires` ; chaque membre de premier niveau de cette période est un bloc, sinon un bloc estimé de premier niveau rattaché (`agrege`) à la ligne de `somme_vers_ligne` existe (le « reste ») ; même règle sous chaque bloc publié qui a des enfants-blocs. Aucune période commune → refus « découpage mixte ». Le reste sans bloc → refus avec membres, montants et part du total. Signal (pas refus) : les membres couverts par le « reste », avec montants | un découpage qui ne retombe pas sur le chiffre d'affaires publié ; deux découpages successifs mélangés |
| [S3] | au premier niveau, les blocs publiés sont sur UN seul axe ; aucun bloc publié n'a pour membre un descendant d'un autre bloc publié… sauf à être son enfant au sens de [S2] — deux blocs dont l'un contient l'autre ne sont jamais tous deux de premier niveau | un double compte (segment et marché ; Data Center et Compute côte à côte) |
| [S3b] | signal : la période de référence de [S2] n'est pas la plus récente publiée sur cet axe (le titre a redécoupé) — nommer le dépôt et les membres du découpage le plus récent | un classeur dessiné sur un découpage que l'émetteur a abandonné, sans que le comité le sache |
| [S4] | un bloc rattaché `agrege` vise une ligne du business plan de la famille ; un bloc rattaché `parent` ne vise jamais un bloc `commun` | un découpage estimé suspendu dans le vide, ou logé dans les frais de structure |
| [S5] | `secteur_unique`/`sans_ventilation` : tout bloc non commun est `estime` | une maille « publiée » qui n'existe pas |
| [S6] | toute pièce de bloc ∈ `matiere.pieces_citables` | une justification sur une pièce hors du dossier |
| [S7] | si un bloc de chiffre d'affaires existe, la ligne de `somme_vers_ligne` a une formule de passage dont l'ensemble des noms `bloc__<variable sommée>` est EXACTEMENT celui des blocs de chiffre d'affaires de premier niveau dont le statut n'est pas `extension_annoncee` | un bloc oublié dans l'agrégé, un enfant compté avec son parent |
| [S8] | aucun bloc `extension_annoncee` n'apparaît dans une formule de passage | une option comptée dans le central (09 §5) |
| [S9] | toute période de `cellules_attendues` ∈ périodes du classeur ; pour chaque nom `bloc__variable` d'une formule de passage dont la fiche a une période, des cellules attendues couvrent TOUTES les périodes projetées | une cellule lue par l'agrégé que personne n'est chargé d'écrire |

Le raccord CHIFFRÉ du détail estimé à son parent et de l'agrégé aux comptes est M5 (il faut des cellules) : M3 ne
contrôle que ce qui se décide sur la structure et la ventilation publiée (#68 : la structure, jamais le sens).

## 6. La signature au procès-verbal

### 6.1 Migration `backend/app/db/migrations/062_v3_signature_architecture.sql` (ÉCRITE, NON APPLIQUÉE)

Calquée sur 051 (décisions) et 061 (append-only) : table `architectures_modele_decisions` — `architecture_id`
(FK, **UNIQUE** : une décision par version), `action` (`signer`|`ecarter`), `auteur`, `motif` (non vides),
`signaux jsonb NOT NULL` (les écarts nommés que le comité avait sous les yeux, tableau de textes), `decide_le`.
Trigger d'immuabilité, `REVOKE UPDATE, DELETE` comme 061 ; en-tête « ce que ferait un vrai fonds ». Éprouvée par
`checks/negatif_062.sh` sur une copie (motif de `negatif_061.sh`).

### 6.2 Le geste et le service : `app/modele_entreprise/signature.py` (NOUVEAU)

Contrat `app/contracts/architecture_signature_schema.py` (calqué sur `signature_modele_schema.py` :
`DemandeDecisionArchitecture(auteur, motif)`, `VersionArchitecture`, `DecisionArchitecture`, `ArchitectureServie`).

- `servir_architecture(versions, pv, *, juger, interrupteur) -> ArchitectureServie` — PURE ; `juger(arch)` rejoue
  contrat + [P] + [S] contre la matière DU JOUR et rend `(tient, motif, signaux)` (#53/#77 : rien de stocké n'est
  un verdict). Sert : `en_attente` (la dernière proposée non décidée — une plus récente remplace l'ancienne,
  comme #98), `signee` (la dernière signée, avec son PV, servie « à revoir » + motif si elle ne tient plus :
  membre disparu, référentiel monté de version, nouveau découpage publié → [S3b] devient un signal neuf), et
  **`en_vigueur`** : interrupteur `true` → la signée si elle tient, sinon aucune (le motif dit pourquoi les
  relances M4 attendent) ; `false` → la dernière proposée qui tient, signée ou non.
- `signer(conn, *, ticker_id, version, demande, juger)` : la version doit être en attente ET tenir aujourd'hui,
  sinon `ActeRefuse` motivé ; le PV reçoit les signaux du jour. `ecarter(…)` : en attente, motif requis.
  Transaction explicite (#35).
- `lire_registre(conn, ticker_id)`.

### 6.3 Endpoints : `app/api/modele_entreprise_v2.py` (calqué sur `valorisation_v2.py`, monté comme lui)

`GET /v2/tickers/{t}/architecture` · `POST …/architecture/v/{n}/signer` · `POST …/architecture/v/{n}/ecarter` —
404 titre/version inconnus, 409 refus motivé, réponse = le service recalculé. Pas de POST « proposer » : c'est le
geste de l'agent (outil, §7).

## 7. Le paramètre du fonds et les outils

- `frameworks.yaml`, `parametres_du_fonds` : `horizon_de_projection` (valeur `5`, unité `exercices`,
  `decide_le: 2026-10-22`, `revoir_avant: 2027-10-22`, décision : « valeur par défaut posée par Opus le
  2026-10-22 en attendant l'arbitrage de l'utilisateur : cinq exercices explicites, puis la valeur terminale de
  l'atelier ») — même forme que `seuil_de_materialite`, sans montée de `schema_version`.
- `tools/architecte.sh TICKER [--matiere-seule] [--hors-porte] [--ecrire]` (+ `.py`), instance neuve de l'image
  (jamais dans `portfolio-backend`) :
  - `--matiere-seule` (GRATUIT) : la porte question par question, puis la matière EXACTE envoyée au modèle, sa
    taille en caractères et une estimation en jetons ;
  - défaut (à blanc, payant ~centimes) : un appel (+ un renvoi au plus), l'architecture rendue en français (blocs
    indentés par rattachement, statut, maille, motif, pièces ; variables par bloc ; formules ; cellules attendues
    par auteur), les signaux, le coût ; rien n'est écrit ; `--sortie FICHIER` garde le JSON ;
  - `--ecrire` : réservé à Opus après lecture d'un passage à blanc.
  - Bilan : `BILAN architecte <T> : porte <ouverte|fermée (n)> — <à blanc|proposée v<n>|refusée|porte fermée> —
    <b> blocs (<p> publiés / <e> estimés), <c> cellules attendues, <s> signaux, <x> $` — reconnaissable par
    `grep -E`, absence de bilan = échec (lanceur versionné, pas dans `/tmp`).
- `tools/montrer_architecture.sh TICKER` (gratuit) : le service (§6.2) rendu en texte.

## 8. Les gardes (une brique n'est faite que gardée ET éprouvée en négatif)

- `checks/check_architecte.py` (sans base), fixtures **copiées du réel** (`checks/fixtures/` : la structure de
  ventilation NVDA et RVMD relevée ce jour, un état de porte NVDA à partir des statuts réels des 12 questions) :
  1. porte : une ligne du tableau §3.1 = un cas ; NVDA réelle → ouverte ;
  2. périodes : NVDA (fins fin janvier → FY2024-FY2026 + 5 projetées), une fin au 1ᵉʳ janvier, une collision ;
  3. matière : contient raison sociale, CIK, date du jour, les adresses `[axe=… membre=…]` de la ventilation,
     les fiches de la famille SEULEMENT (aucune fiche bancaire pour une industrielle), le patron ; déterministe
     (deux rendus identiques) ; `secteur_unique` → la phrase du constat, aucune adresse ;
  4. exemple JSON (#121) : valide contre la sortie, le contrat, [P], [S] ;
  5. en-tête : un `ticker_id` dans la sortie du modèle est refusé ; la version suit le registre ;
  6. [S1]-[S9] : pour CHAQUE règle, un cas réel qui passe (une architecture NVDA plausible au découpage du 10-K,
     une au découpage du 10-Q, une RVMD tout estimée avec programmes) et un cas muté qui la fait refuser par son
     code ; [S2] découpage mixte (Data Center + Gaming + Edge Computing) refusé ; [S3b] signal sur le découpage
     du 10-K ;
  7. renvoi : un faux agent qui rend une sortie refusée puis une valide → acceptée, coût cumulé ; deux refus →
     `ArchitectureRefusee` avec les motifs ; porte fermée → aucun appel (le faux agent compte ses appels : 0) ;
  8. service : en attente / remplacée / signée / signée à revoir / interrupteur `false` ;
  9. réplicabilité : grep des tickers et noms de segments des fixtures dans le code et le prompt livrés —
     sur le texte **dépouillé** des commentaires et docstrings, puis asserté en positif sur un fichier qui en
     contient (`feedback_grep_interdit_lit_sa_propre_enonciation`).
- `checks/negatif_architecte.sh` : une mutation par règle ([S1]…[S9], chaque ligne de la porte, l'en-tête, le
  renvoi, l'interrupteur, la réplicabilité) ; chaque mutation nomme l'assert qui doit rougir et le vérifie
  (`feedback_test_negatif_trois_faux_verts`) ; motifs de mutation uniques dans le fichier muté.
- `checks/check_architecture_persist.py` (avec base, `checks/avec_base.sh`, ROLLBACK) : proposer → servir → signer
  → seconde décision refusée (409 côté service, UNIQUE côté base) ; écarter ; version remplacée non décidable ;
  `UPDATE`/`DELETE` refusés ; prouvé par les refus, jamais par une écriture laissée (append-only en prod).
- `checks/check_modele_entreprise.py` mis à jour (1.1.0, [R6], `motif`/`pieces`) ; `negatif_modele_entreprise.sh`
  gagne [R6] et la règle des pièces d'un bloc estimé.
- `run_all.sh` : la suite ENTIÈRE verte (contrat partagé modifié).
- `ARCHITECTURE.md` du module : M3 passe dans « Ce qui existe », table « Gardé par » à jour.

## 9. Comment le lot s'applique ailleurs (réplicabilité, 07)

- **NVDA** (activités publiées, redécoupage récent) : premier niveau sur l'axe `activites` ; [S2]/[S3b] obligent à
  choisir un découpage et le disent au comité ; un bloc « grands hébergeurs » estimé sous le calcul (découpage du
  10-K) ou publié (découpage du 10-Q).
- **RVMD** (`secteur_unique`, désormais `rentable`) : tous les blocs estimés ([S5]) ; le produit vendu rattaché
  à `chiffre_affaires`, les programmes `en_developpement` rattachés à `recherche_developpement` ou au produit ;
  le patron `rentable` ne prévoit pas de programme : l'architecte compose (09 §2), et les variables du catalogue
  `probabilite_de_succes` etc. lui sont proposées puisque la famille est industrielle.
- **Une financière** : la matière ne se construit pas (famille sans gabarit) — refus nommé, M2 bis d'abord.
- **Une société à un seul secteur et sans ventilation de marchés** : comme RVMD.

## 10. Étapes et ce que Sonnet rend à Opus

0. **Re-mesurer la ligne de base** (§0) — gratuit : `montrer_ventilation.sh NVDA RVMD`, compte des lignes
   d'`architectures_modele`, porte de RVMD lue dans `montrer_parcours.sh RVMD` (aucune hypothèse : si elle est
   fermée, nommer les questions et leur cause).
1. Référentiel 1.1.0, contrat 1.1.0, [R6] ; checks M1 verts.
2. Périodes, porte, rendu à identifiants, matière ; `architecte.sh --matiere-seule NVDA` et `RVMD` — **lire la
   matière en texte** et rapporter sa taille (caractères, jetons estimés) ; si > 60 000 jetons, s'arrêter et le dire.
3. Structure [S1]-[S9], agent, prompt, exemple ; checks et négatif.
4. Migration 062 + `negatif_062.sh` (sur une copie, jamais appliquée) ; signature, service, endpoints ; checks.
5. Suite entière : `bash backend/checks/run_all.sh` — rapporter le bilan (`grep -E`), pas `tail -1`.
6. **Acceptation à blanc** (payante, quelques centimes) : vérifier le crédit DeepInfra par un appel minimal, puis
   `architecte.sh NVDA` **deux fois** et `architecte.sh RVMD` **deux fois** (`--hors-porte` si sa porte est
   fermée), `--sortie` pour chaque passage. Rapporter les 4 BILAN, les 4 JSON, et pour chaque titre ce qui
   diffère entre les deux passages (blocs, axe, découpage choisi, rattachements) — un jugement qui bascule
   entre deux passages est un signal à nommer, pas à lisser (`feedback_jugement_modele_instable_entre_passages`).
7. Rendre : fichiers créés/modifiés ; écarts à cette spec et pourquoi ; sorties des négatifs (nombre de mutations
   rouges / total) ; ce qui n'a PAS été exécuté. **Ne pas committer.**

Opus vérifie ensuite PAR EXÉCUTION (négatifs rejoués, suite rejouée, lecture des quatre architectures contre la
matière), applique 062, déploie, puis — sur accord de l'utilisateur — `--ecrire` pour NVDA et la signature.
