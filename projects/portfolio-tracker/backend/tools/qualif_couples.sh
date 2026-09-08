#!/usr/bin/env bash
# Lanceur de la qualification des couples (ligne de base 5b). Versionné pour la même raison que
# `tools/mesure_conflits.sh` et `checks/run_all.sh` : il porte les invocations correctes, et la
# mesure devra être rejouable À L'IDENTIQUE (`CHANTIER_OUTILLAGE_DEV.md` §27).
#
#   bash tools/qualif_couples.sh
#
# ⚠️ Cette mesure APPELLE UN MODÈLE (contrairement à `mesure_conflits.sh`, gratuite). Elle ne se
# lance qu'après elle : la frontière gratuite écarte déjà 63 des 92 paires.
#
# ⚠️ L'ordre des `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL bidon
# qui doit être écrasée par la vraie. Inversés, la mesure sort en erreur — c'est voulu.
#
# ⚠️ Pas d'exécution dans `portfolio-backend` : ce conteneur porte le code DÉPLOYÉ, qui peut être
# antérieur à ce qu'on mesure. On monte la source locale en lecture seule dans son image.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/qualif_couples_capacite5.py
