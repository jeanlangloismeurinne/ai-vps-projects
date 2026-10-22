---
id: spec-lot-p1-perimetre
status: spec v1.1 2026-10-22 (Opus) — arbitrages §7 rendus par l'utilisateur le même jour ; à exécuter par Sonnet
created: 2026-10-22
project: portfolio-tracker
role: >
  Spec d'EXÉCUTION du lot P1 (plan `07-avant-comite.md`, tâche B4b) : sortir des modules de l'architecte et
  de la ventilation TOUTE la logique des changements de découpage et de périmètre, et la confier à un
  détenteur unique, testé par son propre catalogue de cas. Demande de l'utilisateur du 2026-10-22 : NVDA a
  cumulé deux difficultés (premier test de l'architecte ; redécoupage de ses marchés d'une année sur
  l'autre) qu'il faut pouvoir distinguer, parce que d'autres bugs de périmètre viendront.
---

# Lot P1 — la continuité des découpages : un seul détenteur des changements de périmètre

> **Ce que ferait un vrai fonds** : deux métiers distincts. Le **teneur des séries** (équipe données, ou
> l'analyste quand il tient ses historiques) suit chaque émetteur dans le temps : quand celui-ci change son
> découpage (nouveaux marchés, segments fusionnés) ou son périmètre (activité cédée, retraitée), il établit
> la **table de passage** de l'ancien au nouveau découpage, la **vérifie sur une période publiée dans les
> deux**, reconstitue l'historique dans le nouveau découpage quand le passage boucle, et **marque la
> rupture** quand il ne boucle pas. L'**analyste** construit son modèle SUR ces séries ; il ne refait pas
> la série en construisant le modèle. Quand un modèle déraille, on sait aussitôt si la faute est dans la
> série ou dans le modèle — et une erreur de série se corrige une fois, pour tous les modèles qui la lisent.

## 0. Pourquoi, et la ligne de base

### 0.1 Mesure (2026-10-22, Opus, `montrer_ventilation.sh NVDA`, gratuit) — à RE-MESURER (§6, étape 0)

| Fait | Mesure |
|---|---|
| Dépôts lus | le dernier 10-K (2026-02-25) et le dernier 10-Q (2026-08-26) — **seulement ces deux** |
| Ancien découpage (10-K, FY2024-FY2026) | 5 marchés : Data Center (↳ Compute, Networking), Gaming, Professional Visualization, Automotive, OEM and Other ; boucle au total chaque année |
| Nouveau découpage (10-Q, semestres 2026 ET 2025) | Data Center (↳ Hyperscale, AI Clouds/Industrial/Enterprise) + Edge Computing ; **le semestre 2025 est publié deux fois** : dans l'ancien découpage (10-Q d'août 2025, NON lu) et retraité dans le nouveau (comparatif du 10-Q d'août 2026) |
| Hypothèse à vérifier en étape 0 | sur le semestre 2025, Edge Computing (10 597 M$) = Gaming + ProViz + Automotive + OEM tels que publiés en 2025, et Data Center (80 208 M$) inchangé — si oui, l'historique annuel du nouveau découpage se reconstitue sur trois exercices |
| Douze mois glissants Data Center (277 798 M$) | exercice 2026 (ancien découpage) + semestre 2026 − semestre 2025 (nouveau découpage) : **deux découpages mêlés sans vérification** ; juste seulement si le contenu de Data Center n'a pas changé — rien ne le vérifie |
| Si l'architecte choisit le nouveau découpage | [S2] prend pour référence un CUMUL SEMESTRIEL ; Edge Computing n'a aucun exercice : le choix est aujourd'hui « ancien découpage, trois ans d'histoire » OU « nouveau découpage, un semestre » |
| Ordre des périodes | deux copies (`structure._cle_tri_periode`, `ventilation._cle_periode_rendu`, la seconde le reconnaît dans sa docstring), triant sur la PREMIÈRE date de l'identifiant — pour un cumul, sa date de DÉBUT |

### 0.2 La cause (principe fondateur n° 4)

**La continuité d'une série n'a pas de détenteur.** Six endroits en décident chacun pour leur besoin :

| # | Où | Ce qu'il décide du périmètre |
|---|---|---|
| 1 | `knowledge/ventilation.py` `relever` | membre « nouveau » = absent du 10-K ; cumuls ; parent rattrapé ; douze mois exclus pour un membre nouveau ; statut `decoupage_change` ; « exercice de référence » |
| 2 | `knowledge/ventilation.py` `rendre_ventilation` | « découpages successifs » recalculés au rendu ; motif sur la ligne Σ |
| 3 | `modele_entreprise/structure.py` `_s2_s3b` | période de référence de l'architecture ; signal [S3b] « le titre a redécoupé » |
| 4 | `modele_entreprise/faits_publies.py` (via `parent_de`) | emboîtement FUSIONNÉ entre dépôts, le premier dépôt gagne (`setdefault`) — une hiérarchie qui change d'un dépôt à l'autre est aplatie |
| 5 | consigne de l'architecte (`architecte.py`) | « choisis-en UN, dis LEQUEL et POURQUOI » — on demande au modèle un jugement que le code n'a pas préparé |
| 6 | `knowledge/appariement_feed.py` `douze_mois_glissants` (partagé avec le socle) | aucune vérification que les trois termes sont du même découpage ou du même périmètre (une activité cédée retraitée au 10-Q dans le comparatif, pas dans l'exercice clos) |

Trois conséquences : (a) un échec de l'architecte sur NVDA ne se rattache ni à l'architecte ni au
périmètre ; (b) un futur bug de périmètre se corrigera dans un des six endroits et les cinq autres
re-divergeront ; (c) les contrôles de l'architecte s'éprouvent sur une ventilation qui porte déjà un
redécoupage : ils testent les deux sujets à la fois.

**Test de la cause** — la même absence frapperait : un conglomérat qui fusionne deux divisions ; une société
qui passe d'un découpage par produits à un découpage par clients ; un groupe qui cède une activité et
retraite ses comparatifs ; un émetteur qui garde un nom de segment mais y transfère une ligne de produits
(même nom, contenu changé — le cas le plus dangereux, invisible à toute règle par nom).

## 1. Périmètre et interdits

- **Livré** : le module pur `app/knowledge/perimetre.py` (la chronique) ; la lecture du **dépôt jumeau**
  (celui qui a publié la période de recouvrement dans l'ancien découpage) ; les six consommateurs rebranchés
  sur la chronique, sans règle de périmètre restante ; un catalogue de cas fictifs propre au périmètre, son
  check, son négatif ; des fixtures STABLES pour les contrôles de l'architecte.
- **Pas livré** : la croissance hors acquisitions (module ad hoc après le premier comité, arbitrage Q2 ; le
  SIGNAL d'acquisition significative, lui, est livré, §4 bis) ; aucune dépense de modèle ; aucune
  écriture en production ; pas de déploiement.
- **Ne change pas** : la règle de la porte ; les contrats de l'architecture (1.2.0) ; la liberté de
  composition de l'architecte (arbitrage 09 §1.1) — il peut toujours choisir un découpage ancien, le
  signal [S3b] le dit au comité.
- **Interdits** : aucune règle par libellé ni par nom de membre (un renommage se prouve par les montants,
  jamais par la ressemblance des noms) ; aucun ticker ; aucun seuil calé sur NVDA (la tolérance de bouclage
  est celle de `socle_comptes.tolerance_bouclage`, détenteur unique).

## 2. Le détenteur : `app/knowledge/perimetre.py` (NOUVEAU, pur)

Entrée : les cellules relevées de TOUS les dépôts lus (y compris le jumeau), chaque cellule gardant son
dépôt ; la hiérarchie **par dépôt** (plus fusionnée) ; pour le socle, les lectures déposées par
(concept, période). Sortie : une `Chronique`, **calculée à la lecture, jamais persistée** (une valeur
stockée qui dépend d'un ingrédient non stocké sert le verdict d'avant le correctif).

### 2.1 Les régimes

Par axe, un **régime** = un ensemble de membres de premier niveau avec sa hiérarchie, les périodes qu'il
couvre et les dépôts qui le publient. Une période publiée par deux dépôts dans deux régimes est une
**période de recouvrement** : la seule où un passage peut se prouver. Le **régime de référence** est celui
du dépôt le plus récent (la publication la plus récente fait foi, comme #133) ; sa **période annuelle de
référence** est le dernier exercice clos qu'il couvre, directement ou par passage (§2.3).

### 2.2 Les transitions (entre deux régimes consécutifs d'un axe), typées par les MONTANTS

| Type | Reconnu par | Effet sur la série |
|---|---|---|
| `detail_ajoute` | des enfants nouveaux sous un membre dont la valeur est égale dans les deux régimes | continuité au niveau du parent ; les enfants n'ont d'histoire que là où ils sont publiés |
| `renommage` | un membre nouveau égal, sur le recouvrement, à un seul ancien membre disparu | continuité ; la série porte le nouveau nom |
| `regroupement` / `scission` | un membre nouveau égal à la somme d'une PARTITION d'anciens membres (ou l'inverse) | historique reconstitué par **passage** (somme des anciens membres), marqué comme tel |
| `meme_nom_contenu_change` | même identifiant de membre, valeurs différentes sur le recouvrement | traité comme une `rupture` (§2.3 bis) : jamais de continuité par le nom |
| `rupture` | aucun recouvrement, passage qui ne boucle pas, ou passage AMBIGU (deux partitions bouclent) | historique **réparti par hypothèse** (§2.3 bis), motif nommé ; jamais présenté comme publié ni comme passage vérifié |
| `axe_apparu` / `axe_disparu` | un axe sans cellule dans l'un des régimes | information |

Recherche du passage : partition des anciens membres en sous-ensembles dont chaque somme égale un nouveau
membre, à la tolérance de bouclage ; borne explicite sur le nombre de membres (au-delà : `rupture`, motif
« trop de membres pour établir le passage », jamais un calcul sans fin — un blocage est un état muet).

### 2.3 Les séries comparables

Par (axe, ligne, membre du régime de référence, période) : la valeur et son **origine** — `publie` (lue
dans un dépôt du régime de référence), `passage` (somme d'anciens membres, avec leur liste et leur dépôt)
ou `hypothese` (répartition déclarée, §2.3 bis). **Aucune cellule de l'historique du régime de
référence n'est vide** pour une période où le total du compte de résultat est connu. C'est ce que lisent le rendu, l'architecte et, plus tard, le
classeur (M5) : **un historique, un découpage, chaque chiffre avec sa provenance**.

### 2.3 bis La répartition par hypothèse (arbitrage Q1)

Quand aucun passage vérifié n'existe, l'historique est quand même rendu dans le découpage le plus récent,
par une hypothèse **déclarée et marquée** :
- le **groupe concerné** = la plus petite partie de l'axe qui se raccorde (anciens membres touchés par la
  transition ↔ nouveaux membres qui les remplacent), lue sur le recouvrement ; sans recouvrement, l'axe
  entier ;
- le **montant du groupe** est conservé à chaque période ancienne (somme des anciens membres du groupe) :
  seule sa répartition entre les nouveaux membres est une hypothèse ;
- la **méthode v1, unique** : au prorata des parts des nouveaux membres dans le groupe à la PREMIÈRE
  période publiée dans le nouveau découpage (son identifiant est écrit dans la cellule) ;
- chaque cellule porte `origine: hypothese`, la méthode, la période des parts, et les anciens montants ;
  le rendu le dit en clair (« reconstitué par hypothèse : répartition au prorata de … ») ; le comité le lit.
  Une méthode plus fine (choisie par l'analyste) est un raffinement ultérieur, débrayable vers celle-ci.

### 2.3 ter L'invariant de l'agrégat (remarque de l'utilisateur)

La structure d'un compte de résultat ne change pas d'une année à l'autre : **au niveau agrégé il n'y a pas
de rupture**. Pour chaque axe à raccord et chaque période, la somme des membres de premier niveau de la
série reconstituée (publiés + passages + hypothèses) égale la ligne du socle, à la tolérance de bouclage —
sinon c'est une ERREUR du module, refus nommé, jamais une rupture. Côté socle, un retraitement change des
valeurs, jamais la structure : il est suivi (§2.4), il n'est pas une rupture.

### 2.4 Les douze mois glissants

Pour un membre, les trois termes (exercice clos, cumul en cours, cumul comparable) doivent appartenir au
même régime ou être raccordés par un passage vérifié ; sinon refus NOMMÉ (« douze mois non établis : les
termes relèvent de deux découpages sans passage vérifié »). Même règle pour le socle : si la même
(concept, période) porte deux valeurs selon le dépôt (un **retraitement**), les trois termes sont pris dans
la version retraitée quand elle existe pour chacun, sinon refus nommé — jamais un mélange silencieux.
`douze_mois_glissants` reçoit ce prédicat du détenteur ; elle ne le recopie pas.

### 2.5 L'ordre des périodes

Une seule clef de tri, sur la date de FIN d'une période (`perimetre.ordre_des_periodes`) ; les deux copies
actuelles sont supprimées.

## 3. Les consommateurs rebranchés (aucune règle de périmètre ne leur reste)

| Consommateur | Avant | Après |
|---|---|---|
| `ventilation.relever` | décide « nouveau », « découpage changé », « référence » | relève les cellules par dépôt ; le statut du raccord lit la chronique |
| `rendre_ventilation` | recalcule les découpages | rend la chronique en phrases d'analyste : régimes, transitions, passages, ruptures ; puis la série comparable dans le régime de référence |
| `structure._s2_s3b` | choisit sa période | lit la période annuelle de référence et le régime de référence ; [S3b] = « l'architecture suit un régime autre que celui de référence » |
| `faits_publies` | hiérarchie fusionnée | hiérarchie DU régime suivi par le bloc |
| consigne de l'architecte | « choisis-en un » | « le découpage de référence est le plus récent ; son historique est reconstitué quand le passage est vérifié (marqué « passage ») ; une rupture est dite, ne la comble pas » |
| `douze_mois_glissants` | sans contrôle de régime | prédicat du détenteur (§2.4) |

## 4. Séparer les épreuves

- **Catalogue du périmètre** (`checks/fixtures/perimetre/`, cas FICTIFS, aucun nom réel) : un cas par type de
  transition (§2.2), plus : retraitement d'une activité cédée au socle ; deux transitions successives sur le
  même axe ; un redécoupage et un renommage dans le même dépôt ; un passage ambigu ; un recouvrement absent
  (axe entier réparti par hypothèse) ; une scission (un ancien → trois nouveaux) répartie par hypothèse, dont
  le montant du groupe est conservé ; une mutation qui casse l'invariant de l'agrégat (§2.3 ter) doit rougir.
  Chaque cas déclare la chronique attendue (régimes, transitions, séries et leur origine, douze mois).
  `check_perimetre.py` ; `negatif_perimetre.sh` (une mutation par règle, chaque mutation nomme l'assert qui
  doit rougir, motifs uniques).
- **Un cas réel figé** : les dépôts NVDA (10-K, 10-Q récent, 10-Q jumeau) copiés du réel en fixture —
  attendu, si l'étape 0 le confirme : `detail_ajoute` sous Data Center, `regroupement` vers Edge Computing,
  trois exercices reconstitués.
- **Les contrôles de l'architecte** s'éprouvent sur des ventilations SANS transition ; un seul cas
  d'intégration par type de transition traverse l'architecte, pour prouver qu'il LIT la chronique.
- **Garde de détention** : sur le code dépouillé des commentaires, aucun module hors `perimetre.py` ne
  calcule un ensemble de membres de premier niveau par période ni ne compare deux dépôts — asserté en
  positif sur `perimetre.py`.
- **Règle durable** (convention à écrire à la livraison) : tout bug de périmètre futur se reproduit d'abord
  par un cas fictif du catalogue, puis se corrige dans `perimetre.py` — jamais dans un consommateur.

## 4 bis. Le signal d'acquisition significative (arbitrage Q2)

Le teneur des séries **signale** au comité une acquisition significative dans la période historique ou les
douze derniers mois (« croissance qui inclut une acquisition : <date>, <montant>, part estimée du chiffre
d'affaires ») — sans calculer la croissance hors acquisitions, qui sera un **module ad hoc construit après
le premier comité**. Source : les faits XBRL de regroupement d'entreprises du dépôt (contrepartie
transférée, chiffre d'affaires pro forma ou acquis quand publié) — gratuits, sans modèle ; Sonnet mesure à
l'étape 0 lesquels l'émetteur dépose. Seuil : paramètre du fonds au référentiel de ventilation
(`seuil_acquisition_significative`, défaut 5 % du chiffre d'affaires de l'exercice, ou, faute de chiffre
d'affaires acquis publié, 5 % de la contrepartie rapportée à la capitalisation — à dire au comité). Cas
fictifs : acquisition sous le seuil (rien), au-dessus (signal), sans chiffre d'affaires publié (signal par la
contrepartie).

## 5. Coût

Gratuit : un dépôt de plus lu sur data.sec.gov par émetteur (le jumeau) ; aucun modèle. La structure
persistée de la ventilation gagne le dépôt jumeau : l'empreinte change, une version neuve se publie au
prochain `--publier` (sans migration : JSONB, chronique calculée à la lecture).

## 6. Étapes et ce que Sonnet rend à Opus

0. **Mesurer** (gratuit) : trouver et lire le 10-Q jumeau de NVDA (août 2025) ; vérifier l'hypothèse §0.1
   (Edge = somme des quatre, Data Center inchangé) ; pour le socle de NVDA, RVMD, MSFT, compter les
   (concept, période) qui portent deux valeurs selon le dépôt ; rejouer la suite entière (ligne de base).
   Si l'hypothèse tombe : s'arrêter et rendre la mesure à Opus.
1. `perimetre.py` + catalogue + check + négatif.
2. Lecture du jumeau dans `ventilation_feed` (le dépôt qui publie la période comparable du dernier 10-Q).
3. Rebranchement des six consommateurs ; suppression des copies ; consigne de l'architecte.
4. Suite ENTIÈRE ; bilan par `grep -E` ; `montrer_ventilation.sh NVDA RVMD JPM` et
   `architecte.sh NVDA --matiere-seule` lus en texte (taille de la matière avant/après).
5. Rendre : fichiers ; écarts et pourquoi ; négatifs (rouges / total) ; ce qui n'a pas été exécuté. Ne pas
   committer.

## 7. Arbitrages (rendus par l'utilisateur le 2026-10-22)

- **Q1 → historique dans le découpage le plus récent, « quitte à prendre des hypothèses pour découper
  l'historique »** ; au niveau agrégé, pas de rupture (la structure d'un compte de résultat ne change
  pas) → §2.3 bis, §2.3 ter.
- **Q2 → signaler une acquisition significative ; la croissance hors acquisitions sera un module ad hoc
  construit plus tard** → §4 bis.

Texte des questions telles que posées :

- **Q1 — l'historique après un redécoupage.** Recommandé : le comité voit l'historique dans le découpage le
  plus récent, reconstitué quand le passage est vérifié sur une période publiée dans les deux, chaque
  chiffre reconstitué marqué ; sinon la série commence à la rupture. Autres : montrer les deux découpages
  côte à côte sans passage ; ou ne garder que le nouveau découpage (histoire courte).
- **Q2 — acquisitions et cessions.** Recommandé pour ce lot : le retraitement publié par l'émetteur est
  suivi (§2.4) et une acquisition significative est SIGNALÉE au comité (« croissance qui inclut une
  acquisition »), la croissance hors acquisitions étant reportée après le premier comité (elle exige de lire
  le chiffre d'affaires acquis dans le texte, donc un modèle). Autre : la calculer dès maintenant.

## 8. Addendum du 2026-10-22 (Opus) — le cœur restant (B4c-2), conception arrêtée

Deux passages de Sonnet ont livré le détenteur (`perimetre.py`), la lecture du jumeau, la délégation du
premier niveau et de l'ordre des périodes, le signal d'acquisition et la préférence « version retraitée » des
douze mois ; ils ont buté sur le rebranchement. **Cause mesurée par Sonnet** : l'identité d'une cellule
relevée est `(axe, ligne, membre, période)`, SANS le dépôt — deux dépôts qui publient la même période à des
valeurs différentes (retraitement, même nom au contenu changé) sont fusionnés en silence (« le premier dépôt
gagne »). Tant que cette fusion existe, aucune chronique fidèle ne peut être construite.

**Preuve que la fusion coûte déjà** : la lecture du jumeau (`c551003`) a fait prendre aux douze mois par pays
de NVDA le semestre 2025 d'ORIGINE au lieu du semestre RETRAITÉ — Σ pays = 323 559 M$ pour un total de
302 970 M$ (reste −20 589 M$) — et la suite est restée verte. Corrigé par la préférence « version la plus
récemment déposée » (2ᵉ passage, `appariement_feed._choisir_terme`) ; le trou de contrôle est fermé par la
garde (iv) ci-dessous.

**Conception (à exécuter telle quelle)** :
1. **Relevé brut, sans fusion** : `relever` produit les cellules PAR DÉPÔT (identité `(axe, ligne, membre,
   période, accn)`) ; la structure persistée les garde toutes (le champ `accn` existe déjà) ; la hiérarchie est
   persistée PAR DÉPÔT. L'empreinte change : une version neuve se publiera, sans migration.
2. **Vue servie = chronique, calculée à la lecture** : `perimetre.vue_servie(structure, socle)` rend, par axe à
   raccord, les séries du régime de référence (publié / passage / hypothèse), les régimes, les transitions,
   les membres nouveaux (membres du régime de référence absents du précédent) et les raccords calculés SUR
   LA VUE. C'est le SEUL point d'entrée des lecteurs : `rendre_ventilation`, `matiere` (structure servie à
   l'architecte), `structure._s2_s3b`, `faits_publies`. Aucun lecteur ne lit plus les cellules brutes, sauf
   l'audit (rendu « cellules relevées », facultatif).
3. **Retirer de `relever`** : `membres_nouveaux`, `decoupage_change`, `_reference`, le rattrapage du parent au
   cumul, l'exclusion des douze mois des membres nouveaux — tout passe dans `vue_servie`. Les douze mois d'un
   membre se calculent sur la série de la vue (termes du même régime, ou passage), avec le prédicat existant.
4. **Consigne de l'architecte** : réécrite DANS LE MÊME LOT que le rendu, jamais avant (un prompt qui annonce
   un historique que le rendu ne montre pas ment au modèle — le 2ᵉ passage l'avait fait, Opus l'a retiré).
5. **Gardes** : (i) [P32] étendue : aucune décision de régime hors de `perimetre.py` ; (ii) rendu NVDA réel
   figé : Edge Computing FY2024-FY2026 = Σ des quatre anciens marchés, marqué « reconstitué par passage » ;
   (iii) [S2] sur un bloc publié du nouveau découpage trouve ses exercices ; (iv) **invariant de l'agrégat sur
   la vue servie** : pour chaque axe à raccord et chaque période qui a un total au socle, Σ premier niveau =
   total à la tolérance, sinon refus NOMMÉ — la mutation « prendre le terme d'origine au lieu du retraité »
   doit rougir sur le cas réel NVDA ; (v) `check_ventilation_publiee` : chaque attente changée justifiée une à
   une, aucune affaiblie.
6. **Découpage d'exécution** (pour tenir dans un passage) : tranche A = points 1 + 2 + garde (iv), rendu de
   M2 inchangé en texte (la vue reproduit d'abord le comportement actuel quand il n'y a qu'un régime) ;
   tranche B = 3 + rendu de la chronique + [S2]/[S3b] + `faits_publies` + consigne + gardes (i)-(iii).

**État au soir du 2026-10-22** : tranche A livrée (points 1, garde (iv), `vue_servie` pure) ; le branchement des lecteurs passe en tranche B, qui doit aussi traiter l'axe PAYS de NVDA (redécoupé : Singapour replié dans les autres pays, mesuré sur le jumeau) et nommer les périodes que la garde (iv) ne juge pas (incomplètes) au lieu de les taire.
