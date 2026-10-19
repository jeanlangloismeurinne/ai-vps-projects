#!/usr/bin/env bash
# TEST NÉGATIF de `check_comite_persist.py` — l'ÉCRITURE du procès-verbal contre la vraie base
# (ROLLBACK, zéro résidu). Une mutation par décision de l'écrivain `comite.py` (et, #137, du
# chargeur du dossier qui lit la réinitialisation) ; les CHECK et les
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
# ── #137 : la réinitialisation, lue par le dossier ─────────────────────────────────────────────
"app/agents/v2/parcours.py¦            cree_le=cree_le.get(i), baisse=baisse))¦            cree_le=None, baisse=baisse))  # mutation: l'instant d'écriture n'atteint pas la règle¦APRÈS la réinitialisation la consomme"
"$C¦        question_id=question_id, action=\"reinitialiser\", answer_id=courante,¦        question_id=question_id, action=\"reinitialiser\", answer_id=None,¦relève la réponse COURANTE mise de côté"
"$C¦        raise DecisionRefusee(f\"aucune question applicable dans \`{framework_id}\` : rien à réinitialiser\")¦        return []  # mutation¦SANS question applicable est refusé"
"app/agents/v2/manager_persist.py¦        \"UPDATE framework_mandates SET statut = 'abandonne' WHERE id = \$1 AND statut = 'ouvert' \"¦        \"UPDATE framework_mandates SET statut = 'ouvert' WHERE id = \$1 AND statut = 'ouvert' \"¦REMPLACE le premier"
# ── point 13 : rétablir (migration 060) — l'attendu cible le LABEL (toujours dans la ligne FAIL),
# jamais le texte de l'exception d'origine : la mutation empêche justement cette exception-là.
"$C¦        precedente_row[\"question_id\"]) != (ticker_id, framework_id, version, question_id):¦        precedente_row[\"question_id\"]) != (ticker_id, framework_id, version, question_id) and False:  # mutation¦AUTRE dossier"
"$C¦        \"WHERE id = \$1 AND superseded_by IS NULL\", precedente_row[\"superseded_by\"])¦        \"WHERE id = (SELECT max(id) FROM framework_answers WHERE superseded_by IS NULL) OR id = \$1\", precedente_row[\"superseded_by\"])¦précédente IMMÉDIATE"
"$C¦    if baisse_a_lire(courante_rpb, precedente_rpb, decisions_q) is None:¦    if False:  # mutation: rétablir même sans baisse¦N'EST PAS une baisse"
"$C¦    if precedente_rpb.answer is None:¦    if False:  # mutation: rétablir même un contrat antérieur illisible¦contrat ANTÉRIEUR"
"$C¦        copie = await persist_answer_detail(conn, precedente_rpb.answer)¦        copie = await persist_answer_detail(conn, courante_rpb.answer)  # mutation: recopie la dégradée¦porte le STATUT de la PRÉCÉDENTE"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
