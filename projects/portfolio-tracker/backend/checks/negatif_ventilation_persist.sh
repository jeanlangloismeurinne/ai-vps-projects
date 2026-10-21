#!/usr/bin/env bash
# TEST NÉGATIF de `check_ventilation_persist.py` — la publication de la ventilation (vraie base, ROLLBACK).
#   bash checks/negatif_ventilation_persist.sh
# Chaque mutation exige exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_ventilation_persist.py"
SRC="app/knowledge/ventilation_feed.py"
NET=coolify
export CHECK_DB_URL="$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)"

mutations=(
# Idempotence perdue : chaque passage publie une version, le dossier empile des ventilations identiques.
"$SRC¦    if courants and empreinte(courants[0][\"content_structured\"] or {}) == empreinte(structure):¦    if False:¦le même dépôt ne crée pas de version"
# Remplacement perdu : deux pièces courantes pour un même titre (#43 — combien de lignes actives ?).
"$SRC¦            fiscal_period=f\"AU {fin_du_fait}\", supersedes_entry_id=courants[0][\"id\"] if courants else None,¦            fiscal_period=f\"AU {fin_du_fait}\", supersedes_entry_id=None,¦après remplacement, UNE pièce courante"
# Refus bancaire retiré : JPM (statut `ventilee`, 3 segments) écrit réellement une pièce.
"$SRC¦    if gabarit_famille is None:¦    if False:¦refus NOMMÉ (famille bancaire)"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
