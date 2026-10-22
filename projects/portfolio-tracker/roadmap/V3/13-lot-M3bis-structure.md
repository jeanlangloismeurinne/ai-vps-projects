---
id: spec-lot-m3bis
status: spec v2 2026-10-22 (Opus) — réécrite sur les causes profondes (principe fondateur n° 4) ; à exécuter par Sonnet
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M3 bis (suite de B4, plan `07-avant-comite.md`) : traiter les CAUSES des erreurs des
  4 architectures à blanc du 2026-10-22 (`mesures/2026-10-22/*.json`), pas leurs symptômes, AVANT tout
  `--ecrire`. Lot précédent : `12-lot-M3-architecte.md`. La v1 de cette spec (même jour) reconnaissait
  l'exemple (un libellé de marché, la seule période d'une variable) : remplacée, voir §0.2.
---

# Lot M3 bis — ce que le code sait, il le construit ; ce que le modèle ne voit pas, il ne peut pas le découper

> **Ce que ferait un vrai fonds** : l'analyste ne redessine pas la publication de l'émetteur — il la
> recopie telle quelle, choisit le découpage qui porte les moteurs économiques, et n'ajoute que ce qui est
> plus fin. Il sait que les segments et les marchés d'une entreprise sont deux façons de répartir le même
> chiffre d'affaires : ils se croisent, ils ne s'emboîtent pas. Ses formules sont homogènes (on n'ajoute
> pas un stock à un flux, ni des dollars à des millions de dollars). Avant de valoriser, il dresse
> l'inventaire de ce que l'entreprise PRÉPARE (programmes, prochaines générations, produits annoncés,
> acquisitions en cours) : c'est une part de la valeur, parfois la principale. Une acquisition non conclue
> n'est pas un programme : c'est un changement de périmètre possible, qui va aux scénarios.

## 0. Ligne de base et causes

### 0.1 Mesures (2026-10-22, Opus) — à RE-MESURER en premier (§8, étape 0)

| Fait | Mesure |
|---|---|
| Production | M3 déployé (`1d5dfbf`) ; `GET /v2/tickers/NVDA/architecture` → 200 `aucune_proposee` ; registres à 0 ligne |
| NVDA, 2 passages | premier niveau = segments ; les marchés de l'AUTRE axe (Data Center 193 737 M$, Gaming, Automotive…) déclarés `estime` et rangés sous un segment (Data Center sous Compute & Networking, 193 479 M$) ; passage 2 : Networking frère de Data Center (double compte) ; emboîtement différent d'un passage à l'autre ; acquisition annoncée (Hugging Face) en `en_developpement` |
| RVMD, 2 passages | tout le portefeuille en UN bloc « précliniques » ; `recherche_developpement = …__cout_restant_de_developpement` (stock sans période dans une ligne annuelle) |
| Matière NVDA (`--matiere-seule`) | les axes sont rendus en listes séparées (`— Axe « activites » —`, `— Axe « secteurs » —`) ; **rien ne dit qu'ils répartissent le même total ni qu'ils se croisent** |
| Matière RVMD | ~9 800 jetons ; **aucune molécule hors le produit approuvé** ; or le corpus en compte **44 pièces** (dont 9 dépôts EDGAR) — elles ne passent pas, parce que la matière ne montre que les réponses aux questions sources et qu'**aucune question n'a pour objet l'inventaire de ce que l'entreprise prépare** (vérifié pour toutes les familles : les fiches de programme citent `se_2`, `mo_4`, `me_4`, `me_5`, `qf_7`) |
| Questions sources | union des fiches de la FAMILLE (`questions_sources_applicables`, `referentiel.py:147`), pas de l'archétype : une `rentable` reçoit déjà les sources des fiches de programme |
| Grammaire des formules | arbre d'expression arithmétique (`formule_grammaire.py`) : typable |
| Porte RVMD | fermée (se_3 jamais instruite) |

### 0.2 Les causes (principe fondateur n° 4) — chaque correctif ci-dessous en traite une

