#!/usr/bin/env bash
# Lanceur de la réconciliation des deux vocabulaires (`tools/reconcilier_vocabulaires.py`).
# Versionné pour la raison de `acceptation_gate.sh` et de `checks/run_all.sh` : l'invocation EST une
# partie du test. Retapée à la main, elle se retape un peu différemment à chaque fois.
#
#   bash tools/reconcilier_vocabulaires.sh
#
# ⚠️ `--network none` : la réconciliation ne lit NI la base NI le réseau. Elle compare deux contrats
# entre eux, et c'est exactement ce qui la rend valable avant toute dépense — la frontière gratuite
# (`feedback_frontiere_gratuite_avant_depense_modele`).
#
# ⚠️ Pas d'exécution dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut être
# antérieur au vocabulaire qu'on réconcilie. On monte le dépôt en lecture seule dans une instance
# neuve de son image.
#
# Sortie 1 = ROUGE ATTENDU (30 feuilles orphelines + 13 questions inutilisées, spec v3 §6).
# Sortie 0 = chaque bloc du mémo est la projection d'un framework acquitté — l'état terminal de la
# roadmap. Le bilan `N vérifications OK, M échec(s)` est imprimé dans tous les cas — son absence
# est un échec, jamais un zéro.
#
# ⚠️ Ce script a rendu `14 / 3` jusqu'au 2026-09-21 : il jugeait contre `FIELD_PROFILES`, la grille
# MVDD à qui le lot 3 avait retiré son autorité. Le couple n'est pas passé de 14/3 à 30/13 par
# régression — c'est l'étalon qui a été corrigé.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks "$IMG" python tools/reconcilier_vocabulaires.py
