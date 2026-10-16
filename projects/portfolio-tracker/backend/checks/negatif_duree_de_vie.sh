#!/usr/bin/env bash
# TEST NÉGATIF de `check_duree_de_vie.py` — une mutation par RÈGLE de la fraîcheur par durée de vie
# (2026-10-16, roadmap/V3/06-regle-fraicheur.md), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ +
# bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_duree_de_vie.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_duree_de_vie.py"
DV="app/knowledge/duree_de_vie.py"
FW="app/agents/v2/frameworks.py"
PA="app/agents/v2/parcours.py"
mutations=(
# la règle, durée par durée
"$DV¦        plus_recente = max(datees)¦        plus_recente = min(datees)¦rapport annuel + 10-Q du 30/06 sur le même historique"
"$DV¦    return clotures.derniere if d.cadence == \"trimestrielle\" else exercice¦    return clotures.derniere¦un chiffre courant ANNUEL au dernier exercice"
"$DV¦        return exercice¦        return None¦le proxy 2025 cède"
"$DV¦        if seuil_fait is not None and d_piece < seuil_fait:¦        if False:¦l'approbation du 26/08 rouvre le jugement"
"$DV¦        ings = list(ingredients_des_pieces.get(p) or ()) or [PAR_DEFAUT]¦        ings = list(ingredients_des_pieces.get(p) or ()) or [DureeIngredient(\"x\", \"jugement\")]¦une pièce non rattachée"
"$DV¦    exercice = clotures.exercice or clotures.derniere¦    exercice = clotures.exercice¦exercice inconnu"
"$DV¦    if clotures.derniere is None:¦    if False:¦aucune clôture connue"
"$DV¦    if horloge_indisponible:¦    if False:¦flux injoignable"
"$DV¦    faits = [e for e in horloge.recents if tuple(e.types) != (RESULTATS,)]¦    faits = list(horloge.recents)¦fait_qui_rouvre ignore la part"
# le point de lecture
"$FW¦        if j is not None:¦        if False:¦servir_answer, interrupteur actif"
"$PA¦    if not fichier.fraicheur_par_duree_de_vie:¦    if False:¦interrupteur coupé"
"$PA¦                                              durees=durees),¦                                              durees=None),¦parcours passe \`durees=durees\`"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
