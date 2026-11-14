#!/usr/bin/env bash
# Lanceur de `tools/emetteurs.py` (module M1) — versionné : l'invocation EST une partie de la mesure.
#
#   bash tools/emetteurs.sh importer app/db/seeds/emetteurs_reprise_2026-11-13.json --a-blanc
#   bash tools/emetteurs.sh importer app/db/seeds/emetteurs_reprise_2026-11-13.json
#   bash tools/emetteurs.sh montrer [EMETTEUR]
#   bash tools/emetteurs.sh comparer NVDA NVDA        (lecture seule)
#   bash tools/emetteurs.sh signaler RVMD RVMD        (lecture seule)
#
# ⚠️ `importer` sans `--a-blanc` ÉCRIT en base (fiches et journal des sources, en ajout seul).
# Aucun appel de modèle, aucune recherche web. Jamais dans `portfolio-backend` : instance neuve de
# l'image, dépôt monté en lecture seule. Ordre des `--env-file` load-bearing (le vrai `.env` écrase
# la DATABASE_URL factice de `checks/env.checks`).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/emetteurs.py "$@"
