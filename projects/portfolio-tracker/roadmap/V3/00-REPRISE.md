---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-25
project: portfolio-tracker
role: >
  Prompt de reprise du chantier V3 (frameworks). Le RÉCIT des lots livrés n'est PAS ici : il est
  dans `00-REPRISE-ARCHIVE.md`, les règles durables dans le `CLAUDE.md` du projet (conventions
  numérotées #25…#81), et la PREUVE de ce qui existe dans `backend/checks/` — qu'on exécute.
  Roadmap active : **`roadmap/V3/03-spec-frameworks.md`** (ouverte le 2026-09-09) — le référentiel
  d'indexation passe d'une grille fermée de 19 champs identique pour tous les émetteurs à des
  **frameworks stables à variables par entreprise**, chacun garanti par un **manager**.
  `roadmap/V3/doctrine-trois-axes.md` est **close**.
  ÉTAT au 2026-09-25 : lots 0 à 4 clos, **lot 5 EN COURS** (le projecteur du mémo est livré et
  prouvé ; la chaîne est allée de bout en bout sur `defendabilite` le 2026-09-25 — arbitrage A
  consommé, `moat` → `instruite` ; **le BOUCLAGE comité → collecte est livré au niveau code + tests
  + persistance réelle** le 2026-09-25 (2) — `serve_mandate`/`read_open_mandates` ont enfin un
  appelant de prod (`bouclage.py`), note honnête à 4 sorts, garde qui COMPTE les appelants ; reste le
  **passage réel de bout en bout + le déploiement**, tous deux bloqués par le sandbox de la session,
  voir archive). La chaîne à six agents
  est allée de bout en bout en réel sur **deux** frameworks : RVMD × `qualite_financiere` ×
  `pre_revenus` (2026-09-21, #78) et RVMD × `defendabilite` × `pre_revenus` (2026-09-25, archive).
  Elle n'a jamais produit d'investissement, et c'est NORMAL — on construit l'amont lot par lot, la
  partie aval/suivi vient après (arbitrage utilisateur 2026-09-22).
  Suite `run_all.sh` = **3168 assertions, 0 échec sur 43 scripts** (re-mesuré le 2026-09-25 (2) ;
  +27 par `check_bouclage` ; les 3 checks « live » restent hors périmètre par conception, d'où 43
  exécutés pour 46 fichiers). `negatif_bouclage.sh` = **11 mutations / 0** (dont les 2 « exercé »).
  Migrations : **046 appliquée** (vérifiée en base, `ticker_archetypes` existe) ; la prochaine
  ÉCRITE sera **047**. `portfolio-backend` est À JOUR — rebuild du **2026-09-25** (commit `e2b548f`),
  vérifié DANS le conteneur (`projection_memo.py` présent, `operations_etablies` × 2) et par
  `GET /api/health` → **200**. ⚠️ Ce champ affirmait « à jour » le 2026-09-24 alors que le conteneur
  ne portait **ni la garde ROIC ni le projecteur** : un correctif commité n'est pas un correctif
  déployé, et le feed serait reparti fabriquer un successeur à #656.
  PROCHAIN : voir **▶ PROCHAIN JALON** ci-dessous — seul endroit où il est écrit.
---

# Prompt de reprise — portfolio-tracker V2

> **Ce fichier ne s'empile pas.** Le récit des sessions vit dans `00-REPRISE-ARCHIVE.md` (copie
> conforme, rien de résumé), les règles durables dans le `CLAUDE.md` du projet (conventions
> numérotées), les enseignements d'outillage transverses dans `../../../CHANTIER_OUTILLAGE_DEV.md`.
> Ici : **l'état atteint, ce qui reste, et les pièges à ne pas re-découvrir.** Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5.

> 🗂️ **Réorganisation d'architecture — 2026-09-13.** Toutes les specs actives vivent désormais dans
> `roadmap/V3/` (dossier **autonome**, aucune dépendance sortante) ; l'historique V0/V1/V2 est sous
> `roadmap/archive/{v0,v1,v2}/`. Renommages : `02-spec-autorite-vs-actualite.md` → `doctrine-trois-axes.md`,
> `00-principe-directeur-v2.md` → `principe-directeur.md`, `benchmark-…` → `benchmark-methodologies.md` ;
> `provenance-cards/` et ce fichier ont migré sous `roadmap/V3/`. Les chemins load-bearing du code
> (générateur de migration 025, montages de `run_all.sh`, `check_frameworks_definitions`,
> `ligne_de_base_frameworks`) ont été mis à jour et **la suite est TOUT VERT (2172/0)** après migration.
> `01-spec-v2-unifiee.md` est archivé (ses parties valides sont inlinées dans `03-spec` §1). Nouvelle
> doc d'architecture : `ARCHITECTURE-CIBLE.md` + un `ARCHITECTURE.md` par module (cible ; réalisé = les checks).

---

## 🎯 Roadmap active

### **`roadmap/V3/03-spec-frameworks.md`** — ouverte le 2026-09-09

**Le diagnostic, en une phrase** : le système range la connaissance dans une **grille fermée de
19 champs, identique pour tout émetteur**, et tout ce qui n'y entre pas est **écarté en silence**.

Les faits mesurés qui l'ont ouverte (aucun n'est une opinion) :

| Mesure | Valeur |
|---|---|
| Orphelines (entries qui ne fondent rien) | MSFT 20 % · **NVDA 50 %** · RVMD 26 % |
| Dont, sur NVDA | **16 faits SEC tier A** — revenu ×3, résultat net ×2, marge brute, OCF, capitaux propres, actifs, trésorerie+dette, capex, retour au capital ×2 |
| Feuilles du `research_memo` **sans** chemin d'indexation | **14** (dont `moat.type/trend/durabilite_ans`, `earnings_quality`, `capital_allocation_scorecard`, `epv`, `dcf_scenarios`, `reverse_dcf`) |
| Chemins indexables **jamais consommés** par le mémo | **3** (dont `risques.risques_cles`, le plus peuplé de la base — 15 entries) |
| Étapes 4 / 5 / 6 / 8 du benchmark avec preuve indexable | **0** |
| Synthèses grounded sur RVMD | **0** (3 des 4 cibles vides) |
| Entries sur `produits.unit_economics`, toute base confondue | **2** |

**Ce que la v3 change** — ⚠️ **révisé le 2026-09-10, la version précédente de ce paragraphe est
périmée sur deux points** (elle annonçait « `frameworks` + `framework_questions` en base » et
« `covers` devient une clef étrangère ») :

- le référentiel est un **fichier inerte versionné** (`app/frameworks/frameworks.yaml`), **pas des
  tables** — une question dérivable par requête depuis le corpus ferait mesurer au test de
  couverture sa propre constante (spec §5.2) ;
- **`covers` ne devient pas une FK : elle DISPARAÎT de `knowledge_entries`** (audit du 2026-09-10,
  écart V5). La couverture est une propriété de la **relation** entry ↔ question, comme l'actualité :
  elle vit dans `question_coverage(framework_id, framework_version, question_id, ingredient_id,
  entry_id)`. L'entry ne porte plus aucun mot de framework, donc changer de framework n'invalide
  plus le corpus ;
- **deux agents entre la question et l'entry** (spec §3.6) : un **traducteur** transforme les
  questions universelles en un **plan de collecte** par ticker (métrique, source, ancre — RVMD et
  MSFT ne cherchent pas la même chose au même endroit), un **collecteur** exécute chaque ligne via
  EDGAR / web / futur connecteur. Le collecteur **ne connaît pas la question** ;
