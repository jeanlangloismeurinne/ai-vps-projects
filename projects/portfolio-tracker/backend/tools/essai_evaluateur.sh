#!/usr/bin/env bash
# Essai réel de l'évaluateur des sources inconnues, en mémoire (voir essai_evaluateur.py).
# Instance NEUVE de l'image, le code du dépôt monté par-dessus : jamais dans portfolio-backend.
#   bash tools/essai_evaluateur.sh <domaine> [adresse rencontrée …]
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker run --rm --network coolify --env-file .env -v "$PWD":/app -w /app \
  portfolio-tracker-backend python tools/essai_evaluateur.py "$@"
