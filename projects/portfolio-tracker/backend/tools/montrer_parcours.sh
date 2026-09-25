#!/usr/bin/env bash
# Lanceur de `tools/montrer_parcours.py` — montre les trois niveaux du parcours du comité tels
# que les écrans les reçoivent. Versionné : l'invocation EST une partie de la mesure.
#
#   bash tools/montrer_parcours.sh RVMD [--json 1|2 <framework>|3 <framework> <question>]
#
# ⚠️ LECTURE SEULE — aucun appel de modèle, aucune écriture. Frontière gratuite du lot 6, à rejouer
# après CHAQUE correctif (`feedback_frontiere_gratuite_avant_depense_modele`).
#
# ⚠️ Réseau `coolify` + vrai `.env` : il lit `db_portfolio`, et `material_anchor_for_ticker` sort
# vers EDGAR pour l'ancre. Ordre des `--env-file` load-bearing — `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à la
# dérivation qu'on éprouve. On monte le dépôt en lecture seule dans une instance NEUVE.
#
# Codes : 0 = mesure dressée · 2 = pas mesurable.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/montrer_parcours.py "$@"
