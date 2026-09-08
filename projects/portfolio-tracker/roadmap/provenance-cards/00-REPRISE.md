---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-08
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2 (cartes de provenance). Contrat FIGÉ · couche 2
  DÉPLOYÉE · boucle V2 complète (décider → surveiller → sortir → apprendre, lots 7-9) · écrans
  UX-1/2/3 livrés · chaîne exercée sur NVDA, MSFT et RVMD. Le chantier courant est la **révision du
  modèle de fiabilité** (autorité contre actualité) ; RVMD reste le banc d'essai des modes de panne
  du socle (16 défauts F1→F16). État au 2026-09-08 : **1 815 assertions / 0 échec / 22 scripts**,
  migrations appliquées jusqu'à **035**, prochaine 036. Roadmap active :
  `roadmap/02-spec-autorite-vs-actualite.md` — **capacités 0, 1, 2, 3 et 4 CLOSES**, prochain jalon
  **capacité 5**, RÉÉCRITE le 2026-09-08 (les chiffres ne se discutent pas, les textes s'arbitrent
  et l'arbitrage se trace) — sa rédaction initiale a été réfutée par sa propre mesure.
---

# Prompt de reprise — portfolio-tracker V2 (cartes de provenance)

> **Ce fichier ne s'empile pas.** Le récit des sessions vit dans `00-REPRISE-ARCHIVE.md` (copie
> conforme, rien de résumé), les règles durables dans le `CLAUDE.md` du projet (conventions
> numérotées), les enseignements d'outillage transverses dans `../../../CHANTIER_OUTILLAGE_DEV.md`.
> Ici : **l'état atteint, ce qui reste, et les pièges à ne pas re-découvrir.** Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5.

## 🎯 Roadmap active

