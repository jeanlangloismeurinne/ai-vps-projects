#!/usr/bin/env bash
# Lanceur de `tools/recouper_nombres.py` — recoupe chaque nombre d'une réponse avec ses pièces citées.
#
#   bash tools/recouper_nombres.sh RVMD management_capital [--ids 1451,1452]
#
# Lecture seule, sans modèle. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser. Jamais dans `portfolio-backend`.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/recouper_nombres.py "$@"
