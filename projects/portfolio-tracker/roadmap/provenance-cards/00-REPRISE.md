---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-09-09
project: portfolio-tracker
role: >
  Prompt à coller pour reprendre le chantier V2. Contrat FIGÉ · couche 2 DÉPLOYÉE · boucle V2
  complète (décider → surveiller → sortir → apprendre) · écrans UX-1/2/3 livrés · chaîne exercée
  sur NVDA, MSFT et RVMD. État au 2026-09-09 : **1 858 assertions / 0 échec / 22 scripts**,
  migrations appliquées jusqu'à **035**, prochaine **036**.
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

**Ce que la v3 change** : `frameworks` + `framework_questions` en **base** (le vocabulaire cesse
d'être une constante Python), `covers` devient une **clef étrangère** vers une question existante
(l'écart « tag hors vocabulaire → écarté » devient impossible **par construction**), et chaque
framework est **garanti par un manager** dont l'autorité s'exerce par 4 contrôles vérifiables
(complétude · fondation · honnêteté de l'approximation · non-substitution). Son **renvoi** produit
un **mandat de recherche exécutable** — ce qui ferme la boucle comité → collecte, aujourd'hui
absente.

**Deux pilotes**, choisis pour un contraste maximal de matière disponible :

- **« Qualité financière »** (quantitatif, étape 5, Greenwald) — *ses ingrédients sont déjà en
  base* : les 26 orphelines de NVIDIA en sont littéralement la matière. Il prouve qu'on sait
  **ranger** ce qui existe.
- **« Défendabilité / moat »** (qualitatif, étape 4, Porter-Morningstar) — *ses 4 champs de sortie
  sont 100 % orphelins d'indexation aujourd'hui*. Il prouve qu'on sait **faire chercher** ce qui
  n'existe pas.

### 🚦 Prochain pas — **lot 0 : la ligne de base**

**Rien d'autre ne commence avant.** `feedback_ligne_de_base_est_une_mesure` : l'état de départ d'un
test d'acceptation se **requête AVANT** le lot. Sur ce chantier, la ligne de base a déjà changé le
lot **trois fois de suite** (capacité 4 visait le mauvais émetteur ; capacité 5 a visé deux fois un
mécanisme sans matière).

Trois livrables, aucun n'appelle un modèle :

1. **Versionner** `/tmp/vocab.py` → `tools/reconcilier_vocabulaires.py`. Il **doit rougir
   aujourd'hui** (14 orphelins + 3 inutilisés) et virer au vert au lot 3 : c'est un test négatif
   déjà éprouvé.
2. **Consigner** les 6 valeurs du tableau ci-dessus, requêtées et non recopiées.
3. **Écrire** `tools/acceptation_frameworks.py` + son `.sh`, avec ses 8 critères T1-T8
   (spec v3 §9.2), **qui rougit sur les 8**.

⚠️ Mesureurs **versionnés**, jamais `/tmp` · bilan reconnaissable à sa **forme** (`grep -E` sur le
motif, jamais `tail -1` ; absence de bilan = **échec**) · **jamais exécutés dans
`portfolio-backend`** (il porte le code déployé, qui peut précéder ce qu'on mesure).

### Découpage des lots suivants (spec v3 §10)

| Lot | Contenu | Migration |
|---|---|---|
| 0 | **Ligne de base** (ci-dessus) | — |
| 1 | Contrat `FrameworkAnswer` + `FrameworkMandate`, invariants relationnels **en Python** (#37), écran niveau 3 en maquette | — |
| 2 | Les 2 pilotes et leurs 13 questions écrits **comme données** · analyste + manager sur `qualite_financiere` | — |
| 3 | Le **vocabulaire unique** en base · FK depuis `covers` · backfill relu · **suppression** de `MVDD_SPEC`, `SYNTHESIS_TARGETS`, `DECLARED_NONBLOCKING_GAPS` | **036** |
| 4 | Le **manager** et ses 4 contrôles · le renvoi qui produit un mandat consommé par `search-worker` | 037 |
| 5 | Le `research_memo` devient la **projection** des frameworks acquittés · réconciliation à 0/0 | 038 |
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
  `(ticker_id, question_id)` (violation #31 aujourd'hui : une dispense en source Python exige un
  redéploiement pour adapter la grille à une entreprise).
- **Hybridation RRF de la recherche** — reste **interdite** (mesurée dégradante, MRR 0,905 → 0,655).

---

## Où on en est (2026-09-09)

**Le système est exercé, pas prototypé.** La chaîne complète a tourné de bout en bout sur trois
émetteurs, et on connaît ses modes de panne — c'est le principal actif du chantier.

| | NVDA (cas-pilote) | MSFT (généralité) | RVMD (banc d'essai) |
|---|---|---|---|
| Socle | 52 entries (32 A / 15 B) | 51 entries, 19/19 champs, 0 `llm_memory`, ≈ $0,19 | 27 actives (13 déterministes + 14 qualitatives) |
| Readiness | **`not_ready (peremption)`**, 9 champs périmés, 7 mandats, **0 collecte** | **`not_ready (peremption)`**, 9 champs périmés, **0 collecte** | **rapport #28** — `not_ready`, **9 collecte / 4 rafraîchissement** |
| Chaîne | research → bull/bear → réfutation → synthèse = `PROCEED_AVEC_CONDITIONS` | idem, ≈ $0,018 | **0 synthèse grounded** — 3 des 4 cibles vides |

- **Suite hors-ligne : 1 858 assertions / 0 échec / 22 scripts** — une seule commande,
  **`bash checks/run_all.sh`**. Il porte les invocations correctes : montage `/contract_frozen`
  (sans lui 4 scripts sous-comptent en sortant à 0) et réseau `coolify` + `CHECK_DB_URL` pour
  `check_entry_nature` (§7) **et** `check_edgar_feed` (§12bis) — tous deux **sortent en échec** si
  le pré-requis manque, jamais un saut de section. ⚠️ **Ne pas le réécrire dans `/tmp`** : la
  version jetable sous-comptait 47 assertions en silence (`CHANTIER_OUTILLAGE_DEV.md` §27).
- **Migrations appliquées jusqu'à 035. Prochaine : 036.**
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
> La v3 remplace la grille par des **frameworks stables à variables par entreprise** : le vocabulaire
> passe en base (`frameworks` + `framework_questions`), `covers` devient une **clef étrangère** — le
> tag hors vocabulaire devient impossible **par construction** — et chaque framework est garanti par
> un **manager** aux 4 contrôles vérifiables (complétude · fondation · **honnêteté de
> l'approximation** · **non-substitution**), dont le **renvoi produit un mandat de recherche
> exécutable**, ce qui ferme la boucle comité → collecte aujourd'hui absente. Deux pilotes :
> **« Qualité financière »** (Greenwald — les 26 orphelines de NVDA en sont la matière) et
> **« Défendabilité / moat »** (Porter-Morningstar — ses 4 champs de sortie sont 100 % orphelins).
> **La capacité 5, barreau 4 est FERMÉE** : réfutée **4 fois** par sa ligne de base ; le contre-test
> montre que la formulation n'est pas en cause. L'ingrédient (#33) est **orphelin**, donc hors du
> corpus du champ — *le barreau 4 ne compense pas une limite de la recherche, il compense un défaut
> de rangement*, et c'est le rangement que la v3 corrige.
> 🚦 **PROCHAIN PAS = lot 0, la ligne de base, et rien d'autre avant.** Versionner
> `tools/reconcilier_vocabulaires.py` (il **doit rougir** : 14 + 3), consigner les 6 mesures,
> écrire `tools/acceptation_frameworks.py` avec ses 8 critères T1-T8 **qui rougissent**. Aucun appel
> modèle. ⚠️ Sur ce chantier la ligne de base a **déjà changé le lot trois fois** — elle se
> **requête**, elle ne se souvient pas. ⚠️ Mesureurs versionnés, jamais `/tmp` ; bilan reconnaissable
> à sa **forme** ; **jamais exécutés dans `portfolio-backend`**.
> État : suite hors-ligne **1 858 / 0 / 22**, migrations jusqu'à **035**, prochaine **036** (à écrire
> juste avant son lot).
> LIRE D'ABORD : ce fichier, puis `roadmap/03-spec-frameworks.md` (§1 = ce qui n'est PAS défait),
> le `CLAUDE.md` du projet (conventions #22-**#55**), `00-REPRISE-ARCHIVE.md` si le *pourquoi* d'une
> décision manque.