**`roadmap/02-spec-autorite-vs-actualite.md`** (statut `figée`, ouverte le 2026-09-05) — révision du
modèle de fiabilité : **autorité contre actualité**. Six capacités dans un ordre imposé.
**Capacités 0, 1, 2, 3 et 4 CLOSES** : table de profils co-écrite (#50, 193 assertions) · axe
`nature` dérivé (migration 034, #51, 52 assertions) · registre nominatif des sources (#52, 78
assertions) · axe `actualité` calculé à la lecture (#53, 66 assertions, le 2026-09-07) · **porte de
complétude à trois états** (#54, 131 assertions, le 2026-09-08).
**Prochain jalon : capacité 5**, **RÉÉCRITE le 2026-09-08** — *un chiffre ne se discute pas, un texte
s'arbitre, et l'arbitrage se trace*. Elle se lit en deux moitiés, **5a (les chiffres)** et **5b (les
textes)**, et son prérequis F16 est **fermé** (migration 035 + `check_edgar_feed.py` §12/§12bis).

⚠️ **La rédaction initiale de la capacité 5 a été RÉFUTÉE par sa propre mesure** — c'est le
précédent le plus utile du chantier, et il confirme la consigne « relire sa ligne de base AVANT le
lot » héritée de la capacité 4. Elle prévoyait « la contradiction signalée jamais tranchée » + une
**file d'arbitrage humain**. Mesuré (`bash tools/mesure_conflits.sh`, coût modèle nul) : `has_conflict`
sur **0/180** · **0** collision de clef #43 · **92 paires** `covers` presque toutes des *facettes* ·
et surtout **le cas d'acceptation nommé donne 0 paire**, ses entries couvrant des champs disjoints —
le **test négatif de la capacité interdisait son propre test d'acceptation**. Le cas est en réalité
**déjà servi par la capacité 4** (péremption, remède `rafraichissement`), vérifié par exécution. La
file aurait été du code appelé 0 fois sur le corpus qui l'a motivée.

**Doctrine arbitrée par l'utilisateur** (verbatim dans la roadmap) : sur les **chiffres**, une seule
vérité à un instant donné — EDGAR reste la base réglementaire, actualisée à la prochaine publication
officielle ; la donnée d'actualité ne la remplace jamais, elle sert à **apprécier** s'il y a une
alerte à lever ou un changement significatif de thèse. Sur les **textes**, deux sources peuvent se
contredire : **c'est à l'agent de trancher**, et la recommandation finale doit laisser l'utilisateur
**tracer sur quelle base elle se fonde** — quelle source retenue, ou comment deux signaux
contradictoires ont été pondérés. **Pas de file d'arbitrage humain.**

Deux mesures faites le 2026-09-08 avant d'écrire, et elles cadrent le lot :
- **5a est à moitié déjà tenue** — `_current_fact_ids` filtre `source_type='edgar_official'`
  (`edgar_feed.py:488`), donc un chiffre d'actualité **ne peut pas** superseder un fait EDGAR. Ce
  qui manque n'est pas un garde-fou mais l'**appréciation** (confirme / diverge / non comparable) et
  son routage vers la machinerie d'alerte **existante** (mode 2 `alert_level`, mode 3 `RE_SYNTHESE`),
  jamais vers un second mécanisme parallèle. Cas réel unique en base : MSFT
  `business_model.recurrence_pct` porte #97 (EDGAR, A) **et** #98 (`financial_press`, B+), côte à
  côte en silence.
- **5b n'a aujourd'hui AUCUN porteur** — `GroundedSynthesis.claims[]` = `text` + `cited_entry_ids`
  (ce qui est cité, jamais ce qui est écarté) ; `RiskMatrix`, seul verdict du flux, n'offre que
  `rationale`, 4 scalaires et des comptes par tier. `IncertitudeBloquante` dit « je ne sais pas »,
  `RechercheDivergente` est le mandat de falsification A6 : chacun répond à une **autre** question.
  Et tous ces contrats sont `extra="forbid"` — l'agent **ne peut pas** ajouter la trace.

⚠️ **Ligne de base à re-mesurer AVANT le lot** : combien de couples sont *réellement* divergents
plutôt que facettes ? Si le nombre est nul, 5b est du code sans matière et c'est **5a** qui porte la
valeur. Migration à écrire *juste avant* son lot, jamais en avance — la prochaine est **036**, non
écrite (mesurer d'abord si elle est nécessaire, comme l'a fait la capacité 4).

⚠️ **L'ordre est load-bearing, ne pas le réordonner** : le registre des sources (2) devait précéder
le durcissement de la porte (4), sinon tout champ devenait `couvert_perime` sans remède disponible.

Motif d'ouverture : l'information la plus fraîche du corpus est la moins bien classée (sur RVMD,
tier A moyen 0,931 sur des faits d'avant l'approbation FDA du 2026-08-26 · tier B+ 0,750 sur
l'information du jour), et le `readiness` prononce quand même `ready, 0 gap` — ⚠️ **ce faux vert est
persisté sur NVDA et MSFT, pas sur RVMD** — **fermé le 2026-09-08** par la capacité 4 : le même
corpus, lu par la porte, rend désormais `not_ready (peremption)`. La roadmap **absorbe** les
points 1 et 2 de « Reste à faire » ci-dessous — ils y sont traités comme des symptômes, pas comme des
tâches indépendantes.

`roadmap/01-spec-v2-unifiee.md` §18 reste la roadmap de **référence** du projet (découpage en lots),
mais elle est terminée sur son périmètre courant ; la roadmap 02 est celle qui s'exécute.

## Où on en est (2026-09-08)

**Le système est exercé, pas prototypé.** La chaîne complète a tourné de bout en bout sur trois
émetteurs, et on connaît désormais ses modes de panne — c'est le principal actif du chantier.

| | NVDA (cas-pilote) | MSFT (généralité) | RVMD (banc d'essai) |
|---|---|---|---|
| Socle | 52 entries (32 A / 15 B) | 51 entries, 19/19 champs, 0 `llm_memory`, ≈ $0,19 | 27 actives (13 déterministes + 14 qualitatives) |
| Readiness | **`not_ready (peremption)`**, 9 champs périmés, 7 mandats | **`not_ready (peremption)`**, 9 champs périmés | aucun rapport en base — 9 lacunes de **collecte** |
| Chaîne | research → bull/bear → réfutation → synthèse = `PROCEED_AVEC_CONDITIONS` | idem, ≈ $0,018 | 7 mandats qualitatifs restants (~0,08 $) |

- **Suite hors-ligne : 1 815 assertions / 0 échec / 22 scripts** — une seule commande,
  **`bash checks/run_all.sh`** (versionné depuis le 2026-09-05 (3)). Il porte les invocations
  correctes : montage `/contract_frozen` (sans lui 4 scripts sous-comptent en sortant à 0) et
  réseau `coolify` + `CHECK_DB_URL` pour `check_entry_nature`. ⚠️ **Ne pas le réécrire dans
  `/tmp`** : la version jetable sous-comptait 47 assertions en silence (`CHANTIER_OUTILLAGE_DEV.md`
  §27).
- **Migrations appliquées jusqu'à 035. Prochaine : 036** — à écrire *juste avant* son lot, jamais
  en avance (§18 de la spec).
- ⚠️ **`run_all.sh` passe `CHECK_DB_URL` + réseau `coolify` à DEUX checks** désormais :
  `check_entry_nature` (§7) et `check_edgar_feed` (§12bis). Tous deux **sortent en échec** si le
  pré-requis manque — jamais un saut de section.
- **Déploiement : le chemin nominal est repassé** (`compose-deploy.sh`, un seul appel) après quatre
  sessions de refus du classifieur. Le repli en commandes séparées reste documenté au §12 de
  `CHANTIER_OUTILLAGE_DEV.md`, mais **re-tester le nominal en premier** à chaque session.

### RVMD — 16 défauts du socle, tous trouvés avant ou après dépense, jamais par le contrat

C'est le résultat le plus réutilisable du chantier : **quatorze défauts sur seize ont été trouvés à
coût de modèle nul**, en exécutant les producteurs déterministes et en **lisant leur sortie en
texte**. Aucun n'était visible dans un diff, et aucun n'a fait rougir un contrat Pydantic — leurs
nombres étaient justes, c'est le *fait énoncé* qui était faux.

| Vague | Défauts | Ce qu'ils ont coûté | Convention née |
|---|---|---|---|
| Socle EDGAR (F1→F6) | ancre de bilan, appariement des flux, tri des concepts XBRL… | 0 token | #42, #43 |
| Valorisation (F7→F9) | multiples à dénominateur négatif publiés tels quels | 0 token | #44 |
| Format (F10, F11) | montants écrasés à « 0,0 Md » ; un CA nul sauté par `if x:` | 0 token | #45, #46, #47 |
| Premier vrai modèle (F12, F13) | pas de date dans le message (le modèle datait le présent à sa coupure) ; drapeau calculé mais jamais persisté | ~0,0105 $/mandat | — |
| Péremption (F14) | `source_date` datée du flux sur un ratio de bilan | 0 token | **#48** |
| Partition (F15) | une entry **non datée** rangée à la fois dans `posterieures` et dans `non_datees` — 4 classes pour 3 entries, et une date *inconnue* comptée parmi les fraîches | 0 token | **#53** |
| Lisibilité de la clef (F16) | `poste_kind`, discriminant de la clef #43, **absent de tout le socle NVDA et MSFT** (19 des 43 faits courants) : la règle juste dans le producteur, son porteur absent de la ligne — toute garantie « une seule vérité chiffrée » y était aveugle sur 2 émetteurs sur 3 | 0 token | **#55** |

### Livré cette session (2026-09-08, 2ᵉ lot) — F16 fermé, capacité 5 réécrite

**Aucune dépense de modèle.** Migration **035** appliquée. Suite : **1 815 / 0 / 22**
(+17 : `check_edgar_feed.py` §12 et §12bis). Déploiement `4b8cc74`, HTTP 200.

- 🔴 **F16 — le porteur d'une règle doit être DANS la ligne.** `_current_fact_ids` appliquait #43
  correctement parce qu'il tient le discriminant de la **spec du producteur** ; un **lecteur** du
  corpus n'a que la ligne, et `poste_kind` y était absent sur 19 des 43 faits courants. Migration
  035 (générateur `_gen_035.py` important `POSTES`, garde `RAISE EXCEPTION` **éprouvée en négatif
  avant application** : elle rendait 27). Après : **0 fait non keyable** sur les trois émetteurs.
  Convention **#55**.
- 📌 **Le défaut a été trouvé par un faux ROUGE que je fabriquais moi-même** : mon mesureur coerçait
  `poste_kind` absent en `stock` et sortait 2 collisions imaginaires sur NVDA (trois exercices de CA
  lus comme trois réponses à une question). En cherchant *pourquoi* il rougissait, le vrai défaut est
  apparu dessous. **L'indécidable est un troisième état, compté à part et nommé** (#44/#53).
- ⚠️ **Jumeau supprimé** : `financials_feed._STOCK_METRICS_LEGACY` recopiait `POSTES[].flow` à la
  main. Il était **d'accord** avec son modèle — deux tables d'accord restent deux tables (#46).
- ⚠️ **ABSENT n'est pas CONTRADICTOIRE, et c'est le test négatif qui l'a montré** : retirer un
  `poste_kind` faisait aussi rougir l'assert « contredit POSTES » (motif `→ None`), qui envoie
  chercher une divergence producteur/table là où il n'y a qu'un backfill à rejouer. Deux causes,
  deux remèdes, deux asserts — #54 transposé aux garde-fous. Corrigé **dans le check**.
- ✅ **Test négatif 6/6**, chacun rouge sur un assert nommé : `poste_kind` retiré · ligne contredisant
  `POSTES` · deux faits de bilan courants · fixture rétrécie 50 → 33 lignes · `CHECK_DB_URL` absente
  (**exit 1**, pas un saut de section) · jumeau réintroduit dans le **code** — tandis que le même
  token laissé dans la seule **docstring** reste **vert** (le grep dépouille les docstrings, sinon il
  lit son propre interdit). ⚠️ Fixture = base scratch **copiée du réel** (`COPY` des 84
  `fact_financial` de prod), 100 ok / 0 FAIL avant mutation : fidèle **et** discriminante, et
  **aucune ligne de production touchée**.
- 🔄 **Capacité 5 réécrite** d'après la doctrine utilisateur (5a les chiffres / 5b les textes), après
  que sa mesure l'a réfutée. Détail au § « Roadmap active » ci-dessus.

### Livré cette session (2026-09-08, 1ᵉʳ lot) — capacité 4 close : la porte à trois états

**Aucune dépense de modèle. Aucune migration.** Récit complet dans `00-REPRISE-ARCHIVE.md`.
Suite : **1 798 / 0 / 22**. Ce qui doit rester ici :

- **La porte consomme le triplet de #50 sans le recombiner** : `couvert` / `couvert_perime` /
  `non_couvert`, `champs_perimes` **retranché** de `champs_non_fondables`, deux remèdes
  (`rafraichissement` ≠ `collecte`), `cause_non_ready` **dérivée** puis revérifiée par le
  validateur. Convention **#54**. Gardes : `check_readiness_recompute.py` §15-19 (**131**, test
  négatif 6/6) et l'acceptation sur corpus réel `tools/acceptation_gate.sh` (**13/0**).
- 🔴 **Le faux vert est tombé, mesuré en production** : NVDA et MSFT passent de `ready, 0 gap` à
  `not_ready (peremption)`, 9 champs périmés nommés chacun, aucun envoyé en collecte. Les 9 sont
  exactement les `actualite_bloquante: True` du profil — **c'est le profil qui périme, pas l'âge**.
- 📌 **Un verdict persisté n'est pas un verdict servi.** La porte corrigée et déployée, l'écran
  rendait *encore* `ready, 0 gap` : le GET renvoyait la ligne stockée. Le rapport se persiste, son
  verdict dépend de l'actualité, qui ne se persiste pas (#53). Le GET **rejoue** donc la moitié
  déterministe sur une `deepcopy` — aucun modèle, **aucune écriture** — et renvoie un bloc
  `reevaluation` que l'écran affiche. ⚠️ Le cache d'ancre (TTL 1 h) mémorise la réponse **brute** et
  **jamais un échec** : un `{}` mémorisé se parse en « aucun événement matériel », donc ancre
  `none`, donc `ready` rendu une heure sur tous les émetteurs. `check_material_events.py` §13/§14
  (**81**, test négatif 2/2).
- ⚠️ **Une seconde table d'accord reste une seconde table.** `FIELD_PLANCHER_OVERRIDES` doublait
  `FIELD_PROFILES` : elle empêchait le desserrage de #50 d'atteindre la porte **et** rendait
  circulaire l'assert de `check_field_profiles.py` §5 écrit pour attraper les desserrages tacites —
  le champ abaissé s'y comparait à sa propre valeur abaissée. Sa suppression a révélé un desserrage
  B+ → B non déclaré, invisible depuis trois jours. §5 se compare désormais au socle `MVDD_SPEC`.
- 📌 **La ligne de base a corrigé la spec** : celle-ci désignait RVMD comme porteur du faux vert.
  En base, RVMD n'a **jamais** eu de rapport readiness — le test aurait viré au vert sans rien
  prouver. Les porteurs étaient NVDA et MSFT ; RVMD est le **témoin de séparation**.

### Acquis de la capacité 3 (2026-09-07) — l'axe `actualité`

- **`knowledge/actualite.py` est le détenteur unique** de la question « ce fait est-il antérieur à
  l'ancre ? ». Trois états jamais recombinés en un nombre : `courante` / `perimee` /
  `indeterminable`. `staleness.py` **traduit** vers le vocabulaire du rapport (`posterieures` /
  `suspectes` / `non_datees`) via `classe_rapport()` — il ne recalcule rien (#46).
  `checks/check_actualite.py` : **66 assertions**, test négatif **5/5**. Convention **#53**.
- 📌 **L'axe ne sera JAMAIS une colonne.** C'est une propriété de la *relation* entre une entry et
  une ancre, calculée **à la lecture**. La stocker la figerait — c'est littéralement la cause n°2 du
  diagnostic : un corpus dont le score est fixé à l'écriture ne vieillit jamais, donc ne peut jamais
  signaler qu'il a vieilli.
- 🔴 **F15, trouvé à coût de modèle nul** — le douzième défaut sur quinze. Tant que la partition
  vivait dans `staleness`, la branche « aucun événement matériel » évaluait **deux prédicats
  indépendants** : l'entry non datée sortait dans `posterieures` **et** dans `non_datees` — somme des
  trois classes = 4 pour 3 entries actives, et une date *inconnue* comptée parmi les fraîches, soit
  exactement ce que la docstring du module interdisait. Invisible au diff et à la suite de checks ;
  sorti en **exécutant le producteur et en lisant sa sortie en texte**. Fermé par construction : le
  passage par un état unique rend la double appartenance non représentable.
- ⚠️ **Un test négatif peut faire rougir le CHECK et non le module.** Le premier cas de sabotage
  tuait le script *avant son bilan* (2ᵉ des trois faux verts, §24). Correctif dans le **check**, pas
  dans le module : `axe()` et `_balayage()` transforment une exception en **FAIL nommé**, avec un
  état de repli hors vocabulaire pour qu'aucun assert ne puisse être satisfait par accident.
- ⚠️ **Un grep d'interdit lit sa propre énonciation.** §10 cherchait `superseded_by`, `FIELD_PROFILES`,
  `actualite_bloquante` dans `actualite.py` — et les trouvait dans sa **docstring**, qui les nomme
  précisément pour les interdire : 4 FAIL sur du code conforme. Le check dépouille désormais la
  docstring avant de greper, et vérifie **en positif** qu'elle porte bien les interdits.
- 📌 **`evenement` reste une classe VIDE DÉCLARÉE — la capacité 3 ne l'a pas remplie**, contrairement
  à ce que ce fichier annonçait. Re-mesuré en base le 2026-09-07 : **66 `mesure` / 68
  `interpretation` / 0 `evenement`**, inchangé. C'est une erreur de *prédiction*, pas une omission
  d'exécution : l'axe ne fabrique aucune entry, et `material_events` *signale* sans jamais écrire
  (#49). ⚠️ Ne pas le « corriger » en ajoutant un champ `nature` au contrat C1.

### Reste ouvert des capacités précédentes (à ne pas re-découvrir)

- **`knowledge/source_registry.py`** (#52, capacité 2) : l'ordre **`nature` PUIS `registre`** est
  load-bearing — `qualify()` n'applique le registre que si le source_type vaut encore
  `web_search_generic`, sinon une source admise pour l'*interprétation* gagnerait du standing sur une
  **mesure**. Et le site de câblage qui compte est l'appel dans **`worker.py` avant le filtre
  `reliability_min`** : le worker rejette sous plancher avant d'atteindre `store_knowledge`.
- ✅ **Le desserrage B+ → B est câblé** depuis le 2026-09-08 : `FIELD_PLANCHER_OVERRIDES` supprimée,
  `_plancher_for` lit `FIELD_PROFILES` champ par champ. `_DESSERRAGE_NON_CABLE` est **vide** et
  §1bis de `check_source_registry.py` a viré au vert de lui-même — un écart connu qui se referme
  sans qu'on y touche est le signe qu'il était écrit au bon endroit.
- ⚠️ **`tickers.sector` est NULL sur les 17 tickers** : un registre (ou une règle) clefé dessus
  n'admettrait personne, silencieusement. C'est pourquoi le secteur est déclaré en CODE.
- 📌 **#51 — deux vocabulaires** : la nature d'une **entry** et la nature dominante d'un **champ**.
  La porte lira la première.

⚠️ **Toujours vrai** : le balayage de péremption *signale*, il ne *décide* pas — les 24 entries
suspectes de RVMD restent **actives**, rien n'est retiré du corpus (#49). Ce qui a changé le
2026-09-08 : la porte ne les compte plus comme couvrantes sur les champs à `actualite_bloquante`.
**Un corpus complet peut être périmé** — c'est désormais dit, et avec le bon remède.

## Ce qui reste à faire — dans l'ordre

⚠️ **Les points 1 et 2 sont désormais instruits par la roadmap 02** (voir en tête) : ce sont les
symptômes qui l'ont ouverte, et les traiter isolément recréerait le défaut. Ils restent listés ici
pour le contexte, pas comme des tâches à prendre telles quelles.

1. **Statuer sur les 24 entries suspectes de RVMD** (le balayage rend la liste, motivée et
   ordonnée). C'est un **jugement humain** par construction : décider qu'un fait est remplacé n'est
   pas automatisable sans donner à une heuristique de dates une voix sur ce que le corpus affirme
   (#29, `feedback_optional_schema_gate`). Point d'atterrissage : `superseded_by` écrit à la main.
   ⚠️ Quatre entries tier A affirment « aucun produit approuvé pour la vente commerciale » alors que
   **la FDA a approuvé RASONQUE le 2026-08-26** — aucune n'est fausse, toutes sont périmées.
2. ✅ **Brancher le balayage sur la porte** — **fait le 2026-09-08** (capacité 4, #54). L'arbitrage a
   été tranché en trois états plutôt qu'en oui/non, et le risque symétrique est fermé :
   `ancre_substantielle` écarte les 8-K purement formels (items tous 9.01) mais garde les dépôts
   **sans item** — « sans item » n'est pas « sans substance » (un 6-K).
3. **FDA/EMA en régulateur A- (0,85)** — *décidé avec l'utilisateur, non commencé*. Mesuré :
   `fda.gov` n'est dans **aucune** table, et `_EU_REGULATOR_SUFFIXES` porte `esma.europa.eu`
   (titres) mais pas `ema.europa.eu` (médicaments). L'approbation FDA du 2026-08-26 — l'événement
   même qui a ouvert la roadmap 02 — classe aujourd'hui `web_search_generic` **0,50**. Un
   `regulator_filing_us` touche `SOURCE_RELIABILITY_BASELINE`, le `Literal SourceType`, le frontend
   **et les 12 prompts v2 en base** (tous énumèrent les source_types) → **migration 035** + règle
   #19. Lot séparé à dessein : il n'a rien à voir avec le registre, il élargit le vocabulaire.
4. **File de propositions de sources** — *demandée par l'utilisateur, non conçue*. Le système
   observe les domaines `web_search_generic` réellement rencontrés, **recommande** un classement
   (portée secteur/ticker, natures, tier), l'utilisateur **valide**. ⚠️ L'admission reste un **acte
   humain** : rien ne se promeut tout seul, pas même par corroboration (#50 — N sources recopiant
   un communiqué ne sont pas N sources indépendantes).
5. **Les 7 mandats qualitatifs RVMD restants** (~0,08 $) — désormais sans risque connu : le worker
   porte la date du jour, l'ancre documentaire **et** l'ancre matérielle.
6. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, **non bloquant** tant
   que search-worker + `synthesis_feed` couvrent les champs requis.
7. **4ᵉ ticker** — aucun blocage technique. ⚠️ Ajouter son entrée dans `websearch._ISSUER_DOMAINS`
   **en même temps que le ticker** (#33) : sans elle, son IR retombe sous le plancher. ⚠️ Et son
   **secteur** dans `source_registry._TICKER_SECTEURS` s'il doit hériter d'un registre sectoriel —
   `tickers.sector` est NULL en base et n'est lu par rien (#52).

### Dettes techniques connues, assumées

- **`base_rate_ge` n'est pas câblé** dans `run_research` : `reverse_dcf.croissance_implicite_…` est
  toujours chiffré, mais son consommateur attend le `taux_base_pct` précis.
- **`BullCase.conviction ×10 si ≤1`** : coercition gardée comme filet, risque de polarité théorique
  sur le float `1.0`. Noté, pas corrigé.
- Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « SearXNG/API » :
  **cosmétique**, à corriger à la prochaine migration qui touche `agent_prompts`, pas avant.
- **`covers` multi-champs** : une entry qui couvre 3 champs les couvre *également*, alors qu'elle en
  fonde souvent un et effleure les deux autres. Limite de conception à arbitrer, pas à changer
  unilatéralement.
- **`uncovered_fields` dupliqué** entre deux calculs voisins (mineur, sans effet observé).

## Décisions structurantes (toujours actives)

- **Modèles** — métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731` (ctx 1M, $0.08 in /
  $0.18 out). Les ouvriers émettent du JSON → coût **dominé par l'output** ; le réflexe « petit
  modèle ouvrier » vient de la tarification Anthropic et **ne se transpose pas**.
- **Embeddings** — `BAAI/bge-m3` **1024d**. Corpus en **français** : `bge-base-en-v1.5` ratait les
  entrées EDGAR tier A (MRR 0.644 → **0.905**). **Ne pas « améliorer » en hybride** : la fusion RRF
  **dégrade** (0.905 → 0.655).
- **Web search** — **Exa**, débordement **Serper**. SearXNG écarté sur le **mode de panne** (captcha
  = résultats vides sans erreur), pas sur le coût. Changer de backend = une classe.
- **Contrainte VPS** (mesurée) : 3,8 Go RAM / ~2,1 Go de socle / **0 swap**, ~5 Go libres →
  pas de self-hosting gourmand. ⚠️ Vérifier le disque avant tout `docker pull` volumineux.

## Pièges à ne pas re-découvrir

- **DeepSeek + `response_format=json_object` est NON FIABLE** : collapse sur `{}` ou emballe la
  sortie. Tout passe par `run_json_agent(json_object=False)` + `extract_json`.
- **Contrats = pydantic v2** → tester dans le container backend, **pas** le python hôte (v1).
- **Migrations non auto-appliquées** : `docker cp` + `psql -f`. Le heredoc `psql << EOF` via
  `docker exec` échoue **silencieusement**.
- **asyncpg** : `$1`/`$2` (jamais `%s`) ; JSONB auto-décodé (jamais de `json.dumps` avant INSERT).
  ⚠️ `DATABASE_URL` porte le dialecte SQLAlchemy `postgresql+asyncpg://` — `asyncpg.connect()` le
  **refuse** (`ClientConfigurationError`). Retirer `+asyncpg` pour une connexion directe.
- **Une colonne `NOT NULL` neuve met le déploiement en DETTE.** Entre l'application de la migration
  et le rebuild, le conteneur sert du code qui ne fournit pas la colonne : tout INSERT échoue. Et le
  check ne le voit pas — il *lit*. Prouver le chemin d'écriture par une **écriture réelle** dans le
  conteneur déployé (créer, relire en base, supprimer, vérifier le total inchangé), pas par un SELECT.
- **Déploiement** : rebuild, jamais restart. Le build part du **répertoire local** — un commit non
  poussé serait quand même déployé, donc prod et `origin/main` divergeraient en silence ; le script
  pousse d'abord, ne pas le court-circuiter. Pour portfolio, **2 conteneurs sur le domaine sont
  normaux** (backend `/api` + frontend catch-all) — exception codée en dur dans le script.
- **Règle #19** : tout changement de contrat = 3 points de synchro (prompt en DB · frontend ·
  import). Rafraîchir un prompt en DB ne demande **pas** de rebuild.
- **Un correctif de prompt ou de schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai
  modèle.** Un desserrage fait à chaud (`Optional`, `extra=ignore`) est un trou silencieux :
  durcir le prompt d'abord, re-tester, **PUIS** re-serrer.
- **Un écran ne se vérifie pas par un 200** : Next.js sert la coquille et charge côté client. La
  méthode UX-2/UX-3 reste la référence — capturer les payloads **réels** avant d'écrire du JSX (un
  nom de champ faux n'affiche pas une erreur, il affiche **du vide**), `docker build` comme seule
  vérification frontend (`node --check` est un no-op sur ESM), puis **capture headless regardée**.
- **Méthode, éprouvée 14 fois** : exécuter les producteurs déterministes et **lire leur sortie en
  texte** avant toute dépense de modèle ; après un déploiement qui remplace une vérité, ne pas
  demander « la nouvelle valeur est-elle bonne ? » mais **« combien de lignes sont actives sur
  cette clef ? »** (#43) ; un check neuf n'est livrable qu'après avoir viré au rouge **pour la
  bonne raison** (les trois faux verts : fixture non discriminante, script mort avant ses asserts,
  assert à côté du point de lecture — `CHANTIER_OUTILLAGE_DEV.md` §24).
- **Un agrégateur reconnaît un bilan à sa FORME, jamais à sa position.** Trois dialectes cohabitent
  dans `checks/` (`… vérifications OK`, `N ok / N FAIL`, `N OK / N KO`) et un script émet un LOG
  *après* son bilan : un `tail -1` a sous-compté 47 assertions en silence, `exit 0`. L'absence de
  toute ligne de bilan est un **échec** (script mort avant ses asserts), jamais un zéro. → §27.
- **Un test négatif qui mute la base ne s'écrit jamais en une commande composée** : saboter,
  mesurer, restaurer, re-vérifier = quatre appels. Un `docker run` mort au milieu laisserait la
  production sabotée sans que rien ne le dise.

## À lire avant de reprendre

- **`CLAUDE.md` du projet** — conventions **#22 à #52**. Les plus structurantes du chantier
  courant : #29 (la couverture se lit dans un index), #42/#43 (datation et identité d'un fait),
  #44 (calculé / non calculable / absent), #46 (détenteur unique d'une règle), #47 (un zéro est une
  valeur), **#48** (la colonne `source_date` est un porteur de la date), **#49** (la péremption est
  une seconde horloge, et elle produit un rapport), **#50** (trois axes jamais recombinés ; le
  standing est une propriété du COUPLE source × nature), **#51** (nature d'une ENTRY ≠ nature
  dominante d'un CHAMP : deux vocabulaires, le second ne dérive jamais le premier ; `mesure`
  n'est jamais accordée par défaut), **#52** (une source est admise pour un COUPLE source × nature,
  et l'ordre `nature` puis `registre` est ce qui rend cette phrase vraie ; plafond ≠ qualification),
  **#53** (l'axe `actualité` est une propriété de la RELATION entry × ancre, calculée à la lecture et
  jamais stockée ; `indeterminable` n'est pas `courante` ; le seuil est le `reportDate`, jamais le
  `filingDate`).
- **Specs** : `roadmap/00-principe-directeur-v2.md` · `roadmap/01-spec-v2-unifiee.md`
  (§5 agents, §7 curator/readiness, §8 contrats, §14 migrations, §16 UX, §18 découpage).
- **Cartes de contrat** : `roadmap/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
- **Code** : `backend/app/agents/v2/` (`worker.py` · `curator.py` · `analysis.py` · `runner.py`) ·
  `backend/app/knowledge/` (`service.py` · `websearch.py` · **`source_registry.py`** ·
  `edgar_feed.py` · `synthesis_feed.py` · `financials_feed.py` · `valuation_feed.py` · `units.py` ·
  **`material_events.py`** · **`staleness.py`** · **`actualite.py`**) · `backend/app/contracts/` ·
  `backend/checks/README.md`.
- **Historique complet** : `00-REPRISE-ARCHIVE.md`. **Outillage transverse** :
  `../../../CHANTIER_OUTILLAGE_DEV.md` (§16 délégation, §24 tests négatifs, §25 porteurs d'un fait,
  §26 la ligne de base est une mesure, **§27 un bilan se reconnaît à sa forme**).
- **Visuel** : https://provenance.jlmvpscode.duckdns.org

## À coller pour reprendre

> Reprise de **portfolio-tracker V2** (chantier cartes de provenance).
> Contrat figé, boucle V2 complète (décider → surveiller → sortir → apprendre), écrans livrés,
> chaîne exercée sur **NVDA, MSFT et RVMD**. Principe directeur UX → agents → données, 3 garde-fous :
> G1 schéma versionné = source unique · G2 décision contrainte par l'analyse · G3 donnée versionnée
> + scorée + figée, jamais de texte libre. DÉCISION #1 = Option C (base neutre → bull/bear isolés →
> réfutation bear→bull → synthèse).
> Le chantier courant est le **3ᵉ ticker RVMD**, banc d'essai des modes de panne du socle :
> **16 défauts (F1→F16)** trouvés et corrigés, quatorze à coût de modèle nul en lisant les sorties en
> texte. Le corpus a désormais **une horloge** (ancre d'événements matériels 8-K/6-K + balayage de
> péremption qui rend un rapport, jamais un `superseded_by`).
> **Roadmap active** : `roadmap/02-spec-autorite-vs-actualite.md` (figée le 2026-09-05) — *autorité
> contre actualité*. Le corpus classe son information la plus fraîche au plus bas et prononce quand
> même `ready` : un scalaire unique porte deux propriétés orthogonales et les confond. La révision
> les sépare en **trois axes jamais recombinés** (fiabilité *stockée* · actualité *calculée à la
> lecture* · nature *stockée*), et le standing devient une propriété du **couple (source × nature)**.
> **Capacités 0, 1, 2, 3 et 4 CLOSES** : la table de profils des 19 champs (#50, 193 assertions) ·
> l'axe `nature` en dérivé déterministe (#51, migration 034, 52 assertions) · le **registre nominatif
> des sources** (#52, 78 assertions, 4 sources biotech co-choisies pour RVMD) · l'axe **`actualité`**
> (#53, `knowledge/actualite.py`, 66 assertions), calculé **à la lecture** et jamais persisté — le
> persister reproduirait le défaut d'origine, un corpus qui ne vieillit pas · la **porte de
> complétude à trois états** (#54, 131 assertions, le 2026-09-08), qui consomme les trois axes sans
> les recombiner. Quatre résultats sont load-bearing pour la suite : la nature d'une **entry** ≠ la
> nature dominante d'un **champ** ; le standing s'accorde au **couple** (source × nature) — d'où
> l'ordre `nature` PUIS `registre` dans `qualify()` ; `staleness.py` **traduit** l'axe sans jamais le
> recalculer (#46 — c'était F15) ; et **un verdict persisté n'est pas un verdict servi** — le GET
> readiness rejoue la moitié déterministe de la porte à la lecture, sans écrire.
> **Le faux vert d'origine est tombé, mesuré en production** : NVDA et MSFT passent de `ready, 0 gap`
> à `not_ready (peremption)`, 9 champs périmés nommés, avec un mandat de *rafraîchissement* et non
> de collecte. Suite hors-ligne : **1 815 / 0 / 22**, migrations jusqu'à **035**.
> **F16 fermé** (migration 035, convention **#55**) : `poste_kind`, le discriminant de la clef #43,
> était absent de tout le socle NVDA et MSFT — la règle juste dans le producteur, son porteur absent
> de la ligne, donc **illisible pour un lecteur**. Il a été trouvé par un **faux rouge** que
> fabriquait mon propre mesureur (absence coercée en `stock`).
> **Prochain jalon = capacité 5, RÉÉCRITE le 2026-09-08** : *un chiffre ne se discute pas (5a), un
> texte s'arbitre et l'arbitrage se trace (5b)*. Sa rédaction initiale — « signalée jamais tranchée »
> + file d'arbitrage humain — a été **réfutée par sa propre mesure** : 0 conflit en base, 0 collision
> de clef, et son cas d'acceptation nommé donne **0 paire** (champs disjoints), c'est-à-dire que son
> test négatif interdisait son test d'acceptation. Le cas était déjà servi par la capacité 4
> (péremption). ⚠️ Ne pas réordonner les capacités. ⚠️ **Une ligne de base se requête AVANT le lot** —
> deux fois de suite maintenant, elle a changé le lot : la spec de la capacité 4 visait le mauvais
> émetteur, celle de la capacité 5 visait un mécanisme sans matière.
> LIRE D'ABORD : ce fichier, le `CLAUDE.md` du projet (conventions #22-**#54**),
> `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.
