#!/usr/bin/env bash
# Lanceur de `tools/montrer_memo_projete.py` — montre la note de comité telle qu'elle sort du
# classeur. Versionné pour la raison de `acceptation_gate.sh` : l'invocation EST une partie de la
# mesure. Retapée à la main, elle se retape un peu différemment à chaque fois.
#
#   bash tools/montrer_memo_projete.sh RVMD
#
# ⚠️ LECTURE SEULE — aucun appel de modèle, aucune écriture en base. C'est la frontière gratuite du
# lot 5 : à rejouer après CHAQUE correctif de la projection, pas une seule fois au début
# (`feedback_frontiere_gratuite_avant_depense_modele`).
#
# ⚠️ Réseau `coolify` + vrai `.env` : il lit `db_portfolio`, et `material_anchor_for_ticker` sort
# vers EDGAR pour l'ancre. Ordre des `--env-file` load-bearing — `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser.
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code DÉPLOYÉ, possiblement antérieur à la
# projection qu'on éprouve. On monte le dépôt en lecture seule dans une instance NEUVE.
#
# Le BILAN de fin (`N chapitre(s) : …`) est imprimé dans tous les cas où la note est dressée — son
# absence est un échec, jamais un zéro (`feedback_bilan_par_sa_forme`).
#
# Codes : 0 = note dressée · 1 = projection REFUSÉE (une réponse ne se range pas) · 2 = pas mesurable.
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env \
  "$IMG" python tools/montrer_memo_projete.py "$@"
