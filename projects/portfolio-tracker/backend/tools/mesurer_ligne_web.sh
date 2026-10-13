#!/usr/bin/env bash
# Lanceur de `tools/mesurer_ligne_web.py` (jalon A1 bis) — voir sa docstring.
#
#   bash tools/mesurer_ligne_web.sh 242 1021 1025 [--plafond=600]
#
# N'écrit RIEN en base ; dépense des appels modèle et web (quelques centimes par ligne).
# Réseau `coolify` + vrai `.env` (ordre des `--env-file` load-bearing, cf. executer_chaine.sh) ;
# jamais dans `portfolio-backend` : instance neuve de l'image, dépôt en lecture seule.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/mesurer_ligne_web.py "$@"
