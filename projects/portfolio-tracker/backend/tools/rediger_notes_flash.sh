#!/usr/bin/env bash
# Lanceur de `tools/rediger_notes_flash.py` — la note flash des dépôts « à qualifier » d'un émetteur.
#
#   bash tools/rediger_notes_flash.sh RVMD                 # lecture gratuite (aucun appel modèle)
#   bash tools/rediger_notes_flash.sh RVMD --ecrire        # écrit en PROD (notes_flash, append-only)
#
# ⚠️ Versionné : l'invocation fait partie du test (réseau `coolify`, vrai `.env` APRÈS `env.checks`,
# dépôt monté en LECTURE SEULE dans une instance NEUVE de l'image — jamais dans `portfolio-backend`,
# qui porte le code déployé, possiblement antérieur).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/rediger_notes_flash.py "$@"
