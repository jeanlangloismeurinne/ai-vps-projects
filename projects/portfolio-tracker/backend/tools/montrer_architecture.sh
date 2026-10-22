#!/usr/bin/env bash
# Lanceur de `tools/montrer_architecture.py` — le service de l'architecture (§6.2), en texte.
# GRATUIT, lecture seule : aucun appel modèle, aucune écriture.
#
#   bash tools/montrer_architecture.sh NVDA
#
# ⚠️ Réseau `coolify` + vrai `.env` ; jamais dans `portfolio-backend` (code déployé, possiblement
# antérieur) : instance NEUVE de son image, dépôt monté en lecture seule.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/montrer_architecture.py "$@"
