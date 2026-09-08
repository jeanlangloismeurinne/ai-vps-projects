#!/usr/bin/env bash
# Lanceur du test d'ACCEPTATION de la capacité 4 (`tools/acceptation_capacite4.py`).
# Versionné pour la raison de `mesure_gate.sh` et de `checks/run_all.sh` : l'invocation EST une
# partie du test. Passée à la main, elle se retape un peu différemment à chaque fois — et la
# différence qui compte ici (le vrai `.env` après `env.checks`) est silencieuse.
#
#   bash tools/acceptation_gate.sh
#
# ⚠️ Le conteneur `portfolio-backend` en cours d'exécution ne convient PAS pour ce test : il porte
# le code DÉPLOYÉ, qui peut être antérieur à la capacité qu'on vérifie (mesuré le 2026-09-08 :
# `champs_perimes` absent de son curator). On monte donc le dépôt en lecture seule dans une
# instance neuve de l'image, pour éprouver le code du dépôt et non celui d'hier.
#
# ⚠️ L'ordre des `--env-file` est load-bearing : `checks/env.checks` porte une DATABASE_URL bidon
# qui doit être écrasée par la vraie. Inversés, l'acceptation sortirait en erreur — c'est voulu,
# elle refuse de se mesurer contre une base inexistante.
#
# Sortie 0 = les deux porteurs (NVDA, MSFT) basculent `ready, 0 gap` → `not_ready (péremption)`
# sans qu'aucun champ périmé ne parte en collecte. Sortie 1 = un assert NOMMÉ a rougi ; le bilan
# `N vérifications OK, M échec(s)` est imprimé dans tous les cas.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_capacite4.py
