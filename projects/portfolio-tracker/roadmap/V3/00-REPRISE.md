---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-13
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · boucle V2
  complète (décider → surveiller → sortir → apprendre) · écrans UX-1/2/3 livrés · chaîne exercée
  sur NVDA, MSFT et RVMD. **LOT 2c TERMINÉ le 2026-09-12** — le maillon 5 est livré : `POSTES` est
  devenu un CATALOGUE de recettes (`edgar_feed`), le socle EDGAR ne collecte plus que les postes
  réclamés par le plan (`run_edgar_feed(metrics=…)` câblé par `collecte_executor.postes_edgar_du_plan`),
  le levier `RESSERRER` de `curator.py` est RETIRÉ (`_exigences` lit `MVDD_SPEC` tel quel), et **le
  §12bis hérité est MORT** avec le socle data-first (conventions #61/#62). Migrations appliquées
  jusqu'à **040** ; maillon 5 (lot 2c) = **code seul, aucune migration, aucun réseau**.
  **LOT 3 EN COURS depuis le 2026-09-13** : maillon 1 (l'analyste, convention #63) et maillon 2
  (`framework_answers`/`framework_dispenses`, migration 040, convention #64) sont ✅ — détail dans
  la checklist du lot 3 ci-dessous, ne pas dupliquer ici.
  ✅ **PRÉ-REQUIS DU LOT 3 LEVÉ le 2026-09-12 : `check_entry_nature §7` re-mesuré en INVARIANT, la
  suite est TOUT VERT (`bash checks/run_all.sh` = 2139 assertions, 0 échec).** L'ancien `== 13` était
  un **décompte du banc d'essai promu en cible**, interdit par §0.6 (« les données en base ne dictent
  jamais la roadmap ») : il confondait `entry_type=fact_financial` avec « sortie déterministe » et a
  rougi (lecture **43**) dès que le collecteur du maillon 4 a écrit 30 faits web `edgar_official`/
  `company_ir_official` SANS `metric` — **compatibles et frais** (10-Q 2026-06-30, tous `mesure`),
  pas des parasites. §7 revérifie désormais l'invariant #51 sur l'état : **tout fait à recette
  déterministe (un `metric` structuré, écrit par les 8 producteurs, jamais par le search-worker) est
  `mesure`**, sur TOUS les tickers, avec garde de non-vacuité — jamais un décompte. Test négatif
  versionné `checks/negatif_entry_nature_etat.sh` (satisfiabilité + 4 mutations/4, chacune rouge sur
  son assert nommé). Le corpus RVMD hérité sera de toute façon re-collecté propre au lot 3 (§5.3).
  Voir [[project_entry_nature_gate_invariant]].
  Roadmap active : **`roadmap/V3/03-spec-frameworks.md`** (ouverte le 2026-09-09) — le référentiel
  d'indexation passe d'une **grille fermée de 19 champs identique pour tous les émetteurs** à des
  **frameworks stables à variables par entreprise**, chacun garanti par un **manager**.
  `roadmap/V3/doctrine-trois-axes.md` est **close** : capacités 0 à 4 livrées, capacité 5
  fermée sur son barreau 4 (« le défaut est en dessous »).
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
| `reconcilier_vocabulaires.{py,sh}` | **5 ok / 2 FAIL** — 14 orphelins + 3 inutilisés | lot 3 |
| `ligne_de_base_frameworks.{py,sh}` | **2 ok / 0 FAIL** — les 6 valeurs de §9.1 confirmées | (mesure, pas un test) |
| `acceptation_frameworks.{py,sh}` | **1 ok / 8 FAIL** — les 8 critères T1-T8 rouges | par lots, les 8 au lot 7 |

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
4. 🔄 **Collecte neuve pilotée par le plan** sur NVDA / MSFT / RVMD (§5.3) — **OUVERT, et bloqué
   par l'APPARIEMENT ingrédient → donnée EDGAR.** La collecte réelle **ne doit pas partir** tant
   que la garde décrite au maillon 4bis n'existe pas : un faux appariement écrit un nombre exact en
   face de la mauvaise question (#43/#60), et rien en aval ne le rattrape.
   **Ce qui a été fait le 2026-09-14** (migration **041** appliquée, suite **2429/0**) :
   · `fetch_company_facts()` (`knowledge/edgar_facts.py`) — l'INVENTAIRE complet des concepts
     us-gaap déposés par un émetteur, là où `companyconcept` ne peut jamais révéler un poste qu'on
     ignorait ; · `tools/cartographier_xbrl.py` + `.sh` — le mesureur versionné qui le lit ;
   · `POSTES` enrichi **8 → 33** ; · le traducteur NOMME le poste (`CollectionPlanItem.poste`,
     migration 041, `LigneAveugle.poste`) et l'appariement par sous-chaînes est **supprimé**
     (pierre tombale dans `collecte_executor.py`).
   **LA MESURE, qui est le vrai livrable du jour** (gratuite, `--plan-only`, ~$0,01 au total) :
   | passage | lignes EDGAR | justes | fausses |
   |---|---|---|---|
   | avant (sous-chaînes, 8 postes) | 7 | 2 | 5 |
   | catalogue 33 + poste nommé, prompt v1 | 34 | ~12 | **~22** |
   | + prompt durci (un TEST à faire passer au poste) | 11 | **11** | **0** |
   | **le même prompt, MSFT rejoué** | **15** | 5 | **10** |
   ⚠️ **La dernière ligne disqualifie le remède par prompt** (`feedback_jugement_modele_instable_
   entre_passages`). Le durcissement est conservé et **gardé** (`check_collecte_executor` §3bis :
   le critère, les opérations disqualifiantes, les contre-exemples mesurés) — mais ces asserts
   gardent l'ÉNONCÉ, **jamais le comportement**, et le disent. ⚠️ Inventaire des 627/562/269
   concepts déposés contre **33** au catalogue : le catalogue regardait par le petit bout.
   ⚠️ **Sur les 3 tickers, les 4 postes utiles sont les MÊMES** (`net_income`,
   `operating_cash_flow`, `cash_and_lt_debt`, `long_term_debt_current`) — mais voir 4bis : cela ne
   veut PAS dire que le poste se fige dans le référentiel.
4bis. ⬜ **L'APPARIEMENT PAR TICKER — le maillon manquant** (conçu avec l'utilisateur le
   2026-09-14, **doctrine tranchée, rien à remesurer**). Ce que fait un analyste en fonds : il
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
5. ⬜ **Réconciliation à 0/0** via `tools/reconcilier_vocabulaires.py`.

> **▶ PROCHAIN JALON = lot 3, maillon 4bis** (l'appariement par ticker : inventaire → carte
> persistée → trois états). Les trois arbitrages de doctrine sont **tranchés** ci-dessus : ne pas
> les rouvrir, les implémenter. Le maillon 4 (collecte réelle) attend derrière. Prochaine
> migration : **042** (041 appliquée le 2026-09-14 — `collection_plan_items.poste`).
> Reprise conseillée : **NOUVELLE conversation** (le contexte de celle-ci est consommé par la
> mesure, et la conception est écrite ici), et **OPUS** — contrairement au maillon 4 qui ne
> demandait que de conduire des appels, 4bis est de la conception : trois états à tenir, une règle
> de tier à un discriminant, et un jugement de modèle à **encadrer par du code** après qu'on a
> mesuré qu'il ne tient pas seul. Le critère de succès ne s'énonce pas en trois lignes
> (`feedback_deleguer_recherche_pas_jugement`), donc ce n'est pas délégable à Sonnet.
> **Session du 2026-09-14 terminée** — suite **2429/0**, migration 041 appliquée, rien de déployé,
> **aucune collecte réelle lancée** (et c'est volontaire).

### Découpage des lots suivants (spec v3 §10)

| Lot | Contenu | Migration |
|---|---|---|
| 0 | ✅ **Ligne de base** (ci-dessus) — 2026-09-09 | — |
| 1 | ✅ **Contrat** `FrameworkAnswer` + `FrameworkMandate`, pont relationnel **en Python** (#37), carte de provenance, écran niveau 3 en maquette — 2026-09-09 | — |
| 2a | ✅ **Le référentiel** — 13 questions en données inertes, 39/0, négatif 22/22 — 2026-09-10 | — |
| 2b | **Archivage et dévocabularisation** : `archive_v2` (rien de détruit) · `knowledge_entries` amaigrie de **8 colonnes** (7 à zéro écriture **+ `covers`**) · `question_coverage` créée, portée par framework **et version** · `entry_type`/`report_type` dévocabularisés | **036** |
| 2c | ✅ **TERMINÉ** : traducteur → plan → collecteur (§3.6) · persistance · exécuteur réel + chaîne runtime · **`POSTES` dérivé du plan + retrait du levier `RESSERRER` + mort de §12bis (maillon 5, 2026-09-12)** | **039** ✅ |
| 3 | 🔄 **EN COURS** — ✅ **l'analyste** (maillon 1, 2026-09-13) · ✅ **`framework_answers` / `_dispenses` en base + persistance** (maillon 2, 2026-09-13, migration **040 appliquée**) · **suppression** de `MVDD_SPEC`, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS` · **collecte neuve pilotée par le plan** sur NVDA / MSFT / RVMD | **040** ✅ |
| 4 | Le **manager** et ses 4 contrôles · le renvoi qui produit un mandat consommé par le **collecteur** | 041 |
| 5 | Le `research_memo` devient la **projection** des frameworks acquittés · réconciliation à 0/0 | 042 |
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

**Le système est exercé, pas prototypé.** La chaîne complète a tourné de bout en bout sur trois
émetteurs, et on connaît ses modes de panne — c'est le principal actif du chantier.

| | NVDA (cas-pilote) | MSFT (généralité) | RVMD (banc d'essai) |
|---|---|---|---|
| Socle | 52 entries (32 A / 15 B) | 51 entries, 19/19 champs, 0 `llm_memory`, ≈ $0,19 | 27 actives (13 déterministes + 14 qualitatives) |
| Readiness | **`not_ready (peremption)`**, 9 champs périmés, 7 mandats, **0 collecte** | **`not_ready (peremption)`**, 9 champs périmés, **0 collecte** | **rapport #28** — `not_ready`, **9 collecte / 4 rafraîchissement** |
| Chaîne | research → bull/bear → réfutation → synthèse = `PROCEED_AVEC_CONDITIONS` | idem, ≈ $0,018 | **0 synthèse grounded** — 3 des 4 cibles vides |

- **Suite : `bash checks/run_all.sh` = TOUT VERT (2139 assertions, 0 échec, mesuré le 2026-09-12
  après le re-mesurage de §7).** `check_edgar_feed` **98/0** et **hors ligne** (§12bis mort → ne
  requiert plus `CHECK_DB_URL`) ; `check_entry_nature` **88/0** (§7 = invariant #51, cf. frontmatter).
  Seuls `check_entry_nature §7` et `check_collecte_persist` gardent le montage réseau `coolify` +
  `CHECK_DB_URL`. `run_all.sh`
  porte les montages `/contract_frozen` (sans lui 4 scripts sous-comptent en sortant à 0) **et
  `/roadmap`** (sans lui `check_frameworks_definitions` §7 sort en échec au lieu de se sauter).
  ⚠️ **Ne pas le réécrire dans `/tmp`** : la version jetable sous-comptait 47 assertions en silence
  (`CHANTIER_OUTILLAGE_DEV.md` §27).
- **Migrations appliquées jusqu'à 040** (036/037/038 lot 2b, **039** lot 2c — tables du plan de
  collecte, **040** lot 3 maillon 2 — `framework_answers`/`framework_dispenses`).
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
   ⚠️ Trois d'entre elles sont des **faux** au sens de la v3, pas des périmées : #190 fabrique un
   ROIC pour une société sans revenus, #191 s'intitule « conversion FCF **non définie** », #186
   range l'incidence du cancer du pancréas sous `marche.croissance_marche_historique`. Le lot 3 les
   rendra visibles comme orphelines **nommées** ; l'arbitrage reste humain.
   ⚠️ **Mesuré le 2026-09-12** : RVMD porte **43** entries déterministes actives (vs 13 au banc
   d'essai) — dont **30 faits web SANS `metric`** (25 `edgar_official` + 5 `company_ir_official`),
   écrits par le collecteur du maillon 4 (search-worker sur sec.gov / IR). ✅ **Ces 30 ne sont PAS des
   parasites — §0.6 les qualifie de compatibles** (frais, cités, tous `mesure`) : on ne les
   réconcilie donc pas ici, et §7 a été re-mesuré en invariant plutôt que de compter le corpus (cf.
   frontmatter, [[project_entry_nature_gate_invariant]]). Restent seulement les **faux au sens v3**
   (#190 ROIC fabriqué, #191 « conversion FCF non définie », #186 mal rangé) — jugement humain, que le
   lot 3 rendra visibles comme orphelines nommées, et que sa collecte neuve (§5.3) superséder a.
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
- **`CLAUDE.md` du projet** — conventions **#22 à #66**. Les plus structurantes ici : #29 (la
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
> **16 faits SEC tier A** ; **14 feuilles du `research_memo` sans aucun chemin d'indexation** (donc
> les étapes 4/5/6/8 du benchmark sont produites avec **zéro preuve indexable**) ; **3 chemins
> jamais consommés**, dont le plus peuplé de la base ; RVMD (biotech pré-revenus) produit un ROIC
> fabriqué, une « conversion FCF non définie », et **0 synthèse grounded**.
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
> 🚦 **LOT 2c TERMINÉ (2026-09-12). LOT 3 EN COURS (ouvert 2026-09-13), 3 maillons sur 5 livrés.
> PROCHAIN PAS = LOT 3, MAILLON 4.** Lot 2c : contrat du plan + pont (T1bis) + traducteur +
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
> **Reste au lot 3** : maillon 4 = collecte neuve pilotée par le plan sur NVDA/MSFT/RVMD (§5.3) ;
> maillon 5 = réconciliation à 0/0. Prochaine migration : **041**.
> ✅ **PRÉ-REQUIS DU LOT 3 LEVÉ (2026-09-12)** : `check_entry_nature §7` re-mesuré en **invariant #51**
> (metric structuré ⟹ `mesure`, garde de non-vacuité, tous tickers) au lieu du décompte `== 13`, qui
> était une **cible-corpus interdite par §0.6**. Les 30 faits web du maillon 4 (`edgar_official`/
> `company_ir_official` SANS `metric`) sont **compatibles**, pas des parasites (§0.6 : soit
> compatibles, soit périmés — jamais un tiers « à réconcilier »). Test négatif versionné
> `checks/negatif_entry_nature_etat.sh` (satisfiabilité + 4/4). Voir [[project_entry_nature_gate_invariant]].
> ⚠️ Sur ce chantier la ligne de base a **déjà changé le lot plusieurs fois** — elle se **requête**,
> elle ne se souvient pas ; et depuis §0.6 elle n'est **jamais une cible**. ⚠️ Mesureurs versionnés,
> jamais `/tmp` ; bilan reconnaissable à sa **forme** ; **jamais exécutés dans `portfolio-backend`**.
> État : suite **TOUT VERT** (`run_all.sh` = **2172 assertions, 0 échec** — −66 vs 2238 : sections
> testant les 3 constantes supprimées au maillon 3 retirées comme prévu) ; `check_edgar_feed` 98/0
> hors ligne ; `check_entry_nature` 88/0 ; `check_analyste` 81/0 ; `check_framework_persist` 13/0 ;
> migrations appliquées jusqu'à **040** (maillon 3 = code seul, aucune migration).
> ⚠️ **Ajouter `framework_version` au contrat (maillon 2) a rougi deux checks qui n'avaient pas
> tourné depuis son ajout** (`check_framework_contract` §9 — pixel manquant dans la maquette ;
> `check_frameworks_definitions` §4 — le pont lit une clef que `CLEFS_PROFIL_LUES` ne déclarait
> pas). Corrigés dans la foulée. Voir #64 : **rejouer `run_all.sh` en entier après tout ajout de
> champ à un contrat partagé**, jamais seulement le check du module qu'on vient de toucher.
> LIRE D'ABORD : ce fichier, puis `roadmap/V3/03-spec-frameworks.md` (§1 = ce qui n'est PAS défait),
> le `CLAUDE.md` du projet (conventions #22-**#64**, dont **#63 = l'analyste** et **#64 =
> `framework_version` sur `FrameworkAnswer`**), `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une
> décision manque.
