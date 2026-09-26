#!/usr/bin/env bash
# TEST NÉGATIF de `check_comite_persist.py` — l'ÉCRITURE du procès-verbal contre la vraie base
# (ROLLBACK, zéro résidu). Une mutation par décision de l'écrivain `comite.py` ; les CHECK et les
# droits de la table sont éprouvés par `negatif_048.sh` (sur une copie de la base, avant application).
#
#   bash checks/negatif_comite_persist.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_comite_persist.py"
NET=coolify
CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
C="app/agents/v2/comite.py"
mutations=(
"$C¦        await abandonner_mandat(conn, ouvert)¦        pass  # mutation: la recherche continue¦la recherche en cours est ARRÊTÉE"
"$C¦    if rep[\"superseded_by\"] is not None:¦    if False:  # mutation: une réponse remplacée s'accepte¦REMPLACÉE depuis est refusé"
"$C¦    if (rep[\"ticker_id\"], rep[\"framework\"], rep[\"framework_version\"], rep[\"question_id\"]) != (¦    if False and (rep[\"ticker_id\"], rep[\"framework\"], rep[\"framework_version\"], rep[\"question_id\"]) != (¦AUTRE question est refusé"
"$C¦        \"WHERE ticker_id = \$1 AND framework_version = \$2 ORDER BY id DESC\",¦        \"WHERE ticker_id = \$1 AND framework_version = \$2 ORDER BY id\",¦le plus récent d'abord"
"$C¦    if fait_de_l_ancre(ancre)[0] == \"unavailable\":¦    if False:  # mutation¦faits ILLISIBLES est refusé"
"app/agents/v2/manager_persist.py¦        \"UPDATE framework_mandates SET statut = 'abandonne' WHERE id = \$1 AND statut = 'ouvert' \"¦        \"UPDATE framework_mandates SET statut = 'ouvert' WHERE id = \$1 AND statut = 'ouvert' \"¦REMPLACE le premier"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
