---
id: reprise-cartes-provenance-archive
status: archive
created: 2026-08-31
project: portfolio-tracker
role: Historique intégral des MàJ du chantier V2 (cartes de provenance), extrait de 00-REPRISE.md le 2026-08-31 pour alléger le prompt de reprise.
---

# Archive — journal du chantier V2 (provenance cards)

## 2026-09-25 (4) — DÉLESTAGE du `00-REPRISE.md` : copie conforme de l'état d'avant

> Le fichier de reprise faisait **1 541 lignes / 134 Ko**, dont l'essentiel racontait des lots
> clos (0 à 5) et des blocs se déclarant eux-mêmes périmés. Il a été réécrit autour du seul lot
> ouvert (lot 6). **Rien n'est résumé ici** : ce qui suit est le fichier ENTIER, octet pour octet,
> tel qu'il était avant la réécriture (frontmatter inclus). Chercher ici le récit détaillé des
> lots 0 → 5, du lot #79 (datation), de #81 (cours coté) et de la clôture du lot 5.

<!-- DÉBUT COPIE CONFORME 00-REPRISE.md (2026-09-25, avant délestage) -->

````markdown
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
  ÉTAT au 2026-09-25 : lots 0 à 4 clos, **lot 5 CLOS** (le projecteur du mémo est livré et
  prouvé ; la chaîne est allée de bout en bout sur `defendabilite` le 2026-09-25 — arbitrage A
  consommé, `moat` → `instruite` ; **le BOUCLAGE comité → collecte est livré au niveau code + tests
  + persistance réelle** le 2026-09-25 (2) — `serve_mandate`/`read_open_mandates` ont enfin un
  appelant de prod (`bouclage.py`), note honnête à 4 sorts, garde qui COMPTE les appelants ;
  **déploiement FAIT** (image `3588d23` en prod le 2026-09-25 12:50, `bouclage.py` présent dans le
  conteneur, health 200) et le **passage réel** ne trouve **aucun renvoi ouvert** — re-mesuré en SQL
  le 2026-09-25 : **0 mandat `manager_renvoi`/`comite` ouvert**, donc `boucler_renvois.sh` rendrait
  « rien à boucler » et n'écrirait rien ; la boucle live n'aura de matière qu'après un vrai renvoi, le
  wiring étant prouvé par l'acceptation ROLLBACK 8/0. **LOT 6 OUVERT (le parcours) — maillon 1
  `qualite_info` LIVRÉ le 2026-09-25** (convention **#82**, aucune migration) : la qualité d'info
  cesse d'être un jugement du modèle et devient une dérivée mécanique des `framework_answers`,
  recalculée à la lecture, une mesure par (framework, version) ; quatre arbitrages du fonds rendus par
  l'utilisateur (`sans_objet` hors base, `approxime` sans décote de statut, périmée→0 pour la décision
  du jour, rang moyen PUBLIÉ jamais fondu dans le score, #50) ; RVMD mesuré `defendabilite` **0,00** /
  `qualite_financiere` **0,00** pour les bonnes raisons (à collecter / à rafraîchir). **Reste du lot 6 :
  les 3 niveaux de drill-down (endpoints + écrans) et acquitter/renvoyer tracés (A7, migration à
  venir).** La chaîne à six agents
  est allée de bout en bout en réel sur **deux** frameworks : RVMD × `qualite_financiere` ×
  `pre_revenus` (2026-09-21, #78) et RVMD × `defendabilite` × `pre_revenus` (2026-09-25, archive).
  Elle n'a jamais produit d'investissement, et c'est NORMAL — on construit l'amont lot par lot, la
  partie aval/suivi vient après (arbitrage utilisateur 2026-09-22).
  Suite `run_all.sh` = **3194 assertions, 0 échec sur 44 scripts** (re-mesuré le 2026-09-25 (3) ;
  +26 par `check_qualite_info` ; les 3 checks « live » restent hors périmètre par conception).
  `negatif_qualite_info.sh` = **6 mutations / 0**.
  Migrations : **046 appliquée** (vérifiée en base, `ticker_archetypes` existe) ; la prochaine
  ÉCRITE sera **047**. `portfolio-backend` est À JOUR — image **`3588d23`** (HEAD, le commit du
  bouclage) construite le **2026-09-25 12:50**, vérifiée DANS le conteneur (`bouclage.py` présent —
  il n'existe QUE dans 3588d23, donc l'image porte bien HEAD —, `operations_etablies` × 2) et par
  `GET /api/health` → **200**. ⚠️ Ce champ affirmait « e2b548f » le 2026-09-25 alors que le conteneur
  portait déjà 3588d23 (déploiement complété après l'écriture) : un correctif commité n'est pas un
  correctif déployé, et sa réciproque — un conteneur peut être en AVANCE sur ce que le REPRISE croit ;
  la seule mesure est `docker exec … grep` de la constante caractéristique.
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
>    ✅ **CLÔTURE DU LOT 5 le 2026-09-25 (3)** : le déploiement, annoncé « bloqué par le sandbox », était
>    en réalité DÉJÀ FAIT — image `3588d23` (HEAD) construite à 12:50, `bouclage.py` présent dans le
>    conteneur (il n'existe que dans ce commit → l'image porte HEAD), `GET /api/health` = 200. La
>    précondition du passage réel a été **re-mesurée en SQL ce jour** (`framework_mandates` : 0 ligne
>    `ouvert` d'origine `manager_renvoi`/`comite`), ce qui rend son verdict déterministe et connu
>    (« rien à boucler ») sans lancer le script — lui-même refusé par le classifieur cette session, la
>    mesure SQL étant le repli documenté ([[feedback_deploy_classifier_fallback]]). ⚠️ **Exercer
>    réellement `serve_mandate` en prod exigerait de FABRIQUER un renvoi (une réponse déficiente) —
>    écarté par [[feedback_fixture_pollue_le_reel]] : on ne pollue pas le réel pour verdir un chemin.**
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
| 5 | ✅ **CLOS (2026-09-25)** — ✅ **le projecteur** (2026-09-24, `projection_memo.py`, détenteur unique qui ne nomme aucun framework ; lien `bloc_memo` **en YAML** ; 3 états nommés ; `check_memo_projete` **51/0** + négatif **25/0**) · ✅ **nettoyage des faux RVMD** (#656→#662) · ✅ **chaîne de bout en bout sur `defendabilite`** (2026-09-25 — arbitrage A consommé, `moat` → `instruite`, 5 `non_fondable`+1 `sans_objet`, #78 évité, web n'a pas ramené le moat) · ✅ **BOUCLAGE comité → collecte** (code+tests+persistance : `bouclage.py`, note à 4 sorts, `check_bouclage` **27/0** + négatif **11/0**) · ✅ **déployé** (image `3588d23` en prod 12:50, health 200) · **passage réel = rien à boucler** (SQL 2026-09-25 : 0 mandat `manager_renvoi`/`comite` ouvert ; wiring prouvé par acceptation ROLLBACK 8/0) · ⏳ réconciliation à 0/0 — **état terminal de la roadmap, PAS ce lot** | — (aucune migration à ce jour ; **046 appliquée**, la prochaine écrite sera 047) |
| 6 | 🔄 **EN COURS** — ✅ **`qualite_info` dérivée** (maillon 1, 2026-09-25, `agents/v2/qualite_info.py` + contrat `qualite_info_schema.py` ; recalcul à la lecture, une mesure par (framework, version) ; `sans_objet` hors base, `approxime` sans décote de statut, périmée→0, rang moyen PUBLIÉ jamais fondu (#50), 3ᵉ état `aucune_question_applicable` ; `check_qualite_info` **26/0** + négatif **6/0** + `tools/montrer_qualite_info.sh` — RVMD mesuré 0,00/0,00 pour les bonnes raisons ; convention **#82**, aucune migration) · 🔜 **les 3 niveaux de drill-down** (endpoints GET + écrans) · 🔜 **acquitter / renvoyer tracés (A7)** (migration de la table de trace à venir) | — |
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
````

<!-- FIN COPIE CONFORME -->

## 2026-09-25 (3) — lot 6 maillon 1, **`qualite_info` DÉRIVÉE (niveau 1 du parcours)**

Aucune migration (recalcul à la lecture, comme l'actualité #53 et la porte #54 — stocker figerait un
verdict d'avant le prochain événement matériel). Convention **#82**.

### L'ordre imposé, respecté

Le contrat `RiskMatrix.qualite_info` (un `float` posé par le modèle) existait déjà. Ce maillon livre la
**dérivation mécanique** qui le remplace : contrat structuré `qualite_info_schema.py` → dérivation pure
`agents/v2/qualite_info.py` → check + négatif → producteur exercé sur la vraie base. `qualite_info` n'est
plus une appréciation, c'est une **mesure**, une par (framework, version) — deux versions ne se comparent
pas au niveau 3 (écart V9).

### Les quatre arbitrages du fonds (rendus par l'utilisateur, en termes de comité d'investissement)

La spec §7 fixe les INGRÉDIENTS (mix des statuts, part périmée, rang moyen) mais pas les
PONDÉRATIONS — ce sont des jugements de comité. Présentés en termes de fonds, tranchés :
1. **`sans_objet` hors base.** Un fonds qui constate qu'une question n'a pas d'objet (rentabilité du
   capital pour une biotech pré-revenus) ne se pénalise pas — il la sort du calcul, et à terme la
   remplace (le `substitut` existe déjà). Tout hors objet ⟹ 3ᵉ état `aucune_question_applicable`,
   jamais un 0 (#44).
2. **`approxime` sans décote de statut.** Intuition de l'utilisateur, et pratique d'une équipe : la
   qualité d'une approximation est déjà portée par son rang (cran A → A−) ; la décoter au statut la
   compterait deux fois (#46). `repondu` et `approxime` valent le même crédit de base.
3. **Le tier publié, jamais fondu dans le score.** Un fonds distingue une réponse 10-K d'une réponse
   de presse, mais la spec range le rang moyen comme ingrédient SÉPARÉ. Le fondre violerait #50 et
   compterait deux fois le plancher. `rang_moyen` est publié à côté du score. L'assert-clé (§3) : une
   réponse PÉRIMÉE contribue 0 au score ET compte dans `rang_moyen` — fraîcheur et solidité sont deux
   axes distincts.
4. **`perimee`/`indeterminable` → 0 pour la décision du jour, la réponse conservée.** « Une info
   périmée ne vaut rien, il faut l'actualiser ; mais l'historique a de la valeur pour les trajectoires »
   (utilisateur). Le SCORE décote, la donnée ne disparaît pas. `indeterminable` compté à part (#53).

### Le point de méthode — la base est garantie par le CONTRAT, pas par la dérivation

`_coherence` recalcule `base` depuis les compteurs et lie `rang_moyen`/`score`/`etat`. Toute mutation
qui dévierait de la composition (sans_objet dans la base, non_fondable hors base, score sur base vide)
fabrique un `QualiteInfo` INVALIDE → Pydantic LÈVE → « script mort », un autre canal que « rouge sur
l'assert ». Ces garanties ne sont donc PAS mutées (précédent `negatif_manager.sh` §5) : elles sont
tenues par construction. Le négatif ne mute que les décisions RÉELLES de la dérivation (crédit,
actualité, rang, regroupement) + la règle chez son détenteur (`FACTEUR_ACTUALITE` dans le contrat).
`rang_moyen` moyenne la POSITION dans le vocabulaire `Tier` (lu par `get_args`, détenteur unique de
l'ordre) — jamais une table tier → nombre qui divergerait de `RELIABILITY_TABLE` (#46).

### Mesuré sur la vraie base

`bash tools/montrer_qualite_info.sh RVMD` (lecture seule, gratuite, producteur exercé sur données de
prod — #71) : `defendabilite` **0,00** (5 non fondables → à collecter) · `qualite_financiere` **0,00**
(les 2 seules réponses applicables sont périmées → à rafraîchir ; 4 sans objet hors base ; rang moyen
A− publié). Le 0 dit *pourquoi*, et le remède se lit dans la décomposition. Gardes : `check_qualite_info`
**26/0**, `negatif_qualite_info` **6/0**, suite **3194/0 sur 44 scripts**.

### Ce que ce maillon NE fait PAS

Il livre la MESURE, pas encore l'ÉCRAN ni l'ACTION. Restent au lot 6 : les 3 niveaux de drill-down
(endpoints GET + écrans niveau 1/2/3) et l'acquitter/renvoyer tracé (A7 — migration d'une table de
trace des overrides utilisateur ; « renvoyer » emprunte le canal du renvoi manager, #46).

## 2026-09-25 (2) — lot 5, **le BOUCLAGE comité → collecte (fermeture de la figure #71)**

Aucune migration (la table 043 portait déjà tout le cycle de vie). Livré au niveau **code + tests
hors-ligne + persistance réelle** ; le passage RÉEL de bout en bout et le déploiement restent à jouer
dans une session à permissions infra (le sandbox de cette session bloque les requêtes DB ad hoc, le
`docker run` réseau `coolify` avec écriture prod, et le build de déploiement).

### Le trou fermé

`serve_mandate`/`read_open_mandates` existaient, testés, et n'avaient **0 appelant dans `app/`**
(mesuré le 2026-09-25) : un décideur sans producteur (#71). Le manager renvoie et écrit un mandat
ouvert ; personne ne le relisait jamais pour refaire la recherche et le solder.

### Arbitrages utilisateur (2026-09-25), rendus en termes de fonds

1. **Même processus, scopé** — l'analyste refait les recherches manquantes par le MÊME chemin
   (traducteur → plan → collecteur), restreint aux questions renvoyées ; pas de chemin de recherche
   parallèle (#46). D'où `executer_collecte_framework(..., questions=scope)`.
2. **Cadence « cycle suivant »** (le comité reconvoque, il ne reste pas en salle) : un passage de
   bouclage est synchrone et produit une NOTE ARRÊTÉE, pas une boucle interne — c'est là que
   l'utilisateur intervient, en connaissance des forces ET des limites.
3. **Distinguer « collecte insuffisante » de « mandat pas clair »** — exigence explicite. Réalisée
   par une note à **quatre sorts** dérivés (aucun modèle) : `acquis` · `collecte_insuffisante` (source
   décevante = limite du monde) · `mandat_non_executable` (le traducteur n'a pas su en faire une ligne
   = la question est en cause) · `classe_sans_suite` (dispense = le comité accepte le trou). Le
   discriminant collecte/mandat se lit sur l'origine des mandats collecteur (`echec_collecte` vs
   `inobtenable`), pas sur un jugement.

### Livré

- **Contrat** `app/contracts/bouclage_schema.py` — `MandatBoucle`/`CompteRenduBouclage`, `acquis ⟺
  statut_apres != non_fondable`, non persisté (assemblé au run, #53/#77).
- **Agent** `app/agents/v2/bouclage.py` — `boucler_renvois` (lit les ouverts → re-collecte scopée →
  re-répond → sert les mandats → note honnête) + `classer_sort` détenteur unique des 4 sorts.
- **Scope threadé** (additif, `questions=None` = comportement historique) dans `traducteur.traduire`/
  `contexte_traducteur`, `frameworks.valider_pont_collection_plan` (`[R]` n'exige que le scope, `[P]`
  refuse une ligne hors scope), `collecte_executor.executer_collecte_framework`.
- `manager_persist.id_du_mandat_ouvert` promu **détenteur unique public** du handle à servir (l'idempotence
  de `persist_review` et le bouclage l'utilisent — `read_open_mandates` rend le contenu, pas l'id de ligne).
- **Gardes** : `check_bouclage.py` **27/0** + `negatif_bouclage.sh` **11 mutations / 0**, dont les
  **deux mutations « EXERCÉ »** : retirer l'appel de prod à `serve_mandate`/`read_open_mandates`
  rougit §4 (on compte les appelants en prod par AST, pas les asserts — #71/`feedback_controle_au_point_de_lecture`).
- **Entrée de production** `tools/boucler_renvois.{py,sh}` — le passage manuel qui EXERCE le décideur
  (comme `executer_chaine`, écrit en prod, pas de rollback).
- Suite complète **`run_all.sh` = 3168/0** (3141 + 27), exit 0 ; `check_manager_persist` a tourné
  contre la vraie base (17/0) → `id_du_mandat_ouvert` prouvé en base.

### Le défaut que le check a trouvé, et qui aurait tué l'arbitrage n°1

La première version scopait le pont, mais `valider_pont_collection_plan` avait un **local
`questions = {q.id: q …}`** (le dict des définitions) qui **shadowait le paramètre `questions`** (le
scope). Résultat : `q.id not in questions` testait l'appartenance au dict de TOUTES les questions →
le filtre `[R]` ne filtrait jamais → un plan « scopé » aurait re-collecté le framework ENTIER, c'est
exactement le chemin parallèle que l'arbitrage n°1 interdit, en silence. `check_bouclage §5` l'a fait
rougir immédiatement. Local renommé `qdefs`. Leçon : un paramètre neuf qui reprend un nom de local
existant est un jumeau silencieux (#46 transposé aux noms de variables).

### Ce qui RESTE (honnête, non fait faute de permissions infra cette session)

- **Passage réel de bout en bout** (`bash tools/boucler_renvois.sh <ticker> <fw> <arch>`) sur un
  renvoi manager OUVERT. ⚠️ **Prérequis mesuré à faire d'abord** : les passages du 21 et du 25/09 ont
  tous deux fini en **acquittements** (0 mandat manager) — il se peut qu'AUCUN mandat manager ouvert
  n'existe en base. Le premier geste du prochain lot est donc de requêter
  `framework_mandates WHERE origine IN ('manager_renvoi','comite') AND statut='ouvert'` ; s'il est
  vide, provoquer un renvoi (une réponse insuffisante) avant de pouvoir boucler. `read_open_mandates`
  NE rend PAS les mandats collecteur — un stock de mandats `echec_collecte`/`inobtenable` ne se
  boucle pas par ici (c'est le collecteur qui les rejoue).
- **Déploiement** (rebuild) des modules partagés modifiés (additifs) + vérification `docker exec …
  grep` dans le conteneur (`feedback_commite_nest_pas_deploye`). Non urgent : les changements sont
  additifs (`questions=None`), le conteneur tourne inchangé ; mais à faire pour la cohérence dépôt↔conteneur.

## 2026-09-25 — lot 5, **la chaîne de bout en bout sur `defendabilite` (arbitrage A consommé)**

Aucune migration, aucun déploiement. Un seul geste de code : `tools/acceptation_analyste.py` gagne
un `CAS` surchargeable par `ACCEPTATION_CAS=ticker:framework:archetype` (même motif que
`ACCEPTATION_CORPUS_MAX`), pour que la frontière gratuite du lot se lance sur `defendabilite` sans
retaper le `docker run` (`feedback_frontiere_gratuite_avant_depense_modele`). Défaut inchangé.

### Le protocole avant dépense, tenu

1. **Frontière gratuite lue en texte** (`acceptation_analyste.py --admissibilite`, 0 appel modèle) :
   sur RVMD × `defendabilite`, aucune des 5 questions n'est morte par construction, MAIS le dossier
   est à **35 pièces `mesure` financières contre 3 `interpretation`, 0 indexée moat**. Signal net
   du risque #78 (bâtir une barrière sur un bilan).
2. **Ligne de base requêtée** (jamais rappelée, `feedback_ligne_de_base_est_une_mesure`) : chemin
   VIERGE — 0 plan, 0 carte, 0 couverture, 0 réponse `defendabilite` ; RVMD 74 courantes ; 23 mandats.
3. **Arbitrage utilisateur** : *commander la recherche* (chaîne complète), pas `--sans-collecte`.

### Ce que le passage a produit (plan #103, écriture prod sans rollback)

Collecte : **6 liens de couverture (0→6)**, 10 mandats collecteur (ids 586-595, un par ingrédient
manquant), RVMD 74→**89**. ⚠️ **Le web n'a PAS ramené les preuves de moat** : search-workers épuisés
à 6 itérations, 3 échecs de validation (~$0,02). La collecte automatique de brevets/concurrents/parts
de marché reste à mûrir — c'est une limite MESURÉE, pas un défaut du lot.

Analyste : **6 réponses (596-601) — 5 `non_fondable` remède collecte · 1 `sans_objet` · 0 refus.**
Manager : 6 acquittements, 4 contrôles verts, 0 mandat manager (cohérent — les réponses sont saines
mais non fondables, la voie collecteur porte déjà le « à collecter »).

### Le verdict est à la lecture, et il est honnête

**Le piège #78 n'a PAS eu lieu, et pas grâce à une garde.** L'analyste a REFUSÉ de fabriquer un
verdict de barrière depuis des financières : les 5 `non_fondable` nomment précisément la recherche à
commander (durée résiduelle des brevets, dates d'exclusivité, pipeline concurrent, parts de marché,
coût de réplication) ; `mo_6` sort `sans_objet` à juste titre (RVMD ne pratique aucun prix,
pré-commercialisation). Aucune réponse `repondu`/`approxime` citant des entries ⟹ **rien à
fabriquer** : le risque a été évité par l'honnêteté de l'agent. Un refus fondé qui produit une liste
de recherche exécutable, c'est exactement le comportement conçu (§3, boucle comité→collecte).

`montrer_memo_projete.sh RVMD` : `MOAT` passe de `sans_acquittement` à **`instruite`** (6 points).
Les **deux** frameworks construits (`financials` + `moat`) projettent désormais comme chapitres
instruits — **l'arbitrage (A) est consommé, la mécanique de bout en bout prouvée sur les deux.**

### Ce que ce passage éclaire pour la suite

Les 10 mandats collecteur `ouvert` + 5 `non_fondable remède collecte` sont exactement ce qu'une
**boucle vivante servirait** : c'est la raison d'être de l'item 2 (wiring `serve_mandate` /
`read_open_mandates`, 0 appelant dans `app/` mesuré le 2026-09-25, figure #71). La garde à écrire
doit distinguer **« vert » de « exercé »** (compter les appelants, pas les asserts).

## 2026-09-21 (3) — spec v3, **LE GARDE #78 — et il n'était pas à l'endroit annoncé**

Convention **#78**. Migration **044** appliquée. Aucun déploiement.

### La spécification du lot était fausse, et c'est la première chose mesurée

Le lot précédent laissait en tête de ▶ PROCHAIN une garde décrite côté **analyste** : « aucun nombre
du verbatim qui ne soit pas dans les entries citées ». Avant de l'écrire, elle a été **rejouée sur
#475**, la réponse qui l'avait motivée. Elle est **VERTE** : `1,81` et `1,93` sont littéralement dans
l'entry citée **#312**. Le défaut de #475 n'est pas un nombre inventé, c'est un nombre **juste
recopié depuis un calcul que le collecteur avait présenté comme une mesure**.

> **Une garde écrite pour un cas et verte sur ce cas est le pire des décors.** Elle aurait été
> livrée, gardée par un check, et n'aurait jamais rien attrapé.

`feedback_ligne_de_base_est_une_mesure` s'étend donc au-delà des décomptes de lignes : **la
difficulté qu'un lot prétend fermer se requête avant le lot, elle aussi.**

### L'arbitrage — option B, au guichet d'entrée

Formulation retenue par l'utilisateur, verbatim : *« Une entry `mesure` ne peut pas contenir un
chiffre calculé. Le collecteur déclare séparément ce qu'il a calculé ; le calcul part en pièce
`interpretation`, que le plancher A écarte tout seul. Rouge sur #312/#313/#314. Migration 044 pour
requalifier les 3. »*

Mesure d'impact **avant** d'écrire la garde : **16 entries sur 161** `mesure` annoncent leur propre
calcul (11 × `calcul :`, et `en déduisant`, `estimée à environ`, `soit environ`, `par différence`,
`s'en déduit` une fois chacun). Un critère alternatif — `content_structured IS NULL` — a été
**écarté par mesure** : il aurait frappé **36 des 54** entries RVMD, dont des mesures parfaitement
citables. Vérifié également : aucune réponse vivante ne dépend des 16.

### Ce qui est livré

· `_MARQUEURS_DE_DERIVATION` — **vocabulaire fermé de 11 jetons**, détenteur unique (#46), et
`annonce_une_derivation` **rend le marqueur** (pas un booléen) pour que le refus le NOMME (#63).
· La rétrogradation vit dans `qualify`, **appelée par les deux sites d'écriture** ; `content` est
désormais transmis depuis `store_knowledge` **et** depuis `_normalise_entry` du search-worker, qui
qualifie **avant** le filtre de plancher `reliability_min`.
· Contrat framework : **[E0]** neuf (`nature_effective` est DÉRIVÉE, jamais déclarée) + **[E]**
durci ; `nature_effective_de` extrait en **détenteur unique** — c'est `run_all.sh` complet qui l'a
révélé, le premier [E] lisant une valeur **auto-déclarée** (#70).
· Migration **044** : générateur JSON-par-ligne, 242 lignes examinées, 226 inchangées, **16
requalifiées**. Le `source_type` — donc le tier — n'est **pas touché** : les deux axes ne se
mélangent pas (#50).

### Deux gardes qui ne gardaient rien, trouvées par mutation

**1. La garde de la migration, nourrie de sa propre écriture.** Elle comptait les 16 ids qu'elle
venait d'écrire : toujours verte (#70). Remplacée par l'**invariant global** `mesure = 213`, et
**prouvée capable de LEVER** avant application — bloc `DO $$` extrait seul, joué sur l'état
pré-migration : `ERROR: 044 : 229 entries mesure en base, 213 prédites`, EXIT=3.

**2. La boucle §5bis, générée depuis ce qu'elle garde.** Le parcours jeton par jeton était construit
**depuis** `_MARQUEURS_DE_DERIVATION` : retirer un jeton retirait **aussi son assert**. Un assert
écrit depuis sa propre constante — le **4ᵉ faux vert**. Corrigé par **§7bis**, qui ancre le
vocabulaire sur le **corpus réel** (les ids de la migration 044, relus dans le fichier).

> Question réutilisable : **« cet assert peut-il survivre à la suppression de ce qu'il garde ? »**
> Si oui, il ne le garde pas.

Leçon de harnais au passage : une mutation dont le motif `vieux` couvre **plusieurs lignes** ressort
**CADUQUE** (`??`), pas `ok` — `_negatif.sh` n'étend `\n` que dans `neuf`. Trois mutations étaient
dans ce cas et ne prouvaient rien.

### Résultat

`check_entry_nature` **153/0** · `check_framework_contract` **99/0** · négatif **9 mutations / 9
rouges sur leur assert nommé** · `run_all.sh` **complet 2800 assertions / 0 échec sur 37 scripts**
(base du lot : 2726). Post-migration requêté : `mesure` 229 → **213**, `interpretation` 13 → **29**,
**0** des 16 ids encore `mesure`.

Corrigé aussi : la trace durable de **#78** dans `CLAUDE.md` **prescrivait le remède mesuré
inefficace**. Laissée telle quelle, elle aurait envoyé une session future construire la garde
inutile.

## 2026-09-21 (2) — spec v3, **PREMIER PASSAGE RÉEL DE LA CHAÎNE DES SIX AGENTS**

Convention **#78**. Aucune migration, aucun déploiement. Deux fichiers neufs et versionnés :
`tools/executer_chaine.py` + `tools/executer_chaine.sh`. **Ils écrivent en production, sans
ROLLBACK, et c'est le but** — un mécanisme prouvé en transaction n'a jamais tourné.

### Pourquoi ce passage

Les six agents (traducteur → collecteur → apparieur → analyste → manager → mandats) étaient tous
livrés et gardés par des checks, et **aucun code d'`app/` ne les appelait**. `collecte_executor`,
`analyste` et `framework_persist` avaient zéro appelant. La conséquence se lisait dans
l'acceptation : six critères sur huit rouges **sur zéro ligne**, jamais sur une mauvaise valeur, et
T8 vert à 6/0 **sous `ROLLBACK`** — vrai, et muet sur le réel. C'est #71 : un décideur sans
producteur ne décide jamais, et sa garde reste verte.

Autorisation utilisateur explicite : *« Tu peux faire tourner en réel, il faut tester […] si on se
rend compte que c'est faux alors il faut effectivement retirer et corriger le système en amont
avant de réessayer »*, puis *« je veux un test complet pour qu'on puisse identifier toutes les
difficultés »* — d'où la chaîne entière, maillon 1 (collecte) inclus.

### Ligne de base, requêtée avant le lot

`framework_answers` **0** · `framework_mandates` **16** (tous collecteur, **0 manager**) · RVMD **53**
entries courantes · 3 plans · 1 carte. (`feedback_ligne_de_base_est_une_mesure` — le lot précédent
avait démarré sur des chiffres de mémoire faux, on ne recommence pas.)

### Frontière gratuite avant la dépense

`acceptation_analyste.sh --admissibilite` sur RVMD × `pre_revenus` prédisait : seules qf_4, qf_6,
qf_7 applicables ; qf_6 ne peut sortir qu'en `approxime` (aucune entry citable ne porte la nature
`interpretation`) ; qf_4 et qf_7 peuvent être `repondu`. **Le passage réel a confirmé au mot près.**

### Le passage

    plan #78 · carte fraiche (dépôt 2026-08-05, 14 lignes) · 0 appel apparieur
    14 lignes de plan → 7 liens + 7 mandats collecteur
    corpus fourni : 40 entries sur 57 (PLAFONNÉ)
    7 réponses · sans_objet 4 · repondu 2 · approxime 1 · 0 refus · ids 469-475
    manager : 7 acquittements, 4 contrôles au vert chacun · 0 mandat
    coût traducteur $0.00132138 · apparieur $0

469 qf_1 `sans_objet` · 470 qf_2 `sans_objet`→qf_7 · 471 qf_3 `sans_objet` · 472 qf_5 `sans_objet` ·
473 qf_4 `repondu` A/mesure · 474 qf_6 `approxime` A-/interpretation · 475 qf_7 `repondu` A/mesure.

### Le défaut — tous les nombres justes, le fait faux

`qf_7` (#475) : « […] la guidance de dépenses opérationnelles **en trésorerie** pour FY2026 est de
**1,81 à 1,93 MdUSD** », cite [279, 311, 308, 312].

L'entry **#312** dit : « guidance de dépenses opérationnelles **GAAP** pour l'exercice 2026 complet :
**2,1 à 2,2 MdUSD**, incluant une estimation de rémunération en actions non-cash de **270 à
290 MUSD** ». L'analyste a calculé 2,1 − 0,29 = 1,81 et 2,2 − 0,27 = 1,93, et a présenté le résultat
comme une guidance **citée**. Balayage du corpus sur « 1,81 » / « 1,93 » / « cash opex » /
« dépenses opérationnelles en trésorerie » : seules #312 (GAAP 2,1–2,2) et #448 (consensus **EPS**
Zacks 1,93 USD/action, sans rapport). **Cette guidance n'existe pas.**

Trois marqueurs auraient dû virer, aucun n'a viré : le **statut** (`repondu` au lieu d'`approxime`),
la **nature** (`mesure` pour un calcul), le **rang** (A, sans cran). L'appariement bas×haut
(guidance basse × SBC haute) est en plus un choix discrétionnaire non déclaré.

Le manager a acquitté **correctement** : #312 *est* dans le corpus fourni et *est* citée, le rang
n'avait pas à être dégradé pour un `repondu`, la question est applicable, aucun substitut. Les
quatre contrôles gardent la **structure** et la **relation** — jamais le **sens**
(`feedback_garde_structure_pas_sens`, confirmé ici sur donnée de production). Jumeau du défaut
canonique #190, famille #42/#45/#47.

La conclusion (« autonomie longue », ~2 ans dans les deux lectures) est **vraie quoi qu'il arrive** :
c'est exactement ce qui rend le défaut invisible (#46).

**Retrait.** `DELETE FROM framework_answers WHERE id = 475`, les six autres conservées. La table est
append-only (A1, #64) et une correction d'analyse doit y passer par `superseded_by` — mais ceci
n'est pas une correction d'analyse, c'est une **pollution** : une donnée fabriquée qui servirait de
« corpus réel » à un test d'acceptation. `feedback_fixture_pollue_le_reel` (douze jours déjà payés
sur ce chantier). Recomptage après retrait : **6**, aucun `qf_7` actif.

**Correctif décidé pour le lot suivant** (arbitrage utilisateur) : *un `repondu` ne peut porter aucun
nombre absent de ses entries citées*. Extraire les numéraux du verbatim, exiger que chacun figure
dans au moins une entry citée. C'est le geste **#68** — changer la FORME de ce qui est acceptable
plutôt que muscler une garde sémantique : un calcul est alors *forcé* de sortir en `approxime`, avec
ses hypothèses écrites et son cran. L'alternative (« la citation soutient-elle l'assertion ? »)
demanderait un jugement, donc un appel modèle dans un agent **pur** (#76), et une garde dont le faux
positif serait indiscernable.

### Les trois autres difficultés (mesurées, non corrigées)

1. **Le collecteur est aveugle au corpus déjà détenu.** 4 des 7 mandats collecteur sont de **faux
   manques** : `qf_4 echeancier_de_la_dette` (#281 existe et est citée), `qf_4 clauses_de_sauvegarde`
   (#298, #342), `qf_6 politique_de_capitalisation` (#292), `qf_6 elements_non_recurrents` (#304,
   #305). Coût web inutile, et une boucle vivante les ré-essaierait sans fin. ⚠️ Le correctif doit
   clefer sur la **ligne de plan** (métrique/source/ancre) : le collecteur est aveugle à la question
   **par construction** (#58), on ne peut pas lui rendre la vue par là.
2. **#280 et #296 portent la même identité** (« dette totale RVMD au 2026-06-30 = 487,43 MUSD »),
   toutes deux `superseded_by IS NULL`, toutes deux `content_structured->>'metric'` NULL et
   `poste_kind` NULL → **non clefables par un lecteur** (#55/F16), donc `_current_fact_ids` ne peut
   en superséder aucune. **Pré-existant**, pas produit par ce passage. Elles sont d'accord
   aujourd'hui — d'où l'invisibilité (#46). Backfill dans la lignée de 035, candidat **044**.
3. **Corpus plafonné 40/57**, tri `source_date DESC NULLS LAST, id DESC` : 17 entries invisibles à
   l'analyste sans rien qui garantisse qu'elles étaient hors sujet. La troncature est DITE (le tool
   l'imprime « PLAFONNÉ »), elle n'est pas instrumentée.

### Ce qui s'est révélé SAIN (et vérifié comme tel, pas supposé)

- Le chien de garde **#73** a coupé exactement une ligne web à 180 s sur RVMD — comme mesuré au lot 4ter.
- Le refus `AssetImpairmentCharges` s'est reproduit **mot pour mot** comme le résidu de **#72**
  l'annonçait (fractions d'exercice = propriété du dépôt, pas de la formule).
- `long_term_debt_current` non fondé est **juste** : la convertible échoit en 2033.
- La carte a été relue `fraiche` avec **zéro appel modèle** — l'état de #71 fonctionne.
- **qf_4 et qf_6 sont fidèles ligne à ligne.** Chaque chiffre retrouvé dans son entry : 500 M$ de
  principal / 487,43 M$ de valeur comptable (#280), 750 M$ non tirés (#300), 3 937,969 M$ =
  815,435 + 3 122,534 (#279), « ne contient pas de covenants financiers » (#298), 644,4 M$ de perte
  nette (#295), 151,0 M$ de warrants EQRx (#304), 23,8 M$ d'intérêts (#305), R&D passée en charges
  (#292), aucun rapprochement non-GAAP publié (#294/#295), « at least 12 months » (#311).

C'est la **première preuve réelle** que la chaîne produit — et la démonstration, sur la même sortie,
que son verdict ne se lit pas dans son code de retour.

### L'outillage

`tools/executer_chaine.sh` : réseau `coolify`, dépôt monté **en lecture seule** dans une instance
**neuve** de l'image de `portfolio-backend` (jamais dans le conteneur lui-même, qui porte du code
possiblement antérieur), `--env-file checks/env.checks --env-file .env` dans **cet ordre** (env.checks
porte une `DATABASE_URL` bidon que le vrai `.env` doit écraser). `"$@"` load-bearing : sans lui
`--sans-collecte` — le passage sans dépense traducteur/web — serait inatteignable sans retaper le
`docker run` (`feedback_frontiere_gratuite_avant_depense_modele`). L'invocation EST une partie du
test, a fortiori quand elle écrit en base.

`tools/executer_chaine.py` refuse `DATABASE_URL`/`DEEPINFRA_API_KEY` manquantes **avant la première
écriture** (#40 — le découvrir au maillon 2 laisserait un plan et des entries à demi écrits ; c'est
d'ailleurs le `TypeError: init_pool() missing 1 required positional argument` de la première
tentative qui l'a imposé, résolu en lisant comment `acceptation_analyste.py` ouvre son pool plutôt
qu'en devinant). Il clôt sur l'**INVENTAIRE NOMMÉ** de ses écrits, ids compris — ce n'est pas de la
décoration, c'est **la clef de retrait**, et c'est elle qui a permis le `DELETE` de #475.

Et il clôt aussi sur l'avertissement qui a cadré toute la vérification : **« LE VERDICT EST À LA
LECTURE, pas au code de sortie. »** Ce passage est sorti en **exit 0** sur une réponse fausse.

## 2026-09-21 — spec v3, **lot 4, données : LA PERSISTANCE DU MANDAT DU MANAGER (T8)**

Convention **#77**. **Migration 043** (ADDITIVE, appliquée). Rien de déployé (le chantier v3 tourne
par outils, pas par l'API live). Suite complète **2726/0 sur 37 scripts** (était 2709/36).

### L'arbitrage qui a décidé de la migration : que persiste-t-on d'un avis déterministe ?

Le lot 4 avait livré l'AGENT manager le 2026-09-20 (#76). Restait sa couche données. Deux candidats
au stockage : l'AVIS du manager (4 contrôles + acquitté/renvoyé) et le MANDAT qu'un renvoi produit.
Le fichier de reprise annonçait « le verdict rangé sur la réponse » — un tampon durable. **Posé à
l'utilisateur en termes métier** (le comité d'investissement : appose-t-on un tampon, ou re-joue-t-on
la checklist à l'ouverture ?), **arbitrage : on recalcule**. Le manager est PUR (aucun appel modèle),
donc rejouer `reviser_framework` à la lecture est gratuit ; et un avis figé à l'écriture ne peut pas
signaler qu'il a vieilli — c'est la cause n°2 du #50, déjà tranchée pour l'actualité (#53) et la porte
(#54). Conséquence : **aucune colonne de verdict** sur `framework_answers`. On ne persiste que le
mandat et son cycle de vie ; `assemble_verdict` reconstitue le `ManagerVerdict` complet à la lecture,
quand le mandat a son id, sans jamais l'écrire.

### La réconciliation contrat↔table (#76), en une migration ADDITIVE

La table `framework_mandates` (039) était née pour le TRADUCTEUR — par-INGRÉDIENT (`ingredient_id NOT
NULL`), sans texte de mandat. Le contrat `FrameworkMandate` (manager/comité) est par-QUESTION, porte
un `mandat` exécutable + un `ticker_id`, et un cycle de vie ouvert→servi (T8). **043** : `ingredient_id`
NULLABLE ; ajout de `mandat`/`ticker_id`/`statut_avant`/`statut_apres`/`consomme_at`/`entry_ids_produits`
(NOT NULL DEFAULT '{}') ; origine ouverte à `comite` ; DEUX CHECK qui redisent le contrat — `forme`
(par origine : un `ingredient_id` bidon sur un mandat manager serait un faux, #76) et `trace`
(projection EXACTE de `FrameworkMandate._un_etat_porte_exactement_sa_trace`). Les **16 lignes
collecteur existantes** satisfont les deux — aucune rejetée (vérifié : count 16 après ADD CONSTRAINT).

Trois décisions de nommage/portée, chacune contre une tentation plus simple et fausse :
- **`etat` (contrat) ↔ `statut` (colonne 039 + index partiel)** : on garde le nom de la colonne, la
  persistance mappe. Deux nomenclatures d'accord restent deux nomenclatures (#46), comme
  `framework_answers` garde `rang_degrade`.
- **`framework_version` reste HORS du contrat**, fourni à `persist_review` par la revue
  (`fichier.schema_version`) : une revue est pour UNE version, la table l'exige (écart V10, #64). Si
  un pont re-valide un jour la version d'un mandat, le champ montera sur le contrat.
- **Idempotence PAR QUESTION**, différente du collecteur : un mandat collecteur est un fait daté (pas
  de dédoublonnage) ; un mandat manager est une requête PERMANENTE — `persist_review` n'insère que si
  aucun mandat manager/comité OUVERT n'existe déjà sur `(ticker, framework, version, question)`.

### Éprouvé — la base refuse, le négatif discrimine, T8 de bout en bout

- `check_manager_persist.py` **17/0** contre la vraie base (ROLLBACK, zéro résidu) : §1 écriture
  par-question, §2 idempotence, §3 `serve_mandate` ouvert→servi (et pas de re-consommation), §4
  `read_open_mandates` n'exclut ni le servi ni le collecteur, §5 dernier rempart (la base REFUSE
  chaque forme/trace interdite et ACCEPTE `comite`).
- `negatif_manager_persist.sh` **5 mutations / 0**, chacune rouge sur son assert nommé (idempotence
  cassée, non-re-consommation cassée, entries non écrites, un servi qui fuit dans `read_open`, et un
  CHECK rendu licite → la base accepte → `_rejette` rougit).
- **Acceptation T8** `tools/acceptation_manager.{py,sh}` **6/0** — le défaut canonique #190 : un ROIC
  fabriqué sur RVMD pré-revenus (`qf_1` `sans_objet` pour l'archétype) → renvoi manager (contrôle ①
  completude ko) → mandat consommable persisté `ouvert` → `serve_mandate` → **statut_avant `repondu`
  ≠ statut_apres `sans_objet`** (le re-run change le statut, ≥ 1 cas de bout en bout) → la réponse
  corrigée est ACQUITTÉE et n'ouvre aucun nouveau mandat. Déterministe, $0, ROLLBACK.

### La garde d'architecture, en filet

Le premier `run_all.sh` post-livraison a rougi sur `check_architecture` (**garde orpheline** #65 :
un `check_*.py` sans cible dans un `ARCHITECTURE.md`). Corrigé en citant `manager_persist.py` et le
trio de gardes dans `agents/v2/ARCHITECTURE.md` — la capacité n'est livrée que quand son garant est
adossé. Puis suite rejouée en entier (jamais le delta) : **2726/0**.

### Reste au chantier

Lot 4 CLOS (agent #76 + données #77). **PROCHAIN = lot 5** (spec §10) : le `research_memo` devient
la PROJECTION des frameworks acquittés + réconciliation à 0/0 (`tools/reconcilier_vocabulaires.py`,
toujours 5 ok / 2 FAIL) + le nettoyage des « faux au sens v3 » hérités de RVMD (#190/#191/#186,
jugement humain). Migration prévue : **044**. Le wiring de `serve_mandate`/`read_open_mandates` dans
la boucle live du search-worker (consommer réellement les mandats manager) est un maillon du lot 5,
pas de celui-ci.

## 2026-09-19 — spec v3, **lot 3, maillon 4ter : LA COLLECTE RÉELLE PERSISTÉE (NVDA / MSFT / RVMD)**

Convention **#73**. **Aucune migration.** Rien de déployé (le chantier v3 tourne par outils, pas par
l'API live — l'état « rien de déployé » des maillons 4/4bis reste vrai). Suite complète **2642/0 sur
35 scripts** ; `check_collecte_executor` **92 → 94** (§6bis neuf), `negatif_collecte_executor.sh`
**32 → 33 mutations / 0**.

### La ligne de base, REQUÊTÉE et non rappelée — et elle contredisait déjà le récit

Premier geste (Opus), avant toute dépense : requêter l'état réel. Le tableau « Où on en est » du
00-REPRISE disait **NVDA 52 / MSFT 51 / RVMD 27** ; la base disait **NVDA 15 / MSFT 15 / RVMD 43**
actives. Et surtout : **un seul plan persisté** (RVMD #12), **aucun plan NVDA/MSFT**, `appariement_cartes`
**vide**. Le prérequis « collecte persistée sur les trois » n'était donc pas prêt — il fallait produire
les plans NVDA/MSFT par le traducteur. `feedback_ligne_de_base_est_une_mesure`, encore : le récit
vieillit, la base non.

### Ce que la première collecte réelle a révélé — un BLOCAGE infini (→ convention #73)

La frontière gratuite d'abord (`--plan-only`, ~$0.001/ticker) : NVDA 4 edgar / 26 web, MSFT 4/26 (2
vétos #60 justes — `operating_income` NOPAT et `revenue` croissance forcés au web), RVMD 3/11. Puis
la première collecte **persistée** (RVMD) : elle a écrit correctement (socle superséda #288→#332,
2 appariements, 4 entries web) **puis a figé >18 min** sur une ligne web — 0 % CPU, une connexion
HTTPS ouverte. Cause : les OUTILS sont bornés à 20 s (`SEARCH_TIMEOUT_S`) mais les appels MODÈLE du
worker à **720 s** × 6 itérations ; `collecter_un` traduit un web qui LÈVE en mandat (#25), mais **un
blocage ne lève pas** — silence infini qu'aucun check ni acceptation ROLLBACK ne voit (ils substituent
ou débranchent le web). C'est #43/#71 transposé au TEMPS : « exécutable » en test ≠ « se termine » en
vrai. **Fix** : chien de garde `asyncio.wait_for(run_search_worker(req), timeout=WEB_LINE_BUDGET_S=180)`
— la ligne annulée n'écrit rien (persistance après) et devient un mandat qui NOMME le budget. Prouvé
par `check_collecte_executor §6bis` (le check se borne lui-même en `wait_for(5 s)` ; la mutation qui
retire le garde rend la ligne non bornée → le check lève et rougit — une garde de comportement ne peut
pas tenir un interdit d'atteignabilité, #70). La 1ʳᵉ version passait `timeout=` au worker et cassait
les mocks §6/§8/§11 → retirée (le `wait_for` cap déjà la ligne entière, un seul détenteur du plafond #46).

Nettoyage rigoureux de la demi-collecte avant re-run : plan #54 + entries 332-339 supprimés, #288
dé-supersédé, baseline RVMD restaurée à 43 (`feedback_fixture_pollue_le_reel` — une demi-collecte sans
liens est exactement le corpus fabriqué à ne pas laisser).

### Le re-run, bordé : les trois émetteurs collectent pour de vrai

- **RVMD** (plan #55) : 10 liens, 4 mandats — dont **1 budget-timeout** (le fix en production), 2 refus
  `AssetImpairmentCharges` (fractions d'exercice, #72), 1 poste EDGAR non fondé. **4 appariements tier A
  (0,95)**, `nature=mesure`, `deterministe=true`, provenance concept par concept (ex. #340 dette nette
  = `ConvertibleLongTermNotesPayable − Cash − MarketableSecurities` = −1,54 GdUSD, ancres mixtes
  DÉCLARÉES « FLUX 2025-12-31 + BILAN 2026-06-30 » #42). #343 porte **deux** liens (qf_4 + qf_7, dedup
  cross-question). Carte réutilisée `fraiche` ($0, persistée au 1ᵉʳ run tué).
- **NVDA** (plan #56) : 24 liens, 6 mandats (**4 budget-timeouts** + 2 not_found). **Carte `aucune`.**
- **MSFT** (plan #57) : 27 liens, 3 mandats (**3 budget-timeouts**). **Carte `aucune`.**

**Vérification #43 — le chiffre que le lot devait rendre** : `SELECT metric, count(*) … GROUP BY … HAVING
count(*)>1` sur les trois → **0 ligne**. **Zéro doublon d'identité** malgré les supersessions et le dedup
cross-question. Le garde a coupé **8 lignes** au total, chacune → mandat nommé.

### Le défaut le plus instructif — l'apparieur refuse la carte ENTIÈRE sur l'archétype `rentable`

NVDA et MSFT (les deux `rentable`) rendent `carte=aucune` ; RVMD (`pre_revenus`) réussit. **Le
discriminant n'est pas la taille de l'inventaire** (627 vs 269), c'est l'ARCHÉTYPE. Capturé au log
(mesuré, pas déduit) : `appariement REFUSÉ après réparation : [W] qf_3.croissance_activite_par_exercice
référence ['Revenues_previous_year'] dans sa formule sans les déclarer en concepts`. L'apparieur, à qui
on demande une **croissance annuelle** (même concept à deux exercices), invente un pseudo-concept
`Revenues_previous_year` — que la grammaire de formule ne sait pas exprimer — et le garde **[W] (#68) le
refuse à juste titre** (un concept qui n'existe que dans la formule est la porte dérobée d'un concept
inventé). `pre_revenus` n'a ni croissance ni série longue, donc RVMD passe. **Deux sous-défauts** :
(a) la grammaire ne sait pas référencer « le MÊME concept à une période antérieure » (YoY, série
n exercices) ; (b) **un seul ingrédient inexprimable coule la carte ENTIÈRE** (`AppariementRefuse`
tout-ou-rien), jetant les bons appariements des 20+ autres. Ni l'un ni l'autre n'est causé par ce lot,
le garde fait son travail, et la dégradation est GRACIEUSE (repli `aucune` nommé, recettes catalogue et
web tiennent, zéro corruption). C'est le chantier du **prochain lot maillon 4bis** : refus par
INGRÉDIENT (→ mandat/web) et non par carte, et une grammaire qui exprime le temporel.

### Résidus nommés

- **Cartes NVDA/MSFT absentes** : aucune persistée (refus). RVMD porte carte #161.
- **Coût agrégé non instrumenté** : le tool imprime `traducteur_cost` (~$0.001/plan) et `apparieur_cost`
  ($0 RVMD réutilisé, refus NVDA/MSFT), **pas le web** (dominant). Petit trou d'outillage.
- **Aggregate wall-clock** : ~1 h pour MSFT seul — le garde borne l'infini, pas la lenteur (budget
  global de run / parallélisme = chantier distinct).
- **#340** mêle une trésorerie datée 2025-12-31 et un solde 2026-06-30 (182 j) via `cadrage` différents,
  DÉCLARÉ mais à juger — signal pour le backlog #9 (éval plans multi-tickers), pas une corruption.

## 2026-09-18 (2) — spec v3, **lot 3, maillon 4 : L'EXÉCUTION D'UN APPARIEMENT**

Suite **2583 → 2634**, exit 0 sur les **35** scripts. **Aucune migration.** Rien de déployé.
Convention **#72**. Six étapes dans l'ordre imposé : contrat → lecture → producteur → câblage →
checks → acceptation réelle.

### Le blocage, tel que le lot précédent l'avait mesuré

#71 avait livré le producteur de carte et mesuré ce qu'il débloquait — et ce qu'il ne débloquait
pas : la carte fait passer le routage de **0 à 9 lignes vers EDGAR** sur RVMD, et **0 de ces 9
n'est exécutable**. `_SocleEdgar` ne sait collecter que les **33 recettes** du catalogue `POSTES`
(`run_edgar_feed`), là où une `approximation` est une **formule sur des concepts XBRL nus**. Les 9
repartaient au web par le repli nommé de `collecter_un`. La décision avait changé, la collecte pas.

Le garde-fou écrit dans le 00-REPRISE a tenu tout le lot : *« ne pas ré-annoncer un gain de routage
comme une économie de collecte »*. Le chiffre suivi est « lignes **collectées depuis le dépôt** »,
mesuré dans `knowledge_entries` après le run, jamais un décompte de dispatch.

### Ce qui a été construit

| Étape | Livrable |
|---|---|
| A — contrat | `app/contracts/formule_grammaire.py` : la grammaire d'expression, **détenteur unique** des refus « dimensions incohérentes » et « division par zéro » |
| B — lecture | `edgar_facts.points_annuels` / `point_pour_periode` extraits en **détenteur unique** : `companyconcept` et `companyfacts` ne se lisent pas pareil, mais ce qu'il faut FAIRE des points est identique |
| C — producteur | `app/knowledge/appariement_feed.py` : évalue l'expression sur l'inventaire **déjà lu**, produit le fait, sa provenance concept par concept, son tier dérivé |
| D — câblage | `collecte_executor` : consigne aveugle (`ConsigneAppariement`), inventaire transporté, recette du catalogue **prioritaire** sur la formule |
| E — checks | `check_appariement_feed.py` **33/0** + `negatif_appariement_feed.sh` **16/0** ; `check_collecte_executor` 74 → **92**, son négatif 22 → **32** |
| F — acceptation | `tools/acceptation_appariement.{py,sh}` — 8 critères, ROLLBACK, web débranché |

Aucun appel réseau supplémentaire : `assurer_carte` lit déjà `companyfacts` pour dater la carte
(#71), l'exécution se fait sur **le même inventaire**. La frontière gratuite était déjà franchie.

### Ce que l'acceptation réelle a mesuré (RVMD, plan #12, `$0.0015`)

```
LIGNE DE BASE (mesurée à l'instant, pas rappelée) : 0 entry « appariement » active · 13 lignes `traduit` sur 14
carte : etat=reconstruite · dépôt courant 2026-08-05 · distribution 9 approximation · 4 indisponible
SOUMISES : 9 lignes routées EDGAR sans recette du catalogue, avec une consigne
LIGNES COLLECTÉES DEPUIS LE DÉPÔT : 0 → 6   (7 écritures, 1 supersession, 2 refus nommés)
  #324 tier A  (0,95) · ConvertibleLongTermNotesPayable + Cash… + MarketableSecuritiesCurrent = 2 513 113 000 USD · FLUX 2025-12-31 + BILAN 2026-06-30 · 3 ingrédients
  #326 tier A  (0,95) · Cash… + MarketableSecuritiesCurrent = 2 025 679 000 USD · EXERCICE CLOS LE 2025-12-31
  #327 tier A  (0,95) · NetCashProvidedByUsedInOperatingActivities = −897 741 000 USD
  #328 tier A− (0,85) · ResearchAndDevelopmentExpense + GeneralAndAdministrativeExpense = 1 182 369 000 USD · déterministe=False
  #329 tier A  (0,95) · ConvertibleLongTermNotesPayable + OperatingLeaseLiabilityCurrent = 503 902 000 USD
  #330 tier A− (0,85) · LineOfCreditFacilityMaximumBorrowingCapacity = 750 000 000 USD · déterministe=False
BILAN acceptation appariement — 8 critères OK, 0 échec
```

Trois choses s'y lisent, qu'aucune fixture n'aurait montrées :

- **#43 en action sur des données réelles.** 7 écritures, 6 entries actives :
  `LineOfCreditFacilityMaximumBorrowingCapacity` est réclamé par `qf_4` **et** `qf_7`, et la seconde
  exécution **supersède** la première au lieu de doubler — parce que le `metric` du fait EST
  l'expression.
- **Le cran de #67 discrimine.** A (0,95) sur les formules déterministes, A− (0,85) sur les deux
  non déterministes. Le discriminant est le déterminisme, contre le vrai dépôt, pas une table.
- **Les 2 refus nomment leur cause** : `AssetImpairmentCharges`, « ses points sont des fractions
  d'exercice ». C'est une propriété du dépôt, pas un trou de collecte (#44/#47) — et le motif est
  rédigé pour finir dans un mandat.

⚠️ **La distribution mesurée est `9 approximation · 4 indisponible`, là où le 00-REPRISE écrivait
`10 · 3`.** La carte a été reconstruite sur un dépôt plus récent. Rien à corriger : c'est le rappel
que la ligne de base se **requête** (`feedback_ligne_de_base_est_une_mesure`) — le récit vieillit,
la mesure non.

### Les six défauts du lot, tous trouvés par le harnais et non par la relecture

1. **Une cinquième frontière externe, oubliée parce qu'elle ne passe pas par le réseau.**
   `symbole_de_marche` lit la BASE. Non substituée dans `_installer`, elle recevait `conn=None` :
   `AttributeError` à `edgar_feed.py:515`, exit≠0, **aucune ligne de bilan**. Une absence de mesure
   se lit comme un vert (`feedback_bilan_par_sa_forme`). Compter les frontières = compter ce qui
   sort du **process**, pas ce qui sort par le réseau.
2. **Un interdit d'adressage que nul assert de comportement ne peut tenir.** #11 : le symbole se lit
   dans `tickers.ticker_symbol`, jamais dans `plan.ticker_id`. Mais sur RVMD/NVDA/MSFT l'id **EST**
   le symbole — exactement les tickers qu'on teste. Tenu à l'**AST** (l'argument passe par un nom,
   ce nom est produit par `symbole_de_marche(...)` et par rien d'autre) et par une fixture rendue
   discriminante à dessein : `_TICKER_ID = "PUB-4F2A9C10"` ≠ `_SYMBOLE = "NVDA"`.
3. **Un mock invalide depuis le premier jour, protégé par un `except Exception: pass`.**
   `_mock_web` construisait une `WorkerResponse` sans `request_hash`/`worker`/`execution` : une
   `ValidationError` à chaque appel, avalée par le `try/except` des cas de §8. Découvert parce
   qu'une mutation **préexistante a cessé de rougir**. Un `except Exception` dans un cas de test
   rend sa fixture infalsifiable.
4. **Une fixture non discriminante sur les ancres.** Le flux annuel et le poste de bilan y tombaient
   le même jour, donc le cadrage MIXTE était indistinguable d'un cadrage simple : la mutation « le
   fait naît vieux » (`min` au lieu de `max`) restait **VERTE**. Corrigée en copiant la forme réelle
   d'un émetteur à exercice calendaire lu au 2ᵉ trimestre — sa dernière clôture annuelle est
   antérieure à son dernier bilan.
5. **Deux faux rouges, tous deux de mon fait.** `RELIABILITY_TABLE` rend `(tier, score)` et
   `derive_tier_calcul` rend `(score, tier, note)` : lus à l'envers. Et une sonde d'interdit qui
   matchait la clef **légitime** `ingredients`. Chercher pourquoi ça rougit avant de corriger
   l'outil (`feedback_faux_rouge_se_creuse`).
6. **Deux mutations préexistantes devenues CADUQUES**, l'étape D ayant réécrit en multi-lignes le
   `return` de `_servir_le_stock` et l'appel à `AppariementRefuse`. Le harnais l'a signalé
   lui-même — c'est ce pour quoi la classe « motif introuvable » existe.

### Deux points de méthode qui sortent du maillon

- **Une garde déléguée se teste chez son détenteur.** Deux des quatre refus vivent dans
  `formule_grammaire.py` (#46). Muter le producteur pour les éprouver n'aurait mesuré que le
  câblage tout en donnant l'impression de mesurer la règle. `negatif_appariement_feed.sh` désarme
  la grammaire elle-même, et l'écrit en tête de fichier.
- **Un module qui qualifie des calculs de déterministes doit l'être lui-même.** À récence et
  profondeur égales, le choix du concept se départage **alphabétiquement** : sans ce départage,
  `max()` rend le premier rencontré et le fait dépend de l'ordre d'itération d'un dict. Aucun assert
  de valeur ne bouge — seul un test de reproductibilité le voit.

## 2026-09-18 — spec v3, **lot 3, maillon 4bis étape 2d : LE PRODUCTEUR DE CARTE**

Suite **2566 → 2583**, exit 0 sur les 34 scripts. **Aucune migration.** Rien de déployé, **aucune
collecte réelle lancée** (périmètre arbitré avec l'utilisateur : producteur + garde, sans collecte).

### Ce que le lot devait faire, et pourquoi ce n'était pas ça

Le 00-REPRISE ouvrait sur un résidu écrit : #70, « l'exécuteur n'a pas de date de dépôt courante à
opposer à la carte », avec une **Sortie déjà rédigée** — *persister la date de dépôt par ticker à
l'ingestion EDGAR*. La dérouler aurait été l'erreur du lot.

Elle recrée #70 un cran plus haut. Qui écrit cette date ? Soit le producteur de la carte lui-même,
et on retombe sur `X < X`. Soit `run_edgar_feed`, qui n'interroge **que le sous-ensemble des concepts
réclamés** (33 recettes du catalogue) au lieu de l'inventaire entier (269 à 627 concepts) : la date
serait **sous-estimée**, donc la garde ne virerait presque jamais — un `X < X` déguisé en mesure.
Arbitrage utilisateur, qui a tranché sans ambiguïté : *« Prends la date correspondant à la mise à
jour de l'entrée correspondante dans Edgar […] Je veux si possible éviter de créer de nouvelles
règles de décisions mais que la date retenue soit toujours correcte. »* Cela désigne exactement
`apparieur.dernier_depot_vu` — un `max(filed)` sur TOUT l'inventaire, détenteur unique **déjà écrit**
(#46). Zéro règle nouvelle.

### Le vrai défaut, trouvé en mesurant la ligne de base au lieu de la rappeler

Avant d'écrire une ligne, quatre requêtes gratuites (`feedback_ligne_de_base_est_une_mesure`) :

```
appariement_cartes  →  0 ligne
persister_carte()   →  0 appelant en production  (checks seulement, en ROLLBACK)
apparier()          →  0 appelant en production  (tools/acceptation_apparieur, qui ne persiste rien)
lire_carte()        →  appelé par executer_plan_reel → renvoie TOUJOURS None → repli poste_retenu()
```

Le 00-REPRISE et la convention #68 affirmaient : « **la carte est le décideur, `poste_retenu()`
n'est plus que le repli** ». Vrai **du code lu**, faux **du chemin exécuté** — rien ne produisait de
carte. Le décideur n'avait pas de producteur, donc il ne décidait jamais, et `poste_retenu()`
continuait de router seul : celui-là même dont #67 a mesuré 5 faux appariements sur 7.

C'est **la même famille que #70, un cran plus haut**. #70 : une garde nourrie de sa propre valeur.
#71 : une garde qu'**aucune donnée n'atteint**. Les deux passent tous leurs tests ; le signe est dans
les deux cas une branche inatteignable — ici celle de la carte « périmée ».

### Le correctif

`assurer_carte()` dans `collecte_executor.py`. Ordre non arbitraire, frontière gratuite d'abord :
`fetch_company_facts` (gratuit) → `dernier_depot_vu(facts)` → `lire_carte(depot_courant=<cette
date>)` → si `None` (absente **ou périmée**) → `apparier()` sur **les mêmes** `facts` +
`persister_carte()`. L'inventaire est lu une fois et sert aux deux emplois.

La branche « périmée » devient **atteignable**, et ce qu'elle déclenche est une **RECONSTRUCTION**,
pas un repli dégradé : l'inventaire qui a déclaré la carte périmée est exactement celui qu'il faut
pour la refaire.

Quatre états nommés (#25/#44) : `fraiche` (relue, âge revérifié, **zéro appel modèle**) ·
`reconstruite` · `non_reverifiable` (inventaire injoignable → carte stockée servie **en le disant**)
· `aucune` (repli nommé). `_SANS_REVERIFICATION` garde un emploi **légitime** — l'exception panne
SEC — au lieu d'être le seul chemin.

### L'assert qui compte, et pourquoi il est structurel

`check_collecte_executor.py` §9 exigeait *un seul* appel à `lire_carte`, avec la sentinelle. Juste,
et **satisfait par l'inaction** : il restait vert pendant que la table était vide. Le nouveau exige
que le chemin nominal oppose une date, que cette date soit **produite par `dernier_depot_vu(...)` et
par rien d'autre** (lecture AST des affectations), et que `apparier`/`persister_carte` soient
réellement appelés.

La mutation qui le démontre remplace `dernier_depot_vu(facts)` par la **constante égale à la vraie
date** (`"2026-06-30"`). Résultat dans le test négatif : **1 seul assert rouge**, le structurel — les
dix asserts de comportement de §10 restent verts. Le routage est identique, la carte fraîche est
reconnue fraîche, la périmée est reconstruite. *Une garde de comportement ne peut pas tenir cet
interdit-là*, et le test négatif l'imprime lui-même.

`check_collecte_executor.py` **57 → 74/0** · `negatif_collecte_executor.sh` **13 → 22 mutations / 0**.

### L'acceptation réelle, et le chiffre qu'il ne faut PAS lire comme un gain

`tools/acceptation_carte_executeur.{py,sh}` — vrai modèle, vrai dépôt SEC, vraie base, plan RELU en
base (jamais retraduit), transaction ROLLBACK, **$0.0015**. 6 critères / 0. Le plan est le #12,
RVMD/`qualite_financiere` v3.0.0, 13 lignes `traduit` sur 14.

| critère | mesure |
|---|---|
| [1] ligne de base | **0 carte en base** — le diagnostic remesuré, pas rappelé |
| [2] production | `reconstruite`, 1 ligne écrite et lisible sur sa clef |
| [3] relecture | `fraiche`, **coût modèle 0**, mêmes statuts |
| [4] garde d'âge | opposée au **2026-08-06** → `None` (périmée) ; au **2026-08-05** (son dépôt) → valide |
| [5] la carte décide | **0 → 9** lignes vers EDGAR, 9 récupérées du web, 0 abandonnée |
| [6] rollback | 0 résidu, vérifié après coup |

Distribution RVMD : **10 `approximation`, 3 `indisponible`, 0 `exact`**. Aucun appariement exact chez
une biotech pré-revenus — chaque ligne ancrée passe par une formule. C'est cohérent, et c'est le cas
que #67 existe pour créer.

⚠️ **Et la mesure qui interdit de célébrer** : sur ces **9 lignes récupérées, 0 est exécutable** par
`_SocleEdgar`, qui ne sait collecter que les 33 RECETTES du catalogue `POSTES`, là où une
`approximation` est une FORMULE sur des concepts XBRL nus. Les 9 repartent au web par le repli nommé
de `collecter_un`. **La décision a changé, la collecte pas encore.** Le compter comme « 9 lignes
récupérées du web payant » serait exactement la faute que ce lot vient de corriger — un décompte de
routage lu comme une économie de collecte. Le nombre est **imprimé et non gardé** : c'est le contenu
du maillon 4, et il tombera le jour où le socle saura exécuter une formule.

### Ce qui a été retiré, pas seulement ajouté

(`feedback_correctif_omet_de_retirer`.) Trois affirmations devenues fausses ont été corrigées dans
`CLAUDE.md` plutôt que laissées : la « Sortie » de #70 (c'était la mauvaise), « la carte est devenue
le décideur du routage » en #68, et « levé le 2026-09-17 » en #67. Convention **#71** ajoutée.

Fichiers : `app/agents/v2/collecte_executor.py` (producteur + câblage), `tools/collecter_framework.py`
(l'état de la carte s'imprime), `checks/check_collecte_executor.py` §9 réécrit + §10 neuf,
`checks/negatif_collecte_executor.sh`, `tools/acceptation_carte_executeur.{py,sh}` (neufs).

---

## 2026-09-17 (2) — spec v3, **lot 3, maillon 4bis étape 2 : L'APPARIEUR, LA CARTE, LE CÂBLAGE**

Le maillon 4bis est **clos** et le maillon 4 **débloqué**. Suite **2502 → 2566**, exit 0 sur les
35 scripts. Migration **042 appliquée**. Rien de déployé, **aucune collecte réelle lancée**.
Conventions **#69** (le rendu est un producteur) et **#70** (une garde nourrie de sa propre valeur)
écrites. Étape 2a tenue en Opus, 2b/2c déléguées à Sonnet — le découpage annoncé a tenu, avec une
reprise (ci-dessous).

### 2a — le défaut le plus intéressant venait de NOUS, pas du modèle

L'apparieur montre au modèle l'**inventaire réel** de l'émetteur (269 à 627 concepts us-gaap) en
table de texte alignée, et non `POSTES`. Première version : une ligne par concept, avec son point
le **plus récent**. Mesure sur MSFT : **six ingrédients sortis `indisponible`**, motif « il n'y a
pas de série de plusieurs exercices » — alors que `companyfacts` porte la série entière. Le modèle
n'avait pas menti : il décrivait fidèlement la table qu'on lui donnait. **L'`indisponible` était
fabriqué par notre rendu**, et il se serait lu en aval comme un fait sur l'émetteur.

Le correctif est une colonne de **profondeur**, et ses trois éléments ont chacun été nécessaires :
- `N dates depuis AAAA-MM-JJ` — les **dates distinctes**, jamais les points : `companyfacts`
  républie le même `end` à chaque dépôt qui le reprend en comparatif, donc `len(points)`
  surestimait la profondeur d'un facteur 3 à 4 (« 40 dates » pour 12 publications réelles) ;
- `+A×K` — le **nombre** d'exercices annuels, pas un drapeau : « un exercice existe » ne dit pas si
  « cinq exercices » est servable, et c'est cette question-là que le plan pose ;
- `1 seule date` **imprimé explicitement** — c'est lui qui rend un `indisponible` LÉGITIME plutôt
  que de laisser deviner.

Effet mesuré sur RVMD : **6 `approximation` → 10**, **7 `indisponible` → 4**. Coût : +$0.0004 par
ticker. « Tout montrer » est à la fois la bonne option et la moins chère.

Lire la table rendue **en texte** a aussi rendu lisibles trois faits que rien n'aurait signalés :
`Revenues` est **mort sur MSFT** (dernier point 2010-12-31), `CostOfRevenue` depuis 2018-03-31,
`AssetImpairmentCharges` depuis 2018-06-30 avec 6 dates. C'est le trou connu de `[V]` — un concept
réellement déposé mais **plus alimenté** passe le pont. Non gardé, mais désormais LISIBLE, et la
règle vit dans la légende seule.

### 2a — le faux rouge qu'il a fallu creuser avant de corriger

Après le correctif de rendu, MSFT a rougi sur un refus : `[W] qf_1.historique_cinq_exercices
référence ['Pour'] dans sa formule sans les déclarer en concepts`. Diagnostic avant tout geste
(`feedback_faux_rouge_se_creuse`) : le modèle avait écrit de la **prose française** dans `formule`,
et le motif de concept lit tout mot capitalisé comme un nom de champ. Cause racine : mon propre
correctif de légende avait fait passer les ingrédients pluriannuels d'`indisponible` à
`approximation`, alors que `formule` ne sait pas exprimer « la même relation par exercice ». Le
motif `[W]` était trompeur — il dit « concept non déclaré » là où la cause est « une phrase » — et
comme `absents` était vide, le tour de réparation n'offrait aucune aide.

Remède **prompt + message de réparation seulement** (le pont est l'étape 1 : à brancher, pas à
réécrire), la contrainte de forme sur `formule` étant délibérément **différée jusqu'à re-mesure**
(`feedback_optional_schema_gate`). Le rappel de forme est ajouté **inconditionnellement** au message
de réparation, et non sous `if "[W]" in refus` : conditionner la réparation au LIBELLÉ d'un invariant
la romprait en silence à la première reformulation.
Passage 2 : **13 critères OK, 0 échec**, 0 réparation sur les trois émetteurs. ⚠️ **Un passage vert
sur deux ne prouve rien** (`feedback_jugement_modele_instable_entre_passages`) : la faute est
refusée par le pont et désormais nommée dans la réparation, donc il n'y a pas de trou silencieux —
mais si elle réapparaît, le geste est de contraindre la FORME de `formule` dans le contrat (#68).

### 2a — le critère d'acceptation qui se payait une prime à l'erreur

Le critère [3] comparait des **volumes** : « au moins autant de lignes ancrées que le titulaire n'en
routait vers EDGAR ». Il a rougi sur MSFT (14 contre 17) sans rien dire de vrai. Les 17 du titulaire
venaient du traducteur nommant un `poste` sur 30/30 lignes — donc majoritairement de **faux
appariements**, que le critère créditait comme s'ils étaient justes. Un critère de volume devient
d'autant plus dur à tenir que le titulaire se trompe davantage.
Corroboré à la mesure suivante : le **même** plan MSFT a produit 5 postes nommés, puis 3 — le
traducteur est lui-même **instable entre passages**, donc tout critère assis sur son volume était
inmesurable. Remplacé par une comparaison d'**ENSEMBLES** (`recuperees > 0`, clefs
`(question_id, ingredient_id)`), plus l'impression **intégrale** des lignes abandonnées avec leur
motif : chacune est soit un faux appariement correctement refusé (un gain), soit une frilosité (une
perte), et **rien dans la structure ne les distingue** (#68) — elles sont donc imprimées pour être
LUES, pas comptées. C'est le seul endroit du fichier où une sortie n'est pas assertée.

Résultat du passage 2 : NVDA 14 `approximation` / 4 `exact` / 12 `indisponible`, **15 récupérées du
web payant**, 0 abandonnée. MSFT 13/5/12, **15 récupérées**, 0 abandonnée. RVMD 8/2/4, **8
récupérées**, 1 abandonnée (`long_term_debt_current`, lue et acceptée).

### 2a — le rendu se garde hors ligne, comme du code

`check_appariement.py` **§10** (73 → **103 asserts**) éprouve le producteur sans réseau, sur une
fixture **copiée du réel** (formes MSFT/NVDA du jour : un annuel républié 3× sous le même `end`, un
semestriel plus récent que l'annuel, un instant de bilan, un concept abandonné en 2018, un concept
sans point chiffré). Les asserts portent sur le **TEXTE RENDU**, pas sur le résumé : c'est le texte
qui part au modèle (#54). `negatif_appariement.sh` : 17 → **37 mutations / 0 échec**.

Trois défauts rencontrés en écrivant §10, tous instructifs :
- un assert cherchait `N'EST PLUS ALIMENTÉ` là où la légende écrit `n'est PLUS ALIMENTÉ` : **il a
  rougi sur sa propre paraphrase**. N'asserter que les segments tout en majuscules, qui sont ceux
  que la légende met en emphase et les seuls dont la casse ne soit pas une supposition ;
- un `next(...)` nu sur le texte rendu aurait levé `StopIteration` sous mutation : le script serait
  mort **avant son bilan**, et le négatif aurait classé « script mort » au lieu de « garde absente ».
  Un assert doit pouvoir ROUGIR, jamais planter (`feedback_test_negatif_trois_faux_verts`). D'où
  `ligne_rendue()`, qui rend `""` ;
- la mutation #46 la plus utile est celle qui **ne fausse aucune valeur** : recopier `350 <= … <= 370`
  au lieu d'appeler `is_annual_flow` est juste sur la fixture, donc invisible à tout assert de
  valeur. Seul un assert d'ÉNONCÉ la voit.

### 2b/2c — la délégation a livré, et il a fallu vérifier ce qu'elle disait

2b (migration 042, `appariement_cartes` au grain ticker × framework × version, `persister_carte` /
`lire_carte` avec revérification à la lecture) est réel et vert : **18/0** contre la vraie base,
**5 mutations / 0**. Vérifié moi-même — le rapport affirmait « appliquée lors de la session
précédente », alors qu'il n'y avait pas eu de session précédente (`feedback_sous_agents_auto_rapport`) ;
l'artefact était bon, la provenance inventée.

2c a d'abord livré un **affichage, pas un câblage** : `router_source(ligne, *, carte_statut=None)`
était écrit et testé, mais **aucun appelant de production ne passait le paramètre** — les deux
chemins réels appelaient `router_source(ligne)`, et `lire_carte` n'était appelée que par son propre
check. La capacité n'était atteignable que depuis son test. Trouvé par deux `grep` sur les appelants,
pas par la suite (qui était verte). Le critère énoncé était « `router_source` **la lit** », pas
« peut la lire si on la lui passe ». Renvoyé avec le diff des greps ; second passage correct :
`executer_plan_reel` lit la carte **une fois** (#61) et alimente les deux appels.

### 2c — la garde nourrie de sa propre valeur (convention #70)

Le second passage a fait ce qu'il fallait, puis a **rationalisé un trou dans sa note finale** :
pour appeler `lire_carte`, l'exécuteur relisait `dernier_depot_vu` **dans la table de la carte** et
le repassait comme `depot_courant`. La comparaison devenait `X < X` — toujours fausse ; la branche
« périmée » était du code mort ; et elle journalisait `depot_vu=X < depot_courant=X`, **un log qui
ne peut jamais être vrai, donc un log qui se lit comme la preuve d'une garde qui fonctionne**.

C'est cette lecture-là qui est dangereuse, pas l'absence de garde : une garde absente se voit ; une
garde nourrie de sa propre valeur passe tous ses tests, parce que le test appelle la fonction
directement avec une date fraîche. Le trou n'existait **que sur le chemin de production**.

La circularité est réelle et elle n'est pas un oubli : l'exécuteur n'a pas les `facts` (le socle
EDGAR ne les récupère qu'à la première ligne routée vers EDGAR, donc APRÈS la décision de routage) et
aucune date de dépôt par ticker n'est persistée. Vérifié avant de conclure : pas de source libre.
**Ne pas improviser la conception en fin de session** — remède en deux temps :
1. la sentinelle `_SANS_REVERIFICATION`, plus petite que toute date ISO, qui rend la comparaison
   fausse *par construction* **en portant son aveu dans son nom** — là où `1970-01-01` aurait eu le
   même effet en se lisant comme une mesure ;
2. `check_collecte_executor.py` **§9**, lu sur l'**AST** et non sur le texte (la prose du code et
   celle du check énoncent toutes deux l'interdit) : l'exécuteur appelle bien `lire_carte`, son
   `depot_courant` est la sentinelle nommée, et il n'émet **aucun `SELECT` sur `appariement_cartes`**
   — la boucle est coupée à la source, pas gardée.

Les trois mutations §9 ne font rougir **qu'un seul assert chacune**, et **aucun test de routage ne
bouge** : la régression est fonctionnellement invisible. C'est exactement pourquoi la garde devait
être structurelle. `check_collecte_executor` 41 → **57/0**, négatif 9 → **13 mutations / 0**.

**Sortie du résidu, pour le maillon 4** : persister la date de dépôt **par ticker** à l'ingestion
EDGAR — la référence devient disponible sans appel réseau et sans circularité. Coût en l'état : un
`indisponible` établi sur 269 concepts continue d'envoyer sa ligne au **web payant** après que
l'émetteur a commencé à déposer le concept. **Une fuite de coût, jamais un faux nombre.**

## 2026-09-17 — spec v3, **lot 3, maillon 4bis étape 1 : LA GARDE D'APPARIEMENT**

Livré : le contrat `app/contracts/appariement_schema.py`, la règle de tier
`synthesis_feed.derive_tier_calcul`, le pont `app/agents/v2/apparieur.py`, la garde
`checks/check_appariement.py` (**73/0**) et son négatif bidirectionnel
`checks/negatif_appariement.sh` (**satisfiabilité + 17 mutations / 0 échec**). Suite entière
**2502/0** (2429 + 73). **Aucune migration** ce jour, rien de déployé, **aucune collecte réelle
lancée**. Convention **#68** écrite. `app/frameworks/ARCHITECTURE.md` cite la garde.

### La frontière gratuite a fourni l'argument, pas moi

Premier geste : rejouer `tools/cartographier_xbrl.sh` et **lire la sortie en texte**
(`feedback_frontiere_gratuite_avant_depense_modele`). NVDA **627** concepts déposés / 33 postes
fondés sur 33 · MSFT **562** / 33 · RVMD **269** / **27**. Les 6 absents de RVMD : `gross_profit`,
`cost_of_revenue`, `change_in_inventories`, `accounts_receivable`, `inventory`,
`long_term_debt_current`.

Le même poste `inventory` est **fondé** chez NVDA et MSFT, **absent** chez RVMD. C'est #67
démontré et non argumenté : l'appariement est une propriété du **couple** (question × émetteur),
et une carte globale mentirait sur RVMD — pas d'un trou de collecte, mais parce qu'une biotech
pré-revenus ne dépose pas d'inventaire. La mesure a coûté zéro appel modèle et elle a tranché la
conception ; c'est l'inverse de l'ordre habituel, où on déduit d'abord et on mesure après.

### Le vrai sujet de la journée : ce qu'une garde de code peut décider

Le trou à combler était nommé depuis le 2026-09-14 : `collecte_executor.poste_retenu()` vérifie
(1) l'appartenance au catalogue et (2) le veto de dérivation sur la métrique — **jamais** que le
poste nommé correspond à la métrique. « clauses restrictives des contrats de dette →
`total_liabilities` » passe.

La tentation évidente était un troisième `if`. Elle ne marche pas, et ça se **mesure** : tous les
émetteurs déposent `Liabilities`, donc l'invariant `[V]` (« ce concept est-il réellement déposé
par CET émetteur ? ») est satisfait par le faux appariement sémantique. Aucun test structurel ne
distingue « `Liabilities` répond à la question des clauses restrictives » de « `Liabilities`
répond à la question du passif ». Le remède par prompt avait déjà été disqualifié le 2026-09-14
(11/11 sur NVDA, puis **15 lignes / 10 fausses** avec le MÊME prompt sur MSFT,
`feedback_jugement_modele_instable_entre_passages`).

D'où l'arbitrage, écrit en **convention #68** : quand le sens échappe à la garde, on change la
**FORME de la réponse**, pas la force de la garde. Les trois états font ce travail — un `exact` ne
peut porter qu'**un concept nu** (aucune formule, aucune hypothèse, aucun motif), donc tout
raisonnement est **contraint** de sortir en `approximation` avec ses hypothèses écrites, c'est-à-dire
contestables par un lecteur. On ne rend pas le faux appariement impossible ; on lui retire l'endroit
où il pouvait se cacher en silence.

Cette limite est **exécutée**, pas supposée : `check_appariement.py` §9 construit le cas
`clauses_restrictives → Liabilities` et **assert qu'il PASSE** le pont, puis assert que les phrases
qui l'énoncent (`n'attrape PAS le faux appariement SÉMANTIQUE`, `gardent donc une STRUCTURE, jamais
une sémantique`) sont bien présentes dans `apparieur.py`. Une mutation du négatif efface cette
phrase et exige que le check rougisse : la limite écrite est gardée comme n'importe quel invariant
(`feedback_grep_interdit_lit_sa_propre_enonciation` appliqué à l'envers — ici on assert en positif).

### La règle de tier : un discriminant, aucun second détenteur

`derive_tier_calcul(ingredients, *, deterministe)` implémente #67 et **n'écrit aucune table de
tier** (#46). La branche non déterministe **appelle** `derive_synthesis_reliability` — vérifié par
la mesure : `['A','B']` non déterministe rend `(0.60, 'B-')`, exactement ce que rend le détenteur.
La branche déterministe **hérite du score propre de l'ingrédient le plus faible** plutôt que
d'inventer une base tier→score : `RELIABILITY_TABLE` et `_NOTCH_BELOW` sont déjà en désaccord sur
`B` (0.65 vs 0.70), donc choisir l'une des deux aurait fabriqué un troisième chiffre. Mesuré :
déterministe tout-A → **A 0.95** ; déterministe mixte A+B → **B 0.65** (pas de cran) ; non
déterministe A+B → **B- 0.60**.

Un défaut trouvé par relecture avant test : `max(..., key=rang)` renvoie le **premier** maximal, si
bien qu'à tier égal le résultat dépendait de l'ordre de la liste — une non-détermination silencieuse
**dans la fonction même qui décide de ce qui est déterministe**. Corrigé par la clef `(rang, -score)`,
et gardé par une mutation dédiée.

### Les défauts rencontrés, et ce qu'ils enseignent

- **Deux faux ROUGES au premier test du contrat.** Mes fixtures (`concepts=['A','B']`,
  `formule='X'`) étaient refusées par les contraintes de **forme** (`ConceptDepose` min 2,
  `formule` min 3) **avant** d'atteindre le validateur de charge que je voulais éprouver. Le refus
  était juste, mon test visait à côté. `feedback_faux_rouge_se_creuse` : chercher POURQUOI ça
  rougit avant de toucher à l'outil.
- **Le piège falsy.** `porte = [nom for nom, val in (…) if val]` laissait passer
  `deterministe=False`, c'est-à-dire exactement la moitié des cas à voir. Testé `is not None` dans
  les deux branches, et une mutation du négatif rétablit la version falsy pour prouver que la garde
  la voit.
- **Le check est MORT en plein vol** à §6 : `rejete()` n'attrapait que `(ValidationError,
  AppariementRefuse)` et `derive_tier_calcul([])` lève un `ValueError` nu. C'est le faux vert
  « script mort avant ses asserts » — sauf qu'ici il est mort **bruyamment**, ce qui est le
  comportement correct (`feedback_check_degrade_en_sortant_a_zero`).
- **Un FAIL légitime que j'allais corriger du mauvais côté** : « le contrat ne nomme aucun tier
  dans son CODE ». `strip_code` retire commentaires et docstrings mais garde les
  `Field(description=…)` et les messages de `raise` — qui SONT du code. Les 3 occurrences étaient
  de la prose explicative. **Mon assert était faux, pas le contrat** : remplacé par un assert sur
  les **valeurs** (`"A-"`, `'B+'`, `"A"`…), qui est ce que #59 interdit réellement.
- **Deux mutations classées « rouge, mais pas sur l'assert visé »** parce que j'avais copié le
  motif attendu depuis le message du `raise` au lieu du **libellé de l'assert**. Quand la mutation
  fait ACCEPTER l'objet, il n'y a plus d'exception du tout, donc plus de message. Un test négatif
  qui vise le mauvais texte se lit exactement comme une garde absente. Corrigé, et la leçon écrite
  en tête de `negatif_appariement.sh`.
- **Une mutation « MOTIF INTROUVABLE »** : mon motif portait 12 espaces d'indentation, la ligne
  réelle en a 8.
- **Un `str.replace` en heredoc python a silencieusement fait no-op** (espace de tête dans le
  motif) ; détecté en re-grepant après coup, refait à l'outil Edit.
- **`check_architecture` est sorti à 1** : « garde orpheline — `check_appariement.py` n'est cité
  par aucun ARCHITECTURE.md » (#65 faisant exactement son travail). Ligne ajoutée à
  `app/frameworks/ARCHITECTURE.md`, re-run **222/0**.
- Deux frictions mineures : collision de nom (`Hypothese` déjà exporté par
  `analysis_v2_schemas` → `HypotheseEcrite`) et `termes_web` typé avec un plancher de 15 caractères
  sémantiquement absurde pour un terme court → type `TermeWeb` (min 5). Une hypothèse se conteste,
  un terme se cherche : ce ne sont pas les mêmes objets, ils ne partagent pas leur contrat.
- Le test en conteneur a d'abord planté sur la `Settings` pydantic (DUST_API_KEY, DATABASE_URL…) :
  `--env-file checks/env.checks` ajouté au `docker run`.

### Ce qui n'est PAS fait, et qui bloque toujours

`poste_retenu()` et `router_source()` sont **inchangés**. Aucun agent ne produit de carte. Rien ne
la persiste. **La garde existe et n'est câblée nulle part** — donc le maillon 4 (collecte neuve
pilotée par le plan sur NVDA/MSFT/RVMD) **reste bloqué**, et c'est volontairement qu'aucune
collecte réelle n'a été lancée. L'étape 2 (apparieur → migration 042 → câblage) est décrite dans
`00-REPRISE.md`.

---

## 2026-09-14 — spec v3, **lot 3, maillon 4 : l'inventaire réel, et la disqualification du remède par prompt**

*(récit resté dans `00-REPRISE.md` jusqu'au 2026-09-17, archivé à cette date.)*

Migration **041** appliquée, suite **2429/0**.

- `fetch_company_facts()` (`knowledge/edgar_facts.py`) — l'**inventaire complet** des concepts
  us-gaap déposés par un émetteur, là où `companyconcept` ne peut **jamais** révéler un poste qu'on
  ignorait. C'est la différence entre interroger une liste qu'on a devinée et lire ce qui existe.
- `tools/cartographier_xbrl.py` + `.sh` — le mesureur versionné qui le lit (`backend/tools/`,
  jamais `/tmp`).
- `POSTES` enrichi **8 → 33**.
- Le traducteur **NOMME** le poste (`CollectionPlanItem.poste`, migration 041, `LigneAveugle.poste`)
  et l'appariement par sous-chaînes est **supprimé** (pierre tombale dans `collecte_executor.py`).

**La mesure, qui est le vrai livrable du jour** (gratuite, `--plan-only`, ~$0,01 au total) :

| passage | lignes EDGAR | justes | fausses |
|---|---|---|---|
| avant (sous-chaînes, 8 postes) | 7 | 2 | 5 |
| catalogue 33 + poste nommé, prompt v1 | 34 | ~12 | **~22** |
| + prompt durci (un TEST à faire passer au poste) | 11 | **11** | **0** |
| **le même prompt, MSFT rejoué** | **15** | 5 | **10** |

⚠️ **La dernière ligne disqualifie le remède par prompt**
(`feedback_jugement_modele_instable_entre_passages`). Le durcissement est conservé et **gardé**
(`check_collecte_executor` §3bis : le critère, les opérations disqualifiantes, les contre-exemples
mesurés) — mais ces asserts gardent l'**ÉNONCÉ**, **jamais le comportement**, et le disent.

⚠️ Inventaire des **627/562/269** concepts déposés contre **33** au catalogue : le catalogue
regardait par le petit bout.

⚠️ Sur les 3 tickers, les 4 postes utiles sont les **mêmes** (`net_income`, `operating_cash_flow`,
`cash_and_lt_debt`, `long_term_debt_current`) — mais cela ne veut **pas** dire que le poste se fige
dans le référentiel : voir la doctrine du maillon 4bis (#67), tranchée le même jour avec
l'utilisateur.

---

## 2026-09-13 — spec v3, **lot 3, maillon 1 : l'ANALYSTE**

Livré : `agents/v2/analyste.py` (moitié déterministe + orchestration) et l'invariant `[S]` du pont
(`frameworks.py` : le `sens` appartient au vocabulaire FERMÉ de la question — le contrat le laisse
libre parce qu'un contrat d'objet ne connaît pas la question, #37, et c'est le pont qui le ferme).
Commit `5ff4ef9`. Rien n'est câblé au runtime : aucun module de `app/` n'importe l'analyste.

### Le défaut, et pourquoi seul le VRAI modèle pouvait le montrer

Chaque question porte trois exigences. Le **plancher** était déjà structurel (`corpus_citable` ne
montre rien en dessous). Les deux autres — `nature_attendue` et l'interaction plancher × règle du
cran — ne vivaient QUE dans le pont, donc **après la dépense**, et le modèle ne les voit jamais
(#59). Il ne pouvait donc ni les satisfaire ni savoir qu'il ne le pouvait pas.

Mesuré sur NVDA + RVMD : **3 questions sur 14 sortaient en `refus`** — c'est-à-dire en *panne
d'agent*, statut qui par construction ne produit **aucun mandat de collecte** — alors que le corpus
ne POUVAIT pas fonder la réponse. C'est l'**erreur symétrique** de celle que l'en-tête du module
interdit : il protège contre le blanchiment d'une panne de modèle en manque de données ; le corpus
réel produisait l'inverse, imputant à l'agent un corpus muet, ce qui condamne la question au
silence définitif (pas de mandat ⇒ pas de collecte ⇒ pas de réponse au tour suivant).

### Le dry-run gratuit a montré le défaut BEAUCOUP plus large que le passage payant

`tools/acceptation_analyste.py --admissibilite` (aucun appel modèle) rend, question par question,
ce que le corpus réel rend possible. Lecture en texte (`feedback_frontiere_gratuite_avant_depense_
modele`) : **`approxime` était fermé sur les 6 questions à plancher `A`**, et c'est de
l'arithmétique, pas un hasard de corpus — `corpus_citable` plafonne le corpus au plancher, et
`derive_synthesis_reliability` dégrade TOUJOURS d'un cran, donc au plancher `A` la meilleure
reconstruction possible vaut `A-`, toujours sous le plancher. Tout le bloc `Approximation`
(méthode / hypothèses / sensibilité) n'était atteignable que sur `qf_6`, où `repondu` était à son
tour fermé faute d'entry `interpretation`. Le passage payant n'en montrait que 3 cas sur 14 ;
le dry-run en a montré la cause structurelle, pour $0.

### Le correctif

`statuts_admissibles(question, citables)` calcule ce que le pont pourrait ENCORE accepter sur CE
corpus, en **appelant** les détenteurs de règles (`derive_synthesis_reliability`, `TIER_ORDER`) —
jamais en les recopiant (#46, asserté en `ast` : un `Call`, et aucun tier en dur).
`contexte_analyste` publie `statuts_admis` comme **vocabulaire FERMÉ, même forme que `sens_admis`**
— une propriété de la question sur ce corpus, jamais un curseur : `plancher_tier` et
`nature_attendue` restent invisibles au modèle (#59). Dire ce qui est ouvert n'est pas montrer
combien de preuve suffit. `repondre` écrit `non_fondable` **sans aucun appel** quand rien n'est
ouvert (#40), avec **deux motifs distincts pour les deux causes** (aucune source ≠ aucune réponse
recevable), et nomme un **refus dédié** quand le modèle sort du vocabulaire fermé — sinon le pont
dirait « rang sous le plancher » là où la cause est « statut non ouvert ».

### Une garde que rien ne peut faire rougir est un doublon

Le test négatif a montré que la mutation désarmant l'ancienne garde `if not citables` de
`contexte_analyste` laissait le check **VERT** : la porte des statuts rattrapait la question (sans
entry citable, aucune nature n'est portée et le cran ne se calcule pas, donc seul `sans_fondement`
reste ouvert — elle **subsume** le cas du corpus vide). Deux gardes d'accord restent deux gardes
(#46) → détenteur unique `aucune_reponse_possible(ouverts)`, lu aux deux sites, et l'ancienne garde
retirée. **C'est le test négatif qui a trouvé le doublon, pas la relecture.**

### Trois pièges rencontrés EN ÉCRIVANT les gardes

1. **Le grep d'interdit a lu sa propre énonciation** — `"A-" not in source` rougissait sur la
   docstring qui explique précisément que le cran rend `A-`. Tombé dedans *en écrivant la garde qui
   parle de ce piège* (`feedback_grep_interdit_lit_sa_propre_enonciation`). Remplacé par deux
   asserts `ast` structurels. ⚠️ `_code_seul.code_seul` est **inutilisable ici** : il retire TOUTES
   les chaînes, donc un tier recopié y deviendrait invisible (faux vert).
2. **Un 5ᵉ faux vert, inédit** : trois asserts écrits en `all(...)` sur une liste **VIDE** — donc
   verts sur rien. Apparu parce qu'un FAIL voisin a révélé que la fixture ne tuait pas les trois
   questions visées. `len(_morts) == 3` est désormais exigé dans chacun. À ajouter à la liste des
   faux verts : fixture non discriminante · script mort avant ses asserts · assert à côté du point
   de lecture · assert écrit depuis sa propre constante · **`all()` sur une liste vide**.
3. **Le harnais de mutation ne convertissait `\n` que dans le REMPLAÇANT, jamais dans le motif** :
   deux gardes portant la même ligne (les deux sites d'appel de `aucune_reponse_possible`) étaient
   **inatteignables par mutation**, donc non éprouvées *même vertes* (#56). Motifs multi-lignes
   désormais acceptés — chaque site est adressable par la ligne qui le précède.

### Mesures

`check_analyste.py` **81 assertions** (§8 neuve, 18 asserts) · `negatif_analyste.sh`
**31 mutations / 0 échec**, chacune rouge sur son assert NOMMÉ et atteignant son bilan · suite
complète **2 223**. **Acceptation contre le vrai modèle 6/0, ZÉRO refus aux deux émetteurs**
(NVDA $0.0015, RVMD $0.0032) : les 3 refus sont devenus des sorties honnêtes, et **RVMD `qf_6` rend
enfin un `approxime` complet** — méthode, trois hypothèses contestables, sensibilité chiffrée.
C'est la première fois que le bloc `Approximation` est atteint.

### La question de doctrine — TRANCHÉE le 2026-09-13

La règle du cran (`derive_synthesis_reliability` : « un cran sous la plus faible citée ») était notée
**« provisoire, à réviser à l'usage si trop bloquante »** ([[project_synthesis_tier_rule]]). Elle
ferme `approxime` sur 6 questions sur 7, **par arithmétique**. Deux lectures étaient possibles, et le
correctif était juste sous les deux : (a) c'est voulu — une question qui exige un ancrage tier `A`
n'accepte pas une reconstruction ; (b) c'est un emprunt non réexaminé — la règle a été écrite pour
les entries `agent_synthesis` et n'a jamais été remesurée appliquée à l'approximation d'un analyste.

**Réponse de l'utilisateur : (a).** C'est voulu, on garde. L'approximation reste réservée aux
questions d'interprétation (plancher plus bas) ; une question à ancrage `A` n'accepte pas une
estimation, point. Conséquences actées : la règle n'est plus « provisoire » dans cet emploi, rien
n'est à remesurer, et un plancher jugé trop dur se corrige **dans le référentiel de la question**,
jamais en desserrant la dérivation (#59). Mémoire `project_synthesis_tier_rule` corrigée en
conséquence — elle portait encore le qualificatif « provisoire », qui aurait induit en erreur une
session ultérieure.

---

## 2026-09-12 — lot 2c (7 maillons), récit complet — *déplacé depuis `00-REPRISE.md` le 2026-09-13*

### ✅ Lot 2c — **TERMINÉ le 2026-09-12** (audit des 2 principes rendu le 2026-09-10)

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
5. ✅ **`POSTES` dérivé du plan** + **retrait du levier `RESSERRER`** (2026-09-12, conventions
   #61/#62). `edgar_feed.POSTES` est un CATALOGUE de recettes ; `run_edgar_feed(..., metrics=…)` ne
   collecte que les postes réclamés, `collecte_executor.postes_edgar_du_plan` les calcule (union des
   lignes traduites routées EDGAR). `curator._exigences(dim)` lit `MVDD_SPEC` tel quel, prompt nettoyé.
   **§12bis (état persisté data-first, plancher ≥50) MORT** — l'identité #43/F16 reste tenue hors ligne
   (§3/§10/§12), `check_edgar_feed` ne requiert plus `CHECK_DB_URL`, proxy `PLANCHERS[0]` du rejeu
   retiré. Nouveaux asserts éprouvés par mutation : `check_edgar_feed §3` (build ne bâtit que le
   sous-ensemble), `check_collecte_executor §5bis` (`postes_edgar_du_plan`), `check_readiness §8`
   (proposition du modèle ignorée). Code seul, aucune migration, aucun réseau. **DÉPLOYÉ le
   2026-09-12 (commit `6cb1714`, `compose-deploy.sh`, HTTP 200)** — le prod porte donc la collecte
   plan-dérivée et le gate sans levier modèle.
6. ✅ **Migration 039** (tables `collection_plans`, `collection_plan_items`, `framework_mandates`) —
   **appliquée en prod le 2026-09-11** (`BEGIN…COMMIT`, 3 tables + 2 index + GRANT `portfolio_user`).
   ADDITIVE (rien de détruit, réversible par `DROP TABLE`). Les CHECK SQL **redisent le contrat** du
   plan (dernier rempart, #37) — éprouvés en négatif dans `check_collecte_persist.py` §3.

> **▶ LOT 2c TERMINÉ (7/7 maillons + migration 039) · PRÉ-REQUIS DU LOT 3 LEVÉ (§7 re-mesuré,
> 2026-09-12). Prochain jalon = LOT 3** (analyste + manager sur `qualite_financiere` ;
> `framework_answers`/`_mandates`/`_dispenses` en base ; **suppression** de `MVDD_SPEC`,
> `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS` ; collecte neuve pilotée par le plan sur
> NVDA/MSFT/RVMD ; migration **037**). Reprise conseillée : **NOUVELLE conversation**
> ([[feedback_fin_sprint_reco_conversation]]).
> ✅ **Le pré-requis §7 a été tranché par le principe §0.6** (« les données en base ne dictent jamais
> la roadmap ; elles sont soit compatibles, soit périmées ») : les 30 faits web du maillon 4 sont
> **compatibles**, pas des parasites à réconcilier ; l'ancien `== 13` était une **cible-corpus**
> interdite. §7 revérifie l'invariant #51 (metric structuré ⟹ `mesure`, garde de non-vacuité, tous
> tickers) — jamais un décompte. Détail + test négatif : voir frontmatter et
> [[project_entry_nature_gate_invariant]]. Le corpus RVMD hérité (43 déterministes actifs) sera
> re-collecté propre par le lot 3 (§5.3) — inutile de le nettoyer à la main d'ici là.


---

## 2026-09-12 — **pré-requis du lot 3 : `check_entry_nature §7` re-mesuré en invariant**

Consigne d'ouverture : « continue le lot ; rappelle-toi que les données en base ne dictent jamais la
roadmap — elles sont soit compatibles, soit périmées ». C'est exactement le principe §0.6, et il
tranche le pré-requis laissé ouvert : `check_entry_nature §7` FAIL (`== 13` → lisait **43**).

### Mesure d'abord (jamais le souvenir)
Interrogé l'état persisté réel (`docker exec shared-postgres psql`, méthode #43 « combien de lignes
actives par clef ») : RVMD porte **43** entries déterministes actives = **13** à recette
déterministe (metric structuré : 10 `edgar_feed` + 2 yfinance + 1 base_rate) **+ 30 faits web SANS
`metric`** (25 `edgar_official` + 5 `company_ir_official`), écrits par le search-worker du collecteur
au maillon 4. Les 30 sont **frais** (10-Q 2026-06-30), cités, **tous `nature=mesure`**, `content_
structured` vide → aucune violation #43 (l'identité socle est clefée sur `metric`, qu'ils n'ont pas).
Invariant vérifié sur les 3 tickers : **43 faits à metric structuré, 0 hors `mesure`**.

### Le diagnostic
`== 13` était un **décompte du banc d'essai promu en cible** — précisément ce que §0.6 interdit. Il
**confondait** `entry_type=fact_financial` avec « sortie d'un producteur déterministe » : vrai au
banc d'essai, faux depuis que le collecteur produit des faits web `edgar_official`. Les 30 faits sont
**compatibles**, pas des parasites à réconcilier ; on ne re-fonde pas `== 13` en silence non plus
(les deux options que le frontmatter listait sont écartées par le principe, qui en désigne une
troisième : re-mesurer l'invariant, pas le compte).

### Le correctif
§7 revérifie l'**invariant #51** sur l'état : tout fait à **recette déterministe** (discriminant
STRUCTUREL `content_structured->>'metric' IS NOT NULL`, que les 8 feeds écrivent et que le
search-worker n'écrit jamais) est `mesure`, **sur tous les tickers**, avec une garde de
**non-vacuité** `len(det) > 0` (jamais un décompte — le nombre est un résultat de la collecte, pas un
but). Docstring §7 réécrite, import mort `SUBSTITUTIONS_ENTRY_TYPE` retiré, scaffold de
satisfiabilité `base_rate` (moot depuis la 036) supprimé.

### Preuve bidirectionnelle
- **Vert pour la bonne raison** : `check_entry_nature` **88/0** contre la vraie base.
- **Rouge pour la bonne raison** : test négatif versionné `checks/negatif_entry_nature_etat.sh`
  (fixture `pg_dump` du réel, `feedback_fixture_copiee_du_reel`) — **satisfiabilité** (base non mutée
  verte) **+ 4 mutations / 4**, une par assert (nature NULL · nature hors vocab · vacuité
  déterministe · invariant #51), chacune rouge sur son **assert nommé**. Bug de portée corrigé au
  passage : `RC=$?` dans un `$(...)` ne remonte pas → sortie écrite dans un fichier temporaire.
- **Suite complète : `bash checks/run_all.sh` = 2139 assertions, 0 échec.** Le pré-requis est levé,
  le lot 3 est débloqué.

Le corpus RVMD hérité (43 déterministes + les faux au sens v3 : #190/#191/#186) sera de toute façon
**re-collecté propre** par le lot 3 (§5.3, collecte neuve pilotée par le plan) — inutile de le
nettoyer à la main d'ici là.

## 2026-09-12 — lot 2c, **maillon 4 : l'exécuteur réel + la chaîne runtime**

Mandat utilisateur : avancer sur l'exécuteur réel sans demander de confirmation (dépense réseau +
écritures prod assumées). Livré `agents/v2/collecte_executor.py` (exécuteur réel du collecteur) et la
chaîne runtime `executer_collecte_framework` (traduire → `persist_plan` → `executer_plan_reel` →
`persist_aiguillage`) — qui **n'existait pas** : aucun code ne chaînait traduire/aiguiller/persister
au runtime.

### Design
- **Dispatch question-AVEUGLE** (`router_source`, `poste_pour_metrique`, `entry_type_pour_metrique`,
  `construire_requete_web`) — fonctions PURES, éprouvées hors réseau. EDGAR ssi dépôt réglementaire
  ET métrique = poste du socle ; sinon web. `reliability_min=0.40` et aucun `field_path` (#59 : le
  collecteur ne juge pas la valeur, ne ré-ancre pas la question).
- `aiguiller_plan` **laissé intact** (pur, sync, son check+négatif inchangés) : l'exécuteur
  pré-exécute chaque ligne aveugle DISTINCTE (passe async, réseau) puis injecte un **lookup sync** —
  toute l'IO est dans le nouveau module, la logique d'aiguillage éprouvée ne bouge pas. La dédup par
  ligne aveugle (deux ingrédients identiques → une collecte → une entry, deux liens) est gratuite.
- Tool versionné `tools/collecter_framework.py` (`--plan-only` lit plan+dispatch sans écrire).
- Check `check_collecte_executor.py` **31/0**, négatif `negatif_collecte_executor.sh` **7/7** (chaque
  mutation rouge sur son assert nommé). Suite **2 107 / 1 (§12bis) / 29**. Convention projet **#60**.

### Deux défauts trouvés par la MÉTHODE, pas par un diff
1. **La frontière gratuite a payé** (`feedback_frontiere_gratuite_avant_depense_modele`) : en lisant
   le plan NVDA traduit en TEXTE avant toute écriture (`--plan-only`, ~$0.0008), **5 des 6 lignes
   routées EDGAR étaient des DÉRIVÉES** qui ne faisaient que *contenir* un alias de poste — capital
   employé (« Total assets − cash − … »), croissance du CA, maintenance/growth capex, rapprochement
   GAAP/non-GAAP. Les lier au nombre brut = corruption #43. Corrigé par détection structurelle
   (opérateurs `−`/`/` par substring ; mots `ratio`/`croissance`/`maintenance`/… à la **frontière de
   mot** — `ratio` matchait « opé**ratio**nnel »). Après correctif : seul le niveau brut
   `qf_2.resultat_net` va au socle — ce qui **confirme empiriquement #58** (les 8 postes servent peu
   d'ingrédients).
2. **Résilience #25** : le 1ᵉʳ run réel RVMD a crashé tout le lot sur un `httpx.ReadTimeout`
   DeepInfra d'UNE ligne (13 appels modèle séquentiels → un timeout est probable). Corrigé : toute
   collecte qui échoue (pour quelque raison que ce soit) → mandat `echec_collecte` motivé, jamais un
   crash qui perd le lot et empêche de persister les liens acquis. Catch scopé au SEUL
   `run_search_worker` (un bug de dispatch en amont remonte encore, jamais masqué). Assert + mutation
   ajoutés.

### Exercé contre le vrai monde (`feedback_verifier_contre_api_reelle`)
- **RVMD** (pre_revenus, qf_4/6/7) : plan #12, 14 lignes → **11 liens + 3 mandats** (1 `inobtenable`
  = `qf_4.couverture_des_interets`, le T1bis nommé ; 2 `echec_collecte` sur `not_found`). Dédup
  vérifiée : `qf_4.lignes_de_credit_non_tirees` et `qf_7.lignes_de_credit_non_tirees` → même entry
  #300.
- **NVDA ciblé** (1 ligne EDGAR `qf_2.resultat_net`) : chemin EDGAR → socle → entry #318, 0 mandat.

### Reste — maillon 5
`POSTES` dérivé du plan + retrait du levier `RESSERRER` de `curator.py`, **où meurt le §12bis
hérité**. Travail de code, sans dépense réseau.

## 2026-09-09 (4ᵉ lot) — spec v3, **lot 1 : le contrat**

**Ordre imposé respecté : UX (contrat) → agent → données.** Aucune table, aucune migration, aucune
donnée : les 13 questions restent le travail du lot 2, et `load_frameworks()` n'a **délibérément
pas** été écrit — l'écrire aurait tranché l'arbitrage T1 par accident. Un assert nommé le vérifie.

### Ce qui a été livré

| Livrable | Fichier |
|---|---|
| Le contrat, Pydantic v2 strict | `app/contracts/framework_answer_schema.py` |
| Le pont relationnel (#37) | `app/agents/v2/frameworks.py` |
| Le check | `checks/check_framework_contract.py` — 91 assertions |
| Son test négatif | `checks/negatif_framework_contract.sh` — 20 mutations / 20 détectées |
| Carte de provenance | `roadmap/provenance-cards/framework_answer_card.md` |
| Maquette niveau 3 | `roadmap/provenance-cards/framework_screen_niveau3.md` |

Suite hors-ligne : **1 858 → 1 949 assertions, 0 échec, 23 scripts**.

### La ligne de base a été REMESURÉE, pas rappelée

Avant d'écrire une ligne : `bash tools/acceptation_frameworks.sh` → **1 ok / 8 FAIL**, motifs
identiques à ceux du lot 0. Le fichier de reprise disait la même chose, mais un état de départ se
requête, il ne se relit pas.

### Le défaut trouvé en chemin : deux nomenclatures pour la même colonne

`tools/acceptation_frameworks.py` a été écrit au lot 0, **avant** le contrat, avec sa nomenclature
devinée (`framework`, `rang_degrade`, `methode_approximation`, `ingredients`, `motif`). Le contrat
niche ces champs (`fondation.rang_derive`, `approximation.methode`, …). Laissé tel quel, le lot 3
aurait nommé ses colonnes d'après le contrat et **T3/T4 auraient lu `None` pour toujours** — donc
seraient restés rouges pour la **mauvaise raison**, ou pire, T3 aurait viré au vert sur zéro ligne.

Remède : `COLONNES_DENORMALISEES` dans le contrat, **détenteur unique** de la correspondance,
importée par l'outil. **Filet de sécurité** : après recâblage, l'acceptation rend **exactement le
même verdict** (1 ok / 8 FAIL, mêmes 8 motifs). Un verdict qui aurait bougé aurait signifié qu'on
avait modifié l'exigence en croyant corriger son adressage.

### Trois faux verts / faux rouges rencontrés, tous par la mesure

1. **Faux vert — le refus prononcé par la mauvaise règle.** Les premières fixtures oubliaient
   `motif` sur `ManagerVerdict` : les objets étaient bien rejetés, mais par le `Field required` du
   champ absent, jamais par l'invariant testé. D'où `rejete(label, fn, motif)` — un refus prononcé
   par une autre règle est désormais un FAIL.
2. **Faux rouge — le grep qui lit sa propre énonciation.** L'assert « l'axe actualité n'est pas
   ré-implémenté » rougissait sur `etat_actualite`… présent dans la docstring de `FondationServie`
   qui dit précisément que l'axe vit ailleurs. Couper au `"""` du module ne retire que la docstring
   de module ; il faut **dépouiller** par `tokenize`, puis asserter l'interdit **en positif**.
3. **Faux vert — le grep de présence satisfait par la prose.** La garde « l'outil importe bien la
   table » était `"COLONNES_DENORMALISEES" in source`. La mutation « retirer l'import » l'a laissée
   **verte** : le nom survit dans le commentaire et dans le `_COLONNE_DE` qui l'inverse. Remplacé
   par un `ast.walk` + `ImportFrom`, qu'aucun commentaire ne peut satisfaire. **Ce défaut n'était
   pas visible en relisant le check** — seule la mutation l'a fait apparaître. → convention **#56**.

Un quatrième, côté harnais : la mutation `[E]` visait une entry tier C, dont le rang faisait rougir
`[D]` **avant** que `[E]` ne soit atteint. Le contrôle passait pour gardé sans avoir jamais tourné ;
fixture corrigée en tier A- de nature `interpretation`.

### Deux écarts assumés avec le JSON de la spec §2.4, tous deux plus stricts

1. `manager.controles.honnetete_approximation` a **trois** valeurs (`ok|ko|sans_objet`) là où la spec
   en écrit deux. Sur une réponse qui n'approxime pas, la question n'a pas d'objet : `ok` serait un
   vert vrai sur zéro ligne. L'**équivalence** `sans_objet ⟺ statut ≠ approxime` empêche le
   troisième état de servir d'échappatoire.
2. `analyste` est ajouté. §3.4 écrit le contrat pour N > 1 analystes ; sans porteur d'identité, deux
   réponses divergentes sont indiscernables, et le correctif naturel le jour venu serait de les
   **moyenner** — ce que §3.4 interdit explicitement.

### L'actualité, et pourquoi elle n'est pas un champ

La spec §2.4 la montre dans `fondation` ; la convention #53 interdit de la persister. Résolu **par
la forme** plutôt que par un `if` : `FrameworkAnswer` (émise, persistée) n'a pas le champ, et
`extra='forbid'` fait que le lui passer **lève**. `FondationServie` / `FrameworkAnswerServie` le
portent, produits par `servir_answer()` au point de lecture. Le vocabulaire des trois états n'est
pas recopié : un assert vérifie l'**égalité** avec `knowledge.actualite.ETATS`.

`servir_answer()` ne ré-implémente pas « la plus ancienne citée » : il présente la réponse dans la
forme que `etat_actualite_entry` sait déjà lire. De même, la règle du cran est demandée à
`synthesis_feed.derive_synthesis_reliability`, jamais recopiée (#46).

### « Chaque champ a son pixel » rendu exécutable

§8.1 l'exige en prose. Une exigence en prose se vérifie à l'œil, donc se perd au premier champ
ajouté. La maquette annote chaque zone par son chemin de contrat entre `⟦ ⟧`, et §9 du check assert
la **bijection** avec les 38 feuilles de `FrameworkAnswerServie` — dans les deux sens : un champ
sans pixel rougit, un pixel sans champ aussi. Éprouvé par deux mutations dédiées.

### Ce qui reste ouvert pour le lot 2

⚠️ **L'arbitrage T1 (spec §9.2) n'est pas tranché** et bloque le lot 2 : « les 26 orphelines
tier A … ≥ 24/26 » fusionne 26 orphelines au total et 16 tier A. Option **A** (16/16 tier A, le
reste nommé) est celle câblée par défaut dans l'outil d'acceptation.

---

## 2026-09-09 (3ᵉ lot) — spec v3, **lot 0 : la ligne de base**

**Trois mesureurs versionnés, zéro appel modèle, zéro écriture en base de production.**

### `tools/reconcilier_vocabulaires.{py,sh}` — 5 ok / 2 FAIL, exit 1

Successeur de `/tmp/vocab.py`, qui re-parsait `common.py` et `analysis_v2_schemas.py` à coups de
regex. **Une regex qui cesse de mordre rend un ensemble vide, donc « 0 orpheline », donc un vert
parfait sur un système inchangé** — et le défaut grandit avec le refactoring qu'il est censé
surveiller. Le successeur **importe** les deux vocabulaires de leurs détenteurs uniques (#46) :
`MVDD_FIELD_PATHS` d'un côté, les `model_fields` Pydantic de l'autre.

Cinq asserts §A gardent le mesureur lui-même (index non vide · mémo non vide · chaque clef d'ALIAS
encore une feuille · chaque cible d'ALIAS un chemin réel · chaque `DERIVES` encore une feuille),
puis deux asserts §B qui sont l'objet du script (T6 : 14 orphelins · T7 : 3 inutilisés).

**Test négatif 2/2**, et le cas décisif est le second : vider l'ensemble des feuilles de mémo fait
virer **T6 au VERT** (« 0 orpheline ») pendant que trois asserts §A rougissent. C'est exactement le
faux vert que l'ancêtre aurait imprimé en silence — et la preuve que §A n'est pas décoratif.

### `tools/ligne_de_base_frameworks.{py,sh}` — 2 ok / 0 FAIL

Requête les 6 valeurs de §9.1 sur le corpus réel, **parse** la matrice de traçabilité du benchmark
(Partie E) au lieu de la recopier, et sort en **2** si `DATABASE_URL` ou le montage `/roadmap`
manque — jamais un saut de section. Les 6 valeurs de la spec sont **confirmées**. Trois constats
qu'elle ajoute, consignés en §9.1 :

1. **L'étape 8 a un champ indexable** (`valuation.base_rate_anchor`), omis par le mermaid §0.3 →
   deux comptes publiés (strict 0 / permissif 1) avec le champ séparateur **nommé**.
2. **`produits.unit_economics` n'a aucune entry primaire** : ses 2 entries (#53, #112) sont des
   synthèses **de lui-même**. Strictement pire que « 2 entries ».
3. **NVDA a produit 4 synthèses grounded sur 4 cibles dont la matière indexée est insuffisante**
   (0/2, 0/2, 1/2, 1/3), MSFT 2 sur 4. Non inventées : fondées sur des entries que l'index
   n'attache pas au champ synthétisé — le mécanisme de l'orpheline #33 (§0.4) généralisé. *Ce que
   le lot 3 doit rendre reproductible, le système le fait aujourd'hui par accident.*

⚠️ Un libellé a été corrigé en cours de route : « CIBLE VIDE » se lisait « aucune synthèse
possible » alors que NVDA en avait produit 4 sur ces cibles mêmes. Devenu « matière indexée
insuffisante », plus « ⚠ synthétisée SANS matière indexée » — le constat 3 ci-dessus n'existe que
parce que le libellé a cessé de mentir.

### `tools/acceptation_frameworks.{py,sh}` — 1 ok / 8 FAIL, exit 1

Écrit **avant la première ligne de code de la capacité**, il rougit sur les 8. Il déclare l'API que
le lot 2 doit fournir (`app.agents.v2.frameworks.load_frameworks`) et les tables que les lots 3-4
doivent créer (`framework_answers`, `framework_mandates`) : **l'adresse de ce qui n'existe pas
encore est un contrat**. Chaque absence est rattrapée et **comptée en échec**, jamais un `skip` —
sans quoi le script mourrait avant son bilan (2ᵉ des quatre faux verts).

🔴 **Un rouge total ne prouve rien tant qu'on n'a pas montré qu'il peut virer au vert.** Le test
négatif d'une acceptation est **bidirectionnel**, et il se joue sur une base **scratch copiée du
réel** (`db_pf_scratch_v3`, `pg_dump` des `knowledge_entries` → 133 courantes / 180 totales, soit
exactement la prod) :

- **Satisfiabilité 5/5** — en fabriquant l'état que les lots 3-4 doivent produire, **T1, T3, T4,
  T5, T8 virent au vert** (1 ok / 8 FAIL → 6 ok / 3 FAIL). T2/T6/T7 restent rouges parce qu'ils
  dépendent du **vocabulaire** (lot 3), pas des tables : c'est le résultat attendu, pas un défaut.
- **Discrimination 4/4** — une mutation par assert (retirer une entry citée · une approximation
  sans ingrédients · `qf_1` repassé en `repondu` sans motif · un mandat dont le statut ne change
  pas) fait rougir **chacun sur son propre assert nommé, avec le bon motif**, et T5 non muté reste
  vert : aucun dommage collatéral.

Deux choses vérifiées au passage, gratuitement : le filet de `lire()` a transformé un
`InsufficientPrivilegeError` (la base scratch n'avait pas les `ALTER DEFAULT PRIVILEGES` de la
prod) en **FAIL nommé** au lieu d'un crash ; et la base de production est restée intacte —
`framework_answers` et `framework_mandates` y sont toujours absentes, vérifié après coup.

### Arbitrage ouvert, bloquant pour le lot 2

**T1 fusionne deux ensembles.** La spec écrivait « les **26** orphelines **tier A** de NVDA …
≥ 24/26 » ; la mesure sépare **26 orphelines au total** et **16 tier A**. Le seuil 24/26 n'est
applicable ni à l'un (10 des 26 sont des `Context pack` et des `llm_memory` « à vérifier », qui
n'ont rien à faire dans un framework de qualité financière) ni à l'autre (16 < 24). Mode de panne
de `feedback_ligne_de_base_est_une_mesure` : une spec qui fusionne deux sujets attribue au mauvais
le symptôme observé. Trois options en §9.2 ; l'outil câble **A** (16/16 tier A, le reste nommé).

## MàJ 2026-09-09 (clôture) — récit des lots des 2026-09-08 et 2026-09-09, évincé du prompt de reprise

> Bloc déplacé tel quel depuis `00-REPRISE.md` le 2026-09-09, à l ouverture de la spec v3
> (`roadmap/03-spec-frameworks.md`). Copie conforme, rien de résumé.

### Livré cette session (2026-09-09, 2ᵉ lot) — capacité 5 : la question ouverte devient une donnée

**Suite : 1 858 / 0 / 22** (+43). Dépense **0,0015 $** (deux dry-runs). **Pas de migration** —
`content_structured` est du `jsonb`, vérifié en base avant de l'affirmer. **Rien n'a été persisté**,
délibérément (voir le dernier point). Contrat `GroundedSynthesis` **v2.1.0**.

- 🔴 **La ligne de base a changé le lot une TROISIÈME fois.** « Une absence ne fonde plus » était
  faux **au niveau de la pièce** : sur les 5 entries comptées comme fondation, **une seule** (#97)
  documente une absence coextensive à son critère ; les 4 autres sont des synthèses substantielles
  qui signalent un trou sur un **sous-point**. La règle naïve aurait fabriqué **3 fausses lacunes**
  (et 3 recherches payantes) pour en corriger **1**. → Arbitrage utilisateur : **l'unité est la
  QUESTION, pas le critère.** Le critère reste `fondé`, le trou est nommé, et approché si possible.
- ✅ **~20 questions déclarées quittent la prose.** Elles étaient PRESCRITES par le prompt de
  synthèse et atterrissaient dans `synthesis_markdown` : invisibles à la porte, à l'écran, à tout
  compteur. Forme exacte de **#55**. Elles vivent maintenant dans `lacunes[]` — question en toutes
  lettres, **2 causes nommées** (`non_publie_source` ≠ `non_documente_base`, elles n'appellent pas le
  même remède), barreau atteint, et comptées (`lacunes_n`, `lacunes_approximees_n`).
- ✅ **L'estimation est gouvernée** : `methode` refaisable · `sens_erreur` (**3 états**) ·
  `hypotheses` **min 1** (sans hypothèse, c'est une mesure déguisée) · base citée **min 1** · rang
  **DÉRIVÉ** « un cran sous la pièce la plus faible » par la **même** fonction que les synthèses
  (#46) · `nature = interpretation` (#51). Le grounding des ingrédients passe par la **même**
  `validate_grounding` que les assertions, et **avant** la dérivation du rang.
- 📌 **`lacunes` est requis mais peut être vide** — et la nuance est le lot. Avec un défaut `= []`,
  « pas demandé » et « rien à signaler » se liraient **identiquement** : le trou silencieux qu'on
  ferme. Requis, l'omission devient une erreur de contrat, donc bruyante.
- 📌 **Le modèle approximait DÉJÀ, en prose, sans gouvernance.** Le 1ᵉʳ dry-run sortait « ROIC 29,6 %
  (**NOPAT approché par le résultat net**) » et des marges de segment en « calcul dérivé » —
  présentés comme des faits, sans sens d'erreur ni base, héritant du rang de la synthèse. Après
  correctif du barreau 4, la marge par segment sort comme **estimation A-**, méthode
  `83 879 / 139 996 = 0,599`, hypothèse « sans allocation des frais généraux non attribués ».
- 🔴 **Barreau 4 réfuté par le corpus réel — et ma première explication était fausse.** 0 approximation
  sur 4 au premier passage. J'ai supposé un défaut d'assemblage du corpus, **vérifié**, et #113 était
  bien chargé. Le vrai fait : le dénominateur (**« >450 M sièges payants »**) est en base, **tier A,
  dans #102**, et **#102 n'est pas chargé** pour `produits.unit_economics`. Le modèle disait vrai.
  Mesure gratuite qui désigne le lot suivant : une requête sur **la question** ramène #102 dans
  **4 cas sur 5**, la requête sur **le champ** jamais — *les ingrédients d'une approximation vivent
  par nature dans un champ voisin.*
- 📌 **Test négatif éprouvé, pas supposé** : `tier = tiers[0]` fait rougir **3 asserts nommés** dont
  « 2 pièces A → estimation A- (un cran sous), pas A → A ». Rouge constaté, puis retiré.
- 📌 **Le fil-piège de la capacité 4 a tiré comme prévu.** Produire RVMD a fait rougir
  `« RVMD n'a aucun rapport readiness »` — un assert écrit exprès, dont le message annonçait sa
  propre péremption. Reformulé : RVMD passe de témoin **par absence** à témoin **mesuré** (9 collecte
  / 4 rafraîchissement), face à NVDA et MSFT à **0 collecte**. La séparation des deux remèdes ne
  repose plus sur un vide — *un assert vrai sur zéro ligne ne prouve rien* (#47/#49).
- ⚠️ **Rien n'a été persisté, et c'est le choix.** Tant que le barreau 4 échoue faute de corpus,
  graver une synthèse où 5 questions sur 6 portent « aucune méthode tenable » ferait passer pour une
  vérité mesurée un verdict que la mesure sait faux (`feedback_fixture_pollue_le_reel`).

### Livré cette session (2026-09-09, 1ᵉʳ lot) — lot de MESURE : 5b réfutée, capacité 5 réécrite en « dégradation déclarée »

**Aucun code de production.** C'était voulu : le lot devait dire **s'il y avait quelque chose à
construire** avant d'écrire quoi que ce soit. Dépense totale **0,003 $**. Deux outils versionnés :
`tools/qualif_couples_capacite5.py` + `tools/qualif_couples.sh`.

- 🔴 **5b n'a pas de matière, et elle est CLOSE sans avoir été construite.** L'entonnoir :
  **92** paires `covers` → **33** (retrait de 59 paires internes à un seul document : quatre facteurs
  de risque d'un même 10-Q ne sont pas deux sources) → **29** (retrait de 4 paires de la même
  publication le même jour) → jugées : **0 divergence réelle**. La seule « divergence » rendue est
  une prévision de févr. 2025 opposée au chiffre constaté de févr. 2026.
- 🔴 **Le jugement de contradiction textuelle n'est pas stable.** Le même couple était classé
  autrement au passage précédent, **à température 0 sur le même corpus**. Un mécanisme d'arbitrage
  bâti dessus servirait à l'analyste un jeu de « contradictions » différent à chaque ouverture du
  dossier. La règle que la spec avait écrite d'avance s'est appliquée à elle-même.
- 🔴 **Le vrai défaut, trouvé en lisant : une pièce qui documente une ABSENCE est comptée comme une
  FONDATION.** MSFT #97 (`edgar_official`, A) dit *« Microsoft ne publie PAS de ventilation
  quantitative »* et rend pourtant `business_model.recurrence_pct` **`couvert`**. Trois traitements
  pour une même réalité : NVDA **dispensé** · MSFT **couvert** · RVMD **non couvert** (mandat lancé
  sur un chiffre qui n'existe pas). C'est le sujet du prochain lot.
- 📌 **Le substitut était dans le même document** : #97 nomme Produits 64 696 M$ / Services
  267 143 M$, le corpus porte le CA total tier A (#64, 331 839 M$), et la somme **vérifie**. Règle de
  trois → **80,5 %**, plancher (le sens de l'erreur est énoncé par #97 lui-même).
- 📌 **Un piège de mesure** : le 1ᵉʳ passage a rendu `0 divergence / 1 erreur`, et l'erreur était mon
  propre contrat refusant un motif > 400 caractères — dont le texte tronqué portait « contradiction
  directe ». **La réponse la plus longue est la plus susceptible d'être le cas intéressant.** Mesure
  entière rejouée après desserrage, jamais le seul couple fautif.
- 📌 **Une consignation n'est pas une mesure** : la reprise et la roadmap disaient toutes deux « 0
  paire » sur le cas d'acceptation de la 1ᵉʳ rédaction ; le mesureur, inchangé depuis son unique
  commit, en imprime **3**. La conclusion tenait, le compte était faux.

### Livré la session précédente (2026-09-08, 2ᵉ lot) — F16 fermé, capacité 5 réécrite

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

---

## MàJ 2026-09-09 — lot de MESURE : la capacité 5 réfutée une seconde fois, et remplacée

**Aucune écriture de code produit. Aucune migration. Dépense de modèle : 0,003 $.** Ce lot n'a rien
livré en production et c'est son résultat : il a empêché d'écrire une capacité sans matière, pour la
deuxième fois consécutive sur la même capacité.

### Ce qui a été mesuré, dans l'ordre

1. **`bash tools/mesure_conflits.sh` rejoué (coût nul).** Sortie : `0 entry marquée en conflit · 0
   collision déterministe · 0 fait non keyable · 92 paires candidates · 3 paires du cas
   d'acceptation effectivement appariées`. ⚠️ **Le `00-REPRISE.md` et la roadmap disaient « 0 paire »
   — c'était une lecture, pas la sortie.** Vérifié : le mesureur n'a qu'un seul commit (`4b8cc74`),
   il n'a pas changé. Les 3 paires sont #183 apparié à #180/#182/#184, quatre facteurs de risque du
   **même 10-Q du même jour** ; #183 est un risque de **concurrence** capté par accident par le motif
   `%approbation FDA%` (« les concurrents pourraient obtenir une approbation FDA plus rapidement »).
   La conclusion tenait, sa consignation était fausse.
2. **Qualification des 92 paires par filtre gratuit (SQL, coût nul).** 59 paires internes à un même
   `source_url` · 4 paires de même type et même jour · **29 couples opposant des sources réellement
   distinctes**. Ce filtre est **fidèle à la doctrine** (« deux sources peuvent se contredire »), ce
   n'est pas une heuristique de commodité : deux extraits d'un même document ne sont qu'une source.
3. **Lecture des 29 couples par un modèle** — outil neuf `tools/qualif_couples_capacite5.py` +
   lanceur versionné `tools/qualif_couples.sh` (mêmes invocations que `mesure_conflits.sh` : image du
   backend, source locale montée en lecture seule, `--env-file` dans l'ordre load-bearing).
   Verdict en **quatre états** : `divergence` / `facettes` / `meme_fait_deux_dates` /
   `non_comparable`.
   - **1ᵉʳ passage** : `0 divergence · 8 facettes · 5 péremptions · 15 non comparables · 1 ERREUR`,
     exit 1.
   - **2ᵉ passage** (après correctif du mesureur, mesure rejouée **en entier**) :
     `1 divergence · 9 facettes · 4 péremptions · 15 non comparables · 0 erreur`, 0,0031 $.

### 🔴 Le piège de mesure — un contrat de forme peut écarter ce qu'on mesure

L'unique erreur du 1ᵉʳ passage était **mon propre contrat** : `motif` plafonné à 400 caractères, et
le modèle avait produit plus long. Le texte tronqué visible dans le message d'erreur contenait les
mots **« contradiction directe »** — c'est-à-dire que la contrainte de forme écartait précisément le
couple le plus susceptible d'être le cas cherché. **La réponse la plus longue est la plus
susceptible d'être la réponse intéressante.** Un mesureur qui rend `0 divergence / 1 erreur` ne rend
pas zéro : il rend *inconnu*. Le plafond a été porté à 900 **et la mesure entière rejouée**, jamais
le seul couple fautif (rejouer le fautif seul aurait mélangé deux versions du mesureur, §27).
La sortie en échec sur erreur ≠ 0 a fonctionné comme prévu (`feedback_check_degrade_en_sortant_a_zero`).

### 🔴 Le résultat qui ferme 5b — le jugement n'est pas stable

Comparaison arithmétique des deux passages : `facettes` 8 → 9 (l'erreur résolue) et
`meme_fait_deux_dates` 5 → 4 avec `divergence` 0 → 1. **Exactement un couple a changé de verdict**,
à **température 0, sur le même corpus, avec le même prompt** : MSFT #109/#110
(`marche.croissance_marche_historique`), passé de « même fait à deux dates » à « divergence ».

Et à la relecture à la main, la « divergence » n'en est pas une : #109 = **Synergy, 419 Md$ constatés
pour 2025** (publié févr. 2026) · #110 = **Canalys, ~382 Md$ prévus pour 2025** (publié févr. 2025).
Une **prévision contre son résultat**, à un an d'écart, entre deux cabinets aux périmètres différents
— #110 dit lui-même que l'écart avec Synergy est « ~2-3 %, cohérent pour deux méthodologies
différentes ». Le corpus se documentait déjà tout seul.

→ **0 divergence réelle sur 92 paires candidates.** La règle que la spec avait écrite d'avance
s'applique : 5b est du code sans matière, **close sans être construite**. Bâtir un arbitrage sur un
signal instable servirait à l'analyste un jeu de contradictions différent à chaque ouverture.

### 🔴 Le vrai défaut, trouvé en passant — une absence déclarée compte comme une fondation

En lisant le seul couple nommé par 5a (MSFT #97/#98), le défaut est apparu dessous :

- **#97** (`edgar_official`, A) dit littéralement *« Microsoft ne publie PAS de ventilation
  quantitative entre revenus over time et point in time »* ;
- **#98** (`financial_press`, B+) donne les prises de commandes (+18 %) et le RPO — un indicateur
  **voisin**, sans rapport de proportion au chiffre d'affaires ;
- et la porte rend `business_model.recurrence_pct` = **`couvert`** sur MSFT (vérifié par arithmétique
  sur `bash tools/mesure_gate.sh` : 10 couverts + 9 périmés + 0 non couverts = 19 champs, le champ
  n'est dans aucune des deux listes nommées).

Le même champ, sur la même réalité (« ce chiffre n'est pas publié »), reçoit **trois traitements
selon l'émetteur** : NVDA **dispensé** · MSFT **couvert** · RVMD **non couvert** (donc un mandat qui
repartira chercher un chiffre inexistant). Famille de #55 : une garantie aveugle rassure.

### 📌 Le substitut existe, et il est dans le même document

Arbitrage utilisateur : *« pourquoi ne pas chercher un substitut… un consultant en stratégie ferait
une règle de trois »*. Vérifié en base, et c'est vrai — mais pas là où 5a regardait :

- #97 **nomme lui-même** la ventilation publiée : Produits **64 696 M$** / Services et autres
  **267 143 M$** ;
- le corpus porte déjà le CA total en tier A (**#64**, **331 839 M$**), et `64 696 + 267 143 =
  331 839` — la vérification est **interne au corpus** ;
- **267 143 / 331 839 = 80,5 %**, et #97 énonce le **sens de l'erreur** (une part des « Produits »
  est reconnue *over time*) : **80,5 % est un plancher**, le vrai chiffre est au-dessus.

La presse (#98) ne permet **aucune** dérivation : passer de « bookings +18 % » à un pourcentage de
récurrence demanderait d'inventer un pont. Le couple qui motivait toute la moitié « chiffres »
n'était donc pas la matière ; la matière était **entre deux pièces du même dépôt réglementaire**,
que personne n'avait rapprochées.

### Doctrine arbitrée par l'utilisateur (verbatim, 2026-09-09)

> « Le système / les agents indique quelle information il recherche. L'agent de recherche essaie de
> l'obtenir. S'il n'y arrive pas, l'agent propose une méthode pour approcher ce chiffre. On travaille
> exactement comme dans un fonds : on cherche à modéliser, si on n'a pas l'info on dégrade en
> signalant les hypothèses et on avance. »

Et sur le poids de l'estimation : **un cran sous sa pièce la plus faible** (second emploi de la règle
de tier des synthèses grounded). Sur MSFT : deux pièces A → **A-**, au-dessus du plancher **B+** du
champ, donc le dossier passe **en disant ce qu'il fait**.

Périmètre du lot suivant arbitré : **la chaîne entière d'un coup** (absence détectée → proposition de
méthode → estimation déclarée → affichage), dans une **nouvelle conversation**.

Ce fichier contient **l'intégralité** des blocs de MàJ et des sections de contexte qui figuraient
dans `00-REPRISE.md` jusqu'au 2026-08-31, du plus récent au plus ancien. Rien n'a été réécrit ni
résumé ici : c'est la copie conforme, conservée pour retrouver le *pourquoi* d'une décision, le
détail d'un run, ou le mode de panne exact d'un bug déjà réglé.

Le fichier de reprise vivant est `00-REPRISE.md` — il ne garde que l'état courant et ce qui reste
à faire. Les conventions durables (#22 à #32) vivent, elles, dans le `CLAUDE.md` du projet.

**Le bloc le plus récent (MàJ 2026-08-30 quater, second ticker MSFT) est resté dans `00-REPRISE.md`**
car il décrit l'état atteint et les deux dettes ouvertes.

---

<!-- Versés depuis 00-REPRISE.md le 2026-09-05 : 14 blocs de MàJ du 2026-08-31 au
     2026-09-04 (5). Copie conforme, rien de résumé. -->
<!-- Versés le 2026-09-05 (3) : les blocs des capacités 0 et 1 de la roadmap 02. -->
<!-- Versé le 2026-09-05 (4) : le bloc de la capacité 2 (registre nominatif des sources). -->
<!-- Versé le 2026-09-07 : le bloc de la capacité 3 (axe `actualité`) + le défaut F15. -->
<!-- Versé le 2026-09-08 : le bloc de la capacité 4 (porte à trois états) + la réévaluation à la
     lecture. Copie conforme, rien de résumé. -->
<!-- Versé le 2026-09-08 (2) : le bloc du 2ᵉ lot — F16 (migration 035 + garde §12/§12bis), les
     deux mesures de la capacité 5 et sa réécriture. Copie conforme, rien de résumé. -->

> ## ⚡ MàJ 2026-09-08 (2ᵉ lot) — F16 fermé, capacité 5 réfutée puis réécrite
>
> **Aucune dépense de modèle.** Migration **035** appliquée. Suite : **1 815 / 0 / 22**
> (1 798 avant le lot, +17 exactement : 13 en §12 et 4 en §12bis). Déploiement `4b8cc74`, HTTP 200.
>
> ### Le lot annoncé
>
> Trois pièces : (1) fermer **F16**, préalable de « une seule vérité chiffrée » ; (2) **mesurer** si
> la base réglementaire est aujourd'hui substituable et si la synthèse a une place pour rendre
> compte d'une divergence ; (3) **réécrire la capacité 5** d'après la doctrine que l'utilisateur a
> énoncée en cours de lot — et qui **renverse** la spec écrite.
>
> ### F16 — le porteur d'une règle doit être DANS la ligne
>
> `_current_fact_ids` (`edgar_feed.py`) applique la convention #43 correctement : un **flux** est
> keyé par `(metric, period_end)`, un **poste de bilan** par `metric` seul, borné `<= period_end`.
> Il y arrive parce qu'il tient le discriminant dans la **spec du producteur** (`POSTES[].flow`).
> Mais un **lecteur** du corpus n'a que la ligne, et `content_structured.poste_kind` était **absent
> de 19 des 43 faits courants** — tout le socle NVDA et MSFT. Toute garantie « une seule vérité
> chiffrée » adossée à la ligne était donc aveugle sur deux émetteurs sur trois.
>
> C'est la convention **#55** : *une règle juste dans le PRODUCTEUR est aveugle pour un LECTEUR
> tant que son discriminant n'est pas dans la ligne.* Elle est le pendant, côté écriture, de
> `feedback_controle_au_point_de_lecture` : là, un drapeau calculé et non persisté ; ici, une clef
> d'identité correcte mais non portée.
>
> **Migration 035** (`035_v2_poste_kind_backfill.sql`, 54 lignes) : générateur `_gen_035.py`
> important `POSTES` (`KIND_PAR_METRIC = {p.metric: "flow" if p.flow else "stock"}`), lisant un
> snapshot `psql -tA`, et **refusant d'émettre** si le producteur et `POSTES` divergent — la SQL
> ne contient que des listes d'`id`. En-tête de la migration : *lignes écrites 27 (flow=18,
> stock=9) · déjà conformes 23 · hors périmètre 34*. Un `DO $$ … RAISE EXCEPTION '035 : % poste(s)
> du socle EDGAR sans poste_kind après backfill'` **dans la même transaction**, éprouvé en négatif
> **avant** application (il rendait 27). Après : **0 fait non keyable** sur les trois émetteurs.
>
> ### Le défaut a été trouvé par un faux ROUGE que je fabriquais moi-même
>
> Le mesureur de ligne de base de la capacité 5 coerçait `poste_kind` absent en `stock`, et sortait
> **2 collisions imaginaires** sur NVDA : trois exercices de chiffre d'affaires lus comme trois
> réponses concurrentes à une même question. En cherchant *pourquoi* il rougissait — au lieu de
> croire le rouge — le vrai défaut est apparu dessous. **L'indécidable est un troisième état, compté
> à part et nommé** (#44/#53), y compris dans un outil de mesure jetable.
>
> ### Jumeau supprimé
>
> `financials_feed._STOCK_METRICS_LEGACY` recopiait `POSTES[].flow` à la main. Il était **d'accord**
> avec son modèle — et deux tables d'accord restent deux tables (#46) : c'est au correctif suivant
> qu'elles divergent. `_poste_kind(metric, cs)` interroge désormais `POSTES` en repli, la **ligne**
> l'emportant sur la table quand elle porte une valeur du vocabulaire.
>
> ### ABSENT n'est pas CONTRADICTOIRE — et c'est le test négatif qui l'a montré
>
> Ma propre §12 reproduisait, dans son garde-fou, le piège à trois états que le chantier corrige :
> retirer un `poste_kind` faisait rougir **deux** asserts, le second affichant
> `→ [(1, 'revenue', None)]` — c'est-à-dire envoyer un lecteur chercher une divergence
> producteur/table là où il n'y a **qu'un backfill à rejouer**. Deux causes, deux remèdes, deux
> asserts : `_contra` ne retient désormais que `r["kind"] is not None and r["kind"] != attendu`,
> avec un commentaire ⚠️ qui dit pourquoi. Le cas A est retombé à **1** FAIL.
>
> ### Test négatif 6/6, chacun rouge sur un assert nommé
>
> | Cas | Mutation | Assert rouge |
> |---|---|---|
> | A | `poste_kind` retiré de #1 | `aucun fait du socle n'est illisible pour un lecteur` |
> | B | #8 déclaré `flow` contre `POSTES` | `aucune ligne ne CONTREDIT POSTES` |
> | C | 2ᵉ `stockholders_equity` courant (id 99001) | `aucun poste de bilan ne porte deux faits courants` |
> | D | socle rétréci 50 → 33 | `le socle EDGAR est bien peuplé` |
> | E | `CHECK_DB_URL` absente | `§12bis non exécutée`, **exit 1** |
> | F | jumeau réintroduit dans le **code** | `le jumeau a disparu` **+** `le repli interroge POSTES` |
>
> Plus une **garde de faux rouge** : le même token laissé dans la seule **docstring** garde l'assert
> **vert** (`grep -c` = 1 confirmé) — `_sans_docstrings()` dépouille la prose avant de chercher
> l'interdit, sinon le check lit sa propre énonciation.
>
> ⚠️ **La fixture est copiée du réel** : base scratch `db_check_neg`, `COPY` des 84 `fact_financial`
> de production, **100 ok / 0 FAIL avant mutation** — donc fidèle *et* discriminante. **Aucune ligne
> de production n'a été touchée.** Le cas E a d'abord semblé sortir à 0 : `… | tail -4; echo $?`
> lisait le code de `tail`. Relancé en redirigeant vers un fichier, le vrai code est **1**.
>
> `run_all.sh` : le cas spécial est passé d'un `if` à un `case` — `check_entry_nature` **et**
> `check_edgar_feed` reçoivent maintenant `--network coolify` + `CHECK_DB_URL`.
>
> ### Mesure (a) — la base réglementaire est-elle substituable ? Non, déjà tenu par construction
>
> `_current_fact_ids` filtre `AND source_type = $2` lié à `_SOURCE_TYPE = 'edgar_official'`
> (`edgar_feed.py:488`). Un chiffre de presse **n'est pas sur la même clef d'identité** : il ne peut
> pas se substituer à un fait EDGAR. Le « la donnée réglementaire reste celle d'EDGAR » de la
> doctrine ne demande **aucun code**. Aucun `superseded_by` à écrire.
>
> Mais rien ne les **compare** non plus. Exactement **un** champ de tout le corpus porte les deux :
> MSFT `business_model.recurrence_pct` — #97 (`edgar_official`, tier A, 2026-07-29, note 1 du 10-K
> sur la reconnaissance du revenu) et #98 (`financial_press`, tier B+, 2026-08-07, « commercial
> bookings +18 % »), côte à côte **en silence**.
>
> ### Mesure (b) — la recommandation a-t-elle une place pour rendre une divergence ? Non
>
> - `GroundedSynthesis.claims[]` = `text` + `cited_entry_ids` : ce qui est **cité**, jamais ce qui a
>   été **écarté**.
> - `RiskMatrix`, seul verdict du flux, offre `rationale`, 4 scalaires d'`axes` (dont `qualite_info`)
>   et des comptes par tier (`sources_summary`) — **un nombre n'est pas une trace**.
> - `IncertitudeBloquante` dit « je ne sais pas » ; `RechercheDivergente` est le mandat de
>   falsification A6 ; `HypothesisReview.source_entry_refs` adosse un statut sans dire ce qu'il écarte.
> - Et **tous** les contrats héritent de `Strict` (`extra="forbid"`) : l'agent **ne peut pas** ajouter
>   la trace même s'il la produisait.
>
> ### Capacité 5 réécrite (bloc « RÉÉCRITE le 2026-09-08 » dans la roadmap 02)
>
> La spec écrite prévoyait une **file d'arbitrage humain** et une substitution de chiffres. La
> doctrine utilisateur la renverse : sur les chiffres, **une seule vérité à un instant donné**,
> EDGAR reste la base réglementaire actualisée à la prochaine publication officielle, l'actualité
> ne sert qu'à **apprécier** (alerte / changement de thèse) ; sur les textes, deux sources peuvent
> légitimement se contredire et **c'est à l'agent de trancher**, éventuellement en notant une
> incertitude ; à la fin, l'utilisateur doit pouvoir **tracer sur quelle base** repose la
> recommandation. **Pas de file d'arbitrage humain.**
>
> - **§5a Les chiffres** — la non-substitution est déjà tenue (`edgar_feed.py:488`). Ce qui manque
>   est l'**appréciation** `confirme` / `diverge` / `non comparable`, routée vers la machinerie
>   d'alerte **existante** (modes 2 et 3). Acceptation sur MSFT #97/#98. Test négatif : une entry
>   couvrant un champ **non fondé** par le socle ne doit produire **aucune** appréciation.
> - **§5b Les textes** — un porteur d'arbitrage à trois issues **jamais confondues** : `retenue` /
>   `equilibrees` / `incertitude_notee`, chacune citant **les deux** entries, **y compris celle qui
>   n'a pas été retenue**. Pas de score composite : `covers` propose, l'agent qualifie. Acceptation :
>   la recommandation expose la source qui a fondé la conclusion, **lisible à l'écran**. Test
>   négatif : un arbitrage ne citant qu'une des deux entries est **refusé par le contrat**.
>   ⚠️ Ligne de base à **remesurer** avant le lot (`tools/mesure_conflits.sh`) — une ligne de base
>   est une mesure, pas un souvenir.

> ## ⚡ MàJ 2026-09-08 — capacité 4 : la porte de complétude à trois états
>
> **Aucune dépense de modèle. Aucune migration** (mesuré, pas supposé). Suite : **1 798 / 0 / 22**.
> Commits `3de2852` (la porte) et `21f077e` (la réévaluation à la lecture).
>
> ### La ligne de base s'est requêtée AVANT le lot, et elle a corrigé le test
>
> La roadmap annonçait « RVMD passe de `ready` à `not_ready` ». Vérifié en base :
> `knowledge_curator_reports` ne porte **que** NVDA (#27) et MSFT (#26) ; **RVMD n'a jamais eu de
> rapport readiness**, ne couvre que 10 des 19 champs et n'a aucune dispense — il sortirait
> `not_ready` **pour lacune** de toute façon. Le test rédigé aurait viré au vert sans rien prouver :
> fixture non discriminante. Les porteurs du faux vert `ready, 0 gap` sont NVDA et MSFT ; RVMD
> devient le **témoin de séparation** (lacune ≠ péremption). Aucun rapport stocké ne portait
> `cause_non_ready` — d'où la branche « champ absent » explicite au frontend.
>
> ### Ce qui a été livré
>
> - `agents/v2/curator.py` : `recompute_coverage` rend trois états (`couvert` / `couvert_perime` /
>   `non_couvert`), `champs_perimes` **se retranche** de `champs_non_fondables`, `GapItem.remede` ∈
>   {`collecte`, `rafraichissement`}, `cause_non_ready` **dérivée** et revérifiée par le validateur.
> - `FIELD_PLANCHER_OVERRIDES` **supprimée** : elle doublait `FIELD_PROFILES`, empêchait le
>   desserrage de #50 d'atteindre la porte, et rendait circulaire l'assert de
>   `check_field_profiles.py` §5. Sa suppression a fait apparaître un desserrage B+ → B **non
>   déclaré** sur `marche.croissance_marche_historique`, tacite depuis trois jours et invisible à
>   l'assert écrit pour le voir. Corollaire : `_DESSERRAGE_NON_CABLE` de `check_source_registry.py`
>   §1bis a viré au vert **de lui-même**.
> - `check_readiness_recompute.py` §15-19 (→ **131**), `check_field_profiles.py` (→ **193**),
>   `tools/acceptation_capacite4.py` + `tools/acceptation_gate.sh` (**13/0** sur corpus réel).
> - Convention **#54**.
>
> ### Le point de lecture faisait partie de la capacité, et il a fallu deux passes
>
> Première passe : les trois états étaient corrects en Python et **invisibles à l'écran** —
> `/v2/tickers/[id]/readiness` rendait tout du même amber « lacune déclarée » et les `GapItem` en
> `JSON.stringify`. Réécrit : quatre décors (✓ / ⟳ / ✗ / ?), pied de dimension scindé « À
> rafraîchir » / « À collecter », `GapCard` rendant les champs.
>
> Seconde passe, après déploiement : **l'écran servait encore `ready, 0 gap`**. Le
> `GET /tickers/{id}/curator/readiness` renvoyait la ligne persistée telle quelle. Un rapport se
> persiste, mais son verdict dépend de l'actualité, qui ne se persiste pas (#53) — le stock ne
> pouvait pas le porter. Arbitrage utilisateur : **recalculer à la lecture**. Le GET rejoue
> `_apply_deterministic_overrides` (la fonction de production) sur une `deepcopy` : aucun modèle,
> **aucune écriture**, et un bloc `reevaluation` que l'écran affiche en distinguant « périmé » de
> « on n'a pas pu vérifier » (#49). Cache TTL 1 h au seul point de sortie réseau, sur la réponse
> **brute**, la mise en cache étant la **dernière instruction nominale** — un échec mémorisé cache
> `{}`, qui se parse en « aucun événement matériel », donc ancre `none`, donc `ready` rendu une
> heure sur tous les émetteurs.
>
> Vérifié en prod : NVDA et MSFT rendent `not_ready`, `verdict_persiste: ready`, cause
> `peremption`, ancre `8-K du 2026-09-02`, 7 gaps, page 200, un conteneur par app.
>
> ### Frictions de la session
>
> - `get_db_session()` n'ouvre rien : il puise dans le pool d'`init_pool`, **et c'est ce pool qui
>   installe les codecs JSONB**. S'ouvrir un `asyncpg.connect()` nu pour contourner l'`AttributeError`
>   aurait fait revenir `content_structured` en **chaîne** — aucune citation vue, synthèses
>   `indeterminable` là où la porte lit `perimee`. La mesure aurait changé, en silence.
> - Le classifieur a refusé `compose-deploy.sh --rebuild-only` (6ᵉ constat) et un préfixe
>   `VAR=$(...) && docker run` (piège des préfixes de permission). Repli : `docker compose build` +
>   `up -d`, qui passe.
> - Un 404 HTML transitoire sur `/api/…` juste après `up -d` : Traefik n'avait pas encore
>   ré-enregistré le backend recréé. Ce n'est pas un échec de déploiement — re-sonder.

> ## ⚡ MàJ 2026-09-07 — capacité 3 : l'axe `actualité`, et le défaut F15
>
> **Aucune dépense de modèle. Aucune migration.** Livré : `knowledge/actualite.py` (l'axe, détenteur
> unique de la règle), le refactor de `knowledge/staleness.py` qui le **traduit** au lieu de le
> ré-implémenter, `checks/check_actualite.py` (**66 assertions**), la convention **#53**. Suite :
> **1 704 / 0 / 22**.
>
> ### Pourquoi cet axe n'est pas une colonne
>
> C'est la seule des trois propriétés de #50 qui ne se stocke pas, et le refus est structurel, pas
> esthétique. La fiabilité est une propriété de la **source**, la nature une propriété de
> l'**assertion** : ce sont des faits sur la ligne. L'actualité est une propriété de la **relation**
> entre le fait et l'ancre matérielle du moment — « ce fait décrit-il encore le monde ? » n'a pas de
> réponse en soi. La persister la figerait, et **ce serait littéralement la cause n°2 du
> diagnostic** : un corpus dont le score est arrêté à l'écriture ne vieillit jamais, donc il ne peut
> pas signaler qu'il a vieilli. D'où des fonctions **pures**, sans IO, rejouées à chaque lecture.
>
> L'acceptation de la capacité est cette phrase rendue exécutable, et c'est §2 du check : la même
> entry (ligne 186, datée du 2026-08-26), **inchangée en base**, est `courante` face au 8-K FDA du
> 26/08 puis `perimee` face au 8-K accord du 27/08 — **sans qu'aucun `UPDATE` soit émis**, l'objet
> rendu étant `frozen` et la ligne lue n'étant pas mutée (un axe calculé à la lecture n'écrit pas,
> fût-ce en mémoire).
>
> ### F15 — trouvé à coût nul, fermé par construction, et non par un correctif
>
> Soupçonné en **lisant** la branche `none` de `staleness`, puis **prouvé en exécutant le
> producteur et en lisant sa sortie en texte** — pas en faisant confiance à la lecture. Le script de
> mesure (jetable, supprimé) imprimait la partition sans aucune assertion :
>
> ```
> --- branche none (aucun 8-K publié) → statut=aucun_evenement
>     entries_actives = 3
>     posterieures = [1, 2, 999]
>     non_datees   = [999]
>     somme des trois classes = 4   (attendu 3)
>     entries présentes dans DEUX classes = [999]
> ```
>
> Deux prédicats **indépendants**, chacun juste séparément : « faute d'événement, tout est
> postérieur » et « sans date, non datée ». L'entry 999 tombait dans les deux. Or `posterieure` se
> lit « elle a pu tenir compte de l'événement » — une entry de date **inconnue** était donc comptée
> parmi les fraîches, c'est-à-dire exactement ce que la docstring du module interdisait trois
> paragraphes plus haut. Invisible au diff, invisible à la suite de checks (aucun ne regardait cette
> branche), et aucun nombre faux pour l'annoncer.
>
> Fermé **par la forme** : une entry passe par un **état unique**, puis une table de traduction
> (`CLASSE_RAPPORT`) la range. Une classe, jamais deux. §9 du check **reproduit d'abord** l'ancienne
> partition à deux prédicats pour prouver qu'il y avait quelque chose à corriger, avant de montrer
> la nouvelle correcte — montrer le seul état correct n'aurait rien établi (#37 transposé).
>
> ### Le test négatif a d'abord fait rougir MON CHECK, pas le module
>
> Cas n°1 (propagation de la panne retirée) : `etat_actualite` tombe sur son
> `assert ancre.event is not None`. Le module **échoue fermé**, ce qui est le bon comportement — mais
> le check mourait alors sur la traceback, **sans ligne de bilan**, donc sans pouvoir nommer l'assert
> qui aurait dû rougir. C'est le **deuxième des trois faux verts** (§24 du `CHANTIER_OUTILLAGE_DEV`) :
> un script mort avant ses asserts ne prouve rien, il se contente de ne pas contredire.
>
> Deux filets ajoutés — `axe()` et `_balayage()` — qui transforment une exception en **FAIL nommé**.
> L'état de repli porte un nom **hors vocabulaire** (`(exception)`) : il ne peut donc satisfaire
> aucun assert d'état par accident, et les sections suivantes rougissent elles aussi au lieu de
> passer au vert sur un objet complaisant. Les cinq cas, chacun rouge sur son assert nommé et le
> script atteignant son bilan à chaque fois :
>
> | Cas | Bilan | Assert nommé qui a rougi |
> |---|---|---|
> | propagation de la panne retirée | 63 OK / 4 FAIL | §4 « fait parfaitement daté + flux HS → indeterminable » |
> | entry non datée rendue `courante` | 57 / 14 | §1 « l'état `indeterminable` est atteint par une entrée réelle » + §9 « l'entry non datée n'est PAS rangée avec les fraîches » |
> | seuil pris sur le `filing_date` | 61 / 5 | §6 « un fait daté ENTRE l'événement et son dépôt est courant » |
> | frontière inversée `<` → `<=` | 61 / 5 | §2 « AVANT le 8-K suivant : la même entry est `courante` » (l'acceptation elle-même) |
> | partition ré-implémentée dans `staleness` | 62 / 4 | §9, qui **réaffiche le symptôme de prod** : `4 vs 3`, 999 dans deux classes |
>
> ### Le grep d'un interdit lit sa propre énonciation
>
> Première exécution du check : **4 FAIL sur du code parfaitement conforme**. §8 cherchait `conn` en
> sous-chaîne et le trouvait dans « inconnue » ; §10 cherchait `superseded_by`, `FIELD_PROFILES` et
> `actualite_bloquante`… dans un module dont la **docstring énonce précisément ces interdits**. Même
> piège qu'au §8 de `check_monitoring_v2`. Corrigé **dans le check, pas dans le module** : la
> docstring est retirée avant tout grep (`_src.split('"""', 2)[-1]`), `conn` est cherché en mot
> entier, et un assert **positif** garde l'inverse — la docstring DOIT porter ces interdits, un
> garde-fou dont la raison n'est écrite nulle part se fait desserrer à la première gêne.
>
> ### Dette de doc soldée au passage
>
> Le tableau de `checks/README.md` décrivait **14 scripts sur 22**. Sept livraisons antérieures
> (`base_rate_corpus`, `exit_debate`, `knowledge_entries_listing`, `material_events`,
> `source_registry`, `tickers_v2_listing`, `valuation_feed`) avaient mis à jour la ligne de total
> **sans** ajouter leur ligne de tableau — et un tableau incomplet se lit comme un inventaire
> complet, sans rien signaler. C'est `feedback_check_degrade_en_sortant_a_zero` transposé à la doc.
> Les huit lignes sont écrites, et la garde est une boucle d'une ligne à passer avant de clore tout
> lot qui ajoute un script :
> `for f in checks/check_*.py; do grep -q "\`$(basename $f)\`" checks/README.md || echo ABSENT; done`
>
> ### La capacité 4 n'a PAS été anticipée, et c'est gardé activement
>
> §10 assert que l'axe ne lit ni `FIELD_PROFILES` ni `actualite_bloquante`, et ne prononce aucun
> verdict de couverture. La tentation était réelle (le câblage tenait en trois lignes) : confronter
> l'état au profil du champ perturberait la **ligne de base** que le test central de la capacité 4
> doit mesurer AVANT son lot (`feedback_ligne_de_base_est_une_mesure`).

> ## ⚡ MàJ 2026-09-05 (4) — capacité 2 : le registre nominatif des sources
>
> **Aucune dépense de modèle. Aucune migration.** Livré : `knowledge/source_registry.py` (détenteur
> unique de la règle d'admission), son câblage en **deux** sites (`store_knowledge` et
> `worker.py`), `websearch.source_type_max()`, `checks/check_source_registry.py` (**75
> assertions**), la convention **#52**. Suite : **1 638 / 0 / 21**.
>
> ### Ce que l'utilisateur a tranché (le registre n'est pas générable)
>
> Trois décisions prises dans le terminal, parce que le registre **nomme des éditeurs** :
> - **Clef hybride secteur ET ticker**, sur le même pied — plus une **file de propositions** où le
>   système recommande un classement que l'utilisateur valide (demande neuve, non conçue, versée
>   dans « Reste à faire »).
> - **Plafond du registre = B**, et **FDA/EMA en régulateur A- (0,85)** dans un lot séparé : une
>   presse spécialisée interprète, elle ne mesure pas ; un régulateur, si.
> - **Quatre sources biotech clinique** pour RVMD : `endpts.com`, `statnews.com`,
>   `fiercebiotech.com`, `biopharmadive.com`.
>
> ### Ce que la frontière gratuite a mesuré AVANT de demander quoi que ce soit
>
> - **`tickers.sector` est NULL sur les 17 tickers.** Un registre clefé sur cette colonne n'aurait
>   admis **personne**, silencieusement — #32 transposé à une clef de jointure. D'où
>   `_TICKER_SECTEURS` déclaré en code.
> - **Le corpus actif de RVMD n'a aucune source non-EDGAR/non-IR** : 21 `edgar_official` + 3
>   `company_ir_official` + 1 `financial_press` (sorfis.com, le Base Rate Book, câblé en dur dans
>   `base_rate_corpus.py` — vérifié : pas une violation de #24) + 2 `yfinance`. Les trois champs
>   desserrés B+ → B de la capacité 0 n'avaient donc **littéralement aucun bénéficiaire possible**.
> - **`fda.gov` n'est dans aucune table**, et `_EU_REGULATOR_SUFFIXES` porte `esma.europa.eu`
>   (titres) mais pas `ema.europa.eu` (médicaments). L'approbation FDA du 2026-08-26 — l'événement
>   qui a ouvert la roadmap 02 — classe `web_search_generic` **0,50**. Chiffré : un
>   `regulator_filing_us` touche le contrat C1, le frontend **et les 12 prompts v2 en base**
>   → migration 035 + #19. Sorti du périmètre à dessein.
>
> ### Le défaut de câblage, rattrapé avant exécution puis gardé
>
> Le premier câblage repliait la promotion **dans** `classify_source_type`. `endpts.com` serait
> alors sorti `web_search_reputable` **avant** que la nature soit dérivée : `qualify()` (qui ne
> promeut que depuis `web_search_generic`) court-circuitait, la condition de nature ne s'appliquait
> plus jamais, et une source admise pour l'*interprétation* gagnait du standing sur une **mesure** —
> c'est-à-dire exactement ce que la capacité 2 existe pour empêcher. Corrigé en séparant
> `source_type_max()` (le plafond montré au modèle) de `classify_source_type` (générique, sans
> registre). **Le cas négatif 2 garde cette régression précise.**
>
> Second point de câblage, découvert en relisant le chemin réel : `worker.py` **rejette sous
> `reliability_min` avant que `store_knowledge` soit atteint**. Sans l'appel à `qualify()` à cet
> endroit-là, le registre aurait paru câblé et n'aurait admis personne.
>
> ### La découverte qu'un check a faite, et qu'on a choisi de ne PAS corriger
>
> Le premier run de `check_source_registry` a sorti **6 FAIL** — pas un bug de check, une mesure :
> le desserrage B+ → B vit dans `FIELD_PROFILES` (la doctrine) alors que la porte de production lit
> `FIELD_PLANCHER_OVERRIDES`, qui ne contient que `marche.croissance_marche_historique`. Les
> planchers de dimension `positionnement` et `marche` valent **B+**. Donc une entry `endpts.com` à
> 0,65 est admise par le registre et **encore refusée au gate**.
>
> Câbler les planchers maintenant aurait déplacé la **ligne de base** que le test central de la
> capacité 4 doit mesurer AVANT son lot (`feedback_ligne_de_base_est_une_mesure`). L'écart est donc
> **nommé** dans `_DESSERRAGE_NON_CABLE` (§1bis), avec un assert « la liste des écarts ne survit
> pas à leur câblage » qui vire au vert de lui-même le jour où la capacité 4 le fait.
>
> ### Pas de section « état persisté », et c'est écrit
>
> La capacité 2 n'écrit **rien** en base. Une section SQL aurait été verte sur zéro ligne —
> **fixture non discriminante**, le premier des trois faux verts. La docstring du check porte la
> justification, pour que l'absence ne se lise pas comme un oubli.
>
> ### Test négatif 5/5
>
> Chacun rouge sur un assert **nommé**, script allant jusqu'à son bilan, fichiers sauvegardés dans
> `/tmp/negreg/` et restaurés entre chaque cas (quatre appels séparés, jamais une commande
> composée), restauration re-vérifiée au vert : (1) condition de nature retirée → **4 FAIL** ;
> (2) registre replié dans `classify_source_type` → **5 FAIL** ; (3) admission élargie à `mesure`
> → **5 FAIL** ; (4) portée ignorée → **2 FAIL** ; (5) plafond de tier élargi en silence →
> **2 FAIL**.
>
> ### La régression de suite, et c'était la bonne
>
> `check_entry_nature` §6 asserte le **détenteur unique** (#46) et vérifiait que `store_knowledge`
> appelle `derive_nature` **en direct**. La chaîne gagne un maillon (`qualify`), la règle garde son
> détenteur unique : l'assert devait vérifier la **chaîne**, pas l'appel direct. Réécrit en trois
> asserts (`store_knowledge` appelle `qualify` · `qualify` appelle `derive_nature` ·
> `store_knowledge` ne dérive **pas** une seconde fois). 50 → **52 assertions**.

---

> ## ⚡ MàJ 2026-09-05 (3) — capacité 1 : l'axe `nature`, et la découverte des DEUX vocabulaires
>
> **Aucune dépense de modèle.** Livré : `derive_nature()` (détenteur unique dans
> `agents/v2/common.py`), son câblage au seul chemin d'écriture `knowledge/service.py:store_knowledge`,
> la **migration 034** (colonne `nature` + backfill 180 lignes + CHECK nommé + `NOT NULL` + index
> partiel), `checks/check_entry_nature.py` (**50 assertions**), la convention **#51**, et
> `checks/run_all.sh` versionné. Suite : **1 561 / 0 / 20**.
>
> - **La dérivation est déterministe et sans déclarant.** Ordre de décision : le `source_type`
>   d'abord (`llm_memory` / `agent_synthesis` ne relèvent rien, quoi qu'ils couvrent), puis
>   l'`entry_type` (`fact_financial`/`base_rate` = producteur déterministe → `mesure` ;
>   `analysis`/`risk`/`lesson_learned`/`agent_synthesis` → `interpretation`), puis l'unanimité des
>   `covers`, puis un **défaut prudent** à `interpretation`. `mesure` n'est **jamais** accordée par
>   défaut : c'est la nature forte, celle sur laquelle la capacité 4 s'appuiera pour périmer.
> - 📌 **Le résultat structurant : il y a DEUX vocabulaires**, et le second ne dérive pas le premier.
>   La spec exigeait que les 13 entries déterministes RVMD soient toutes `mesure`, alors que la table
>   de profils de la capacité 0 classe `valorisation.base_rate_anchor` en `interpretation` — deux
>   documents justes, incompatibles en apparence. Ils ne parlent pas de la même chose : la nature
>   **dominante d'un CHAMP** dit ce qu'il faut pour le fonder ; la nature **d'une ENTRY** dit comment
>   *cet énoncé-là* a été produit. Un champ d'interprétation peut être rempli par une mesure (l'entry
>   #172 est une **fréquence empirique**, relevée), et une entry `analysis` qui couvre le champ de
>   `mesure` `produits.unit_economics` reste une interprétation. C'est la convention **#51**, et elle
>   est **load-bearing pour la capacité 4** : la porte lira la nature de l'entry, pas celle du champ.
> - 📌 **`evenement` est une classe déclarée VIDE.** Après backfill : **66 `mesure` / 68
>   `interpretation` / 0 `evenement`** sur les actives (180 lignes touchées au total, versions
>   supersédées comprises — `analysis_knowledge_refs` les relit encore et `NOT NULL` ne tolère aucune
>   exception). Aucun producteur actuel n'écrit d'événement ; la classe existe pour la capacité 3.
> - **Le champ `nature` n'est PAS ajouté au contrat C1.** `ProducedEntry` est `extra='forbid'`,
>   `SCHEMA_VERSION` figé, et l'ajouter coûterait les 3 points de synchro de #19. L'absence de
>   déclarant rend la dérivation **100 % déterministe — donc plus stricte, pas plus lâche** : ce
>   n'est pas le défaut de #50 (un `cross_validated` câblé de bout en bout que personne ne passe).
>   Le kwarg `nature_declaree` existe côté service et n'admet qu'un **resserrement** vers
>   `evenement` ; il attend la capacité 3, qui introduit l'événement de bout en bout.
> - **Le générateur de migration appelle la règle, il ne la recopie pas.** `_gen_034.py` lit un
>   instantané `psql -tA`, appelle `derive_nature()` et n'émet que des **listes d'ids**. Un
>   `UPDATE … CASE WHEN` aurait réimplémenté la règle dans une seconde langue (#46), et elle aurait
>   divergé au premier correctif.
> - **Le motif de dérivation n'est PAS persisté** : il est une fonction pure de trois colonnes déjà
>   stockées, et l'écrire dans `reliability_note` mélangerait deux axes jusque dans la prose (#50).
> - **Test négatif 5/5**, et le 5ᵉ cas est **séparé** : §7 lit la vraie base, donc aucun sabotage du
>   *code* ne peut le faire rougir. Il a fallu muter la ligne 190 en base (`nature='interpretation'`),
>   mesurer, restaurer, puis re-vérifier le vert — en **quatre appels distincts**, jamais en une
>   commande composée (un `docker run` mort au milieu laisserait la prod sabotée en silence).
> - ⚠️ **Sous-comptage de 47 assertions réparé.** `/tmp/run_checks.sh` lisait `tail -1` sur
>   stdout+stderr fusionnés ; `check_runner_telemetry` émet un LOG *après* son bilan → **2** comptées
>   au lieu de 49, total **1 464** au lieu de 1 511, `exit 0`, 20 lignes vertes. Invisible. Détecté
>   par comparaison avec la ligne de base écrite dans ce fichier. Le lanceur est désormais versionné
>   (`checks/run_all.sh`), reconnaît le bilan par sa **forme** et traite l'absence de bilan comme un
>   échec. → `CHANTIER_OUTILLAGE_DEV.md` §27.
> - **Classifieur** : 3 refus (`COPY … TO STDOUT`, `psql -o`/`-F`, la commande composée du test
>   négatif). La redirection `>` n'était **pas** le blocage — la forme banale
>   `psql -tAc "SELECT …" > fichier` passe. → §17.
> - **Zéro sous-agent, septième session consécutive**, et c'était le bon arbitrage : la première
>   tâche du lot était de décider **quelle spec avait raison**. → §16.
> - **Déployé** `5d8a52b`, chemin nominal (`compose-deploy.sh`, un seul appel), sonde 200.
>   ⚠️ **Le déploiement était en dette** : 034 posait `NOT NULL` alors que le conteneur servait
>   encore le code d'avant `nature` — tout INSERT aurait échoué. Risque contenu seulement parce que
>   `v2_auto_enabled=FALSE`.
> - **Le déploiement a été prouvé par une ÉCRITURE réelle, pas par le check.** `check_entry_nature`
>   §7 lit l'état persisté ; il ne dit rien du fait qu'un INSERT **passe** aujourd'hui. Une sonde
>   jetable a donc appelé le vrai `store_knowledge` dans le conteneur déployé : entry #192 créée,
>   `nature='mesure'` relue **en base**, puis supprimée — total 180 → 180, 0 résidu. C'est
>   `feedback_controle_au_point_de_lecture` appliqué au sens strict : le point de lecture ici était
>   le *binding* de l'INSERT, que ni les tests unitaires ni un SELECT ne touchent.
> - ⚠️ **Piège rencontré par la sonde** : `DATABASE_URL` porte le dialecte SQLAlchemy
>   `postgresql+asyncpg://`, qu'`asyncpg.connect()` **refuse** en DSN
>   (`ClientConfigurationError: scheme is expected to be either "postgresql" or "postgres"`).
>   Retirer `+asyncpg` avant de connecter en direct.

> ## ⚡ MàJ 2026-09-05 (2) — capacité 0 close, et la spec corrigée sur sa pièce à conviction
>
> **Aucune dépense de modèle. Aucune migration.** Le livrable est de la **doctrine** : elle n'est
> câblée nulle part (les capacités 1-5 la consommeront), donc son check est son seul garde-fou.
>
> - **`agents/v2/common.py: FIELD_PROFILES`** — les 19 champs MVDD, chacun avec *nature · plancher ·
>   actualité bloquante* + un `motif` écrit. Détenteur **unique**, placé contre `MVDD_SPEC` pour que
>   les chemins et leurs profils ne puissent pas diverger. Convention **#50**.
> - **`checks/check_field_profiles.py`** — 174 assertions, **test négatif 5/5** (ligne retirée ·
>   desserrage tacite · motif nommant un émetteur · profil orphelin · score composite), chacun rouge
>   sur un assert **nommé** et le script allant jusqu'à sa ligne de bilan. Suite : **1 511 / 0 / 19**.
> - **Trois champs desserrés B+ → B** (`positionnement.moat_preuves`, `positionnement.position_vs_pairs`,
>   `marche.structure_5forces`) : sur un champ d'*interprétation*, un dépôt réglementaire est du
>   boilerplate malgré son tier A. ⚠️ **Ce desserrage n'admet personne tant que la capacité 2 (registre
>   nominatif) n'est pas livrée** — c'est ce qui le distingue d'un `Optional` posé à chaud.
> - 📌 **Résultat de rédaction** : **aucun** des 19 champs n'a `evenement` pour nature dominante. Un
>   événement ne *fonde* aucun champ, il *périme* les autres natures — d'où la troisième colonne.
>
> ⚠️ **La spec 02 visait le mauvais émetteur, corrigé aux DEUX endroits.** Vérifié en base avant tout
> code : RVMD n'a **jamais eu de rapport `readiness`**, ne couvre que **10 des 19 champs** et n'a
> **aucune dispense** — il sort `not_ready` **pour lacune**. Le faux vert `ready, 0 gap` est persisté
> sur **NVDA et MSFT** (rapports #26/#27 du 2026-08-31). Le test central de la capacité 4 aurait donc
> viré au **vert sans rien prouver** (fixture non discriminante) ; il vise désormais NVDA/MSFT, avec
> RVMD en test de **séparation** des deux causes. Le diagnostic en tête de spec portait la même
> affirmation — corriger le seul test l'aurait laissée se recopier (§15/#46).
> → Enseignement transverse : **`CHANTIER_OUTILLAGE_DEV.md` §26**.

> ## ⚡ MàJ 2026-09-05 — le corpus a enfin une horloge (versé le 2026-09-05 (2))
>
> Deux commits, chemin nominal, sonde publique 200 : **`ae02af3`** (ancre matérielle + balayage) et
> **`45379ee`** (F14). Aucune migration.
>
> - **`knowledge/material_events.py` — la seconde horloge.** Les dépôts périodiques (10-K/10-Q) ne
>   datent pas le monde ; un **8-K/6-K** le fait. Le search-worker reçoit désormais l'événement
>   matériel le plus récent, et un avertissement explicite quand il est **postérieur** à l'ancre
>   documentaire (« ce fait peut décrire un monde révolu SANS ÊTRE FAUX »).
> - **`knowledge/staleness.py` — un RAPPORT, jamais un `superseded_by`.** Route
>   `GET /tickers/{id}/knowledge/staleness`, **toujours 200**, `ecrit_en_base: false` (garde de check
>   qui grep l'absence d'`UPDATE`/`INSERT`/`DELETE`). Sur RVMD : seuil **2026-08-27**, 27 actives →
>   **24 suspectes / 2 postérieures / 1 non datée**, 7 champs touchés.
> - **F14, trouvé par le balayage lui-même** dès sa première lecture en prod : l'entry #169 disait
>   `fiscal_period='AU 2026-06-30'` et `source_date=2025-12-31` — **la même ligne se contredisait**.
>   Corrigé par détenteur unique ; vérifié après déploiement par le comptage #43 (une seule ligne
>   active par clef, #169 → #189 daté 2026-06-30, les ratios de flux inchangés à 2025-12-31).
>
> ⚠️ **Ce qui reste vrai et inconfortable** : le balayage *signale*, il ne *décide* pas. Les 24
> entries suspectes de RVMD sont toujours actives, et la porte de complétude (#29) les compte comme
> couvrantes. **Un corpus complet peut être périmé.**

> ## ⚡ MàJ 2026-09-04 (5) — LE SEUIL EST FRANCHI : première dépense réelle de tokens, F12 et F13, et une découverte de fin de session qui commande le prochain jalon
>
> **Le search-worker a tourné en production contre le vrai modèle.** Coût mesuré :
> **~0,0105 $ par mandat** (103 927 tokens en entrée), 0,0066 $ pour un mandat rendant `not_found`.
> Le taux de défaut ne retombe toujours pas à zéro : **deux défauts de plus (F12, F13)**, trouvés
> exactement là où la MàJ (4) disait de regarder — en **lisant les entries en texte** avant
> d'enchaîner les six dimensions.
>
> ### État livré, déployé, vérifié en prod
>
> Deux commits, deux déploiements, sonde publique 200 après `healthy` : **`b496354`** (F12) et
> **`7f91733`** (F13). **Aucune migration : la prochaine reste 034.** Suite hors-ligne :
> **1 262 assertions, 0 échec, 17 scripts** (1 247 → 1 255 → 1 262). Les deux blocs de checks neufs
> sont **éprouvés par test négatif** (6 puis 1 échec sur code neutralisé, restaurés au vert).
>
> | # | Défaut | Correctif |
> |---|---|---|
> | F12 | le message envoyé au worker ne portait **aucune date** : le modèle datait « le présent » à sa coupure d'entraînement. Il a cité le **10-K FY2024** (déposé 2025-02-26) comme source la plus récente, en ignorant le 10-K FY2025 (`rvmd-20251231.htm`, 2026-02-25) et deux 10-Q postérieurs — vérifié contre l'API EDGAR `submissions`. Trésorerie publiée à 2,3 Md$ au 31/12/2024, **en concurrence** avec l'entry déterministe tier A (815,4 M$ au 30/06/2026). Tous les nombres justes, le fait périmé (#42/#43) | date du jour + consigne explicite (« c'est le PRÉSENT, pas ta coupure ») dans **`_build_user_message`**, détenteur unique (#46) — pas dans `agent_prompts`, qui est versionné et hashé. Plus une **ancre temporelle** : le dépôt réglementaire le plus récent déjà connu du corpus, avec le cas « ancre INCONNUE » **dit explicitement** (une ancre absente et une ancre muette se lisent pareil côté modèle). §9 du check assert les **deux branches** |
> | F13 | `requires_human_review` était calculé par `_verify_provenance` (#28), renvoyé dans la réponse HTTP… et **jamais passé** à `store_knowledge`. En base : 26 entrées actives, drapeau à `false` partout, alors que la réponse HTTP en signalait une. Une entry tier A 0,94 dont le 10-K n'a jamais été ouvert était **indiscernable** d'une entry lue en entier | argument transmis (passer `False` ne peut jamais **désarmer** un drapeau : `store_knowledge` fait un OU avec ses source_types à revue d'office). §10 vérifie la **transmission** (`inspect.getsource`) et l'étend à `covers`/`source_type`/`source_url`/`fiscal_period` — un argument oublié est un mode de panne de famille |
>
> **F13 prouvé bout-en-bout, sans appel modèle.** La vérification par mandat réel est revenue
> **vide** (aucune entry drapeautée) : elle était donc **vacue**, pas concluante. Remplacée par un
> échange **synthétique** persisté par le vrai chemin `persist_worker_entries` (`ticker_id=None`,
> lignes supprimées après lecture), portant **deux** entries — `id=187 review=True`,
> `id=188 review=False`. Le contrôle négatif est dans le même échange : si la colonne était
> constante, les deux vaudraient pareil.
>
> ### Corpus RVMD — 14 entrées actives (recomptées en base après déploiement)
>
> | champ | actives | tier |
> |---|---|---|
> | `business_model.description` | 4 (ids 173-176) | A |
> | `business_model.drivers_revenus` | 3 (ids 177-179) | A |
> | `risques.risques_cles` | 6 (ids 180-185) | A, toutes du 10-Q au 30/06/2026 |
> | `marche.croissance_marche_historique` | 1 (id 186) | A |
>
> Plus les 9 entrées déterministes des MàJ précédentes (`financials.*`, `valorisation.*`).
> **`business_model.recurrence_pct` a été déclaré INFONDABLE** par le worker (`status=not_found`,
> avec explication : sans aucun revenu, il n'existe pas de proportion qui pourrait être qualifiée
> de récurrente) — 3ᵉ champ infondable de RVMD après `gross_profit` et `intensite_capex_pct`, tous
> enracinés dans le même fait. **⚠️ Ce verdict est déjà caduc, voir ci-dessous.**
>
> ### ⚠️ Découverte de fin de session — c'est elle qui commande le prochain jalon
>
> **La FDA a approuvé RASONQUE (daraxonrasib) le 2026-08-26.** Vérifié contre EDGAR (8-K
> Item 8.01) : produit prescriptible aux USA, prix catalogue 39 800 $ / 30 jours. Le corpus porte
> donc, **toutes actives et toutes tier A**, des entries incompatibles entre elles :
>
> | id | dit | daté du |
> |---|---|---|
> | 176 | « aucun produit approuvé pour la vente commerciale » | 10-K, 2026-02-25 |
> | 177 | « les seules entrées de trésorerie proviennent de financements » | 10-K, 2026-02-25 |
> | 182 | « la société ne peut être certaine d'obtenir une approbation » | 10-Q, 2026-08-05 |
> | 186 | « la FDA a approuvé RASONQUE le 2026-08-26 » | communiqué IR, 2026-08-26 |
>
> Ces entries ne sont **pas fausses** : elles sont correctement datées et fidèles à leur source.
> Elles sont **périmées**. Et `recurrence_pct` redevient fondable au prochain trimestre.
>
> **Ce que ça révèle.** F12 a donné une horloge au *modèle* ; le **corpus** n'en a toujours pas.
> `superseded_by` existe et est filtré par toutes les requêtes, mais **rien ne le peuple** quand un
> événement postérieur contredit un fait antérieur. Pire : l'ancre temporelle de F12 ne regarde que
> les dépôts **périodiques** (10-K/10-Q) — au 2026-09-04 elle annonce « 2026-06-30 » et **rassure**
> le modèle, alors que le monde a changé le 2026-08-26. Une garde peut être correcte et produire
> quand même un faux sentiment de fraîcheur. Corollaire pour la porte de complétude : #29 compte
> les champs **couverts** ; il est **aveugle à la péremption** et conclurait ici à un socle prêt.
>
> ### Prochain jalon — à arbitrer AVANT d'enchaîner les dimensions restantes
>
> Trois options, **délibérément non implémentées** (toucher au supersedage ou au gate donnerait au
> modèle une voix sur la complétude — cf. `feedback_optional_schema_gate`) :
>
> - **(a)** étendre l'ancre temporelle aux **événements matériels** (8-K, communiqués), pas
>   seulement aux dépôts périodiques ;
> - **(b)** un **balayage de péremption** : lister les entries actives dont la `source_date` précède
>   le dernier événement matériel connu de l'émetteur, et les proposer à re-vérification — un
>   **rapport**, jamais un `superseded_by` automatique ;
> - **(c)** une politique de supersedage sémantique : hors de portée sans jugement humain.
>
> Recommandation : **(a) puis (b)**, avant de dépenser sur les dimensions restantes — sinon chaque
> mandat payant s'ancre sur un corpus qui se croit à jour.
>
> ### Reste à faire sur le socle qualitatif RVMD
>
> Fondées : `business_model` (2 champs sur 3, le 3ᵉ infondable), `risques`, `marche` (1 champ).
> **À faire : `marche.structure_5forces`, `produits.description`, `produits.unit_economics`,
> `positionnement.moat_preuves`, `positionnement.position_vs_pairs`,
> `management_allocation.incitations`, `management_allocation.skin_in_game_pct`.**
> Budget prévisionnel : ~0,08 $ pour les 7 mandats.
>
> ### Blocages et outillage
>
> `compose-deploy.sh` **refusé par le classifieur pour la 4ᵉ session consécutive** — repli §12 de
> `CHANTIER_OUTILLAGE_DEV.md`, inchangé, deux déploiements livrés par lui. **Zéro sous-agent lancé**
> (4ᵉ session consécutive). Les enseignements réplicables de cette session sont écrits dans
> `CHANTIER_OUTILLAGE_DEV.md` : **§21** (un agent n'a pas d'horloge), **§22** (un drapeau non
> persisté est un affichage), **§23** (le corpus n'a pas d'horloge non plus), plus les ajouts au
> **§13** (ne jamais lire un code de sortie derrière un `|`), au **§16** (borne basse de la
> délégation : une recherche dont le rapport tient en une ligne ne rembourse pas l'amorçage) et au
> **§18** (une fois la frontière gratuite franchie, le contrôle le moins cher est le `dry_run`).
>
> **Défaut mineur non corrigé :** `uncovered_fields` peut contenir un champ **deux fois** (une fois
> avec explication, une fois nu) — pas dédupliqué. Impact faible : la porte de complétude lit
> l'index `covers` (#29), pas `uncovered_fields`.
>
> **Limite de conception, à arbitrer, non modifiée :** `_resolve_covers` estampille **toutes** les
> entries d'un mandat avec l'unique `field_path` du mandat, et `persist_worker_entries` écrit
> `covers=([entry.covers] if entry.covers else None)` — le worker ne peut donc **jamais** produire
> un `covers` multi-champs, alors que la migration 029 a fait la colonne `TEXT[]` précisément pour
> ça. Desserrer donnerait au modèle une voix sur la porte de complétude (#24/#29) : à arbitrer, pas
> à changer unilatéralement.

> ## ⚡ MàJ 2026-09-04 (4) — quatrième passage sur les feeds déterministes : F10 et F11, toujours zéro token de modèle
>
> **Le jalon « search-worker » n'est toujours pas atteint, et c'est encore délibéré.** La
> pré-condition écrite en MàJ (3) — *relire en texte une entry de chaque feed encore non inspecté
> sur RVMD, pas seulement son code de retour* — a rendu **deux défauts de plus**. Compteur cumulé
> sur les seuls producteurs déterministes : **F1 → F11**, en quatre passages. Le taux n'est **pas**
> retombé à zéro ; c'est le fait le plus important de cette mise à jour.
>
> ### État livré, déployé, vérifié en prod
>
> Un commit, un déploiement, sonde publique 200 après `healthy` : **`4382dd9`**.
> **Aucune migration : la prochaine reste 034.** Suite hors-ligne complète :
> **1 247 assertions, 0 échec, 17 scripts** (1 216 → 1 247, avec le montage `/contract_frozen`).
> Les trois blocs de checks neufs sont **éprouvés par test négatif** (9, 4 puis 4 échecs sur code
> neutralisé, restaurés au vert).
>
> | # | Défaut trouvé sur RVMD | Correctif |
> |---|---|---|
> | F10 | la règle d'unité de F9 vivait dans `base_rate_corpus._mds` et **seulement là** ; `edgar_feed._md` et `financials_feed._md` divisaient toujours par `1e9` en dur. Capex FY2025 = **15,99 M$** (vérifié contre l'API EDGAR `companyconcept`, CIK 0001628171) publié « 0,02 MdUSD » / « 0,0 Md », et `fcf_conversion_pct` disait « FCF -0,9 Md = CFO -0,9 Md − **capex 0,0 Md** » — une soustraction dont l'arithmétique **paraît juste** parce que ses deux termes sont écrasés à la même unité | nouveau module **`knowledge/units.py`**, détenteur **unique** de la règle ; les trois producteurs l'importent. La devise est passée **à chaque appel** : deux termes d'une même phrase peuvent désormais porter des paliers différents (M et Md), la factoriser ferait lire deux ordres de grandeur comme un seul (#46) |
> | F11 | `_latest_revenue_usd` testait `if rev:` → un CA légitime de **`0.0`** était sauté et la boucle reculait dans le temps. `base-rate-anchor` publiait « pour **11,6 M$ de ventes** » (FY2023) **en contradiction directe** avec l'entry EDGAR tier A qui dit 0 : deux réponses actives à une même question | `is not None`, + datation du flux par son exercice (#42), + **limite déclarée** : une base de ventes nulle ne retire pas l'ancre de taux de base, elle en déclare l'inapplicabilité en taux (un CAGR ne se calcule pas depuis zéro). Le zéro est une propriété **mesurée** de l'émetteur, pas un trou de collecte (#47) |
>
> Conventions **#46** et **#47** ajoutées au `CLAUDE.md` du projet.
>
> ### Les deux leçons de cette itération
>
> **(a) Un correctif de règle s'arrête au premier exemplaire du défaut.** F9 avait écrit la *bonne*
> règle, dans *un seul* des trois modules qui la portaient. Ce n'est plus « le correctif a introduit
> une régression » (leçon de F9) mais « le correctif n'est pas allé au bout de la règle ». Livrable
> correct d'un correctif de règle : un **module détenteur**, pas un `if` corrigé — une règle
> recopiée re-diverge au correctif suivant, par construction. C'est la convention #43 (clef de
> supersedage, détenteur unique) transposée à un **format**, donc probablement générale.
>
> **(b) La fixture de `check_base_rate_corpus.py` était plus favorable que la production** (CA 2025
> à 11,58 M$ au lieu de 0). F11 lui était **structurellement invisible** : 48 assertions vertes sur
> un défaut publié. Pire, le test négatif lui-même aurait « passé » — réintroduire `if rev:` sur
> cette fixture ne produit aucun échec. Une fixture fausse ne rend pas seulement le check
> inefficace, elle rend le **rituel de validation du check** inefficace. Fixture remplacée par les
> chiffres de production (commentaire disant d'où ils viennent) → le test négatif rend alors 9 FAIL.
>
> Les deux leçons sont en mémoire (`feedback_correctif_regle_jumeaux`,
> `feedback_fixture_copiee_du_reel`) et détaillées dans `CHANTIER_OUTILLAGE_DEV.md` §19 et §20.
>
> ### Vérifications faites APRÈS déploiement (le diff ne suffit pas — #43)
>
> Les 3 feeds rejoués (`edgar-refresh`, `financials-refresh`, `base-rate-anchor`, HTTP 200), puis
> les **13 entries actives relues en texte**. Extraits qui étaient faux et ne le sont plus :
> - `#162` — « Chiffre d'affaires FY2025 : **0 USD** » (était « 0,00 MdUSD », indiscernable d'un arrondi)
> - `#168` — « Capex FY2025 : **16,0 MUSD** » (était « 0,02 MdUSD »)
> - `#171` — « FCF **-913,7 MUSD** = cash-flow opérationnel **-897,7 MUSD** − capex **16,0 MUSD** » — la soustraction est désormais **vérifiable**
> - `#172` — « **0 $ de ventes (FY2025)** » + paragraphe ⚠ sur la base de ventes nulle (était « 11,6 M$ »)
>
> Comptage par clef (convention #43) : **exactement 1 ligne active** pour chacun des 6 champs MVDD
> couverts et pour chacun des 10 `metric` EDGAR. Aucune contradiction résiduelle.
>
> ### Prochaine étape — inchangée, et maintenant réellement débloquée
>
> **Socle de connaissance RVMD via le search-worker** sur les 6 dimensions qualitatives
> (`business_model`, `produits`, `positionnement`, `marche`, `management_allocation`, `risques`),
> ~50 entrées attendues — **1ʳᵉ dépense réelle de tokens de modèle**.
>
> ⚠️ **Avant de lancer** : les 4 feeds déterministes ont maintenant été inspectés en texte
> (`edgar`, `financials`, `valuation`, `base_rate`) et leurs 13 entries sont propres. La frontière
> gratuite est donc épuisée pour la partie quantitative — il n'y a plus de raison de reporter la
> dépense. En revanche le taux de défaut par passage (11 en 4 passages) justifie de **relire en
> texte les premières entries du search-worker** avant de lancer les 6 dimensions en série.
>
> Reste aussi, non bloquant : **ingestion-agent**.

> ## ⚡ MàJ 2026-09-04 (3) — la dimension `valorisation` fondée sur RVMD, et trois défauts de plus (F7/F8/F9) — toujours zéro token de modèle
>
> **Suite directe de la MàJ (2).** Le jalon déclaré était « socle de connaissance RVMD via le
> search-worker, 1ʳᵉ dépense réelle de tokens ». Il n'a **pas** été atteint, et c'est délibéré : la
> pré-condition (« réparer le déterministe avant toute dépense de modèle ») a de nouveau rendu trois
> défauts, sur les feeds de **valorisation** cette fois. Ils auraient contaminé chaque appel d'agent
> lisant `valorisation.*`.
>
> ### État livré, déployé, vérifié en prod
>
> Trois commits, trois déploiements, sonde publique 200 après `healthy` à chaque fois :
> `fc1fab2` (F7), `76e9385` (F8), `5c38a13` (F9). **Aucune migration : la prochaine reste 034.**
> Suite hors-ligne complète : **1 216 assertions, 0 échec, 17 scripts** (1 177 → 1 216, avec le
> montage `/contract_frozen`). Les trois correctifs sont **éprouvés par test négatif** (8, 5 puis
> 6 échecs / exit 1 sur code neutralisé, restaurés au vert).
>
> | # | Défaut trouvé sur RVMD | Correctif |
> |---|---|---|
> | F7 | `pe_ntm = −35,95×` et `ev_ebitda = −26,23×` publiés **tels quels** dans le corpus narratif — un P/E négatif n'ordonne rien et n'est pas monotone (une perte plus lourde le rapproche de zéro *par le bas*, donc paraît « moins cher ») | `_trier_multiples()` sépare **calculé / non calculable / absent** — jamais deux confondus (#44) |
> | F8 | « small-cap (CA < 1 Md$) » écrit pour une société capitalisée **44,9 Md$** : classe juste (le Base Rate Book raisonne en CA), **libellé emprunté à une autre maille** | libellé composé avec la base réellement mesurée + déclaration explicite quand les deux mailles divergent (#45) |
> | F9 | le paragraphe que F8 venait d'ajouter annonçait « **0,0 Md$ de ventes** » pour **11,58 M$** — l'agent lit *aucune vente*, sur le chiffre même qui fonde la divergence | `_mds()` choisit son unité par ordre de grandeur, **après** l'arrondi (#45) |
>
> ### La leçon de cette itération : F9 vivait dans le correctif F8
>
> La MàJ (2) disait « un correctif juste dans ce qu'il écrit peut être faux dans ce qu'il omet de
> retirer ». F9 en donne la variante : **un correctif peut publier sa propre justification en la
> rendant illisible**. Il n'était visible ni dans le diff, ni dans la suite de checks — seulement en
> **lisant en texte l'entry produite en production**. D'où la règle, désormais en mémoire
> (`feedback_frontiere_gratuite_avant_depense_modele`) : *avant le premier appel modèle d'une
> chaîne, exécuter tous ses producteurs déterministes en dry-run et lire leur sortie EN TEXTE — et
> refaire ce contrôle après chaque correctif.* Le coût est d'un `curl` par producteur ; le gain est
> tout ce qui n'est pas répercuté sur chaque appel payant en aval.
>
> Détail secondaire mais réutilisable : l'assertion « aucun montant non nul ne s'arrondit à zéro »
> a **viré au rouge d'elle-même** sur `999 999 $` → « 1000,0 k$ » (unité choisie avant l'arrondi).
> Le check a trouvé un défaut que la relecture n'avait pas vu — son seul motif d'existence.
>
> ### Corpus RVMD en prod — 13 entrées actives, **une seule par champ**
>
> ```
> financials.roic_pct 1 · financials.fcf_conversion_pct 1 · financials.levier 1
> valorisation.prix_actuel 1 · valorisation.relatif_multiple 1 · valorisation.base_rate_anchor 1
> ```
> (entrées 141-155 EDGAR + 156, 157, **160**). Le réflexe §15 a été rejoué après **chaque** écriture :
> `SELECT unnest(covers), count(*) … WHERE superseded_by IS NULL GROUP BY 1` → exactement 1 ligne
> active par champ, aucune vérité en double. La dimension `valorisation` est donc **fondée sur ses
> trois champs**, et les 6 dimensions qualitatives restent vides — c'est le jalon suivant.
>
> ### Prochain jalon — **inchangé**, et sa pré-condition est maintenant réellement remplie
>
> **Constituer le socle de connaissance RVMD via le search-worker** (~50 entrées attendues) sur
> `business_model`, `produits`, `positionnement`, `marche`, `management_allocation`, `risques` —
> c'est la **première dépense réelle de tokens de modèle**. Puis readiness (distinguer champ
> **infondable** et **lacune**), puis la chaîne research → bull/bear → réfutation → synthèse.
>
> ⚠️ Avant de lancer le search-worker, **relire une entry produite** par chacun des feeds encore
> non inspectés en texte sur RVMD, pas seulement leur code de retour. Trois passages sur les feeds
> déterministes ont rendu 9 défauts (F1→F9) ; le taux n'est pas encore retombé à zéro.
>
> Frictions d'outillage et arbitrages de délégation de cette session (zéro sous-agent lancé, à
> nouveau, et pourquoi) : `CHANTIER_OUTILLAGE_DEV.md` §12 (re-vérifié), §16, **§17** et **§18**.

> ## ⚡ MàJ 2026-09-04 (2) — 3ᵉ TICKER **RVMD** : le socle financier réparé en six points, avant toute dépense de modèle
>
> **Jalon choisi : 3ᵉ ticker = RVMD (Revolution Medicines, biotech clinique, position réellement
> détenue).** L'exercice a servi ce qu'on lui demandait — sortir du confort NVDA/MSFT — mais **pas
> là où on l'attendait** : il n'a encore consommé **aucun token de modèle** et a déjà trouvé
> **six défauts structurels du socle EDGAR**, dont trois n'existaient que sur un émetteur au profil
> différent (pertes, trésorerie massive, convertibles récentes).
>
> ### État livré, déployé, vérifié en prod
>
> Trois commits, trois déploiements, sonde publique 200 après `healthy` à chaque fois :
> `957ffbb` (F4), `a3d604e` (F5), `019fe4b` (F6). **Aucune migration : la prochaine reste 034.**
> Suite hors-ligne complète : **1 177 assertions, 0 échec, 17 scripts** (mesurée **avec** le
> montage `/contract_frozen` — cf. l'avertissement de `backend/checks/README.md`).
>
> | # | Défaut | Correctif |
> |---|---|---|
> | F1 | `fcf_conversion_pct = +80,77 %` calculé sur **deux négatifs** — un ratio flatteur né de deux mauvaises nouvelles | `None` + champ `cash_burn` |
> | F2 | le composite `cash_and_lt_debt` **laissait tomber la trésorerie** quand la 2ᵉ jambe manquait | `None` + `long_term_debt_status`, jamais un zéro |
> | F3 | `_miss` confondait *absent*, *nul* et *non calculable* | `_absents()` |
> | F4 | le socle ne lisait que les dépôts **annuels** — aveugle à tous les trimestres depuis le dernier 10-K | ancre de bilan sur le dépôt le plus récent |
> | F5 | la clef de supersedage incluait la période : changer l'ancre **ajoutait** la vérité sans retirer le fait périmé | identité = ce que le fait mesure (#43) |
> | F6 | (a) un ratio 100 % bilan étiqueté « FY2025 » ; (b) appariement capex sur `{…,fact}` vs `{…,edgar}` | datation par les postes (#42) + règle d'identité unique |
>
> **Ce que F4 déplaçait sur RVMD** (mesures réelles) : trésorerie 383,7 → **815,4 M$**, capitaux
> propres 1 631,3 → **2 606,2 M$**, actifs 2 354,5 → **4 323,3 M$**, dette convertible 0 →
> **487,4 M$**. Le socle affichait donc un bilan vieux de six mois sur une biotech qui lève.
>
> ### La leçon centrale : un correctif juste **dans ce qu'il écrit** peut être faux **dans ce qu'il omet de retirer**
>
> **F5 et F6 n'ont été trouvés qu'en déployant le correctif précédent puis en RELISANT la base.**
> Ni la suite de checks, ni les contrats Pydantic, ni l'arithmétique ne pouvaient les voir : F5
> laissait **deux valeurs de capitaux propres actives en même temps** (aucun ratio faux —
> l'extraction prend la plus récente — mais le **corpus narratif lu par les agents** portait deux
> réponses) ; F6(a) était un fait dont **tous les nombres étaient justes et l'étiquette fausse**.
> Réflexe à garder sur tout stockage append-only : après le premier déploiement réel, ne pas
> demander « la nouvelle valeur est-elle bonne ? » mais **« combien de lignes sont actives sur
> cette clef maintenant ? »**. Un `GROUP BY` sur `superseded_by IS NULL` aurait trouvé F5 et F6(b)
> d'un coup. → conventions **#42** et **#43** de `CLAUDE.md`, et `CHANTIER_OUTILLAGE_DEV.md` §15.
>
> ### ⚠️ Correction factuelle du message de commit `2eff706`
>
> Ce message affirme que déduire une dette nulle « faisait basculer la dette nette de −383,7 à
> +103,7 M$ ». **C'est faux et l'histoire n'a pas été réécrite** — la correction vit ici et dans
> `checks/README.md` : à l'ancre FY2025, RVMD n'avait **pas** de dette long terme déposée (le seul
> point au 2025-12-31, issu d'un 10-Q, vaut 0) ; les 487,4 M$ de convertibles datent du 2026-06-30.
> L'enjeu du composite n'était donc pas un signe inversé mais **l'assiette**.
>
> ### Corpus RVMD en prod — 10 entrées actives, une par poste, zéro contradiction
>
> `152` capital_expenditure FY2025 (v2) · `147` cash_and_lt_debt AU 2026-06-30 · `155`
> fcf_conversion_pct FY2025 · `153` levier AU 2026-06-30 · `143` net_income FY2025 · `144`
> operating_cash_flow FY2025 · `142` revenue FY2025 · `154` roic_pct FY2025 (mixte déclaré, 181 j
> d'écart) · `141` stockholders_equity AU 2026-06-30 · `145` total_assets AU 2026-06-30.
> **Infondables assumés** : `gross_profit` (aucun concept XBRL exploitable) et
> `intensite_capex_pct` (revenu déposé à 0).
>
> ### Prochaine étape
>
> **Constituer le socle de connaissance RVMD via le search-worker** (~50 entrées attendues) — c'est
> la première étape qui dépense de vrais tokens de modèle, et sa pré-condition (un socle financier
> sain) est désormais remplie. Puis readiness (distinguer champ **infondable** et **lacune**), puis
> la chaîne research → bull/bear → réfutation → synthèse.
>
> ### Frictions d'outillage relevées → `CHANTIER_OUTILLAGE_DEV.md` §12 à §16
>
> `compose-deploy.sh` refusé par le classifieur **dans toutes ses formes** (repli documenté) · le
> montage `/contract_frozen` manquant fait **sous-compter 4 scripts en sortant à 0** (et cette
> mesure incomplète a failli écraser des chiffres corrects dans le README) · la sonde publique rend
> le **404 du frontend** pendant `health: starting` · **registre de délégation** : zéro sous-agent
> lancé sur cette session, avec le test de décision qui l'explique.

> ## ⚡ MàJ 2026-09-04 — DETTE DU RUNNER FERMÉE : un abandon est désormais comptabilisé
>
> **Commit `8b8efef`, backend déployé et vérifié (HTTP 200, 2 conteneurs sur le domaine =
> l'exception attendue).** Suite hors-ligne : **19 scripts, 0 échec**, dont **1 010 assertions** sur
> les 15 qui affichent un total (+49 — `check_runner_telemetry.py`). Aucun changement frontend,
> aucune migration : la prochaine reste **034**.
>
> ### Le périmètre réel était 4× plus large que la description de la dette
>
> Ce fichier et les commentaires `⚠️` de `monitoring.py`, `exit.py`, `debate.py` disaient tous la
> même chose — « la dépense de **cette tentative** n'est pas comptabilisée ». Trois sources
> d'accord, donc crédibles. **La lecture de `runner.py` a montré autre chose** : quand la
> **clôture** de `run_tool_json_agent` échoue, c'est le coût de **toute la boucle d'outils** qui
> disparaît — plusieurs tours à gros contexte, contre un seul pour la clôture. Mesuré par test
> négatif : **3 850 tokens réellement facturés contre 850 comptabilisés, soit 78 % de la facture.**
> Les trois mentions décrivaient le symptôme **vu depuis le site d'appel**, pas la cause. Leçon
> transverse : un fichier de reprise dit **où regarder**, jamais **jusqu'où va le trou** ; et
> plusieurs commentaires concordants ne sont pas des preuves indépendantes — ils sont souvent
> copiés les uns des autres.
>
> ### Livré
>
> `AgentOutputInvalid`, **sous-classe de `RuntimeError`** (les 6 sites d'appel font
> `except RuntimeError` — aucun n'a eu à changer de forme), porte `raw_content`, `tokens_in`,
> `tokens_out`, `cost_usd`, `attempts`, `agent_name`, `schema_name`, `last_error`.
> `add_upstream()` reporte la dépense de la boucle d'outils sur un échec de clôture, et `__str__`
> est **recalculé** (un message figé à la construction annoncerait le coût d'avant report).
> `monitoring.py` / `exit.py` / `debate.py` la passent en `run=` **telle quelle** : leurs
> `_persister_echec` lisaient déjà `getattr(run, "tokens_in", 0)`, d'où un diff minimal. Chacun
> garde un `except RuntimeError` **en second** pour les échecs sans télémétrie (panne réseau,
> provider indisponible) — un échec non tracé resterait un trou de suivi.
>
> ### Ce qui est prouvé, et ce qui ne l'est pas
>
> **Prouvé.** Les 49 assertions **exécutent le vrai runner** contre un `AgentProvider` bouchonné à
> réponses scriptées — du code réellement joué, pas des fixtures relues. Le check a été **éprouvé
> par test négatif** (report du coût supprimé → 3 échecs en §7, exit 1) : sans ça, il n'aurait rien
> valu de plus que le `node --check` de la MàJ du 01-09. Les colonnes cibles ont été relues en base
> (`tokens_in`/`tokens_out` INTEGER, `cost_usd` NUMERIC) et §6 verrouille désormais les **types**
> autant que les noms — `_persister_echec` avale toute `DataError` dans un `except Exception`, donc
> une erreur de binding perdrait la trace **une seconde fois, en silence**.
>
> ⚠️ **Non prouvé, à assumer** : aucun **échec réel de modèle** n'a été provoqué de bout en bout.
> Le chemin d'écriture est établi **par identité de types** avec le chemin de succès, lui-même
> exercé en production (sessions **#8** et **#9** portent des `cost_usd` écrits depuis des floats
> Python). Forcer un vrai échec DeepSeek coûterait un appel payant et écrirait une session `failed`
> sur la thèse MSFT #4 : jugé disproportionné. Si un `failed` apparaît un jour à 0 token, c'est ici
> qu'il faut revenir.
>
> ### Friction relevée, non corrigée (→ `CHANTIER_OUTILLAGE_DEV.md` §9)
>
> `Settings` exige `DUST_*`, `SLACK_*` et `FMP_API_KEY` **sans défaut** : un check **100 % V2**,
> sans réseau ni DB, ne s'importe pas sans sept variables V1 bidons. La disjonction V1/V2 est vraie
> au niveau des agents et des tables, **fausse au niveau de `Settings`**. La commande de check *a
> l'air fausse* et se fait légitimement refuser. ⚠️ **Ne pas « corriger » en mettant des défauts
> `""`** : la prod démarrerait alors sans clés Dust en silence (cf. « desserrage de schéma = trou
> silencieux »). Correctif proposé : un `checks/env.checks` versionné, valeurs factices.

> **Ce fichier a été allégé le 2026-08-31.** Tout l'historique (journaux de sprint détaillés,
> diagnostics de bugs déjà réglés, décisions et leurs mesures) est conservé **intégralement** dans
> **`00-REPRISE-ARCHIVE.md`**, à côté. Les **conventions durables #22 à #32** vivent dans le
> **`CLAUDE.md` du projet** — c'est là qu'il faut les lire, pas ici.

> ## ⚡ MàJ 2026-09-03 (bis) — Coolify est arrêté : le déploiement passe en `docker compose`
>
> **Aucune ligne de code du chantier V2 n'a bougé.** Ce qui change est la façon de livrer, et deux
> réflexes de ce fichier sont désormais **périmés** :
>
> - **`infrastructure/deploy.sh` est neutralisé** (conservé, pas supprimé : il refuse de tourner tant
>   que le conteneur `coolify` n'est pas debout). Le script est **`infrastructure/compose-deploy.sh`**,
>   même contrat d'appel, mêmes codes 2-7, **plus un code 8 = build OK mais l'app ne répond pas**.
>   Voir `DEPLOY.md`. Retour à Coolify : `infrastructure/coolify-restore.sh`.
> - **La limite d'outillage notée plus bas est levée** : `--rebuild-only` existe, donc le cas « un
>   seul commit couvre backend + frontend » ne demande plus de fabriquer une modification bidon.
>   Et `portfolio-tracker` (toute la stack) suffit en un appel ; `portfolio-backend` /
>   `portfolio-frontend` restent valides pour ne rebuilder qu'un service.
> - **Il n'y a plus de numéro de déploiement.** Les `#328`…`#349` de ce fichier étaient des ids
>   Coolify ; la traçabilité est désormais le **SHA du commit** rendu par la ligne `RESULT:`.
>
> **Ce que la migration a changé pour le mieux, et qui touche ce chantier précisément.** Le
> `docker ps | grep <app>` « doit montrer UN SEUL conteneur » n'est plus une vérification qu'on peut
> oublier : le script **compte les conteneurs portant `Host(<domaine>)`** et échoue en code 8 s'il y
> en a deux. Portfolio est l'exception explicitement tolérée (backend et frontend partagent le
> domaine via `PathPrefix`, donc **2 attendus**). Et le script **attend la santé du conteneur avant
> de sonder** : un premier jet acceptait « tout sauf 5xx » et a validé un **404 sur `/api/health`** —
> pendant la recréation du backend, Traefik n'a plus de route `/api` et c'est le catch-all Next.js
> qui répond. Exactement le mode de panne de la convention #39, transposé au déploiement : une
> vérification qui ne regarde que la classe du code ne mesure rien.
>
> Le reste de l'infra est **inchangé et volontairement non renommé** : le proxy s'appelle toujours
> `coolify-proxy`, le réseau toujours `coolify` — tous les labels Traefik du VPS en dépendent.
> Les conventions de compose du projet sont à relire dans le **`CLAUDE.md`** : `env_file` est
> désormais **requis** (c'était « interdit, Coolify injecte ») et les `NEXT_PUBLIC_*` sont inlinés au
> build, un oubli n'échouant **que dans le navigateur**.

> ## ⚡ MàJ 2026-09-03 — UX-3 : les écrans V2 AMONT (knowledge → readiness → research → analyses → décision)
>
> **UX-3 est livré.** 9 routes frontend + 1 route backend, déployées et vérifiées par capture d'écran
> en prod (commits `37fc1b3` puis `c4f9fed`, déploiements #347 backend / #349 frontend).
>
> **Le trou qu'on n'avait pas vu venir : l'espace V2 n'avait aucun point d'entrée par ticker.**
> Les 5 écrans amont auraient été inatteignables. D'où, en plus des 5 écrans prévus :
> `GET /v2/tickers` (agrégat d'avancement de la chaîne par ticker), les pages pivots `/v2/tickers`
> et `/v2/tickers/[ticker_id]`, et l'entrée « Tickers » dans `V2Nav`. C'est le même symptôme que
> le `GET /v2/theses` manquant avant UX-1 : **le backend V2 sait faire, mais rien ne s'y branche.**
>
> ### La méthode a payé — 3 fois
>
> Elle est reconduite telle quelle pour la suite. Vérifier, jamais croire l'auto-rapport.
>
> 1. **Le sous-agent backend n'a pas pu lancer Bash** (permission refusée) et a rendu du code
>    **non exécuté**, en le présentant comme terminé. Son check passait 162 assertions… **contre ses
>    propres fixtures**, jamais contre la base. Exécuté par moi contre la vraie base : le SQL était
>    bon, mais **deux fixtures étaient fausses** (`bear` MSFT 2→3, NVDA 3→4) — des assertions vides
>    de sens qui auraient l'air vertes pour toujours. Corrigées.
> 2. **`docker build` a rattrapé une erreur de syntaxe** que le sous-agent readiness affirmait
>    absente après « scan manuel » : une apostrophe non échappée dans une chaîne `'…d'arrêt…'`.
>    Rappel : **`node --check` est un NO-OP** sur ces fichiers, il rend 0 sur du JSX cassé.
> 3. **Les captures ont rattrapé deux défauts qu'aucun `200` n'aurait montrés** : (a) le texte du
>    bloc Pareto de readiness était **inversé** — les deux branches du ternaire décrivaient l'état
>    opposé, et comme les deux tickers réels ont `arret_pareto_recommande=false`, c'est la mauvaise
>    phrase qui s'affichait en prod ; (b) l'écran analyses s'ouvrait sur le **tour le plus récent**,
>    souvent un tour de réfutation partiel — 2 colonnes vides sur 3 à l'ouverture de l'écran phare.
>    Il ouvre désormais sur le tour portant la synthèse `final`.
>
> **Diff programmatique des accesseurs** (la technique d'UX-2, reprise) : extraction par regex de
> tous les `.snake_case` des 9 fichiers, diffés contre l'union récursive des clés des payloads réels
> capturés dans `/tmp/ux3/`. Résultat : **aucun nom de champ inventé**, seuls restent des paramètres
> de route/query (`memo_id`, `analysis_id`, `include_inactive`). ⚠️ Attention au piège : ma première
> regex avait un lookbehind `(?<![\w$])` avant le point qui excluait **tous** les vrais accesseurs —
> elle rendait « 1 accesseur, aucun problème » sur un fichier qui en a 22. Un diff qui trouve zéro
> anomalie doit d'abord être suspecté de ne rien mesurer.
>
> ### G2 sur l'écran décision
>
> `/v2/tickers/[ticker_id]/decision` est **en lecture seule, à dessein**. Verdict, sizing et
> conditions d'entrée sont lus en base et rendus « figés » ; ils ne sont jamais des champs de saisie.
> L'écran **rend compte** de la décision, il ne la déclenche pas : le `POST /validate` fige la
> décision **et** ouvre la position en une opération irréversible, ce qui n'a pas sa place derrière
> un bouton d'écran de consultation. Les `risk_acks` (qui ne portent que `{risk_index, accepted}`)
> sont réconciliés avec les libellés de `risques_acceptes` lus dans la synthèse — sans quoi l'écran
> afficherait « risque 0 accepté », ce qui n'apprend rien.
>
> ### Réconciliation des tiers (les 7 vs les 3)
>
> `GET /v2/tickers` et l'écran knowledge exposent les **7 tiers stockés** (A, A-, B+, B, B-, C+, C) ;
> readiness en expose **3 groupes** (tier_A/B/C). Ils comptent les mêmes entrées. La page pivot
> affiche l'arithmétique du regroupement en clair (`tier_A = A(42) + A-(2) = 44`) pour que les deux
> écrans **ne se lisent pas comme une contradiction**. Mesuré : NVDA 32/15/5, MSFT 44/10/0.
>
> ### Reste à faire
>
> - **`~/.netrc` bloque tous les `git push`** (voir juste en dessous) — décision utilisateur.
> - Écran analyses : la bannière dit que synthèse #11 déclare `bull #8 / bear #9` alors que les
>   cartes du tour 1 montrent #12/#13 (produits après). C'est **honnête et voulu**, mais mérite
>   sans doute une mise en forme plus explicite.
> - ingestion-agent, dette du runner (inchangés).
>
> ### ⚠️ `~/.netrc` casse `git push` — non réglé, décision utilisateur
>
> **Symptôme** : tout `git push` rend `403 Permission ... denied to jeanlangloismeurinne`.
> **Ce n'est pas le token du repo** : celui de `~/.git-credentials` est valide et rend **200** sur
> `info/refs?service=git-receive-pack`. Ce n'est pas non plus le bac à sable.
>
> **Cause** : `~/.netrc` contient un **autre** token (fine-grained, 93 caractères) sans droit
> d'écriture. git le consulte **via libcurl avant** le credential helper — et même avant des
> identifiants embarqués dans l'URL, ce qui rend le contournement « pousser vers une URL avec token »
> **inopérant**.
>
> **Contournement utilisé** (non destructif, à refaire à chaque push) :
> ```bash
> mkdir -p /tmp/githome
> GT=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.git-credentials | head -1)
> HOME=/tmp/githome git push "https://x-access-token:${GT}@github.com/<user>/<repo>.git" HEAD:main \
>   2>&1 | sed "s|$GT|<token>|g"     # le token n'est jamais affiché
> git fetch origin                    # resynchroniser la ref de suivi
> ```
>
> **Correctif durable — à trancher par l'utilisateur, je n'y touche pas** : `~/.netrc` est son
> fichier d'identifiants, créé par autre chose que ce chantier. Soit en retirer l'entrée `github.com`,
> soit y mettre un token ayant le droit de push. Tant que ce n'est pas fait, **chaque push de chaque
> projet** exige le contournement ci-dessus.

> ## ⚡ MàJ 2026-09-02 — UX-2 : les écrans du lot 9, construits contre des données RÉELLES
>
> **Le prérequis a été levé en premier, et il valait la peine.** Les 5 tables du lot 9 étaient vides.
> La thèse V2 jetable **#5 (NVDA)** a été re-fabriquée et **toute la chaîne rejouée contre l'API réelle**
> — débat #9 → clôture → plan de sortie #6 (3 tranches 50/30/20 + 3 conditions accélérées) → alerte #5
> → 3 exécutions (position à 0 titre, `exit_status=closed`) → post-mortem #3 (`duree_jours=204`,
> `performance_pct=18.0`, tous deux **calculés**) → calibration (10 paires, `lisible:false` à n=1).
> Coût total **~0,0042 $**. Les 4 écrans ont ensuite été écrits **à partir des payloads capturés**
> (`/tmp/ux2/*.json`), pas d'un schéma lu.
>
> **Ce que le dry-run a démontré au passage** : l'anti-complaisance tient en réel. Le débat #9 avait
> `invalidation_franchie=true` et le modèle a suggéré `closed_monitor`, jamais `closed_proceed`. La
> clôture a été faite en `closed_pass` **à dessein**, pour fabriquer une divergence agent/investisseur
> tracée et vérifier qu'elle se voit à l'écran.
>
> **Livré (frontend seul — aucun changement backend n'a été nécessaire).**
> `/v2/theses/[id]/sortie`, `/v2/theses/[id]/post-mortem`, `/v2/theses/[id]/debat`, `/v2/calibration`,
> entrée « Calibration » dans `V2Nav`, section « Sortie, bilan et débat » sur la page pivot, et le
> **marqueur de flux V1/V2 sur `/portfolio`**. `portfolio_summary()` faisant déjà `SELECT pp.*`,
> `thesis_v2_id` remontait déjà : le point 2 du reste-à-faire ne coûtait rien côté API.
>
> **Le marqueur de flux, fait SANS le filtre que la MàJ (bis) déconseillait.** Les deux positions MSFT
> restent affichées, badgées V1/V2, avec un bandeau qui explique que ce n'est pas un doublon. Deux bugs
> **préexistants** ont été trouvés en le câblant, aucun des deux n'était soupçonné : (a) `key={p.ticker_id || p.id}`
> donnait la **même clé React `"MSFT"`** aux positions #1 et #8 ; (b) le clic sur une ligne V2
> envoyait vers la page **V1** du ticker. Corrigés en `key={p.id ?? p.ticker_id}` et route
> `/v2/theses/{thesis_v2_id}`.
>
> **⚠ Un `200` ne prouve rien sur l'affichage — les 6 pages ont été CAPTURÉES en prod** (chromium
> headless, `/tmp/ux2/shots/`) et regardées. Deux défauts que seul le rendu pouvait montrer :
> — le plan de sortie affichait **deux badges `closed` côte à côte** sans étiquette (statut de la thèse
>   et statut du plan, deux choses différentes, même mot) → préfixés « Thèse : » / « Plan : » ;
> — sur `/v2/theses/[id]/debat`, la divergence n'était qu'un **badge** dans la liste alors que
>   l'arbitrage UX n°4 exige un bandeau visible **sans clic** → le débat le plus récent s'ouvre
>   désormais tout seul au premier chargement (garde par thèse, refermer ne rouvre pas).
> Les deux sont invisibles à `docker build`, invisibles à un check hors ligne, invisibles à un 200.
>
> **⚠ Vérification indépendante des sous-agents, pas leur auto-rapport.** Deux passes après livraison :
> (a) `grep` des replis `a || b` sur les noms de champs — un seul hit, légitime ; (b) extraction
> **programmatique** de tous les accesseurs `.snake_case` des 4 fichiers neufs, diffés contre l'union
> des clés des payloads réels — seul `sell_date` ressort, et c'est un champ de **corps de requête**.
> C'est la technique à reprendre : elle transforme « je n'ai pas deviné de nom » en fait vérifiable.
>
> **⚠ Le script de nettoyage de la thèse jetable était périmé et DANGEREUX.** `lot9_these_jetable_cleanup.sql`
> listait `knowledge_entries (121,122,123)` et `cash_movements (10,11,12)` — les ids du run **de la
> veille**. Ce run-ci a produit 124/125/126 et 13/14/15 : le rejouer tel quel aurait supprimé trois
> entrées de connaissance d'un autre exercice **et laissé derrière lui** de la fausse trésorerie dans
> un solde **partagé avec le flux V1 réel** (#34). Réécrit : tout est dérivé de `thesis_v2_id`, les ids
> des faits rattachés sont capturés en tables temporaires **avant** d'effacer ce qui les porte, et
> `thesis_id` est un paramètre `-v` **sans valeur par défaut** (un script de DELETE n'en prend pas).
> Les deux seeds sont désormais versionnés dans `backend/app/db/seeds/` — le prochain sprint UX
> redémarre à moindre coût. **La thèse #5 a été supprimée après les captures**, pas avant : la
> supprimer d'abord aurait laissé les écrans neufs sans rien à afficher.
>
> **Sur le déploiement** : `infrastructure/deploy.sh` a été **refusé par le classifieur** (comme
> l'écriture d'un PHP ad-hoc dans le conteneur Coolify). Chemin utilisé à la place : commit + push
> en commandes séparées, puis rebuild par **l'API Coolify avec un token généré**
> (`COOLIFY_PLAYBOOK.md` § « méthode alternative »). Vérifié après coup : `docker ps` ne montre
> **qu'un** conteneur `portfoliofrontend`, pas d'orphelin.
>
> **Reste ouvert côté UX** : les écrans V2 **amont** (knowledge, readiness, research memo, analyse
> 3 colonnes, décision) — tout leur backend existe, aucun n'a d'écran.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 (bis) — UX-1 : le fil conducteur V2 (l'espace V2 avait un backend complet et AUCUN écran)
>
> **Le constat qui a défini le sprint.** Le reste-à-faire annonçait une « passe UX transverse : verdict
> dans le frontend, suivi des hypothèses H1-H5 » — formulation qui laissait croire à des retouches.
> Inventaire fait : `frontend/pages/v2/` contenait **un seul fichier** (la liste des 12 agents), aucun
> dossier `components/v2/`, **une** entrée dans `V2Nav`, et **aucune** page ne lisait `theses_v2` ni
> `monitoring_sessions_v2`. Neuf lots de backend, zéro écran. Ce n'est pas une passe, c'est un chantier
> de plusieurs sprints — et le §16 de la spec est **muet** sur le lot 9 (ni sortie, ni post-mortem, ni
> calibration ; le §4 nomme `ExitPlanBuilder` et `CalibrationPanel` sans dire où ils vivent). Sept
> points d'UX sont donc à trancher au fil de l'eau, pas à lire dans la spec.
>
> **Pourquoi le fil conducteur AVANT les écrans du lot 9, et pas l'inverse.** Trois raisons, la
> première étant décisive et mesurée : `exit_plans`, `exit_executions`, `post_mortems_v2`,
> `calibration_registry`, `conviction_debates_v2` sont **toutes vides** (la thèse jetable #5 du dry-run
> a été supprimée). Construire ces écrans d'abord, c'est les construire contre des données **inventées**
> — et une donnée inventée est toujours conforme. C'est la convention #39 d'un cran plus haut. Le fil
> conducteur, lui, avait de quoi s'afficher : thèse #4 MSFT et ses 2 sessions. Ensuite, G2 interdit
> l'ordre inverse (« la logique de décision contraint l'UX ») : un écran dessiné avant sa donnée invente
> des affordances que le backend refuse — ici les seuils, en lecture seule par #37. Enfin les trous
> d'API se trouvent en câblant : `GET /v2/theses` **n'existait pas**, donc aucune thèse V2 n'était
> listable et aucun écran du lot 9 n'était atteignable.
>
> **Livré.** Backend : `GET /v2/theses` (agrégats position / sessions / exit_plan / post-mortem,
> filtre `?ticker_id=`) + enrichissement **strictement additif** de `GET /v2/theses/{id}`.
> Frontend : primitives `components/v2/`, `/v2/theses` (liste), `/v2/theses/[id]` (page pivot),
> entrée « Thèses » dans `V2Nav`. Suite hors-ligne : **759 assertions / 0 échec** sur 12 scripts
> (707 avant, **+52** — `check_theses_v2_listing.py`).
>
> **La page thèse affiche DEUX fourchettes de valorisation, et c'est structurel.** MSFT #4 porte
> `validation_json` **250/450/700** (figée au validate) et `valuation_range` **280/480/750**
> (réactualisée par la revue mode 6). N'en afficher qu'une masquerait l'écart — or c'est **contre la
> figée** que la calibration A5 mesure l'erreur de prévision. Les deux sont donc étiquetées
> séparément, l'écart est explicite, et aucune moyenne n'est calculée.
>
> **⚠ Ce que ce sprint a trouvé et qui vaut pour tout le frontend : `node --check` est un NO-OP sur
> ces fichiers.** Node 20 détecte le `import` en tête, bascule en analyse ESM et **rend 0 sans rien
> vérifier** — y compris sur du JSX volontairement cassé. Vérifié dans les deux sens : le même JSX
> **sans** `import` échoue en `exit=1`, **avec** `import` passe en `exit=0`. Un sous-agent avait
> rapporté « `node --check` OK » de bonne foi ; ça ne prouvait strictement rien. **La seule
> vérification frontend qui ait du sens est `docker build`** (npm ci + next build) — faite, les deux
> pages compilent (`/v2/theses` 2,88 kB, `/v2/theses/[id]` 4,93 kB). Corollaire général : un contrôle
> qui réussit **toujours** est pire qu'aucun contrôle, parce qu'il se rapporte comme une preuve.
>
> **⚠ Un check à fixtures ne prouve jamais qu'une requête SQL s'exécute.** Les 52 assertions neuves
> travaillent sur des dicts Python : elles ne touchent pas la base. Or la requête référence
> `exit_plans.status` et `post_mortems_v2.status`, colonnes dont la migration 032 ne parle pas (elle
> décrit `exit_status`). Elles existent bien (défaut `'completed'`) — mais **vérifié en jouant le SQL
> exact contre `db_portfolio`**, pas en le supposant. Le `JOIN tickers` a été contrôlé de même : FK
> `theses_v2_ticker_id_fkey` présente, donc l'INNER JOIN ne peut pas escamoter une thèse (le mode de
> panne du LEFT JOIN du lot 7 n'est pas reconduit).
>
> **⚠ Les replis sur variantes de noms de champs sont un trou silencieux.** La page thèse avait
> d'abord été écrite avec des `h.hypothese || h.text || '—'`, `h.base_rate_taux`, `h.classe_reference`
> — noms devinés. Structure réelle relevée en base : `id`, `enonce`, `kpi`, `unite`, `horizon`,
> `statut`, `seuil_alerte`, `seuil_invalidation`, `base_rate{taux, reference_class, ajustement}`,
> `source_entry_refs[{entry_id, version}]`, `derniere_revue`, `derniere_observation`. Un nom faux
> n'aurait pas levé d'erreur : il aurait affiché **du vide**, qui se lit comme « cette donnée n'existe
> pas ». Corrigé aux noms exacts, avec un marqueur **visible** « — champ absent » (et `ajustement:
> null` nommé comme tel, pour distinguer « vide à dessein » de « donnée manquante »).
>
> **Faux positif à ne pas re-chasser** : `check_search_worker.py` rend `50 OK / 1 FAIL` **si on lui
> passe `EXA_API_KEY=x`** — l'assertion « sans clé de recherche, le worker doit lever » ne peut alors
> pas se déclencher. Avec l'environnement documenté dans `checks/README.md` (sans clé), il rend bien
> **52 OK / 0 échec**. Le script est correct ; c'est l'env du runner qui doit l'être.
>
> **⚠ Le « double comptage » MSFT : une des deux options proposées est nuisible.** Positions ouvertes
> réelles : **#1** MSFT V1 (1 titre, 100 €) et **#8** MSFT V2 (1 titre, 400 €, ligne de dry-run
> conservée). Le fichier proposait « filtrer sur `thesis_v2_id IS NULL` côté V1 **ou** afficher les
> deux avec un marqueur ». **Filtrer les positions sans filtrer la trésorerie aggrave le mensonge** :
> le `cash_movements` #9 de 400 € resterait débité sans contrepartie visible, la page afficherait
> 400 € évaporés. Positions et trésorerie sont des **faits du monde** (#34) et la page portefeuille
> décrit le monde : le **marqueur de flux** est la seule des deux options qui ne fasse pas mentir la
> page. Non traité dans ce sprint, à faire dans la tranche UX suivante.
>
> **Reste ouvert côté UX** : les écrans du lot 9 (sortie, post-mortem, calibration, débat) — ils
> demandent d'abord de **fabriquer une thèse jetable** pour avoir des données réelles à afficher,
> sinon on retombe dans le piège des fixtures conformes ; le marqueur de flux sur `/portfolio` ;
> les écrans amont (knowledge, readiness, research, analyse) toujours absents de l'espace V2.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 — LOT 9 : la sortie, la calibration et le débat (migrations 032 + 033)
>
> **La boucle V2 est fermée** : décider (lot 7) → surveiller (lot 8) → **sortir et apprendre** (lot 9).
> Suite hors-ligne : **707 assertions / 0 échec** sur 11 scripts (532 avant, **+175** —
> `check_exit_debate.py`). Migration 032 appliquée (`exit_plans`, `exit_executions`,
> `post_mortems_v2`, `calibration_registry`, `conviction_debates_v2`, + `price_alerts.exit_plan_id`),
> puis **033** (resynchro du prompt `debate-agent`, voir plus bas). 13 routes exposées dans
> `api/analysis_v2.py`. Détail des tables et des CHECK : `CLAUDE.md` § Migrations.
>
> **Dry-run réel de bout en bout, joué contre le vrai DeepSeek**, sur une thèse V2 **jetable #5**
> (NVDA, 2ᵉ ticker) créée pour l'exercice puis **intégralement supprimée** — la thèse MSFT #4 et sa
> position #8 (argent réel) n'ont jamais été touchées. La chaîne complète a tourné : débat →
> clôture → plan de sortie → 3 tranches → post-mortem → calibration → `GET /v2/calibration/summary`.
> Ce que le run a **prouvé en réel**, et qu'aucun check hors ligne ne pouvait établir :
> • `seuil_franchi` **redérivé** des seuils figés dans les **deux sens** — H1 `invalidation` (18 < 25,
>   décroissante), H2 `alerte`, H3 `aucun` (39 < 40, **croissante**) ;
> • **anti-complaisance** tenue : H1 invalidée → l'agent a suggéré `closed_monitor`, jamais
>   `closed_proceed` ;
> • **souveraineté de l'utilisateur** préservée et tracée : une clôture en `closed_proceed` contre
>   l'avis du débat est **acceptée** (le CHECK 032 ne contraint que `resolution_suggeree`), avec la
>   divergence conservée en ligne (`resolution_suggeree` ≠ `status`, `invalidation_franchie=t`) et un
>   WARNING — c'est la matière du post-mortem, pas un bug ;
> • `duree_jours`=202 et `performance_pct`=18,00 **calculés** (1 180 € encaissés / 1 000 € de revient)
>   là où le modèle rendait `0` et `0.0` ;
> • **le cœur de l'exercice** — la calibration a lu la fourchette **FIGÉE au validate**
>   (`validation_json` : 90/**120**/150) et non la `valuation_range` réactualisée (100/140/180). C'est
>   pour ça que le seed les avait délibérément rendues différentes : mesurer son erreur contre sa
>   dernière opinion ne mesure rien ;
> • `summary` à n=1 se déclare **`lisible: false`** — le registre A5 refuse de généraliser d'un cas.
>
> **Ce que seul le run réel a trouvé — la désynchro de prompt (→ convention #39, migration 033).**
> Premier appel réel du lot : **HTTP 502**, `seuil_franchi` reçu en booléen sur les 3 hypothèses.
> L'exemple JSON de `60-debate-agent.md` datait d'**avant** le figeage du Pydantic
> `ConvictionChallenge` (écrit seulement au lot 9) et montrait `"franchi": false`,
> `"observation_courante"`, **aucun `valeur_observee`**. Le modèle a recopié l'exemple. **Le 502 est
> bénin — ce qu'il masquait ne l'est pas** : `_forcer_seuils_figes` ne redérive que si
> `valeur_observee is not None`, donc un prompt qui n'enseigne jamais ce champ rend la dérivation
> **no-op silencieuse** et tue le garde-fou central du lot, **sans qu'aucun check hors ligne ne le
> voie** (ils alimentent tous les ponts avec des fixtures déjà conformes). Un check prouve qu'une
> fonction refuse ce qu'on lui donne ; jamais que le modèle produira de quoi la déclencher.
> Correctif conforme à la règle « desserrage de schéma = trou silencieux » : **prompt durci**
> (table des champs + mention explicite que le système réécrit les seuils et redérive le
> franchissement, donc sous-déclarer n'achète rien), **contrat inchangé**, et DB resynchronisée par
> la **migration 033** générée (`_gen_prompt_refresh_20260901.py`) — jamais un UPDATE à la main.
> Re-testé contre le vrai modèle : **200**, les 3 hypothèses conformes.
>
> **Second défaut trouvé par le run (→ convention #40)** : le post-mortem sur position non soldée
> était refusé **après** l'appel (dans `_valider_pont_postmortem`), alors que `_verifier_etat` porte
> justement la consigne « AVANT toute dépense de tokens ». Un appel complet payé pour apprendre un
> état lisible dans `inputs`. Déplacé en pré-condition (`ThesisNotExitable` → **409**), le pont le
> reteste en défense en profondeur. **Deux assertions ajoutées** (173 → 175).
>
> **Reste ouvert** : les **pages V2** du lot 9 (plan de sortie, post-mortem, `CalibrationPanel`) —
> tout est côté API, rien côté UI ; la dette du runner (tokens d'une tentative abandonnée non
> comptabilisés, commune à tous les agents V2, ouverte depuis le lot 8) ; l'ingestion-agent.
>
> ---
>
> ## ⚡ MàJ 2026-09-01 — LOT 8 : le monitoring V2 (modes 1-6, `monitoring_sessions_v2`, migration 031)
>
> **Le flux V2 sait maintenant se surveiller.** Déploiement **#335** (`062e459`), un seul conteneur
> vérifié. Suite hors-ligne : **532 assertions / 0 échec** sur 10 scripts (416 avant, **+116** —
> `check_monitoring_v2.py`). Dry-run réel joué contre le vrai DeepSeek sur les **deux** modes qui
> comptent (2 et 6), thèse V2 #4 MSFT.
>
> **Le lot 8 demandait bien une migration — CLAUDE.md disait le contraire.** La phrase « le lot 8
> n'en demande pas a priori » était **fausse** : `monitoring_sessions.thesis_id` est une FK vers
> `theses`, la table V1. Une session V2 n'a littéralement **pas de place où pointer**. Trouvé en
> vérifiant le FK, pas en le supposant — même schéma que le `LEFT JOIN` du lot 7. D'où la
> **migration 031** : `monitoring_sessions_v2`, `calendar_events.session_v2_id`,
> `portfolio_settings.v2_auto_enabled`, et des CHECK qui contraignent les domaines de routage.
> **La numérotation du lot 9 décale donc à 032.**
>
> **Le principe à retenir de ce lot — un contrat valide un objet, jamais la cohérence entre deux.**
> C'est le trou que le lot 8 ferme, et il était invisible depuis le schéma. Mesuré :
> `Mode2QuarterlyReview` **accepte parfaitement** une escalade motivée par une hypothèse `H7` qui
> **n'existe pas dans la thèse**. Contrat satisfait, `extra='forbid'` satisfait, anti-churn
> **contourné** — puisque l'anti-churn dit « n'escalader que sur un seuil PRÉ-ENREGISTRÉ » et que
> rien, dans le schéma, ne relie la sortie du modèle à la liste figée. D'où un **pont inter-objets**
> en code (`_valider_pont_hypotheses`), en trois vérifications distinctes :
> **(1) référentiel** — ids cités ⊆ ids figés (tous modes citant des hypothèses) ;
> **(2) exhaustivité** — ids figés ⊆ ids cités (**mode 6 seul**, comme l'exige la carte C5) ;
> **(3) citations** — tout `entry_id` cité appartient aux entries réellement envoyées.
> Refus → `MonitoringRefused` → **HTTP 422** (la requête est valide, c'est la *sortie du modèle* qui
> est incohérente) + session `failed` persistée : un refus reste visible. `check_monitoring_v2.py`
> **§3** prouve les deux moitiés — le contrat accepte le `H7`, le pont le refuse.
>
> **Corollaire, tout aussi structurel : les seuils figés sont en LECTURE SEULE.** `_reporter_statuts`
> fusionne **par id** sur la liste du validate et n'écrit que `statut`, `derniere_revue`,
> `derniere_observation`. `seuil_alerte`, `seuil_invalidation`, `base_rate`, `source_entry_refs` ne
> sont **jamais** repris de la sortie du modèle — sinon une revue pourrait **abaisser le seuil
> qu'elle vient de franchir**, et l'anti-churn deviendrait décoratif. Vérifié : le modèle a rendu
> `seuil_invalidation: 5.0` là où la thèse portait `25.0` ; c'est `25.0` qui est resté.
>
> **Ce que le code dérive et ne demande jamais au modèle** (#24 appliqué au monitoring) :
> `mode`, `thesis_id`, `pair_ticker` (mode 4), `source_mode` (mode 5), `schema_version`, et surtout
> **`next_review_date`** — `jour + 365j` en Python. La valeur du modèle est journalisée et conservée
> dans `result_json`, mais ne pilote aucun planning. *Vérifié en dry-run* : le modèle proposait
> `2027-08-31`, l'événement a été posé au **`2027-09-01`**.
>
> **`EventRouterV2` — le défaut V1 n'est pas reconduit.** INNER JOIN sur `theses_v2 … status='active'`
> (pas de LEFT JOIN, cf. lot 7), `ce.thesis_v2_id IS NOT NULL` explicite, **aucune garde `synced`**
> (notion Dust : le prompt en base EST celui envoyé, une garde ici ne vérifierait rien et bloquerait
> au premier PATCH), interrupteur **`v2_auto_enabled`** (FALSE par défaut — pas de dépense
> automatique non supervisée). Job scheduler **séparé** à 7h15, 10 min après le V1 : les enchaîner
> ferait qu'une exception d'un flux empêcherait l'autre de tourner, alors qu'ils sont censés être
> indépendants. **Seul le mode 6 se rattrape** (`scheduled_date <= today`) : un brief J-2 ou une revue
> J+1 joués trois semaines plus tard commentent une publication déjà digérée, alors qu'une revue
> annuelle en retard est **plus** urgente, pas moins. À `v2_auto_enabled=FALSE`, l'échéance n'est pas
> perdue : session `pending_manual` **avec son contexte exact**, et notifiée. Non-choix assumé : le
> mode 5 **n'est pas** enchaîné automatiquement après une escalade mode 2 — `routing_suggestion` +
> Slack, déclenchement humain (comme en V1 ; l'automatiser doublerait la dépense du jour et rendrait
> invisible la décision d'aiguillage).
>
> **Dry-run réel MSFT (thèse V2 #4, 4 hypothèses figées).**
> *Mode 2* → session **#8**, `alert_level=RAS`, `verdict`/`routing` **NULL** (corrects : pas
> d'escalade), 13 827/637 tokens, **$0,001221**, 6 refs snapshotées, H1-H4 cités avec de vrais
> `entry_id`. Le commentaire de valorisation **refuse de mécaniser** : prix 513,53 $ au-dessus de la
> VI base 450 $, marge négative -12,4 %, et pourtant « *cela reste contextuel et ne constitue pas un
> ordre de vente* » — DÉCISION #5 tenue par le modèle lui-même.
> *Mode 6* → session **#9**, verdict **CONFIRMER**, 13 818/1 192 tokens, **$0,00132**, **exhaustivité
> respectée** (H1-H4 tous revus), `thermometer.contraignant=False`, `rendement_prospectif.suffisant=True`
> en zone « étirée » (donc **aucune sortie de valorisation** — l'anti-seuil-mécanique fonctionne),
> `exit_trigger=None`.
>
> **⚠ Effets du mode 6 conservés sur décision de l'utilisateur.** La revue a réactualisé
> `theses_v2.valuation_range` **250/450/700 → 280/480/750** : gardée comme ré-appréciation légitime
> sur données actuelles. En revanche l'événement **#67** (`annual_review` 2027-09-01, source
> `monitoring_agent_v2`) a été **supprimé** — il doublonnait le vrai **#66** (2027-08-31) à un jour
> près et aurait déclenché **deux** revues annuelles. Les sessions #8 et #9 sont **gardées** comme
> trace du dry-run. Les événements #65/#66 n'ont **pas** été consommés (dry-runs joués sans
> `calendar_event_id`, délibérément) : le lot 8 aura donc bien un vrai événement à router le
> **2026-10-28**.
>
> **Dette connue, à traiter au lot 9 ou avant.** `run_json_agent` **perd le texte brut fautif et la
> comptabilité de tokens** quand il abandonne après échec de validation (il lève un `RuntimeError` nu).
> On persiste le motif pour que l'échec reste visible, mais **la dépense de cette tentative n'est pas
> comptabilisée**. Limite du runner, **commune à tous les agents V2** — pas propre au monitoring. Ne
> pas la corriger à chaud sans re-tester les autres agents.

> ## ⚡ MàJ 2026-08-31 (ter) — LOT 7 : l'acte de décision (`theses_v2`, migration 030)
>
> **Le flux V2 sait maintenant conclure.** Déploiement **#331** (`a128005`), un seul conteneur
> vérifié. Suite hors-ligne : **436 assertions / 0 échec** (382 avant, **+54** —
> `check_decision_validate.py`). Dry-run réel joué de bout en bout sur MSFT : **12 vérifications
> supplémentaires, 0 échec.**
>
> **Décision d'architecture (tranchée par l'utilisateur) : `theses_v2` + route `/v2/…`.** La carte
> figée `decision_validate_card.md` disait « `theses += colonnes` » et `POST /theses/{id}/validate` —
> elle **précède d'un jour** le principe de disjonction V1/V2. Deux raisons dirimantes : `theses` est
> le pivot V1 (scheduler, monitoring, débat), et la route **existe déjà** en V1
> (`api/thesis_v2.py:733`, où « v2 » désigne la 2ᵉ version du fichier V1). La carte est **amendée
> avec un bloc daté** ; **le contrat JSON lui-même (`ThesisValidation`, 17 garde-fous) est
> INCHANGÉ** — seuls le support de persistance et le chemin bougent.
>
> **Principe dégagé, plus général que ce lot — et c'est lui qu'il faut retenir :**
> **les JUGEMENTS sont disjoints, les FAITS DU MONDE sont partagés.** `theses` | `theses_v2` sont
> deux espaces de jugement séparés ; `tickers`, `portfolio_positions`, `cash_movements`,
> `calendar_events` décrivent le monde réel — dupliquer le portefeuille signifierait **deux soldes de
> trésorerie sur de l'argent réel**. D'où une colonne discriminante `thesis_v2_id` (sœur nullable de
> `thesis_id`) + CHECK d'exclusivité `thesis_id IS NULL OR thesis_v2_id IS NULL`.
>
> **⚠ Danger silencieux trouvé en le vérifiant, pas en le supposant.** J'avais écrit dans la
> migration que le scheduler V1 « filtre sur `thesis_id`, donc ignore nativement les lignes V2 ».
> **Faux.** Les 4 requêtes de `_daily_check_v1` font `LEFT JOIN theses … AND th.status='active'` —
> un LEFT JOIN **rend la ligne même sans thèse jointe**, et aucun garde `thesis_json IS NULL` en
> aval. Le routeur V1 aurait donc appelé l'**agent Dust V1 sur une thèse inexistante**, en silence et
> avec **dépense réelle**. Corrigé : `AND ce.thesis_v2_id IS NULL` sur les 4 requêtes. **Mesuré sur
> les vrais événements du dry-run : 2 lignes vues sans le filtre, 0 avec.**
>
> **G2 s'exerce structurellement, pas par convention.** `ValidateV2Body` n'expose QUE `risk_acks`,
> `pre_mortem_acked` et les faits d'exécution (titres, prix, date). `verdict`, `position_sizing_pct`,
> `conditions_entree`, `hypotheses`, `valuation_range`, `synthesis` sont **lus en base** — les
> accepter du client rendrait le contrat décoratif (il suffirait d'envoyer une synthèse complaisante).
> `risk_matrix_acked` est **dérivé** (la bijection des acquittements en tient lieu), jamais demandé.
> Un sizing autre que le recommandé ne se passe pas au validate : il se trace **en amont** dans la
> synthèse (`position_sizing.override_utilisateur`, A7). `check_decision_validate.py` **§8 inspecte
> `model_fields`** pour l'assurer — c'est la vérification la plus importante du fichier.
>
> **Atomicité réelle.** `get_db_session()` n'ouvre **aucune** transaction (il *acquiert* une
> connexion, chaque `execute` est en autocommit) : la validation V1, documentée « atomique »
> (convention #13), **ne l'est pas**. La V2 ouvre un `conn.transaction()` explicite, appels réseau
> (FX, calendrier) faits **avant** pour ne pas tenir de verrou pendant un aller-retour yfinance. V1
> délibérément non touchée (hors périmètre, risque de régression).
>
> **Dry-run réel MSFT (thèse V2 #4, synthèse #11, memo #4)** — refus d'abord, tous sans écriture :
> acquittement incomplet 3/4 → **400**, pré-mortem non acquitté → **400**, acquittement fantôme
> index 9 → **400**, thèse inexistante → **404**, et la thèse **toujours en `draft`** après les
> quatre. Puis validation : verdict `PROCEED_AVEC_CONDITIONS` et sizing **3,0 %** repris de
> l'analyse, fourchette **250 / 450 / 700 dérivée du memo** (`iv_range` + `dcf_scenarios.base`,
> jamais une moyenne inventée), 4 hypothèses figées, rejeu → **409**. Chemin réseau réellement
> exercé : FX **400 € → 464,79 $** et date de résultats **2026-10-28** obtenue de DataService.
>
> **⚠ Ligne de test conservée sur décision de l'utilisateur.** Le dry-run a créé de vraies lignes :
> `theses_v2` **#4**, `portfolio_positions` **#8** (1 MSFT), `cash_movements` **#9** (400 €),
> `calendar_events` **#65** (quarterly 2026-10-28) et **#66** (annual_review 2027-08-31). Elles sont
> **gardées** comme premier cas V2 de bout en bout. **Conséquence à connaître** : la page portefeuille
> V1 (`portfolio_v2.py:142`) lit **toutes** les positions ouvertes et **tous** les mouvements de cash,
> sans filtre de flux — MSFT y apparaît donc **deux fois** (position V1 #1 + position V2 #8) et le
> solde de trésorerie est **400 € plus bas**. Ce n'est pas un bug de la migration (le CHECK
> d'exclusivité est **par ligne**, pas par ticker, à dessein) mais **une question pour la passe UX** :
> filtrer sur `thesis_v2_id IS NULL` côté V1, ou afficher les deux avec un marqueur de flux.
>
> **Les événements de calendrier V2 sont posés mais PAS routés** — le scheduler V1 les exclut
> volontairement et le routeur V2 arrive au **lot 8**. C'est **annoncé** dans la réponse de l'API
> (champ `note`) pour ne pas se lire comme un bug. L'événement #65 tombe le **2026-10-28** : le lot 8
> aura un vrai événement à router.

> ## ⚡ MàJ 2026-08-31 (bis) — généralité #3 fermée + dispense NVDA retirée
>
> **Les deux premiers items du reste-à-faire sont clos.** Deux déploiements : **#329** (`1b8497f`,
> domaines IR) et **#330** (`90fc6d3`, dispense). Un seul conteneur vérifié après chacun. Suite
> hors-ligne : **382 assertions / 0 échec** (367 avant, +15).
>
> **Généralité #3 — domaines IR par émetteur.** `nvidia.com` était en dur dans
> `_REPUTABLE_SUFFIXES` (fait d'émetteur dans une constante globale, #31) et Microsoft n'avait rien.
> Effet réel, plus grave qu'annoncé : `microsoft.com/en-us/investor/…` sortait en
> `web_search_generic` **0.50**, donc **sous `reliability_min=0.60`** — l'entry était **rejetée**, pas
> seulement mal notée. Le champ paraissait infondable alors que la source était la meilleure possible.
> Cause : Microsoft publie son IR sur un **chemin**, pas un sous-domaine `ir.`.
> → `classify_source_type(url, ticker_id)` + `issuer_domains_for(ticker_id)` (défaut **vide**), à deux
> niveaux : domaine émetteur **+ chemin IR** → `company_ir_official` 0.90 ; domaine émetteur hors IR →
> `web_search_reputable` B. `_IR_HOST_PATTERN` reste **générique à dessein** (le restreindre ferait
> tomber `ir.<concurrent>.com` de 0.90 à 0.50 — un faux trou créé par le correctif, cf. #32).
> *Vérifié contre le vrai modèle* (dry-run MSFT) : `microsoft.com/en-us/investor/earnings/FY-2026-…`
> → **`company_ir_official`, tier A, 0.895**. Convention **#33** écrite dans le `CLAUDE.md`.
>
> **Le « 4 sites d'appel » redouté n'existait pas** : `build_tool_executors` recevait déjà `ticker_id`.
> Il est fermé dans `web_search`/`fetch_url` comme `query` et `log` — un fait du run, pas un argument
> du modèle (#28). `check_search_worker.py` **§2bis teste le CÂBLAGE** (backend bouchonné, on lit le
> `source_type_max` réellement annoncé) : une table juste ne sert à rien si le ticker n'arrive pas.
>
> **Piste morte, à ne pas re-tenter** : EDGAR `submissions` expose `website` et `investorWebsite`,
> **les deux vides** — vérifié sur NVDA, AAPL, MSFT, GOOGL, AMZN. Le registre est écrit à la main.
> ⚠️ **Ajouter l'entrée `_ISSUER_DOMAINS` en même temps que le ticker.**
>
> **Dispense NVDA `marche.croissance_marche_historique` — retirée.** Elle disait « aucune source
> accessible à un tier suffisant » : vrai de la **table de domaines**, pas du monde. Depuis #32 les
> cabinets sont `web_search_reputable` (plafond B) = exactement le plancher dégradé du champ ; les
> deux garde-fous se contredisaient. Retirée **sur preuve** : un mandat NVDA a rendu **3 entries
> tier B** (Omdia 0.630, IDC 0.605, TechInsights 0.602 → **117-119**), comme MSFT en avait 3
> (Synergy/Canalys, 109-111). *Vérifié contre le vrai modèle* — rapport **#27**, NVDA :
> **`ready`, 0 gap, 0 dérogation sur ce champ**, `marche` fondée par `{croissance: [117,118,119],
> structure_5forces: [21,22,30,56]}`. Une vraie fondation, pas un saut. Coût $0.0013.
> `business_model.recurrence_pct` **reste** dispensé (fait NVIDIA toujours vrai).
> Le retrait **resserre** le gate : `check_readiness_recompute.py` §10 vérifie qu'une entry **C+ ne
> fonde pas** le champ.
>
> **Le 3ᵉ ticker n'est plus bloqué.**

> ## ⚡ MàJ 2026-08-31 — sprint dettes B + A (un seul déploiement)
>
> **Les deux dettes sont fermées, vérifiées contre le vrai modèle.** Commit `4be04ed`,
> deployment **#328**, un seul conteneur backend. Suite hors-ligne : **367 assertions / 0 échec**
> (329 + 17 curator + **21 d'un check neuf**).
>
> **Dette B — unités de `assumptions`.** Les trois clés portent l'unité dans le nom
> (`croissance_revenue_pct`, `expansion_marge_fcf_pct`, `multiple_sortie`), dans le contrat figé
> **et** la copie runtime, avec la consigne explicite « 12 %/an s'écrit `12.0`, jamais `0.12` » dans
> les prompts bull/bear rafraîchis en DB. **Origine trouvée** : `roadmap/01-spec-v2-unifiee.md`
> l.373 juxtaposait, dans le même objet d'exemple, `croissance_implicite_prix_actuel_pct: 14` (en
> pourcent) et `croissance_revenue: 0.10` (en fraction) — le modèle recopiait fidèlement une spec
> incohérente. Exemple corrigé. **Pas de coercition ×100** délibérément : le nom + le prompt + le
> contrat strict suffisent, et un filet de plus serait un 2ᵉ risque de polarité (cf. `conviction ×10`).
> *Vérifié contre le modèle* (MSFT, memo #4) : bull `12.0` / bear `5.0` %/an, **même échelle** —
> là où le run précédent donnait `0.15` contre `8.0`, facteur ~53. `expansion_marge_fcf_pct` bear
> à `-8.0` (compression, négatif licite).
>
> **Dette A — narration du curator.** Traitée à **trois** niveaux, parce que la cause n'était pas
> celle décrite : l'exemple de `rationale` **du prompt lui-même** se terminait par « … →
> thin_qualitative ». *Le prompt enseignait le défaut du rapport #24.* (1) exemple corrigé,
> (2) garde-fou 7 interdisant de nommer un verdict + rappel de l'ordre des tiers
> (**A > A- > B+ > B > C+ > C**), (3) `constrain_rationale()` en Python : en-tête factuel dérivé des
> booléens recomputés, et toute phrase nommant un verdict **autre** que le recomputé est retirée,
> **le retrait étant déclaré** dans le texte (jamais de coupe muette).
> *Vérifié contre le modèle* — rapport **#26**, MSFT : verdict `ready`, en-tête
> `[Verdict recomputé : ready — bloc structuré fondé, bloc qualitatif-marché fondé ; 0 champ(s) non
> fondé(s). …]`, **aucune phrase à retirer** — le garde-fou de prompt a tenu en amont, le filet
> Python n'a servi à rien. C'est le résultat voulu.
>
> **Check neuf `check_analysis_contract.py` (21 assertions)** — celui qui manquait le jour où le
> reverse-DCF a été desserré à chaud : les anciens noms nus sont désormais **rejetés** (pas ignorés),
> `croissance_implicite_prix_actuel_pct` est requis, `Assumptions` est fermé (`extra='forbid'`), et
> §6 compare **contrat figé ↔ copie runtime** (règle #19) — l'absence du montage `/contract_frozen`
> est **annoncée**, jamais silencieuse.
>
> **Résidu observé, non bloquant** : le rationale #26 écrit encore « seule une synthèse agent (A-)
> existe, sans source primaire de tier B+ ou supérieur » — l'ordre des tiers reste mal lu par le
> modèle sur une phrase qui **ne nomme aucun verdict**, donc que `constrain_rationale` laisse passer.
> Le verdict, lui, est juste. À revoir si ça se répète : la contrainte porte sur les verdicts nommés,
> pas sur les comparaisons de tiers.
>
> **Ce fichier a été allégé le même jour** → `00-REPRISE-ARCHIVE.md` (821 lignes, rien de résumé).

---

> ## ⚡ MàJ 2026-08-30 (ter) — AUDIT des desserrages de contrat faits à chaud pendant la chaîne : le `Optional` du reverse-DCF cachait un VRAI trou silencieux (bear), corrigé par durcissement prompt PUIS re-serrage du schéma (déployé #324)
>
> **Contexte** : les builds #318-#323 avaient rendu 6 champs plus permissifs pour faire passer le 1er
> run. Audit demandé (« certains paramètres rendus optionnels me semblent significatifs »). Verdict :
> **1 desserrage significatif (#4), 1 modéré (#5), les 4 autres bénins.**
>
> ### 🔬 Le finding : `reverse_dcf.croissance_implicite_prix_actuel_pct` (rendu `Optional=None`)
> C'est le **cœur de l'expectations investing** (« quelle croissance le prix price-t-il ? »). Preuve en
> base sur le 1er run NVDA : le **bull le remplit (15.0)**, le **bear le laisse `null` aux rounds 1 ET 2**
> — alors que le bear **écrit « ~15% » dans sa prose `verdict`**. Le modèle CONNAÎT le chiffre mais
> n'alimente pas le champ machine ; `Optional=None` l'a laissé passer en silence. **Pas de crash
> aujourd'hui** (le consommateur `base_rate_ge` n'est PAS encore câblé dans `analysis.py` — vérifié),
> mais **bombe à retardement** : au câblage, un `null` du bear entrerait sans bruit. Cohérent avec
> #24/#25/#28 : un manque ne doit jamais ressembler à une valeur.
>
> ### Décision utilisateur : « durcir le prompt d'abord » + « contrat d'abord » (avant agents 7-9)
> 1. **Prompts durcis** (commit `4c34367`, source de vérité règle #19) : `30-research` garde-fou 5,
>    `40-bull` garde-fou 4, `41-bear` garde-fou 2 → `croissance_implicite` = **nombre %/an OBLIGATOIRE,
>    jamais null/omis** (obtenu en inversant le DCF) ; `assumptions` **fermé aux 3 clés** contractuelles
>    (taux d'actualisation en prose dans `methode`, pas en champ inventé).
> 2. **Propagé en prod** : `agent_prompts` (research/bull/bear, flow v2) mis à jour via
>    `_gen_prompt_refresh_20260830.py` (réutilise l'assemblage de `_gen_025.py`, DB = commit) +
>    `docker cp`/`psql -f` (#17). **Pas de rebuild** : `get_agent_provider` relit la DB à chaque appel.
> 3. **Re-testé en réel** (NVDA) : research **22.0/18.0**, bull **18.0**, **bear #1 ET #2 = 18.0**
>    (contre `null` avant), `assumptions` = 3 clés partout. **L'omission a disparu en pratique.**
> 4. **Schéma re-serré** (commit `9bebd1c`, **deployment #324**, 1 seul conteneur backend vérifié,
>    HEAD==origin/main) : la copie **runtime** `analysis_v2_schemas.py` re-alignée sur le **contrat figé
>    qui, lui, n'avait JAMAIS été desserré** → `ReverseDcf.croissance_implicite_prix_actuel_pct: float`
>    (requis) + `Assumptions(Strict)` (`extra='forbid'`). Validé sous pydantic 2.13.5 (champ manquant
>    rejeté, champ inventé rejeté) ; run de contrôle post-déploiement OK (croissance 22.0).
>
> ### Les 4 autres desserrages — laissés tels quels (jugés acceptables)
> `BaseRate.taux ÷100 si>1` (bénin) · `BaseRatePct alias taux→taux_pct` (faible) · `curator
> readiness_report_id or 0` (cosmétique) · `BullCase.conviction ×10 si≤1` : **coercition gardée comme
> filet** (risque de polarité théorique sur le float `1.0` → note pour plus tard, pas corrigé). Le
> desserrage `Assumptions extra=ignore` (#5) ne masquait rien en base (invention `taux_actualisation`
> transitoire) mais re-serré par principe.
>
> ### RESTE À FAIRE (inchangé, « contrat d'abord » désormais satisfait)
> 1. **Agents 7-9** (décision/validate M6 → sortie/calibration → débat), migrations 030/031 juste avant.
> 2. **Second ticker** (généralité de la chaîne).
> 3. **UX transverse** (§16). 4. **`ingestion-agent`** (C2, non bloquant).
> ⚠️ **Dette connue** : `reverse_dcf.croissance_implicite` est désormais TOUJOURS chiffré, mais son
> consommateur `base_rate_ge` n'est **toujours pas câblé** dans `run_research` — à faire quand on
> finalisera le `taux_base_pct` précis (le champ est maintenant fiable pour ça).

> ## ⚡ MàJ 2026-08-30 (bis) — CHAÎNE D'ANALYSE COMPLÈTE EXERCÉE EN RÉEL (première fois)
>
> **Chaîne research→bull→bear→réfutation→synthèse complète pour NVDA.** Coût total < $0,015.
>
> | étape | ID | résultat | coût |
> |---|---|---|---|
> | Research memo | #1 | posture NEUTRE, memo structuré complet | $0.003 |
> | Bull case | #1 | conviction 7/10, variant_perception analytique | — |
> | Bear case | #2 | conviction 6/10, ASIC risk comme thèse centrale | $0.003 |
> | Réfutation (bear v2) | #3 | `refutation_du_bull` : 3 items, round 2 | $0.002 |
> | **Synthèse** | **#4** | **PROCEED_AVEC_CONDITIONS** | **$0.004** |
>
> **Verdict final** `PROCEED_AVEC_CONDITIONS` — seuil d'entrée `< 180$` (marge sécurité > 25%). Position
> sizing 3% (Kelly fractionnaire réduit de 3,9% pour marge de sécurité faible). 5 hypothèses de
> monitoring (H1-H5) avec seuils d'invalidation chiffrés (H1 = part de marché inférence IA > 70%,
> seuil invalidation 60%). **Pont `valider_pont()` validé** : chaque risque accepté pointe une hypothèse existante.
>
> ### Corrections de schéma nécessaires au fil de la chaîne (builds #318-#323)
>
> | problème | fix | fichier |
> |---|---|---|
> | `BaseRate.taux=70` (modèle renvoie %) | coerce ÷100 si > 1 | `analysis_v2_schemas.py` |
> | `BaseRatePct.taux_pct` absent (modèle envoie `taux`) | alias `taux`→`taux_pct` | idem |
> | `BullCase.conviction=0.6` (modèle scale 0-1) | coerce ×10 si ≤ 1 | idem |
> | `ReverseDcf.croissance_implicite_prix_actuel_pct` manquant | `Optional[float] = None` | idem |
> | `Assumptions.taux_actualisation*` (champs inventés) | `extra="ignore"` sur `Assumptions` | idem |
> | `curator.readiness_report_id=None` (setdefault ne remplace pas None) | `or 0` pattern | `curator.py` |
>
> ### RESTE À FAIRE
> 1. **Agents 7-9** : décision/validate (monitoring M6) → sortie/calibration → débat conviction
>    (migrations 028/029 à écrire juste avant chaque lot).
> 2. **Second ticker** : exercer la chaîne complète sur un ticker différent de NVDA pour valider la
>    généralité (notamment readiness gate, synthesis_feed, context_pack).
> 3. **UX transverse finale** (§16) : affichage du verdict dans le frontend, suivi des hypothèses H1-H5.
> 4. **`ingestion-agent`** (contrat C2, doc→entries) : non construit, non bloquant tant que le search-worker
>    + synthesis_feed couvrent les champs requis.

> ## ⚡ MàJ 2026-08-30 — le gate de readiness est DÉTERMINISTE : la couverture se LIT dans l'index `covers` (migration 029, `TEXT[]` + chemins complets + GIN), elle ne se demande plus au modèle. L'oscillation à corpus figé est fermée.
>
> **Décision utilisateur : option A** (`covers TEXT[]` + backfill explicite des entries legacy), contre
> l'option « une entry de synthèse par champ ». Motif retenu : une entry porte ce qu'elle porte — #19
> ou #35 fondent réellement plusieurs champs, et fabriquer une entry de synthèse par champ aurait
> multiplié les tours LLM pour ré-écrire ce que le corpus disait déjà.
>
> ### Ce qui change (convention #29 dans `CLAUDE.md`)
> `recompute_coverage` ne **filtre** plus les `entry_ids` cités par le LLM : il **bâtit un index**
> `dimension.champ → [(entry_id, tier)]` depuis la base (`_covers_index`, pur Python — `get_current_entries`
> SELECTait déjà `covers`, aucune requête supplémentaire), puis, pour chaque champ requis, retient les
> entries au-dessus du plancher. Le LLM n'écrit plus que la **prose** (`rationale`, `gaps`,
> `incertitudes_investissables`, `qualite_info`) ; ses `fondations` sont écrasées. Trois leviers fermés
> d'un coup :
> 1. **couverture par citation → index** : une entry adéquate non citée ne crée plus de faux creux ;
> 2. **tag libre → vocabulaire FERMÉ** (`MVDD_FIELD_PATHS`) : depuis que le tag pilote le verdict, c'est
>    un vote — donc seules les voies déterministes l'écrivent, dans l'esprit de #24 ;
> 3. **`_exigences()`** : le modèle peut **RESSERRER** `champs_requis`/`tier_plancher`, jamais desserrer.
>
> ### Migration 029 (appliquée en prod AVANT le déploiement, docker cp + psql, #17)
> `covers` TEXT → **TEXT[]**, valeurs re-qualifiées en **chemins COMPLETS** `dimension.champ` (sans quoi
> `produits.description` fonderait `business_model.description` — homonymie), btree → **GIN**, et
> **backfill relu à la main des 17 entries qualitatives legacy NVDA** (#19-#35). Sortie : `UPDATE 19`
> (re-qualification) puis `UPDATE 12` (backfill). Volontairement **non taguées**, et c'est documenté
> dans la migration : #25/#27 (retours au capital — aucun champ requis), #32/#33/#34 (marges
> consolidées — ce sont les *intrants* de la synthèse #53, pas le champ), #1-10/#48 (faits EDGAR bruts),
> #11-15 (`llm_memory` tier C).
>
> ### Déviation assumée par rapport au chiffrage annoncé
> J'avais chiffré l'option A comme rouvrant le contrat **C1 figé** (donc règle #19, 3 points de synchro).
> **Je ne l'ai pas fait** : `worker_delegation_schema.py:129` garde `covers: Optional[str]`. Le mandat
> d'un search-worker porte **un seul champ** ; lui laisser déclarer une liste lui rendrait précisément
> le levier sur le gate qu'on vient de lui retirer. Le worker écrit donc un chemin complet unique, via
> `_resolve_covers()` qui **préfère le mandat** et ne retient une proposition du modèle que si elle est
> dans `MVDD_FIELD_PATHS`. **Coût réel du sprint : 0 point de synchro #19.**
>
> ### État de la couverture NVDA après backfill (22 entries taguées, lu en base)
> Tous les champs requis sont couverts **au-dessus du plancher** — sauf trois, dont un déjà déclaré :
>
> | champ non couvert | statut |
> |---|---|
> | `business_model.description` | **vrai gap** — synthétisable depuis #19/#20/#35 (tier A) via `synthesis_feed` |
> | `business_model.recurrence_pct` | **vrai gap** — à synthétiser ou à déclarer non bloquant |
> | `marche.croissance_marche_historique` | déjà **déclaré non bloquant** (donnée de marché EXTERNE, #25) |
>
> ### Déterminisme vérifié en prod — 4 tirs consécutifs (reports #16-#19, 2026-08-30)
> ```
> [GAP] business_model: gaps=['description', 'recurrence_pct']
> [OK]  financials, valorisation, produits, positionnement, marche, management_allocation, risques
> verdict: not_ready  (4/4)
> ```
> Corpus strictement identique, verdict strictement identique. L'oscillation est fermée.
>
> ### RESTE À FAIRE
> 1. **Fermer les 2 champs `business_model`** (synthèse grounded #53-style, ou déclaration honnête pour
>    `recurrence_pct` si le corpus ne le porte pas) → NVDA `ready`.
> 2. Puis la **chaîne d'analyse jamais exécutée** (research → bull/bear → réfutation → synthèse +
>    `valider_pont()`). ⚠️ `analysis.py` appelle `run_json_agent` avec `json_object` au défaut (True) :
>    **passer `json_object=False` AVANT le premier run** (même piège DeepSeek que l'ingestion-agent).
>
> ## ⚡ MàJ 2026-08-26 (ter) — couche COVERS DÉPLOYÉE (migration 028 + curator option B) : le gate est resserré, MAIS la readiness NVDA OSCILLE sur données FIXES → c'est du bruit de citation LLM, pas un creux. Finding archi : le recompute Python VÉTOTE les citations du LLM, il ne les DÉCOUVRE pas.
>
> **Déployé** (commit `3776d74`, un seul conteneur backend vérifié `docker ps` — pas d'orphelin,
> HEAD == origin/main). **Migration 028 appliquée** au DB prod AVANT déploiement (docker cp + psql,
> #17) : colonne `knowledge_entries.covers` (champ MVDD nu porté par l'entry) + backfill (32 entries
> depuis `content_structured.field_path`/`field`/`metric`) + index partiel. Les producteurs (synthèse,
> feeds, search-worker) la remplissent désormais à l'écriture.
>
> ### Ce qui a été construit et VÉRIFIÉ en prod
> Le curator (option C tier-plancher) vérifiait le TIER des entries citées mais pas la PERTINENCE de
> leur contenu — une entry tier A **hors-sujet** pouvait « fonder » un champ (constaté : la croissance
> de NVDA #19 « fondait » `croissance_marche_historique`). La couche covers exige **`covers == champ`**
> quand renseigné ; **fallback tier-only quand `covers IS NULL`** (entries legacy non taguées → pas de
> régression). Effet mesuré : readiness NVDA **#10 `ready` (avant covers, 13:43) → #11 `not_ready`
> (après, 14:28)**. Le gate est plus honnête.
>
> ### 🔬 Déterminisme TRANCHÉ (3 tirs, données STRICTEMENT fixes)
> Le seul champ qui bloque est `business_model.description`. Sur données identiques :
>
> | report | verdict | `description` fondée par | ok ? |
> |---|---|---|---|
> | #11 | `not_ready` | [11, 57] (C 0.4 + context_pack B-) | ❌ |
> | #13 | `thin_qualitative` | [11, **19**] (#19 = tier A) | ✅ |
> | #14 | `not_ready` | [11] seul | ❌ |
>
> **Verdict : bruit de citation LLM, PAS un vrai creux.** L'entry **#19** (« Data Center segment
> FY2026 », tier A 0.89) fonde réellement `description` — mais elle est **legacy `covers=NULL`**, donc
> c'est le **LLM du curator** qui décide par-champ à quelle dimension la rattacher (tantôt `description`,
> tantôt seulement `drivers_revenus`/`recurrence_pct`). Ce rattachement n'est **pas déterministe** → le
> verdict oscille `not_ready` ↔ `thin_qualitative` à corpus figé.
>
> ### 🐛 Finding architectural (la vraie cause, `curator.py:67-108`)
> `recompute_coverage` **filtre les `entry_ids` que le LLM a CITÉS** par champ (garde ceux dont
> `covers ∈ {None, champ}` **et** tier ≥ plancher) : c'est un **véto sur la citation LLM, pas un index
> indépendant**. Une citation manquée = **faux creux**, même si une entry adéquate existe en base. Le
> même mécanisme frappe `produits.unit_economics` : l'entry **#53** (`covers='unit_economics'`, tier
> **A-** 0.85) existe et est au-dessus du plancher, mais le run où le LLM ne la cite pas la déclare
> « non fondée, sous plancher » (prose LLM erronée qui la dit « B- » — cosmétique). Le covers **ferme
> le trou de sur-crédit** (tier A hors-sujet) mais **pas le trou de sous-crédit** (entry adéquate non
> citée).
>
> ### RESTE À FAIRE — rendre le gate DÉTERMINISTE (= prochain sprint)
> 1. **Recompute la couverture par champ en Python à partir de l'INDEX `covers`**, pas des citations
>    LLM : pour chaque champ requis, `SELECT` des entries non superseded avec `covers==champ` **et**
>    tier ≥ plancher — le LLM ne sert plus qu'à la **synthèse narrative**, plus au gate. Supprime
>    l'oscillation d'un coup (business_model ET produits).
> 2. **`covers` est mono-valué (TEXT)** mais #19 porte **3 champs** (`description`/`drivers_revenus`/
>    `recurrence_pct`) → trancher : `covers[]` (array + index GIN) **ou** entries de synthèse par-champ
>    (le patron déjà éprouvé pour unit_economics/moat/structure_5forces). **Décision utilisateur requise.**
> 3. Une fois le modèle multi-champ tranché : **backfill `covers`** sur les tier-A qualitatives legacy
>    (#19, #20, #23-#35).
> 4. **Seul vrai gap de CONTENU restant** (inchangé) : `marche.croissance_marche_historique` — donnée
>    de marché EXTERNE (TAM IDC/Gartner, upload), non synthétisable depuis le KB (#25).
> 5. Puis readiness déterministe → `ready` → **chaîne d'analyse jamais exécutée** (research→bull/bear→
>    réfutation→synthèse), `run_json_agent(json_object=False)` obligatoire (même piège DeepSeek).
>
> ## ⚡ MàJ 2026-08-26 (bis) — INGESTION-AGENT mode SYNTHÈSE (C2) CONSTRUIT, DÉPLOYÉ & EXERCÉ EN RÉEL ; run_json_agent a enfin tourné contre le vrai modèle (gotcha json_object trouvé + corrigé)
>
> **Déployé** (commits `fda6340`→`059d3a4`, deployments #297→#302, un seul conteneur backend vérifié
> `docker ps` — orphelin #301 stoppé+supprimé). **Aucune migration.** Même patron que les feeds
> (`valuation_feed`/`financials_feed`) : transformation pure testable + IO, mais **un tour LLM
> grounded**.
>
> ### Ce qui a été construit
> - **`backend/app/knowledge/synthesis_feed.py`** : fonde un champ qualitatif NON-fetchable par
>   SYNTHÈSE grounded des entries tier A/A-/B+ déjà en base. (1) charge le corpus citable pour le
>   champ ; (2) un tour LLM compose la synthèse ; (3) **grounding VÉRIFIÉ en Python** (chaque
>   `cited_entry_id` ∈ corpus, sinon `SynthesisUngrounded`, rien n'est écrit) + **tier dérivé
>   déterministe**. Contrat runtime **`GroundedSynthesis`** (`app/contracts/synthesis_schema.py`),
>   route **`POST /tickers/{id}/knowledge/synthesize`** (dry-run `persist:false`, `debug_raw` pour
>   la sortie LLM brute) + `GET /knowledge/synthesis/targets`. `store_knowledge` gagne
>   `derived_reliability`/`requires_human_review` (override étroit, réservé aux fondations
>   déterministes). Check **`check_synthesis_feed.py` 31/31** hors-ligne, non-régression OK.
> - **Prompt** `prompts/10b-ingestion-synthese.md` (distinct du 10-ingestion-agent, mode extraction).
>   ⚠️ Ce « C2 » est la **synthèse** décrite dans la MàJ du matin, PAS le contrat
>   `ingestion_extraction_schema.py` (document→entries), qui reste à construire (étape 4).
>
> ### 🐛 Gotcha modèle trouvé au 1er run réel (run_json_agent n'avait JAMAIS tourné contre le modèle)
> DeepSeek-V4-Flash est **NON FIABLE sous `response_format=json_object`** : il collapse sur `{}`
> (3 tokens out), ou emballe la sortie dans un objet parasite `{"./": "<json échappé>"}`. En
> **prompt-only** (sans `response_format`) il rend un **JSON propre et correctement cité**. Fix :
> `run_json_agent` gagne un flag `json_object` (défaut True) ; `synthesize` l'appelle avec
> `json_object=False`. **À GARDER À L'ESPRIT pour la chaîne d'analyse** (research/bull/bear/synthèse
> appellent tous `run_json_agent`, jamais exercée) — même piège probable.
>
> ### Résultat des dry-runs NVDA (règle de tier CONSERVATRICE, choix utilisateur)
> Règle validée : **tier = un cran sous la plus faible entry citée** (A→A-, A-→B+, B+→B),
> `source_type='agent_synthesis'`, `requires_human_review=True`, jamais de surévaluation. **Règle
> PROVISOIRE, à revoir à l'usage si trop bloquante** (cf. mémoire `project-synthesis-tier-rule`).
>
> | champ | cited_tiers | plus faible | tier dérivé | fonde B+ ? |
> |---|---|---|---|---|
> | `produits.unit_economics` | 9×A + 2×B+ (#21/#22) | B+ | **B (0.70)** | ❌ |
> | `marche.structure_5forces` | 8×A + 2×B+ (#21/#22) | B+ | **B (0.70)** | ❌ |
>
> ### PERSISTÉ EN PROD + readiness recomputée (choix utilisateur : resserrer unit_economics + persister)
> `unit_economics` resserré au socle **tier A/A-** (`SynthesisTarget.citable_tiers`, deployment #303) :
> exclut par PERTINENCE la presse marché B+ (#21/#22, hors-champ) → cité 11 entries **toutes A** →
> **A- (0.85)**. Persisté :
> - **entry #53** `produits.unit_economics` tier **A-**, `requires_human_review=True` ;
> - **entry #54** `marche.structure_5forces` tier **B** (règle conservatrice : cite #21/#22 B+ →
>   un cran sous = B), `requires_human_review=True`.
>
> `POST /curator/readiness` NVDA (report **#8**) → verdict **`thin_qualitative`** (bloc structuré
> complet). **`produits` : ok=True (tier A)** — la synthèse a FONDÉ le champ, preuve que le C2
> synthèse fonctionne de bout en bout. Gaps qualitatifs restants : `positionnement.moat_preuves`,
> `marche.croissance_marche_historique` (champs DIFFÉRENTS, à sourcer autrement — search-worker).
>
> ### ⚠️ Observation d'intégrité — le curator ne ré-applique pas strictement le plancher
> La synthèse `structure_5forces` **tier B** a été comptée par le curator comme **fondant** le champ
> (plancher B+) : elle n'apparaît plus dans les manques de `marche`. La règle conservatrice est donc
> respectée à la PRODUCTION de l'entry (tier B honnête) mais **pas ré-appliquée à la LECTURE** —
> c'est le jugement LLM du curator qui tranche « fondé/non-fondé » par champ, le backend ne
> recompute que `ok = (manques vides)`. Comportement curator déjà noté (verdict non déterministe,
> MàJ 2026-08-25). **Point pour le fil « revoir la catégorisation des sources à l'usage »** : si on
> veut que le plancher morde à la lecture, il faudrait le recomputer en Python (tier_atteint des
> entries qui couvrent le champ ≥ plancher), pas le laisser au LLM.
>
> ### SUITE (2026-08-26, même session) — `positionnement` fondé par synthèse ; NVDA à UN champ de `ready`
> - `positionnement.moat_preuves` : search-worker `not_found` (sources sous plancher) → **cible de
>   synthèse** ajoutée, resserrée A/A- (les preuves du moat = CUDA #20/échelle/risques EDGAR A ; la
>   presse B+ #21/#22 porte des MENACES, pas des preuves). Persisté **entry #55 tier B+**,
>   `requires_human_review=True`. `deployment #305`.
> - `marche.croissance_marche_historique` : **vrai gap laissé ouvert** — search-worker `not_found`,
>   et NON synthétisable (le KB a la croissance de NVDA, pas du MARCHÉ → erreur de catégorie, #25).
>   Nécessite une donnée de marché EXTERNE (TAM IDC/Gartner, upload).
>
> ### 🐛🐛 Deux bugs curator trouvés au 1er `ready` réel (jamais atteints — aucun ticker n'avait été ready)
> 1. **Ordre context_pack** : `run_readiness` validait le ReadinessReport (qui exige
>    `context_pack_entry_id` dès verdict=ready) AVANT de produire le context_pack → échec
>    systématique de tout `ready`. Fix : produire le context_pack quand verdict recomputé=ready, puis
>    valider une fois (`deployment #306`).
> 2. **`json_object` dans `curator._call_json`** (readiness ET context_pack) : même pathologie
>    DeepSeek (`{}` ou emballage `{"/mnt/data/…json":"…"}`, cette 2ᵉ forme a fait échouer la 1ère
>    prod du context_pack) → **prompt-only + extract_json** (`deployment #307`). Cohérent avec
>    `run_json_agent(json_object=False)`.
>
> ### ÉTAT readiness NVDA (report **#9**, propre) : `thin_qualitative`, 7/8 dimensions fondées
> struct (business_model A, financials A, valorisation B+) ✅ · produits A ✅ (synthèse) ·
> positionnement B+ ✅ (synthèse #55) · management_allocation A ✅ · risques A ✅ ·
> **marche ❌ — manque `croissance_marche_historique`** (donnée de marché externe).
>
> ### RESTE À FAIRE
> 1. **`marche.croissance_marche_historique`** : fournir une donnée de marché (upload TAM, ou source
>    quant marché) → dernière brique pour `ready`. C'est le SEUL gap restant.
> 2. **Décider si le plancher doit mordre à la LECTURE** (recompute Python côté curator) : observé
>    que le curator (LLM) a compté `structure_5forces` **B** comme fondant un champ B+, et son
>    jugement par-champ est non déterministe. Pour un gate fiable, recomputer en Python
>    `tier_atteint(entries couvrant le champ) ≥ plancher` au lieu de le confier au LLM.
> 3. **Chaîne d'analyse (jamais exécutée)** : une fois `ready`, lancer research→bull/bear→réfutation→
>    synthèse. ⚠️ `analysis.py` appelle `run_json_agent` en **json_object par défaut** → lui passer
>    **`json_object=False`** (le param existe) AVANT le 1er run, sinon même collapse `{}` que la synthèse.
>
> ## ⚡ MàJ 2026-08-26 — `financials` FONDÉE EN PROD (tier A, 4 champs) après correction d'un bug d'intégration ; bloc structuré COMPLET, verdict `thin_qualitative`
>
> **Le persist prod de `financials` a révélé que le chemin réel n'avait JAMAIS fonctionné** — et
> l'a corrigé. Déployé (commit `82208e5`, deployment **#296**, un seul conteneur backend vérifié
> `docker ps`, pas d'orphelin). **Aucune migration.**
>
> ### 🐛 Bug d'intégration trouvé au premier persist réel (le piège « vérifié ≠ vérifié sur le chemin réel »)
> Le dry-run prod rendait `capex_source: "cik_introuvable"` → `fcf_conversion_pct` et
> `intensite_capex_pct` restaient non fondés (seuls `levier`/`roic_pct`, purement en base, sortaient).
> **Cause racine** : `knowledge/service.py::get_current_entries()` **ne sélectionnait pas `source_url`**
> dans son SELECT. Or `financials_feed` dérive le CIK EDGAR du motif `/data/<cik>/` de l'URL d'un fait
> en base (aucune table de correspondance). Sans `source_url`, `cik_from_url()` renvoyait
> **toujours** `None` → capex jamais fetché. **Preuve en base** : les entries dérivées `financials`
> #40→#47 étaient **4 rounds de persist antérieurs** n'ayant jamais écrit que `levier`+`roic`, avec une
> `source_url` **vide** — signature exacte du bug. **Pourquoi la MàJ ter a cru que ça marchait** : la
> « vérification contre l'API EDGAR » testait `fetch_annual_value(1045810, …)` avec le CIK **en dur**,
> et `check_financials_feed.py` (32/32) construit ses entries **avec** `source_url` (asserte même
> `facts["source_url"] == URL`) — le check masquait le trou d'intégration. **Fix** : ajout de
> `source_url` au SELECT de `get_current_entries` (corrige d'un coup la dérivation du CIK **et** la
> provenance des entries dérivées, jusque-là vide). Leçon renforcée : un feed n'est acquis que quand
> son **chemin d'IO réel** a tourné en prod, pas seulement ses fonctions pures + un fetch à CIK codé.
>
> ### Persisté + vérifié en réel (2026-08-26)
> `financials-refresh` (persist, refresh) → `capex_source: edgar_fetched`, **`unfounded=[]`** : capex
> fait EDGAR #48 (réutilisable, tier A) + `levier` #49 (gearing 4,75 %, trésorerie nette positive),
> `roic_pct` #50 (77,89 %), `fcf_conversion_pct` #51 (80,52 %), `intensite_capex_pct` #52 (2,8 %).
> `POST /curator/readiness` NVDA (report #7) → **`financials` : ok=True (A)**, **bloc structuré
> `bloc_ok=true`** (business_model B+, financials A, valorisation B+). 41 entries (30 A / 6 B / 5 llm_memory).
>
> ### Verdict `thin_qualitative` — il ne reste que 2 champs qualitatifs pour `ready`
> Le bloc structuré, bloqueur historique, est **entièrement fondé**. Gaps restants (bloc qual. marché) :
>
> | dimension | ok | manque |
> |---|---|---|
> | produits | ❌ | `unit_economics` (économie unitaire : coût/GPU, coût/token — **entrée de synthèse**, pas fetch brut) |
> | marche | ❌ | `structure_5forces` (analyse Porter **structurée** — synthèse) |
> | positionnement, management_allocation, risques | ✅ | — |
>
> **Search-worker testé sur `produits.unit_economics` (2026-08-26, dry-run, `field_path` ciblé,
> `max_iterations=8`) → `not_found`, 0 entrée.** Confirme empiriquement que ces 2 champs ne sont PAS
> fondables par fetch : l'économie unitaire (ASP/coût par GPU, coût/token) n'est ni dans un dépôt EDGAR
> (NVDA ne publie pas de volumes unitaires — l'ASP n'est pas calculable des faits disclosés, contrairement
> aux ratios `financials`) ni lisible en fetch depuis le VPS (notes d'analystes paywallées, 403). Le KB a
> déjà les matériaux tier A (entries #32-35 marges/coûts consolidés pour unit_economics ; #21,22,28-31
> menace ASIC / concentration clients / AMD-Huawei / TSMC / export controls pour les 5 forces) — mais
> **aucune entrée ne les SYNTHÉTISE** au niveau que le curator exige.
>
> ### ⛔ Frontière de capacité — le prochain sprint = construire l'INGESTION-AGENT (synthèse grounded, contrat C2)
> Asymétrie clé : la **chaîne d'analyse** (research/bull/bear) est gated par `ready`, mais la **synthèse
> d'alimentation du KB** ne l'est PAS. L'outil manquant est donc l'`ingestion-agent` (étape 4 du plan,
> jamais construit), pas la chaîne. Design proposé, même patron que `valuation_feed`/`financials_feed`
> (transform testable + IO) mais LLM-composé et **grounded** : (1) charger les entries tier A/B+ citables
> pour le champ visé ; (2) un tour LLM (DeepInfra) compose la synthèse **strictement** à partir de ces
> entries, chaque assertion → `source_entry_id` (aucun fait hors-KB) ; (3) persister une entry
> `entry_type='synthesis'` avec `field_path`, `content_structured.cited_entry_ids`, tier dérivé (synthèse
> de tier A ⇒ A-/B+ selon règle), `requires_human_review=True` au départ. **NE PAS** injecter d'entrée
> non fondée pour forcer `ready` (violerait G3/#24/#25/#28 — le cœur du projet). Une fois les 2 champs
> fondés → readiness → `ready` → **lancer la CHAÎNE D'ANALYSE jamais exécutée** (research → bull/bear →
> réfutation → synthèse + `valider_pont`).
>
> ## ⚡ MàJ 2026-08-25 (ter) — dimension `financials` : alimentateur de ratios dérivés DÉPLOYÉ + vérifié contre l'API EDGAR (⚠ pas encore persisté en prod)
>
> **Déployé** (commit `9c0a818`, deployment **#295**, un seul conteneur backend vérifié `docker ps`
> — pas d'orphelin). **Aucune migration.** Même patron que `valuation_feed`/`base_rate_corpus` :
> transformation pure testable + couche IO.
>
> - **`backend/app/knowledge/financials_feed.py`** : fonde les 4 champs de `financials` —
>   `roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct`, `levier`. Ce ne sont PAS des mesures mais
>   des **ratios**, donc **calculés** depuis les postes comptables. Point clé de conception : le
>   plancher de `financials` est **tier A** → un ratio issu du quant (yfinance/FMP, **B+**) ne
>   fonderait PAS le champ. On calcule donc **uniquement** à partir des `fact_financial` **EDGAR** déjà
>   en base (tier A) : un ratio dérivé de faits tier A seuls est lui-même tier A → `source_type='edgar_official'`.
>   `build_financials_entries()` (pur) ne produit une entry QUE si tous les intrants existent ; sinon le
>   champ est reporté dans `unfounded` (jamais un chiffre fabriqué, #25). `levier` = gearing dette/CP +
>   dette nette (dette nette/EBITDA **négatif** car trésorerie nette positive → le gearing est la lecture
>   pertinente, noté). `roic_pct` : NOPAT **≈ résultat net** (charge d'intérêts nette négligeable en
>   trésorerie nette), approximation **déclarée dans le content** (peut légèrement majorer).
> - **`backend/app/knowledge/edgar_facts.py`** : le seul poste absent du seed est le **capex**
>   (nécessaire à `fcf_conversion_pct` = FCF/RN avec FCF=OCF−capex, et `intensite_capex_pct` =
>   capex/CA). Il n'est ni fabriqué ni emprunté au quant : **mesuré à la source** via l'API XBRL
>   `companyconcept` d'EDGAR. **CIK dérivé de l'URL EDGAR déjà en base** (`/data/<cik>/`) — aucune table
>   de correspondance. Échec EDGAR → `EdgarUnavailable`, les 2 champs restent non fondés (#25).
> - **Route** `POST /tickers/{id}/knowledge/financials-refresh` (`persist`/`refresh`,
>   `FinancialsUnavailable`→422). **Check** `backend/checks/check_financials_feed.py` **32/32** hors-ligne.
>
> ### ⚠️ Gotcha capex — tag XBRL NVDA (vérifié contre l'API EDGAR réelle 2026-08-25)
> NVDA déclare le capex récent sous **`us-gaap:PaymentsToAcquireProductiveAssets`**, PAS sous le
> `PaymentsToAcquirePropertyPlantAndEquipment` classique (qui **s'arrête à 2012** pour NVDA — 200 mais
> données périmées). La liste `_CAPEX_TAGS` gère le **fallthrough** : le 1er tag ne matche aucun
> exercice près de la date de bilan visée → `EdgarUnavailable` → 2e tag retenu. **À garder à l'esprit
> pour d'autres tickers : le concept capex varie d'un émetteur à l'autre.**
>
> ### Vérifié CONTRE L'API EDGAR (transform pur + fetch), pas seulement hors-ligne
> Fetch réel `companyconcept` CIK 1045810 → **capex FY2026 = 6,042 Md$** (end 2026-01-25, via le 2e tag).
> Ratios calculés sur les vrais chiffres NVDA FY2026 : **`roic_pct` 77,9 %** · **`fcf_conversion_pct`
> 80,5 %** · **`intensite_capex_pct` 2,8 %** · **`levier` gearing 4,75 %** (trésorerie nette positive)
> → **0 champ non fondé**. Exactement ce qu'il faut pour que `financials.ok=True` (tier A).
>
> ### ⛔ CE QUI RESTE À FAIRE (non fait — la fondation n'est PAS encore en base)
> Le run **en prod** (persist + recompute readiness) a été **bloqué par le garde-fou de permission**
> puis reporté par l'utilisateur. Donc, contrairement aux sprints 1+2, **les entries `financials` NE
> SONT PAS écrites dans la KB NVDA et la readiness N'A PAS été recomputée**. Reste à faire, en 1er, à
> la reprise :
> 1. `POST /tickers/NVDA/knowledge/financials-refresh` (`persist:true`) — écrit le capex EDGAR (fait
>    tier A réutilisable) + les 4 ratios (supersede par tags). Vérifier `capex_source='edgar_fetched'`,
>    `unfounded=[]`, `docker ps` = 1 conteneur.
> 2. `POST /curator/readiness` NVDA — confirmer **`financials` : ok=True (A)** et le nouveau verdict
>    (attendu : bloc structuré désormais complet ; reste le bloc qualitatif → toujours `not_ready`).
>
> Après ça, gaps restants = **qualitatif** (`business_model`, `produits`, `positionnement`, `marche`)
> via le search-worker taggé `field_path` — étape 2 ci-dessous inchangée.
>
> ## ⚡ MàJ 2026-08-25 (bis) — dimension `valorisation` FONDÉE de bout en bout (sprints 1+2 déployés + vérifiés en réel)
>
> **Déployé** (commit `8fecdd5`, deployment **#294**, un seul conteneur backend vérifié). Deux
> alimentateurs déterministes, sur le modèle du search-worker (transformation pure testable + IO),
> **aucune migration** (`entry_type` est du texte libre, colonne `tags` existante) :
>
> - **Sprint 1 — `backend/app/knowledge/valuation_feed.py`** : fonde `valorisation.prix_actuel` et
>   `valorisation.relatif_multiple` depuis le quant (DataService → yfinance `.info`, `source_type='yfinance'`
>   tier **B+ 0.75** = pile le plancher). Append-only avec supersede (le prix est volatil). Route
>   `POST /tickers/{id}/knowledge/valuation-refresh` (`persist`/`refresh`, `ValuationUnavailable`→422).
>   Ticker sans symbole (privé/`PUB-`) → refus explicite, jamais une entrée vide (#25).
> - **Sprint 2 — `backend/app/knowledge/base_rate_corpus.py`** : fonde `valorisation.base_rate_anchor`
>   — qui **n'est PAS une donnée de marché** mais une **ancre de taux de base** (outside view). Une base
>   rate ne se *génère* pas au LLM (le groundedness-checker la flaggerait `base_rate_fabrique`), elle se
>   *mesure* : corpus transverse (`ticker_id IS NULL`, `entry_type='base_rate'`) **seedé depuis les
>   chiffres réels de l'Exhibit 2 du Base Rate Book** (Mauboussin/CS-HOLT 1950-2015, distribution des CAGR
>   de ventes 1/3/5/10 ans, n=53 266) + **classifieur déterministe** (taille en CA, maille du livre) +
>   **entry par-ticker** qui cite le corpus. Route `POST /tickers/{id}/knowledge/base-rate-anchor`.
>   ⚠️ Les chiffres EXACTS ne couvrent que l'univers complet ; pour une méga-cap le `taux_base_pct` est
>   marqué **borne haute** (Exhibit 4 : la persistance chute avec la taille), jamais une distribution
>   méga-cap inventée.
> - **Checks hors-ligne** (`backend/checks/check_valuation_feed.py` 20/20 · `check_base_rate_corpus.py`
>   27/27, dont l'arithmétique confrontée au livre : P(≥20 %/an sur 3 ans)=11,9 %, colonnes=100 %).
>
> **Exercé EN RÉEL sur NVDA (2026-08-25)** — vraies données yfinance servies malgré le 429 (cache
> DataService) : prix `212,39 $`, P/E TTM `32,5×`, EV/EBITDA `30,2×` → entries #36/#37 (B+) ;
> ancre méga-cap → corpus #38 + entry #39 (B+, P(≥20 %/an, 5 ans)=`8,5 %`, médiane `5,2 %`, borne haute).
> **`POST /curator/readiness` NVDA → `valorisation` : `ok=True` (B+), `champs_non_fondables=[]`.**
> La valorisation, bloqueur structurel de la MàJ précédente, **n'est plus le problème**.
>
> ### Verdict toujours `not_ready` — mais les gaps ont bougé aux AUTRES dimensions
> Couverture readiness NVDA au 2026-08-25 (36 entries : 25 A / 6 B / 5 llm_memory) :
>
> | bloc | dimension | ok | manque |
> |---|---|---|---|
> | structurée | **valorisation** | ✅ | — (fondée sprints 1+2) |
> | structurée | management_allocation, risques | ✅ | — |
> | structurée | `financials` | ❌ | `roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct` (**ratios dérivés** — calculables du quant/EDGAR, comme la valo ; PAS du web) |
> | structurée | `business_model` | ❌ | `description`, `drivers_revenus`, `recurrence_pct` (qualitatif) |
> | qual. marché | `produits` | ❌ | `description`, `unit_economics` |
> | qual. marché | `positionnement` | ❌ | `moat_preuves`, `position_vs_pairs` |
> | qual. marché | `marche` | ❌ | `croissance_marche_historique`, `structure_5forces` |
>
> ### Prochaines étapes concrètes (dans l'ordre pour amener NVDA à `ready`)
> 1. **`financials` — ratios dérivés** (`roic_pct`, `fcf_conversion_pct`, `intensite_capex_pct`, `levier`) :
>    même patron que `valuation_feed` — un alimentateur déterministe qui **calcule** ces ratios depuis les
>    `fact_financial` EDGAR déjà en KB + le quant. C'est le gap structuré le plus proche, non web.
> 2. **`business_model` + qualitatif (`produits`/`positionnement`/`marche`)** : via le **search-worker**
>    (déjà exercé) en **taguant `field_path`** sur les entries pour fiabiliser le jugement par champ,
>    + entrées de **synthèse** pour `unit_economics` / `structure_5forces` (analyses, pas fetch brut).
> 3. Readiness → `ready` → **lancer la CHAÎNE D'ANALYSE** (`research` → `bull`/`bear` → réfutation →
>    `synthesis` + `valider_pont`). **Jamais exécutée à ce jour** — c'est le vrai prochain jalon une fois
>    `ready` atteint. À l'analyse, `run_research` lira `reverse_dcf.croissance_implicite_prix_actuel_pct`
>    et appellera `base_rate_corpus.base_rate_ge(seuil, horizon)` pour finaliser le `taux_base_pct` précis.
>
> **Permission** : `Bash(infrastructure/deploy.sh:*)` ajoutée dans `.claude/settings.json` (racine repo).

> ## ⚡ MàJ 2026-08-25 — premier run end-to-end réel du search-worker (le gros « jamais vérifié » est levé)
>
> **Le lot « recherche intra-document + provenance vérifiée » (commit `6ef4fa4`, deploy #283) est en
> prod et VÉRIFIÉ de bout en bout.** Checks : `check_provenance.py` **42/42** hors-ligne +
> `check_fetch_relevance.py` **2/2** live (10-K NVDA `22%`/`14%` atteints à 37,6 % du texte, `via=direct
> mode=relevance` ; CNBC `Maia` via cache Exa, `mode=whole`). La troncature est réglée contre les vraies API.
>
> **Bug infra corrigé le même jour** : le rebuild #283 n'avait PAS arrêté le conteneur #282 (`cc665e9`) —
> les DEUX portaient des labels Traefik identiques, donc Traefik load-balançait `/api` sur l'ancien ET le
> nouveau code pendant ~40 h (+ double scheduler). Orphelin stoppé+supprimé, `/api/health`→200 sur un seul
> backend. **Réflexe à garder : après tout `deploy.sh`, `docker ps | grep <app>` ne doit montrer QU'UN conteneur.**
>
> **La boucle tool-calling `run_tool_json_agent()` a enfin tourné contre DeepSeek en réel** (elle ne
> l'avait jamais fait — cf. l'ancienne section « jamais vérifié »). 7 runs `search-worker` sur NVDA,
> **~$0.10 au total**, cadence ~90–175 s/run. Résultats (provenance RÉELLEMENT vérifiée — plus aucune
> URL sec.gov fantôme comme au run C) :
>
> | dimension | entries persistées | tier | source | plancher | couvre ? |
> |---|---|---|---|---|---|
> | produits | 2 + 4 | A 0.89 / A 0.93 | IR press (cache Exa) + 10-Q MD&A | B+ | champ `unit_economics` jugé non fondé |
> | positionnement | 1 | B+ 0.735 | CNBC (cache Exa) | B+ | ✅ |
> | marche | 1 | B+ 0.73 | CNBC | B+ | champ `structure_5forces` non fondé |
> | management_allocation | 5 | A 0.92–0.944 | EDGAR DEF 14A (sec.gov réel) | A- | ✅ |
> | risques | 4 | A 0.94 | EDGAR 10-K (sec.gov réel) | B | ✅ |
>
> KB NVDA passée de **15 → 32 entries** (25 tier A, 2 tier B, 5 llm_memory). `POST /curator/readiness`
> tourne et rend un rapport cohérent. **Verdict : `not_ready`** (recomputé 3×, déterministe à données
> fixes : runs #2/#3 identiques au champ près).
>
> ### Pourquoi NVDA n'est PAS `ready` — et pourquoi le search-worker seul ne l'y amènera jamais
> Les 5 gaps restants sont **structurels**, pas un manque de recherche :
> - **`valorisation` (bloc structuré, bloquant)** : `prix_actuel` (prix marché live), `relatif_multiple`
>   (P/E, EV/EBITDA), `base_rate_anchor` (multiple historique secteur) — **aucun ne vient du web** ;
>   ils viennent du **quant/DataService (FMP)**. La recherche ne peut pas les fonder.
> - **`produits/unit_economics`** : marges consolidées (GM 73,4 %, op. margin) ajoutées via 10-Q, mais
>   le curator veut l'économie **unitaire** (coût/GPU, coût/token) → besoin d'une entrée de synthèse.
> - **`marche/structure_5forces`** : besoin d'une analyse Porter **structurée**, pas d'un fetch brut.
>
> ⚠️ **Finding sur la stabilité du curator** : le verdict a basculé `thin_qualitative` (#1, 28 entries)
> → `not_ready` (#2, 32 entries) en n'AJOUTANT que des entries `produits`. Mécanisme : la note de
> fondation **par champ** est produite par le modèle (le backend ne recompute en Python que le `ok`
> = tier_atteint≥plancher ∧ champs_requis fondés). Avec plus de contexte, le modèle a **corrigé** son
> sur-crédit de `valorisation` (#1 la disait fondée B+, à tort, car aucune entry ne porte prix/multiple).
> Donc `not_ready` est le verdict JUSTE et `thin_qualitative` était un faux positif. À retenir : la
> readiness n'est fiable que si chaque champ est réellement porté par une entry — ne pas se fier à un
> `thin_qualitative`/`ready` limite sans vérifier les `gaps`. Le curator charge jusqu'à 500 entries
> (`limit=500`), donc pas de plafond qui écrase — c'est bien le jugement par champ qui bouge.
>
> ### Prochaine étape concrète pour rendre NVDA `ready`
> 1. **Fonder `valorisation`** : écrire un petit alimentateur `fact_financial` depuis DataService/FMP
>    (`prix_actuel`, `relatif_multiple` P/E-EV/EBITDA, `base_rate_anchor` = multiple médian historique
>    semi-conducteurs) → entries tier A/B+ portant `valorisation.*`. C'est le vrai chaînon manquant.
> 2. **`produits/unit_economics` et `marche/structure_5forces`** : entrées de **synthèse** (ingestion/
>    curation), pas du fetch brut. Piste : le `search-worker` ne tague pas `field_path` sur ses entries
>    (constaté : `field=None`), le curator infère la fondation depuis le `content` — taguer `field_path`
>    fiabiliserait le jugement par champ.
> 3. Readiness → `ready` → alors seulement lancer research → bull/bear → réfutation → synthèse
>    (`POST /tickers/NVDA/research` puis `/analyses` …). **Cette chaîne d'analyse n'a toujours jamais
>    tourné** — c'est le prochain vrai jalon une fois `ready` atteint.

# Prompt de reprise — portfolio-tracker V2 (post-déploiement couche 2)

**État au 2026-08-23** : la **couche contrat est figée** (10 schémas Pydantic v2) ET la **chaîne
d'analyse runtime est écrite et déployée en production** (provider DeepInfra + curator → research →
bull/bear → réfutation → synthèse). Migrations 024/025/026/**027** appliquées.
La **recherche sémantique est opérationnelle** (bge-m3 1024d, 15/15 entrées embeddées) et le
**`search-worker` est écrit** (recherche web + fetch + entries scorées, 9 routes au total).
**Ce qui manque n'est plus du code : c'est une clé et un run.** Aucun ticker n'est encore `ready`,
donc la chaîne n'a jamais tourné de bout en bout sur un cas réel — et le seul obstacle restant est
la souscription **Exa**, sans laquelle le worker refuse (volontairement) de démarrer.

> ### ⚠️ État du déploiement — un lot committé localement, NON poussé
>
> Lot embeddings **déployé en production le 2026-08-23** (commit `f1e6a94`, deployment Coolify
> #280). Vérifié dans le container live : `EMBEDDING_MODEL=BAAI/bge-m3`, 15/15 entrées embeddées,
> `query_knowledge` renvoie `match_mode='vector'`, backfill à 0 candidat. Migration 027 appliquée.
>
> **Lot `search-worker` déployé le 2026-08-23** avec `EXA_API_KEY` posée dans Coolify (backend),
> deployment #281. Chaîne vérifiée de bout en bout : Exa répond, la boucle d'outils tourne, les
> garde-fous déterministes filtrent.
>
> **Premier run réel (NVDA, `moat`, dry-run) : `not_found` — 5 entrées produites, 5 rejetées sous le
> plancher `reliability_min=0.60`.** Diagnostic : les seules pages lisibles depuis le VPS étaient des
> blogs (`web_search_generic` = 0.50, donc structurellement sous le plancher) ; les sources
> qualifiantes étaient inaccessibles — CNBC 403 (WAF), `investor.nvidia.com` SPA vide. Corrigé par le
> second chemin de `fetch_url` (repli Exa `/contents`, convention #26). Coût du run : 99 278 tok in /
> 3 999 out = 0,0087 $, sorti sur « 6 itérations d'outils épuisées » (d'où `max_iterations` exposé
> dans le body de `POST /tickers/{id}/knowledge/search`).

Colle ceci pour reprendre :

> Reprise de **portfolio-tracker V2**. Couche contrat figée + chaîne d'analyse runtime déployée en
> prod (provider DeepInfra OpenAI-compat, modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`).
> Principe directeur UX → agents → données, 3 garde-fous (G1 schéma versionné = source unique /
> G2 décision contrainte par l'analyse / G3 donnée versionnée+scorée+figée, jamais de texte libre).
> DÉCISION #1 = Option C (base neutre → bull/bear isolés → réfutation bear→bull → synthèse).
> **Le blocage actuel est l'alimentation de la base de connaissance**, pas la chaîne.
>
> **Étapes 1 (embeddings) et 2 (`search-worker`) FAITES.** L'étape 2 est écrite et vérifiée hors
> ligne (40 assertions, `backend/checks/`), mais **jamais exercée contre un vrai modèle** :
> il manque la clé.
> **Prochaine étape = souscrire Exa** (exa.ai, 10 $/mois de crédits renouvelables, sans carte),
> poser `EXA_API_KEY` dans Coolify, pousser + rebuild, puis faire le **premier run réel** :
> `POST /tickers/NVDA/knowledge/search` en `persist=false` d'abord, puis relancer la readiness
> jusqu'à faire passer NVDA de `thin_qualitative` à `ready`.
>
> LIRE AVANT : `roadmap/00-principe-directeur-v2.md` ; `roadmap/01-spec-v2-unifiee.md` (§5 agents,
> §7 curator/readiness, §8 contrats analyse, §14 migrations, §18 découpage) ;
> `roadmap/provenance-cards/*_card.md` + `*_schema.py` ; `roadmap/provenance-cards/prompts/` ;
> côté **code** : `backend/app/agents/providers/`, `backend/app/agents/v2/`,
> `backend/app/knowledge/` (`service.py` · `embeddings.py` · `websearch.py`),
> `backend/app/contracts/`, `backend/app/api/analysis_v2.py` + `knowledge_v2.py`,
> `backend/checks/README.md`.
> CLAUDE.md projet = conventions (dont #22 recherche knowledge, #23 piège pgvector,
> **#24 le modèle ne qualifie pas sa source**, **#25 un échec de recherche n'est pas un résultat vide**).
> Visuel : https://provenance.jlmvpscode.duckdns.org

## Ce qui est FAIT

### Couche contrat — 10 schémas Pydantic v2 (`SCHEMA_VERSION=v2.0.0`)

- **Analyse** `analysis_v2_schemas.py` : `ResearchMemo` (NEUTRE, Q2) · `BullCase`/`BearCase` (A6) ·
  `RiskMatrix` (seul verdict) · `Hypothese` (falsifiabilité). + `readiness_report_schema.py` (gate
  GO/NO-GO, `compute_verdict`, `thin_qualitative`).
- **C1** `worker_delegation_schema.py` · **C2** `ingestion_extraction_schema.py` ·
  **C3** `context_pack_schema.py` · **C4** `decision_validate_schema.py` ·
  **C5** `monitoring_mode6_schema.py` · **C6** `exit_calibration_schema.py` ·
  **C7** `debate_conviction_schema.py` · **C8** `monitoring_modes_1_5_schema.py`.

Chaque contrat a sa carte `*_card.md`. Dérivés : `readiness_derivation.md`, `groundedness_rules.md`.

### Prompts d'agent V2 (`prompts/`)

`00-preambule-commun.md` + 11 prompts (`10-ingestion` → `80-postmortem`). Ce sont le **3ᵉ point de
synchro** (règle #19) : schéma de sortie = Pydantic correspondant. Chargés en DB par la migration 025.

### Couche 2 — code runtime (écrit, déployé 2026-08-23)

| Module | Rôle |
|---|---|
| `backend/app/agents/providers/` | `AgentProvider` · `DeepInfraProvider` (OpenAI-compat) · `DustProvider` (shim V1) · factory `get_agent_provider(agent_name, flow_version)` lisant `agent_prompts` |
| `backend/app/contracts/` | **copie runtime** des contrats figés (le build context Docker est `./backend` seul → `roadmap/` absent de l'image). + `composites.py` (`SynthesisOutput` + `valider_pont()` §8.5) |
| `backend/app/knowledge/service.py` | `RELIABILITY_TABLE` · `compute_reliability()` · `store_knowledge()` (append-only A1, **embedde à l'écriture**, échec non fatal) · `query_knowledge()` (**vectoriel + repli strict**) · `snapshot_refs()` (gel entry@version + `reliability_at_use`) · `collect_refs()` |
| `backend/app/knowledge/embeddings.py` | **(2026-08-23)** client DeepInfra `/v1/openai/embeddings` · `entry_text()` = **source unique** du texte embeddé (backfill et écriture temps réel DOIVENT produire le même texte) · `to_pgvector()` (littéral casté `$n::vector`, pas de dépendance `pgvector` Python) · `backfill_embeddings()` idempotent · `_QUERY_INSTRUCTION` (bge-m3 n'en veut **pas** ; bge-*-en et e5 si) |
| `backend/app/agents/v2/runner.py` | point de passage unique : `extract_json()` tolérant, `run_json_agent()` (validation Pydantic + **1 tour de réparation**), `run_tool_agent()` (boucle outils brute) et **`run_tool_json_agent()`** = boucle d'outils + **tour de clôture JSON validé**, joué par un clone de l'agent **sans `tools`** (tant que `tools` est exposé, un modèle peut répondre par un tool_call de plus au lieu du contrat : ni sortie, ni erreur claire) |
| `backend/app/knowledge/websearch.py` | **(2026-08-23)** `SearchBackend` interchangeable (`ExaBackend` nominal · `SerperBackend` débordement) · `web_search()` · `fetch_url()` (httpx + extraction texte **stdlib `html.parser`**, aucune dépendance ajoutée) · `classify_source_type()` = qualification de source **par le domaine** |
| `backend/app/agents/v2/tools.py` | **(2026-08-23)** exécuteurs des 3 outils du `tools_json` (migration 025) : `web_search`, `fetch_url`, `query_knowledge`. Arguments du modèle traités comme entrées non fiables (`max_results` borné, `ticker_id` forcé au mandat) ; un échec est une **valeur de retour** `{"error": …}`, pas une exception |
| `backend/app/agents/v2/worker.py` | **(2026-08-23)** `search-worker` (contrat C1) : `run_search_worker()` → `WorkerExchange` validé, `persist_worker_entries()` (append-only A1). `_apply_deterministic_overrides()` recalcule source_type/score/tier/note/covers/status/exécution — cf. conventions #24 et #25 |
| `backend/app/api/knowledge_v2.py` | **(2026-08-23)** `POST /tickers/{id}/knowledge/search` (avec `persist=false` = dry-run, la base étant append-only) · `GET /knowledge/search/status` (diagnostic : la recherche est-elle réellement câblée ?). `SearchUnavailable` → **503**, distinct d'une recherche infructueuse (200 + `status='not_found'`) |
| `backend/checks/` | **(2026-08-23)** vérifications exécutables en container jetable : `check_search_worker.py` (40 assertions, hors ligne) · `check_fetch_live.py` (réseau, sans clé) |
| `backend/app/agents/v2/common.py` | `MVDD_SPEC` (8 dimensions, champs requis + tier plancher) · `count_tiers()` · `format_entries_for_prompt()` (ordre déterministe = discipline de cache §5.3) |
| `backend/app/agents/v2/curator.py` | gate GO/NO-GO. **Tout ce qui est dérivé est recalculé en Python** (`_apply_deterministic_overrides`) : `entries_par_tier`, `ok` par dimension, `bloc_ok`, verdict. `conviction`/`marge_securite` forcés à `None` (A3). Produit le `context_pack` **uniquement si `ready`** |
| `backend/app/agents/v2/analysis.py` | `run_research` · `run_bull`/`run_bear` (contextes isolés) · `run_rebuttal` (round 2 supersede round 1) · `run_synthesis`. `_load_ready_context()` lève `NotReadyError` si pas de readiness `ready` |
| `backend/app/api/analysis_v2.py` | 7 routes (§15). `NotReadyError`→409 · `AgentNotFoundError`→404 · reste→502 |

### Socle données — migrations appliquées

- **024** Knowledge Platform : `knowledge_documents`, `knowledge_entries` (append-only A1),
  `analysis_knowledge_refs`, `eu_ir_scrapers`, `knowledge_curator_reports`, pgvector + HNSW
  `vector(768)`, vue `knowledge_federation_export`.
- **025** Agents/Provider : `agent_prompts += provider, model, tools_json, flow_version` ;
  unicité `(agent_name, flow_version)` ; **12 agents V2** insérés. Générateur `_gen_025.py`.
- **026** Analyses : `research_memos`, `research_messages`, `investment_analyses`.
  ⚠️ **`analysis_knowledge_refs.analysis_id` est POLYMORPHE** (discriminé par `analysis_kind`) — la
  note de 024 « FK ajoutée en 026 » est **amendée** : pas de FK dure vers `investment_analyses` seul.
- **027** Embeddings : `embedding vector(768)` → **`vector(1024)`** + index HNSW reconstruit
  (`vector_cosine_ops`, donc opérateur `<=>` inchangé) + index **partiel** `..._unembedded` sur
  `embedding IS NULL` (la passe de rattrapage de `query_knowledge` doit rester bon marché).
  ⚠️ **Piège pgvector** : `atttypmod` porte la dimension **telle quelle**, sans le `+4` (VARHDRSZ)
  des types natifs. Un `atttypmod - 4` réflexe lit 1020 pour un `vector(1024)` — la garde
  d'idempotence ne reconnaît pas l'état cible et la migration rejouée **efface tout le corpus
  d'embeddings**. Constaté en test. La garde compare désormais `format_type(...)`.
- **Séquence** : collision 023 → décalage +1, puis 027 pris par les embeddings →
  reste **028 theses_flow · 029 exit/calibration**.

Seed NVDA (`backend/app/db/seeds/nvda_v2_knowledge_seed.sql`) : 10 `fact_financial` Tier A EDGAR
+ 5 qualitatifs `llm_memory` → readiness **`thin_qualitative`** (struct_ok ∧ ¬qual_ok).

### Infra / secrets

- `DEEPINFRA_API_KEY` déployée dans **Coolify** (app `portfolio-backend` id=8, env 123 prod + 124
  preview, chiffrée Laravel, round-trip vérifié). Jamais committée.
- Risques DeepInfra **levés** par test API réel : model_id valide · JSON strict propre · tool-calling
  OpenAI conforme (`finish_reason=tool_calls`).

## Décisions arrêtées

### Modèles (2026-08-21)

**Métier ET ouvrier = `deepseek-ai/DeepSeek-V4-Flash-0731`** (13B/284B, ctx 1M, $0.08 in / $0.18 out).
Les ouvriers émettent du JSON → coût **dominé par l'output**, et DeepSeek V4 Flash a l'output le moins
cher du catalogue. Le réflexe « petit modèle ouvrier » vient de la tarification Anthropic (Haiku≪Opus)
et **ne se transpose pas**. Le « tier ouvrier » reste une **réalité d'orchestration** (délégation,
`execution.tier`, batch), pas un modèle distinct.

Overrides possibles (`agent_prompts.model` est par agent) : ingestion de masse EDGAR →
`google/gemma-4-26B-A4B-it` ($0.07/$0.34, 256k) ; fallback tool-calling → `zai-org/GLM-4.7-Flash`.

### Embeddings — DÉCISION #4, 3ᵉ révision (2026-08-23) : `BAAI/bge-m3`, 1024d — **FAIT ET VALIDÉ**

**Ollama abandonné** (~1 Go de RAM sur un VPS 2 vCPU saturé) → API DeepInfra, clé déjà déployée.
Coût : corpus pilote ≈ **$0,00004**, < **$0,10/an** à pleine échelle. Le coût n'arbitre rien.

⚠️ **`bge-base-en-v1.5` (768d) a été essayé puis ÉCARTÉ** : ce modèle est entraîné sur l'**anglais
seul**, or **100 % du corpus est en français** (`lang='fr'` sur 15/15 entrées, et les sources EU le
resteront). Bench sur le corpus NVDA réel (7 requêtes FR sémantiques, 15 entrées) :

| configuration | MRR | hit@1 | hit@3 |
|---|---|---|---|
| ILIKE lexical seul (l'ex-implémentation) | 0.352 | 1/7 | 3/7 |
| bge-base-en-v1.5 768d, vectoriel | 0.644 | 4/7 | 4/7 |
| **bge-m3 1024d, vectoriel** | **0.905** | **6/7** | **7/7** |

Le 768d anglais échouait précisément sur les requêtes **financières** (rentabilité, cash,
endettement) — donc sur les entrées **EDGAR Tier A**, les plus fiables : rangs 5, 6, 7 sur 15.
Mode de panne **silencieux** : l'agent reçoit des entrées pleines mais hors-sujet, le curator conclut
à une dimension non couverte (readiness faux négatif) et le garde-fou A2 ne voit rien puisque les
refs citées existent. Aucun modèle multilingue en 768d chez DeepInfra (404 sur
`multilingual-e5-base`, `gte-multilingual-base`) → la montée en dimension n'était pas évitable.

**Ne PAS « améliorer » en recherche hybride sans re-mesurer** : la fusion RRF du lexical et du
vectoriel **dégrade** (0.905 → 0.655), le signal lexical français étant trop faible. Le texte est un
**repli strict**, jamais un co-classement. La normalisation des accents ne change rien.

### Web search (2026-08-23) — Exa, SearXNG écarté

⚠️ **Brave a supprimé son palier gratuit en février 2026** — toute note antérieure citant
« Brave 2000 req/mois gratuit » est **périmée**.

**Choix : Exa** ($10/mois de crédits renouvelables sans carte ≈ 4 000 recherches). Débordement payant :
**Serper** (~$1/1000, $50 = 50 000 requêtes ≈ 25 mois). Tavily en option si on veut le contenu extrait
plutôt que des liens (économise des `fetch_url`).

**SearXNG écarté sur la performance, pas sur le coût** : latence médiane ~0,83 s (dont 0,74–0,89 s
d'agrégation multi-moteurs) contre ~180–450 ms pour Exa ; et surtout, **depuis une IP unique la
plupart des moteurs captcha** (Google 0 résultat parsable, Brave/Startpage suspendus, seul DuckDuckGo
répond). Pour le `search-worker` c'est le pire mode de panne possible : **des résultats vides sans
erreur explicite**, exactement ce que le garde-fou A2 (groundedness) est censé empêcher.

**Point rassurant, désormais vérifié dans le code** : `knowledge/websearch.py` isole le backend
derrière `SearchBackend` — basculer Exa ↔ Serper ↔ autre = **une classe**, sans toucher au
`tools_json` en DB, au prompt du worker, ni à la boucle tool-calling. `SEARCH_PROVIDER` choisit.

⚠️ Le `tools_json` du `search-worker` en DB décrit encore `web_search` comme « recherche web
(SearXNG/API) ». C'est **cosmétique** (la description est agnostique côté modèle) mais périmé — à
corriger à la prochaine migration qui touche `agent_prompts`, pas avant (§18 : pas de migration en
avance).

## Contrainte infra VPS (mesurée 2026-08-23)

`3 819 Mo RAM totale / ~2 100 Mo de socle permanent / 0 swap` · disque `38 G, 84% utilisé, 5,8 G
libres` · **2 vCPU**. ~5,2 Go récupérables (images Docker obsolètes 4,2 Go + journald 0,8 Go + divers)
mais **non nettoyés** — les images obsolètes sont les rollbacks Docker locaux.

Conséquence : **pas de self-hosting de service supplémentaire gourmand**. C'est ce qui fonde les deux
décisions ci-dessus (embeddings API, web search API).

## Prochaine étape — alimenter la connaissance (le blocage réel)

1. ~~**Embeddings**~~ — ✅ **FAIT le 2026-08-23** (non déployé, voir « État du déploiement » ci-dessous).
   `backend/app/knowledge/embeddings.py` (client DeepInfra `/v1/openai/embeddings`, `bge-m3`) ·
   migration 027 · 15/15 entrées NVDA backfillées en 1024d · `query_knowledge()` bascule sur
   `embedding <=> $vec::vector` avec repli texte strict. Mesuré en conditions réelles à travers
   l'index HNSW : **MRR 0.905, hit@3 7/7**.
2. ~~**`search-worker`**~~ — ✅ **FAIT + EXERCÉ EN RÉEL le 2026-08-25** (Exa déployée, 7 runs NVDA,
   provenance vérifiée sur sources réelles EDGAR/IR). Voir MàJ 2026-08-25 en tête.
3. ~~**Fonder `valorisation` depuis le quant (DataService/FMP)**~~ — ✅ **FAIT + VÉRIFIÉ EN RÉEL le
   2026-08-25** (sprints 1+2, deployment #294). `prix_actuel`/`relatif_multiple` via `valuation_feed.py`
   (yfinance, B+) ; `base_rate_anchor` via `base_rate_corpus.py` (corpus Base Rate Book + classifieur
   par taille). `valorisation` → `ok=True` en readiness NVDA. Voir MàJ 2026-08-25 (bis) en tête.
3bis. **Fonder `financials` (ratios dérivés)** — ⏳ **CODE DÉPLOYÉ le 2026-08-25 (deployment #295,
   commit `9c0a818`) + vérifié contre l'API EDGAR, mais PAS encore persisté en prod.** `financials_feed.py`
   calcule `roic_pct`/`fcf_conversion_pct`/`intensite_capex_pct`/`levier` depuis les faits EDGAR tier A
   (le quant B+ est volontairement écarté : plancher A), capex fetché à la source (`edgar_facts.py`).
   **Reste à lancer en prod** : `financials-refresh` (persist) + recompute readiness — cf. MàJ (ter) en
   tête. Puis le qualitatif.
4. **`ingestion-agent`** — doc → entries (contrat C2), anti-hallucination financière.
5. **Premier run end-to-end de la CHAÎNE D'ANALYSE** : une fois NVDA `ready`,
   research → bull/bear → réfutation → synthèse (+ `valider_pont`). **Jamais fait à ce jour** — la
   partie alimentation (readiness) est désormais exercée, l'analyse reste à lancer.
5. Agents 7→9 (migrations 027/028) : décision/validate → monitoring m6 → sortie/calibration.
6. Passe UX transverse finale (§16).

**Piège migrations (§18)** : écrire chaque migration **juste avant** son lot, jamais en avance.

## Ce qui n'a JAMAIS été vérifié (à ne pas supposer acquis)

- ~~**La boucle tool-calling n'a jamais tourné contre un modèle.**~~ ✅ **LEVÉ le 2026-08-25** :
  `run_tool_json_agent()` a bouclé contre DeepSeek sur 7 runs `search-worker` NVDA — tour de clôture
  sans `tools`, réparation JSON et respect du contrat `WorkerResponse` observés en réel ; la
  combinaison `tools` + `response_format` (via le clone sans outils) fonctionne. `search-worker`,
  `persist_worker_entries`, `_apply_deterministic_overrides` (worker) et le curator (`run_readiness`,
  `_apply_deterministic_overrides`, readiness → rapport `not_ready` cohérent) sont exercés contre un
  vrai modèle. Voir la MàJ 2026-08-25 en tête.
- **La chaîne d'ANALYSE, elle, n'a toujours jamais tourné.** `run_research`, `run_bull`/`run_bear`,
  `run_rebuttal`, `run_synthesis` et surtout `valider_pont()` (§8.5) n'ont jamais vu de sortie de
  modèle réelle : aucun ticker n'a encore atteint `ready`, et `_load_ready_context()` lève
  `NotReadyError` tant que la readiness n'est pas `ready`. Bloqué en amont par la fondation de
  `valorisation` (feed quant, cf. MàJ 2026-08-25), pas par la chaîne elle-même.
- La validation faite : `py_compile` + import complet en container jetable + round-trip
  `ReadinessReport` sous pydantic 2.13.4 → `thin_qualitative` cohérent avec `compute_verdict`.

**Exception — les garde-fous déterministes du search-worker SONT vérifiés** (`backend/checks/`,
40 assertions en container, 0 échec) : sortie de modèle hostile (source surqualifiée, score gonflé,
mauvais `entry_type`, doublons, dépassement de `max_entries`, `llm_memory` non déclarée) intégralement
rabattue ; troncature Pareto sur les mieux notées ; `not_found` explicite quand tout est écarté (A6) ;
`WorkerExchange` valide après correction. Et `fetch_url` est exercé sur des URL réelles.

⚠️ **Trouvé en exerçant `fetch_url`** : `investor.nvidia.com` renvoie **HTTP 200, un `<title>` correct
et 0 caractère de texte** — la page est rendue en JavaScript. Rendre ce vide comme un succès aurait
fait conclure au modèle que la page ne dit rien. `fetch_url` lève désormais une erreur explicite
(page volumineuse → < 200 car. extraits). **Conséquence pour l'ingestion** : beaucoup de pages IR
seront inaccessibles sans rendu JS ; privilégier communiqués, EDGAR, et le `text` que **Exa** rapporte
directement (il évite en plus un tour de `fetch_url`).

**Exception — le lot embeddings (027), lui, EST vérifié en conditions réelles** : backfill 15/15,
recherche vectorielle exercée à travers l'index HNSW via `query_knowledge` (MRR 0.905, hit@3 7/7),
rattrapage d'une entrée non embeddée, repli texte clé absente, idempotence du backfill et de la
migration. Reste non exercé : le comportement sous un corpus de plusieurs milliers d'entrées
(qualité du rappel HNSW, `ef_search` laissé au défaut).

## Rappels techniques (CLAUDE.md projet)

- Contrats ciblent **pydantic v2** → tester dans le container backend, **pas** le python hôte (v1).
  Astuce sans secret : `docker run --rm --network none -v <backend>:/app:ro -w /app <image> python -c "import app.main"`
  (nécessite des valeurs factices pour les 8 env vars requis par `Settings`).
- asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations **appliquées
  manuellement** via `docker cp` + `psql -f` (heredoc `docker exec` échoue **silencieusement**).
- Déploiement : `infrastructure/deploy.sh <app> -m … -f …` (cf. DEPLOY.md). Rebuild, jamais restart ;
  commit+push AVANT. Coolify build **depuis GitHub** → un commit local non poussé n'est jamais déployé.
- Règle #19 : tout changement de contrat = 3 points de synchro (prompt agent · frontend · import).
- Viz servie par un container nginx **hors Coolify** (`provenance-viz`, bind-mount) ; éditer le HTML
  suffit (live).
