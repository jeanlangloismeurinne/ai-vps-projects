---
id: decision-validate-card
status: carte-de-provenance
created: 2026-08-21
project: portfolio-tracker
role: >
  Carte de provenance du contrat de décision/validation (§9, migration 026) : POST /theses/{id}/validate.
  La décision est CONTRAINTE par l'analyse (G2), indépendante de l'UX. Se cross-valide contre la
  synthèse (RiskMatrix). Pydantic : decision_validate_schema.py (17/17 vérifiés, container 2.13.4).
---

# Carte de provenance — Décision / validation de thèse

## Ce qui distingue cette carte

Ce n'est pas un JSON d'agent : c'est le **contrat de l'acte de décision**. C'est le point où **G2
s'exerce le plus fort** — la décision est *contrainte par l'analyse, indépendante de l'UX*.
L'utilisateur ne « saisit » pas une position ; il **acquitte une analyse**, et le contrat vérifie que
l'acte est cohérent avec le verdict, le sizing capé et les risques de la synthèse. C'est le pendant
décisionnel du `ready` forcé rejeté au readiness : ici, un `PROCEED` sur des risques non acceptés,
ou un sizing au-dessus du plafond Kelly, est **rejeté à la construction**.

Le contrat ne recopie pas la synthèse — il la **référence** (`RiskMatrix`) et se **cross-valide**
contre elle. Même schéma d'enveloppe que C1 (`WorkerExchange`) : les invariants vivent sur le
couple {analyse, décision}, pas sur l'un des deux isolément.

## Twin table — décision (A) & figement/traçabilité (B)

| Champ | nature | grounding | Vérification (G2) | Provisioning (figé au validate) |
|---|---|---|---|---|
| `synthesis.verdict` | **contrôle** | hérité (synthèse) | ∈ {PROCEED, PROCEED_AVEC_CONDITIONS} — les 3 autres ne créent pas de position | `investment_analyses` (synthèse) |
| `risk_acks[]` | **contrôle** | — | **bijection stricte** avec `synthesis.risques_acceptes` (chaque risque acquitté 1×) ; `accepted=Literal[True]` | acquittement utilisateur (§9) |
| `pre_mortem_acked` | **contrôle** | — | `True` obligatoire | acquittement utilisateur (§9) |
| `hypotheses[]` | **factual** | refs | pont risque→hypothèse (chaque `hypothese_liee` existe) ; `seuil_invalidation` porté | figées → pilotent le monitoring |
| `position_sizing_pct` | **derived** | hérité (sizing) | ≤ `pct_max` ; = `pct_recommande` **sauf** override tracé A7 (= `override.valeur_pct`) | `theses.position_sizing_pct` |
| `conditions_entree` | **ref** | hérité | non vide si `PROCEED_AVEC_CONDITIONS` | `theses.conditions_entree` |
| `valuation_range` | **factual** | hérité (research/valuation) | `low ≤ base ≤ high` | `theses.valuation_range` |
| `synthesis_analysis_id` · `research_memo_id` | **ref** | — | FK figées (lignée d'auditabilité) | `theses.*` |

## Garde-fous encodés (decision_validate_schema.py — 17/17 vérifiés)

- **G2 — verdict actionnable seulement.** On ne valide QUE `PROCEED` / `PROCEED_AVEC_CONDITIONS`.
  `PASSER`/`SURVEILLER`/`TOO_HARD` sont rejetés : pas de position depuis un non-verdict.
- **§9 — acquittements complets (bijection).** `risk_acks` couvre **exactement** les
  `risques_acceptes` (aucun risque silencieux, aucun ack fantôme). `pre_mortem_acked=True` requis.
  C'est l'invariant que le bouton « Valider » matérialise côté UX — mais il est vérifié au contrat,
  pas confié à l'UX.
- **Q6 — sizing borné et non libre.** `position_sizing_pct ≤ pct_max` (cap Kelly sectoriel) **et**
  égal à `pct_recommande`, sauf **override tracé (A7)** où il doit égaler `override_utilisateur.valeur_pct`.
  Aucun sizing arbitraire ne passe.
- **Falsifiabilité.** Chaque risque accepté pointe une hypothèse existante (`valider_pont_risques_
  hypotheses`) ; chaque hypothèse porte son `seuil_invalidation` (hérité de `Hypothese`) — le
  monitoring n'escaladera que sur franchissement de ce seuil pré-enregistré (anti-churn §10).
- **Conditions figées.** `PROCEED_AVEC_CONDITIONS` ⇒ `conditions_entree` non vide.
- **Valuation cohérente.** `low ≤ base ≤ high`.

## Transaction atomique (§9, convention CLAUDE.md #13)

`POST /theses/{id}/validate` — une fois `ThesisValidation` validée, exécute atomiquement :
`thesis.status='active'` · `tickers.status='portfolio'` · crée `portfolio_positions` (sizing) ·
`cash_movements(type='buy')` · `calendar_events` (modes 1/2 + **revue annuelle mode 6** planifiés).
Fige sur `theses` : `synthesis_analysis_id`, `research_memo_id`, `pre_mortem_acked`,
`risk_matrix_acked`, `position_sizing_pct`, `valuation_range`, `conditions_entree`, hypothèses H1-Hn.

## Migration 026 (theses_flow) — colonnes ajoutées

`theses += research_memo_id, synthesis_analysis_id, pre_mortem_acked, risk_matrix_acked,
position_sizing_pct, conditions_entree, valuation_range`. `tickers += ingestion_status, edgar_cik,
has_eu_scraper, v2_flow, too_complex_re_revue`. **Ne pas écrire la migration avant ce contrat figé.**

## Les 3 points de synchronisation (G1, règle #19)

1. **Backend décision** — la route `validate` construit et valide `ThesisValidation` AVANT la
   transaction ; aucun champ figé qui ne soit passé par le contrat.
2. **Frontend** — `RiskMatrixPanel` (un « J'accepte » par risque) + `PreMortemPanel` +
   `PositionSizingWidget` (min/reco/max + justification si override) ; bouton « Valider » = les
   invariants ci-dessus, en miroir.
3. **Import / validation** — `decision_validate_schema.py`.

## Ancrage

- Pydantic vérifié (2.13.4, container backend) : `decision_validate_schema.py` — 17 cas (G2 verdict,
  bijection acks, pré-mortem, pont hypothèses, cap Kelly, override A7, conditions, valuation).
- Réutilise `RiskMatrix`/`Hypothese`/`valider_pont_risques_hypotheses` d'`analysis_v2_schemas.py` (§8.4-8.5).
- Amont : synthèse (`risk_matrix_json`). Aval : monitoring (les hypothèses figées ici pilotent
  les modes 2/3/6) — carte C5.
