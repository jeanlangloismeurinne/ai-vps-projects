#!/usr/bin/env bash
# Lanceur de l'acceptation T8 du manager (`tools/acceptation_manager.py`).
#
#   bash tools/acceptation_manager.sh
#
# Le manager est PUR (aucun appel modèle) et le web n'est pas sollicité : coût $0. On lit et ÉCRIT
# `framework_mandates` en base (réseau `coolify` + vrai `.env`), dans une transaction ROLLBACK — le
# critère [T8.0] vérifie qu'il n'en reste rien.
#
# Ordre des `--env-file` load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que le vrai
# `.env` doit écraser (inversés, on écrirait dans la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à ce qu'on
# éprouve.
#
# Sortie 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env, ticker).
# Le bilan `BILAN acceptation manager — …` est imprimé dans tous les cas ; son absence est un échec.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_manager.py
