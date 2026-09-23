#!/usr/bin/env bash
# Lance UN check qui a besoin de l'état persisté (section « base »).
#
#   bash checks/avec_base.sh check_datation
#   bash checks/avec_base.sh check_entry_nature
#
# POURQUOI CE FICHIER EST VERSIONNÉ. L'invocation était retapée à la main à chaque session, et
# une invocation retapée re-diverge : ordre des `--env-file` inversé (la `DATABASE_URL` bidon de
# `checks/env.checks` écrase alors la vraie, et le check mesure une autre base), montage
# `/roadmap` oublié (une section sort en échec au lieu de mesurer), réseau `none` au lieu de
# `coolify`. Le lanceur de la suite vit déjà ici pour la même raison — celui-ci le rejoint.
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut précéder
# celui qu'on éprouve.
set -u
cd "$(dirname "$0")/.." || exit 1

CHECK="${1:?usage: bash checks/avec_base.sh <nom_du_check>}"
CHECK="checks/$(basename "$CHECK" .py).py"
[ -f "$CHECK" ] || { echo "check introuvable : $CHECK" >&2; exit 2; }

IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
DB=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
[ -n "$DB" ] || { echo "DATABASE_URL absente de .env — le check mesurerait une base vide" >&2; exit 2; }

exec docker run --rm --network coolify \
  -v "$PWD:/app:ro" \
  -v "$PWD/../roadmap:/roadmap:ro" \
  -v "$PWD/../roadmap/V3/provenance-cards:/contract_frozen:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks -e "CHECK_DB_URL=$DB" \
  "$IMG" python "$CHECK"
