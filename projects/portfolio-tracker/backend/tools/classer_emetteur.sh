#!/usr/bin/env bash
# Lanceur de `tools/classer_emetteur.py` — inscrit au dossier l'archétype d'un émetteur.
# Versionné pour la raison de `montrer_memo_projete.sh` : l'invocation EST une partie du geste.
# Une commande retapée à la main se retape un peu différemment à chaque fois, et ce geste-ci ÉCRIT.
#
#   bash tools/classer_emetteur.sh RVMD pre_revenus "Société de biotechnologie en phase clinique…"
#   bash tools/classer_emetteur.sh --lire RVMD
#
# ⚠️ IL ÉCRIT EN PROD (`ticker_archetypes`, migration 046) — pas de ROLLBACK, c'est le but : un
# classement qui disparaît avec le terminal est exactement le défaut que la 046 vient de fermer.
# L'outil imprime l'AVANT et l'APRÈS : c'est la lecture qui fait foi, pas le code de sortie.
#
# ⚠️ Réseau `coolify` + vrai `.env` : il lit et écrit `db_portfolio`. Ordre des `--env-file`
# load-bearing — `checks/env.checks` porte une DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à la
# migration qu'on exerce. On monte le dépôt en lecture seule dans une instance NEUVE.
#
# Codes : 0 = classé (ou lu) · 1 = refusé (archétype inconnu, motif vide) · 2 = pas exécutable.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/classer_emetteur.py "$@"
