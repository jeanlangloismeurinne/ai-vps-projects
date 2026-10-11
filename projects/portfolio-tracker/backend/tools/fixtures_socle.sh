#!/usr/bin/env bash
# Lanceur de `tools/fixtures_socle.py` — régénère les fixtures du socle des comptes, copiées du réel.
# Réseau PUBLIC (data.sec.gov), NI base NI modèle. Instance neuve de l'image, dépôt monté en écriture
# sur le seul dossier des fixtures.
#
#   bash tools/fixtures_socle.sh RVMD NVDA MSFT --ecart    # ce qui changerait, sans écrire
#   bash tools/fixtures_socle.sh RVMD NVDA MSFT            # écrit
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -v "$PWD/checks/fixtures/socle_comptes:/app/checks/fixtures/socle_comptes" \
  -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" python tools/fixtures_socle.py "$@"
