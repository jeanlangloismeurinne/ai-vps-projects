#!/usr/bin/env bash
# Lanceur de la mesure de ligne de base (capacité 4). Versionné pour la même raison que
# `checks/run_all.sh` : il porte les invocations correctes (réseau `coolify` pour la base,
# sortie internet pour EDGAR, et le `.env` réel APRÈS `env.checks` pour écraser l'URL factice).
#
#   bash tools/mesure_gate.sh
#
# ⚠️ L'ordre des `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL
# bidon (`postgresql://u:p@h…`) qui doit être écrasée par la vraie. Inversés, la mesure sortirait
# en erreur — c'est voulu, le script refuse de mesurer contre une base inexistante.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/mesure_gate_capacite4.py
