---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
updated: 2026-08-21
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier V2 (couche contrat FIGÉE → passage au code).
---

# Prompt de reprise — portfolio-tracker V2 (post couche contrat)

**État au 2026-08-21** : la **couche contrat est complète et figée** (10 schémas Pydantic v2 vérifiés
en container + cartes de provenance), les **prompts d'agent V2 sont écrits**, tout est **committé**
(local `8d8c698` sur `main`, non poussé). **Il ne reste que du code.** Décision produit majeure depuis
la spec : **le provider cible est DeepInfra (endpoint OpenAI-compatible), pas Dust.**

Colle ceci pour reprendre :

> Reprise de **portfolio-tracker V2**. La logique métier est entièrement figée (cartes de provenance
> + Pydantic v2 vérifiés en container 2.13.4) et les prompts d'agent sont rédigés. **Je passe au
> code**, dans l'ordre de la chaîne runtime. Principe directeur UX → agents → données, 3 garde-fous
> (G1 schéma versionné = source unique / G2 décision contrainte par l'analyse / G3 donnée
> versionnée+scorée+figée, jamais de texte libre). DÉCISION #1 = Option C (base neutre → bull/bear
> isolés → réfutation bear→bull → synthèse). **Provider = DeepInfra OpenAI-compatible** ; modèle
> métier défaut = **DeepSeek V4 Flash 0731** ; ouvrier = à choisir dans le catalogue DeepInfra.
>
> LIRE AVANT : `roadmap/00-principe-directeur-v2.md` ; `roadmap/01-spec-v2-unifiee.md` (§5 agents +
> abstraction provider, §5.2 roster, §7 curator/readiness, §8 contrats analyse, §14 migrations,
> §18 découpage) ; `roadmap/provenance-cards/*_card.md` + `*_schema.py` (contrats figés) ;
> `roadmap/provenance-cards/prompts/` (prompts d'agent + `00-preambule-commun.md`) ; côté **code** :
> `backend/app/agents/` (dust_client, classes agents V1), `app/config.py`, `app/db/database.py`,
> `app/api/admin_v1.py` (endpoints agents), `docker-compose.yml`. CLAUDE.md projet = conventions.
> Visuel : https://provenance.jlmvpscode.duckdns.org

## Ce qui est FAIT

### Couche contrat — 10 schémas Pydantic v2 (`SCHEMA_VERSION=v2.0.0`, importés ensemble sans conflit, vérifiés en container)

- **Analyse** `analysis_v2_schemas.py` : `ResearchMemo` (NEUTRE, Q2) · `BullCase`/`BearCase` (A6) ·
  `RiskMatrix` (seul verdict) · `Hypothese` (falsifiabilité). + `readiness_report_schema.py` (gate
  GO/NO-GO, `compute_verdict`, `thin_qualitative`).
- **C1** `worker_delegation_schema.py` (interface orchestrateur→ouvrier, `ProducedEntry` partagé, G3).
- **C2** `ingestion_extraction_schema.py` (doc→entries, anti-hallucination financière, déterministe=gratuit).
- **C3** `context_pack_schema.py` (front-load ready-only, discipline de cache).
- **C4** `decision_validate_schema.py` (décision contrainte, bijection acks, cap Kelly).
- **C5** `monitoring_mode6_schema.py` (revue annuelle, anti-seuil-mécanique, thermomètre `contraignant=False`).
- **C6** `exit_calibration_schema.py` (sortie thèse-driven, post-mortem bijectif, calibration A5).
- **C7** `debate_conviction_schema.py` (conviction challenge, G2 anti-complaisance — 12/12).
- **C8** `monitoring_modes_1_5_schema.py` (union discriminée `Mode1..Mode5`, anti-churn — 20/20).

Chaque contrat a sa carte `*_card.md` (twin table nature×grounding + garde-fous + 3 points de synchro).
Autres dérivés : `readiness_derivation.md`, `groundedness_rules.md` + `groundedness_checker.py`.

### Prompts d'agent V2 (`prompts/`) — cible DeepInfra OpenAI-compatible

`00-preambule-commun.md` (bloc système partagé : mission, G1/G2/G3, framework fiabilité
source→tier→score, interface délégation, discipline JSON, 6 règles) + **11 prompts** : `10-ingestion`,
`11-search-worker`, `12-gap-intake`, `13-groundedness-checker`, `20-knowledge-curator`,
`30-research`, `40-bull`, `41-bear`, `50-thesis-synthese`, `60-debate`, `70-monitoring` (modes 1-6),
`80-postmortem` + `README.md`. Ce sont le **3ᵉ point de synchro** (règle #19) : schéma de sortie =
Pydantic correspondant.

### Socle données (déjà appliqué)

Migration **024** (V2 Knowledge Platform) appliquée à `db_portfolio` : `knowledge_documents`,
`knowledge_entries` (append-only A1), `analysis_knowledge_refs` (snapshot figé), `eu_ir_scrapers`,
`knowledge_curator_reports`, pgvector + HNSW, vue `knowledge_federation_export`. Seed NVDA réel
(`backend/app/db/seeds/nvda_v2_knowledge_seed.sql`) → readiness `thin_qualitative`.
**Collision 023 résolue → séquence décalée +1** : 025 agents/provider · 026 analyses+research_memos ·
027 theses_flow · 028 exit/calibration.

### Git

Commit local **`8d8c698`** sur `main` (34 fichiers : tout `provenance-cards/` C1-C8 + `prompts/` +
viz). **Non poussé** — le push se fait au moment d'un déploiement (protocole DEPLOY.md).

## Prochaine étape — que du code, dans l'ordre de la chaîne (§18)

1. **Choisir le modèle ouvrier DeepInfra** (Llama-3.3-70B / Gemma-4-31B / Qwen — le mieux adapté aux
   tâches d'ouvrier : ingestion, search, gap, groundedness). Le métier est DeepSeek V4 Flash 0731.
2. **Abstraction provider** — `backend/app/agents/providers/` (**inexistant**) : interface
   `AgentProvider` (`complete`/`stream`), `deepinfra_provider.py` (endpoint OpenAI-compatible,
   `messages[]`/`tools[]`/`response_format`, clé `DEEPINFRA_API_KEY`), factory `get_provider(name)`
   lisant la config DB. **NE PAS calquer sur `dust_client.run_agent`.** + **migration 025**
   (`agent_prompts += provider, model, tools_json` ; inserts des nouveaux agents V2 avec les prompts
   de `prompts/`). Infra pure, débloque tous les agents. Contrat C1 prêt à câbler.
3. **Agents 3→6** (migration 026) : ingestion → curator → research → bull/bear/synthèse.
4. **Agents 7→9** (migrations 027/028) : décision/validate → monitoring m6 → sortie/calibration.
5. **Passe UX transverse finale** (§16) une fois les champs éprouvés.

**Piège migrations (§18)** : écrire chaque migration **juste avant** son lot, jamais en avance ; ne
jamais commencer un lot par le schéma de table.

## Rappels techniques (CLAUDE.md projet)

- `roadmap/provenance-cards/*.py` cible **pydantic v2** → tester dans le container backend
  (`portfoliobackend00000000-*`), **pas** le python hôte (v1). `docker cp` le dossier + `python`.
- asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations **appliquées
  manuellement** via `docker cp` + `psql -f` (pas d'auto-run au startup ; heredoc `docker exec` échoue
  silencieusement).
- Règle #19 : tout changement de contrat = 3 points de synchro (prompt agent · frontend · import).
- Coolify : **rebuild** (PHP, jamais restart) ; commit+push AVANT ; provider-agnostic côté agents.
- Viz servie par un container nginx **hors Coolify** (`provenance-viz`, bind-mount sur le fichier) ;
  éditer le HTML suffit (live). Onglets : research_memo · données NVDA · bull/bear · risk_matrix ·
  hypotheses · **conviction challenge (C7)** · **monitoring 1-5 (C8)** · dérivation.
