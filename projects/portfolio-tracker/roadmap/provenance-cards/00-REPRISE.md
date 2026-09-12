---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-12
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · boucle V2
  complète (décider → surveiller → sortir → apprendre) · écrans UX-1/2/3 livrés · chaîne exercée
  sur NVDA, MSFT et RVMD. État au 2026-09-12 : **2 107 assertions / 29 scripts**, un seul FAIL, le
  §12bis HÉRITÉ (socle EDGAR data-first, en voie de retrait au maillon 5 du lot 2c). Migrations
  appliquées jusqu'à **039** (les tables du plan de collecte : `collection_plans`,
  `collection_plan_items`, `framework_mandates`). **Lot 2c aux 6/6 maillons sur 6 pour la COLLECTE** :
  contrat du plan + pont (T1bis) + traducteur + collecteur (cœur déterministe) + persistance + **l'EXÉCUTEUR
  RÉEL câblé et exercé contre le vrai monde (2026-09-12, `agents/v2/collecte_executor.py`)** —
  dispatch question-aveugle EDGAR/web, chaîne runtime `executer_collecte_framework`, check 31/0 +
  négatif 7/7, suite 2 107/1. Run réel RVMD : **11 liens + 3 mandats** (1 inobtenable T1bis + 2
  echec_collecte), run ciblé NVDA : le seul niveau brut (`qf_2.resultat_net`) lié au socle EDGAR.
  **Reste le maillon 5** : `POSTES` dérivé du plan + retrait du levier `RESSERRER` de `curator.py`,
  **où meurt le §12bis hérité**.
  Roadmap active : **`roadmap/03-spec-frameworks.md`** (ouverte le 2026-09-09) — le référentiel
  d'indexation passe d'une **grille fermée de 19 champs identique pour tous les émetteurs** à des
  **frameworks stables à variables par entreprise**, chacun garanti par un **manager**.
  `roadmap/02-spec-autorite-vs-actualite.md` est **close** : capacités 0 à 4 livrées, capacité 5
  fermée sur son barreau 4 (« le défaut est en dessous »).
---

# Prompt de reprise — portfolio-tracker V2

> **Ce fichier ne s'empile pas.** Le récit des sessions vit dans `00-REPRISE-ARCHIVE.md` (copie
> conforme, rien de résumé), les règles durables dans le `CLAUDE.md` du projet (conventions
> numérotées), les enseignements d'outillage transverses dans `../../../CHANTIER_OUTILLAGE_DEV.md`.
> Ici : **l'état atteint, ce qui reste, et les pièges à ne pas re-découvrir.** Protocole
> d'éviction : `CONTROL_SYSTEM.md` §5.

---

## 🎯 Roadmap active

### **`roadmap/03-spec-frameworks.md`** — ouverte le 2026-09-09

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
| Carte de provenance champ par champ | `roadmap/provenance-cards/framework_answer_card.md` |
| Écran niveau 3 en maquette | `roadmap/provenance-cards/framework_screen_niveau3.md` |

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

⚠️ **Le §12bis reste ROUGE (46 < 50), et c'est diagnostiqué, pas à colmater.** Le seuil « 50 » n'est
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

### 🚦 Prochain pas — **lot 2c** (audit des 2 principes rendu le 2026-09-10)

L'audit de la spec complète a produit **10 écarts (V1–V10)**, dont deux structurants, tous deux
consignés dans la spec. **V5** (`covers` re-vocabularisée) est traité par la 036 + `question_coverage`.
Reste **V1**, qui est le cœur du lot 2c :

- **V1** — le socle EDGAR collecte **avant et indépendamment de toute question** : `POSTES` est
  une liste de **8** métriques écrites à la main qui servent **4** des **33** ingrédients essentiels,
  3 postes ne répondent à rien, et les 12 ingrédients `mo_*` n'ont aucune source sans que rien ne le
  dise. → `POSTES` devient **dérivé du plan de collecte** (spec §3.6), par la chaîne à deux agents
  traducteur → plan persisté → collecteur. Retrait du levier `RESSERRER` de `curator.py` dans le
  même lot.

**Découpe du lot 2c, ordre imposé `contrat → agent → données` :**

