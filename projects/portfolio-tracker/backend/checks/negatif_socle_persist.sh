#!/usr/bin/env bash
# TEST NÉGATIF de `check_socle_persist.py` — la publication du socle des comptes (vraie base, ROLLBACK).
#   bash checks/negatif_socle_persist.sh
# Chaque mutation exige exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_socle_persist.py"
SRC="app/knowledge/socle_feed.py"
NET=coolify
export CHECK_DB_URL="$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)"

mutations=(
# Idempotence perdue : chaque passage publie une version, le dossier empile des socles identiques.
"$SRC¦    if courants and empreinte(courants[0][\"content_structured\"] or {}) == empreinte(structure):¦    if False:¦le même dépôt ne crée pas de version"
# Remplacement perdu : deux socles courants pour un même titre (#43 — combien de lignes actives ?).
"$SRC¦            supersedes_entry_id=courants[0][\"id\"] if courants else None,¦            supersedes_entry_id=None,¦UNE pièce courante"
# Datation : le socle daté du jour de son dépôt, plus du dernier fait qu'il constate (#79).
"$SRC¦            datation=constatee(date_du_fait=fin, date_du_document=filed),¦            datation=constatee(date_du_fait=filed, date_du_document=filed),¦datée du dernier fait"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
