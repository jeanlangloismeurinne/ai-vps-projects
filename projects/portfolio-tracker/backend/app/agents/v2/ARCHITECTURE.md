# `agents/v2/` — le flux d'analyse V2/V3

> **Cible** (spec : `roadmap/V3/03-spec-frameworks.md` §3, `doctrine-trois-axes.md`, DÉCISION #1).
> **Réalisé** : prouvé par les `check_*.py` cités — les exécuter.

## Rôle

La couche 2 (agents), provider-agnostique. Deux boucles :
- **La boucle de décision V2** (Option C, DÉCISION #1) : base neutre → bull/bear isolés → réfutation
  asymétrique bear→bull → synthèse dialectique (seul verdict) → décider → surveiller → sortir → apprendre.
- **La chaîne de collecte V3** (§3.6) : à **deux agents** (le plan est persisté, sinon « mauvais plan
  ou mauvaise collecte ? » est indécidable), garantie par un **manager** aux 4 contrôles.

## Fichiers par rôle

| Fichier | Rôle |
|---|---|
| `traducteur.py` | Questions universelles → **plan de collecte** par ticker (métrique, source, ancre) |
| `collecteur.py` · `collecte_executor.py` | Plan → collecte réelle ; l'exécuteur route en **aveugle** (ne connaît pas la question, #60) |
| `collecte_persist.py` | Persistance du plan / liens / mandats |
| `analyste.py` | Réponses de framework ; refuse **avant dépense** ce que le pont refuserait (#63) |
| `curator.py` | Porte de complétude à 3 états + rôle de manager ; **aucun levier de modèle sur l'exigence** (#62) |
| `framework_persist.py` | Écriture append-only versionnée des réponses/dispenses (#64) |
| `common.py` | `MVDD_SPEC`, `FIELD_PROFILES`, `derive_nature` (détenteurs uniques) |
| `runner.py` | Boucle d'outils + tour de clôture JSON validé ; télémétrie de coût exacte (#41) |
| `worker.py` · `tools.py` | `search-worker` + exécuteurs des 3 outils |
| `debate.py` · `decision.py` · `exit.py` · `monitoring.py` · `analysis.py` | Maillons de la boucle V2 |

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Chaîne à deux agents, plan persisté, collecte aveugle | `check_traducteur.py`, `check_collecteur.py`, `check_collecte_executor.py`, `check_collecte_persist.py` |
| Analyste : refus avant dépense, 3 états, pas de levier | `check_analyste.py` + `negatif_analyste.sh` + `tools/acceptation_analyste.sh` (vrai modèle) |
| Porte à 3 états, remèdes distincts, lue au point de sortie | `check_readiness_recompute.py`, `tools/acceptation_gate.sh` |
| Décision contrainte par l'analyse (G2, #36) | `check_decision_validate.py` |
| Réfutation bear→bull + anti-complaisance | `check_exit_debate.py`, `check_monitoring_v2.py` |
| Télémétrie de coût (un abandon est facturé comme un succès) | `check_runner_telemetry.py` |