1. ✅ **Le contrat du plan de collecte** (2026-09-11) — `app/contracts/collection_plan_schema.py`
   (`CollectionPlan` / `CollectionPlanItem`, strict). Le statut d'une ligne porte **exactement** sa
   charge (`traduit` ⟺ métrique+source+ancre · `inobtenable` ⟺ motif seul → mandat) ; le 3ᵉ état
   `omis` **n'est pas un statut** (absence de ligne, constatée au pont) ; ce que le traducteur n'a
   pas le droit de porter (`plancher_tier`/`nature_attendue`/`essentiel`, #59) est **absent du
   contrat**, donc rejeté par `extra='forbid'`, pas gardé par un `if`. Check
   `check_collection_plan_contract.py` **22/0**, négatif bidirectionnel
   `negatif_collection_plan_contract.sh` **satisfiabilité + 9 mutations / 9**, carte
   `provenance-cards/collection_plan_card.md`. Suite **2 030**.
2. ✅ **Le pont `valider_pont_collection_plan`** (2026-09-11, `agents/v2/frameworks.py`, lève
   `CollectionPlanRefused`) : invariants relationnels `[N]` framework+version · `[O]` archétype
   déclaré · `[P]` chaque `(question_id, ingredient_id)` résout · `[Q]` pas de collecte sur une
   question sans objet · **`[R]` chaque ingrédient essentiel d'une question applicable a une
   ligne — omission = plan REFUSÉ (c'est T1bis, §9.2)**. Check §6 (fixture construite depuis le
   référentiel réel, complète par construction), négatif 7 mutations de pont. Suite **2 039**.
3. ✅ **L'agent 1, le traducteur** (2026-09-11, `agents/v2/traducteur.py`). Moitié déterministe :
   `questions_applicables` (filtre par archétype), `contexte_traducteur` (**lever-free : ni
   `plancher_tier` ni `nature_attendue`**, #59), orchestration `traduire` où **l'en-tête du plan est
   posé par le CODE** (le modèle ne produit que `TraducteurSortie.items`), sortie validée contrat +
   pont. Prompt en **code** (`_TRADUCTEUR_SYSTEM_PROMPT`, comme la synthèse #54). Check
   `check_traducteur.py` **15/0**, négatif **satisfiabilité + 6 mutations**.
   **Acceptation contre le vrai modèle PASSÉE** (`tools/acceptation_traducteur.{py,sh}`, ne persiste
   rien, ~$0.0012) : NVDA (rentable) → 30 lignes, 20 essentiels couverts, `cout_du_capital` sorti en
   **traduit-vers-web** (WACC via données de marché — l'une des deux issues licites de §3.6) ; RVMD
   (pre_revenus) → seules qf_4/6/7 (qf_1/2/3/5 correctement exclues), 13 traduits + **1 inobtenable
   honnête** (`qf_4.couverture_des_interets` : biotech sans dette → mandat).
   **RÈGLE D'ANCRAGE resserrée** (2026-09-11, re-testée) — améliore réellement : NVDA ancre « clôture
   fin janvier » (émetteur-conscient) ; RVMD raisonne désormais sur le **jalon clinique** (une ligne
   explicite). ⚠️ **Reste partiel** : la ligne phare *cash burn* de RVMD retombe encore sur « clôture
   du trimestre ». **Non sur-optimisé sur 1 ticker à dessein** → à traquer par l'**éval multi-tickers**
   (backlog #9), pas par du tuning sur RVMD seul. Resynchro du prompt en `agent_prompts` (#19/#39) au
   câblage runtime.
4. ✅ **L'agent 2, le collecteur** + l'aiguilleur — **cœur déterministe + persistance livrés**
   (2026-09-11/12, `agents/v2/collecteur.py`) : `LigneAveugle` (le collecteur **ne voit ni question
   ni ingrédient** → l'entry ne peut porter aucun vocabulaire de framework, principe 2 structurel),
   `aiguiller_plan` (orchestration PURE, exécuteur `collecter` **injecté**) où **la couverture est un
   sous-produit déterministe du dispatch** (`LienCouverture` = colonnes exactes de
   `question_coverage`, écrites par l'aiguilleur qui tient le plan, jamais par le modèle, #57).
   **Trois états, aucune ligne ne s'évapore** : traduit-collecté → lien ; inobtenable → mandat
   (jamais exécuté) ; collecte échouée → mandat `echec_collecte` (jamais un silence, #25). Check
   `check_collecteur.py` **15/0**, négatif **6 mutations**.
   ✅ **Persistance (2026-09-12)** : `agents/v2/collecte_persist.py` (`persist_plan` écrit le plan +
   ses lignes, `persist_aiguillage` écrit `question_coverage` **et** `framework_mandates` dans la
   MÊME transaction, #35/#58, à appeler `async with conn.transaction()`). `check_collecte_persist.py`
   **8/0** vérifie l'**ÉTAT persisté** contre la vraie base en transaction **ROLLBACK** (aucun
   résidu, #47) — plan relu, liens et mandats relus, et §3 le **dernier rempart** : les CHECK SQL de
   la 039 refusent une ligne `traduit` sans métrique / un mandat d'origine inconnue. Négatif
   `negatif_collecte_persist.sh` **satisfiabilité + 5 mutations / 5** (réseau `coolify` + ROLLBACK).
   Câblé dans `run_all.sh` (bloc `coolify` + `CHECK_DB_URL`).
   ✅ **L'EXÉCUTEUR RÉEL + la chaîne runtime (2026-09-12, `agents/v2/collecte_executor.py`, mandat
   utilisateur)** : dispatch question-AVEUGLE sur `source_pressentie` (+ métrique) — dépôt
   réglementaire ET poste du socle → EDGAR (déterministe, tier A) ; tout le reste → search-worker.
   `aiguiller_plan` laissé **intact** (pur, sync, son check+négatif inchangés) : l'exécuteur
   pré-exécute chaque ligne aveugle DISTINCTE (passe async) puis injecte un **lookup sync** — toute
   l'IO est dans `collecte_executor`. `executer_collecte_framework` = la chaîne runtime qui n'existait
   pas (traduire → `persist_plan` → `executer_plan_reel` → `persist_aiguillage`). Tool versionné
   `tools/collecter_framework.py` (`--plan-only` lit le plan+dispatch sans écrire, ~$0.0008).
   Check `check_collecte_executor.py` **31/0**, négatif `negatif_collecte_executor.sh` **7/7**.
   ⚠️ **Deux défauts trouvés par la méthode, pas par un diff** : (a) en lisant le plan NVDA en TEXTE
   avant toute écriture, **5 des 6 lignes routées EDGAR étaient des dérivées** (capital employé,
   croissance du CA, maintenance capex, rapprochement GAAP) qui ne faisaient que *contenir* un alias
   de poste → corruption #43 ; corrigé par détection structurelle de dérivation (opérateurs + mots à
   la **frontière de mot** — `ratio` matchait « opé**ratio**nnel ») ; après correctif, seul le niveau
   brut `qf_2.resultat_net` va au socle (confirme #58 : les 8 postes servent peu d'ingrédients).
   (b) le 1ᵉʳ run réel a **crashé tout le lot** sur un timeout fournisseur d'UNE ligne ; corrigé :
   toute collecte qui échoue → mandat `echec_collecte` motivé (#25), jamais un crash. Convention
   **#60** (CLAUDE.md projet). Exercé en réel : **RVMD** (11 liens + 1 inobtenable T1bis + 2
   echec_collecte ; et la dédup par ligne aveugle vérifiée — deux ingrédients « lignes de crédit non
   tirées » sur l'unique entry #300) + **NVDA ciblé** (chemin EDGAR → entry #318).
5. ⬜ **`POSTES` dérivé du plan** + **retrait du levier `RESSERRER`** de `curator.py`. C'est ici que
   le §12bis hérité disparaît avec le socle data-first.
6. ✅ **Migration 039** (tables `collection_plans`, `collection_plan_items`, `framework_mandates`) —
   **appliquée en prod le 2026-09-11** (`BEGIN…COMMIT`, 3 tables + 2 index + GRANT `portfolio_user`).
   ADDITIVE (rien de détruit, réversible par `DROP TABLE`). Les CHECK SQL **redisent le contrat** du
   plan (dernier rempart, #37) — éprouvés en négatif dans `check_collecte_persist.py` §3.

> **▶ Reprise conseillée : NOUVELLE conversation** (arbitrage 2026-09-12,
> [[feedback_fin_sprint_reco_conversation]]). La COLLECTE est bouclée (6/6 maillons) ; le **maillon 5**
> qui reste — `POSTES` dérivé du plan + retrait du levier `RESSERRER` de `curator.py` — est une tâche
> de **nature différente** (restructurer un producteur déterministe et un levier de `curator`, pas
> écrire un exécuteur réseau), et c'est là que **meurt le §12bis hérité**. Le contexte de l'exécuteur
> ne l'aide pas ; mieux vaut repartir du fichier. ⚠️ Maillon 5 = travail de code sans dépense réseau,
> mais il touche `edgar_feed.POSTES` (4 sites) et `curator.py` (leviers RESSERRER, lignes ~114-127,
> 264-265, 543-544) — relire #58/#59 avant.

### Découpage des lots suivants (spec v3 §10)

| Lot | Contenu | Migration |
|---|---|---|
| 0 | ✅ **Ligne de base** (ci-dessus) — 2026-09-09 | — |
| 1 | ✅ **Contrat** `FrameworkAnswer` + `FrameworkMandate`, pont relationnel **en Python** (#37), carte de provenance, écran niveau 3 en maquette — 2026-09-09 | — |
| 2a | ✅ **Le référentiel** — 13 questions en données inertes, 39/0, négatif 22/22 — 2026-09-10 | — |
| 2b | **Archivage et dévocabularisation** : `archive_v2` (rien de détruit) · `knowledge_entries` amaigrie de **8 colonnes** (7 à zéro écriture **+ `covers`**) · `question_coverage` créée, portée par framework **et version** · `entry_type`/`report_type` dévocabularisés | **036** |
| 2c | **La chaîne de collecte** : traducteur → plan → collecteur (§3.6) · **persistance** · **exécuteur réel + chaîne runtime (2026-09-12) ✅** · reste : `POSTES` dérivé du plan + retrait du levier `RESSERRER` (maillon 5) | **039** ✅ |
| 3 | Analyste + manager sur `qualite_financiere` · `framework_answers` / `_mandates` / `_dispenses` en base · **suppression** de `MVDD_SPEC`, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS` · **collecte neuve pilotée par le plan** sur NVDA / MSFT / RVMD | **037** |
| 4 | Le **manager** et ses 4 contrôles · le renvoi qui produit un mandat consommé par le **collecteur** | 038 |
| 5 | Le `research_memo` devient la **projection** des frameworks acquittés · réconciliation à 0/0 | 039 |
| 6 | Les 3 niveaux de drill-down · acquitter / renvoyer tracés (A7) · `qualite_info` **dérivée** | — |
| 7 | Le second pilote de bout en bout · acceptation complète T1-T8 | — |

⚠️ **Ordre imposé, inchangé : UX (contrat) → agent → données.** Jamais commencer par la table.
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

- **Suite hors-ligne : 2 107 assertions / 1 FAIL (§12bis hérité, à dessein) / 29 scripts** — une
  seule commande, **`bash checks/run_all.sh`**. Il porte les invocations correctes : montages `/contract_frozen`
  (sans lui 4 scripts sous-comptent en sortant à 0) **et `/roadmap`** (sans lui
  `check_frameworks_definitions` §7 ne peut plus confronter la spec au référentiel, et **sort en
  échec** au lieu de se sauter), plus réseau `coolify` + `CHECK_DB_URL` pour
  `check_entry_nature` (§7) **et** `check_edgar_feed` (§12bis) — tous deux **sortent en échec** si
  le pré-requis manque, jamais un saut de section. ⚠️ **Ne pas le réécrire dans `/tmp`** : la
  version jetable sous-comptait 47 assertions en silence (`CHANTIER_OUTILLAGE_DEV.md` §27).
- **Migrations appliquées jusqu'à 039** (036/037/038 lot 2b, **039** lot 2c — tables du plan de collecte).
- **Déploiement : le chemin nominal est repassé** (`compose-deploy.sh`, un seul appel) après quatre
  sessions de refus du classifieur. Le repli en commandes séparées reste documenté au §12 de
  `CHANTIER_OUTILLAGE_DEV.md`, mais **re-tester le nominal en premier** à chaque session.

### Roadmap 02 — close, et ce qu'elle laisse acquis

`roadmap/02-spec-autorite-vs-actualite.md` : **capacités 0 à 4 CLOSES**, capacité 5 fermée (§ ci-dessus).
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

- **`roadmap/03-spec-frameworks.md`** — la roadmap active. §0 les faits mesurés · §1 **ce qui n'est
  PAS défait** (à relire à chaque lot) · §2 l'objet framework · §3 le manager · §4 les deux pilotes
  rédigés en entier · §5 le stockage · §9 le test d'acceptation · §10 les lots.
- **`CLAUDE.md` du projet** — conventions **#22 à #55**. Les plus structurantes ici : #29 (la
  couverture se **lit** dans un index), #31 (ce qui décrit un émetteur ne vit jamais dans une
  constante globale), #37 (un contrat valide un objet, jamais la cohérence entre deux), #42/#43
  (datation et **identité** d'un fait), #44 (calculé / non calculable / absent), #46 (**détenteur
  unique** d'une règle), #48, #49, **#50** (trois axes jamais recombinés), **#51**, **#52**,
  **#53**, **#54** (la porte à trois états), **#55**.
- **Specs** : `roadmap/00-principe-directeur-v2.md` (constitution) ·
  `roadmap/01-spec-v2-unifiee.md` (§5 agents, §7 curator, §8 contrats, §14 migrations, §16 UX,
  §18 découpage) · `roadmap/02-spec-autorite-vs-actualite.md` (**close**, doctrine des 3 axes) ·
  `roadmap/benchmark-methodologies-decision-investissement.md` (**Partie B** le processus canonique
  en 15 étapes, **Partie D3** le contrat `RiskMatrix`, **Partie E** la matrice de traçabilité — c'est
  la matière **descendante** des frameworks).
- **Cartes de contrat** : `roadmap/provenance-cards/*_card.md` + `*_schema.py` + `prompts/`.
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
> **Roadmap active : `roadmap/03-spec-frameworks.md`** (ouverte le 2026-09-09). Diagnostic mesuré :
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
> 🚦 **PROCHAIN PAS = maillon 5 du lot 2c.** Lots 0, 1, 2a, 2b **acquis** ; lot 2c : contrat du plan
> + pont (T1bis) + traducteur + collecteur + persistance + **l'EXÉCUTEUR RÉEL câblé et exercé contre
> le vrai monde (2026-09-12)** — dispatch question-aveugle EDGAR/web, chaîne runtime
> `executer_collecte_framework`, check 31/0 + négatif 7/7 ; run réel RVMD (11 liens + 3 mandats, les
> trois états) + NVDA ciblé (chemin EDGAR → socle). **Reste le maillon 5** : `POSTES` dérivé du plan
> + retrait du levier `RESSERRER` de `curator.py`, **où meurt le §12bis hérité** — travail de code,
> sans dépense réseau.
> ⚠️ Le §12bis reste ROUGE (46 < 50) à dessein : c'est un socle data-first qui disparaît au maillon 5,
> **ne pas le recalibrer ni rejouer pour le verdir** (`feedback_fixture_pollue_le_reel`).
> ⚠️ Sur ce chantier la ligne de base a **déjà changé le lot trois fois** — elle se **requête**, elle
> ne se souvient pas ; et depuis §0.6 elle n'est **jamais une cible**. ⚠️ Mesureurs versionnés,
> jamais `/tmp` ; bilan reconnaissable à sa **forme** ; **jamais exécutés dans `portfolio-backend`**.
> État : suite hors-ligne **2 107 / 1 (§12bis hérité) / 29**, négatif collecte-persist **5/5** et
> collecte-executor **7/7**, migrations appliquées jusqu'à **039**.
> LIRE D'ABORD : ce fichier, puis `roadmap/03-spec-frameworks.md` (§1 = ce qui n'est PAS défait),
> le `CLAUDE.md` du projet (conventions #22-**#59**, dont **#57/#58/#59 issues de l'audit du
> 2026-09-10**), `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une
> décision manque.
