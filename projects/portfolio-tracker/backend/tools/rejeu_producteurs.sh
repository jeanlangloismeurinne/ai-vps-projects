#!/usr/bin/env bash
# Lanceur du rejeu des producteurs déterministes (`tools/rejeu_producteurs.py`).
#
#   bash tools/rejeu_producteurs.sh
#
# ⚠️ CE SCRIPT ÉCRIT DANS LE CORPUS RÉEL. Il n'a pas de dry-run : les producteurs sont
# append-only et idempotents par supersession, donc un second passage ne duplique pas — il
# ajoute une génération. C'est voulu.
#
# ⚠️ L'ordre des `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL bidon
# que la vraie doit écraser. Inversés, le rejeu écrirait ailleurs (ou nulle part).
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder
# celui qu'on rejoue.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/rejeu_producteurs.py
