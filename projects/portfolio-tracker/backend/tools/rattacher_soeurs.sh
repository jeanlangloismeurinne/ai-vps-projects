#!/usr/bin/env bash
# Lanceur de `tools/rattacher_soeurs.py` — rattache les pièces sœurs orphelines d'avant #106.
# À blanc par défaut ; `--ecrire` écrit les liens de couverture (prod, une transaction, idempotent).
#
#   bash tools/rattacher_soeurs.sh [--ecrire]
#
# ⚠️ Réseau `coolify` + vrai `.env` ; ordre des `--env-file` load-bearing (`checks/env.checks` porte
# une DATABASE_URL bidon que le vrai `.env` écrase). Jamais dans `portfolio-backend` : on monte le
# dépôt en lecture seule dans une instance neuve.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app -e PYTHONDONTWRITEBYTECODE=1 \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/rattacher_soeurs.py "$@"
