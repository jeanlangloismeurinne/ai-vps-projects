#!/usr/bin/env bash
# Hook PRÉ-COMMIT — garde l'architecture de portfolio-tracker, en variante HÔTE (sans docker, instant).
#
# `check_architecture.py` n'importe que la stdlib et résout ses chemins depuis __file__ : il tourne
# donc tel quel avec `python3` nu, hors conteneur. Ce hook ne s'exécute QUE si des fichiers de
# portfolio-tracker sont indexés — il ne gêne jamais un commit portant sur un autre projet du repo.
#
# INSTALLATION (le contenu de .git/hooks n'est pas versionné) :
#   ln -sf ../../projects/portfolio-tracker/backend/checks/pre-commit.sh "$(git rev-parse --git-dir)/hooks/pre-commit"
# CONTOURNEMENT ponctuel : git commit --no-verify
#
# ⚠️ Il mesure l'ARBRE DE TRAVAIL (pas le contenu exactement indexé) — suffisant pour une garde
# structurelle ; si des modifs non indexées traînent sur les fichiers d'archi, les intégrer d'abord.
set -u
ROOT="$(git rev-parse --show-toplevel)"

# Rien de portfolio-tracker dans l'index → ne pas gêner.
if ! git diff --cached --name-only --diff-filter=ACMRD -- 'projects/portfolio-tracker/' | grep -q .; then
  exit 0
fi

CHECK="$ROOT/projects/portfolio-tracker/backend/checks/check_architecture.py"
out=$(python3 "$CHECK" 2>&1); rc=$?

if [ "$rc" -ne 0 ]; then
  {
    echo "✖ pré-commit : check_architecture a échoué — commit BLOQUÉ."
    printf '%s\n' "$out" | grep -E 'FAIL|échec'
    echo "  → corrige l'organisation (bijection docs↔checks, orphelin, dossier, autonomie /V3),"
    echo "    ou 'git commit --no-verify' pour outrepasser en connaissance de cause."
  } >&2
  exit 1
fi
echo "✓ pré-commit : $(printf '%s' "$out" | tail -1)"
exit 0
