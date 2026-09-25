#!/usr/bin/env bash
# Acceptation de bout en bout du BOUCLAGE (`tools/acceptation_bouclage.py`, lot 5) — le wiring DB
# neuf (read_open_mandates → id_du_mandat_ouvert → serve_mandate → note) rejoué contre la VRAIE base
# en transaction ROLLBACK, zéro résidu. Rapporte aussi l'état réel (mandats ouverts en base).
#
#   bash tools/acceptation_bouclage.sh
#
# ⚠️ Réseau `coolify` + vrai `.env` (base uniquement ; ni modèle ni web). Ordre des `--env-file`
# load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que le vrai `.env` doit écraser.
# ⚠️ Jamais dans `portfolio-backend` : on monte le dépôt en lecture seule dans une instance NEUVE.
#
# Codes : 0 = tous critères OK · 1 = un critère KO · 2 = pas mesurable (env/base).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_bouclage.py
