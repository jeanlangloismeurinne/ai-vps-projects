#!/usr/bin/env bash
# Lanceur d'un PASSAGE DE BOUCLAGE comité → collecte (`tools/boucler_renvois.py`, lot 5).
#
#   bash tools/boucler_renvois.sh RVMD qualite_financiere pre_revenus
#
# ⚠️ Versionné pour la même raison qu'`executer_chaine.sh` : l'invocation EST une partie du test, et
# elle ÉCRIT en base (réponses re-persistées, mandats passés `servi`). Une variante retapée à la main
# laisserait des lignes qu'on ne saurait plus attribuer.
#
# ⚠️ IL PERSISTE EN PROD, ET C'EST LE BUT (pas de ROLLBACK) : c'est ce passage qui EXERCE
# `serve_mandate`/`read_open_mandates`, testés mais jamais appelés en production jusqu'ici (#71). La
# note imprimée dit par renvoi ce qui a été obtenu et ce qui ne l'a pas été.
#
# ⚠️ Réseau `coolify` + vrai `.env` : il appelle DeepSeek (DeepInfra), data.sec.gov, le web, et
# lit/écrit `db_portfolio`. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur. On monte le
# dépôt en lecture seule dans une instance NEUVE de son image.
#
# Codes : 0 = passage allé au bout · 1 = aucun renvoi ouvert · 2 = pas exécutable (env).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/boucler_renvois.py "$@"
