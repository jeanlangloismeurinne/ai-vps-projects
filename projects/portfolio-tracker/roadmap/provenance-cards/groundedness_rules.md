---
id: groundedness-rules
status: derivation
created: 2026-08-19
project: portfolio-tracker
role: >
  3ᵉ dérivé des cartes de provenance : les règles du groundedness-checker (A2). La colonne
  `nature` × `grounding` de la carte définit MÉCANIQUEMENT la vérification à appliquer à chaque
  champ. Garantie (2) « champ fondé ». Voir analysis_v2_schemas.py, readiness_derivation.md, §7/§13.3.
---

# Groundedness-checker (A2) — règles dérivées de la carte

Le `groundedness-checker` est un **ouvrier Haiku** (§5.2) invoqué par l'orchestrateur avec une
requête structurée. La traçabilité passe de **déclarative** (l'agent dit « sourcé sur entry_67 »)
à **vérifiée** (entry_67 contient-il vraiment le fait ?).

## Entrée / sortie

**Entrée** : `{ json_produit, snapshot_refs (A1 : analysis_knowledge_refs figés), card_meta }`
où `card_meta[path] = {nature, grounding, tier_floor, base_rate?}` — la carte projetée en données.

**Sortie** : `GroundingReport{ affirmations_total, etayees, non_etayees, verdicts[], blocking }`,
`verdicts[i] = {field_path, nature, status, grounding_score, refs_checked, note}`.
Ce rapport alimente `bull_case/bear_case.grounding_report` et est stocké par affirmation (§13.3).

## Règle de vérification par `nature × grounding`

| nature | grounding | Vérification | Coût |
|---|---|---|---|
| `factual` | direct | (a) refs non vides [Pydantic] · (b) `tier(entry) ≥ tier_floor` · (c) **LLM-judge** : l'entry citée *contient/soutient* le fait → sinon `unsupported` | LLM-judge |
| `judgment` | délégué(frère) | (a) le frère factuel (`preuves[]`…) est non vide & lui-même `grounded` · (b) **LLM-judge léger** : le jugement est *cohérent* avec les preuves (non contredit) → sinon `inconsistent` | LLM-judge léger |
| `derived` | hérité(inputs) | (a) inputs présents & `grounded` · (b) **si formule connue → recompute DÉTERMINISTE** (pas de LLM) ; sinon LLM-judge de cohérence | **déterministe** si formule |
| `ref` | — | `entry_id` ∈ snapshot (A1) | déterministe |
| `factual` (base_rate) | direct | `reference_class` non générique + entry `pattern_library`/corpus ; sinon flag `base_rate_fabrique` | LLM-judge léger |
| `checker` | — | c'est la **sortie** (`grounding_report`) — non vérifié | — |
| `contrôle` / `user` | — | `posture` = Literal [Pydantic] · `override_reason` présent (A7) | déterministe |

**Statuts** : `grounded · unsupported · inconsistent · ungrounded · base_rate_fabrique · skipped`.
`grounding_score` = 1.0 si `grounded`, sinon dégradé (LLM-judge) ; `non_etayees` = tout ce qui n'est
pas `grounded`. `blocking = true` si une affirmation d'un bloc **décisif** est `unsupported`/`inconsistent`.

## Économie (constitution §3) — déterministe d'abord, LLM-judge ensuite

Sous-segmentation : on n'appelle le LLM-judge que là où c'est irréductible.

- **Gratuit / déterministe** (aucun token LLM) : existence des `ref` dans le snapshot · planchers de
  tier · **recompute des `derived` à formule connue** · comptes de `sources_summary` · présence
  `override_reason`.
- **LLM-judge (Haiku, batché)** : « l'entry soutient-elle le fait ? » (`factual` direct) ·
  « le jugement est-il cohérent avec ses preuves ? » (`judgment` délégué) · plausibilité base-rate.
- **Prompt caching** : les `snapshot_refs` triés déterministe en **tête** ; les affirmations à vérifier
  en **fin**.

### `derived` à formule connue → recompute exact (exemples)
- `valuation.marge_securite_base_pct` = `(iv_base − prix_actuel) / prix_actuel × 100`
- `scenario_destruction_valeur.perte_pct` = `(prix_actuel − prix_bear) / prix_actuel × 100`
- `sources_summary.{tier_A,…,total}` = comptes recalculés depuis `snapshot_refs`
- `position_sizing.pct_formule` : borne dure (`≤ cap`) + monotonie (le facteur exact reste une
  constante de politique Kelly-fractionnaire)

Les `derived` narratifs (`roic_vs_wacc`, `reverse_dcf.verdict`, `relatif.vs_historique`,
`epv.valeur_rentabilite`) passent au LLM-judge de cohérence (pas de formule fermée).

## Insertion dans le flux (§7)

Le checker s'insère **après le curator** (memo) **et après bull/bear** : chaque affirmation reçoit
son `grounding_score` ; les affirmations non étayées sont **flaggées** (badge front) et, si un bloc
décisif est concerné, escaladent (`blocking`). C'est le pendant vérifié de la règle mémoire LLM
(`llm_memory`, reliability 0.40) : cold-start ≠ angle mort d'auditabilité.

## Ancrage
Cartes : `provenance-viz/index.html` + §8. Pydantic : `analysis_v2_schemas.py`. Readiness :
`readiness_derivation.md`. Audit : **A2** (groundedness), A1 (snapshot), §13.3 (stockage par affirmation).
