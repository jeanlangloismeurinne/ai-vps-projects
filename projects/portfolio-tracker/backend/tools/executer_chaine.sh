#!/usr/bin/env bash
# Lanceur du PREMIER PASSAGE RÉEL de la chaîne frameworks (`tools/executer_chaine.py`).
#
#   bash tools/executer_chaine.sh RVMD qualite_financiere pre_revenus
#   bash tools/executer_chaine.sh RVMD qualite_financiere pre_revenus --sans-collecte
#
# ⚠️ Versionné pour la raison de `reconcilier_vocabulaires.sh` : l'invocation EST une partie du
# test. Retapée à la main, elle se retape un peu différemment à chaque fois — et celle-ci ÉCRIT
# en base, donc une variante silencieuse laisserait des lignes qu'on ne saurait plus attribuer.
# Le `"$@"` n'est pas un confort : sans lui, `--sans-collecte` — le passage le moins cher, celui
# qui n'appelle ni traducteur ni web — ne serait atteignable qu'en retapant le `docker run`
# (`feedback_frontiere_gratuite_avant_depense_modele`, et l'omission déjà corrigée dans
# `acceptation_analyste.sh`).
#
# ⚠️ IL PERSISTE EN PROD, ET C'EST LE BUT : `knowledge_entries`, `collection_plans`,
# `question_coverage`, `appariement_cartes`, `framework_answers`, `framework_mandates`. Pas de
# ROLLBACK ici — un mécanisme prouvé en transaction n'a pas tourné. L'outil imprime en fin de
# course l'INVENTAIRE NOMMÉ de ses écrits : si la sortie est fausse, on retire par ces ids et on
# corrige EN AMONT avant de réessayer (`feedback_fixture_pollue_le_reel`).
#
# ⚠️ Réseau `coolify` + vrai `.env` : il appelle DeepSeek (DeepInfra), data.sec.gov, le web, et
# lit/écrit `db_portfolio`. Ordre des `--env-file` load-bearing : `checks/env.checks` porte une
# DATABASE_URL bidon que le vrai `.env` doit écraser (inversés, on écrirait dans la mauvaise base).
#
# ⚠️ Jamais dans `portfolio-backend` : il porte le code déployé, possiblement antérieur à la chaîne
# qu'on éprouve. On monte le dépôt en lecture seule dans une instance NEUVE de son image.
#
# ⚠️ LE VERDICT EST À LA LECTURE, pas au code de sortie. Un `repondu` bien formé sur un fait
# inventé passe les quatre contrôles du manager : ils gardent la STRUCTURE, jamais le sens
# (`feedback_garde_structure_pas_sens`).
#
# Codes : 0 = la chaîne est allée au bout · 1 = un maillon a refusé · 2 = pas exécutable (env).
cd "$(dirname "$0")/.." || exit 2
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
exec docker run --rm --network coolify -v "$PWD:/app:ro" \
  -w /app -e PYTHONPATH=/app \
  --env-file checks/env.checks --env-file .env "$IMG" python tools/executer_chaine.py "$@"
