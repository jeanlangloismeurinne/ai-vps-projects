---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-08-23
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2 (couche contrat FIGÉE + couche 2 code DÉPLOYÉE → passage à la couche 3 données).
---

# Prompt de reprise — portfolio-tracker V2 (post-déploiement couche 2)

**État au 2026-08-23** : la **couche contrat est figée** (10 schémas Pydantic v2) ET la **chaîne
d'analyse runtime est écrite et déployée en production** (provider DeepInfra + curator → research →
bull/bear → réfutation → synthèse, 7 routes exposées). Migrations 024/025/026/**027** appliquées.
La **recherche sémantique est opérationnelle** (bge-m3 1024d, 15/15 entrées embeddées).
**Ce qui manque n'est plus du code de chaîne : c'est de la DONNÉE.** Aucun ticker n'est encore
`ready`, donc la chaîne n'a jamais tourné de bout en bout sur un cas réel.

> ### ✅ État du déploiement — À JOUR, aucune divergence
>
> Lot embeddings **déployé en production le 2026-08-23** (commit `f1e6a94`, deployment Coolify
> #280). Vérifié dans le container live et non pas seulement au statut du build :
> `EMBEDDING_MODEL=BAAI/bge-m3`, 15/15 entrées embeddées, `query_knowledge` renvoie
> `match_mode='vector'`, backfill à 0 candidat. Migration 027 appliquée en base.
>
> Repo et prod sont alignés — **rien à rattraper avant de commencer l'étape 2**.

Colle ceci pour reprendre :

> Reprise de **portfolio-tracker V2**. Couche contrat figée + chaîne d'analyse runtime déployée en
> prod (provider DeepInfra OpenAI-compat, modèle unifié `deepseek-ai/DeepSeek-V4-Flash-0731`).
> Principe directeur UX → agents → données, 3 garde-fous (G1 schéma versionné = source unique /
> G2 décision contrainte par l'analyse / G3 donnée versionnée+scorée+figée, jamais de texte libre).
> DÉCISION #1 = Option C (base neutre → bull/bear isolés → réfutation bear→bull → synthèse).
> **Le blocage actuel est l'alimentation de la base de connaissance**, pas la chaîne.
>
> **Étape 1 (embeddings) FAITE et déployée** — la recherche sémantique fonctionne (bge-m3 1024d).
> **Prochaine étape = 2, le `search-worker`** : câbler les exécuteurs `web_search` (Exa) et
> `fetch_url` dans `run_tool_agent()`, qui n'a **jamais tourné**. C'est ce qui produit la couverture
> **qualitative** manquante, seul obstacle entre NVDA (`thin_qualitative`) et `ready`.
> Prérequis à trancher en début de session : **la clé Exa n'est pas encore souscrite ni déployée**.
>
> LIRE AVANT : `roadmap/00-principe-directeur-v2.md` ; `roadmap/01-spec-v2-unifiee.md` (§5 agents,
> §7 curator/readiness, §8 contrats analyse, §14 migrations, §18 découpage) ;
> `roadmap/provenance-cards/*_card.md` + `*_schema.py` ; `roadmap/provenance-cards/prompts/` ;
> côté **code** : `backend/app/agents/providers/`, `backend/app/agents/v2/`,
> `backend/app/knowledge/` (`service.py` + `embeddings.py`), `backend/app/contracts/`,
> `backend/app/api/analysis_v2.py`.
> CLAUDE.md projet = conventions (dont #22 recherche knowledge, #23 piège pgvector).
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
| `backend/app/agents/v2/runner.py` | point de passage unique : `extract_json()` tolérant, `run_json_agent()` (validation Pydantic + **1 tour de réparation**), `run_tool_agent()` (boucle outils OpenAI, **non exercée**) |
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

**Point rassurant** : `run_tool_agent()` et le `tools_json` du `search-worker` sont agnostiques du
backend → basculer Exa ↔ Serper ↔ SearXNG = réécrire **une seule fonction exécutrice**.

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
2. **`search-worker`** — câbler l'exécuteur `web_search` (Exa) + `fetch_url` (httpx, déjà faisable)
   dans `run_tool_agent()` (écrit, jamais exercé). C'est ce qui produit la couverture **qualitative**
   manquante.
3. **`ingestion-agent`** — doc → entries (contrat C2), anti-hallucination financière.
4. **Premier run end-to-end réel** : amener NVDA de `thin_qualitative` à `ready`, puis
   research → bull/bear → réfutation → synthèse. **Jamais fait à ce jour.**
5. Agents 7→9 (migrations 027/028) : décision/validate → monitoring m6 → sortie/calibration.
6. Passe UX transverse finale (§16).

**Piège migrations (§18)** : écrire chaque migration **juste avant** son lot, jamais en avance.

## Ce qui n'a JAMAIS été vérifié (à ne pas supposer acquis)

- **Aucun run réel de la chaîne V2.** Les 7 routes sont exposées et importent proprement, mais aucune
  n'a été appelée contre un vrai ticker. Le `_apply_deterministic_overrides` du curator, la boucle de
  réparation JSON du runner et `valider_pont()` n'ont jamais vu de sortie de modèle réelle.
- **`run_tool_agent()` n'a jamais tourné** (aucun exécuteur d'outil câblé).
- La validation faite : `py_compile` + import complet en container jetable + round-trip
  `ReadinessReport` sous pydantic 2.13.4 → `thin_qualitative` cohérent avec `compute_verdict`.

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
