#!/usr/bin/env bash
# Lanceur de l'acceptation de l'APPARIEUR contre le vrai modèle et le vrai dépôt
# (`tools/acceptation_apparieur.py`).
#
#   bash tools/acceptation_apparieur.sh
#
# ⚠️ Appelle DeepSeek (DeepInfra), lit `agent_prompts` en DB, et interroge data.sec.gov — d'où réseau
# `coolify` + le vrai `.env`. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser (inversés, on lirait la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à ce qu'on
# éprouve — on mesurerait le prompt d'avant.
#
# Ne persiste rien (la persistance de la carte est l'étape 2b). Coût : 3 plans + 3 à 6 appariements,
# soit ~$0.05 ; l'inventaire entier dans le contexte coûte $0.0015 par appel sur le plus gros
# émetteur — c'est la frontière gratuite `tools/inventaire_apparieur.sh` qui l'a chiffré avant.
#
# Sortie 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env, modèle ou SEC
# injoignable). Le bilan `BILAN acceptation apparieur — …` est imprimé dans tous les cas ; son
# absence est un échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_apparieur.py
