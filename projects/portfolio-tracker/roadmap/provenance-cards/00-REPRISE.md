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

## Recommandation de suite (par ordre de levier, selon la spec)

1. **Lot 1 — Fondation données (§18-1), le socle.** Migration `023_v2_knowledge_platform.sql` :
   `knowledge_documents` ; `knowledge_entries` **versionnées / append-only** (A1 : `version`,
   `valid_from`, `superseded_by`) ; **`analysis_knowledge_refs`** (jointure snapshot figé — A1, le P0
   d'auditabilité) ; extension **pgvector** (DÉCISION #4). Puis **seed NVDA réel** (cas-pilote de la
   spec KP) → la couche données illustrative devient vivante et le groundedness-checker + le readiness
   deviennent exécutables sur un vrai cas. *Pourquoi en premier : tous les dérivés qu'on vient de
   structurer présupposent ce socle ; c'est le geste le plus rentable de l'audit (A1).*
2. **Carder `readiness_report_json` (curator, §7)** — le seul contrat majeur du chemin critique pas
   encore traité en carte/Pydantic (il gate tout le flux : coverage struct/qual, gaps[], verdict
   `not_ready|researching|thin_qualitative|ready|too_hard`). Rapide, complète la couche contrat.
3. **Générer les tickets du lot 6 (§18)** — les contrats sont désormais implémentables (UX /analyse
   3 colonnes → agents bull/bear/synthèse → migration 025 + snapshots).

## Rappels techniques (CLAUDE.md projet)

- `roadmap/provenance-cards/*.py` cible **pydantic v2** → tester dans le container backend
  (`portfoliobackend00000000-*`), **pas** sur le python hôte (v1). `docker cp` puis `python`.
- asyncpg `$1` (pas `%s`) ; JSONB auto-décodé (pas de `json.dumps`) ; migrations **appliquées
  manuellement** via `docker cp` + `psql -f` (pas d'auto-run au startup).
- Règle #19 : tout changement de contrat = 3 points de synchro (prompt agent · frontend · import).
- La viz est servie par un container nginx **hors Coolify** (`provenance-viz`, bind-mount sur le
  fichier) ; éditer le HTML suffit (live) ; suppr = `docker rm -f provenance-viz`.
