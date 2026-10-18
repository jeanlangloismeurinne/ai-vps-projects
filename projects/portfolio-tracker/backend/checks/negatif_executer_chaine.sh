#!/usr/bin/env bash
# TEST NÉGATIF de `check_executer_chaine.py` — le filtre refus→mandat (addendum spec point 14,
# même lot — 2026-10-18). Une mutation par garde, chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ.
# Sans réseau, sans base : `_negatif.sh` par défaut (NET=none, pas de montage).
#   bash checks/negatif_executer_chaine.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_executer_chaine.py"
SRC="tools/executer_chaine.py"

mutations=(
# ── §1 un refus d'agent n'est plus retiré de questions_manquantes (régression du bug initial) ──
"$SRC¦        questions_manquantes=[q for q in review.questions_manquantes if q not in refus_qids],¦        questions_manquantes=list(review.questions_manquantes),  # mutation: refus plus retiré¦qf_1 (refusée) retirée de questions_manquantes"
# ── §1 un refus d'agent n'est plus retiré de mandats_manquantes (le mandat survit quand même) ──
"$SRC¦        mandats_manquantes=[m for m in review.mandats_manquantes if m.question_id not in refus_qids],¦        mandats_manquantes=list(review.mandats_manquantes),  # mutation: mandat du refus survit¦qf_1 (refusée) retirée de mandats_manquantes"
# ── §4 la liste des retirés ne nomme plus que l'intersection — elle nomme TOUS les refus ───────
"$SRC¦    retires = sorted(set(review.questions_manquantes) & refus_qids)¦    retires = sorted(refus_qids)  # mutation: nomme aussi un refus hors questions_manquantes¦qf_9 (refusée mais pas dans questions_manquantes) n'est pas listée"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
