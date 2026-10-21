#!/usr/bin/env bash
# Lanceur de `tools/montrer_ventilation.py` — la ventilation publiée relevée depuis les dépôts, en texte.
# Réseau PUBLIC (data.sec.gov), NI base NI modèle PAR DÉFAUT. Jamais dans `portfolio-backend` (code
# déployé) : instance neuve de son image, dépôt monté en lecture seule.
#
#   bash tools/montrer_ventilation.sh NVDA RVMD JPM
#   bash tools/montrer_ventilation.sh NVDA --publier     # ÉCRIT — réservé à Opus après vérification
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
EXTRA=()
if [[ " $* " == *" --publier "* ]]; then
  NET=coolify
  DB=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
  EXTRA=(-e "DATABASE_URL=$DB")
else
  NET=coolify   # data.sec.gov reste un accès public, mais passe par le même réseau sortant
fi
exec docker run --rm --network "$NET" -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks "${EXTRA[@]}" "$IMG" python tools/montrer_ventilation.py "$@"
