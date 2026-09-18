#!/usr/bin/env bash
# Lanceur de l'acceptation de l'EXÉCUTION d'un appariement (`tools/acceptation_appariement.py`).
#
#   bash tools/acceptation_appariement.sh
#
# ⚠️ Interroge data.sec.gov, lit le plan et la carte en base et ÉCRIT des `knowledge_entries` —
# d'où réseau `coolify` + le vrai `.env`. L'écriture se fait dans une transaction ROLLBACK et le
# critère [7] vérifie qu'il n'en reste rien.
#
# Ordre des `--env-file` load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que le vrai
# `.env` doit écraser (inversés, on lirait — et on écrirait — dans la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à ce qu'on
# éprouve — on mesurerait la collecte d'avant.
#
# Coût : au plus UN appel apparieur (~$0.0015) si la carte manque ou a vieilli, zéro sinon. Le web
# payant est DÉBRANCHÉ pendant la mesure (cf. l'en-tête du .py) : une retombée web est un échec.
#
# Sortie 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env, SEC, plan).
# Le bilan `BILAN acceptation appariement — …` est imprimé dans tous les cas ; son absence est un
# échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_appariement.py
