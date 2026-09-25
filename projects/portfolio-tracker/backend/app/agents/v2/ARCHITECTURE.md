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
| `dossier.py` | **Détenteur unique** de l'assemblage du corpus remis à l'analyste (#46) : une chemise par point de la liste du comité — clef `(question_id, ingredient_id)` LUE de `question_coverage` (#29/#57), jamais la ligne de plan (elle dérive à chaque run) ; la pièce la plus récente en vigueur, les antérieures gardées en base et comptées, les pièces hors index jointes ; le plafond mord sur le reste, **jamais** sur une pièce en vigueur |
| `analyste.py` | Réponses de framework ; refuse **avant dépense** ce que le pont refuserait (#63) |
| `manager.py` | **Manager** d'un framework — 4 contrôles déterministes (complétude · fondation · honnêteté · non-substitution), acquitte ou renvoie ; un renvoi PRODUIT un mandat (ferme l'Écart B, §3) |
| `apparieur.py` · `appariement_persist.py` | Appariement questions↔champs-EDGAR (3 états) ; persistance UPSERT + revérification à la lecture (#54) |
| `curator.py` | Porte de complétude à 3 états + rôle de manager ; **aucun levier de modèle sur l'exigence** (#62) |
| `framework_persist.py` | Écriture append-only versionnée des réponses/dispenses (#64) |
| `manager_persist.py` | Persistance du **mandat** du manager + son cycle de vie (ouvert→servi) ; l'avis se **recalcule** à la lecture, jamais stocké (#53/#54, arbitrage 2026-09-21) — migration 043 (#77) ; `id_du_mandat_ouvert` détenteur unique du handle à servir |
| `bouclage.py` | **Bouclage comité → collecte** (lot 5, #71) — lit les renvois ouverts (`read_open_mandates`), refait la recherche PAR LE MÊME PROCESSUS scopé aux questions renvoyées (`executer_collecte_framework(questions=…)`, #46 : pas de chemin parallèle), re-répond, SERT les mandats (`serve_mandate`) et rend une note à 4 sorts (`classer_sort`, détenteur unique) |
| `common.py` | `MVDD_SPEC`, `FIELD_PROFILES`, `derive_nature` (détenteurs uniques) |
| `runner.py` | Boucle d'outils + tour de clôture JSON validé ; télémétrie de coût exacte (#41) |
| `worker.py` · `tools.py` | `search-worker` + exécuteurs des 3 outils |
| `debate.py` · `decision.py` · `exit.py` · `monitoring.py` · `analysis.py` | Maillons de la boucle V2 |

## Cible → garde (réalisé)

| Invariant cible | Garant |
|---|---|
| Chaîne à deux agents, plan persisté, collecte aveugle | `check_traducteur.py`, `check_collecteur.py`, `check_collecte_executor.py`, `check_collecte_persist.py` |
| Carte d'appariement persistée, revérifiée à la lecture (#54), UPSERT sans historique | `check_appariement_persist.py` + `negatif_appariement_persist.sh` |
| Dossier : un point = une chemise, la plus récente en vigueur, le plafond ne coupe jamais une pièce en vigueur, la datation hétérogène est NOMMÉE | `check_dossier.py` + `negatif_dossier.sh` + `tools/montrer_dossier.sh` (lecture du dossier réel, gratuite) |
| Analyste : refus avant dépense, 3 états, pas de levier | `check_analyste.py` + `negatif_analyste.sh` + `tools/acceptation_analyste.sh` (vrai modèle) |
| Manager : 4 contrôles déterministes, chaque `ko` atteignable, renvoi → mandat | `check_manager.py` + `negatif_manager.sh` |
| Mandat manager persisté (par-question, réconcilié avec la table 039), consommable, statut qui change au re-run (T8) | `check_manager_persist.py` + `negatif_manager_persist.sh` + `tools/acceptation_manager.sh` |
| Bouclage comité → collecte : renvois relus et servis (EXERCÉ, pas seulement vert — appelants comptés en prod, #71), même processus scopé (#46), note honnête à 4 sorts (`acquis`/`collecte_insuffisante`/`mandat_non_executable`/`classe_sans_suite`) distinguant « collecte insuffisante » de « mandat pas clair » | `check_bouclage.py` + `negatif_bouclage.sh` + `tools/acceptation_bouclage.sh` (wiring DB de bout en bout contre la vraie base, ROLLBACK, zéro résidu) + `tools/boucler_renvois.sh` (passage réel complet, vrai modèle, écrit en prod) |
| Note de comité PROJETÉE : ne publier que l'instruit, 4 états de rubrique jamais fusionnés, l'ordre du jour couvert en entier — et surtout **ajouter une méthodologie est une opération de DONNÉES** (un 3ᵉ framework en YAML seul se projette sans diff de code) | `check_memo_projete.py` + `negatif_memo_projete.sh` + `tools/montrer_memo_projete.sh` (lecture de la note réelle, gratuite) |
| Porte à 3 états, remèdes distincts, lue au point de sortie | `check_readiness_recompute.py`, `tools/acceptation_gate.sh` |
| Table de profils par champ (`FIELD_PROFILES` dans `common.py`) | `check_field_profiles.py` |
| Décision contrainte par l'analyse (G2, #36) | `check_decision_validate.py` |
| Réfutation bear→bull + anti-complaisance | `check_exit_debate.py`, `check_monitoring_v2.py` |
| Télémétrie de coût (un abandon est facturé comme un succès) | `check_runner_telemetry.py` |
