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
#
# ⚠️ Sortie 2 = « je n'ai PAS PU mesurer », qui n'est ni un succès ni un échec (trois états, #44).
# Deux causes, toutes deux nommées sur stderr : `DATABASE_URL` absente, ou — depuis le lot 2b —
# l'index de couverture sans émetteur tant que le dispatch du lot 2c n'écrit pas
# `question_coverage`. Ne PAS lire ce 2 comme une régression de la capacité 4, et ne pas le
# « réparer » en fournissant un index vide : la suspension se lève d'elle-même au lot 2c.
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_capacite4.py
