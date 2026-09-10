#!/usr/bin/env bash
# Lanceur de l'inventaire de la grappe V2 (`tools/inventaire_grappe_v2.py`, lot 2b / spec §5.2-§5.3).
#
#   bash tools/inventaire_grappe_v2.sh
#
# ⚠️ Deux choses sont load-bearing, et leur absence sort en ERREUR, jamais en saut de section
# (`feedback_check_degrade_en_sortant_a_zero`) :
#   · réseau `coolify` + la vraie DATABASE_URL — l'inventaire se REQUÊTE, il ne se souvient pas
#     (`feedback_ligne_de_base_est_une_mesure`) ;
#   · l'ordre des `--env-file` : `checks/env.checks` porte une DATABASE_URL bidon que la vraie doit
#     écraser. Inversés, le script sortirait en erreur — c'est voulu.
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code déployé, qui peut précéder ce
# qu'on mesure.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/inventaire_grappe_v2.py
