#!/usr/bin/env bash
# Lanceur de la ligne de base « une absence est-elle comptée comme une fondation ? » (capacité 5).
# Versionné pour la même raison que `checks/run_all.sh` et `tools/mesure_conflits.sh` : il porte les
# invocations correctes, et la mesure devra être rejouée À L'IDENTIQUE après le lot — un mesureur
# réécrit entre les deux mesures ne mesure plus rien (`CHANTIER_OUTILLAGE_DEV.md` §27).
#
#   bash tools/mesure_absences.sh
#
# ⚠️ L'ordre des `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL bidon
# qui doit être écrasée par la vraie. Inversés, la mesure sortirait en erreur — c'est voulu, le
# script refuse de mesurer contre une base inexistante.
#
# ⚠️ Pas d'exécution dans `portfolio-backend` : ce conteneur porte le code DÉPLOYÉ, qui peut être
# antérieur à ce qu'on mesure. On monte la source locale en lecture seule dans son image.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/mesure_absences_capacite5.py
