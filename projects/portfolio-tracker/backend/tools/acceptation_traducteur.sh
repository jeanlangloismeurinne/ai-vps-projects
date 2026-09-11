#!/usr/bin/env bash
# Lanceur de l'acceptation du traducteur contre le VRAI modèle (`tools/acceptation_traducteur.py`).
#
#   bash tools/acceptation_traducteur.sh
#
# ⚠️ Appelle DeepSeek (DeepInfra) et lit `agent_prompts` en DB — d'où réseau `coolify` + le vrai
# `.env`. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que
# le vrai `.env` doit écraser (inversés, on lirait la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur.
# Ne persiste rien (lecture seule) ; consomme une petite quantité de tokens (2 appels).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_traducteur.py
