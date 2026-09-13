---
id: decision-validate-card
status: carte-de-provenance
created: 2026-08-21
updated: 2026-08-31
project: portfolio-tracker
role: >
  Carte de provenance du contrat de décision/validation (§9, migration 030) :
  POST /v2/theses/{id}/validate. La décision est CONTRAINTE par l'analyse (G2), indépendante de l'UX.
  Se cross-valide contre la synthèse (RiskMatrix). Pydantic : decision_validate_schema.py
  (17/17 vérifiés, container 2.13.4). Amendée le 2026-08-31 : support `theses_v2` (disjonction
  V1/V2) + renumérotation 026→030 — le contrat JSON lui-même est INCHANGÉ.
---

# Carte de provenance — Décision / validation de thèse

> ## ⚠ Amendement 2026-08-31 — support de persistance, PAS le contrat
>
> Cette carte a été figée le **2026-08-21**. Le principe des **deux espaces disjoints V1/V2** a été
> acté le **2026-08-22** — soit un jour plus tard. La carte est donc antérieure à la règle qu'elle
> enfreignait, et elle portait deux références devenues fausses :
>
> | Écrit dans la carte | Corrigé en | Pourquoi |
> |---|---|---|
> | `theses += colonnes` | table **`theses_v2`** | `theses` est la table pivot du flux V1 (positions, calendrier, monitoring, débats y pointent). Les migrations 026 ont créé des tables **neuves** (`research_memos`, `investment_analyses`) — étendre `theses` aurait été la première entorse à la disjonction, sur la table la plus chargée. |
> | `POST /theses/{id}/validate` | **`POST /v2/theses/{id}/validate`** | La route existe **déjà** en V1 (`api/thesis_v2.py:733`, corps `ValidateThesisBody`, sans les garde-fous G2). Collision réelle, pas théorique. |
> | « migration 026 (theses_flow) » | **migration 030** | Collision 023 : toute la séquence V2 décale de +1 (cf. CLAUDE.md). |
>
> **Ce qui ne change pas : le contrat.** `ThesisValidation` et ses 17 garde-fous (G2 verdict
> actionnable, bijection des acquittements, pont risques→hypothèses, cap Kelly, override A7,
> conditions, valuation) sont **strictement identiques**. L'amendement porte sur le *support de
> persistance et l'adressage*, jamais sur l'invariant décisionnel — c'est précisément la distinction
> que G1 protège. Le nom de fichier `api/thesis_v2.py` désigne la **2ᵉ version du fichier V1**, pas
> le flux V2 : piège de nommage à ne pas re-découvrir.

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

`POST /v2/theses/{id}/validate` — une fois `ThesisValidation` validée, exécute atomiquement :
`theses_v2.status='active'` · `tickers.status='portfolio'` · crée `portfolio_positions` (sizing) ·
`cash_movements(type='buy')` · `calendar_events` (modes 1/2 + **revue annuelle mode 6** planifiés).
Fige sur `theses_v2` : `synthesis_analysis_id`, `research_memo_id`, `pre_mortem_acked`,
`risk_matrix_acked`, `position_sizing_pct`, `valuation_range`, `conditions_entree`, hypothèses H1-Hn.

⚠ La validation du contrat précède la transaction : **aucun champ n'est figé qui ne soit passé par
`ThesisValidation`**. Un rejet du contrat n'écrit rien — c'est ce qui rend la décision contrainte
par l'analyse et non par l'UX (G2).

## Migration 030 (theses_flow) — table `theses_v2`

Table **neuve** `theses_v2` (et non `theses +=`, cf. amendement en tête) portant :
`research_memo_id, synthesis_analysis_id, pre_mortem_acked, risk_matrix_acked, position_sizing_pct,
conditions_entree, valuation_range, hypotheses`. **Ne pas écrire la migration avant ce contrat figé.**

*Reporté, pas abandonné* : la version initiale de cette carte annonçait aussi
`tickers += ingestion_status, edgar_cik, has_eu_scraper, v2_flow, too_complex_re_revue`. Ces colonnes
décrivent l'**ingestion** (lot 3) et la révisabilité `too_hard` (A10), pas l'acte de décision — les
écrire ici anticiperait un lot non joué, contre §18 (« migrations écrites juste avant leur lot »).
Elles restent dues à leurs lots respectifs. `edgar_cik` en particulier est aujourd'hui résolu à la
volée par `resolve_cik()` (convention #30) : sa persistance est une optimisation, pas un manque.

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
