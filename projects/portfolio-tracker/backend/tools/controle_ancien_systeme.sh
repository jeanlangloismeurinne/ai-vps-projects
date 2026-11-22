#!/usr/bin/env bash
# K13 — contrôle de la base de connaissance par l'ancien système (voir controle_ancien_systeme.py).
# Lecture seule ; `--en-memoire` relit au registre (gratuit) les dépôts que la collecte n'a pas demandés.
# Instance NEUVE de l'image, le code du dépôt monté par-dessus : jamais dans portfolio-backend.
#   bash tools/controle_ancien_systeme.sh [EMETTEUR …] [--en-memoire] [--detail]
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker run --rm --network coolify --env-file .env -v "$PWD":/app -w /app \
  portfolio-tracker-backend python tools/controle_ancien_systeme.py "$@"
