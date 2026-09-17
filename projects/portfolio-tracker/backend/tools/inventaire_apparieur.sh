#!/usr/bin/env bash
# Lanceur de l'inventaire apparieur (`tools/inventaire_apparieur.py`).
# Versionné pour la raison de `cartographier_xbrl.sh` : l'invocation EST une partie du test. Retapée
# à la main, elle se retape un peu différemment à chaque fois — et une mesure de contexte obtenue
# avec d'autres arguments n'est pas comparable à la précédente.
#
#   bash tools/inventaire_apparieur.sh                 # les 3 émetteurs pilotes du lot 3
#   bash tools/inventaire_apparieur.sh RVMD --plein    # la table ENTIÈRE, telle qu'elle part au modèle
#   bash tools/inventaire_apparieur.sh NVDA --extrait 60
#
# ⚠️ Réseau PUBLIC requis (data.sec.gov) mais NI base NI modèle : `--network coolify` pour la sortie
# internet, aucun `CHECK_DB_URL`, aucune clef de fournisseur. C'est la FRONTIÈRE GRATUITE de l'étape
# 2a — elle se lit en texte avant le premier jeton payé.
#
# ⚠️ Pas d'exécution dans le conteneur `portfolio-backend` : il porte le code DÉPLOYÉ, qui peut être
# antérieur au rendu qu'on mesure — on lirait le contexte d'avant le correctif. On monte le dépôt en
# lecture seule dans une instance neuve de son image.
#
# Sortie 0 = inventaire rendu et total. Sortie 1 = un PRÉ-REQUIS manquant (émetteur injoignable,
# rendu partiel, dépôt non datable) : jamais un saut de section, parce qu'un inventaire tronqué se
# lirait comme un émetteur qui dépose peu. Le bilan `BILAN inventaire apparieur — …` est imprimé dans
# tous les cas ; son absence est un échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks "$IMG" python tools/inventaire_apparieur.py "$@"
