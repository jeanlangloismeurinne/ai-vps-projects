#!/usr/bin/env bash
# Lanceur de la cartographie XBRL (`tools/cartographier_xbrl.py`).
# Versionné pour la raison de `reconcilier_vocabulaires.sh` : l'invocation EST une partie du test.
# Retapée à la main, elle se retape un peu différemment à chaque fois — et une carte obtenue avec
# d'autres arguments n'est pas comparable à la précédente.
#
#   bash tools/cartographier_xbrl.sh                       # les 3 émetteurs pilotes du lot 3
#   bash tools/cartographier_xbrl.sh NVDA --hors-catalogue 40
#
# ⚠️ Réseau PUBLIC requis (data.sec.gov) mais NI base NI modèle : `--network coolify` pour la sortie
# internet, aucun `CHECK_DB_URL`, aucune clef de fournisseur. Coût : quelques appels HTTP publics.
#
# ⚠️ Pas d'exécution dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut être
# antérieur au catalogue qu'on cartographie — on mesurerait les postes d'avant l'enrichissement.
# On monte le dépôt en lecture seule dans une instance neuve de son image.
#
# Sortie 0 = carte complète. Sortie 1 = un PRÉ-REQUIS manquant (catalogue vide, poste sans candidat,
# émetteur injoignable) : jamais un saut de section, parce qu'une carte tronquée se lirait comme une
# absence de données chez l'émetteur. Le bilan `BILAN cartographie — …` est imprimé dans tous les
# cas ; son absence est un échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks "$IMG" python tools/cartographier_xbrl.py "$@"
