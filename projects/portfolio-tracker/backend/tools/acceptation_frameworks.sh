#!/usr/bin/env bash
# Lanceur de l'acceptation du chantier v3 (`tools/acceptation_frameworks.py`, spec §9.2 T1-T8).
#
#   bash tools/acceptation_frameworks.sh
#
# ⚠️ Il se joue sur le CORPUS RÉEL — réseau `coolify` + la vraie DATABASE_URL. L'ordre des
# `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que la vraie
# doit écraser. Sans base, le script sort en **2**, jamais en saut de section
# (`feedback_check_degrade_en_sortant_a_zero`).
#
# ⚠️ Jamais dans le conteneur `portfolio-backend` : il porte le code déployé, qui peut précéder ce
# qu'on mesure. On monte le dépôt en lecture seule dans une instance neuve de son image.
#
# Sortie 1 = ROUGE ATTENDU au lot 0 : les 8 critères échouent avant la première ligne de code de la
# capacité. Sortie 0 = le lot 7 est tenu. Le bilan `N vérifications OK, M échec(s)` est imprimé dans
# tous les cas — son absence est un échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_frameworks.py
