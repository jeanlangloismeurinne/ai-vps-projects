---
id: reprise-cartes-provenance
status: prompt-de-reprise
created: 2026-08-19
project: portfolio-tracker
role: Prompt à coller pour reprendre le chantier « cartes de provenance V2 » plus tard.
---

# Prompt de reprise — chantier cartes de provenance V2

Colle ceci pour reprendre :

> Reprise du chantier **cartes de provenance champ-par-champ** des JSON d'analyse V2 de
> portfolio-tracker (fondation d'auditabilité). Principe directeur UX → agents → données, 3
> garde-fous (G1 schéma versionné = source unique / G2 décision contraint l'UX / G3 donnée
> versionnée+scorée+figée). DÉCISION #1 = Option C (base neutre → bull/bear isolés → réfutation
> asymétrique bear→bull → synthèse). Contrats figés §8 de `01-spec-v2-unifiee.md`.
>
> LIRE AVANT : `roadmap/00-principe-directeur-v2.md` ; `roadmap/01-spec-v2-unifiee.md` (§7 curator/
> readiness, §8 contrats + amendement 2026-08-19, §13 auditabilité, §14 migrations 023-027, §18
> découpage) ; `roadmap/provenance-cards/` (analysis_v2_schemas.py, readiness_derivation.md,
> groundedness_rules.md, groundedness_checker.py) ; visuel : https://provenance.jlmvpscode.duckdns.org
> (onglets research_memo · couche données NVDA · bull/bear · risk_matrix · hypotheses · dérivation).

## Ce qui est FAIT (2026-08-18 → 19)

- **4 JSON cartographiés** (grain feuille, twin tables A validation+grounding / B provisioning+
  traçabilité) : `research_memo` · `bull_case`/`bear_case` · `risk_matrix` · `thesis.hypotheses[]`.
