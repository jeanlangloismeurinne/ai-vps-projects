---
id: spec-v2-unifiee
status: spec-decisions-prises (toutes tranchées — DÉCISION #1 incluse, 2026-08-17)
created: 2026-08-11
project: portfolio-tracker
role: >
  Consigne unique de mise en place de l'Architecture V2. Fusionne :
  - 00-principe-directeur-v2.md (constitution — prime sur tout)
  - roadmap-1786358823158-architecture-v2-knowledge-platform.md (spec Knowledge Platform + bull/bear)
  - roadmap-1786304902922-refonte-flux-investissement-processus-fonds.md (spec flux screening/research)
  - audit-roadmap-1786358823158-...md (audit du flux LT + auditabilité)
  Destinée à être découpée en tickets par un agent aval, selon l'ordre UX → agents → données.
downstream: >
  Le découpage en tickets suit le principe de développement : pour chaque capacité,
  d'abord le contrat d'affichage (UX + schéma JSON), puis l'agent qui le produit,
  puis les données qui l'alimentent. Voir §18.
---

# Spec V2 unifiée — Portfolio Tracker

> **Comment lire ce document.** Le §0 liste les décisions à trancher (les deux specs
> sources divergent — il faut choisir). Les §1–§17 sont la spec réconciliée, écrite dans
> l'hypothèse retenue. Le §18 explique comment la découper en tickets. **Toutes les décisions #1–#5 sont prises** (#2–#5 le 2026-08-11, #1 le 2026-08-17) ; les marqueurs `⚠` de suspens ont été retirés.
>
> **La constitution (`00-principe-directeur-v2.md`) prime.** En cas de contradiction
> entre ce document et le principe directeur, c'est le principe qui gagne.
>
> **Toutes les décisions sont tranchées.** #2–#5 le 2026-08-11 ; **#1 (architecture des agents d'analyse) le 2026-08-17** via les 6 questions de la Partie F du benchmark (`benchmark-methodologies-decision-investissement.md`). Les marqueurs `⚠` ont été retirés ; le lot 6 (§18) est déverrouillé.

---

## 0. Décisions à trancher & incohérences entre sources

Les deux specs V2 ont été rédigées séparément et se contredisent sur des points
structurants. **Toutes les décisions sont prises : #2–#5 le 2026-08-11, #1 (architecture d'agents) le 2026-08-17. Le lot d'analyse (§18 lot 6) est déverrouillé.**

### 0.1 Incohérences majeures — décisions (#2–#5 : 2026-08-11 · #1 : 2026-08-17)

**✅ DÉCISION #1 — Architecture des agents d'analyse. → Option C (base neutre → jugement adversarial → synthèse).**
Tranchée le 2026-08-17 sur la base du benchmark (`benchmark-methodologies-decision-investissement.md`, Parties C/D/F). Les 6 questions de la Partie F sont résolues ainsi :
- **Q1 — Option C confirmée.** `research-agent` construit une **base factuelle neutre versionnée** (étapes 3-8) ; **puis** `bull` et `bear` argumentent depuis cette base (recherche divergente autorisée) ; `synthesis` (thesis-agent) réconcilie. Rejet de A (analyste+challenger, memo mono-auteur biaisable) et B (symétrique, fact-finding dédoublé). Fidélité maximale à la convergence A4 (« collecte des faits ≠ contestation du jugement, rôles séparés »).
- **Q2 — `research_memo` strictement neutre.** Aucun `verdict_recherche` : analyser ≠ recommander. Le verdict PROCEED/PASSER n'existe **qu'une fois**, dans `risk_matrix_json.verdict` (étape 12). Le memo livre les faits analysés + les incertitudes bloquantes/investissables, rien d'autre. Évite d'ancrer bull/bear.
- **Q3 — Isolation du jugement, pas des faits.** `bull` et `bear` partagent le **même memo neutre + la même base** `knowledge_entries` ; leur **cas adverse est caché** pendant la production indépendante ; le voile se lève **dans un seul sens** au round de réfutation. Recherche divergente préservée (bear orienté falsification).
- **Q4 — Une passe + escalade conditionnelle.** Flux par défaut : `bull ∥ bear → réfutation bear→bull → synthèse` (une passe). Un **unique** second tour est déclenché si (a) une incertitude bloquante reste `non_resolvable` et décisive, (b) dissensus de conviction non résolu, ou (c) `synthesis.needs_second_round=true`. Jamais de débat multi-tours ouvert (arrêt de Pareto).
- **Q5 — Curator = gate GO/NO-GO en amont ; research démarre seulement sur `ready`.** Ajouts : le readiness sépare **couverture structurée** et **couverture qualitative/marché** (nouveau statut `thin_qualitative` : un dossier financièrement complet mais mince sur produits/positionnement/état du marché **ne passe pas** `ready`) ; **boucle d'approfondissement pilotée par l'utilisateur** sur les `gaps[]` émis par le curator **et** sur des gaps signalés en **langage naturel** (transcrits par un ouvrier `gap-intake` Haiku, qui vérifie d'abord la base) ; le curator produit un **`context_pack` distillé** (`agent_synthesis`) réutilisé comme base front-loadée par research/bull/bear/synthèse ; sous-segmentation Haiku du scoring de couverture. Détail : §7, §6.6.
- **Q6 — Sizing par formule Kelly-capée comme ancre.** `pct_formule = conviction × marge_sécurité × (1/corrélation portefeuille)`, **capé dur** par `MAX_SECTOR_CONCENTRATION` ; puis `pct_recommande` (ajustement agent justifié) ; puis `override_utilisateur` (`override_reason` obligatoire, A7). La formule ne décide jamais seule mais reste visible comme référence — force l'intégration du risque corrélé portefeuille (A8). Détail : §8.4.

**✅ DÉCISION #2 — Provider & budget mensuel. → Plafond supprimé, remplacé par deux principes.**
- Le plafond **5 USD/mois est levé**. À la place, deux principes deviennent structurants (inscrits dans la constitution §3–§4, appliqués §5.3) :
  1. **Économie de tokens** — agent adapté à chaque tâche + **sous-segmentation** des tâches lourdes en sous-tâches déléguées aux ouvriers ; on ne paie de l'Opus que pour le jugement.
  2. **Arrêt de Pareto** — on cesse de chercher plus d'information dès que l'impact marginal sur la décision devient faible, comme un fonds.
- *Non tranché (non bloquant)* : provider par défaut (Dust en parallèle vs bascule LiteLLM) — absorbé par l'abstraction provider.

**✅ DÉCISION #3 — Données financières. → US via EDGAR, EU via agents web-search.**
- **US** : EDGAR Company Facts (10 ans XBRL, gratuit) + filings.
- **EU** : acquisition **par agents** — `search-worker` (web-search) + `fetch_url` sur les pages IR/communiqués ; upload manuel en fallback. Pas de scrapers IR dédiés comme voie primaire.
- Les **deux marchés dès le départ**, avec une acquisition différente. Voir §6.5, §17.

**✅ DÉCISION #4 — Infrastructure. → pgvector + Ollama + SearXNG retenus.**
- **pgvector** (RAG sur shared-postgres) + **Ollama/nomic-embed-text** (embeddings 768d, container VPS) + **SearXNG** self-hosted pour le web-search — **ou** les outils de recherche liés aux API déjà utilisées quand c'est plus simple.
- Containers VPS sécurisés (bind `127.0.0.1`, UFW DENY, §17).

**✅ DÉCISION #5 — Sortie. → Thèse-driven, avec réévaluation thèse-vs-prix.**
- Déclencheur primaire : **dégradation de thèse** (pas de market-timing sur un seuil de prix).
- **Nuance retenue** : à chaque revue (surtout Mode 6), on réévalue si la thèse **valide justifie encore le prix** — si le **rendement attendu à terme** ne compense plus le risque et le coût d'opportunité, on **commence à réduire l'exposition, même thèse intacte** (comportement de fonds). Ce n'est pas vendre parce que « le prix est haut » ; c'est un arbitrage rendement/risque **prospectif** piloté par la thèse. Voir §11.

### 0.2 Incohérences de fond issues de l'audit (à intégrer, pas à débattre)

Ces points **corrigent** la spec Knowledge Platform ; ils sont intégrés dans les sections concernées :

| # | Correction | Section |
|---|---|---|
| A1 | `knowledge_entries` **append-only + versionnées** ; référence par snapshot figé, pas par `INT[]` mutable | §6, §13 |
| A2 | Vérification de **groundedness** des citations (agent tiers) | §7, §13 |
| A3 | `confidence_score` **décomposé en 3** (info / conviction / marge de sécurité) — jamais fusionné | §8 |
| A4 | Horizon **≥ 5 ans** : valorisation scénarisée (bear/base/bull) + **reverse-DCF** | §8 |
| A5 | **Boucle de calibration** post-mortem → pattern library | §12 |
| A6 | Bear à **recherche divergente** + **round de réfutation** | §8 |
| A7 | **Overrides utilisateur** justifiés et tracés (`override_reason`) | §8, §13 |
| A8 | **Risque agrégé portefeuille** au sizing | §9 |
| A9 | Résolution de contradictions **pondérée tier + récence** | §7 |
| A10 | `too_hard` **révisable** (date de re-revue, pas archivage définitif) | §7 |

### 0.3 Collisions techniques

- **Migration 023** : les deux specs nomment `023_*.sql` avec des contenus différents. → séquence unique définie en §14 (`023` … `027`).
- **Colonnes `theses`** : les deux ajoutent `pre_mortem_acked`, `position_sizing_pct`, `conditions_entree` → dédupliquées en §14.
- **Renommage `debate-agent`** : *Processus fonds* renomme `opportunity-agent`→`debate-agent`. Cohérent, retenu.

### 0.4 Reste ouvert

- **Provider par défaut (DÉCISION #2)** — Dust en parallèle vs bascule LiteLLM ; non bloquant (l'abstraction provider absorbe le choix).
- Migration progressive (nouveau flux pour nouveaux tickers ; NVDA/CAP/TSLA restent V1) : confirmée par les deux specs.

---

## 1. Principe directeur (rappel — la constitution prime)

Toute capacité se conçoit **UX → agents → données**, sous trois garde-fous :

- **G1** — le **schéma JSON est un artefact versionné**, source de vérité unique des 3 points de synchronisation (prompt agent · frontend · import/validation backend).
- **G2** — la **logique de décision contraint l'UX**, jamais l'inverse (pas d'écran qui pilote un mauvais comportement d'investisseur).
- **G3** — **toute donnée entre versionnée et scorée avant usage**, y compris la recherche ad hoc ; `knowledge_entries` append-only.

Invariants métier (contraignent toute UX de décision) : horizon ≥ 5 ans · sortie sur dégradation de thèse (pas sur prix étiré) · trois indicateurs séparés (info / conviction / marge de sécurité) · auditabilité reconstructible · curator MVDD/readiness/too-hard préservé.

Tiering agents : **Opus 4.8** (jugement/synthèse) délègue à **Haiku 4.5** (recherche/extraction) via requêtes structurées ; **Sonnet 4.6** en intermédiaire. Prompt caching pour le contexte réutilisé, Batch API pour l'ingestion de masse. Détail complet : `00-principe-directeur-v2.md`.

---

## 2. Vision & architecture en 3 couches

```
┌─────────────────────────────────────────────────┐
│  PORTFOLIO TRACKER (frontend Next.js)           │  ← COUCHE 1 : UX / contrats JSON
│  watchlist · analyse · thèse · monitoring · exit│
└──────────────────────┬──────────────────────────┘
                       │ consomme des JSON contractuels
┌──────────────────────▼──────────────────────────┐
│  AGENT LAYER (provider-agnostic, tiering)       │  ← COUCHE 2 : logique métier
│  curator · research · bull · bear · synthèse ·  │
│  monitoring · ingestion · workers · calibration │
└──────────────────────┬──────────────────────────┘
                       │ interroge / enrichit
┌──────────────────────▼──────────────────────────┐
│  KNOWLEDGE PLATFORM (données auditables)        │  ← COUCHE 3 : données
│  ingestion · knowledge_entries versionnées ·    │
│  fiabilité scorée · RAG pgvector · snapshots     │
└─────────────────────────────────────────────────┘
```

Règle centrale : **toute information qui influence une analyse existe dans la couche 3**, tracée, scorée, figée au moment de la décision.

---

## 3. Flux d'investissement unifié (réconcilié)

**DÉCISION #1 tranchée (Option C)** : entonnoir séquentiel **jusqu'à** la readiness, puis analyse **adversariale** (base neutre → bull/bear → synthèse). Voir §0.1 pour les 6 sous-décisions.

```
[WATCHLIST]  ajout ticker
    ↓  onboarding auto (couche 3)
[ONBOARDING KNOWLEDGE]  EDGAR/yfinance → knowledge_entries + embeddings
    ↓
[CURATOR — MVDD + READINESS]  (absorbe le screening-agent)
    GO/NO-GO + « a-t-on assez pour juger ? » + incertitudes bloquantes
    couverture SÉPARÉE : structurée | qualitative/marché (plancher dur)
    ↓                                    ↑
    │  si not_ready / thin_qualitative :  │  BOUCLE D'APPROFONDISSEMENT (Haiku, avant tout Opus)
    │   gaps[] (curator) + gaps NL (gap-intake) → search-worker → knowledge_entries → re-run readiness
    ↓  ready (les DEUX planchers atteints)
[RESEARCH]  dialogue utilisateur ↔ research-agent  (part du context_pack distillé par le curator)
    construit la compréhension, résout les incertitudes bloquantes
    ↓  research_memo NEUTRE validé (pas de verdict)
[ANALYSE ADVERSARIALE]
    BULL-agent  (contexte isolé)      BEAR-agent  (contexte isolé, recherche divergente)
              ↘                      ↙
        [SYNTHÈSE — thesis-agent]  → risk_matrix + pré-mortem + sizing
    ↓
[DÉCISION]  acquittement risque par risque → position_sizing → conditions d'entrée
    ↓  validate
[POSITION]  portfolio_position + cash_movement + calendrier (modes 1-6 planifiés)
    ↓
[MONITORING]  modes 1-6 (mode 6 = revue annuelle)
    ↓  dégradation de thèse OU décision manuelle
[SORTIE]  déclencheur = thèse (pas prix) ; plan de sortie ; exécution par tranches
    ↓  clôture
[POST-MORTEM + CALIBRATION]  leçons → pattern_library ; prédit vs réalisé → registre
```

Machine d'états d'une position : `WATCHLIST → ONBOARDING → READINESS → RESEARCH → ANALYSE → DECISION → (PASSE|POSITION_ACTIVE) → MONITORING → EXIT_PLAN → PARTIAL → CLOSED → POST_MORTEM`. `too_complex` est un état terminal **révisable** (A10).

---

## 4. Couche 1 — UX / contrats d'affichage

Chaque écran est défini par son **contrat JSON versionné**. Le tableau ci-dessous est la liste des écrans V2 ; les schémas détaillés sont en §8–§12.

| Écran | URL | Contrat JSON principal | Produit par |
|---|---|---|---|
| Watchlist | `/watchlist-v2` | statut onboarding + badge readiness | curator |
| Fiche ticker | `/ticker/[id]` | métriques + readiness report | curator |
| Knowledge | `/knowledge/[id]` | knowledge_entries (onglets profil/financiers/concurrence/à-vérifier/documents) | ingestion + curator |
| Readiness | `/knowledge/[id]` onglet Readiness | `readiness_report_json` | curator |
| Research | `/ticker/[id]/research/[memo_id]` | `research_memo_json` (chat + memo) | research-agent |
| Analyse | `/ticker/[id]/analyse` | `bull_case_json`, `bear_case_json`, `risk_matrix_json` (3 colonnes) | bull/bear/synthèse |
| Décision | `/ticker/[id]/decision/[thesis_id]` | risk matrix + sizing + conditions | synthèse |
| Thèse | `/ticker/[id]/thesis/[thesis_id]` | `thesis_json` (hypothèses, seuils) | synthèse |
| Monitoring | `/ticker/[id]/monitoring/[session_id]` | `monitoring_json` par mode | monitoring |
| Portfolio | `/portfolio` | positions + sizing cible/actuel + valuation status | — |
| Exit | `/ticker/[id]/decision/...` (ExitPlanBuilder) | `exit_plan_json` | monitoring + user |
| Post-mortem | (auto) | `post_mortem_json` + calibration | post-mortem-agent |
| Admin | `/admin` | agents (provider/model/tools), scrapers, ingestion, budget | — |

Composants front nouveaux (fusion des deux specs) : `ReadinessBadge`, `KnowledgeAuditPanel`, ` ResearchMemoEditor`, `BullBearPanel`, `RiskMatrixPanel`, `PreMortemPanel`, `PositionSizingWidget`, `ValuationThermometer`, `ExitPlanBuilder`, `CalibrationPanel`.

> **G2** : sur les écrans de décision (Analyse, Décision, Exit), la logique métier (invariants §1) est validée **avant** l'habillage. Le `ValuationThermometer` est un composant **contextuel** (non-renforcement / revue), pas un déclencheur de vente — voir §11.

---

## 5. Couche 2 — Architecture des agents

### 5.1 Abstraction provider (provider-agnostic)

`backend/app/agents/providers/` — interface `AgentProvider` (`complete`, `stream`) avec implémentations `litellm_provider.py` et `dust_provider.py`, factory `get_provider(name)` lisant la config en DB (`agent_prompts.provider`, `.model`, `.tools_json`). Changer de provider/modèle = `PATCH /admin/agents/{name}`, pas de code. Le **défaut** (Dust conservé vs bascule LiteLLM) reste à préciser — résiduel non bloquant de la DÉCISION #2.

### 5.2 Roster d'agents V2 (réconcilié)

| Agent | Tier | Modèle défaut | Rôle | Origine |
|---|---|---|---|---|
| `ingestion-agent` | ouvrier | haiku-4-5 (sonnet pour 10-K complets) | extrait `knowledge_entries` des documents bruts | KP |
| `search-worker` | ouvrier | haiku-4-5 | `web_search`/`fetch_url` à la demande d'un agent métier | KP (tools) |
| `gap-intake` | ouvrier | haiku-4-5 | transcrit un gap signalé en **langage naturel** → `query_knowledge` (anti-doublon) → `gaps[]` structurés dispatchables (Q5) | DÉCISION #1 |
| `knowledge-curator` | métier léger | sonnet-4-6 | MVDD (**2 couvertures : structurée \| qualitative-marché**) + readiness (gate GO/NO-GO, `thin_qualitative`) + `context_pack` distillé + lint. Sous-segmente le scoring de couverture à des ouvriers Haiku. **Absorbe `screening-agent`** | KP §14 + PF §4.1 + DÉCISION #1 |
| `research-agent` | métier | opus-4-8 | dialogue utilisateur + `research_memo` **neutre** (pas de verdict) + résolution incertitudes bloquantes ; part du `context_pack` du curator | PF §4.2 |
| `bull-agent` | métier | opus-4-8 | meilleur cas POUR (contexte isolé) | KP §5.2 |
| `bear-agent` | métier | opus-4-8 | meilleur cas CONTRE (contexte isolé, **recherche divergente** A6) | KP §5.3 |
| `thesis-agent` | métier | opus-4-8 | **synthèse** bull+bear → risk matrix + pré-mortem + sizing | KP §5.4 + PF §4.3 |
| `monitoring-agent` | mixte | modes 1/4 haiku · 2/5 sonnet · 3/6 opus | modes 1-6 (mode 6 = revue annuelle) | existant + KP/PF |
| `debate-agent` | métier | sonnet-4-6 | conviction challenge (option C page décision) | renommage opportunity-agent |
| `groundedness-checker` | ouvrier | haiku-4-5 | vérifie que chaque affirmation est étayée par ses `source_entry_ids` (A2) | audit |
| `postmortem-agent` | ouvrier | sonnet-4-6 | post-mortem + registre de calibration (A5) | audit + stub |

**Interface orchestrateur → ouvrier (obligatoire)** : un agent métier ne demande jamais « cherche sur X » ; il émet une **requête structurée** `{query, schéma de sortie attendu, reliability_min}` ; l'ouvrier renvoie des `knowledge_entries` scorées, jamais du texte libre.

### 5.3 Coût & exécution — budget déplafonné, deux principes (DÉCISION #2)

- Cœur intellectuel (research, bull, bear, synthèse) sur **Opus 4.8** : c'est là que se joue la qualité — à préserver.
- Ouvriers (ingestion, search, groundedness, post-mortem) sur **Haiku 4.5**.
- Monitoring : modes légers Haiku, modes lourds Sonnet/Opus.
- **Prompt caching** : le contexte réutilisé (system prompt figé, **`context_pack` distillé par le curator**, `knowledge_entries` triées déterministe, contexte portefeuille) en tête ; la query/cas adverse du tour en fin. Lectures ~0,1× l'entrée. Interdits en tête : `datetime.now()`, ID de session, JSON non trié. L'isolation bull/bear (Q3) n'empêche pas le cache : elle isole le *jugement adverse* (au tail), pas la *base factuelle commune* (au head).
- **Deux mécanismes de réutilisation, complémentaires (réponse à la charge de tokens du curator)** : (1) **durable** — le `context_pack` (`agent_synthesis`, versionné, `source_entry_refs`) est **persisté** et rechargé par toute la chaîne aval, donc l'assessment du curator n'est jamais jeté ; (2) **intra-rafale** — le prompt caching amortit `research/bull/bear/synthèse` lancés rapprochés (fenêtre ~5 min). Le coût lourd réel est l'**ingestion** (parse des filings → entries), payée **une fois** en Haiku/batch ; le curator lit des entries déjà distillées, pas les documents bruts.
- **Batch API** (−50 %) pour l'ingestion de masse (onboarding EDGAR, regénération annuelle, ingestion 10-K/10-Q).
- **Budget déplafonné (DÉCISION #2)** — le plafond 5 USD/mois est levé, remplacé par **deux principes** (constitution §3-§4) : (1) **économie de tokens** — agent adapté à chaque tâche + **sous-segmentation** des tâches lourdes en sous-tâches déléguées aux ouvriers, on ne paie de l'Opus que pour le jugement ; (2) **arrêt de Pareto** — on cesse de chercher plus d'information dès que l'impact marginal sur la décision devient faible (le curator §7 opérationnalise ce seuil via readiness / incertitudes bloquantes). Leviers d'économie complémentaires disponibles si besoin : research/bull/bear/synthèse sur Sonnet, analyses complètes réservées aux tickers readiness GO, monitoring majoritairement Haiku.

---

## 6. Couche 3 — Knowledge Platform (données)

### 6.1 LLM Wiki Pattern (Karpathy)

Wiki cumulatif, pas RAG ré-exécuté. Trois opérations : **Ingest** (`ingestion-agent`), **Query** (`query_knowledge` + `store_knowledge` si finding valuable), **Lint** (curator, §7). Chaque analyse peut enrichir le corpus (`source_type='agent_synthesis'`). Fichiers Markdown lisibles (`/knowledge/companies/{ticker}/…`) synchronisés avec la DB requêtable.

### 6.2 knowledge_entries — versionnées & append-only (A1)

**Correction d'audit majeure (P0).** On ne mute jamais une entrée : on crée une nouvelle version et on marque l'ancienne obsolète. `DELETE` = soft-delete. Chaque analyse référence les sources via une **table de jointure avec snapshot figé**, pas un `INT[]` mutable. Schéma en §14.

### 6.3 Score de fiabilité (framework)

`reliability_score` (0.0–1.0) + `reliability_tier` (A/A-/B+/B/B-/C+/C) par `source_type` (edgar_official 0.95 … llm_memory 0.40 …). Modulation : âge (−0.05/an financier), cross-validation (+0.10), contradiction (−0.20, flag `has_conflict`). Table complète : source KP §3.3.

### 6.4 Règle mémoire LLM (P2)

Toute affirmation issue du pré-entraînement → `store_knowledge` avec `source_type='llm_memory'`, `reliability_score=0.40`, `requires_human_review=true`, `model_cutoff`. Badge « ⚠ Mémoire modèle — à vérifier » ; l'utilisateur confirme/marque obsolète. **Renforcé par le groundedness-checker (A2)** : la traçabilité passe de déclarative à vérifiée.

### 6.5 Pipeline d'ingestion

3 modes : **A** automatisé (EDGAR US · News/RSS), **B** **agent on-demand — voie primaire pour l'EU** (`search-worker` : web-search + `fetch_url` + `store_knowledge`), **C** manuel (upload PDF · URL · formulaire · confidentiel). Sources par type — **US** : EDGAR Company Facts 10 ans + yfinance ; **EU** : agents web-search (SearXNG / API) + `fetch_url` sur pages IR + fallback upload manuel ; **privé** : Crunchbase + presse + upload confidentiel. Onboarding & mises à jour périodiques (quotidien/trimestriel/annuel) : source KP §4.

### 6.6 Amorçage & démarrage à froid (cold-start)

La base est vide au départ ; le flux est conçu pour l'absorber sans exploser les coûts ni brader la décidabilité.

- **Le remplissage précède le gate.** L'étape `[ONBOARDING KNOWLEDGE]` (§3) amorce la base *avant* le curator ; le readiness ne juge jamais sur du vide, il **mesure la complétude** et lance des recherches pour combler (état transitoire `researching`).
- **Amorçage large mais bon marché.** US : **EDGAR Company Facts (10 ans XBRL, gratuit)** récupéré d'un coup + yfinance. Extraction des `knowledge_entries` par ouvriers **Haiku en Batch API (−50 %)**, **une seule fois** ; sous-segmentation des 10-K. On ne paie de l'Opus que pour le jugement aval.
- **Eager vs lazy (arbitrage retenu)** : **eager** pour le structuré bon marché (EDGAR/yfinance — récupéré dès l'ajout du ticker) ; **lazy/divergent** pour le qualitatif coûteux (positionnement, litiges, scuttlebutt — cherché à la demande via la boucle d'approfondissement §7, jamais en ratissage).
- **Plancher qualitatif = garde-fou anti-faux-complet.** Le structuré rempli ne suffit pas à passer `ready` : la couverture qualitative/marché doit atteindre son plancher (§7). C'est ce qui empêche de lancer l'Opus sur un dossier « qui a l'air complet ».
- **Coût décroissant, wiki cumulatif.** Le corpus s'accumule (§6.1) : 2ᵉ ticker d'un secteur réutilise `industry`, pairs, **base-rates**, `sector_schemas` et `pattern_library` ; le prompt caching amortit ce contexte réutilisé (§5.3).
- **Filet tracé.** Trou résiduel → `llm_memory` (`reliability=0.40`, `requires_human_review=true`, badge), vérifié par le `groundedness-checker` (A2) — cold-start ≠ angle mort d'auditabilité.
- **Pas de big-bang.** Migration progressive (§19) : le flux V2 ne s'active que pour les nouveaux tickers ; la base se remplit au rythme des ajouts en watchlist.

---

## 7. Curator — MVDD, Readiness, Lint (absorbe le screening)

Le curator remplit **le rôle du screening-agent** de *Processus fonds* et le rôle curator de *Knowledge Platform*. Trois modes :

- **Mode MVDD** (auto à l'onboarding) : checklist bloquante en **deux blocs de couverture jamais fusionnés** (DÉCISION #1, Q5) :
  - **couverture structurée** — business model compris · ≥3 ans financials · valorisation actuelle (largement remplie par EDGAR/yfinance à l'onboarding) ;
  - **couverture qualitative/marché** — produits & proposition de valeur · **positionnement concurrentiel** (≥1 concurrent + part de marché relative + dynamique switching) · **structure & état du marché** (croissance, cycle, disruption) · **management & allocation du capital** (grille Outsiders : M&A · buybacks · dividendes · réinvestissement ; incitations ; skin-in-the-game — *ajout 2026-08-19, finding #1 des cartes de provenance*) · risques principaux.
  Lance des recherches ciblées (ouvriers Haiku) pour combler ; **sous-segmente** le scoring de couverture dimension par dimension. Sortie watchlist : `⏳ struct 4/4 · qual 1/4` / `✅ complet` / `⚠ bloquant manquant`.
- **Mode Readiness** (au clic « Analyser ») : produit `readiness_report_json` — MVDD, entrées par tier, **3 indicateurs séparés (A3)**, `coverage{structuree, qualitative_marche}`, **incertitudes bloquantes vs investissables**, `gaps[]` **dispatchables**, verdict `not_ready | researching | thin_qualitative | ready | too_hard`. C'est le **GO/NO-GO** (ex-screening). **Le verdict `ready` exige un plancher sur les DEUX couvertures** : un dossier structuré-complet mais mince en qualitatif sort `thin_qualitative`, jamais `ready` (empêche de lancer l'Opus sur un set « qui a l'air complet »). Bouton « Analyser » actif seulement si `ready`.

**Boucle d'approfondissement avant analyse (Q5) — pilotée par l'utilisateur.** Tant que le verdict n'est pas `ready`, le readiness émet des `gaps[]` structurés (`{dimension, manque, queries_suggerees, priorite, coverage_actuelle}`). Deux sources de gaps convergent dans **un seul pipeline** :
1. **Gaps détectés par le curator** (couverture insuffisante sur une dimension).
2. **Gaps signalés par l'utilisateur en langage naturel** → l'ouvrier **`gap-intake` (Haiku)** vérifie d'abord la base (`query_knowledge`, anti-doublon), puis transcrit en `gaps[]` du même schéma, que l'utilisateur relit/édite.

L'utilisateur **choisit** quels gaps approfondir et à quelle profondeur → `search-worker` (Haiku : `web_search` + `fetch_url` + `store_knowledge`) → `knowledge_entries` scorées → **re-run readiness** → boucle jusqu'à `ready` ou décision d'arrêt. Toute la boucle est en **tier ouvrier**, **avant** tout appel Opus : la largeur/profondeur bon marché en amont protège la dépense Opus en aval. L'**arrêt de Pareto** est la *recommandation* du curator (impact marginal faible) ; le **plancher qualitatif** interdit de s'arrêter avant décidabilité ; l'**utilisateur garde l'override** (aller un tour plus loin, tracé).

**`context_pack` réutilisable.** Le curator ne se contente pas d'émettre un verdict : il produit un **artefact distillé** (état des connaissances par dimension MVDD + `source_entry_refs`), stocké comme `knowledge_entry` `source_type='agent_synthesis'` (LLM Wiki Pattern §6.1). Si `ready`, ce `context_pack` devient la **base front-loadée** de research/bull/bear/synthèse (réutilisation durable + cache, §5.3) — les tokens de l'assessment ne sont pas perdus.
- **Mode Lint** (hebdo / post-ingestion) : contradictions (**résolution pondérée tier + récence — A9**, jamais auto sur conflit Tier-A/Tier-A en portefeuille), entrées périmées, orphelines, cross-refs manquantes → rapport dans `log.md` + Slack si bloquant.

`too_hard` = décision d'investissement valide (business opaque, incertitude réglementaire binaire, comptabilité non vérifiable, privé sans données). **Révisable (A10)** : `too_complex` porte une `date_re_revue`, pas un archivage définitif.

Le **groundedness-checker (A2)** s'insère ici et après bull/bear : pour chaque affirmation, vérifie que les `source_entry_ids` cités contiennent le fait ; sortie `grounding_score` + flag des affirmations non étayées.

> **Fusion screening→curator** : `screening_json` (cercle de compétence / santé financière / valorisation grossière + verdict GO/NO-GO) de *Processus fonds* est **réexprimé comme la sortie du mode Readiness**. On ne crée pas d'agent screening distinct ; on ne crée pas de table `screenings` séparée (voir §14 : `knowledge_curator_reports` couvre MVDD + readiness + lint).

---

## 8. Contrats des agents d'analyse — recherche neutre, bull/bear, synthèse

Contrats **figés** le 2026-08-17 (DÉCISION #1, Partie D du benchmark). Chaque JSON **encode la méthodologie** pour que l'agent ne puisse pas sauter une étape (G1/G2). **6 règles transverses obligatoires** à tous les contrats ci-dessous :

1. Toute affirmation factuelle porte `source_entry_refs` (grounding vérifié par le `groundedness-checker`, A2).
2. Toute prévision porte une **ancre base-rate** — interdiction du point chiffré sans classe de référence.
3. Les hypothèses portent un **seuil d'invalidation chiffré** (falsifiabilité).
4. Les axes **qualité business / info / conviction / marge de sécurité** restent **séparés** — jamais un score unique (A3).
5. La valorisation porte **toujours** le **reverse-DCF** (ce que le prix price déjà — A4).
6. Le champ **variant perception** (edge) est obligatoire : pas d'edge articulé ⇒ pas de thèse.

> **Amendement 2026-08-19 (passe cartes de provenance).** `research_memo` complété sur 3 findings, chacun répercuté aux 3 points de synchronisation à la construction (règle #19) : **(#1)** ajout de `management.source_entry_refs[]` **et** d'une dimension de couverture MVDD *management & allocation du capital* (§7) — sans elle un dossier passait `ready` sans aucune donnée d'allocation du capital, alors que le contrat exige un bloc `management` ; **(#2)** ajout de `moat.durabilite_ans.base_rate` (règle 2 — c'était une prévision chiffrée sans ancre) ; **(#3)** `industry.croissance_marche_pct` scindé en `croissance_marche_historique_pct` (factual) et `croissance_marche_prospective{taux_pct, base_rate}` (prévision → ancre obligatoire).

### 8.0 research_memo_json (research-agent — base NEUTRE, étapes 3-8)

Produit après `readiness = ready`, à partir du `context_pack` du curator. **Neutre : pas de recommandation, pas de `verdict_recherche`** (Q2). Livre les faits analysés + les incertitudes.

```json
{
  "business_model": {"description":"...","drivers_revenus":[],"recurrence_pct":90,
                     "unit_economics":"...","source_entry_refs":[{"entry_id":12,"version":1}]},
  "moat": {"type":["switching_costs","scale_economics_shared"],"score":4,
           "durabilite_ans":{"forte":5,"incertaine":10,
              "base_rate":{"reference_class":"moats de type X ayant duré >5 ans","taux":0.5}},
           "trend":"widening|stable|eroding","preuves":[{"fait":"...","source_entry_refs":[]}]},
  "financials": {"roic_pct":18,"wacc_estime_pct":9,"roic_vs_wacc":"spread positif durable",
                 "roic_trend_5y":"stable","fcf_conversion_pct":85,"intensite_capex_pct":6,
                 "earnings_quality":{"score":"high","accruals_flag":false,"note":"..."},
                 "levier":{"dette_nette_ebitda":-0.3},"source_entry_refs":[]},
  "management": {"capital_allocation_scorecard":{"ma":"disciplinée","buybacks":"opportunistes sous IV",
                    "dividendes":"modérés","reinvestissement":"fort ROIC","note":"grille Outsiders"},
                 "incitations":"...","skin_in_game_pct":1.6,"candeur":"...","score":3,
                 "source_entry_refs":[{"entry_id":0,"version":1}]},
  "industry": {"structure_5forces":"...","croissance_marche_historique_pct":12,
               "croissance_marche_prospective":{"taux_pct":15,
                  "base_rate":{"reference_class":"...","taux_pct":10}},
               "cyclicite":"faible","disruption_vectors":[],
               "position_vs_pairs":"leader mid-market","source_entry_refs":[]},
  "valuation": {
     "dcf_scenarios":{"bear":95,"base":130,"bull":165,"drivers":{"croissance":0.10,"marge_fcf":0.28}},
     "epv":{"valeur_rentabilite":105,"note":"croissance payée justifiée par moat: oui/non"},
     "reverse_dcf":{"croissance_implicite_prix_actuel_pct":14,"verdict":"le prix price une croissance > base"},
     "relatif":{"multiple":"EV/FCF 22x","vs_historique":"prime 15%","vs_pairs":"en ligne"},
     "base_rate_anchor":{"reference_class":"SaaS >1Md$ maintenant >12% croissance 10 ans","taux_base_pct":15},
     "prix_actuel":108,"iv_range":[95,140],"marge_securite_base_pct":-6
  },
  "incertitudes_bloquantes":[{"question":"...","impact_si_non_resolu":"inverse la thèse",
                              "statut":"resolue|en_cours|non_resolvable","source_entry_refs":[]}],
  "incertitudes_investissables":[{"question":"...","fourchette":"n'inverse pas la décision"}],
  "posture":"NEUTRE — pas de recommandation ; base factuelle pour bull/bear"
}
```

### 8.1 bull-agent

Contexte **isolé** (ne voit jamais le bear). Reçoit : `knowledge_entries` du ticker (RAG), contexte portefeuille (coût d'opportunité), température de marché. Peut appeler `search-worker` (stocké en entries). Règle : tout fait provient d'une entry fournie ou d'une recherche ; sinon `llm_memory`. Liste les `source_entry_ids` utilisés.

`bull_case_json` (canonique, **corrigé A3/A4 + 6 règles transverses**) :
```json
{
  "variant_perception": {"type":"analytique|informationnel|temporel",
     "enonce":"le marché sous-estime la durabilité du moat car ...",
     "catalyseur_re_rating":"...","horizon_mois":36,"source_entry_refs":[]},
  "arguments": [{"titre":"...","explication":"...","probabilite":0.6,
     "base_rate":{"reference_class":"...","taux":0.4,"ajustement":"+ car ..."},
     "source_entry_refs":[{"entry_id":42,"version":3}],
     "recherche_divergente":[{"query":"...","finding_entry_id":91}]}],
  "valorisation": {
    "horizon_ans": 5,
    "reverse_dcf": {"croissance_implicite_prix_actuel_pct": 14, "note": "ce que le prix price déjà"},
    "scenarios": {"bear": 95, "base": 130, "bull": 165},
    "methode": "FCF normalisé + croissance conservatrice + exit multiple",
    "assumptions": {"croissance_revenue": 0.10, "expansion_marge_fcf": 0.02, "multiple_sortie": 18}
  },
  "catalyseurs": ["..."],
  "conviction": 7,
  "indicateurs": {"qualite_info": 0.74, "conviction": 0.70, "marge_securite": 0.20},
  "grounding_report": {"affirmations_total": 9, "etayees": 9, "non_etayees": 0}
}
```
> `variant_perception` **obligatoire** (règle 6) ; chaque argument porte `probabilite` + **ancre `base_rate`** (règle 2) et sa **recherche divergente** tracée. `horizon_ans ≥ 5` + **valorisation scénarisée + reverse-DCF** remplacent `prix_cible`/`horizon_mois: 36` (A4). `confidence_score` unique **supprimé** → `indicateurs` à 3 composantes (A3). `grounding_report` renseigné par le `groundedness-checker` (A2).

### 8.2 bear-agent

Contexte **isolé** (ne voit ni le cas bull ni le bear pendant la production), **mandat de recherche divergent (A6)** : lance ses propres `search-worker` orientés falsification (litiges, red flags comptables, avis short-sellers, attrition), crée ses entries. `bear_case_json` = même ossature que `bull_case_json` (mêmes 6 règles transverses : `variant_perception`, `arguments[]` avec `base_rate` + `recherche_divergente`, `indicateurs` 3 composantes, `grounding_report`) **plus** : `failles_bull_conventionnel[]`, `scenario_destruction_valeur{prix_bear, perte_pct, declencheurs[]}`, `conviction_negative`. Le champ `refutation_du_bull[]` est ajouté **après** le round de réfutation (§8.3).

### 8.3 Round de réfutation (A6) — asymétrique bear → bull (Q3/Q4)

Après production **indépendante** des deux cas (cas adverse caché), le voile se lève **dans un seul sens** : le **bear voit le bull** et l'attaque argument par argument dans `refutation_du_bull[]` (**une passe**, contexte tracé). Le bull ne voit pas le bear (dernier mot critique à l'avocat du diable). La synthèse dialectique remplace la synthèse one-shot.

**Escalade conditionnelle (Q4) — un unique second tour.** Par défaut on s'arrête après la passe. Un **seul** tour supplémentaire (le bull répond à la réfutation → nouvelle synthèse) est déclenché si l'une de ces conditions est vraie, sinon jamais :
- une **incertitude bloquante** du `research_memo` reste `non_resolvable` **et** décisive (peut faire basculer PROCEED ↔ PASSER) ; **ou**
- **dissensus de conviction** non résolu (bull et bear tous deux à forte conviction opposée) ; **ou**
- `synthesis.needs_second_round = true` avec justification tracée.

Au-delà d'un tour → on tranche (ou `TOO_HARD` si l'incertitude est irréductible, A10). Jamais de boucle ouverte.

### 8.4 thesis-agent (synthèse)

Reçoit bull + bear + réfutation + toutes les `knowledge_entries` utilisées (via snapshots). Produit **le seul verdict du flux** (Q2). `risk_matrix_json` :
```json
{
  "verdict": "PROCEED | PROCEED_AVEC_CONDITIONS | PASSER | SURVEILLER | TOO_HARD",
  "rationale": "...",
  "axes": {"qualite_business":0.80,"qualite_info":0.72,"conviction":0.71,"marge_securite":0.15},
  "risques_acceptes": [{"risque":"...","probabilite":0.35,"impact":"fort","reversible":false,
     "base_rate":{"reference_class":"...","taux":0.3},
     "reponse_si_materialise":"réduire si perte PDM > 3pts / 2 trimestres",
     "hypothese_liee":"H3","source_entry_refs":[]}],
  "pre_mortem": ["Scénario 1 ...","Scénario 2 ...","Scénario 3 ..."],
  "position_sizing": {
     "pct_formule": 4.5,
     "pct_recommande": 4.0,
     "pct_max": 7.0,
     "methode": "Kelly fractionnaire : conviction × marge_securite × (1/correlation), capé MAX_SECTOR_CONCENTRATION",
     "inputs": {"conviction":0.71,"marge_securite":0.15,"correlation_portefeuille":1.3},
     "cap_applique": {"contrainte":"MAX_SECTOR_CONCENTRATION","valeur_pct":20.0,"actif":false},
     "risques_correles_portefeuille": [{"facteur":"CapEx datacenter","exposition_pct":22}],
     "cout_opportunite": "vs meilleure alternative en portefeuille : ...",
     "ajustement_justification": "réduit de 4.5 à 4.0 car corrélation CapEx datacenter déjà à 22%",
     "override_utilisateur": null
  },
  "conditions_entree": ["Prix < 115 pour marge de sécurité > 10%"],
  "needs_second_round": false,
  "second_round_trigger": null,
  "sources_summary": {"tier_A":12,"tier_B":8,"tier_C_llm_memory":3,"total_entries":23}
}
```
> **A3/règle 4** : score global unique **supprimé** → **4 axes séparés** (`qualite_business` ajouté). **règle 2** : chaque risque porte une **ancre `base_rate`**. **A8/Q6** : `position_sizing` expose la formule Kelly-capée (`pct_formule` → `pct_recommande` → `override_utilisateur`), le cap sectoriel dur, les risques corrélés portefeuille et le coût d'opportunité. `pct_max` piloté par conviction mais **jamais au-dessus** du cap sectoriel. `needs_second_round` opérationnalise l'escalade Q4.

### 8.5 thesis_json.hypotheses[] (étape 10 — falsifiabilité)

Chaque risque accepté → une hypothèse de monitoring falsifiable, avec **seuil d'invalidation chiffré** (règle 3) et **ancre base-rate** (règle 2) :
```json
{"id":"H3","enonce":"NVDA conserve >80% de PDM GPU IA jusqu'en 2028",
 "kpi":"part de marché GPU datacenter","unite":"%",
 "seuil_alerte":78,"seuil_invalidation":72,"horizon":"2028",
 "base_rate":{"reference_class":"leaders tech maintenant >80% PDM 4 ans","taux":0.45},
 "statut":"active","source_entry_refs":[]}
```
> Le `seuil_invalidation` alimente le monitoring : les modes trimestriels (§10) n'escaladent que sur **franchissement** de ce seuil pré-enregistré (anti-churn, audit §1.3).

### 8.6 Édition utilisateur tracée (A7)

Après chaque cas, l'utilisateur peut éditer le JSON (mécanique `result_json_original` vs `result_json`). **Tout champ édité exige un `override_reason`** et, si l'édition contredit l'analyse, référence une `knowledge_entry` créée (`source_type='user_provided'`). Diff + auteur + timestamp + raison journalisés.

---

## 9. Décision, sizing, entrée

`RiskMatrixPanel` : chaque risque a « J'accepte ce risque » (obligatoire) ; `PreMortemPanel` à acquitter ; `PositionSizingWidget` (min/reco/max + justification si modifié, **affiche l'exposition corrélée A8**) ; `ValuationThermometer` **contextuel** (zones attractive/juste/étiré/surévalué → actions *suggérées*, non contraignantes). Bouton « Valider » actif seulement quand tous les risques + pré-mortem acquittés.

`POST /theses/{id}/validate` (atomique) : `thesis.status='active'`, `tickers.status='portfolio'`, crée `portfolio_positions`, `cash_movements(type='buy')`, `calendar_events` (modes 1/2 + revue annuelle mode 6 planifiés). La thèse fige `synthesis_analysis_id`, `pre_mortem_acked`, `risk_matrix_acked`, `position_sizing_pct`, `valuation_range`, hypothèses H1-Hn (chaque risque accepté → hypothèse de monitoring), `conditions_entree`.

---

## 10. Monitoring (modes 1-6)

Inchangé fonctionnellement, enrichi par la knowledge platform (contexte = `knowledge_entries` pertinentes, pas seulement yfinance). Chaque session enrichit le wiki (résultats trimestriels → entries financières ; commentaires management → `fact_qualitative`).

| Mode | Déclencheur | Rôle | Modèle |
|---|---|---|---|
| 1 Pré-event | J-2 | checklist lecture (≤3 pts) | haiku |
| 2 Revue trim. | J+1 | statut hypothèses + RAS/REVIEW_REQUIRED + valuation status | sonnet |
| 3 Décision Review | escalade | diagnostic + décision | opus |
| 4 Sector Pulse | J+1 pair | score -5→+5 | haiku |
| 5 Routing alerte | après 2/4 si REVIEW_REQUIRED | route vers synthèse/debate | (routing) |
| **6 Revue annuelle** | validated_at + 365j, puis annuel | relit thèse + research_memo + entries de l'année → CONFIRMER/RÉDUIRE/SORTIR/RENFORCER, réactualise `valuation_range`, replanifie +365j | opus/sonnet |

> **Hiérarchie (audit §1.3)** : Mode 6 est la **colonne vertébrale** de la revue LT ; les modes trimestriels n'escaladent que sur franchissement de seuil d'invalidation pré-enregistré — ils ne produisent pas un verdict à chaque passage (anti-churn cognitif).

---

## 11. Sortie — thèse-driven, avec réévaluation thèse-vs-prix (DÉCISION #5)

**Déclencheur primaire — dégradation de thèse** : hypothèse critique invalidée en mode 2/3/6 (`status: invalidated`), ou IV révisée significativement à la baisse en Mode 6.

**Déclencheur secondaire — la thèse ne justifie plus le prix** : à chaque revue (surtout Mode 6), on recalcule si la thèse **valide** justifie **encore le prix actuel** — c.-à-d. si la valeur intrinsèque réactualisée et le **rendement attendu à terme** compensent le risque et le coût d'opportunité. **Si le rendement prospectif est devenu insuffisant, on commence à réduire l'exposition, même thèse intacte** (comportement de fonds). Ce n'est **pas** un seuil de prix mécanique (l'anti-pattern que l'audit rejette : `Prix > IV×1.15`) : c'est un arbitrage rendement/risque **prospectif**, produit par l'agent (IV réactualisée × croissance vs prix × alternatives portefeuille).

Le `ValuationThermometer` reste **contextuel** : il signale la zone (attractif/juste/étiré/surévalué) et **alimente** la réévaluation ci-dessus, mais ne déclenche jamais seul une vente.

`ExitPlanBuilder` → `exit_plans` (tranches, conditions accélérées). Exécution par tranches via `_check_price_alerts_v1` étendu (seuils) + wizard de vente (`POST /portfolio-v2/cash type=sell`). Conditions de sortie accélérée : hypothèse critique invalidée, ou IV révisée −20 %+ → Mode 3 auto. `portfolio_positions.exit_status` : `null|plan_created|partially_exited|closed|accelerated_exit`.

---

## 12. Post-mortem, calibration, pattern library

Déclencheur : dernière tranche vendue. `postmortem-agent` produit `post_mortem_json` (durée, perf, statut de chaque hypothèse, décision de sortie, leçons). Leçons → `pattern_library` (`knowledge_entries` type `lesson_learned`, réutilisables par les futurs bull-agents sur comparables).

**Boucle de calibration (A5) — nouveau** : le post-mortem alimente un **registre de calibration** (risque prédit vs réalisé, IV estimée vs réalisée). Après 15-20 positions, `CalibrationPanel` affiche le biais systématique (« vos IV hautes sont en moyenne 20 % trop basses »). C'est le mécanisme d'apprentissage LT le plus précieux et il boucle avec l'auditabilité.

---

## 13. Colonne vertébrale d'auditabilité (les P0 de l'audit)

1. **Entrées versionnées / append-only (A1)** — `knowledge_entries(entry_id, version, valid_from, superseded_by)`, jamais mutées.
2. **Snapshot figé au moment de la décision** — table de jointure `analysis_knowledge_refs(analysis_id, entry_id, entry_version, content_snapshot, reliability_at_use)` remplace tout `INT[]`.
3. **Groundedness vérifiée (A2)** — `groundedness-checker` valide chaque citation ; `grounding_score` stocké par affirmation.
4. **Overrides tracés (A7)** — `override_reason` + diff + auteur + timestamp obligatoires.
5. **Reproductibilité** — persister le **prompt matérialisé complet** (hash + contenu) + provider/model/tokens/cost par analyse ; température basse (0.2-0.3) sur synthèse/valorisation.

---

## 14. Modèle de données (migrations fusionnées)

Séquence unique (résout la collision 023) :

- **`023_v2_knowledge_platform.sql`** — `knowledge_documents` ; `knowledge_entries` **versionnées** (colonnes de §6.2 + `version`, `valid_from`, `superseded_by`, `question_status`, `question_priority`, `resolves_entry_id`, `embedding vector(768)`) ; `analysis_knowledge_refs` (jointure snapshot A1/A2) ; `eu_ir_scrapers` ; `knowledge_curator_reports` (mvdd|readiness|lint — **couvre l'ex-`screenings`**). Extension `pgvector` (DÉCISION #4).
- **`024_v2_agents_provider.sql`** — `agent_prompts` += `provider`, `model`, `tools_json`. Nouveaux agents insérés.
- **`025_v2_analyses.sql`** — `investment_analyses` (bull|bear|synthesis, `result_json`, `result_json_original`, `provider_used`, `model_used`, `prompt_snapshot`, `grounding_report`, cost/tokens). `research_memos` + `research_messages` (recherche). 
- **`026_v2_theses_flow.sql`** — `theses` += `research_memo_id`, `synthesis_analysis_id`, `pre_mortem_acked`, `risk_matrix_acked`, `position_sizing_pct`, `conditions_entree`, `valuation_range` (**dédup** des deux specs). `tickers` += `ingestion_status`, `edgar_cik`, `has_eu_scraper`, `v2_flow BOOL`, `too_complex_re_revue DATE`.
- **`027_v2_exit_calibration.sql`** — `exit_plans`, `exit_executions` ; `price_alerts` += `exit_plan_id`, `alert_type` ; `calibration_registry` (prédit vs réalisé, A5).

> **Supprimé du plan** : la table `screenings` de *Processus fonds* (couverte par `knowledge_curator_reports`). Les colonnes `theses` communes aux deux specs sont fusionnées ci-dessus, pas dupliquées.
> **Rappels DB projet** : asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations appliquées manuellement via `docker cp` (pas d'auto-run au startup).

---

## 15. Surface API (fusionnée)

```
# Knowledge (couche 3)
GET/POST/DELETE /knowledge/{ticker}/documents[...]
GET/POST/PATCH/DELETE /knowledge/{ticker}/entries[...]  (PATCH = nouvelle version, jamais mutation)
POST /knowledge/{ticker}/entries/{id}/confirm | /flag
POST /knowledge/query                          RAG {ticker, query, limit, min_reliability}

# Curator (remplace screening)
POST /tickers/{id}/curator/mvdd                 (auto onboarding)
POST /tickers/{id}/curator/readiness            → readiness_report_json (coverage struct+qual, gaps[], GO/NO-GO)
POST /tickers/{id}/curator/gap                  {text} → gap-intake Haiku (NL → gaps[] après query_knowledge)
POST /tickers/{id}/curator/research-gap         {gap_id | queries[], depth} → search-workers puis re-run readiness
POST /admin/curator/lint                        (hebdo)

# Research
POST /tickers/{id}/research                     (requiert readiness = ready)
GET  /tickers/{id}/research | /research/{memo_id}
POST /research/{memo_id}/chat | /refresh-json | /validate

# Analyse bull/bear/synthèse
POST /tickers/{id}/analyses {type:'bull'|'bear'}
POST /tickers/{id}/analyses/rebuttal            (round de réfutation A6)
POST /tickers/{id}/analyses/synthesis {bull_id, bear_id}
GET  /tickers/{id}/analyses | /analyses/{id}    (+ refs snapshot + grounding)

# Thèse / décision
POST /theses/{id}/ack-risk/{risk_index} | /ack-pre-mortem
POST /theses/{id}/validate

# Exit / calibration
POST /tickers/{id}/exit-plan | /exit-plan/{id}/execute-tranche
GET  /calibration/summary

# Admin / ingestion
POST /admin/ingestion/{ticker}/trigger ; GET /admin/ingestion/status ; GET /admin/scrapers/eu
```

---

## 16. Frontend (fusionné)

Pages nouvelles : `/knowledge/[id]` (onglets + Readiness), `/ticker/[id]/research/[memo_id]`, `/ticker/[id]/analyse` (3 colonnes bull/bear/résultat). Modifiées : `watchlist-v2` (bouton « Analyser » → readiness gate ; badges MVDD/readiness), `thesis/[id]` (pré-mortem à acquitter), `portfolio` (sizing cible/actuel + valuation status). Composants : §4. `⚠` supprimer de la watchlist l'ancien lien `/opportunity/new` (remplacé par le parcours curator→research→analyse).

---

## 17. Données & infra (réalisme)

- **US** : EDGAR Company Facts (10 ans XBRL, gratuit) + derniers filings + yfinance.
- **EU** : **acquisition par agents** — `search-worker` (web-search) + `fetch_url` sur les pages IR/communiqués + **fallback upload manuel** (DÉCISION #3). Les scrapers IR dédiés (`eu_ir_scrapers`) deviennent une optimisation *ultérieure*, pas la voie primaire.
- **Privé** : Crunchbase free + presse tech + upload confidentiel (`is_confidential`).
- **Embeddings** : Ollama/nomic-embed-text (768d) sur le VPS (DÉCISION #4).
- **Web search** : SearXNG self-hosted **ou** outils de recherche liés aux API déjà utilisées (DÉCISION #4).
- **Dégradations acceptables** (de *Processus fonds* §11) : management via insider % + qualitatif ; ROIC 3 ans yfinance si pas de FMP ; IV = fourchette agent scénarisée ; newsflow = RSS Google News existant ; short = yfinance.
- **Sécurité VPS** : nouveaux containers (Ollama, SearXNG) bindés `127.0.0.1`, UFW DENY, pas de port exposé (règles CLAUDE.md repo).

---

## 18. Découpage en tickets — mode d'emploi pour l'agent aval

**Ordre imposé par la constitution : pour chaque capacité, ticket UX (contrat) → ticket agent → ticket données.** Ne jamais commencer un lot par le schéma de table.

Séquencement recommandé (par capacité, chacune produit son triplet UX/agent/données) :

1. **Fondation données** — knowledge_documents + entries versionnées + pgvector + snapshots (couche 3 pure ; pas d'UX propre, sert de socle). *Migrations 023.*
2. **Abstraction provider** — factory LiteLLM/Dust + `agent_prompts` étendu. *Migration 024.*
3. **Onboarding + ingestion** — UX watchlist (badge état) → ingestion-agent + search-worker → EDGAR/yfinance.
4. **Curator (readiness/MVDD, ex-screening)** — UX Readiness (2 couvertures struct/qual + liste `gaps[]` avec bouton « approfondir » + champ gap en langage naturel) → curator (MVDD/readiness/lint) + `gap-intake` + `groundedness-checker`, boucle d'approfondissement `search-worker`, `context_pack` distillé → `knowledge_curator_reports`.
5. **Research** — UX ResearchMemoEditor (chat+memo) → research-agent (`research_memo` **neutre**, part du `context_pack`) → research_memos. *Migration 025 (partie research).*
6. **Analyse bull/bear/synthèse** *(DÉVERROUILLÉ — DÉCISION #1 tranchée le 2026-08-17)* — UX `/analyse` 3 colonnes + RiskMatrixPanel + PreMortemPanel + PositionSizingWidget → bull ∥ bear (isolés) → réfutation asymétrique bear→bull (+ escalade conditionnelle) → synthèse (4 axes + sizing Kelly-capée) → investment_analyses + snapshots. Contrats figés en §8. *Migration 025.*
7. **Décision & validation** — UX sizing + acquittements → (synthèse) → theses étendues + validate. *Migration 026.*
8. **Monitoring mode 6 + valuation thermometer contextuel** — UX → monitoring-agent → calendar_events.
9. **Sortie thèse-driven + calibration + post-mortem** — UX ExitPlanBuilder + CalibrationPanel → postmortem-agent → exit_plans + calibration_registry. *Migration 027.*

**Test de conformité par ticket** (checklist de la constitution §6) : part d'un contrat JSON ? schéma versionné synchronisé 3 points ? décision indépendante de l'UX & conforme aux invariants ? donnée versionnée+scorée+figée (ad hoc compris) ? agent déclare tier/modèle/batch/cache ? passe par l'abstraction provider ? — un « non » = ticket non prêt.

**Rappel des corrections d'audit à ne pas perdre au découpage** : A1 (snapshots), A2 (groundedness), A3 (3 indicateurs), A4 (horizon 5 ans + reverse-DCF), A5 (calibration), A6 (bear divergent + réfutation), A7 (overrides tracés), A8 (risque portefeuille), A9 (contradictions pondérées), A10 (too_hard révisable), + DÉCISION #5 (sortie thèse-driven).

---

## 19. Ce qui ne change pas / migration progressive

Nouveau flux activé **pour les nouveaux tickers seulement** (`tickers.v2_flow=true` ou `created_at > migration_date`). NVDA/CAP/TSLA restent en V1, leur monitoring continue ; leur knowledge base s'enrichit en background. Tables V0 intactes. Migration par phases (§18) ; Dust reste disponible tant que `provider='dust'` (défaut à préciser — résiduel non bloquant DÉCISION #2).