| Cause | Symptômes | Autres formes d'entreprise où elle frapperait | Correctif |
|---|---|---|---|
| ① le modèle DÉCLARE ce que le code SAIT (maille publiée, emboîtement) et les contrôles lisent sa déclaration | marchés « estimés » sous un segment ; Networking frère de Data Center ; emboîtement instable | tout émetteur à deux axes (activités × pays, produits × clients) ; tout émetteur à sous-membres | §2 squelette construit par le code |
| ② la matière ne dit pas ce qu'est un axe | emboîtement inféré de la prose du 10-K | idem | §3 rendu |
| ③ aucune question n'inventorie ce que l'entreprise prépare | portefeuille regroupé ; programmes futurs absents de la valeur | laboratoire, technologie (générations suivantes), industriel (nouvelles usines), toute société qui annonce | §4 question `me_7` + manques du dossier |
| ④ les formules ne sont pas typées | stock dans une ligne annuelle | tout classeur : % dans des M$, unités × $/unité rangé en M$ (facteur 10⁶) | §5 dimensions |
| ⑤ le statut mêle maturité et origine | acquisition annoncée comptée comme programme (pondérée dans le central) | tout acquéreur, toute licence ou partenariat | §6 deux champs |

**Méthode de validation** (principe n° 4) : NVDA et RVMD seulement en réel ; les autres formes s'éprouvent par
des cas FICTIFS dans les contrôles (§7) — aucune recherche web. Une troisième entreprise réelle n'entre que si un
cas fictif révèle une ambiguïté qu'on ne peut pas trancher sans elle : c'est alors dit à l'utilisateur.

## 1. Périmètre et interdits

- **Livré** : squelettes publiés (code) ; rendu des axes ; question `me_7` (définition, table de la spec 03,
  rattachements du catalogue) ; contrat `architecture-1.2.0` ; référentiel `1.2.0` (unités, une fiche) ; contrôle
  des dimensions ; contrôles réécrits ; prompt et exemple ; checks, négatifs, cas fictifs.
- **Pas livré** : l'instruction de `me_7` pour NVDA et RVMD (payante, §8 étape 5, sur accord) ; M4, M5.
- **Ne change pas** : `schema_version` de `frameworks.yaml` (un ajout de question ne la monte pas, #92 — aucune
  réponse invalidée) ; la porte (sa règle ; ses ENTRÉES changent avec `me_7`, §4.3) ; `socle_comptes.yaml`.
- **Réplicabilité** : aucun ticker, nom de segment, marché, produit, membre ou molécule dans le code, le prompt,
  l'exemple, le référentiel ni l'énoncé de `me_7`. **Aucune règle par libellé** (la v1 en avait une : refusée, elle
  ne tient pas sur un émetteur qui nomme autrement).
- **Ne pas committer, ne pas déployer, ne rien écrire en production.**

## 2. Cause ① — le squelette publié est construit par le code (`app/modele_entreprise/squelette.py`, NOUVEAU, pur)

`squelettes_publies(ventilation_structure) -> list[Squelette]` : pour chaque axe et chaque **découpage** de cet
axe (ensemble distinct des membres de premier niveau du chiffre d'affaires, relevé période par période — même
logique que `ventilation._premier_niveau_de`, appelée, jamais recopiée), un `Squelette(id, axe, periodes,
depot_le_plus_recent, blocs)` où `blocs` = chaque membre de ce découpage ET ses descendants publiés sur le MÊME
axe, avec un id de bloc dérivé du nom local du membre (minuscules, `_`), leur rattachement (publié + parent dérivé
de la hiérarchie) et leurs montants de chiffre d'affaires par période. Id du squelette : `<axe>__<n>` stable (tri
par période la plus récente puis par membres). Sans ventilation : liste vide.

Le modèle **choisit** : `ArchitecteSortie.squelette: str` (un id de la liste) — et ne déclare plus aucun bloc
publié. Pour les blocs du squelette, il fournit seulement `blocs_publies: list[CompletionBlocPublie]` =
`{id, variables, motif}` (ensemble des id = EXACTEMENT celui du squelette, sinon refus [S1]). Le code assemble
l'architecture (blocs publiés du squelette + blocs déclarés). Le modèle ajoute librement : blocs estimés plus
fins, rattachés `parent` à une **feuille** du squelette (un membre sans descendant publié) ou `agrege` ; blocs
communs ; programmes ; extensions.

