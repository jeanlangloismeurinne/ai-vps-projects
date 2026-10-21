---
id: spec-lot-m2
status: spec-2026-10-21 (Opus) — à exécuter par Sonnet
created: 2026-10-21
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M2 (B2 du plan `07-avant-comite.md`) : la ventilation que l'émetteur publie
  lui-même (secteurs, activités, géographie, concentration des clients), relevée par le code dans le
  dépôt, raccordée aux comptes reconstitués, publiée comme une pièce du dossier. La spec métier est
  `09-modele-entreprise.md` (§3 ①, §4, §9) ; la mesure de départ `mesures/2026-10-21/mesure_m0_ventilation.md`.
---

# Lot M2 — la ventilation publiée, relevée et raccordée aux comptes

> **Ce que ferait un vrai fonds** : l'analyste recopie la note sectorielle du **dernier rapport annuel** —
> chiffres retraités au découpage en vigueur, pas un empilement de découpages successifs —, la complète des
> douze derniers mois quand un rapport trimestriel est sorti depuis, vérifie qu'elle **retombe sur le total
> publié**, et écrit à côté ce qui ne retombe pas (les charges que la direction n'affecte à aucun secteur).
> Il ne réinvente aucun secteur : il note aussi qu'une société n'en publie qu'un. C'est la matière que
> l'architecte (M3) recevra pour dessiner ses blocs, et la maille « publiée » d'un bloc (09 §4).

## 0. Décision technique prise par mesure (2026-10-21, Opus) — elle remplace la méthode de M0

M0 lisait les pages rendues `R#.htm` (présentation humaine : en-têtes, mise à l'échelle, colonnes) et
signalait lui-même que la voie robuste est l'**instance XBRL** du dépôt. Remesuré ce jour, gratuitement :

| Pièce du dépôt | Ce qu'elle donne | Mesure |
|---|---|---|
| `{prefixe}_htm.xml` (instance) | chaque fait = concept, période (début/fin ou instant), membres explicites par axe, unité, valeur — exacts, sans mise en forme | NVDA 10-K 1,7 Mo : `Revenues` × `srt:ProductOrServiceAxis` = Data Center 193 737 / Compute 162 361 / Networking 31 376 / Gaming 16 042 / ProViz 3 191 / Auto 2 349 / OEM 619 (M$, identiques à M0) ; segments sous DEUX axes (`srt:ConsolidationItemsAxis = us-gaap:OperatingSegmentsMember` × `us-gaap:StatementBusinessSegmentsAxis`) : C&N 193 479 / Graphics 22 459, résultat d'exploitation 130 141 / 9 156. JPM 14,9 Mo lu en 0,24 s / 55 Mo de mémoire |
| `{prefixe}_lab.xml` (étiquettes) | le libellé de chaque membre (`terseLabel` puis `verboseLabel` puis `label` sans « [Member] ») | `nvda:ComputeMember` → « Compute » ; `country:US` → « United States » |
| `{prefixe}_def.xml` (définitions) | la hiérarchie des membres (arcs `domain-member`) | `srt:ProductsAndServicesDomain → nvda:DataCenterMember → {ComputeMember, NetworkingMember}` |

Donc : **instance + étiquettes + définitions**, trouvées par l'index du dépôt
(`https://www.sec.gov/Archives/edgar/data/{cik}/{accn_sans_tirets}/index.json`, suffixes `_htm.xml`,
`_lab.xml`, `_def.xml`) ; ni `FilingSummary.xml` ni `R#.htm`. Décision technique, sans effet métier : pas
d'arbitrage à demander. La note 09 §9 « Ventilation publiée (B2) » est à corriger dans ce sens (§9 ci-dessous).

## 1. Périmètre et interdits

- **Livré** : un référentiel (donnée), un lecteur XBRL pur, une fonction pure de relevé et de raccord, une
  publication en pièce du dossier (idempotente, versionnée), un outil gratuit de lecture, des fixtures
  copiées du réel, des checks et leurs négatifs.
- **Pas livré** : la jointure de la pièce aux chapitres (aucun framework ne la reçoit d'office en M2 —
  changer `frameworks.yaml` changerait `schema_version` et invaliderait des réponses, #64 ; son lecteur est
  l'architecte, M3) ; le gabarit bancaire (M2 bis) ; l'architecte et sa porte (M3) ; l'agrégé (M5).
- **Aucun appel modèle, aucune migration** (la pièce va dans `knowledge_entries`, comme le socle). Aucun
  prompt ne change. `socle_comptes.yaml` n'est **pas** modifié (sa version clefe les encadrés).
- **Réplicabilité** : aucun ticker, CIK, nom de segment ou de membre propre à un émetteur dans le code ni
  dans le référentiel. Le référentiel ne nomme que des axes et membres des taxonomies **standard**
  (`us-gaap:`, `srt:`). Les fixtures, elles, sont copiées du réel et nomment NVDA/RVMD/JPM.
- **Ne pas committer, ne pas déployer, ne rien publier en production** : Opus vérifie d'abord.

## 2. Le référentiel : `backend/app/knowledge/ventilation_publiee.yaml` (NOUVEAU, `version: 1.0.0`)

En-tête de commentaire dans le style de `socle_comptes.yaml` (pourquoi une donnée ; détenteur unique ;
contrat qui le valide ; checks qui le gardent). Contenu :

```yaml
version: 1.0.0

# Les AXES de ventilation que le fonds relève. Un axe hors de cette liste n'est jamais lu.
axes:
  - id: secteurs
    libelle: Secteurs opérationnels (information sectorielle publiée)
    axe: us-gaap:StatementBusinessSegmentsAxis
    raccord: total                 # la somme des membres de premier niveau se rapproche du total publié
  - id: activites
    libelle: Activités et marchés (chiffre d'affaires ventilé)
    axe: srt:ProductOrServiceAxis
    raccord: total
  - id: geographie
    libelle: Zones géographiques
    axe: srt:StatementGeographicalAxis
    raccord: total
  - id: clients
    libelle: Concentration des clients
    axe: srt:MajorCustomersAxis
    raccord: aucun                 # des parts rapportées à des bases différentes : jamais sommées
    concepts: [us-gaap:ConcentrationRiskPercentage1]
    qualificateurs:                # axes ADMIS en plus de l'axe principal ; leur membre devient la « base »
      - us-gaap:ConcentrationRiskByBenchmarkAxis
      - us-gaap:ConcentrationRiskByTypeAxis
      - us-gaap:StatementBusinessSegmentsAxis

# Un qualificateur NEUTRE ne change pas le sens d'un fait : il est ignoré pour le classement.
qualificateurs_neutres:
  - {axe: srt:ConsolidationItemsAxis, membre: us-gaap:OperatingSegmentsMember}

# Un axe dont les seuls membres sont ceux-ci n'est pas une ventilation : la société n'a qu'un secteur.
membres_secteur_unique: [us-gaap:OperatingSegmentsMember]
```

**Les concepts relevés** sur les axes à `raccord: total` ne sont PAS listés ici : ce sont les concepts des
**recettes à un seul concept** des lignes du gabarit de la famille du titre (`socle_comptes.yaml`, lu par
`charger_gabarit`) — détenteur unique (#46) ; un fait sur un axe retenu dont le concept n'appartient à
aucune recette va dans `non_rattaches` (visible, compté, jamais perdu ni deviné).
**La famille** se lit au référentiel du classeur (`modele_entreprise.yaml`, `famille_par_archetype`, via
`app/modele_entreprise/referentiel.py`) à partir de l'archétype en vigueur du titre (`read_archetype`,
`agents/v2/framework_persist.py`). Famille dont le gabarit est `null` (bancaire en 1.0.0) → refus nommé
à la publication (§5), la fonction pure reste exécutable.

Contrat pydantic strict `VentilationReferentiel` dans `backend/app/contracts/ventilation_schema.py`
(NOUVEAU) : ids uniques, axes uniques, `raccord ∈ {total, aucun}`, `concepts` exigé si `raccord: aucun`,
préfixe `us-gaap:`/`srt:` exigé sur tout axe et membre (c'est la garde de réplicabilité au chargement).

## 3. Le lecteur XBRL : `backend/app/knowledge/ventilation_xbrl.py` (NOUVEAU, pur)

- `lire_instance(xml: bytes) -> list[FaitDimensionne]` : `FaitDimensionne(concept, debut, fin, instant,
  membres: tuple[(axe, membre)…], unite, valeur: float, decimales)` ; `concept` et membres au format
  `prefixe:Nom` (le préfixe résolu par l'espace de noms de l'instance, pas recopié du texte) ; ignore les
  faits sans `contextRef`, les `typedMember` (axe typé : pas une ventilation), les valeurs non numériques ;
  `xsi:nil` → ignoré, jamais 0 (#47).
- `lire_etiquettes(xml: bytes) -> dict[membre, libelle]` : `terseLabel` > `verboseLabel` > `label` ôté de
  « [Member] » / « [Domain] ».
- `lire_hierarchie(xml: bytes) -> dict[membre, parent]` : arcs `…/domain-member` de toutes les
  `definitionLink` ; un membre à deux parents différents → le premier rencontré par rôle trié (déterministe)
  et le conflit est rendu dans une liste `conflits` (jamais tu).
- `ElementTree` de la bibliothèque standard (n'interprète pas les entités externes) ; aucun réseau ici.

## 4. Le relevé et le raccord : `backend/app/knowledge/ventilation.py` (NOUVEAU, pur)

`relever(depots, gabarit, referentiel, socle: dict) -> Ventilation`, où `depots` est la liste des dépôts lus
(chacun : `accn, form, filed, faits, etiquettes, hierarchie`) — le **dernier 10-K**, et le **dernier 10-Q
s'il est postérieur** à ce 10-K ; `socle` est la structure en vigueur (`structure_du_socle`).

**4.1 Classement d'un fait.** Après retrait des qualificateurs neutres, un fait appartient à l'axe A si
son contexte porte exactement un membre de A et aucun autre axe (sauf, pour `clients`, les
`qualificateurs` déclarés). Un fait qui porte un axe de plus (ex. JPM, provision du segment CCB × portefeuille
Apple Card) est un **sous-détail** : compté dans `sous_details`, pas relevé (le bloc plus fin que la
publication est l'affaire de l'architecte, 09 §4).

**4.2 Les périodes** — celles du socle, jamais une règle recopiée :
- **exercices** : les durées annuelles du dernier 10-K dont la fin est un id `FY{fin}` du socle (en pratique
  trois : le 10-K retraite ses comparatifs au découpage en vigueur — c'est le chiffre qu'un fonds retient ;
  les exercices plus anciens, publiés à un autre découpage, ne sont pas relevés en 1.0.0) ;
- **douze mois glissants** : si le socle a une période `TTM{fin}` et que le 10-Q porte le cumul en cours et
  le cumul comparable du même membre, la valeur est l'identité de `douze_mois_glissants`
  (`appariement_feed`, détenteur unique) appliquée aux points du membre mis à la forme qu'elle lit
  (`start, end, val, accn, form, filed`) — refus NOMMÉ si un terme manque, jamais de repli sur l'exercice ;
- **instants** (actifs par secteur) : aux ids `B{fin}` du socle ;
- un membre présent au 10-Q mais absent du 10-K → `membres_nouveaux` (un découpage annoncé : information
  pour l'architecte), sans douze mois.

**4.3 Les cellules.** Une cellule par (axe × ligne du gabarit × membre × période) : valeur déposée, concept,
accession, libellé du membre, parent (hiérarchie). Un membre absent pour une période = pas de cellule,
jamais un zéro (#25, #47). Concepts `clients` : valeur en proportion, avec la base (membres des
qualificateurs) ; aucune somme.

**4.4 Le raccord** (axes `raccord: total`), pour chaque (axe × ligne × période) :
- **premier niveau** = membres présents dont le parent est le domaine ou n'est pas présent ;
- `total` = la cellule du socle `{ligne}|{periode}` (valeur `v`) — lue, jamais recalculée ici ;
- `reste = total − Σ premier niveau` ; statut **`boucle`** si `|reste| ≤ _tolerance(total)` (tolérance du
  socle, exposée par un accès public — pas recopiée), sinon **`non_ventile`** avec le montant signé du reste
  (le cas normal du résultat d'exploitation : charges non affectées) ; **`sans_total`** si le socle n'a pas
  la cellule (nommé) ;
- **emboîtement** : pour chaque parent présent qui a des enfants présents, `Σ enfants` vs parent → `boucle`
  ou **`ecart`** (montant publié, jamais absorbé — l'écart dit qu'il manque un membre ou que la hiérarchie
  est mal lue).

**4.5 Les issues** de `relever` : `Ventilation(statut, axes, cellules, raccords, membres_nouveaux,
non_rattaches, sous_details, conflits, refus)` avec `statut` ∈ `ventilee` (au moins un axe relevé avec ≥ 2
membres de premier niveau), `secteur_unique` (aucun axe, et un axe `secteurs` réduit aux
`membres_secteur_unique` ou absent), `sans_ventilation` (aucun fait sur aucun axe retenu). Les trois sont
des **constats**, pas des échecs.

`structure_de_ventilation(v) -> dict` (le `content_structured`, `metric = "ventilation_publiee"`,
`poste_kind = "stock"`, `version_referentiel`, `version_gabarit`, `depots` [accn, form, filed]) ;
`empreinte(structure)` (versions + accessions + cellules triées) ; `rendre_ventilation(structure, *,
raison_sociale) -> str` : texte français, un tableau par axe (membres en ligne, périodes en colonne,
emboîtement indenté), la ligne « non ventilé (par différence) » quand elle existe, la concentration des
clients en phrases (« le premier client direct représente 22 % du chiffre d'affaires du secteur Compute &
Networking, exercice clos le 2026-01-25 »), tamponné `mesure` comme le socle (#110).

## 5. La publication : `backend/app/knowledge/ventilation_feed.py` (NOUVEAU)

Calquée sur `socle_feed.py` (mêmes trois issues, même idempotence) :
- `assurer_ventilation(conn, ticker_id) -> VentilationPubliee` : identité (`identite_de_l_emetteur`),
  famille (§2) ; famille sans gabarit → `VentilationIndisponible` « famille bancaire : gabarit à écrire
  (M2 bis) — aucune ventilation publiée, un zéro trompeur ne doit pas entrer au dossier » ; socle en vigueur
  (`assurer_socle`) ; dépôts : réutiliser le lecteur `submissions` existant d'`edgar_feed` /
  `material_events` (ne pas en écrire un second — greper avant), puis l'index du dépôt et les trois
  fichiers, en série, User-Agent `_UA` d'`edgar_facts`, ≥ 0,25 s entre appels, délai borné par requête
  (#73 : un blocage réseau devient un échec nommé) ;
- `publier_ventilation(conn, ticker_id, *, depots, …)` : la moitié base, éprouvable sans réseau.
  `ventilee` → `store_knowledge` (`entry_type="fact_financial"`, `source_type="edgar_official"`, tags
  `["financials", "edgar", "ventilation_publiee"]`, `datation=constatee(date_du_fait=fin la plus récente,
  date_du_document=filed du dépôt le plus récent)`, `source_url=filing_url(cik, accn le plus récent)`,
  `supersedes_entry_id` de la pièce courante, transaction explicite #35) ; même empreinte → `a_jour`, rien
  écrit ; `secteur_unique` / `sans_ventilation` → statut rendu, **rien écrit** (le constat est recalculable,
  #77 ; M3 décidera comment l'architecte le reçoit).
- Aucun appelant en production en M2 (pas de jointure, pas de matin) : seul l'outil l'appelle.

## 6. L'outil : `backend/tools/montrer_ventilation.sh TICKER…` (+ `.py`)

Gratuit. Instance neuve de l'image comme `montrer_socle.sh`. Par défaut **à blanc** : lit EDGAR, relève,
imprime le rendu et un bilan d'une ligne par titre de la forme
`BILAN ventilation <TICKER> : <statut> — <n> axes, <n> cellules, raccords <b> bouclés / <n> non ventilés /
<e> écarts / <s> sans total` (bilan reconnaissable par `grep -E`, absence de bilan = échec). `--publier`
écrit (réservé à Opus après vérification).

## 7. Les gardes (une brique n'est faite que gardée ET éprouvée en négatif)

**Fixtures copiées du réel** : `backend/tools/extraire_fixture_ventilation.py` (versionné) télécharge un
dépôt et en garde les éléments XML d'origine utiles — contextes et unités référencés, faits portant un axe
du référentiel, faits sans dimension des mêmes concepts, étiquettes et arcs des membres gardés — en
`checks/fixtures/ventilation/{TICKER}_{accn}_{inst|lab|def}.xml.gz`. Dépôts : NVDA 10-K
`0001045810-26-000021` et 10-Q `0001045810-26-000075` ; RVMD 10-K `0001193125-26-071563` ; JPM 10-K
`0001628280-26-008131`. Le socle de chaque titre : celui de `tools/fixtures_socle.py` s'il existe, sinon
généré par le même outil. Taille visée < 300 Ko par fichier compressé.

**`checks/check_ventilation_publiee.py`** — assertions nommées, chiffres relevés au réel :
- [V1] NVDA FY2026-01-25 `secteurs` × `chiffre_affaires` : deux membres 193 479 / 22 459 M$, `boucle` ;
- [V2] NVDA `activites` : cinq membres de premier niveau (somme 215 938), `boucle` ; Data Center = Compute
  162 361 + Networking 31 376, emboîtement `boucle` ; Compute et Networking ne sont PAS au premier niveau ;
- [V3] NVDA `geographie` : quatre membres, `boucle` ; libellé « United States » ;
- [V4] NVDA `secteurs` × `resultat_exploitation` : 130 141 / 9 156, statut `non_ventile`, reste = cellule du
  socle − 139 297 (valeur exacte relevée par Sonnet et écrite dans l'assertion) ;
- [V5] NVDA douze mois glissants au 2026-07-26 pour un membre de `activites`, égal à l'identité calculée à
  la main depuis les trois points de la fixture ;
- [V6] NVDA `clients` : part du premier client 22 % (FY2026), base = secteur C&N ; aucun raccord ;
- [V7] RVMD : statut `secteur_unique`, aucune cellule, rien de publiable ;
- [V8] JPM : la fonction pure relève les quatre métiers (CCB, CIB, AWM, Corporate) en `non_rattaches` ou
  cellules selon le gabarit industriel, et `publier_ventilation` refuse (famille bancaire) — refus nommé ;
- [V9] aucun zéro fabriqué : un membre retiré d'une période dans une copie de la fixture → pas de cellule,
  raccord `non_ventile` du montant retiré ;
- [V10] sous-détail : JPM provision CCB × Apple Card comptée dans `sous_details`, absente des cellules ;
- [V11] idempotence de l'empreinte (deux relevés identiques → même empreinte ; une cellule changée → autre) ;
- [V12] réplicabilité : grep des tickers, CIK et noms de membres propres (`nvda:`, `jpm:`, `rvmd:`, Data
  Center, Compute…) sur le code et le YAML livrés **dépouillés de leurs commentaires et docstrings**
  (mémoire « un grep d'interdit lit sa propre énonciation ») → 0 ; et une assertion POSITIVE que le grep
  trouve bien `nvda:` dans la fixture (sinon le grep est aveugle).

**`checks/check_ventilation_persist.py`** (base, ROLLBACK, comme `check_socle_persist.py`) : publication →
une pièce courante ; republication identique → `a_jour`, aucune ligne ; fixture modifiée → nouvelle
version, l'ancienne `superseded_by` ; `secteur_unique` → aucune ligne ; bancaire → refus, aucune ligne.

**`checks/negatif_ventilation_publiee.sh`** (harnais unique `_negatif.sh`, #65 — même usage que `negatif_socle_comptes.sh`) — chaque
mutation doit faire rougir l'assertion NOMMÉE (exiger son nom dans la sortie) :
- qualificateur neutre non retiré → [V1] ; hiérarchie ignorée (tout au premier niveau) → [V2] ;
- tolérance mise à zéro OU multipliée par 1 000 → [V2]/[V4] (deux mutations, les deux sens) ;
- `xsi:nil` lu comme 0 / membre absent compté zéro → [V9] ; sous-détail relevé → [V10] ;
- un 10-K antérieur choisi au lieu du dernier → [V1] ; refus bancaire retiré → [V8] ;
- `douze_mois_glissants` remplacé par l'exercice → [V5] ; grep de réplicabilité sans dépouillement → [V12].
Motif de chaque mutation **unique** dans le fichier muté (le harnais le vérifie). `negatif_ventilation_persist.sh`
sur les trois issues de la publication.

Rejouer `bash backend/checks/run_all.sh` **en entier** ; ajouter les nouveaux checks à son inventaire.
Mettre à jour `app/knowledge/ARCHITECTURE.md` (tableau des modules et tableau des gardes).

## 8. Comment le lot s'applique ailleurs (exigence de réplicabilité, 07)

- **RVMD** : `secteur_unique` — rien n'est publié ; l'architecte (M3) le saura, et tous les blocs de RVMD
  seront `estime`, rattachés `agrege` à la recherche et à la trésorerie totales (09 §4). Aucun code propre.
- **Financière** : la fonction relève déjà les métiers de JPM ; la publication attend le gabarit bancaire
  (M2 bis). Quand ce gabarit existera, ses recettes (produit net, coût du risque, fonds propres moyens…)
  rattacheront les faits par secteur **sans une ligne de code** : le rattachement passe par les recettes du
  gabarit de la famille.
- **Un émetteur qui change de découpage** : seul le dernier 10-K fait foi ; un membre neuf au 10-Q est
  signalé, pas extrapolé.
- **Un émetteur étranger (20-F, IFRS)** : axes `ifrs-full:` absents du référentiel 1.0.0 → `sans_ventilation`,
  constat nommé. L'ajout est une ligne de référentiel le jour où un 20-F entre dans le jalon.

## 9. Ce que Sonnet rend à Opus

1. Les fichiers créés/modifiés, sans commit.
2. La sortie de `montrer_ventilation.sh NVDA RVMD JPM` (à blanc) **en texte**, bilans compris.
3. La sortie des deux `negatif_*.sh` (comptes rouges/verts, nom de l'assertion rougie par mutation) et le
   bilan de `run_all.sh` (nombre de checks, d'assertions).
4. Tout écart à cette spec, avec sa raison (un écart non signalé est un défaut).
5. Corriger en passant la note de `09-modele-entreprise.md` §9 « Ventilation publiée (B2) » : instance +
   étiquettes + définitions, plus `FilingSummary`/`R#`.