- **Findings #1-#3 intégrés au contrat** (spec §8.0/§7, note d'amendement §8) : #1 `management.
  source_entry_refs` + dimension MVDD *management & allocation* ; #2 `moat.durabilite_ans.base_rate` ;
  #3 `industry.croissance_marche_{historique,prospective}`.
- **Les 4 dérivés de la carte** (« 1 source → 4 consommateurs », G1) :
  - Pydantic versionné `analysis_v2_schemas.py` (`SCHEMA_VERSION=v2.0.0`) — **vérifié en container
    backend (pydantic 2.13.4)** : Q2 verrouillé, refs factual obligatoires (#1), edge obligatoire (R6),
    cap sizing (Q6).
  - Readiness `readiness_derivation.md` — couverture = projection des champs *factual* du memo sur les
    dimensions MVDD (tier plancher) ; calculable avant recherche.
  - Groundedness A2 `groundedness_rules.md` + `groundedness_checker.py` — vérif par nature×grounding ;
    déterministe d'abord (recompute derived/comptes/tier/refs, **vérifié en container**), LLM-judge Haiku ensuite.
  - Visualisation `provenance-viz/index.html` (18 diagrammes Mermaid).

## Lot 1 — FAIT (2026-08-19)

- **Migration `024_v2_knowledge_platform.sql`** appliquée à `db_portfolio` (collision 023 : le nom
  `023_v2_...` de la spec §14 était pris par `purchase_price_eur` déjà appliqué → **toute la séquence
  V2 décale de +1** : 024 platform (fait), 025 agents/provider, 026 analyses+research_memos, 027
  theses_flow, 028 exit/calibration). Contenu : `knowledge_documents` ; `knowledge_entries`
  **versionnées/append-only** (A1 : `version`, `valid_from`, `superseded_by`, + questions ouvertes
  `question_status/priority`, `resolves_entry_id`, soft-delete) ; **`analysis_knowledge_refs`**
  (snapshot figé A1/A2 : `entry_version`, `content_snapshot`, `reliability_at_use`, `field_path` ;
  `analysis_id` en INT nu → FK posée en 026) ; `eu_ir_scrapers` ; `knowledge_curator_reports`
  (mvdd|readiness|lint) ; **pgvector + index HNSW** (préféré à ivfflat : pas d'entraînement, inserts
  incrémentaux) ; vue **`knowledge_federation_export`** (enveloppe commune, `KNOWLEDGE_ARCHITECTURE.md`
  §3 — vérifiée conforme aux 17 champs du contrat).
- **Seed NVDA réel** `backend/app/db/seeds/nvda_v2_knowledge_seed.sql` (idempotent) : **10
  `fact_financial` Tier A tirés d'EDGAR** (10-K FY2026 réel, accession 0001045810-26-000021 ; revenue
  FY2024-26 60,9/130,5/215,9 Md$, résultat net, marge brute, OCF, bilan) + **5 qualitatifs
  `llm_memory`** (Tier C, `requires_human_review`, filet tracé cold-start §6.6). Projection
  readiness = **`thin_qualitative`** (structurée Tier A ✅ / qualitatif sous plancher ❌) : le
  garde-fou anti-faux-complet démontré sur un vrai cas. Le groundedness-checker + le readiness sont
  désormais exécutables sur des entries réelles.

## Lot 2 — FAIT (2026-08-20)

- **`readiness_report_json` cardé** (curator, §7) — dernier contrat majeur du chemin critique.
  Carte `readiness_report_card.md` (twin table nature×grounding + mapping table) + Pydantic
  `readiness_report_schema.py` **vérifié en container backend (2.13.4)** sur le cas NVDA réel →
  `thin_qualitative`. Particularité : **presque tout `derived` à formule connue** (recompute
  déterministe, aucun token LLM) — gate bon marché placé AVANT toute dépense Opus. Garde-fous
  encodés : **G2** verdict contraint par la coverage (`compute_verdict` ; un `ready` forcé sur
  dossier mince est rejeté — anti-faux-complet) ; `ok`/`bloc_ok` dérivés (déclaration incohérente
  refusée) ; **A3** conviction/marge_securite = None au readiness ; gate d'explicabilité (NO-GO
  muet interdit) ; `ready ⇒ context_pack_entry_id`. **La couche contrat est complète** : les 5 JLM
  majeurs sont cardés + Pydantic (research_memo · bull/bear · risk_matrix · hypotheses[] · readiness).
  Stockage : `knowledge_curator_reports` (déjà en place, migration 024) — pas de nouvelle migration.

## Lot 3 — FAIT (2026-08-21) : couche contrat COMPLÈTE de bout en bout (2→9)

Stratégie retenue : **carder TOUS les contrats métier manquants avant la moindre ligne de code**
(UX repoussée en toute fin, « on dessine une fois qu'on connaît les champs remplis »). Les 6
contrats des deux bouts de chaîne (amont ingestion, aval décision/monitoring/sortie) sont désormais
cardés + Pydantic **vérifiés en container (2.13.4)**, complétant les 5 déjà figés (research_memo ·
bull/bear · risk_matrix · hypotheses[] · readiness). **8 schémas, un `SCHEMA_VERSION=v2.0.0` unique,
importés ensemble sans conflit.**

- **C1 — `worker_delegation_schema.py`** (interface orchestrateur→ouvrier §5.2, 18/18) : requête
  structurée `{query, output_schema, reliability_min}` → entries scorées, jamais de texte libre (G3).
  Définit `ProducedEntry` (forme d'une knowledge_entry produite), **partagée avec C2**. Garde-fous :
  reliability_min honoré, plafond de source (§6.3), P2 llm_memory, déclaration d'exécution §5.3, A6 divergent.
- **C2 — `ingestion_extraction_schema.py`** (doc → entries §6.5, 14/14) : **anti-hallucination
  financière** (nombres via XBRL/yfinance déterministe 0 token ; le LLM ne produit jamais de
  `fact_financial`), déterministe=gratuit (§6.6), source cohérente au document, confidentiel tracé,
  matérialité 0.3, A1 supersedes_period.
- **C3 — `context_pack_schema.py`** (curator §7+§5.3, 10/10) : artefact distillé front-loadé,
  A2 (chaque dim cite ses refs), ready-only, 8 dims MVDD complètes, **discipline de cache = invariant
  du contrat** (ordre canonique + refs triées, aucun champ volatil).
- **C4 — `decision_validate_schema.py`** (validate §9, 17/17) : décision **contrainte par l'analyse**
  (G2), se cross-valide contre `RiskMatrix`. Verdict actionnable only, bijection risk_acks↔risques,
  pré-mortem acquitté, cap Kelly (sizing ≤ pct_max, override tracé A7), pont hypothèses.
- **C5 — `monitoring_mode6_schema.py`** (revue annuelle + thermomètre §10/§11, 14/14) :
  **anti-seuil-mécanique** (sortie valorisation = arbitrage rendement prospectif, jamais `Prix>IV×1.15`),
  **thermomètre `contraignant=Literal[False]`** (ne vend jamais seul), explicabilité de sortie.
- **C6 — `exit_calibration_schema.py`** (sortie/post-mortem/calibration §11/§12, 15/15) : sortie
  **thèse-driven** (origine typée), tranches Σ≤100, **post-mortem couvre exactement les hypothèses
  figées** (bijection, `valider_postmortem_couvre`), leçons taguées→pattern_library, calibration A5.

Chaque contrat a sa carte `*_card.md` (twin table + garde-fous + 3 points de synchro + stockage).

## Recommandation de suite — la couche contrat n'est plus le chemin critique

**Toute la logique métier est figée** ; il ne reste que du code, dans l'ordre de la chaîne runtime
(chaque lot = agent + migration, l'UX en réserve pour une passe transverse finale) :

1. **Lot 2 — abstraction provider** (`backend/app/agents/providers/` n'existe pas encore) : factory
   `get_provider` + `litellm_provider.py`/`dust_provider.py` + **migration 025** (`agent_prompts +=
   provider, model, tools_json`). Infra pure, débloque tous les agents. Contrat C1 prêt à câbler.
2. Puis **3 (ingestion) → 4 (curator) → 5 (research) → 6 (analyse)** : agents + migration 026, en
   suivant les cartes C2/C3 + readiness + les 4 cartes d'analyse.
3. **7 (décision, migr. 027) → 8 (monitoring m6) → 9 (sortie, migr. 028)** : cartes C4/C5/C6.
4. **Passe UX finale transverse** (§16) une fois tous les champs éprouvés en prod.

**Piège migrations** : ne pas écrire 026/027/028 en avance — les cartes figent les champs, mais
écrire la migration juste avant son lot (jamais commencer un lot par le schéma de table, §18).

## Rappels techniques (CLAUDE.md projet)

- `roadmap/provenance-cards/*.py` cible **pydantic v2** → tester dans le container backend
  (`portfoliobackend00000000-*`), **pas** sur le python hôte (v1). `docker cp` puis `python`.
- asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations **appliquées
  manuellement** via `docker cp` + `psql -f` (pas d'auto-run au startup).
- Règle #19 : tout changement de contrat = 3 points de synchro (prompt agent · frontend · import).
- La viz est servie par un container nginx **hors Coolify** (`provenance-viz`, bind-mount sur le
  fichier) ; éditer le HTML suffit (live) ; suppr = `docker rm -f provenance-viz`.
