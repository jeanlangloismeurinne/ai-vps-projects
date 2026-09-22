#!/usr/bin/env bash
# Lanceur de `tools/montrer_dossier.py` — montre le dossier tel qu'il part chez l'analyste.
# Versionné pour la raison de `acceptation_gate.sh` : l'invocation EST une partie de la mesure.
# Retapée à la main, elle se retape un peu différemment à chaque fois.
#
#   bash tools/montrer_dossier.sh RVMD qualite_financiere v3.0.0 [plafond]
#
# ⚠️ LECTURE SEULE — aucun appel de modèle, aucune écriture en base. C'est la frontière gratuite du
# lot : à rejouer après CHAQUE correctif de l'assemblage, pas une seule fois au début
# (`feedback_frontiere_gratuite_avant_depense_modele`).
#
# ⚠️ Réseau `coolify` + vrai `.env` : il lit `db_portfolio`. Ordre des `--env-file` load-bearing —
# `checks/env.checks` porte une DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à
# l'assemblage qu'on éprouve. On monte le dépôt en lecture seule dans une instance NEUVE.
#
# Le bilan `N vérification(s) OK, M échec(s)` est imprimé dans TOUS les cas — son absence est un
# échec, jamais un zéro (`feedback_bilan_par_sa_forme`).
#
# Codes : 0 = dossier assemblé · 1 = un invariant de lecture est rouge · 2 = pas mesurable.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/montrer_dossier.py "$@"
