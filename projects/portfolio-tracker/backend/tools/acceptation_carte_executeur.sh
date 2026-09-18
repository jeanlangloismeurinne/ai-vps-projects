#!/usr/bin/env bash
# Lanceur de l'acceptation du PRODUCTEUR de carte sur le chemin d'exécution
# (`tools/acceptation_carte_executeur.py`).
#
#   bash tools/acceptation_carte_executeur.sh
#
# ⚠️ Appelle DeepSeek (DeepInfra), lit `agent_prompts` en DB, interroge data.sec.gov et ÉCRIT dans
# `appariement_cartes` — d'où réseau `coolify` + le vrai `.env`. L'écriture se fait dans une
# transaction ROLLBACK et le critère [6] vérifie qu'il n'en reste rien.
#
# Ordre des `--env-file` load-bearing : `checks/env.checks` porte une DATABASE_URL bidon que le vrai
# `.env` doit écraser (inversés, on lirait — et on écrirait — dans la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à ce qu'on
# éprouve — on mesurerait le câblage d'avant.
#
# Coût : UN appel apparieur (~$0.0015). Le plan est RELU en base, jamais retraduit ; aucune collecte
# réelle n'est déclenchée (ni socle EDGAR, ni search-worker).
#
# Sortie 0 = tous les critères tenus · 1 = un critère rouge · 2 = pas mesurable (env, modèle, SEC,
# ou aucun plan persisté). Le bilan `BILAN acceptation carte-exécuteur — …` est imprimé dans tous les
# cas ; son absence est un échec, jamais un zéro.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/acceptation_carte_executeur.py
