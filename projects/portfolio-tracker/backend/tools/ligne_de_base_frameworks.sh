#!/usr/bin/env bash
# Lanceur de la ligne de base du chantier v3 (`tools/ligne_de_base_frameworks.py`, spec §9.1).
#
#   bash tools/ligne_de_base_frameworks.sh
#
# ⚠️ Trois montages/variables sont load-bearing, et leur absence sort en ERREUR, jamais en saut de
# section :
#   · réseau `coolify` + la vraie DATABASE_URL — la ligne de base se REQUÊTE, elle ne se souvient
#     pas (`feedback_ligne_de_base_est_une_mesure`) ;
#   · `../roadmap` monté en `/roadmap` — la matrice de traçabilité du benchmark (Partie E) est
#     PARSÉE, jamais recopiée dans le mesureur ;
#   · l'ordre des `--env-file` : `checks/env.checks` porte une DATABASE_URL bidon que la vraie doit
#     écraser. Inversés, le script sortirait en erreur — c'est voulu.
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code déployé, qui peut précéder ce
# qu'on mesure.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap:/roadmap:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/ligne_de_base_frameworks.py
