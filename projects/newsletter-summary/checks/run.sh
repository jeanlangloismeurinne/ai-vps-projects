#!/usr/bin/env bash
# Lance un check dans un conteneur JETABLE de la même image que la prod (mêmes dépendances),
# contre une base JETABLE `db_ns_scratch` (créée puis supprimée) — jamais la base de prod.
#
#   checks/run.sh checks/check_xxx.py [args…]
#
# - PROD_DATABASE_URL (lecture seule, pour capturer des lignes réelles) = DATABASE_URL du .env.
# - PYTHONDONTWRITEBYTECODE=1 : pas de __pycache__ (un .pyc périmé fabrique un faux vert).
# - Le lanceur vit ICI (versionné), pas dans /tmp : la suite doit être rejouable à l'identique.
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="${NS_IMAGE:-newsletter-summary-newsletter-summary:latest}"
SCRATCH=db_ns_scratch
PROD_URL="$(grep -E '^DATABASE_URL=' .env | cut -d= -f2-)"
SCRATCH_URL="${PROD_URL%/*}/${SCRATCH}"
docker exec shared-postgres psql -U admin -q -c "DROP DATABASE IF EXISTS ${SCRATCH}" -c "CREATE DATABASE ${SCRATCH} OWNER newsletter" >/dev/null
trap 'docker exec shared-postgres psql -U admin -q -c "DROP DATABASE IF EXISTS ${SCRATCH}" >/dev/null' EXIT
docker run --rm --network coolify -v "$PWD":/w -w /w --env-file .env \
  -e DATABASE_URL="$SCRATCH_URL" -e PROD_DATABASE_URL="$PROD_URL" \
  -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/w "$IMAGE" python "$@"
