#!/usr/bin/env bash
# Lanceur de `tools/extraire_fixture_ventilation.py` — fixture de ventilation publiée, copiée du réel.
# Réseau PUBLIC (data.sec.gov), NI base NI modèle. Instance neuve de l'image, dépôt monté en écriture
# sur le seul dossier des fixtures de ventilation.
#
#   bash tools/extraire_fixture_ventilation.sh NVDA 0001045810-26-000021
#   bash tools/extraire_fixture_ventilation.sh NVDA 0001045810-26-000075
#   bash tools/extraire_fixture_ventilation.sh RVMD 0001193125-26-071563
#   bash tools/extraire_fixture_ventilation.sh JPM 0001628280-26-008131
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
mkdir -p checks/fixtures/ventilation
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -v "$PWD/checks/fixtures/ventilation:/app/checks/fixtures/ventilation" \
  -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" python tools/extraire_fixture_ventilation.py "$@"
