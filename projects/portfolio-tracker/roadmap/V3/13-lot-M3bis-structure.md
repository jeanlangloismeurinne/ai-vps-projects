---
id: spec-lot-m3bis
status: spec v2.1 2026-10-22 (Opus) — réécrite sur les causes profondes (principe fondateur n° 4), cause ① corrigée pour respecter l'arbitrage du 2026-10-21 (architecte libre de composer) ; à exécuter par Sonnet
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot M3 bis (suite de B4, plan `07-avant-comite.md`) : traiter les CAUSES des erreurs des
  4 architectures à blanc du 2026-10-22 (`mesures/2026-10-22/*.json`), pas leurs symptômes, AVANT tout
  `--ecrire`. Lot précédent : `12-lot-M3-architecte.md`. La v1 de cette spec (même jour) reconnaissait
  l'exemple (un libellé de marché, la seule période d'une variable) : remplacée, voir §0.2.
---

# Lot M3 bis — le modèle choisit, le code établit les faits ; ce que le modèle ne voit pas, il ne peut pas le découper

> **Ce que ferait un vrai fonds** : l'analyste compose librement son classeur — il choisit le découpage qui
> porte les moteurs économiques, s'arrête à la maille qui lui sert, regroupe ce qui est immatériel, découpe
> plus fin là où il a une thèse — mais il ne travestit pas un fait : un chiffre publié reste publié, et il
> garde le second découpage de l'émetteur À CÔTÉ, pour raccorder (les marges par segment, par exemple). Il sait que les segments et les marchés d'une entreprise sont deux façons de répartir le même
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
| ① le contrat n'offre AUCUNE place au second découpage publié, et il laisse le modèle AFFIRMER deux faits que le code connaît (« ce bloc est estimé », « ce membre en contient un autre ») que les contrôles croient sur parole. Le CHOIX de composition n'est pas en cause : il reste libre (arbitrage 09 §1.1, §2 : « une suggestion, pas une cage ») | voulant les segments au premier niveau ET le détail des marchés, le modèle a forcé l'autre axe dans l'arbre (son motif le dit : « sous-détail publié dans l'axe activites ») en marquant « estimé » des membres publiés ; Networking frère de Data Center | tout émetteur à deux axes (activités × pays, produits × clients) ; tout émetteur à sous-membres | §2 : une place pour les autres axes ; maille et emboîtement entre blocs publiés établis par le code |
| ② la matière ne dit pas ce qu'est un axe | emboîtement inféré de la prose du 10-K | idem | §3 rendu |
| ③ aucune question n'inventorie ce que l'entreprise prépare | portefeuille regroupé ; programmes futurs absents de la valeur | laboratoire, technologie (générations suivantes), industriel (nouvelles usines), toute société qui annonce | §4 question `me_7` + manques du dossier |
| ④ les formules ne sont pas typées | stock dans une ligne annuelle | tout classeur : % dans des M$, unités × $/unité rangé en M$ (facteur 10⁶) | §5 dimensions |
| ⑤ le statut mêle maturité et origine | acquisition annoncée comptée comme programme (pondérée dans le central) | tout acquéreur, toute licence ou partenariat | §6 deux champs |

**Méthode de validation** (principe n° 4) : NVDA et RVMD seulement en réel ; les autres formes s'éprouvent par
des cas FICTIFS dans les contrôles (§7) — aucune recherche web. Une troisième entreprise réelle n'entre que si un
cas fictif révèle une ambiguïté qu'on ne peut pas trancher sans elle : c'est alors dit à l'utilisateur.

## 1. Périmètre et interdits

- **Livré** : maille et emboîtement des blocs publiés établis par le code, regroupements, place des autres axes ; rendu des axes ; question `me_7` (définition, table de la spec 03,
  rattachements du catalogue) ; contrat `architecture-1.2.0` ; référentiel `1.2.0` (unités, une fiche) ; contrôle
  des dimensions ; contrôles réécrits ; prompt et exemple ; checks, négatifs, cas fictifs.
- **Pas livré** : l'instruction de `me_7` pour NVDA et RVMD (payante, §8 étape 5, sur accord) ; M4, M5.
- **Ne change pas** : `schema_version` de `frameworks.yaml` (un ajout de question ne la monte pas, #92 — aucune
  réponse invalidée) ; la porte (sa règle ; ses ENTRÉES changent avec `me_7`, §4.3) ; `socle_comptes.yaml`.
- **Réplicabilité** : aucun ticker, nom de segment, marché, produit, membre ou molécule dans le code, le prompt,
  l'exemple, le référentiel ni l'énoncé de `me_7`. **Aucune règle par libellé** (la v1 en avait une : refusée, elle
  ne tient pas sur un émetteur qui nomme autrement).
- **Ne pas committer, ne pas déployer, ne rien écrire en production.**

## 2. Cause ① — le modèle compose, le code établit les faits (`app/modele_entreprise/faits_publies.py`, NOUVEAU, pur)

**Ce qui reste au modèle (arbitrage 09 §1.1, §2 — inchangé)** : l'axe du premier niveau, la maille à laquelle il
s'arrête (un membre publié peut rester un seul bloc sans ses enfants), les **regroupements** (plusieurs membres
publiés d'un même axe et d'un même niveau en un bloc — ex. de forme : les membres sous le seuil de matérialité
réunis), les découpages plus fins que la publication (estimés, sous n'importe quel bloc publié, y compris
autrement que l'émetteur ne le fait), les programmes, extensions et blocs communs, les variables.

**Ce que le contrat change** :
- `RattachementPublie` admet `membres: list[str]` (un ou plusieurs qnames du MÊME axe, mêmes parents) au lieu
  d'un seul `membre` : le regroupement est un bloc publié, pas un estimé.
- **La maille n'est plus déclarée** : `Bloc.maille` disparaît de la sortie du modèle ; le code la pose
  (`publie` si le bloc cite une adresse, `estime` sinon) en même temps que l'en-tête (§4.3 de la spec M3).
- **L'emboîtement entre blocs publiés n'est plus déclaré** : un bloc publié n'a jamais de `RattachementParent` ;
  son parent (le bloc publié dont un membre est l'ancêtre de ses membres, sur le même axe) est DÉRIVÉ de la
  hiérarchie de la ventilation. Un bloc estimé, lui, se rattache librement (`parent` vers tout bloc, `agrege`).
- **Une place pour les autres axes** : `ArchitecteSortie.autres_axes: list[{axe, usage}]` — pour CHAQUE axe de la
  ventilation qui ne porte aucun bloc, l'architecte écrit ce qu'il en fait (`usage`, min 20 : raccord des marges,
  contrôle de concentration, information pour un bloc…). C'est la case qui manquait : le second découpage a
  désormais un endroit où aller qui n'est pas l'arbre.

**Contrôles** (sur l'architecture assemblée) :
- [S1] chaque adresse citée existe ; les membres d'un regroupement sont du même axe et ont le même parent.
- [S2] couverture : inchangée dans son principe (membres de premier niveau non couverts → un « reste » estimé),
  appliquée aux membres des blocs publiés, regroupements compris.
- [S3] un seul axe pour les blocs publiés de premier niveau ; un membre n'appartient qu'à un bloc ; un bloc publié
  et un bloc publié descendant sont parent et enfant (dérivé), jamais frères.
- [S3b] inchangé (signal de redécoupage).
- **[S10]** tout axe de la ventilation sans bloc a son `usage` ; un axe oublié → refus.
- Signal pour le comité : chaque bloc estimé rattaché à un bloc publié, avec son motif et ses pièces (un découpage
  d'un autre axe pourrait s'y glisser sous un autre nom : le comité le lit, #68 ; le raccord chiffré des
  estimés à leur parent est M5).

**Ce qui n'est PAS fait, et pourquoi** : aucun squelette imposé, aucun ensemble de blocs obligatoire, aucune
comparaison de libellés. La v2 de cette spec imposait un squelette complet : refusé, c'était la cage que
l'arbitrage du 2026-10-21 a écartée.

## 3. Cause ② — le rendu dit ce qu'est un axe (`ventilation.py`, rendu à identifiants seulement)

En tête de la section « Ventilation publiée » de la matière, une phrase fixe : « Chaque axe répartit le MÊME chiffre
d'affaires total de l'émetteur selon un critère différent. Deux axes se croisent : un membre d'un axe n'est jamais
contenu dans un membre d'un autre axe. L'emboîtement n'existe qu'à l'intérieur d'un axe (marqué ↳). » Puis, par
axe et par période annuelle, la somme de ses membres de premier niveau à côté du chiffre d'affaires du socle (« axe
X, FYn : Σ = a M$ ; chiffre d'affaires des comptes = b M$ »). Puis, par axe, **les découpages successifs** (ensembles de
membres de premier niveau, avec leurs périodes et le dépôt le plus récent) — une information pour choisir, pas un
gabarit à reprendre. Le rendu de M2 (`montrer_ventilation.sh`) est
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
  refusé par la règle de SA cause (NVDA 1/2 convertis au plus proche en 1.2.0 — segments choisis, marchés en
  estimés sous un segment, aucun `autres_axes` — refusés par [S10] (axe `activites` sans usage) ; la même architecture
  avec l'axe `activites` déclaré en raccord et les marchés RETIRÉS de l'arbre passe ; NVDA 2 (Networking et Data
  Center frères, si cités par adresse) refusé par [S3] ; RVMD 1/2 :
  [S11] et contrat (jalon, origine)).
- **Cas fictifs** (aucun nom réel, écrits dans le check, structure de ventilation complète) — ce sont eux qui
  éprouvent la généralité :
  1. société découpée d'abord par **pays** (axe géographique seul) ;
  2. **conglomérat** à trois métiers, dont un à sous-membres publiés, et un axe produits qui croise les métiers ;
  3. société **à un seul métier** sans programme : `me_7` répond « rien de préparé », l'architecture passe ;
  4. **laboratoire rentable** à six programmes dont deux précoces non nommés (plateforme) et une licence ;
  5. **acquéreur** : une acquisition conclue (métier actuel), une annoncée (extension), une tentative de la
     classer en développement refusée par [S12] ;
  6. **redécoupage** : un axe qui change de découpage en cours d'année → deux découpages, [S3b] sur l'ancien.
  Pour chacun : la matière (rendu des axes, découpages) et **deux** architectures qui passent, de compositions
  différentes (ex. de forme : maille fine / maille grossière avec regroupement), pour prouver que les contrôles
  n'imposent pas une composition ; puis une mutation par règle.
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
2. Faits publiés (maille, emboîtement dérivés ; regroupements ; autres axes), rendu des axes, contrat 1.2.0, contrôles réécrits et neufs, dimensions ; prompt (§2-§6 en termes
   d'analyste) et exemple fictif ; checks, cas fictifs, négatifs.
3. Suite entière ; bilan par `grep -E`.
4. `architecte.sh NVDA --matiere-seule` et `RVMD --matiere-seule` : lire en texte le rendu des axes et des
   découpages ; rapporter la taille ; la porte (attendu : fermée par `me_7`, et se_3 pour RVMD).
5. **Pas exécuté par Sonnet** — sur accord de l'utilisateur, par Opus : instruire `me_7` pour NVDA et RVMD
   (`executer_chaine.sh … --questions=me_7`, payant, ~1 h chacun), lire les réponses contre leurs pièces, puis
   l'acceptation à blanc (`architecte.sh` deux fois par titre, `--hors-porte` pour RVMD si se_3 la ferme encore).
6. Rendre : fichiers ; écarts et pourquoi ; négatifs (rouges / total) ; ce qui n'a PAS été exécuté. Ne pas committer.
