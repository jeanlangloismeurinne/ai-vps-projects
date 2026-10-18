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
"$DV¦        plus_recente, p_recente = max(datees)¦        plus_recente, p_recente = min(datees)¦rapport annuel + 10-Q du 30/06 sur le même historique"
"$DV¦    return clotures.derniere if d.cadence == \"trimestrielle\" else annuel¦    return clotures.derniere¦un chiffre courant ANNUEL au dernier exercice"
"$DV¦        return annuel¦        return None¦le proxy 2025 cède"
"$DV¦        if seuil_fait is not None and d_piece < seuil_fait:¦        if False:¦témoin ordre 0 : la pièce du 18/05"
"$DV¦        seule = [i for i in (rattache or [PAR_DEFAUT]) if i not in en_sujet]¦        seule = [i for i in (rattache or [DureeIngredient(\"x\", \"jugement\")]) if i not in en_sujet]¦une pièce non rattachée"
"$DV¦    exercice = clotures.exercice or clotures.derniere¦    exercice = clotures.exercice¦exercice inconnu"
"$DV¦    if clotures.derniere is None:¦    if False:¦aucune clôture connue"
"$DV¦    if horloge_indisponible:¦    if False:¦flux injoignable"
"$DV¦    faits = [e for e in horloge.recents if tuple(e.types) != (RESULTATS,)]¦    faits = list(horloge.recents)¦fait_qui_rouvre ignore la part"
# le point de lecture
"$FW¦        if j is not None:¦        if False:¦servir_answer, interrupteur actif"
"$PA¦    if not fichier.fraicheur_par_duree_de_vie:¦    if False:¦interrupteur coupé"
"$PA¦                                              durees=durees),¦                                              durees=None),¦parcours passe \`durees=durees\`"
"$DV¦    annuel = exercice - TOLERANCE_ANNUELLE if exercice is not None else None¦    annuel = exercice¦tolérance annuelle : les pairs clos"
"$DV¦TOLERANCE_ANNUELLE = timedelta(days=92)¦TOLERANCE_ANNUELLE = timedelta(days=400)¦l'exercice d'AVANT"
"$PA¦            ings = propres.get((qid, e)) or du_chapitre.get((fid, e))¦            ings = propres.get((qid, e))¦collectée pour ma_1 (même chapitre)"
"$PA¦            ings = propres.get((qid, e)) or du_chapitre.get((fid, e))¦            ings = propres.get((qid, e)) or next((v for (_f, _e), v in du_chapitre.items() if _e == e), None)¦jamais celle d'un AUTRE chapitre"
# sujet par sujet (point 15)
"$DV¦        en_sujet = [i for i in rattache if par_sujet or i.duree_de_vie == \"historique\"]¦        en_sujet = [i for i in rattache if i.duree_de_vie == \"historique\"]¦rachats du 18/05 + du 28/09"
"$DV¦        en_sujet = [i for i in rattache if par_sujet or i.duree_de_vie == \"historique\"]¦        en_sujet = [i for i in (rattache or [PAR_DEFAUT]) if par_sujet or i.duree_de_vie == \"historique\"]¦deux pièces NON RATTACHÉES"
"$DV¦        if not datees or (ing.duree_de_vie != \"historique\" and len(datees) < len(pieces)):¦        if not datees:¦une pièce sans date dans un sujet"
"$DV¦        and all(i.duree_de_vie != \"historique\" and i in recente and dates[p] < recente[i]¦        and all(i in recente and dates[p] < recente[i]¦un historique complété n'a pas de pièce"
"$DV¦            perimes.append(f\"{quoi} précède le fait qui rouvre la question ({fait.resume()})\")¦            pass¦anti-blanchiment ENTRE sujets"
"$PA¦        ingredients_des_pieces=par_question, par_sujet=fichier.fraicheur_par_sujet)¦        ingredients_des_pieces=par_question, par_sujet=True)¦contexte_durees porte l'interrupteur"
"$FW¦            else None, par_sujet=durees.par_sujet)¦            else None, par_sujet=True)¦servir_answer suit l'interrupteur"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
