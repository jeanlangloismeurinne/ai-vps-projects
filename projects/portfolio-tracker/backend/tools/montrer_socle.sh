#!/usr/bin/env bash
# Lanceur de `tools/montrer_socle.py` — le socle des comptes reconstitué, en texte.
# Réseau PUBLIC (data.sec.gov), NI base NI modèle. Jamais dans `portfolio-backend` (code déployé) :
# instance neuve de son image, dépôt monté en lecture seule.
#
#   bash tools/montrer_socle.sh RVMD NVDA MSFT
#   bash tools/montrer_socle.sh NVDA --provenance resultat_exploitation
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks "$IMG" python tools/montrer_socle.py "$@"
