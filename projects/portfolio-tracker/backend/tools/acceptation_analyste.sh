#!/usr/bin/env bash
# Lanceur de l'acceptation de l'ANALYSTE contre le VRAI modèle (`tools/acceptation_analyste.py`).
#
#   bash tools/acceptation_analyste.sh                   # contre le vrai modèle (2 appels)
#   bash tools/acceptation_analyste.sh --admissibilite   # DRY-RUN, aucun appel modèle
#
# ⚠️ Le `"$@"` de la dernière ligne n'est pas un confort : sans lui, le mode `--admissibilite` —
# la frontière GRATUITE, celle qui dit ce que le corpus rend possible avant de payer — n'était
# atteignable qu'en retapant la commande `docker run` à la main. Un mode qu'on ne peut pas lancer
# par son lanceur versionné n'est pas lancé (`feedback_frontiere_gratuite_avant_depense_modele`).
#
# ⚠️ Appelle DeepSeek (DeepInfra) et lit `agent_prompts` + `knowledge_entries` en DB — d'où réseau
# `coolify` + le vrai `.env`. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser (inversés, on lirait la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à celui
# qu'on éprouve.
# Ne persiste rien (lecture seule) ; consomme une petite quantité de tokens (2 appels).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_analyste.py "$@"