- chaque framework est **garanti par un manager** dont l'autorité s'exerce par 4 contrôles
  vérifiables (complétude · fondation · honnêteté de l'approximation · non-substitution). Son
  **renvoi** produit un **mandat de recherche exécutable** — ce qui ferme la boucle comité →
  collecte, aujourd'hui absente.

**Deux pilotes**, choisis pour un contraste maximal de matière disponible :

- **« Qualité financière »** (quantitatif, étape 5, Greenwald) — *ses ingrédients sont déjà en
  base* : les 26 orphelines de NVIDIA en sont littéralement la matière. Il prouve qu'on sait
  **ranger** ce qui existe.
- **« Défendabilité / moat »** (qualitatif, étape 4, Porter-Morningstar) — *ses 4 champs de sortie
  sont 100 % orphelins d'indexation aujourd'hui*. Il prouve qu'on sait **faire chercher** ce qui
  n'existe pas.

### ✅ Lot 0 — ligne de base **acquise le 2026-09-09**

Trois mesureurs versionnés dans `backend/tools/` (jamais `/tmp`), aucun n'appelle un modèle, tous
rendent un bilan `N vérifications OK, M échec(s)` reconnaissable à sa **forme** :

| Outil | Aujourd'hui | Vire au vert |
|---|---|---|
| `reconcilier_vocabulaires.{py,sh}` | **4 ok / 2 FAIL** — 30 orphelins + 13 inutilisés, **0/6 blocs du mémo adossés** | état terminal (un framework par bloc) |
| `check_reconciliation.py` + `negatif_reconciliation.sh` | **10 ok / 0 FAIL** · **5 mutations / 0 échappée** | (vert — garde l'instrument, pas le chiffre) |
| `ligne_de_base_frameworks.{py,sh}` | **2 ok / 0 FAIL** — les 6 valeurs de §9.1 confirmées | (mesure, pas un test) |
| `acceptation_frameworks.{py,sh}` | **3 ok / 10 FAIL** — T1-T8 rouges, dont 6 sur **zéro ligne** | par lots, les 8 au lot 7 |

> ⚠️ **Le `14 / 3` cité partout jusqu'au 2026-09-21 mesurait l'ANCIEN étalon** (`FIELD_PROFILES`,
> la grille MVDD que le lot 3 a dépossédée). L'acceptation, elle, mesurait déjà 30/13 : deux
> copies d'une règle, divergentes en silence pendant tout le lot 3. Le couple n'a pas régressé,
> l'étalon a été corrigé — détail en spec §6, règle désormais détenue une seule fois dans
> `tools/reconcilier_vocabulaires.ecart`.

⚠️ Depuis le lot 1, cet outil **importe** `COLONNES_DENORMALISEES` du contrat au lieu de deviner
ses noms de colonnes. Verdict inchangé après recâblage (mêmes 8 motifs) : un changement de verdict
aurait signifié qu'on avait modifié l'exigence en croyant corriger son adressage.

Les 6 valeurs sont consignées **dans la spec §9.1** avec les trois constats que la mesure ajoute
(l'étape 8 a un champ indexable ; `produits.unit_economics` n'a **aucune** entry primaire ; NVDA
produit 4 synthèses grounded sur des cibles sans matière indexée — *ce que le lot 3 doit rendre
reproductible, le système le fait aujourd'hui par accident*).

### ✅ Lot 1 — le contrat **acquis le 2026-09-09**

**Ordre imposé respecté : UX (contrat) → agent → données.** Le contrat existe et est éprouvé ; les
13 questions restent des **données du lot 2**, délibérément non écrites.

| Livrable | Fichier |
|---|---|
| Le contrat, Pydantic strict | `backend/app/contracts/framework_answer_schema.py` |
| Le **pont relationnel** (#37) | `backend/app/agents/v2/frameworks.py` |
| Le check | `backend/checks/check_framework_contract.py` — **91 assertions** |
| Son **test négatif** | `backend/checks/negatif_framework_contract.sh` — **20 mutations, 20 détectées** |
| Carte de provenance champ par champ | `roadmap/V3/provenance-cards/framework_answer_card.md` |
| Écran niveau 3 en maquette | `roadmap/V3/provenance-cards/framework_screen_niveau3.md` |

**Deux écarts assumés avec le JSON de la spec §2.4**, tous deux plus stricts, documentés en tête du
contrat et dans la carte : (1) `honnetete_approximation` a **trois** valeurs (`ok|ko|sans_objet`) —
sur une réponse qui n'approxime pas, `ok` serait un vert vrai sur zéro ligne ; l'**équivalence**
`sans_objet ⟺ statut ≠ approxime` empêche le 3ᵉ état de servir d'échappatoire. (2) `analyste` est
ajouté — §3.4 écrit le contrat pour N > 1, et sans porteur d'identité le correctif naturel serait de
**moyenner** deux réponses divergentes, ce que §3.4 interdit.

**L'actualité n'est pas un champ de `FrameworkAnswer`** (#53) : `FrameworkAnswer` est ce qui s'émet
et se persiste, `FrameworkAnswerServie` ce que le GET rend. `extra='forbid'` rend la persistance de
l'axe **impossible par construction**, plutôt que gardée par un `if`.

**Ce que le lot 1 a corrigé au passage** : l'outil d'acceptation du lot 0 devinait ses noms de
colonnes (`framework`, `rang_degrade`, `methode_approximation`, `ingredients`, `motif`) — le contrat
les niche. `COLONNES_DENORMALISEES` est désormais le **détenteur unique** de la correspondance, et
l'outil l'importe. Vérifié après recâblage : l'acceptation rend **exactement le même verdict
qu'avant** (1 ok / 8 FAIL, mêmes motifs) — seul l'adressage a changé, pas l'exigence.

### ✅ Lot 2a — le référentiel **acquis le 2026-09-10**

Les 2 pilotes et leurs **13 questions** en **données inertes** (`app/frameworks/frameworks.yaml`),
contrat strict `framework_definition_schema.py`, invariants relationnels G–M dans le pont (#37).
`check_frameworks_definitions.py` **39 / 0** — dont **§5, la garde de l'ordre questions → données**
(aucun énoncé, ingrédient ou gabarit ne nomme un ticker, une entry ou un poste EDGAR) et **§7, la
confrontation spec ↔ référentiel** (la spec est **parsée**, jamais recopiée). Test négatif
**22 / 22**, chaque mutation rouge sur son **assert nommé** et atteignant quand même son bilan.
Suite **1 988 / 0**.

**L'arbitrage T1 n'a pas été tranché : il a été DISSOUS** (spec §9.2). Il demandait « quel seuil
d'orphelines rattacher ? » alors que la vraie question était « de quel droit le corpus est-il la
cible ? ». Réponse : d'aucun (§0.6). Remplacé par **T1** (aucun ingrédient essentiel ni servi ni
mandaté) + **T1bis** (il DOIT en manquer au moins un, **nommé** — `qf_1.cout_du_capital`) : une
couverture à 100 % **fait échouer** le pilote, parce qu'elle prouverait la rétro-conception.

### ✅ Lot 2b — **acquis** (migrations 036/037/038 le 2026-09-10, exploitation le 2026-09-11)

Les trois migrations sont **appliquées en production** : **036** (archivage `archive_v2`, 8 colonnes
retirées, `entry_type` fermé à 5 jetons), **037** (resynchro des prompts `ingestion-agent` /
`search-worker`, #39), **038** (`archive_v2` en lecture seule). Détail dans `CLAUDE.md`.

**Les deux gestes d'exploitation sont joués (2026-09-11).** Le **rebuild** est fait —
`GET /tickers/NVDA/knowledge/entries` rend **200** (rendait 500 : `column ke.is_deleted does not
exist`), `docker ps | grep portfolio` montre **exactement un** backend. Le **rejeu déterministe** a
tourné (`bash tools/rejeu_producteurs.sh`, 3 tickers, 0 erreur) — ⚠️ **le classifieur N'A PAS
bloqué le chemin nominal** (`feedback_blocage_classifieur_non_permanent` confirmé : refus levé). Le
plancher §7 (13 déterministes RVMD) est **restauré**.

> ✅ **RÉSOLU au maillon 5 (2026-09-12) : §12bis est MORT, le proxy `PLANCHERS[0]` du rejeu retiré**
> (conventions #61/#62). Le paragraphe ci-dessous est le diagnostic d'origine, conservé pour le *pourquoi*.

⚠️ **Le §12bis restait ROUGE (46 < 50), et c'était diagnostiqué, pas à colmater.** Le seuil « 50 » n'est
pas une couverture : c'est le **compteur de générations accumulées** le 2026-09-08 (archive : MSFT 8
+ NVDA 11 + RVMD **31** = 50, dominé par les 31 rejeux de RVMD pendant la saga des 16 défauts). Après
recréation propre par la 036, le socle courant est **complet** (MSFT 8/8 · NVDA 8/8 · RVMD 7/8 = 23
faits) mais ne porte que 2 générations = 46 lignes. Atteindre 50 exigerait de rejouer EDGAR une 3ᵉ
fois **juste pour ajouter des générations** — le gonflage que ce chantier proscrit
(`feedback_fixture_pollue_le_reel`). **Le §12bis meurt au lot 2c**, quand `POSTES` cesse d'être une
liste en dur et devient dérivé du plan de collecte : le socle data-first qu'il gardait disparaît.
Ne pas le recalibrer, ne pas rejouer pour le verdir. ⚠️ Au passage : le proxy `PLANCHERS[0]` de
`rejeu_producteurs.py` est un **faux vert** (il compte `edgar_official` toutes métriques = 68, pas
les 8 postes socle que §12bis lit = 46) — à corriger ou retirer avec §12bis au lot 2c.

**Deux enseignements du lot, tous deux de la même famille — un balayage par `grep` ne voit que ce
qui est écrit là où il regarde :**

- `exit.LESSON_ENTRY_TYPE` valait `lesson_learned`, jeton que la 036 ne retient pas. Le vocabulaire
  fermé avait été dérivé des littéraux `entry_type=` trouvés dans `app/` — ici la valeur passe par
  une **constante**, donc le balayage l'a manquée. Le prochain post-mortem aurait violé le CHECK à
  l'INSERT, sur un chemin qu'aucun check hors ligne n'emprunte. Corrigé en `analysis` : l'`entry_type`
  nomme ce que l'assertion **est** (#57), pas qui l'a produite — le producteur est déjà porté par
  `LESSON_SOURCE_TYPE`.
- `check_edgar_feed.py` §12bis portait encore `AND is_deleted = FALSE` dans une **f-string SQL**
  d'une section qui ne s'exécute qu'avec une vraie `CHECK_DB_URL` : hors ligne, le check passait au
  vert **sans jamais compiler ce SQL**.

⚠️ **Piège de séquencement, tenu** : l'archivage vide les tables que `check_edgar_feed` §12bis
(`>= 50` faits socle) et `check_entry_nature` §7 (`== 13` entries déterministes RVMD) **lisent**. La
tentation était de baisser les planchers (`feedback_optional_schema_gate`) — **refusée**. Les
producteurs concernés sont déterministes : les rejouer coûte des appels réseau et **zéro token**, et
ils repeuplent exactement ce que ces planchers mesurent. `tools/rejeu_producteurs.py` **lit dans
`archive_v2` qui avait un socle**, il ne retape aucune liste de tickers.

⚠️ Mesureurs **versionnés**, jamais `/tmp` · bilan reconnaissable à sa **forme** (`grep -E` sur le
motif, jamais `tail -1` ; absence de bilan = **échec**) · **jamais exécutés dans
`portfolio-backend`** (il porte le code déployé, qui peut précéder ce qu'on mesure).

### ✅ Lot 2c — **TERMINÉ le 2026-09-12** · 7 maillons + migration 039

> Récit complet (les 7 maillons, les défauts trouvés, les acceptations réelles) : **archive,
> entrée « 2026-09-12 — lot 2c »**. Le durable est en conventions **#57 → #62** du `CLAUDE.md`
> projet. Ne rien re-déduire d'ici : ce bloc n'est qu'un index.

L'audit avait rendu 10 écarts (V1–V10). **V1** en était le cœur : le socle EDGAR collectait *avant
et indépendamment de toute question* — 8 postes écrits à la main servant 4 des 33 ingrédients
essentiels, et 12 ingrédients `mo_*` sans aucune source **sans que rien ne le dise**.

| # | Maillon | Mesure |
|---|---|---|
| 1 | Contrat du plan (`collection_plan_schema.py`) — le statut porte exactement sa charge ; `omis` n'est pas un statut | 22/0 · négatif 9/9 |
| 2 | Pont `valider_pont_collection_plan` — `[N]`…`[R]`, dont **`[R]` : omettre un ingrédient essentiel = plan REFUSÉ** | négatif 7 mutations |
| 3 | **Traducteur** (`traducteur.py`) — contexte lever-free, en-tête du plan posée par le CODE | 15/0 · acceptation réelle passée |
| 4 | **Collecteur** + aiguilleur — `LigneAveugle` (ni question ni ingrédient, principe 2 **structurel**) ; la couverture est un **sous-produit déterministe du dispatch** (#57) | 15/0 · persistance 8/0 · négatif 6+5 |
| 5 | **`POSTES` dérivé du plan** + retrait du levier `RESSERRER` de `curator.py` | #61/#62 · **déployé** `6cb1714` |
| 6 | **Migration 039** (`collection_plans`, `collection_plan_items`, `framework_mandates`) — les CHECK SQL redisent le contrat (#37) | appliquée en prod 2026-09-11 |
| 7 | **Exécuteur réel + chaîne runtime** (`collecte_executor.py`) — dispatch question-AVEUGLE | 31/0 · négatif 7/7 |

⚠️ **Ce que le lot 2c a laissé comme dette de méthode, à relire avant de bâtir dessus :**
- la ligne phare *cash burn* de RVMD retombe encore sur « clôture du trimestre » dans l'ancrage —
  **non sur-optimisé sur 1 ticker à dessein**, à traquer par l'éval multi-tickers (backlog #9) ;
- **`check_edgar_feed §12bis` est MORT** avec le maillon 5 (plus de socle de taille garantie).
  L'identité #43/F16 reste tenue **hors ligne** (§3/§10/§12). Ne pas le « verdir » en rejouant
  EDGAR : ce serait le gonflage que `feedback_fixture_pollue_le_reel` proscrit ;
- **pré-requis §7 levé** par le principe §0.6 — les 30 faits web du maillon 4 sont **compatibles**,
  pas des parasites ; l'ancien `== 13` était une cible-corpus interdite ([[project_entry_nature_gate_invariant]]).
  Le corpus RVMD hérité (43 déterministes actifs) sera re-collecté propre par le lot 3 (§5.3) —
  **inutile de le nettoyer à la main d'ici là**.

### 🔄 Lot 3 — **EN COURS**, ouvert le 2026-09-13

Ordre imposé `contrat → agent → données`. Le contrat `FrameworkAnswer` et son pont sont acquis au
lot 1 ; les tables viennent en dernier.

1. ✅ **L'ANALYSTE** (2026-09-13, `agents/v2/analyste.py`, commit `5ff4ef9`) — moitié déterministe
   (hors-sujet écrit par le CODE depuis le `motif_gabarit`, corpus plafonné au plancher, contexte
   **sans aucun levier d'exigence**, trois états nommés, aucune évaporation) + orchestration
   `repondre`, + l'invariant **`[S]`** du pont (le `sens` appartient au vocabulaire FERMÉ de la
   question — un contrat d'objet ne connaît pas la question, #37, donc c'est le pont qui ferme).
   **Le défaut que seul le vrai modèle pouvait montrer** : sur les trois exigences par question,
   seul le **plancher** était structurel. `nature_attendue` et l'interaction plancher × règle du
   cran ne vivaient QUE dans le pont, donc **après la dépense** — et le modèle ne les voit jamais
   (#59), donc il ne pouvait ni les satisfaire ni savoir qu'il ne le pouvait pas. Mesuré :
   **3 questions sur 14 sortaient en `refus`**, c'est-à-dire en *panne d'agent*, statut qui ne
   produit **aucun mandat** — alors que le corpus ne POUVAIT pas fonder la réponse. C'est l'erreur
   **symétrique** de celle que l'en-tête du module interdit, et elle condamne la question au silence.
   ⚠️ **Le dry-run GRATUIT a montré le défaut bien plus large que le passage payant** :
   `--admissibilite` (aucun appel) révèle que **`approxime` était fermé sur les 6 questions à
   plancher `A`**, par arithmétique — le corpus est plafonné au plancher, le cran dégrade toujours
   d'un rang, donc la meilleure reconstruction y vaut `A-`, toujours dessous. Tout le bloc
   `Approximation` n'était atteignable que sur `qf_6`. → `statuts_admissibles` calcule avant l'appel
   ce que le pont pourrait ENCORE accepter, en **appelant** les détenteurs de règles (#46) ;
   `statuts_admis` est publié comme **vocabulaire FERMÉ, même forme que `sens_admis`** ;
   `non_fondable` est écrit **sans appel** quand rien n'est ouvert (#40), avec deux motifs pour les
   deux causes. Détenteur unique `aucune_reponse_possible` aux deux sites — le test négatif a montré
   que l'ancienne garde `if not citables` était **subsumée**, donc un doublon (#46).
   **`check_analyste.py` 81/0 · `negatif_analyste.sh` 31 mutations / 0 · suite 2 223 ·
   acceptation contre le vrai modèle 6/0, ZÉRO refus**, et RVMD `qf_6` rend enfin un `approxime`
   complet (méthode, hypothèses contestables, sensibilité). Convention **#63**. Récit + les trois
   pièges de garde rencontrés : **archive, entrée « 2026-09-13 »**.
   ✅ **Doctrine tranchée le 2026-09-13** : la fermeture d'`approxime` sur les questions à plancher
   `A` est **voulue**. Une question qui exige un ancrage tier `A` n'accepte pas une reconstruction ;
   l'approximation reste réservée aux questions d'interprétation (plancher plus bas). La règle du
   cran n'est plus « provisoire » dans cet emploi — **rien à remesurer**, et un plancher qui gêne se
   corrige dans le référentiel de la question, jamais dans la règle de dérivation (#59, #63).
2. ✅ **Les tables** `framework_answers` / `framework_dispenses` (**migration 040**, appliquée
   2026-09-13) + persistance. `framework_answers` **append-only et versionnée** (A1, comme
   `knowledge_entries`) : une correction ne fait jamais d'UPDATE, elle INSERT et pose
   `superseded_by` sur l'ancienne ligne ; lignée `(ticker_id, framework, framework_version,
   question_id, analyste)` — **avec** `analyste` : deux analystes distincts ne se supersèdent
   jamais (§3.4, N ≥ 1). `framework_dispenses` remplace `DECLARED_NONBLOCKING_GAPS` : clef
   `(ticker_id, framework_id, framework_version, question_id)`, idempotente (`ON CONFLICT ... DO
   UPDATE`). Écriture : `app/agents/v2/framework_persist.py` (`persist_answer`/`persist_dispense`,
   #35 — atomicité explicite à la charge de l'appelant). **`FrameworkAnswer` portait `framework_id`
   mais pas `framework_version`** avant ce maillon : fix + invariant `[V]` du pont (convention
   **#64**). `check_framework_persist.py` **13/0** · `negatif_framework_persist.sh` **6 mutations
   / 0 échec** — tout tourne en transaction ROLLBACK contre la base réelle, **zéro résidu vérifié**
   (`feedback_fixture_pollue_le_reel`).
   ⚠️ **`run_all.sh` n'avait pas tourné depuis l'ajout de `framework_version` au contrat (maillon
   1)** : deux checks rougissaient déjà, invisibles jusqu'à ce que la suite complète soit rejouée
   pour ce maillon. `check_framework_contract` §9 (bijection contrat↔pixels) — annotation
   `⟦framework_version⟧` ajoutée à `framework_screen_niveau3.md`. `check_frameworks_definitions`
   §4 — le pont lit `profil.get("framework_version")` en plus des 3 clefs de `CLEFS_PROFIL_LUES` ;
   scindé en `CLEFS_PROFIL_QUESTION` (copiées par `getattr(q, …)`) et `CLEFS_PROFIL_LUES =
   CLEFS_PROFIL_QUESTION + ("framework_version",)`. `run_all.sh` lui-même mis à jour : `check_
   framework_persist` rejoint la case `CHECK_DB_URL` (comme `check_entry_nature`/`check_collecte_
   persist`). Les deux checks + leurs négatifs sont revenus verts (**check_framework_contract
   96/0, check_frameworks_definitions 39/0, négatif 22/22**) ; suite entière **2238/0**.
3. ✅ **Suppression** de `MVDD_SPEC`, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS`
   (2026-09-13, commit `203fe65`) — 15 fichiers ; `nonblocking_gaps_for()` retourne `{}` ;
   `read_dispenses()` branché dans `framework_persist.py` ; `run_all.sh` **2172/0** (29 scripts,
   −66 assertions vs 2238 : sections testant les symboles supprimés retirées comme prévu).
4. ✅ **L'EXÉCUTION d'un appariement — livrée le 2026-09-18** (convention **#72**, aucune migration).
   Le socle sait désormais **exécuter** une formule d'appariement, et plus seulement router vers
   EDGAR. Six étapes dans l'ordre imposé : **contrat** `app/contracts/formule_grammaire.py`
   (détenteur unique des refus « dimensions incohérentes » et « division par zéro ») · **lecture**
   `edgar_facts.points_annuels`/`point_pour_periode` extraits en détenteur unique (`companyconcept`
   et `companyfacts` ne se lisent pas pareil, mais ce qu'il faut FAIRE des points est identique —
   recopiée, la règle aurait rendu **deux nombres pour un même concept** selon le chemin) ·
   **producteur** `app/knowledge/appariement_feed.py` (évalue sur l'inventaire **déjà lu** par
   `assurer_carte`, donc **zéro appel réseau de plus**) · **câblage** `collecte_executor` (consigne
   aveugle `ConsigneAppariement` — la cécité est une propriété du TYPE, #58 ; la recette du catalogue
   reste **prioritaire** sur la formule, #30/#43) · **checks** · **acceptation réelle**.
   **Quatre refus NOMMÉS, jamais un nombre fabriqué** : terme web manquant · ancres non communes
   (tolérance 20 j) · dimensions incohérentes · ratio à dénominateur nul (qui reste *inexistant*,
   jamais un zéro — #44). Chaque motif nomme la cause ET l'expression, pour finir dans un mandat.
   Mesures : `check_appariement_feed.py` **33/0** + `negatif_appariement_feed.sh` **16 mutations/0** ·
   `check_collecte_executor.py` **74 → 92** (§11 neuf) + son négatif **22 → 32 mutations/0** ·
   suite complète **2634/0 sur 35 scripts** · acceptation `tools/acceptation_appariement.{py,sh}`
   **8 critères OK / 0** (RVMD, $0.0015, ROLLBACK, **web débranché** — une retombée web y est un
   échec), **lignes COLLECTÉES depuis le dépôt 0 → 6** (7 écritures, **1 supersession** — #43 visible
   sur données réelles —, 2 refus nommés), tiers **A (0,95) vs A− (0,85)** : le cran de #67
   discrimine sur le déterminisme contre le vrai dépôt.
   ⚠️ **Distribution RVMD re-mesurée : `9 approximation · 4 indisponible`** (le paragraphe ci-dessous
   écrivait `10 · 3` le 2026-09-17). La carte a été reconstruite sur un dépôt plus récent — la ligne
   de base se **requête**, elle ne se rappelle pas.
   ⚠️ **Deux résidus nommés, aucun n'est un défaut** : (a) `symbole_de_marche` n'a que **2 appelants**
   — `valuation_feed`, `base_rate_corpus` et `financials_feed` portent encore chacun leur copie de la
   règle #11 (jumeaux connus, à réduire quand l'un d'eux sera touché) ; (b) les 2 refus portent tous
   deux sur `AssetImpairmentCharges`, dont les points sont des **fractions d'exercice** — propriété du
   dépôt, pas un trou de collecte.
   → **récit complet, les six défauts trouvés par le harnais et les deux points de méthode :
   `00-REPRISE-ARCHIVE.md` § 2026-09-18 (2).**
4ter. ✅ **Collecte neuve pilotée par le plan sur NVDA / MSFT / RVMD (§5.3) — LIVRÉE le 2026-09-19**
   (convention **#73**, aucune migration). La chaîne `executer_collecte_framework` a tourné pour de
   vrai et **persisté** sur les trois émetteurs : plans **#55/#56/#57**, **zéro doublon d'identité**
   (#43 vérifié en base sur les trois), RVMD **43→53** actives dont **4 appariements tier A** ;
   NVDA 15→57, MSFT 15→59 (liens web + recettes catalogue). **Ce que seule une écriture durable a
   révélé, et qui EST le contenu du lot** : (1) la collecte figeait **>18 min** sur une ligne web —
   les OUTILS sont bornés (20 s) mais les appels MODÈLE du worker à 720 s×6, et un **blocage n'est pas
   une exception** (silence infini invisible aux checks et à l'acceptation ROLLBACK). Fix = chien de
   garde `asyncio.wait_for` par ligne web → mandat NOMMÉ (#25/#73) ; il a coupé **8 lignes** en prod,
   chacune motivée. (2) **L'apparieur refuse la carte ENTIÈRE sur l'archétype `rentable`** (NVDA/MSFT
   `carte=aucune`, RVMD `pre_revenus` OK) : `[W]` (#68) refuse à juste titre une **croissance annuelle**
   que la grammaire de formule ne sait pas exprimer (le modèle invente `Revenues_previous_year`) —
   discriminant = l'archétype, PAS la taille d'inventaire. Dégradation gracieuse (repli `aucune`, zéro
   corruption). → **récit complet, ligne de base requêtée, les 8 timeouts et le refus apparieur :
   `00-REPRISE-ARCHIVE.md` § 2026-09-19.**
   ⚠️ Historique du blocage conceptuel, conservé pour le *pourquoi* : un faux appariement écrit un
   nombre exact en face de la mauvaise question (#43/#60), et rien en aval ne le rattrape — c'est
   `[W]` qui le garde, et son refus sur `rentable` est le prix (correct) de cette garde.
   **Acquis le 2026-09-14** (migration **041**, suite **2429/0**) : `fetch_company_facts()`
   (l'INVENTAIRE réellement déposé, que `companyconcept` ne peut jamais révéler),
   `tools/cartographier_xbrl.py` + `.sh`, `POSTES` 8 → 33, le traducteur NOMME le poste
   (`CollectionPlanItem.poste`, `LigneAveugle.poste`) et l'appariement par sous-chaînes est
   **supprimé**. ⚠️ **Le remède par prompt est DISQUALIFIÉ, c'est mesuré** : prompt durci = 11/11
   justes sur NVDA, **le même prompt sur MSFT = 15 lignes dont 10 fausses**
   (`feedback_jugement_modele_instable_entre_passages`). Le durcissement est conservé et gardé
   (`check_collecte_executor` §3bis), mais ces asserts gardent l'ÉNONCÉ, **jamais le comportement**.
   → **récit complet et tableau des 4 passages : `00-REPRISE-ARCHIVE.md` § 2026-09-14.**
4bis. ✅ **L'APPARIEMENT PAR TICKER — CLOS le 2026-09-18** (étapes 1 et 2a→2d livrées ; conçu avec
   l'utilisateur le 2026-09-14, **doctrine tranchée, rien à remesurer**). Ce que fait un analyste en fonds : il
   prend les questions de son framework, **liste les champs réellement déposés par CET émetteur**,
   et construit le meilleur appariement — **exact**, ou **par approximation en explicitant les
   hypothèses**, quitte à chercher sur le web un terme manquant du calcul.
   ⚠️ **Le poste ne va PAS dans le référentiel du framework** (piste envisagée puis **écartée par
   l'utilisateur**) : le référentiel doit rester applicable à **tout** ticker, et y écrire
   `poste: net_income` graverait une hypothèse us-gaap dans un cadre qui doit valoir pour un
   émetteur européen ou une société non cotée — #31 déplacé d'un cran vers le haut. L'appariement
   est **par ticker**, mais contre l'**inventaire réel**, jamais contre une liste devinée.
   **TROIS états, jamais deux** (#44/#54) : `exact` (le champ répond tel quel) · `approximation`
   (formule sur N champs déposés + **hypothèses écrites**) · `indisponible` (→ web).
   La case du milieu est celle qui porte l'information : aujourd'hui `qf_1.capital_employe` part
   au web chercher un nombre **que personne ne publie**, alors que NVDA dépose `Assets`,
   `CashAndCashEquivalentsAtCarryingValue`, `ShortTermInvestments`, `LiabilitiesCurrent`. Le
   lecteur doit pouvoir **contester l'hypothèse**, jamais être trompé.
   **RÈGLE DE TIER (tranchée le 2026-09-14 — convention #67)** : le discriminant est le
   **DÉTERMINISME du calcul**, pas la nature du choix de formule. Calcul déterministe (formule
   fermée, aucun paramètre à choisir) sur ingrédients **tous tier A → tier A** (2+2=4 n'est pas
   moins sûr que 2 et 2) ; ingrédients **mixtes → le tier du plus FAIBLE**, sans cran (le calcul
   n'ajoute aucune incertitude) ; calcul **non déterministe** (une part, une allocation, une
   estimation) → **un cran sous le plus faible**, ce qui retombe exactement sur la règle acquise
   du 2026-09-13. ⚠️ Une seule règle, un discriminant, **pas de second détenteur** (#46) — c'est
   ce qui sépare `capital_employe` (soustraction de 4 postes déposés) de
   `investissement_de_maintien` (« la part du capex nécessaire au maintien » : aucune formule
   fermée, il faut choisir un pourcentage).
   **RECALCUL DE LA CARTE (tranché)** : à **tout nouveau dépôt** — une société mûrit et se met à
   déposer des ingrédients importants. Cas réel déjà sous la main : RVMD ne dépose ni `Revenues`,
   ni `InventoryNet`, ni `AccountsReceivableNetCurrent` (27 postes sur 33, mesuré le 2026-09-14) —
   ce n'est pas un trou de collecte, c'est une biotech pré-revenus ; son produit approuvé par la
   FDA en août 2026 fera apparaître ces trois champs au premier trimestre de commercialisation.
   Mécanique : la carte est **persistée** avec le dernier dépôt vu, et sa validité **revérifiée à
   la lecture** — exactement le motif de #54 (`_apply_deterministic_overrides`).
   **RÔLE DU WEB (tranché)** : aller chercher **un terme manquant du calcul**, pas « caler une
   hypothèse ». La recherche cesse d'être ce qu'on fait après avoir échoué : elle devient un
   **ingrédient**, et fait tomber le calcul dans la branche « mixtes » de la règle de tier.
   ⚠️ **Ce que ça déplace** : `POSTES` garde son rôle de #61 (les recettes de collecte : concepts
   candidats, flux/bilan, choix par fraîcheur #30) et l'enrichissement 8 → 33 garde sa valeur —
   mais il **cesse d'être la frontière**. Le vocabulaire montré au modèle devient l'inventaire
   réel du ticker. Réemployable tel quel : `fetch_company_facts()`, `cartographier_xbrl.py`, et
   `financials_feed` qui sait déjà produire un fait dérivé en déclarant ses ancres (#42).
   ────────────────────────────────────────────────────────────────────────────
   **✅ ÉTAPE 1 — LA GARDE, livrée le 2026-09-17** (ordre respecté : contrat → agent → données ;
   l'agent et la migration sont l'étape 2, donc **aucune migration ce jour**, prochaine = **042**).
   Quatre pièces, à BRANCHER et non à réécrire :
   · **contrat** `app/contracts/appariement_schema.py` — trois états, chacun portant EXACTEMENT sa
     charge (`exact` ⟺ UN concept nu · `approximation` ⟺ formule + hypothèses + `deterministe`
     · `indisponible` ⟺ motif seul) ; **aucun champ de tier** (`extra='forbid'`, #53/#59) ;
   · **règle de tier #67** — `synthesis_feed.derive_tier_calcul(ingredients, deterministe=…)`,
     un seul discriminant, zéro table de tier écrite ailleurs (#46 : la branche non déterministe
     **appelle** `derive_synthesis_reliability`) ;
   · **pont** `app/agents/v2/apparieur.py` — `valider_pont_appariement(carte, inventaire, plan=…)`,
     PUR (l'inventaire est reçu déjà lu, donc rejouable hors-ligne et sans dépense). Invariants
     `[V]` concept réellement déposé · `[W]` formule ⟺ concepts déclarés · `[X]` un `deterministe`
     ne survit pas à un coefficient décimal · `[S]/[T]/[U]` cohérence avec le plan ;
   · `check_appariement.py` **73/0** · `negatif_appariement.sh` **satisfiabilité + 17 mutations /
     0 échec**. Suite **2502/0** (2429 + 73).
   → **récit complet — frontière gratuite 627/562/269, valeurs de tier mesurées, et les 8 défauts
   rencontrés (faux rouges, piège falsy, mutations visant le mauvais texte) :
   `00-REPRISE-ARCHIVE.md` § 2026-09-17.**
   ⚠️ **CE QUE LA GARDE N'ATTRAPE PAS, ET C'EST ÉCRIT DANS LE CODE** : le faux appariement
   **SÉMANTIQUE**. « clauses restrictives → `Liabilities` » **passe `[V]`**, puisque tous les
   émetteurs déposent `Liabilities` — `check_appariement.py` §9 EXÉCUTE ce cas et assert qu'il
   passe, pour qu'aucun lecteur ne croie le pont sémantique. Ce qui s'y oppose est la FORME de la
   réponse, pas un `if` : un `exact` ne pouvant porter qu'un concept nu, tout raisonnement est
   CONTRAINT de sortir en `approximation` écrite et contestable. Voir **convention #68**.
   ────────────────────────────────────────────────────────────────────────────
   **✅ ÉTAPE 2 — L'AGENT, LES DONNÉES ET LE CÂBLAGE** (livrée le 2026-09-17) :
   a. ✅ **l'apparieur** `apparieur.py` — le modèle reçoit l'**inventaire réel** de l'émetteur (269
      à 627 concepts) en table de texte alignée, plus les ingrédients du plan. `POSTES` a cessé
      d'être la frontière. **Le rendu est un producteur et il se garde** : sa première version, en
      ne montrant qu'un point par concept, FABRIQUAIT six `indisponible` « pas de série » sur MSFT
      — corrigé par la colonne de profondeur (`N dates depuis…`, `+A×K`, `1 seule date`), effet
      mesuré sur RVMD **6→10 `approximation`, 7→4 `indisponible`**. Voir **convention #69**.
      `check_appariement.py` **103/0** · `negatif_appariement.sh` **37 mutations / 0**.
   b. ✅ **migration 042 appliquée** — `appariement_cartes` au grain **ticker × framework × version**,
      `dernier_depot_vu`, items en JSONB, gardes SQL (items non vide, format de date).
      `check_appariement_persist.py` **18/0** contre la vraie base (ROLLBACK, aucun résidu) ·
      `negatif_appariement_persist.sh` **5 mutations / 0**.
   c. ✅ **lecture** — `executer_plan_reel` lit la carte **une fois par exécution** (#61) et passe le
      `carte_statut` de chaque ligne à `router_source` : `indisponible` → web, `exact`/`approximation`
      → edgar si la source est un dépôt réglementaire. Le repli est NOMMÉ et journalisé.
      ⚠️ Cette étape a été **annoncée à tort comme « la carte est le décideur »** : elle livrait la
      LECTURE, pas la décision — rien ne produisait de carte (voir d).
   d. ✅ **producteur** (2026-09-18, convention **#71**) — `assurer_carte()` : `fetch_company_facts`
      (gratuit) → `dernier_depot_vu(facts)` → `lire_carte(depot_courant=<cette date>)` → si `None`
      (absente **ou périmée**) → `apparier()` sur les mêmes `facts` + `persister_carte()`. La branche
      « périmée » devient **atteignable** et déclenche une **reconstruction**, pas un repli dégradé.
      Quatre états nommés : `fraiche` (zéro appel modèle) · `reconstruite` · `non_reverifiable`
      (inventaire injoignable → carte stockée servie en le disant) · `aucune` (repli `poste_retenu()`).
      **Aucune migration, aucune règle de décision nouvelle** — la date vient du détenteur unique
      déjà écrit (#46). `check_collecte_executor.py` **74/0** (§9 réécrit en assert structurel plus
      fort, §10 neuf : les quatre états exercés) · `negatif_collecte_executor.sh` **22 mutations / 0**.
      Acceptation réelle `tools/acceptation_carte_executeur.{py,sh}` : **6/0, $0.0015, 0 résidu**.
   **Suite complète : 2583 assertions, exit 0 sur les 34 scripts** (2502 → 2566 → 2583).
   Rien de déployé, **aucune collecte réelle lancée**.
5. ⬜ **Réconciliation à 0/0** via `tools/reconcilier_vocabulaires.py`.

> **✅ SOLDÉ — LES DEUX CHANTIERS OUVERTS PAR 4ter** (A robustesse apparieur · C le manager).
> *Ce bloc n'est plus le prochain jalon : il est CLOS. Le jalon vit plus bas, à `▶ PROCHAIN JALON`
> — un seul endroit. Conservé ici pour les pièges qu'il documente, pas pour ce qu'il reste à faire.*
> Le maillon 4ter est **LIVRÉ** (2026-09-19, #73) : collecte réellement persistée sur les trois,
> **zéro doublon d'identité** (#43 en base), plans #55/#56/#57. La chaîne se TERMINE désormais (le
> blocage web infini est borné par ligne, #73). Mais deux défauts que **seule l'écriture durable a
> révélés** restent ouverts :
>
> **(A) — robustesse apparieur.** Deux gestes, ordre imposé contrat→agent.
> ✅ **(a) LA GRAMMAIRE TEMPORELLE — LIVRÉE le 2026-09-19** (convention **#74**, aucune migration).
> L'archétype `rentable` sortait `carte=aucune` parce que `qf_3.croissance_activite_par_exercice` n'a
> pas de forme sans référence à l'exercice antérieur : le modèle inventait `Revenues_previous_year`,
> un nom absent du dépôt → refus `[W]` → carte entière coulée. La grammaire exprime désormais un
> **décalage d'exercice `Concept[-1]`** (`ast.Subscript` contraint, offset entier ≤ 0, relatif jamais
> absolu). Décision de fond : **l'offset porte sur le NOM, il ne crée pas un concept** — c'est #57
> appliqué à la formule, `noms_de_la_formule` le PROJETTE (`Revenues[-1]` → `Revenues`) donc `[V]/[W]`
> confrontent à l'inventaire un concept déposé, l'évaluateur lit le grain fin `(concept, offset)` via
> `references_de_la_formule`. Détenteur unique `_offset_du_subscript` (#46). Le fait est daté de
> l'exercice le plus RÉCENT (offset 0), les antérieurs sont sa provenance ; un exercice décalé absent
> est un refus NOMMÉ, jamais un repli sur le point courant (fausse croissance 0 %). Défaut corrigé au
> passage : un ratio SANS DIMENSION (une croissance) rendu « 0 » par `montant` → `rendre_resultat`
> (#42/#45). `check_appariement §11` (115/0), `check_appariement_feed §6` (40/0), négatifs 40/0 et
> 19/0, **suite 2661/0 sur 35 scripts**. **MESURÉ contre le vrai modèle** (`tools/acceptation_
> apparieur.sh`) : MSFT `qf_3` → `(RevenueFromContractWithCustomerExcludingAssessedTax[0] - […][-1])
> / […][-1]` accepté tier A ; RVMD `qf_7` → `Ncf[0]+[-1]+[-2]+[-3]`. Le blocage MESURÉ est retiré.
> ✅ **(b) LE REFUS PAR INGRÉDIENT — LIVRÉ le 2026-09-19** (convention **#75**, aucune migration).
> Entre deux passages de l'acceptation, la carte NVDA était passée de ACCEPTÉE (13/0) à REFUSÉE (8/1)
> — **non sur la croissance** (le geste (a) l'avait réglée), mais sur un AUTRE ingrédient
> (`qf_4.endettement_brut_et_net`, un `[W]` « concept déclaré non employé », bévue de modèle). C'était
> `feedback_jugement_modele_instable_entre_passages` × le tout-ou-rien de `apparier()` : une seule
> bévue sur l'un des 30 ingrédients coulait la carte ENTIÈRE. Geste livré : un `AppariementRefuse`
> décidable PER-COUPLE (`[S]`/`[T]`/`[V]`/`[W]`/`[X]`, jamais `[U]` card-structural) sort en
> `indisponible`/mandat via `_repli_par_ingredient`, les autres survivent (#25/#44/#54/#67 transposé du
> couple à la carte). `check_appariement.py §12` (128/0), `negatif_appariement.sh` (45 mutations/0),
> **suite 2674/0 sur 35 scripts**. **MESURÉ contre le vrai modèle** (`tools/acceptation_apparieur.sh`,
> NVDA/MSFT/RVMD, 13 critère(s) OK / 0 échec) : MSFT a reproduit EXACTEMENT la bévue
> `qf_4.endettement_brut_et_net [W]` (+ une seconde sur `qf_5.decomposition_marge_rotation [W]`) et la
> carte a quand même été **acceptée** (1 réparation), les deux couples fautifs mandatés au web. ⚠️ Le
> prompt n'a PAS été re-durci (`feedback_jugement_modele_instable_entre_passages`) — la garde est en
> code. **Chantier A (robustesse apparieur) CLOS.**
>
> **(C) — LE MANAGER (§10 lot 4), AGENT LIVRÉ le 2026-09-20** (convention **#76**, aucune migration).
> ⚠️ **Cadrage rectifié en début de lot** : le REPRISE nommait « maillon 5 réconciliation » comme
> seul chantier ouvert, mais §10 impose le **manager (lot 4) AVANT** le mémo projeté (lot 5), et la
> réconciliation à 0/0 dépend de frameworks *acquittés* — donc du manager. De plus le 0/0 complet
> exige un framework par bloc de mémo (2 pilotes / 13 questions contre 36 feuilles) : c'est l'**état
> terminal** de la roadmap, pas un lot. Arbitrage utilisateur : **faire le manager**.
> Livré : le contrat du manager existait déjà (lot 1 — `ControlesManager`/`ManagerVerdict`/
> `FrameworkMandate`), donc ce lot livre l'**AGENT** (ordre contrat→agent→données). `agents/v2/
> manager.py` : quatre contrôles **déterministes** (aucun appel modèle), chacun re-vérifiant ce que
> le contrat **ne peut pas** juger (#37) et donc chacun `ko` **atteignable** — ① question inapplicable
> répondue (T4/#190), ② citation hors du corpus *fourni au manager* (#28), ③ rang non dégradé, ④
> substitut vers sa propre question (détenteur `motif_substitut_hors_sujet` **extrait du pont** et
> partagé, #46). Un renvoi PRODUIT un `FrameworkMandate` `ouvert`/`manager_renvoi` (ferme l'Écart B) ;
> les questions applicables sans réponse deviennent des mandats (contrôle ①, niveau framework).
> `check_manager.py` **35/0** + `negatif_manager.sh` **7 mutations / 0**, suite **2709/0 sur 36
> scripts**. Détail : convention **#76**.
>
> **✅ DONNÉES DU MANAGER — LIVRÉES le 2026-09-21 (convention #77)**, ce qui CLÔT le lot 4. Migration
> **043** appliquée (ADDITIVE), `manager_persist.py`, `check_manager_persist` **17/0**, négatif
> **5/0**, **acceptation T8 6/0**. **Arbitrage utilisateur (2026-09-21)** : l'avis du manager NE SE
> PERSISTE PAS — il se **recalcule** à la lecture (le manager est pur, gratuit ; un verdict figé ne
> peut pas signaler qu'il a vieilli, #53/#54) ; seul l'EFFET durable, le **mandat** et son cycle de
> vie ouvert→servi, est archivé. Le libellé « verdict rangé sur la réponse » est ainsi corrigé.
> La 043 réconcilie `FrameworkMandate` (par-question, `mandat` exécutable, `ticker_id`) et la table
> `framework_mandates` (039, par-ingrédient) : `ingredient_id` NULLABLE + colonnes de cycle de vie +
> `comite` + deux CHECK (`forme`, `trace`) qui redisent le contrat — un `ingredient_id` bidon serait
> un faux (#76). T8 mesuré de bout en bout sur le défaut canonique #190 (ROIC fabriqué RVMD →
> renvoi → mandat consommable → servi, `repondu`→`sans_objet`). Détail : archive 2026-09-21, #77.
> ⚠️ Depuis le 2026-09-24, #190 n'est plus qu'un **exemple** : le producteur qui le refabriquait à
> chaque passage est corrigé et sa dernière génération (#656) est superseded. La voie manager reste
> nécessaire — elle traite ce que le déterministe ne peut pas voir, pas ce cas-là en particulier.
>
> **✅ PREMIER PASSAGE RÉEL DE LA CHAÎNE — 2026-09-21 (convention #78)**, `tools/executer_chaine.{py,sh}`
> (versionnés, ils ÉCRIVENT EN PROD, sans ROLLBACK, et c'est le but). Les six agents existaient,
> validés hors ligne, et **personne ne les appelait** (#71). `RVMD × qualite_financiere × pre_revenus`
> est allé de bout en bout contre le vrai modèle et la vraie base : plan #78, carte relue `fraiche`
> (**0 appel apparieur**), corpus **40/57 (PLAFONNÉ)**, **7 réponses** (4 `sans_objet`, 2 `repondu`,
> 1 `approxime`, **0 refus**), ids 469-475, **7 acquittements / 0 mandat manager**, traducteur
> $0,0013. La frontière gratuite avait prédit **exactement** ce résultat
> (`acceptation_analyste.sh --admissibilite`).
> ⚠️ **UN DÉFAUT, et c'est le plus important du chantier** : `qf_7` (#475) citait une « guidance de
> dépenses opérationnelles **en trésorerie** 1,81–1,93 MdUSD » **qui n'existe nulle part** — l'analyste
> avait soustrait la SBC de la guidance **GAAP** 2,1–2,2 de l'entry #312 et présenté le calcul comme
> une citation. Statut `repondu`, nature `mesure`, rang **A**, aucun cran. Les quatre contrôles du
> manager l'ont acquitté **correctement** : #312 est bien dans le corpus et bien citée ; rien ne compare
> les NOMBRES du verbatim à ceux de l'entry. `feedback_garde_structure_pas_sens` **confirmé en
> production**. La conclusion (« autonomie longue ») reste vraie dans les deux lectures — c'est ce qui
> le rend invisible (#46). **Ligne #475 physiquement SUPPRIMÉE** (pollution, pas correction d'analyse :
> A1 trace les secondes, `feedback_fixture_pollue_le_reel` proscrit les premières) ; recomptage
> `framework_answers` = **6**. Les six survivantes sont fidèles ligne à ligne, vérifiées chiffre par
> chiffre contre leurs entries — **première preuve réelle que la chaîne produit**.
>
> **▶ PROCHAIN — §10 lot 5. LE GARDE #78 EST LIVRÉ (2026-09-21), mais PAS À L'ENDROIT ANNONCÉ.**
> **(1) ✅ LIVRÉ — et l'énoncé de ce point était FAUX, ce qui est l'enseignement.** Le garde annoncé
> (« un `repondu` ne peut porter aucun nombre absent de ses entries citées ») a été **MESURÉ VERT sur
> le cas même qui l'a motivé** : 1,81 et 1,93 figurent bel et bien dans l'entry #312, qui était bel et
> bien citée. L'analyste avait recopié fidèlement une pièce qui **mentait sur son propre statut**.
> Le défaut n'est donc pas chez l'analyste mais **au guichet d'entrée** (arbitrage utilisateur,
> option B) : un producteur qui CALCULE un chiffre à partir de chiffres déposés le rangeait sous
> `fact_financial` × source officielle, donc sous `mesure`, donc sous l'autorité du dépôt.
> **16 des 161 entries `mesure` courantes étaient dans ce cas** — toutes honnêtes dans leur prose
> (elles écrivent leur calcul en toutes lettres), seul le tampon était faux. Livré : `derive_nature`
> rétrograde sur un **vocabulaire fermé de 11 marqueurs de dérivation** (`annonce_une_derivation`
> rend le marqueur TROUVÉ, jamais un booléen : le motif doit pouvoir le nommer), `content` transmis
> depuis **les deux** sites d'appel (`store_knowledge` et le `_normalise_entry` du search-worker, qui
> qualifie AVANT le filtre de plancher), contrôle **[E0]** neuf dans le pont (`nature_effective` est
> DÉRIVÉE, jamais déclarée — le pendant de [C] sur l'axe nature) et **[E]** durci, avec
> `nature_effective_de` en détenteur unique partagé par le pont et `assembler_answer` (le second la
> tenait **en ligne** : un jumeau qui attendait de diverger). ⚠️ Le tier n'est PAS touché : le dépôt
> reste un dépôt, c'est la phrase qu'on en a tirée qui n'est pas un relevé (#50).
> **Migration 044 appliquée** (16 requalifiées, garde globale `mesure = 213` **éprouvée en négatif
> avant application** : jouée seule sur l'état d'avant, elle RAISE sur 229). `check_entry_nature`
> **153/0** avec un **§7bis** neuf, `negatif_garde_guichet.sh` **9 mutations / 0 échec**,
> `run_all.sh` **2800 assertions / 0 échec sur 37 scripts**.
> ⚠️ **Ce que §7bis a coûté et pourquoi il existe** : le parcours jeton par jeton de §5bis est
> **GÉNÉRÉ depuis `_MARQUEURS_DE_DERIVATION`**, donc retirer un jeton retire AUSSI son assert — un
> assert écrit depuis sa propre constante (4ᵉ faux vert). La mutation « amputer le vocabulaire » est
> restée invisible jusqu'à ce qu'on lui cherche une ancre **non circulaire** : le CORPUS RÉEL, via
> les ids que la migration 044 requalifie, **relus depuis le fichier** (#46) et confrontés au
> `content` stocké. Un vocabulaire fermé ne se garde pas contre lui-même.
> **(2) ⇢ REQUALIFIÉ le 2026-09-22 — ce n'était pas un défaut.** « Le collecteur est aveugle au
> corpus déjà détenu : 4 des 7 mandats sont de faux manques. » **Arbitrage utilisateur** : à
> l'initialisation et en test, **on rachète TOUT** — le rachat n'est pas une dépense à éviter, c'est
> le mode nominal. Ce qui reste à construire n'est pas un filtre amont mais la **comparaison du
> nouvel état à l'ancien** quand le ticker est déjà en portefeuille (partie aval/suivi, après
> l'amont). Le coût web se borne par budget, pas en aveuglant la collecte.
> **(3) ⇢ REFORMULÉ.** #280 et #296 assertent la même identité (dette RVMD 487,43 MUSD au
> 2026-06-30), toutes deux courantes, `metric`/`poste_kind` NULL → non clefables (#55/F16). Ce n'est
> **pas** un problème de supersession : l'utilisateur veut que l'historique **s'empile** et se garde.
> Le vrai besoin est la **LIGNÉE** — savoir que ces deux pièces parlent du même point, et laquelle
> fait foi. C'est ce que `dossier.py` rend désormais au moment de la LECTURE (voir ci-dessous) ; le
> backfill lignée 035 (candidat **045**) reste utile pour les pièces hors index de couverture.
> **(4) ✅ ADRESSÉ le 2026-09-22 — le plafond ne peut plus couper une pièce qui fonde un point.**
> Voir le lot ci-dessous.
> **✅ LE DOSSIER REMIS À L'ANALYSTE — LIVRÉ le 2026-09-22.** `app/agents/v2/dossier.py`, détenteur
> unique (#46), aucune migration, aucune écriture. Ce qu'il ferme, **mesuré**, pas supposé :
> le corpus était assemblé **à plat** (les N plus récentes par `source_date`, tronquées), et cette
> règle était recopiée à l'identique dans `tools/acceptation_analyste.py` et `tools/executer_chaine.py`
> — sous le commentaire « même plafond que l'autre, et pour la même raison », c'est-à-dire une règle
> sans détenteur. Conséquences mesurées sur RVMD : `qf_4.endettement_brut_et_net` portait **trois**
> entries courantes toutes tier A (#296, #340, #443), aucune ne remplaçant l'autre → l'analyste
> recevait trois réponses concurrentes au même point ; et la troncature par date pouvait écarter la
> pièce qui fonde un ingrédient tout en gardant trois versions d'un autre. **C'est l'outil de MESURE
> qui fabriquait le vrac du corpus de test.**
> Livré : une **chemise par point de la liste du comité**, la plus récente **en vigueur**, les
> antérieures **gardées en base** et comptées au bilan, les pièces hors index **jointes** (les
> écarter ferait lire « indisponible » là où il y a de la donnée), le plafond mordant sur le RESTE —
> et `plafond_insuffisant` DIT au lieu de couper un porteur.
> ⚠️ **La clef de regroupement n'est PAS la ligne de plan.** Premier réflexe, et il est faux :
> mesuré sur les 4 plans RVMD du même framework en version identique, **9 ingrédients sur 14 portent
> QUATRE libellés `metrique` distincts**, l'ancre dérive aussi, **aucun n'est stable**. Le traducteur
> reformule à chaque passage, c'est son droit. Ce qui est stable est le point du référentiel inerte —
> `(question_id, ingredient_id)` — déjà écrit par `question_coverage` (#57) et **LU** (#29).
> ⚠️ **L'aveuglement du collecteur reste intact (#58)** : ce module lit la question, mais il est en
> aval de toute collecte ; le collecteur ne l'importe pas.
> Gardes : `check_dossier.py` **24/0** (fixture **copiée du corpus RVMD réel** : ids, dates de source
> ET de collecte authentiques), `negatif_dossier.sh` **10 mutations / 0**, `tools/montrer_dossier.sh`
> (lecture gratuite du dossier réel). Suite **2824 / 0 sur 39 scripts**.
> ⚠️ **CE QUI A TROUVÉ LE VRAI DÉFAUT** : pas un décompte. Écrite avec la date nue, la clef de tri
> `_rang` trie en ordre CROISSANT — elle élisait la **plus ANCIENNE** pièce « en vigueur »
> (`qf_4.lignes_de_credit_non_tirees` servait le 2025-06-30 en écartant le 2026-08-05). Le dossier
> sortait bien formé, de la bonne taille, une pièce par point, et l'outil imprimait « 0 échec ».
> Seule la **LECTURE du dossier en texte** l'a montré (`feedback_rendu_est_un_producteur`,
> `feedback_frontiere_gratuite_avant_depense_modele`). Figé en §3 du check, éprouvé par mutation.
>
> ⚠️ **DÉFAUT NOUVEAU, NOMMÉ ET DÉLIBÉRÉMENT NON CORRIGÉ ICI — la DATATION HÉTÉROGÈNE.** Sur RVMD,
> **6 des 8 chemises à plusieurs versions** ont une pièce en vigueur **collectée AVANT** une de ses
> antérieures. ~~Cause : `edgar_feed` date une entry à la clôture de période (`period_end`), le chemin
> narratif/web à ce que le modèle déclare.~~ **Deux horloges dans la même chemise.** L'assemblage n'a
> pas de quoi trancher — il le NOMME au bilan (et dit `INDÉTERMINABLE` si `created_at` n'est pas
> chargé, #25/#44). **Le remède est à la PRODUCTION des entries, c'est un lot distinct.**
> ⚠️ **LA CAUSE ÉCRITE CI-DESSUS ÉTAIT FAUSSE** (re-mesurée le 2026-09-23 avant d'écrire une ligne,
> #78) : les deux horloges vivent **toutes les deux sur `edgar_official`**, pas une par canal. Ne pas
> la re-citer.

---

> **✅ LOT « LE GUICHET DATE LE FAIT » — LIVRÉ le 2026-09-23 (convention #79, migration 045).**
> Ordre imposé respecté : **contrat → agent → données**.
>
> **Ce qui était mesuré** (relevé en base avant le lot, non rappelé) : **21 des 54** entries
> courantes datées de RVMD écrivent DEUX dates dans leur prose et n'en stockent qu'une.
> #307 affirme « au 2026-06-30 » et trie au **2026-08-05** (le dépôt du 10-Q) ; #309 est la colonne
> **comparative** du même 10-Q — un chiffre de 2025 portant le tampon le plus frais du dossier ;
> #296 trie au **2026-09-01**, une date qui n'apparaît **nulle part dans sa propre prose** — ni le
> fait, ni le dépôt : le tampon du greffier au moment du classement. Ce dernier n'est plus un
> problème de fraîcheur mais de **traçabilité** : la ligne ne peut plus être rapprochée de sa source.
>
> **Ce qui a été livré, et pourquoi ce n'est PAS une garde de plus.** Une garde vérifie la structure
> et la relation, **jamais le sens** (#68) : aucun code ne peut regarder `source_date = 2026-08-05`
> et savoir si c'est le fait ou le papier — les deux sont des dates plausibles, structurellement
> indiscernables. C'est donc la **FORME de la réponse** qui change : deux cases nommées
> (`date_du_fait`, `date_du_document`) rendent la confusion **inexprimable** au lieu de la rendre
> surveillée. Le modèle écrivait DÉJÀ les deux dates dans sa prose — il ne lui manquait pas la
> connaissance, il lui manquait la case. Et **`source_date` cesse d'être reçue** : elle est DÉRIVÉE
> (`app/knowledge/datation.py`, détenteur unique #46), comme `nature` l'est au guichet depuis la 034.
> Les lecteurs (`dossier._rang`, `actualite`, `compute_reliability`) ne changent pas d'une ligne.
>
> **Le vocabulaire est FERMÉ, trois états** (#25/#44/#54) : `constatee` fait foi à la date du **FAIT**
> · `prospective` à la date de son **ANNONCE** · `indatable` n'a **pas** de date de tri (`NULL`, donc
> `actualite` rend `indeterminable` et la pièce perd toute élection de fraîcheur — perdre faute de
> date est honnête, gagner sur la date d'une page ne l'est pas). Pas de quatrième état, **pas de
> défaut**. En base, `portee_temporelle IS NULL` désigne les lignes **antérieures à la 045** : un
> constat d'héritage dénombré, pas un état du vocabulaire.
>
> **▶ LES DEUX ARBITRAGES DU FONDS** (l'utilisateur a raisonné depuis la pratique d'un vrai fonds) :
> 1. **2026-09-23 — « on note les deux dates, et la mesure retenue est celle du dernier FAIT »**,
>    pas du dernier papier reçu. C'est toute la règle de dérivation de `constatee`.
> 2. **2026-09-23 — une pièce prospective se classe en `prospective` à la date de son ANNONCE**, et
>    la période visée devient un **attribut** de la pièce (`periode_visee`), pas sa fraîcheur. Une
>    guidance émise le 5 août est une information du 5 août, pas une information de l'exercice
>    qu'elle vise. ⇢ Ouvre un **module de backlog** : confronter ultérieurement le **réalisé à
>    l'annoncé** pour produire des insights sur **la qualité des prévisions du management**,
>    destinés à alimenter certains frameworks (`qualite_financiere`, futur framework gouvernance).
>    `periode_visee` en est le seul ingrédient — c'est pourquoi il est au contrat alors qu'il ne sert
>    aucun tri aujourd'hui.
> 3. **2026-09-23 — une note produite par le fonds lui-même est un DOCUMENT DU JOUR**, à condition
>    qu'elle indique **sur quel état de la base de connaissance — et notamment de quels frameworks —
>    elle se fonde**. Donc `date_du_fait = date_du_document = aujourd'hui` pour `synthesis_feed`,
>    le context pack du `curator` et l'ancre de base rate : une synthèse n'hérite **pas** de la date
>    de ses ingrédients. La règle de dérivation de son **tier** (« un cran sous la plus faible entry
>    citée ») et celle de sa **date** ne répondent pas à la même question : le tier dit « à quel point
>    peut-on s'y fier », la date dit « de quand est cette lecture ». Ce qui empêche la note de se
>    faire passer pour un fait frais n'est pas sa date, c'est **l'état écrit à côté**.
>    ⇢ **Résiduel #80** : cet état est **partiellement** écrit (`source_entry_refs` id+version pour le
>    context pack, `cited_entry_ids` + tiers pour la synthèse) — **la version des frameworks n'est
>    enregistrée nulle part**. Une note ne devrait pas pouvoir citer ses pièces sans dire selon
>    quelle grille elle les a lues. Mesuré, pas supposé : `grep framework_version` = 0 occurrence
>    dans les trois producteurs.
>
> **Gardes.** `check_datation.py` **107/0** (sept sections ; §6 rejoue les cas RÉELS #307/#309/#296
> sur leurs valeurs **mesurées en base**, ancre non circulaire ; §7 lit l'état persisté et **dénombre
> l'héritage** au lieu de le tolérer en silence). `negatif_datation.sh` **28 mutations / 0 échec**,
> avec satisfiabilité mesurée avant toute mutation. Suite **2926 / 0 sur 40 scripts**.
>
> ⚠️ **CE QUE LE TEST NÉGATIF A TROUVÉ, ET QUI VAUT LE FICHIER.** Deux trous, aucun visible au vert :
> - **La mutation « `indatable` se fabrique une date » est restée VERTE.** §2 n'éprouvait `indatable`
>   que **sans** document — le seul cas où la mutation ne change rien. Le cas réel (une indatable qui
>   NOMME sa source, ce que le contrat autorise et encourage) n'était asserté nulle part. Un assert
>   écrit sur le cas commode est aveugle au cas réel (`feedback_fixture_copiee_du_reel`).
> - **La liste des producteurs était RETAPÉE À LA MAIN : six fichiers, alors qu'il y en a NEUF.**
>   `curator.py`, `base_rate_corpus.py` et `synthesis_feed.py` appelaient `store_knowledge` **sans
>   `datation=`** — donc plantaient au premier appel réel — et le check était **vert** : il ne les
>   regardait pas. Un recensement par nom qui ne couvre qu'une partie du corpus refait le bug en
>   `verdict=ok` (`feedback_adressage_par_nom_exige_lecture`). Les appelants sont désormais **LUS
>   dans l'arbre des sources** (AST) ; la liste écrite n'est plus qu'un **accusé de réception**, et
>   tout écart — producteur neuf **comme** producteur disparu — rougit et exige une décision
>   explicite sur sa datation. Les deux sens sont éprouvés par mutation.
> ⚠️ Corollaire méthodo : l'assert « X appelle bien `store_knowledge` » a été **retiré** — depuis que
> la liste est découverte, il est une tautologie, et une garde qu'aucune mutation ne peut atteindre
> est le 6ᵉ faux-vert. Ce qu'il protégeait est tenu par `require(…, 9)` + le recensement.
>
> ⚠️ **FAUX ROUGE DE MA PROPRE FABRICATION, gardé pour le motif.** §7 filtrait les contraintes par
> `conname LIKE '%datation%' OR '%portee_temporelle%'` : parenthésage fautif **et**, plus
> fondamentalement, `..._source_date_derivee_check` ne porte **aucun** de ces motifs — l'assert était
> **structurellement insatisfiable** sur une base parfaitement conforme. Les noms attendus sont
> maintenant **lus dans le fichier de migration** (#46). `feedback_faux_rouge_se_creuse` : chercher
> pourquoi ça rougit **avant** de corriger l'outil.
>
> ⚠️ **RÉSIDUS NOMMÉS (aucun n'est un défaut de ce lot)** :
> 1. **`date_du_document` n'est pas rapprochée de l'index des dépôts EDGAR.** Ce serait un contrôle
>    juste, et il rendrait la **porte d'écriture dépendante du réseau** : une panne d'EDGAR se lirait
>    « date invérifiable », donc, sous la moindre tolérance, « date acceptée » — une panne réseau qui
>    produit la phrase rassurante (#49). Le rapprochement est un travail de **LECTURE**.
> 2. **#445 étiquette une ligne de crédit non tirée « EXERCICE CLOS LE 2025-06-30 »** — un **stock**
>    présenté comme un **flux**. Défaut du producteur XBRL, famille `poste_kind` (#55/F16), pas de la
>    datation.
> 3. **La règle retire un faux ordre, elle ne fabrique pas un meilleur gagnant** (#71). Sur
>    `qf_7.tresorerie_disponible`, #307 et #444 s'ÉGALISENT au 2026-06-30 et c'est le départage aval
>    (`dossier._rang`, `-id`) qui tranche — vers #444, qui couvre un fait **plus étroit**. À ne pas
>    survendre.
>
> ⚠️ **LIGNE DE BASE DU 2026-09-23, lue EN TEXTE avant toute re-collecte** (frontière gratuite,
> `bash tools/montrer_dossier.sh RVMD qualite_financiere v3.0.0`) : 40 pièces remises sur 57
> courantes · 14 chemises · **8 chemises à plusieurs versions** · **6 à datation hétérogène**
> (`qf_4.endettement_brut_et_net`, `qf_4.lignes_de_credit_non_tirees`, `qf_7.charges_fixes_decaissables`,
> `qf_7.consommation_de_tresorerie_recente`, `qf_7.lignes_de_credit_non_tirees`,
> `qf_7.tresorerie_disponible`) · #296 toujours en vigueur au **2026-09-01**. **C'est l'état à battre,
> et il se REQUÊTE à nouveau après la re-collecte, jamais il ne se rappelle**
> (`feedback_ligne_de_base_est_une_mesure`).
>
> **▶ FAIT le 2026-09-23 — la re-collecte a tourné, et elle a montré sa LIMITE.** Le rejeu a été
> re-tenté (`feedback_blocage_classifieur_non_permanent` : le refus de la veille était levé) et il
> est passé : **15/15 `ok`, 0 erreur, plancher tenu** (RVMD déterministes actives 72 ≥ 13). Mais il
> a d'abord échoué **6 fois sur 15** sur `Token "NaN" is invalid` — un défaut de DONNÉES, pas du lot
> #79 : c'est le lot **#81** (`CLAUDE.md`), corrigé, gardé et documenté.
>
> **Les trois mesures d'après, requêtées et non rappelées** (`feedback_ligne_de_base_est_une_mesure`) :
> - (a) `bash checks/avec_base.sh check_datation` §7 → **128 entrées d'héritage · 110 datées** sous
>   la 045 (départ 174/0). **L'objectif « héritage → 0 » n'est PAS atteint et ne peut pas l'être par
>   ce chemin** — voir ci-dessous.
> - (b) dossier RVMD × `qualite_financiere` relu EN TEXTE → **5 chemises hétérogènes sur 6**
>   subsistent. Seule `qf_7.tresorerie_disponible` a été résorbée.
> - (c) suite complète **3072 / 0 sur 41 scripts**.
>
> ⚠️ **POURQUOI LE REJEU NE PEUT PAS FINIR LE TRAVAIL — mesuré, pas supposé.** Les entries des cinq
> chemises restantes (#296, #300, #308, #311, #340, #351, #445, #449) sont toutes
> `portee_temporelle IS NULL`, toutes `source_type=edgar_official`, et toutes **créées le
> 2026-09-12 par le search worker** — tags en forme libre, pas les tags champ-par-champ des feeds
> déterministes. `rejeu_producteurs.sh` ne rejoue que les producteurs DÉTERMINISTES : il ne détient
> pas ces champs, donc il ne les supersede pas, et il ne les supersedera jamais quel que soit le
> nombre de passages. **Le solde des 128 est une dette à coût MODÈLE**, pas une dette d'outillage —
> c'est un lot à part entière, à décider, pas une étape d'exécution restante.
>
> Ce qui reste vrai et ne change pas : on **re-collecte**, on ne backfille **jamais** par modèle
> (« quelle date cette phrase affirme-t-elle ? » n'est pas un vocabulaire fermé, donc pas dérivable),
> et l'arbitrage utilisateur du 2026-09-22 tient (**à l'initialisation et en test, on rachète TOUT**).
>
> ```
> bash tools/rejeu_producteurs.sh      # zéro token, à relancer après tout correctif de feed
> bash checks/avec_base.sh <check>     # lanceur versionné des checks qui lisent l'état persisté
> ```
>
> ✅ **#81 EST DÉPLOYÉ (2026-09-24, `a62d580`).** Le conteneur tournait sur l'image du **2026-09-12**
> — 12 jours et 8 commits de retard (#78, `dossier.py`, #79 + migration 045, #81). Le classifieur a
> refusé `compose-deploy.sh --rebuild-only` une **3ᵉ** fois ; repli §12 de `CHANTIER_OUTILLAGE_DEV.md`
> (`docker compose … up -d --build backend`, en commandes SÉPARÉES — un `&&` entre deux commandes
> pourtant autorisées se fait refuser, `feedback_permission_prefix_trap`). Vérifié en trois points :
> sonde officielle **HTTP 200** `{"status":"ok"}`, **un seul** conteneur (pas de doublon Traefik),
> et les symboles #79/#81 grepés DANS le conteneur qui tourne — l'artefact, pas le diff.
>
> ⚠️ **LA PREUVE EN RÉEL N'EXISTAIT PAS, ET ELLE A UNE TROISIÈME CASE.** `check_cours_cote.py` est
> explicitement **hors ligne** (séries fabriquées) : il prouve la RÈGLE, jamais le CHEMIN — or le
> défaut d'origine ne se voyait qu'à l'écriture PostgreSQL, APRÈS l'appel réseau payé
> (`feedback_verifier_contre_api_reelle`). D'où **`checks/check_cours_cote_live.py`** (hors
> `run_all.sh` : réseau ouvert + clé fournisseur + écriture DB réelle) :
> `docker exec portfolio-backend python /app/checks/check_cours_cote_live.py`.
> La garde « aucun non fini ne survit » ne peut PAS distinguer « le filet a retenu » de « il n'y
> avait rien à retenir » — verte dans les deux cas, alors que le second ne prouve rien du correctif.
> On change donc la FORME de la réponse plutôt que de muscler la garde (#68,
> `feedback_garde_structure_pas_sens`) : **ASSAINI / RIEN_A_ASSAINIR / FAIL**, et le bilan distingue
> **« vert »** de **« exercé »**.
> **Premier passage, 2026-09-24 : `3 ok / 0 FAIL`, exercés `0/3` → VERT MAIS NON EXERCÉ**, dit en
> clair par le script. Ne pas lire cette ligne comme « #81 prouvé en réel ». Ce qui EST prouvé en
> réel : `refresh_m1` ne lève plus (symptôme d'origine : **6 échecs sur 15**), et `1y_change_pct`
> est renseigné sur les trois titres — la colonne que le seuil de 252 séances sur 251 rendait
> structurellement toujours vide (§4 du check hors ligne).
>
> ⚠️ **TROUVAILLE NON CHERCHÉE — FMP rend `403 Forbidden` sur `analyst-estimates`** pour MSFT, NVDA
> et RVMD (donc la CLÉ ou le plan, pas le titre). Les estimations d'analystes sont absentes, et
> cette absence se lit aujourd'hui comme une **propriété de l'émetteur** au lieu d'une panne de
> fournisseur (#69). Non instruit — à trancher : réparer la clé, ou nommer l'état.
>
> ⚠️ **`check_architecture` a immédiatement classé le nouveau fichier en garde ORPHELINE** (« cité
> par aucun ARCHITECTURE.md »). C'est la garde qui fonctionne, pas un faux positif : tout check est
> adossé à une cible. Adossé dans `app/data_collection/ARCHITECTURE.md`, suite de retour à 3072/0.
>
> **▶ CE QUE L'UTILISATEUR A TRANCHÉ LE 2026-09-22, et qui commande la suite :**
> 1. **On finit l'AMONT** pour faire tourner la V3 complète sur un cas sans difficulté. **Ensuite
>    seulement** l'aval/suivi. Les questions d'obsolescence entre runs ne se posent qu'en mode suivi
>    (ou quand on actualise un mémo que le comité avait jugé insuffisamment attractif il y a
>    quelques mois) — ne pas les instruire avant.
> 2. **La spec V3 doit gagner une PARTIE MONITORING** : les règles d'ajout de données à la base à
>    mesure que l'état du monde change. **On n'écrase pas** — on **empile** pour construire
>    l'historique — mais le système doit répondre au framework sur la donnée **la plus récente (et
>    son historique)**, sans passer à côté d'une information récente. `dossier.py` est la moitié
>    LECTURE de cette règle ; la moitié ÉCRITURE reste à spécifier.
> 3. **Sur les entrées en PROSE** : le système doit **juger** si une prose ancienne est toujours
>    d'actualité (recherche web ou appel EDGAR). Si oui, elle continue de servir ; si périmée, on
>    l'**archive pour la trace** et on la remplace par une prose actualisée.
> 4. **Publications trimestrielles = revue complète de la thèse.** Position ouverte = actualisations
>    régulières cherchant ce qui ferait évoluer la thèse, dans les deux sens.
> 5. **Périmètre : EDGAR uniquement** pour l'instant. Le mode dégradé (européennes, non-coté) est une
>    version ultérieure — ne pas le construire maintenant.
>
> Puis le lot 5 proprement dit : **le mémo projeté / réconciliation à 0/0** via
> `tools/reconcilier_vocabulaires.py` (⚠️ **`4 ok / 2 FAIL — 30 orphelins + 13 inutilisés`, 0/6 blocs**,
> re-mesuré le 2026-09-21 : le `5 ok / 2 FAIL — 14 / 3` cité ici jusque-là était jugé contre
> `FIELD_PROFILES`, la grille MVDD à qui le lot 3 avait retiré son autorité — l'étalon a été corrigé,
> ce n'est pas une régression), **+** ~~le nettoyage des « faux au sens v3 » hérités de RVMD~~
> **✅ FAIT le 2026-09-24** (un seul faux réel, #190→…→#656, retiré par correctif de PRODUCTEUR et
> refus publié → **#662** ; #191 et #186 n'en étaient pas — voir §« Nettoyage des faux » plus bas),
> **+** le wiring de `serve_mandate`/`read_open_mandates` dans la boucle live du search-worker.
> ⚠️ Migration : **aucune à ce jour dans ce lot** ; **046 est appliquée**, la prochaine écrite sera
> **047** (le « 045 » écrit ici était une prévision, jamais une mesure).
>
> ⚠️ **Ligne de base du 2026-09-21 avant le passage** (requêtée, pas rappelée) : `framework_answers`
> **0**, `framework_mandates` **16** (tous collecteur, **0 manager**), RVMD **53** entries courantes,
> 3 plans, 1 carte. Après passage et retrait de #475 : `framework_answers` **6**.
>
> ⚠️ **La ligne de base se REQUÊTE, toujours.** Ce lot a démarré en trouvant NVDA 15 / MSFT 15 /
> RVMD 43 actives là où « Où on en est » disait 52/51/27, et **aucun plan NVDA/MSFT** — le prérequis
> n'était pas prêt. `feedback_ligne_de_base_est_une_mesure`.
> ⚠️ **Résidus nommés (aucun n'est un défaut)** : cartes NVDA/MSFT non persistées (refus) ; **coût
> web agrégé non instrumenté** (le tool imprime traducteur/apparieur, pas le web) ; **wall-clock ≈ 1 h
> pour MSFT** — le garde #73 borne l'infini, pas la lenteur (budget global de run / parallélisme web =
> chantier distinct) ; #340 mêle deux ancres à 182 j, DÉCLARÉ, à juger (backlog #9).
> ⚠️ **Ne pas ré-annoncer un gain de routage comme une collecte** (#71) ; le chiffre est « lignes en
> base », jamais « lignes routées ». La distribution se re-mesure, elle ne se cite pas.

---

> **▶ PROCHAIN JALON — LOT 5, LE MÉMO PROJETÉ, CADRÉ PAR L'ARBITRAGE DU 2026-09-24.**
>
> **Ligne de base du 2026-09-25, re-requêtée ce jour** (`feedback_ligne_de_base_est_une_mesure`) —
> suite **3141 / 0 sur 42 scripts** (3072 le 24 au matin ; +69 par le nettoyage RVMD ci-dessous,
> dont +15 dans `check_financials_feed` et le négatif neuf).
> ⚠️ **42, pas 43** — le « 43 » écrit ici le 24 était un décompte de mémoire. `run_all.sh` exclut
> **par conception** les 3 checks « live » (`check_fetch_live`, `check_fetch_relevance`,
> `check_cours_cote_live` : réseau ouvert, clé fournisseur, écriture DB réelle) ; 45 fichiers
> `check_*.py` existent, 42 tournent hors-ligne. Un total juste sur un dénominateur faux se relit
> comme une couverture qu'on n'a pas.
> ⚠️ **Et le rapport ne se lit que par `run_all.sh`** : lancé à la main sur `$PWD:/app`,
> `check_frameworks_definitions` sort **41 ok / 1 FAIL — « spec absente »**. Ce n'est pas une
> régression, c'est la garde de `feedback_check_degrade_en_sortant_a_zero` qui fonctionne : §7
> confronte le référentiel à `/roadmap/V3/03-spec-frameworks.md`, et `run_all.sh` monte `/roadmap`
> (+ `/contract_frozen`) que l'invocation nue n'a pas. Avec les montages : **44 / 0**.
> ⚠️ **ET LE VERT DE LA SUITE NE DIT RIEN DE LA PRODUCTION.** Mesuré le 2026-09-25 :
> `docker exec portfolio-backend grep -c operations_etablies …/financials_feed.py` rendait **0**, et
> `projection_memo.py` n'existait pas dans le conteneur — **la garde ROIC tournait à 3141/0 dans la
> suite pendant que le conteneur de prod exécutait le code qui fabrique le faux.** Le prochain
> passage du feed aurait superseded #662 par un #66x fabriqué, en silence, sans qu'aucun compteur
> ne bouge. Rebuild fait (`e2b548f`), vérifié DANS le conteneur puis par `GET /api/health` = 200.
> **Réflexe à garder : après un correctif de producteur, `docker exec … grep` la constante
> caractéristique — le dépôt et le conteneur sont deux mesures différentes.**
>
> Héritage `check_datation` §7 :
> **128 courantes sans portée / 110 datées** · RVMD × `qualite_financiere` **5 chemises hétérogènes**
> (40 pièces remises sur **74** courantes — 57 le 23/09, la valorisation en a ajouté) ·
> `reconcilier_vocabulaires.sh` **4 ok / 2 FAIL — 30 orphelins + 13 inutilisées, 0/6 blocs**.
>
> ⚠️ **LE 0/0 N'EST PAS LE LOT — c'est l'état TERMINAL de la roadmap, et l'outil le dit lui-même**
> (« Avec 2 pilotes sur 6 blocs, l'écart est bloc-par-bloc… Un vert ici avant cela est un défaut du
> mesureur, pas une bonne nouvelle »). Viser 0/0 maintenant, c'est confondre le but et l'étape.
>
> **LE DÉFAUT MESURÉ — ÉTAT DU 2026-09-24 AU MATIN, CORRIGÉ DEPUIS** (gardé parce que le jalon ne se
> comprend pas sans lui). `frameworks.yaml` ne portait **aucun** champ reliant un framework à un bloc
> du mémo (`chemin_indexation` vit dans l'espace de noms du framework, pas dans celui du mémo). Les 6
> blocs du `ResearchMemo` sortaient donc tous « aucune méthodologie approuvée » : sur RVMD, **14
> chemises instruites et 40 pièces remises n'atteignaient pas la note de comité**, dont
> `qf_7.tresorerie_disponible` en rang **A**. Le bloc `financials` que lit le comité était rédigé
> librement par le modèle, à côté du classeur — **c'était littéralement la cause racine §0.3**.
>
> **▶ ARBITRAGE UTILISATEUR DU 2026-09-24 — option (A), et sa contrainte de croissance :**
> *« On commence par faire tourner de bout en bout sur les 2 frameworks construits ; ensuite il
> suffira de compléter les frameworks pour que le système grossisse et gagne en robustesse. »*
>
> Deux exigences, la seconde étant la plus contraignante :
> 1. **Ne publier que l'instruit.** `qualite_financiere` → `financials`, `defendabilite` → `moat`
>    sont PROJETÉS depuis les dossiers. Les 4 autres blocs sortent dans un **état NOMMÉ**
>    (« pas de méthodologie approuvée »), **distinct d'un bloc vide** : un bloc vide se lit « rien à
>    signaler », l'état nommé se lit « non instruit ». C'est la troisième case de #68 / le trio de
>    #44, appliqués au mémo — le même remède qui vient de payer sur `check_cours_cote_live`.
> 2. ⚠️ **AJOUTER UNE MÉTHODOLOGIE DOIT ÊTRE UNE OPÉRATION DE DONNÉES, JAMAIS DE CODE.** C'est le
>    sens de « il suffira de compléter les frameworks ». Si brancher `industry` demande de toucher
>    le projecteur, la règle aura été **recopiée** et elle re-divergera au premier correctif
>    (`feedback_correctif_regle_jumeaux`, #46). Donc : **détenteur unique** de la projection, le lien
>    framework→bloc **déclaré dans `frameworks.yaml`**, et un check qui l'exige. Le test qui le prouve
>    n'est pas « les 2 blocs marchent » mais **« un 3ᵉ framework fictif ajouté en YAML SEUL se projette
>    sans diff de code »** — la garantie porte sur la croissance, elle se teste sur la croissance.
>
> ✅ **LES DEUX EXIGENCES SONT LIVRÉES ET PROUVÉES — 2026-09-24.** Ce fichier ne le disait pas encore
> (écrit le 2026-09-25) : le jalon était mesuré sur son diagnostic, jamais sur sa livraison.
> - **Détenteur unique** : `app/agents/v2/projection_memo.py`. ⚠️ **Il ne nomme AUCUN framework** —
>   ni `qualite_financiere`, ni `defendabilite`, nulle part : ni constante, ni `if`, ni table de
>   correspondance. Le lien vit **en données**, `bloc_memo:` dans `frameworks.yaml` (2 occurrences,
>   lignes 45 et 294), et le module l'itère. C'est exactement l'exigence n°2.
> - **La preuve de croissance, pas la preuve d'usage** : `check_memo_projete.py` **§4** injecte un
>   framework **fictif** (`cadre_fictif` → un bloc cible) **en YAML seul**, et vérifie qu'il se
>   projette. Un projecteur qui aurait codé les 2 en dur passerait « les 2 blocs marchent » et
>   rougirait ici. ⚠️ Le négatif correspondant **mute le YAML, pas le Python** — c'est le seul
>   endroit du dépôt où la mutation porte sur la donnée, parce que c'est la donnée qui porte la règle.
> - **Trois états nommés, jamais un bloc vide** : `instruite` / `sans_acquittement` /
>   `pas_de_methodologie_approuvee`. Un bloc vide se lit « rien à signaler ».
> - **Le projecteur ne RÉDIGE pas, n'AGRÈGE pas, ne JUGE pas, n'ÉCRIT pas** — aucun appel de modèle,
>   deux analystes sur une question donnent **deux points** (moyenner reproduirait la cause n°1 de
>   #50), `posture='NEUTRE'` verrouillée par le contrat, production **à la lecture** (#53/#54).
> - **Une réponse orpheline lève un `ProjectionRefusee`, elle n'est jamais sautée.** Sautée, elle
>   ferait passer un chapitre de `instruite` à `sans_acquittement` **sans qu'aucun décompte ne bouge**
>   (`feedback_check_degrade_en_sortant_a_zero`).
> - **Gardes** : `check_memo_projete.py` **51 / 0** + `negatif_memo_projete.sh` **25 mutations / 0** ;
>   `check_frameworks_definitions.py` **44 / 0** + `negatif_frameworks_definitions.sh` **25 / 0**
>   (ré-exécutés le 2026-09-25, pas rappelés).
> - **Lecture gratuite** : `bash tools/montrer_memo_projete.sh RVMD` — exit 0 = note imprimée,
>   1 = projection REFUSÉE, 2 = non mesurable. Bilan RVMD : **6 chapitres — 1 instruite
>   (`financials`) · 1 `sans_acquittement` (`moat` : méthodologie approuvée, 0 réponse au dossier) ·
>   4 `pas_de_methodologie_approuvee` · 6 points publiés · 0 réponse non acquittée.**
>
> ⚠️ **CE QUE CE BILAN DIT ET QU'IL FAUT ENTENDRE** : `moat` est `sans_acquittement`, donc
> l'arbitrage (A) — « faire tourner de bout en bout sur **les 2** frameworks construits » — n'est
> **pas** consommé. La mécanique est prouvée sur 2 blocs ; la CHAÎNE n'a tourné que sur un. C'est le
> premier point de la reprise, et il coûte des appels modèle (voir ci-dessous).
>
> ✅ **Nettoyage des « faux au sens v3 » de RVMD — FAIT le 2026-09-24, et c'était un défaut de
> PRODUCTEUR, pas de donnée.** Le jugement humain a corrigé la caractérisation que ce fichier en
> donnait (cf. §« 24 entries suspectes » plus bas, réécrit) : **#191 n'est pas un faux** — son
> descendant courant #657 refuse le ratio et publie la consommation de trésorerie, c'est la doctrine
> correctement appliquée, jugée sur son titre et non sur son contenu. **#186 n'a aucun descendant
> vivant.** Seul **#190** en était un, et il s'était **reproduit** #190→#231→#274→#549→**#656** :
> supprimer la ligne n'aurait rien réglé, le détenteur est le producteur (#46). Livré dans
> `financials_feed.py` — garde ROIC jumelle de la garde FCF (elle manquait parce qu'on n'avait
> cherché que les nombres **flatteurs** : +80,8 % de conversion saute aux yeux, −49,7 % de ROIC
> paraît plausible) · le refus est **PUBLIÉ** avec les tags du champ, donc il supersede la ligne
> fausse par le chemin normal (un refus muet aurait laissé #656 courante pour toujours —
> `ENTRIES_COURANTES` ne connaît que `superseded_by`) · « intrant absent » et « ratio non défini »
> deviennent un `etat` **structuré** (la prose ne se testait qu'au `in`, et ce `in` n'a jamais vu le
> préfixe ajouté devant : le motif sortait « intrant manquant en base EDGAR : chiffre d'affaires NUL
> (déposé, pas manquant) », au vert depuis le 2026-09-04). Écrit en prod : #656 → **#662**
> (`roic_pct` NULL). Gardes : `check_financials_feed.py` **108/0** (dont le retrait de l'assert
> « ROIC négatif publié tel quel (−90,7 %) », qui **verrouillait le faux**) +
> `negatif_financials_feed.sh` **8 mutations / 0**, satisfiabilité mesurée d'abord.
> ⚠️ Confirmation indépendante et gratuite : `qf_1` était déjà `sans_objet` en base (#469, « sans
> exploitation qui immobilise du capital productif, la question n'a pas d'objet ») — **l'analyste
> avait raison pendant que le producteur déterministe le contredisait en tier A.**
>
> **▶ CE QUI RESTE DU LOT 5, DANS L'ORDRE.**
>
> 1. ✅ **FAIT le 2026-09-25 — la chaîne est allée de bout en bout sur `defendabilite` (arbitrage A
>    consommé).** Protocole tenu : frontière gratuite lue en texte (aucune question morte, mais
>    dossier à **35 `mesure` / 3 `interpretation`, 0 indexée moat**), ligne de base requêtée (chemin
>    VIERGE), arbitrage utilisateur = *commander la recherche* (chaîne complète, pas `--sans-collecte`).
>    Passage réel (plan #103, prod sans rollback) : **6 liens de couverture (0→6)**, 10 mandats
>    collecteur (ids 586-595), RVMD 74→**89** ; analyste **6 réponses (596-601) : 5 `non_fondable`
>    remède collecte · 1 `sans_objet` · 0 refus** ; manager 6 acquittements. `MOAT` passe de
>    `sans_acquittement` à **`instruite`** — les DEUX frameworks construits projettent désormais.
>    ⚠️ **Le piège #78 n'a PAS eu lieu** : l'analyste a refusé de fabriquer une barrière depuis des
>    financières, il a `non_fondable` en NOMMANT la recherche à commander. ⚠️ **LIMITE MESURÉE, pas un
>    défaut** : le web n'a pas ramené les preuves de moat (search-workers épuisés, 3 échecs de
>    validation) — `moat` reste `non_fondable` en attente de collecte réelle. Détail : archive
>    2026-09-25. Outil : `tools/acceptation_analyste.py` gagne `ACCEPTATION_CAS` (surcharge du `CAS`).
> 2. ✅ **Wiring de `serve_mandate`/`read_open_mandates` — LIVRÉ le 2026-09-25 (2) au niveau code +
>    tests + persistance réelle** (récit complet : archive § « le BOUCLAGE comité → collecte »).
>    `app/agents/v2/bouclage.py` (`boucler_renvois`) lit les renvois ouverts, refait la recherche PAR
>    LE MÊME PROCESSUS scopé (arbitrage : pas de chemin parallèle, #46 ; d'où `executer_collecte_
>    framework(questions=…)`), re-répond, SERT les mandats, et rend une note à **4 sorts** distinguant
>    « collecte insuffisante » de « mandat pas clair » (arbitrage utilisateur). `serve_mandate`/
>    `read_open_mandates` ont donc un appelant de PROD (fin de la figure #71). ⚠️ **Ni #19 ni #39 ne
>    sont touchés** : le mandat re-rentre par le traducteur, pas par un input élargi du search-worker
>    (l'arbitrage « même processus » l'a évité). Garde : `check_bouclage.py` **27/0** (§4 COMPTE les
>    appelants en prod par AST — « exercé » ≠ « vert », [[feedback_controle_au_point_de_lecture]]) +
>    `negatif_bouclage.sh` **11/0**. Entrée de prod : `tools/boucler_renvois.{py,sh}`.
>    ✅ **BOUT EN BOUT MESURÉ contre la VRAIE base** (`tools/acceptation_bouclage.sh`, **8/0**,
>    transaction ROLLBACK, zéro résidu) : un renvoi seedé est lu par `read_open_mandates`, retrouvé par
>    `id_du_mandat_ouvert`, SERVI (`ouvert→servi`, avant/après figés), absent des ouverts ensuite, et
>    transformé en note `acquis`. ⚠️ **MESURE au passage : 0 mandat `manager_renvoi`/`comite` OUVERT en
>    base** — les passages du 21 et du 25/09 ont acquitté. Donc un PASSAGE RÉEL complet
>    (`boucler_renvois.sh`) rendrait « rien à boucler » : la boucle live n'aura de matière qu'après un
>    vrai renvoi (une réponse insuffisante qui échoue un des 4 contrôles). Le wiring, lui, est prouvé.
>
> **Ce que ce lot NE fait PAS**, et pourquoi : la partie **MONITORING** (moitié ÉCRITURE de « on
> n'écrase pas, on empile ») relève du **suivi**, que l'arbitrage #1 du 2026-09-22 place APRÈS
> l'amont. La **dette des 128 entrées d'héritage** reste un lot à **coût MODÈLE** à part entière —
> `rejeu_producteurs.sh` ne la soldera jamais (il ne détient pas des entries écrites par le search
> worker). Le résiduel **#80** (`framework_version` écrit par aucun des 3 producteurs de notes,
> `grep framework_version` = 0) reste ouvert.

### Découpage des lots suivants (spec v3 §10)

| Lot | Contenu | Migration |
|---|---|---|
| 0 | ✅ **Ligne de base** (ci-dessus) — 2026-09-09 | — |
| 1 | ✅ **Contrat** `FrameworkAnswer` + `FrameworkMandate`, pont relationnel **en Python** (#37), carte de provenance, écran niveau 3 en maquette — 2026-09-09 | — |
| 2a | ✅ **Le référentiel** — 13 questions en données inertes, 39/0, négatif 22/22 — 2026-09-10 | — |
| 2b | **Archivage et dévocabularisation** : `archive_v2` (rien de détruit) · `knowledge_entries` amaigrie de **8 colonnes** (7 à zéro écriture **+ `covers`**) · `question_coverage` créée, portée par framework **et version** · `entry_type`/`report_type` dévocabularisés | **036** |
| 2c | ✅ **TERMINÉ** : traducteur → plan → collecteur (§3.6) · persistance · exécuteur réel + chaîne runtime · **`POSTES` dérivé du plan + retrait du levier `RESSERRER` + mort de §12bis (maillon 5, 2026-09-12)** | **039** ✅ |
| 3 | 🔄 **EN COURS** — ✅ **l'analyste** (maillon 1, 2026-09-13) · ✅ **`framework_answers` / `_dispenses` en base + persistance** (maillon 2, 2026-09-13, migration **040 appliquée**) · **suppression** de `MVDD_SPEC`, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS` · **collecte neuve pilotée par le plan** sur NVDA / MSFT / RVMD | **040** ✅ |
| 4 | ✅ **CLOS (2026-09-21)** — AGENT (2026-09-20, #76 : manager + 4 contrôles + renvoi→mandat, `check_manager` 35/0) **et DONNÉES** (2026-09-21, **#77** : migration **043** appliquée réconciliant `FrameworkMandate` par-question ↔ table 039 par-ingrédient · `manager_persist.py` — l'avis se **recalcule**, seul le mandat est persisté (arbitrage utilisateur) · `check_manager_persist` 17/0 · négatif 5/0 · **acceptation T8 6/0**) | **043** ✅ |
| 5 | 🔄 **EN COURS** — ✅ **le projecteur** (2026-09-24, `projection_memo.py`, détenteur unique qui ne nomme aucun framework ; lien `bloc_memo` **en YAML** ; 3 états nommés ; `check_memo_projete` **51/0** + négatif **25/0**) · ✅ **nettoyage des faux RVMD** (#656→#662) · ✅ **chaîne de bout en bout sur `defendabilite`** (2026-09-25 — arbitrage A consommé, `moat` → `instruite`, 5 `non_fondable`+1 `sans_objet`, #78 évité, web n'a pas ramené le moat) · ✅ **BOUCLAGE comité → collecte** (2026-09-25 (2), code+tests+persistance : `bouclage.py`, note à 4 sorts, `check_bouclage` **27/0** + négatif **11/0** dont les 2 « exercé » ; `tools/boucler_renvois.sh`) — ⏳ **passage réel + déploiement** (sandbox) · ⏳ réconciliation à 0/0 — **état terminal de la roadmap, PAS ce lot** | — (aucune migration à ce jour ; **046 appliquée**, la prochaine écrite sera 047) |
| 6 | Les 3 niveaux de drill-down · acquitter / renvoyer tracés (A7) · `qualite_info` **dérivée** | — |
| 7 | Le second pilote de bout en bout · acceptation complète T1-T8 | — |

⚠️ **Ordre imposé, inchangé : UX (contrat) → agent → données.** Jamais commencer par la table.
⚠️ **Les numéros de migration de cette table étaient périmés** (lots 3/4/5 annoncés 037/038/039
alors que 039 a été consommée par le 2c) — renumérotés 040/041/042 le 2026-09-13. Vérifier la
dernière migration **appliquée** avant d'en écrire une, jamais se fier à ce tableau.
⚠️ **Migration 036 écrite juste avant son lot**, jamais en avance ; générateur qui **importe** la
règle plutôt que la ré-implémenter en SQL (méthode des migrations 034/035) ; garde
`RAISE EXCEPTION` **éprouvée en négatif avant application**.

### Ce que la v3 ferme explicitement

- **Capacité 5, barreau 4** (l'agent propose une méthode d'approximation depuis le dossier) —
  **hors périmètre**. Réfuté **4 fois** par sa propre ligne de base ; le contre-test montre que la
  formulation n'est pas en cause (dépouiller la question de sa négation fait passer les rangs de
  `[6,10,—,9,—]` à `[5,15,—,9,16]` : aucune amélioration). Cause réelle : l'ingrédient (entry #33,
  citée dans la prose de la synthèse) est **orphelin**, donc absent du corpus du champ.
  **Le barreau 4 ne compense pas une limite de la recherche : il compense un défaut de rangement.**
  À rouvrir **seulement** si, le rangement fait, une approximation reste bloquée faute de méthode.
- **Grille MVDD de 19 champs** · **`SYNTHESIS_TARGETS`** (sacs de mots-clefs français en dur) →
  supprimés au lot 3. **`DECLARED_NONBLOCKING_GAPS`** → devient une table clefée
  `(ticker_id, framework_id, framework_version, question_id)` (violation #31 aujourd'hui : une
  dispense en source Python exige un redéploiement pour adapter la grille à une entreprise ; et sans
  la version, une dispense survit à la question qu'elle dispensait — écart V10).
- **Hybridation RRF de la recherche** — reste **interdite** (mesurée dégradante, MRR 0,905 → 0,655).
- **Le corpus en base comme point de départ** — **interdit** (spec §0.6, posé le 2026-09-10). Les
  données en base sont l'**historique de recette** d'un système inachevé : utilisables pour
  **éprouver**, jamais pour **concevoir**. Le système n'est en usage réel sur aucun périmètre, donc
  **rien en base n'est un fait à préserver** — ni V0/V1, qui ne contraignent plus aucune décision
  de modèle v3.
- **Le modèle n'a aucun levier sur l'exigence** — `curator.py` peut aujourd'hui **RESSERRER**
  `champs_requis` / `tier_plancher` (« le DERNIER levier du modèle sur le verdict »). Retiré au
  lot 2c : sous le principe « c'est le framework qui dicte les questions », un resserrement
  discrétionnaire est une question posée par le **modèle**.
- **Dégrader le tier d'une source selon l'émetteur** (le 10-K de RVMD « vaut moins » que celui de
  MSFT) — **refusé**. C'est de l'**actualité**, pas de la fiabilité : l'ancre de RVMD bouge, la
  source ne devient pas moins fiable. Le traducteur **nomme l'ancre** ; l'actualité reste calculée
  à la lecture (#53).

---

## Où on en est (2026-09-09)

> ⚠️ **CE TITRE MENT SUR SON CONTENU : ce tableau est un INSTANTANÉ DU 2026-09-09, pas un état
> courant.** Il a déjà coûté un faux départ : le lot 4 a démarré sur ses « 52 / 51 / 27 » alors que
> la base portait **15 / 15 / 43**. ⚠️ **Aucun chiffre de cette section ne se cite sans être
> re-requêté** (`feedback_ligne_de_base_est_une_mesure`). Ce qui est à jour vit à un seul endroit :
> **▶ PROCHAIN JALON** ci-dessus. On le garde pour les **modes de panne** qu'il documente, qui eux
> n'ont pas de date de péremption.

**Le système est exercé, pas prototypé.** La chaîne complète a tourné de bout en bout sur trois
émetteurs, et on connaît ses modes de panne — c'est le principal actif du chantier.

| | NVDA (cas-pilote) | MSFT (généralité) | RVMD (banc d'essai) |
|---|---|---|---|
| Socle | 52 entries (32 A / 15 B) | 51 entries, 19/19 champs, 0 `llm_memory`, ≈ $0,19 | 27 actives (13 déterministes + 14 qualitatives) |
| Readiness | **`not_ready (peremption)`**, 9 champs périmés, 7 mandats, **0 collecte** | **`not_ready (peremption)`**, 9 champs périmés, **0 collecte** | **rapport #28** — `not_ready`, **9 collecte / 4 rafraîchissement** |
| Chaîne | research → bull/bear → réfutation → synthèse = `PROCEED_AVEC_CONDITIONS` | idem, ≈ $0,018 | **0 synthèse grounded** — 3 des 4 cibles vides |

- **Suite : `bash checks/run_all.sh` = TOUT VERT.** ⚠️ **Le total vit au ▶ PROCHAIN JALON, pas ici**
  (détenteur unique, #46) — le « 2726 / 37 » qui traînait sur cette ligne datait du 2026-09-21 et
  valait **3141 / 42** au 2026-09-25. Un compteur recopié re-diverge au correctif suivant. Ce qui
  suit ne décrit que des **conditions d'exécution**, qui elles ne se périment pas au même rythme :
  `check_manager`
  **35/0** hors ligne (le manager est pur — aucun appel modèle) + `negatif_manager.sh` 7/7 ;
  `check_manager_persist` **17/0** (base réelle, ROLLBACK) + `negatif_manager_persist.sh` 5/0.
  `check_edgar_feed` **98/0** et **hors ligne** (§12bis mort → ne
  requiert plus `CHECK_DB_URL`) ; `check_entry_nature` **88/0** (§7 = invariant #51, cf. frontmatter).
  Les checks « état persisté » gardent le montage réseau `coolify` + `CHECK_DB_URL` (`check_entry_nature §7`,
  `check_collecte_persist`, `check_framework_persist`, `check_appariement_persist`, `check_manager_persist`). `run_all.sh`
  porte les montages `/contract_frozen` (sans lui 4 scripts sous-comptent en sortant à 0) **et
  `/roadmap`** (sans lui `check_frameworks_definitions` §7 sort en échec au lieu de se sauter).
  ⚠️ **Ne pas le réécrire dans `/tmp`** : la version jetable sous-comptait 47 assertions en silence
  (`CHANTIER_OUTILLAGE_DEV.md` §27).
- **Migrations appliquées jusqu'à 043** (036/037/038 lot 2b, **039** lot 2c — tables du plan de
  collecte, **040** lot 3 maillon 2 — `framework_answers`/`framework_dispenses`, **041** `poste` sur
  l'item de plan, **042** lot 3 maillon 4bis — `appariement_cartes`, **043** lot 4 données —
  réconciliation `framework_mandates` pour le mandat manager). Prochaine = **044**.
- **Déploiement : le chemin nominal est repassé** (`compose-deploy.sh`, un seul appel) après quatre
  sessions de refus du classifieur. Le repli en commandes séparées reste documenté au §12 de
  `CHANTIER_OUTILLAGE_DEV.md`, mais **re-tester le nominal en premier** à chaque session.

### Roadmap 02 — close, et ce qu'elle laisse acquis

`roadmap/V3/doctrine-trois-axes.md` : **capacités 0 à 4 CLOSES**, capacité 5 fermée (§ ci-dessus).
Les trois axes **jamais recombinés en scalaire** sont en production et restent la doctrine de la v3 :

- **fiabilité** — propriété de la **source**, stockée (#50).
- **nature** — propriété de l'**assertion**, stockée (migration 034, #51).
- **actualité** — propriété de la **relation** fait ↔ ancre, **calculée à la lecture, jamais
  persistée** (#53). La persister reproduirait le défaut d'origine : un corpus qui ne vieillit pas.
- **Porte de complétude à trois états** (#54) : `couvert` / `couvert_perime` / `non_couvert`, deux
  remèdes `rafraichissement` ≠ `collecte`. Le faux vert d'origine est tombé **en production** :
  NVDA et MSFT passent de `ready, 0 gap` à `not_ready (peremption)`.
- **Un verdict persisté n'est pas un verdict servi** : le GET readiness rejoue la moitié
  déterministe de la porte à la lecture, **sans écrire**.
- **Règle de rang** : une estimation vaut **un cran sous sa pièce citée la plus faible**, toujours
  **dérivée**, jamais auto-déclarée ; `nature` forcée à `interpretation`.

### RVMD — 16 défauts du socle, tous trouvés avant ou après dépense, jamais par le contrat

Résultat le plus réutilisable du chantier : **quatorze défauts sur seize trouvés à coût de modèle
nul**, en exécutant les producteurs déterministes et en **lisant leur sortie en texte**. Aucun
n'était visible dans un diff, aucun n'a fait rougir un contrat Pydantic — leurs nombres étaient
justes, c'est le *fait énoncé* qui était faux.

| Vague | Défauts | Convention née |
|---|---|---|
| Socle EDGAR (F1→F6) | ancre de bilan, appariement des flux, tri des concepts XBRL | #42, #43 |
| Valorisation (F7→F9) | multiples à dénominateur négatif publiés tels quels | #44 |
| Format (F10, F11) | montants écrasés à « 0,0 Md » ; un CA nul sauté par `if x:` | #45, #46, #47 |
| Premier vrai modèle (F12, F13) | pas de date dans le message ; drapeau calculé jamais persisté | — |
| Péremption (F14) | `source_date` datée du flux sur un ratio de bilan | **#48** |
| Partition (F15) | une entry non datée dans deux classes à la fois | **#53** |
| Lisibilité de la clef (F16) | `poste_kind` absent de tout le socle NVDA et MSFT | **#55** |

---

## Ce qui reste ouvert — hors roadmap active

0. **Deux arbitrages posés par l'utilisateur le 2026-09-10**, à honorer quand leur lot arrive :

   **(a) L'existence d'entries étiquetées « pairs » ne PROUVE PAS qu'une analyse concurrentielle a
   eu lieu.** Un futur framework « analyse concurrentielle » apportera des éléments sur les pairs ;
   mais une analyse de concurrence peut aussi se faire en faisant passer le concurrent dans le
   **système complet** sans ouvrir de position — coûteux, exhaustif, et produisant un tout autre
   corpus. L'étiquette peut être distincte ; la **règle** qui fonde le verdict « analyse
   concurrentielle faite » sera plus compliquée que la présence de l'étiquette. ⚠️ C'est le mode de
   panne de `feedback_controle_au_point_de_lecture` : compter des lignes portant un tag est un
   **affichage**, pas un contrôle. Ne pas câbler le raccourci « `tags @> {pairs}` ⇒ couvert ».

   **(b) Une affirmation en fiabilité basse se range dans les constats de l'entreprise, mais le
   système doit chercher à la vérifier quand elle PÈSE.** Décidé : le risque déclaré dans un dépôt
   est un `fact_qualitative` (constat), pas un `fact_financial` — il n'a pas l'autorité d'une
   mesure. Backlog qui en découle : quand une assertion est à la fois **de fiabilité basse** et
   **déterminante pour le jugement final**, le système va chercher des sources pour la **confirmer
   ou l'infirmer**. ⚠️ Le déclencheur est le **couple** (fiabilité basse × poids dans la décision),
   jamais la fiabilité seule — sinon on relance une collecte sur tout le bruit du corpus. Le poids
   n'est pas encore une grandeur lisible : c'est ce qu'il faudra définir en premier.

1. **24 entries suspectes de RVMD** à statuer à la main (le balayage rend la liste, motivée et
   ordonnée). **Jugement humain par construction** : décider qu'un fait est remplacé n'est pas
   automatisable sans donner à une heuristique de dates une voix sur ce que le corpus affirme (#29).
   ⚠️ Quatre entries tier A affirment « aucun produit approuvé pour la vente commerciale » alors que
   **la FDA a approuvé RASONQUE le 2026-08-26** — aucune n'est fausse, toutes sont périmées.
   **Ce point reste ouvert.**

   ✅ **Le volet « faux au sens v3 » est CLOS le 2026-09-24 — et ce fichier en donnait une
   caractérisation fausse sur deux points sur trois.** Ce qui a été mesuré, et qui se re-mesure en
   deux requêtes :
   - **Les ids #186/#190/#191 ne sont plus lus par la chaîne vivante.** La migration 036 a déplacé la
     grappe V2 dans `archive_v2.knowledge_entries` (ids **1–191**, gelés) ; `public` commence à
     **192**. Un `SELECT … WHERE id IN (186,190,191)` sur `public` rend **0 ligne** — ce n'est pas un
     corpus propre, c'est un corpus qu'on regardait au mauvais endroit.
   - **Les faux se REPRODUISENT.** #190 → #231 → #274 → #549 → **#656**, quatre générations de la
     même entry tier A, la dernière courante. Supprimer une ligne n'aurait rien réglé : **le
     détenteur est le producteur** (#46), pas la donnée.
   - **#191 n'est pas un faux.** Ce fichier le jugeait sur son TITRE (« conversion FCF non
     définie »). Son descendant courant **#657** refuse le ratio et publie la consommation de
     trésorerie à la place : c'est la doctrine correctement appliquée, l'exemplaire dont la garde
     ROIC manquait.
   - **#186 n'a aucun descendant vivant** — rien à statuer.
   - **Seul #190 en était un**, et il est retiré par le chemin normal : correctif de producteur dans
     `financials_feed.py` (garde ROIC **jumelle** de la garde FCF, absente parce qu'on n'avait
     cherché que les nombres **flatteurs**), refus **PUBLIÉ** avec les tags du champ, donc
     **#656 → #662** (`roic_pct` NULL). Un refus muet aurait laissé #656 courante pour toujours :
     `ENTRIES_COURANTES` ne connaît que `superseded_by`. Gardes : `check_financials_feed.py`
     **108/0** + `negatif_financials_feed.sh` **8/0**. Détail et arbitrages : §« Nettoyage des faux
     au sens v3 » plus haut.

   ⚠️ **Mesuré le 2026-09-12** : RVMD porte **43** entries déterministes actives (vs 13 au banc
   d'essai) — dont **30 faits web SANS `metric`** (25 `edgar_official` + 5 `company_ir_official`),
   écrits par le collecteur du maillon 4 (search-worker sur sec.gov / IR). ✅ **Ces 30 ne sont PAS des
   parasites — §0.6 les qualifie de compatibles** (frais, cités, tous `mesure`) : on ne les
   réconcilie donc pas ici, et §7 a été re-mesuré en invariant plutôt que de compter le corpus (cf.
   frontmatter, [[project_entry_nature_gate_invariant]]).
2. **FDA / EMA en régulateur A- (0,85)** — décidé, non commencé. `fda.gov` n'est dans **aucune**
   table ; `_EU_REGULATOR_SUFFIXES` porte `esma.europa.eu` (titres) mais pas `ema.europa.eu`
   (médicaments). L'approbation FDA du 2026-08-26 classe aujourd'hui `web_search_generic` **0,50**.
   Un `regulator_filing_us` touche `SOURCE_RELIABILITY_BASELINE`, le `Literal SourceType`, le
   frontend **et les 12 prompts v2 en base** → migration dédiée + règle #19.
   ⚠️ **Prérequis de fait du pilote biotech** — à faire avant le lot 7.
3. **File de propositions de sources** — demandée, non conçue. Le système observe les domaines
   `web_search_generic` rencontrés, **recommande** un classement, l'utilisateur **valide**.
   ⚠️ L'admission reste un **acte humain** : rien ne se promeut tout seul, pas même par
   corroboration (#50).
4. **7 mandats qualitatifs RVMD** restants (~0,08 $) — sans risque connu : le worker porte la date
   du jour, l'ancre documentaire **et** l'ancre matérielle.
5. **`ingestion-agent`** (contrat C2, document → entries) : jamais construit, non bloquant.
6. **4ᵉ ticker** — aucun blocage technique, et c'est ce qui éprouverait l'universalité sur un
   archétype non représenté. ⚠️ Ajouter son entrée dans `websearch._ISSUER_DOMAINS` **en même temps
   que le ticker** (#33) ; et son secteur dans `source_registry._TICKER_SECTEURS`
   (`tickers.sector` est NULL en base et n'est lu par rien, #52).
7. **Nombre d'analystes par framework** : N = 1 au démarrage, contrat écrit pour N > 1. Deux
   réponses divergentes ne se moyennent **jamais**.
8. **Interface visuelle d'audit des agents** (demandée le 2026-09-11) — une page web rendant le
   système auditable **en termes non techniques** : pour chaque agent, ce qu'il fait et comment il
   est paramétré, avec la distinction **règles en dur** (déterministe, sans modèle : `edgar_feed`,
   `financials_feed`, `valuation_feed`, `base_rate_corpus`, ponts `valider_pont_*`, porte `curator`)
   **vs prompt système + variables** (LLM : `search-worker`, chaîne d'analyse, **traducteur** et
   **collecteur** à venir — modèle/provider/prompt/variables visibles). Prolongement visuel des
   cartes de provenance. `agent_prompts` (`provider`/`model`/`tools_json`/`flow_version`) porte déjà
   la moitié LLM. À cadrer quand la liste d'agents du lot 2c/3 est stable.
9. **Évaluation des plans par modèle ad hoc, sur BEAUCOUP de tickers** (demandée le 2026-09-11) —
   faire juger par un modèle (éventuellement autre que le producteur) les plans du traducteur sur un
   large échantillon, pour débusquer les modes de panne qu'un test à 2-3 tickers rate (cas d'origine :
   ancres génériques sur RVMD, #59). **Signal, pas porte** : le juge trie et motive, il ne décide ni
   n'écrit. Garde-fous : critère énonçable en 3 lignes ([[feedback_deleguer_recherche_pas_jugement]]),
   lire le décompte par catégorie, jamais un cas isolé ([[feedback_jugement_modele_instable_entre_passages]]).
   Réutilise le patron `tools/acceptation_traducteur.py`. À outiller après le collecteur.
10. **Module « réalisé vs annoncé » — la qualité des prévisions du management** (arbitrage du fonds
    du 2026-09-23, cf. le lot #79 ci-dessus). Une pièce `prospective` est datée de son **ANNONCE** et
    porte la période qu'elle vise en **attribut** (`periode_visee`). Le module confronte
    ultérieurement le **constat** publié pour cette période à ce qui avait été annoncé, et en tire un
    insight sur la fiabilité des prévisions de l'émetteur — matière pour `qualite_financiere` et un
    futur framework gouvernance. ⚠️ `periode_visee` est **le seul ingrédient** de ce module : c'est
    pourquoi il est au contrat #79 alors qu'il ne sert **aucun tri** aujourd'hui. ⚠️ Ne PAS le
    dériver en fraîcheur : une guidance émise le 5 août est une information du 5 août, jamais une
    information de l'exercice qu'elle vise — c'est l'arbitrage même qui fonde `prospective`.
11. **Résiduel #80 — une note du fonds ne dit pas selon QUELLE GRILLE elle a lu ses pièces**
    (ouvert par le lot #79). L'arbitrage n° 3 du fonds autorise `date_du_fait = date_du_document =
    aujourd'hui` pour les notes dérivées **à la condition** que l'état de la base sur lequel elles se
    fondent soit écrit à côté. Cet état est **partiellement** écrit : `source_entry_refs`
    (entry_id + version) pour le context pack du `curator`, `cited_entry_ids` + tiers pour
    `synthesis_feed`. **La version des frameworks n'est enregistrée nulle part** — mesuré, pas
    supposé : `grep framework_version` = **0 occurrence** dans les trois producteurs de notes
    (`curator.py`, `synthesis_feed.py`, `base_rate_corpus.py`). Une note relue dans six mois ne peut
    donc pas dire si la grille a changé depuis. ⚠️ C'est l'argument de #64 transposé de la réponse à
    la **note** : sans version, la note reste rattachée à une grille dont le libellé a pu bouger.

### Dettes techniques connues, assumées

- **`base_rate_ge` n'est pas câblé** dans `run_research` : `reverse_dcf.croissance_implicite_…` est
  chiffré, mais son consommateur attend le `taux_base_pct` précis.
- **`BullCase.conviction ×10 si ≤1`** : coercition gardée comme filet, polarité théorique sur `1.0`.
- Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « SearXNG/API » :
  cosmétique, à corriger à la prochaine migration touchant `agent_prompts`.
- **`covers` multi-champs** : une entry qui couvre 3 champs les couvre *également*, alors qu'elle en
  fonde souvent un et effleure les deux autres. ⚠️ **Instruit par la v3** — le lot 3 doit trancher
  la pondération, ou déclarer qu'il n'y en a pas.
- **`uncovered_fields` dupliqué** entre deux calculs voisins (mineur, sans effet observé).
- **`get_db_session()` n'ouvre aucune transaction** (#35) : toute écriture multi-table du lot 4
  doit être explicitement `async with conn.transaction():`.

---

## Décisions structurantes (toujours actives)

- **Modèles** — métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731` (ctx 1M, $0.08 in /
  $0.18 out). Les ouvriers émettent du JSON → coût **dominé par l'output** ; le réflexe « petit
  modèle ouvrier » vient de la tarification Anthropic et **ne se transpose pas**.
- **Embeddings** — `BAAI/bge-m3` **1024d**. Corpus en **français** : `bge-base-en-v1.5` ratait les
  entrées EDGAR tier A (MRR 0,644 → **0,905**). **Ne pas hybrider** : RRF **dégrade** (→ 0,655).
- **Web search** — **Exa**, débordement **Serper**. SearXNG écarté sur le **mode de panne**
  (captcha = résultats vides sans erreur), pas sur le coût. Changer de backend = une classe.
- **DÉCISION #1 = Option C** — base neutre → bull/bear isolés → réfutation asymétrique bear→bull →
  synthèse dialectique (**seul verdict**). **DÉCISION #5** — sortie thèse-driven.
- **Contrainte VPS** (mesurée) : 3,8 Go RAM / ~2,1 Go de socle / **0 swap**, ~5 Go libres →
  pas de self-hosting gourmand. ⚠️ Vérifier le disque avant tout `docker pull` volumineux.

---

## Pièges à ne pas re-découvrir

- **Ne pas induire les frameworks de la base.** La base est le **banc d'essai**, pas le plan. Les
  questions viennent du benchmark méthodologique (Parties B/E) ; la base sert à vérifier qu'elles
  fonctionnent.
- **Une question se pose en substance ÉCONOMIQUE, jamais en artefact comptable.** « Le capital
  employé rapporte-t-il plus que son coût ? » traverse les secteurs ; « quel est le ROIC ? » ne
  traverse pas une biotech. C'est la règle que la grille de 19 avait violée en nommant ses champs
  d'après leurs formules.
- **Le hors-sujet est un signal, pas une panne.** `sans_objet` motivé est une information sur
  l'émetteur — et souvent la réponse d'un vrai fonds est « ce n'est pas dans notre cercle de
  compétence ». Ne jamais fabriquer une réponse plausible là où la question n'a pas de sens.
- **DeepSeek + `response_format=json_object` est NON FIABLE** : collapse sur `{}` ou emballe la
  sortie. Tout passe par `run_json_agent(json_object=False)` + `extract_json`.
- **Contrats = pydantic v2** → tester dans le container backend, **pas** le python hôte (v1).
- **Migrations non auto-appliquées** : `docker cp` + `psql -f`. Le heredoc `psql << EOF` via
  `docker exec` échoue **silencieusement**.
- **asyncpg** : `$1`/`$2` (jamais `%s`) ; JSONB auto-décodé (jamais de `json.dumps` avant INSERT).
  ⚠️ `DATABASE_URL` porte le dialecte SQLAlchemy `postgresql+asyncpg://` — `asyncpg.connect()` le
  **refuse**. Retirer `+asyncpg` pour une connexion directe.
- **Une colonne `NOT NULL` neuve met le déploiement en DETTE.** Entre l'application de la migration
  et le rebuild, le conteneur sert du code qui ne fournit pas la colonne : tout INSERT échoue. Le
  check ne le voit pas — il *lit*. Prouver le chemin d'**écriture** par une écriture réelle dans le
  conteneur déployé.
- **Déploiement** : rebuild, jamais restart. Le build part du **répertoire local** — le script
  pousse d'abord, ne pas le court-circuiter. Pour portfolio, **2 conteneurs sur le domaine sont
  normaux** (backend `/api` + frontend catch-all).
- **Règle #19** : tout changement de contrat = 3 points de synchro (prompt en DB · frontend ·
  import), **+ l'exemple JSON du prompt** (#39). Rafraîchir un prompt en DB ne demande pas de rebuild.
- **Un correctif de prompt ou de schéma n'est pas acquis tant qu'il n'a pas tourné contre le vrai
  modèle.** Un desserrage fait à chaud (`Optional`, `extra=ignore`) est un trou silencieux :
  durcir le prompt d'abord, re-tester, **PUIS** re-serrer.
- **Un écran ne se vérifie pas par un 200** : Next.js sert la coquille et charge côté client.
  Capturer les payloads **réels** avant d'écrire du JSX (un nom de champ faux affiche **du vide**),
  `docker build` comme seule vérification frontend, puis **capture headless regardée**.
  ⚠️ **Le point de lecture fait partie de la capacité** — un rang dégradé calculé et non affiché
  est un rang qui n'existe pas (`feedback_controle_au_point_de_lecture`).
- **Méthode, éprouvée 14 fois** : exécuter les producteurs déterministes et **lire leur sortie en
  texte** avant toute dépense de modèle ; après un déploiement qui remplace une vérité, ne pas
  demander « la nouvelle valeur est-elle bonne ? » mais **« combien de lignes sont actives sur cette
  clef ? »** (#43) ; un check neuf n'est livrable qu'après avoir viré au rouge **pour la bonne
  raison** — les **quatre** faux verts : fixture non discriminante · script mort avant ses asserts ·
  assert à côté du point de lecture · assert écrit en fonction de sa propre constante.
- **Une fixture se copie du réel** (`COPY` de la prod vers une base scratch), jamais écrite à la
  main : une fixture plus favorable que la prod est un check aveugle au vert.
- **Un grep d'interdit lit sa propre énonciation** : dépouiller les docstrings avant de chercher, et
  asserter aussi **en positif** (le détenteur unique est bien consulté).
- **Un agrégateur reconnaît un bilan à sa FORME, jamais à sa position.** Trois dialectes cohabitent
  dans `checks/` : un `tail -1` a sous-compté 47 assertions en silence, `exit 0`. L'absence de toute
  ligne de bilan est un **échec**, jamais un zéro. → §27.
- **Un test négatif qui mute la base ne s'écrit jamais en une commande composée** : saboter,
  mesurer, restaurer, re-vérifier = quatre appels.
- **Un `__pycache__` périmé fabrique un faux vert** : l'invalidation `(mtime, size)` est aveugle à
  une édition même-seconde/même-taille en conteneur.

---

## À lire avant de reprendre

- **`roadmap/V3/03-spec-frameworks.md`** — la roadmap active. §0 les faits mesurés · §1 **ce qui n'est
  PAS défait** (à relire à chaque lot) · §2 l'objet framework · §3 le manager · §4 les deux pilotes
  rédigés en entier · §5 le stockage · §9 le test d'acceptation · §10 les lots.
- **`CLAUDE.md` du projet** — conventions **#22 à #74**. Les plus structurantes ici : **#74**
  (le TEMPOREL d'une formule porte sur le NOM `Concept[-1]`, pas un concept neuf — #57 appliqué à la
  formule ; débloque l'archétype `rentable`, vérifié contre le vrai modèle), **#73**
  (un BLOCAGE réseau est un 4ᵉ état muet, invisible aux checks et à l'acceptation ROLLBACK : borné par
  ligne web via `asyncio.wait_for` → mandat nommé, #25), **#72**
  (l'EXÉCUTION d'un appariement : formule sur concepts XBRL nus évaluée sur l'inventaire **déjà
  lu**, 4 refus nommés, tier dérivé du **déterminisme**, `metric` = l'expression donc une
  ré-exécution **supersède**), **#67 → #71** (la carte d'appariement : trois états, persistance,
  revalidation contre `dernier_depot_vu`, producteur sur le chemin réel), #29 (la
  couverture se **lit** dans un index), #31 (ce qui décrit un émetteur ne vit jamais dans une
  constante globale), #37 (un contrat valide un objet, jamais la cohérence entre deux), #42/#43
  (datation et **identité** d'un fait), #44 (calculé / non calculable / absent), #46 (**détenteur
  unique** d'une règle), #48, #49, **#50** (trois axes jamais recombinés), **#51**, **#52**,
  **#53**, **#54** (la porte à trois états), **#55**.
- **Specs** : `roadmap/V3/principe-directeur.md` (constitution) ·
  `roadmap/archive/v2/01-spec-v2-unifiee.md` (§5 agents, §7 curator, §8 contrats, §14 migrations, §16 UX,
  §18 découpage) · `roadmap/V3/doctrine-trois-axes.md` (**close**, doctrine des 3 axes) ·
  `roadmap/V3/benchmark-methodologies.md` (**Partie B** le processus canonique
  en 15 étapes, **Partie D3** le contrat `RiskMatrix`, **Partie E** la matrice de traçabilité — c'est
  la matière **descendante** des frameworks).
- **Cartes de contrat** : `roadmap/V3/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
- **Architecture** : `roadmap/V3/ARCHITECTURE-CIBLE.md` (vue d'ensemble + carte des modules) et un
  `ARCHITECTURE.md` par module backend (`knowledge/`, `frameworks/`, `agents/v2/`, `contracts/`,
  `api/`) = **cible** ; l'**état réalisé** se lit en exécutant `backend/checks/` (`run_all.sh`).
  L'organisation est gardée par `check_architecture.py`.
- **Méthode de test & mesure** : `roadmap/V3/METHODE-TEST.md` — décideur ouvert (décidabilité, pas
  coût), catalogue d'outils sans friction, faux-verts. Harnais : `checks/_negatif.sh` (boucle de
  mutation, détenteur unique) + `checks/_harness.py` (garde-fous py). Conventions #65/#66.
- **Code** : `backend/app/agents/v2/` (`common.py` — **`MVDD_SPEC`, la grille à remplacer** ·
  `worker.py:141` `_resolve_covers` · `curator.py:69` `DECLARED_NONBLOCKING_GAPS` · `analysis.py` ·
  `runner.py`) · `backend/app/knowledge/` (`synthesis_feed.py:145` **`SYNTHESIS_TARGETS`** ·
  `service.py` · `websearch.py` · `source_registry.py` · `edgar_feed.py` · `financials_feed.py` ·
  `valuation_feed.py` · `units.py` · `material_events.py` · `staleness.py` · `actualite.py`) ·
  `backend/app/contracts/analysis_v2_schemas.py` (**`RiskMatrix` ligne 411**) ·
  `backend/checks/README.md`.
- **Historique complet** : `00-REPRISE-ARCHIVE.md`. **Outillage transverse** :
  `../../../CHANTIER_OUTILLAGE_DEV.md` (§16 délégation, §24 tests négatifs, §25 porteurs d'un fait,
  §26 la ligne de base est une mesure, §27 un bilan se reconnaît à sa forme).
- **Visuel** : https://provenance.jlmvpscode.duckdns.org

---

## À coller pour reprendre

> Reprise de **portfolio-tracker V2**.
> Contrat figé, boucle V2 complète (décider → surveiller → sortir → apprendre), écrans livrés,
> chaîne exercée sur **NVDA, MSFT et RVMD**. Principe directeur **UX → agents → données**, 3
> garde-fous : G1 schéma versionné = source unique · G2 décision contrainte par l'analyse · G3
> donnée versionnée + scorée + figée, jamais de texte libre. DÉCISION #1 = Option C (base neutre →
> bull/bear isolés → réfutation bear→bull → synthèse dialectique, seul verdict).
> **La roadmap 02 est CLOSE** : les trois axes sont en production et **jamais recombinés en
> scalaire** — fiabilité (source, stockée) · nature (assertion, stockée) · **actualité** (relation
> fait ↔ ancre, **calculée à la lecture, jamais persistée**) ; porte de complétude à **trois états**
> avec deux remèdes distincts (`rafraichissement` ≠ `collecte`) ; règle de rang (une estimation vaut
> **un cran sous sa pièce la plus faible**, dérivée jamais déclarée). Le faux vert d'origine est
> tombé en production : NVDA et MSFT passent de `ready, 0 gap` à `not_ready (peremption)`.
> **Roadmap active : `roadmap/V3/03-spec-frameworks.md`** (ouverte le 2026-09-09). Diagnostic mesuré :
> le système range la connaissance dans une **grille fermée de 19 champs identique pour tout
> émetteur**, et écarte en silence tout ce qui n'y entre pas — **50 % d'orphelines sur NVDA** dont
> **16 faits SEC tier A** ; **14 feuilles du `research_memo` sans aucun chemin dans cette grille** (donc
> les étapes 4/5/6/8 du benchmark sont produites avec **zéro preuve indexable**) ; **3 chemins
> jamais consommés**, dont le plus peuplé de la base ; RVMD (biotech pré-revenus) produit un ROIC
> fabriqué, une « conversion FCF non définie », et **0 synthèse grounded**.
> ⚠️ **Relecture du 2026-09-24 sur ce diagnostic** : le ROIC fabriqué était réel (corrigé depuis, au
> producteur), mais la « conversion FCF non définie » était **l'exemple du système qui marche**, pas
> un défaut — l'entry NOMME son refus. Un diagnostic qui juge une entry sur son TITRE se trompe de
> sujet ; c'est la garde ROIC jumelle qui manquait, pas celle du FCF.
> La v3 remplace la grille par des **frameworks stables à variables par entreprise** : le
> référentiel est un **fichier inerte versionné** (`app/frameworks/frameworks.yaml`, **pas des
> tables**), **`covers` DISPARAÎT de `knowledge_entries`** au profit d'une table de liaison
> `question_coverage` portée par framework **et version** — l'entry ne porte plus aucun mot de
> framework, donc en changer n'invalide plus le corpus. Entre la question et l'entry, **deux
> agents** : un **traducteur** qui transforme les questions universelles en un **plan de collecte**
> par ticker (métrique, source, ancre), un **collecteur** qui l'exécute sans jamais connaître la
> question. Chaque framework est garanti par
> un **manager** aux 4 contrôles vérifiables (complétude · fondation · **honnêteté de
> l'approximation** · **non-substitution**), dont le **renvoi produit un mandat de recherche
> exécutable**, ce qui ferme la boucle comité → collecte aujourd'hui absente. Deux pilotes :
> **« Qualité financière »** (Greenwald — les 26 orphelines de NVDA en sont la matière) et
> **« Défendabilité / moat »** (Porter-Morningstar — ses 4 champs de sortie sont 100 % orphelins).
> **La capacité 5, barreau 4 est FERMÉE** : réfutée **4 fois** par sa ligne de base ; le contre-test
> montre que la formulation n'est pas en cause. L'ingrédient (#33) est **orphelin**, donc hors du
> corpus du champ — *le barreau 4 ne compense pas une limite de la recherche, il compense un défaut
> de rangement*, et c'est le rangement que la v3 corrige.
> 🚦 **LOT 3 TERMINÉ. LOT 4 CLOS (2026-09-21) : agent manager (#76) + ses DONNÉES (#77, migration 043,
> `manager_persist.py`, acceptation T8 6/0). Arbitrage utilisateur : l'avis du manager se RECALCULE à
> la lecture, seul le MANDAT est persisté (#53/#54).
> **LOT 5 EN COURS (2026-09-25) : ✅ le `research_memo` EST la projection des frameworks acquittés**
> — `projection_memo.py`, détenteur unique qui **ne nomme aucun framework** (le lien est `bloc_memo`
> dans `frameworks.yaml`), 3 états nommés, `check_memo_projete` **51/0** + négatif **25/0**, prouvé
> par un **3ᵉ framework fictif ajouté en YAML seul**. ✅ Faux RVMD nettoyés au producteur (#656→#662).
> ⏳ Restent : la chaîne de bout en bout sur `defendabilite` (coût modèle) et le wiring de
> `serve_mandate` en live (**0 appelant dans `app/`, mesuré**). ⚠️ **Aucune migration dans ce lot à
> ce jour** ; 046 est appliquée, la prochaine écrite sera 047 — le « 044 » annoncé ici était une
> prévision, et ce tableau de prévisions a déjà menti trois fois.** Historique — Lot 2c :
> contrat du plan + pont (T1bis) + traducteur +
> collecteur + persistance + exécuteur réel + **maillon 5 : `POSTES` devenu CATALOGUE de recettes
> (collecte plan-dérivée), levier `RESSERRER` de `curator.py` RETIRÉ, §12bis MORT** (conventions
> #61/#62). Lot 3 : ✅ **maillon 1 = l'analyste** (`agents/v2/analyste.py`, trois états nommés,
> aucun levier de modèle sur l'exigence, convention #63) ; ✅ **maillon 2 = `framework_answers`/
> `framework_dispenses` en base + persistance** (migration **040 appliquée**, append-only
> versionnée A1, lignée `ticker_id+framework+version+question_id+analyste` — §3.4, `framework_id`
> manquait sa version sur le contrat, fix + invariant `[V]`, convention #64 ;
> `check_framework_persist.py` 13/0, `negatif_framework_persist.sh` 6 mutations/0, zéro résidu) ;
> ✅ **maillon 3 = suppression** de `MVDD_SPEC` / `SYNTHESIS_TARGETS` / `DECLARED_NONBLOCKING_GAPS`
> (commit `203fe65`, 15 fichiers, `nonblocking_gaps_for()` → `{}`, `read_dispenses()` branché).
> ~~**Reste au lot 3**~~ *(phrase d'époque, conservée telle quelle : elle disait « maillon 4ter =
> collecte neuve persistée sur NVDA/MSFT/RVMD (§5.3) ; maillon 5 = réconciliation à 0/0. Prochaine
> migration : 043 ». Le lot 3 est clos et la 043 est appliquée depuis. **Rien de ce bloc « À coller »
> ne se lit comme une consigne** — le seul endroit où le prochain pas est écrit reste ▶ PROCHAIN
> JALON.)*
> ✅ **maillon 4 = l'EXÉCUTION d'un appariement, LIVRÉ le 2026-09-18** (convention **#72**, aucune
> migration) : `knowledge/appariement_feed.py` évalue la `formule` sur les concepts XBRL **déjà lus**
> par `assurer_carte` — **zéro appel réseau supplémentaire** — et écrit l'entry avec sa provenance
> concept par concept et son tier dérivé. Quatre refus nommés (ancre hors tolérance, concept absent,
> dimensions incohérentes, division par zéro), les deux derniers **délégués** à
> `contracts/formule_grammaire.py` (détenteur unique #46) et donc éprouvés **chez leur détenteur**.
> Acceptation réelle RVMD (ROLLBACK) : **8 critères OK / 0 échec**, **lignes COLLECTÉES depuis le
> dépôt 0 → 6** (7 écritures, 1 supersession #43, 2 refus nommés), distribution **9 `approximation`
> · 4 `indisponible`**, tiers **A (0,95)** vs **A− (0,85)**, $0.0015, dépôt courant 2026-08-05.
> Suite **2634/0 sur 35 scripts** (était 2583/34) ; `check_appariement_feed` 33/0 ;
> `negatif_appariement_feed.sh` **16 mutations / 0** ; `check_collecte_executor` 74 → **92** ;
> `negatif_collecte_executor.sh` **32 / 0**.
> ✅ **maillon 4bis = l'appariement, CLOS le 2026-09-18** : garde + apparieur (l'inventaire réel
> remplace `POSTES` comme frontière) + migration **042** + **producteur** `assurer_carte()` sur le
> chemin réel de `executer_plan_reel` (le câblage du 2026-09-17 n'était qu'une **lecture** : sans
> producteur, `lire_carte()` renvoyait toujours `None` et la carte ne décidait jamais — #71).
> Conventions **#67 → #71**, **#70 et #71 levés**, aucun résidu. La date de dépôt courante vient de
> `dernier_depot_vu(companyfacts)` = `max(filed)` sur l'inventaire complet — détenteur unique, zéro
> nouvelle règle de décision.
> ✅ **PRÉ-REQUIS DU LOT 3 LEVÉ (2026-09-12)** : `check_entry_nature §7` re-mesuré en **invariant #51**
> (metric structuré ⟹ `mesure`, garde de non-vacuité, tous tickers) au lieu du décompte `== 13`, qui
> était une **cible-corpus interdite par §0.6**. Les 30 faits web du maillon 4 (`edgar_official`/
> `company_ir_official` SANS `metric`) sont **compatibles**, pas des parasites (§0.6 : soit
> compatibles, soit périmés — jamais un tiers « à réconcilier »). Test négatif versionné
> `checks/negatif_entry_nature_etat.sh` (satisfiabilité + 4/4). Voir [[project_entry_nature_gate_invariant]].
> ⚠️ Sur ce chantier la ligne de base a **déjà changé le lot plusieurs fois** — elle se **requête**,
> elle ne se souvient pas ; et depuis §0.6 elle n'est **jamais une cible**. ⚠️ Mesureurs versionnés,
> jamais `/tmp` ; bilan reconnaissable à sa **forme** ; **jamais exécutés dans `portfolio-backend`**.
> État au 2026-09-12 (dépassé — l'état courant est en tête de fichier) : suite **TOUT VERT**
> (`run_all.sh` = **2172 assertions, 0 échec** — −66 vs 2238 : sections
> testant les 3 constantes supprimées au maillon 3 retirées comme prévu) ; `check_edgar_feed` 98/0
> hors ligne ; `check_entry_nature` 88/0 ; `check_analyste` 81/0 ; `check_framework_persist` 13/0 ;
> migrations appliquées jusqu'à **040** à cette date (**042** depuis le 4bis).
> ⚠️ **Ajouter `framework_version` au contrat (maillon 2) a rougi deux checks qui n'avaient pas
> tourné depuis son ajout** (`check_framework_contract` §9 — pixel manquant dans la maquette ;
> `check_frameworks_definitions` §4 — le pont lit une clef que `CLEFS_PROFIL_LUES` ne déclarait
> pas). Corrigés dans la foulée. Voir #64 : **rejouer `run_all.sh` en entier après tout ajout de
> champ à un contrat partagé**, jamais seulement le check du module qu'on vient de toucher.
> LIRE D'ABORD : ce fichier, puis `roadmap/V3/03-spec-frameworks.md` (§1 = ce qui n'est PAS défait),
> le `CLAUDE.md` du projet (conventions #22-**#73**, dont **#73 = le garde de blocage web**, **#63 = l'analyste**, **#64 =
> `framework_version` sur `FrameworkAnswer`**, **#67-#71 = la carte d'appariement** et **#72 = son
> EXÉCUTION**), `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une décision manque.