Contrôles réécrits (sur l'architecture ASSEMBLÉE) :
- [S1] l'id du squelette existe ; les id de `blocs_publies` = ceux du squelette.
- [S2] couverture : vraie par construction pour les blocs publiés ; reste un « reste » estimé si le squelette ne
  boucle pas sur le chiffre d'affaires du socle à sa période (écart > seuil de matérialité du référentiel).
- [S3] un bloc estimé n'est rattaché `parent` qu'à une FEUILLE du squelette ou à un autre bloc estimé (on ne
  découpe pas à côté de ce que l'émetteur publie déjà plus finement).
- [S3b] signal : le squelette choisi n'est pas le découpage le plus récent de son axe (nommer le dépôt).
- **[S10] les autres axes ne deviennent pas des blocs** : `ArchitecteSortie.autres_axes: list[{axe, usage}]` —
  pour CHAQUE axe de la ventilation non choisi, l'architecte écrit ce qu'il en fait (`usage`, min 20 : raccord des
  marges, contrôle de concentration…) ; un axe oublié → refus. (Troisième case qui force l'hypothèse à s'écrire,
  `feedback_garde_structure_pas_sens` ; aucune comparaison de libellés.)
- Signal pour le comité : chaque bloc estimé rattaché à une feuille publiée, avec son motif et ses pièces (c'est là
  qu'un découpage d'un autre axe pourrait se glisser sous un autre nom : le comité le lit, #68).

## 3. Cause ② — le rendu dit ce qu'est un axe (`ventilation.py`, rendu à identifiants seulement)

En tête de la section « Ventilation publiée » de la matière, une phrase fixe : « Chaque axe répartit le MÊME chiffre
d'affaires total de l'émetteur selon un critère différent. Deux axes se croisent : un membre d'un axe n'est jamais
contenu dans un membre d'un autre axe. L'emboîtement n'existe qu'à l'intérieur d'un axe (marqué ↳). » Puis, par
axe et par période annuelle, la somme de ses membres de premier niveau à côté du chiffre d'affaires du socle (« axe
X, FYn : Σ = a M$ ; chiffre d'affaires des comptes = b M$ »). Puis **la liste des squelettes** (§2) avec leur id,
leurs périodes, leur dépôt le plus récent, leurs blocs indentés. Le rendu de M2 (`montrer_ventilation.sh`) est
inchangé (défaut `avec_identifiants=False`).

## 4. Cause ③ — la question `me_7` : ce que l'entreprise prépare

### 4.1 La question (framework `modele_economique`, `frameworks.yaml` ; table §4.3 de la spec 03)

- **Énoncé** : « Que prépare l'entreprise pour ses années futures — programmes en développement, générations et
  produits annoncés, capacités en construction, acquisitions et accords en cours — à quel stade est chacun, quel
  est son prochain jalon, combien coûte-t-il et que pourrait-il rapporter ? »
- `chemin_indexation: modele_economique.programmes_futurs` ; `nature_attendue: mesure` (un inventaire de faits,
  chacun daté et sourcé ; le potentiel est un ingrédient de jugement) ; `plancher_tier: B+` (le tableau des
  programmes et la feuille de route figurent dans les dépôts et les présentations de l'émetteur ; le potentiel
  vient d'observateurs) — Sonnet aligne sur les valeurs admises et le dit si le contrôle des définitions refuse.
- `rouverte_par` : `changement_de_stade`, `reglementaire_favorable`, `reglementaire_defavorable`,
  `accord_commercial`, `perimetre`, `resultats`, `surprise_execution`.
- **Ingrédients** :
  - `inventaire_des_programmes` (essentiel, `description_annuelle`) : CHAQUE programme ou projet nommé — y compris
    les plus précoces (découverte, préclinique, prototype, génération suivante annoncée) — avec son origine
    (interne, acquisition, licence, partenariat), son dernier jalon franchi et sa date, son prochain jalon et sa
    date attendue, le marché ou l'indication visé ; ceux que l'émetteur ne nomme pas individuellement sont
    décrits comme plateforme, avec leur nombre ;
  - `depense_par_programme` (non essentiel, `chiffre_courant`, cadence annuelle) : la dépense de l'exercice
    affectée par programme quand l'émetteur la publie, sinon la R&D totale et la part non affectée ;
  - `potentiel_par_programme` (non essentiel, `jugement`) : ventes au pic, probabilité de succès au prochain
    jalon, sources et méthode ;
  - `operations_de_perimetre_en_cours` (non essentiel, `description_annuelle`) : acquisitions, cessions, accords
    annoncés et non conclus, avec leur condition et leur date.
- **Chiffres clés** : `nombre_de_programmes` (unités, à la date de l'analyse) ; `depense_de_developpement`
  (M$, dernier exercice).
- `variables_par_archetype` : `rentable` → « programmes et produits futurs qui s'ajouteront aux activités
  actuelles » ; `pre_revenus` → « portefeuille de programmes, chacun au stade et au jalon suivant » ;
  `financiere` → « nouveaux métiers, implantations et opérations de périmètre en cours ». **Jamais `sans_objet`** :
  une entreprise qui ne prépare rien le dit, et c'est une information pour la valorisation.

### 4.2 Les rattachements (référentiel `1.2.0`)

- `me_7` entre dans `questions_sources` de `probabilite_de_succes`, `annee_de_lancement`, `ventes_au_pic`,
  `cout_restant_de_developpement` et de la fiche neuve **`depense_de_developpement_du_bloc`** (« dépense de
  recherche et développement de l'exercice pour le programme du bloc — ce que le compte de résultat de l'année
  supporte », M$, `exercice`, `industrielle`, origines `piece`/`jugement`/`calcul`, sources `[me_7, qf_7]`,
  ajoutée au patron `pre_revenus`).
- `cout_restant_de_developpement` : définition complétée (« montant sans période ; la dépense de l'exercice est
  `depense_de_developpement_du_bloc` »).

### 4.3 Effet sur la porte (à dire au comité, pas à contourner)

`me_7` devient une question source de la famille industrielle : **la porte de NVDA se FERME** jusqu'à sa
première réponse instruite (comme RVMD, déjà fermée par se_3). Le BILAN de `architecte.sh --matiere-seule` le
montre. L'instruction de `me_7` est l'étape 5 (§8), payante, sur accord.

### 4.4 La matière et les manques

La matière rend la réponse de `me_7` comme les autres questions sources (verbatim entier). `ArchitecteSortie` et
`Architecture` gagnent `manques_du_dossier: list[{sujet (min 20), blocs: list[id], consequence (min 20)}]` : quand
le dossier ne permet pas de découper (programmes non nommés, dépense non affectée), l'architecte l'écrit au lieu de
regrouper en silence. Chaque manque est un signal servi au comité et écrit au PV à la signature.

## 5. Cause ④ — les formules sont typées (`app/modele_entreprise/dimensions.py`, NOUVEAU, pur)

- **Référentiel** : une table `unites:` (détenteur unique) — pour chaque unité du catalogue (`M$`, `$/unité`,
  `unités`, `%`, `%/an`, `(0-1)`, `année`, `années`), sa dimension (exposants de montant, quantité, temps) et son
  échelle (`M$` = 10⁶ $, `%` = 0,01). [R7] : toute fiche, toute variable propre a une unité de la table.
- **Une ligne du business plan** : dimension montant en M$ ; cadrage `flux` ou `instant` lu dans le gabarit de la
  famille (`socle_comptes.yaml`, `etats[].cadrage`, par le chargeur du socle — jamais une liste recopiée).
- **[S11]** `dimension_de(formule, fiches)` parcourt l'arbre de `formule_grammaire` : `+`/`−` exigent des termes
  de même dimension ET même échelle ; `×`/`÷` composent dimensions et échelles ; un nombre littéral est sans
  dimension. Période : dans un produit, un facteur `sans_periode` est neutre ; un terme ADDITIF de la formule
  d'une ligne `flux` doit contenir au moins un facteur `exercice` et aucun `instant` ; d'une ligne `instant`, au
  moins un `instant` et aucun `exercice`. Refus nommé avec la dimension trouvée et l'attendue.
- Ce qui est arrêté, sur n'importe quel émetteur : `…__cout_restant_de_developpement` dans une ligne annuelle ;
  `…__part_de_marche` dans le chiffre d'affaires ; `…__volume * …__prix_moyen` rangé en M$ sans `/ 1000000`.

## 6. Cause ⑤ — maturité et origine sont deux champs (contrat `architecture-1.2.0`)

- `Bloc.origine: Literal["interne", "acquisition", "licence", "partenariat"]` (requis, défaut absent : l'écrire).
- Règle [S12] : `origine == "acquisition"` ⟹ `statut ∈ {metier_actuel (conclue et consolidée),
  extension_annoncee (non conclue)}` — jamais `en_developpement`. `licence`/`partenariat` : tout statut.
- `Bloc.jalon` (requis si `statut == "en_developpement"`, interdit sinon) : `franchi` (min 10), `franchi_le`
  (date), `prochain` (min 10 : le jalon que mesure `probabilite_de_succes`), `attendu_vers` (optionnel). Signal :
  deux programmes au même prochain jalon à la même échéance (un portefeuille sous une seule probabilité).
- Signal pour le comité, chaque bloc hors métier actuel : « origine, statut, jalon » — le comité vérifie le sens.

## 7. Les gardes

- **Les 4 JSON du 2026-10-22 en fixtures** (`checks/fixtures/architecte/2026-10-22/`) : rejoués sous 1.2.0, chacun
  refusé par la règle de SA cause (NVDA 1/2 : forme 1.1.0 sans squelette → [S1] ; la conversion la plus proche —
  segments choisis, marchés en estimés sous une feuille — refusée par [S10] (axe `activites` sans usage) ; RVMD 1/2 :
  [S11] et contrat (jalon, origine)).
- **Cas fictifs** (aucun nom réel, écrits dans le check, structure de ventilation complète) — ce sont eux qui
  éprouvent la généralité :
  1. société découpée d'abord par **pays** (axe géographique seul) ;
  2. **conglomérat** à trois métiers, dont un à sous-membres publiés, et un axe produits qui croise les métiers ;
  3. société **à un seul métier** sans programme : `me_7` répond « rien de préparé », l'architecture passe ;
  4. **laboratoire rentable** à six programmes dont deux précoces non nommés (plateforme) et une licence ;
  5. **acquéreur** : une acquisition conclue (métier actuel), une annoncée (extension), une tentative de la
     classer en développement refusée par [S12] ;
  6. **redécoupage** : un axe qui change de découpage en cours d'année → deux squelettes, [S3b] sur l'ancien.
  Pour chacun : la matière (rendu des axes, squelettes) et une architecture qui passe, puis une mutation par règle.
- `dimensions.py` : table de cas (somme de M$ et de %, produit volume × prix, facteur sans période, ligne instant).
- `check_frameworks_definitions` : `me_7` conforme ; table de la spec 03 à jour (la garde §7 confronte prose et YAML).
- `negatif_architecte.sh` : une mutation par règle et par validateur neufs, chaque mutation nomme l'assert qui
  doit rougir ; motifs de mutation uniques.
- **Réplicabilité** : grep, sur le texte dépouillé des commentaires, des noms des fixtures réelles dans le code, le
  prompt, l'exemple, le référentiel et l'énoncé de `me_7` → 0, asserté en positif sur un fichier qui en contient.
- `run_all.sh` : suite ENTIÈRE.

## 8. Étapes et ce que Sonnet rend à Opus

0. Re-mesurer §0.1 (gratuit) ; rejouer les 4 JSON contre `valider_structure` actuel → « passent » (les trous existent).
1. Référentiel 1.2.0 (unités, fiche, rattachements), `me_7` + spec 03 ; checks M1 et frameworks verts.
2. Squelettes, rendu des axes, contrat 1.2.0, contrôles réécrits et neufs, dimensions ; prompt (§2-§6 en termes
   d'analyste) et exemple fictif ; checks, cas fictifs, négatifs.
3. Suite entière ; bilan par `grep -E`.
4. `architecte.sh NVDA --matiere-seule` et `RVMD --matiere-seule` : lire en texte le rendu des axes et des
   squelettes ; rapporter la taille ; la porte (attendu : fermée par `me_7`, et se_3 pour RVMD).
5. **Pas exécuté par Sonnet** — sur accord de l'utilisateur, par Opus : instruire `me_7` pour NVDA et RVMD
   (`executer_chaine.sh … --questions=me_7`, payant, ~1 h chacun), lire les réponses contre leurs pièces, puis
   l'acceptation à blanc (`architecte.sh` deux fois par titre, `--hors-porte` pour RVMD si se_3 la ferme encore).
6. Rendre : fichiers ; écarts et pourquoi ; négatifs (rouges / total) ; ce qui n'a PAS été exécuté. Ne pas committer.
