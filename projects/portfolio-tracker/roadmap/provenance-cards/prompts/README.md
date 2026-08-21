---
id: prompts-v2-index
status: chantier-prompts
created: 2026-08-21
project: portfolio-tracker
role: >
  Index des prompts système V2 des agents, réécrits pour la logique métier figée par les cartes de
  provenance (flux données → analyses). Cible d'exécution : provider DeepInfra (endpoint
  OpenAI-compatible). Modèle métier par défaut : DeepSeek V4 Flash 0731 ; ouvriers sur un modèle
  DeepInfra plus léger (choix arrêté au moment de la migration 025).
---

# Prompts agents V2 — réécriture calée sur les cartes de provenance

Ces prompts sont le **3ᵉ point de synchronisation** (règle #19) : le schéma JSON de sortie de chaque
prompt doit rester identique au Pydantic (`*_schema.py`, `analysis_v2_schemas.py`) et au frontend/import.
Toute évolution de contrat se répercute sur les trois en même temps.

## Cible technique

- **Provider** : DeepInfra, endpoint **OpenAI-compatible** (`/v1/openai/chat/completions`,
  `messages[]`, `tools[]`, `response_format`). Câblé via `providers/` (factory `get_provider`, lot 2).
- **Modèles** (defaults figés en migration 025, `agent_prompts.model`) :
  - Métier (research/bull/bear/synthèse/curator) → **DeepSeek V4 Flash 0731**.
  - Ouvriers (ingestion/search/gap/groundedness) → modèle DeepInfra plus léger (Llama/Gemma/Qwen —
    arrêté à la migration).
- **Stateless** : l'agent ne conserve aucun état ; tout l'historique/contexte pertinent est passé
  dans le message. Le préfixe `[mode: …]` (existant V1) reste la convention d'aiguillage interne.
- **Sortie** : JSON strict **uniquement** (aucune prose hors JSON), conforme au schéma de l'agent,
  `extra='forbid'` (aucun champ hors contrat).

## Préambule commun

Tout prompt d'agent est **préfixé** par [`00-preambule-commun.md`](00-preambule-commun.md) : mission,
3 garde-fous (G1/G2/G3), framework de fiabilité (source_type→tier→score), interface de délégation,
grammaire des `knowledge_entries`, discipline JSON. Les fichiers par agent ne redéfinissent que leur
rôle, leurs entrées, leur schéma de sortie et leurs garde-fous spécifiques.

## Chaîne amont → analyses (priorité de ce chantier)

| # | Fichier | Agent | Tier | Carte / schéma source |
|---|---|---|---|---|
| 10 | [10-ingestion-agent.md](10-ingestion-agent.md) | `ingestion-agent` (mode llm) | ouvrier | `ingestion_extraction_card.md` |
| 11 | [11-search-worker.md](11-search-worker.md) | `search-worker` | ouvrier | `worker_delegation_card.md` |
| 12 | [12-gap-intake.md](12-gap-intake.md) | `gap-intake` | ouvrier | `worker_delegation_card.md`, §7 |
| 13 | [13-groundedness-checker.md](13-groundedness-checker.md) | `groundedness-checker` | ouvrier | `groundedness_rules.md` |
| 20 | [20-knowledge-curator.md](20-knowledge-curator.md) | `knowledge-curator` | métier léger | `readiness_report_card.md`, `context_pack_card.md` |
| 30 | [30-research-agent.md](30-research-agent.md) | `research-agent` | métier | `analysis_v2_schemas.py` (ResearchMemo) |
| 40 | [40-bull-agent.md](40-bull-agent.md) | `bull-agent` | métier | `analysis_v2_schemas.py` (BullCase) |
| 41 | [41-bear-agent.md](41-bear-agent.md) | `bear-agent` | métier | `analysis_v2_schemas.py` (BearCase) |
| 50 | [50-thesis-agent-synthese.md](50-thesis-agent-synthese.md) | `thesis-agent` | métier | `analysis_v2_schemas.py` (RiskMatrix + Hypothese) |

## Chaîne aval — décision / suivi / sortie

| # | Fichier | Agent | Tier | Carte / schéma source |
|---|---|---|---|---|
| 60 | [60-debate-agent.md](60-debate-agent.md) | `debate-agent` | métier | `debate_conviction_card.md` / `debate_conviction_schema.py` (figé) |
| 70 | [70-monitoring-agent.md](70-monitoring-agent.md) | `monitoring-agent` (modes 1-6) | mixte | `monitoring_mode6_card.md` (mode 6) + `monitoring_modes_1_5_card.md` (modes 1-5) — figés |
| 80 | [80-postmortem-agent.md](80-postmortem-agent.md) | `postmortem-agent` | ouvrier | `exit_calibration_card.md` (ExitPlan/PostMortem/Calibration) |

> **Tous les contrats de sortie sont désormais figés** (carte + Pydantic vérifié en container 2.13.4).
> Le conviction challenge (`ConvictionChallenge`) et les monitoring modes 1-5 (union `Mode1..Mode5`)
> ont été cardés le 2026-08-21, complétant le mode 6 et les 3 contrats du postmortem déjà figés.

## Statut

Réécriture en cours (2026-08-21). Une fois les prompts validés, ils alimentent les `INSERT` de la
**migration 025** (`agent_prompts` += `provider`, `model`, `tools_json`) et sont recopiés dans la
config provider. Ne pas écrire la migration avant validation des prompts (§18 : jamais commencer un
lot par le schéma de table).
