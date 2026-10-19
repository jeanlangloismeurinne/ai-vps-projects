#!/usr/bin/env bash
# Lanceur de `tools/retitrer_pieces.py` — rattrapage des titres des pièces EN VIGUEUR touchées par
# le défaut mesuré le 2026-10-18 (titre composé de ce qu'on a DEMANDÉ, pas de ce que la pièce
# CONTIENT). Versionné : l'invocation EST une partie de la mesure.
#
#   bash tools/retitrer_pieces.sh                  # à blanc, toutes les pièces en vigueur
#   bash tools/retitrer_pieces.sh --ticker NVDA     # restreint à un émetteur
#   bash tools/retitrer_pieces.sh --exemples 20     # plus d'exemples affichés (défaut 10)
#
# ⚠️ MODE PAR DÉFAUT = À BLANC. `--appliquer` ÉCRIT dans une transaction — interdit tant que la
# mesure à blanc n'a pas été relue et validée (cf. la spec qui a commandé cet outil).
#
# ⚠️ Réseau `coolify` + vrai `.env` : il lit `db_portfolio` en LECTURE (et en ÉCRITURE seulement
# sous `--appliquer`). Ordre des `--env-file` load-bearing — `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à la
# dérivation qu'on éprouve. On monte le dépôt en lecture seule dans une instance NEUVE de son image
# (même patron que `tools/montrer_parcours.sh`) — seul le MONTAGE du code est en lecture seule, la
# connexion à la base reste celle du vrai `.env`.
#
# Codes : 0 = mesure dressée (à blanc) ou écriture faite (`--appliquer`) · 2 = pas mesurable.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/retitrer_pieces.py "$@"
