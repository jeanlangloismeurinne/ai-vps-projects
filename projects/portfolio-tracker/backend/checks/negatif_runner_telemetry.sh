#!/usr/bin/env bash
# TEST NÉGATIF de `check_runner_telemetry.py` §10 (jalon A1 bis) — le plafond d'écriture des tours de
# RECHERCHE du search-worker. Une mutation par décision, chacune exigeant exit≠0 + FAIL sur l'assert
# NOMMÉ + ligne de bilan atteinte (boucle : `_negatif.sh`, détenteur unique, #65).
#   bash checks/negatif_runner_telemetry.sh
#
# Les §1-§9 (comptabilité des échecs, #41) précèdent ce test négatif et n'y sont pas re-mutés.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_runner_telemetry.py"
RUN="app/agents/v2/runner.py"
WRK="app/agents/v2/worker.py"

mutations=(
# ── le plafond n'atteint plus le modèle pendant la recherche ──────────────────────────────────────
"$RUN¦convo, temperature=temperature, timeout=timeout, max_tokens=max_tokens_recherche)¦convo, temperature=temperature, timeout=timeout)  # mutation¦chaque tour de recherche reçoit le plafond"
# ── la clôture est plafonnée elle aussi (le JSON contractuel serait coupé) ───────────────────────
"$RUN¦temperature=temperature, max_repair=max_repair, timeout=timeout,¦temperature=temperature, max_repair=max_repair, timeout=timeout, max_tokens=max_tokens_recherche,  # mutation¦la clôture ne reçoit AUCUN plafond"
# ── un tour coupé exécute quand même ses appels d'outils (arguments tronqués) ────────────────────
"$RUN¦if tour_coupe or not last.tool_calls:¦if not last.tool_calls:  # mutation¦un tour coupé par le plafond n'exécute pas ses outils"
# ── run_tool_json_agent ne transmet plus le plafond à la boucle ──────────────────────────────────
"$RUN¦        max_tokens_recherche=max_tokens_recherche,¦        max_tokens_recherche=None,  # mutation¦chaque tour de recherche reçoit le plafond"
# ── le search-worker oublie le plafond (ou le recopie en dur au lieu de `settings`) ──────────────
"$WRK¦max_tokens_recherche=settings.WEB_TOUR_MAX_TOKENS,¦max_tokens_recherche=2048,  # mutation¦le search-worker passe"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
