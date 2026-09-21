#!/usr/bin/env bash
# TEST NÉGATIF de `checks/check_reconciliation.py` — une mutation par clause de `ecart()`.
#
#   bash checks/negatif_reconciliation.sh
#
# POURQUOI CE FICHIER. `check_reconciliation` est VERT le jour de sa naissance, ce qui est le pire
# moment pour le croire : un check neuf n'est éprouvé qu'après avoir viré au rouge une fois
# (`feedback_test_negatif_obligatoire`). Il garde en plus une règle dont les deux copies venaient
# de diverger en silence pendant tout le lot 3 — c'est précisément le genre de garde dont on veut
# savoir qu'elle mord.
#
# Les mutations portent sur `tools/reconcilier_vocabulaires.py`, DÉTENTEUR unique de la règle. Une
# mutation qui laisserait le check vert dirait que la règle n'est gardée par rien.
#
# ⚠️ La boucle de mutation n'est PAS recopiée ici : elle est dans `checks/_negatif.sh` (#46). Seize
# des dix-neuf `negatif_*.sh` en portent encore une copie, et c'est exactement ce qui a laissé la
# mutation FROZEN de `negatif_frameworks_definitions.sh` résoudre son chemin autrement que le
# harnais — caduque, donc muette, depuis sa création.
set -u
cd "$(dirname "$0")/.." || exit 1

CHECK="checks/check_reconciliation.py"
REC="tools/reconcilier_vocabulaires.py"

# ── fichier ¦ motif remplacé ¦ remplaçant ¦ assert qui DOIT rougir ──────────────────────────────
mutations=(
# La dispense des DÉRIVÉS disparaît : 6 champs CALCULÉS se mettent à compter comme orphelins. Un
# T6 gonflé de faux défauts envoie corriger des champs qui n'ont rien à être fondés.
"$REC¦    sans_question = sorted(f for f in memo - DERIVES if f not in vocabulaire)¦    sans_question = sorted(f for f in memo if f not in vocabulaire)¦les champs DÉRIVÉS ne comptent pas comme orphelins"
# T7 cesse de soustraire le mémo : TOUTE question est déclarée inutilisée, même celle que le mémo
# consomme. La clause déborde, et un rouge ne dit plus laquelle des deux discrimine.
"$REC¦    jamais_consommees = sorted(vocabulaire - memo)¦    jamais_consommees = sorted(vocabulaire)¦sans toucher T6"
# T6 cesse de regarder le vocabulaire : plus aucun champ n'est jamais orphelin. C'est le faux vert
# que ce chantier a déjà produit une fois, en jugeant contre une grille retirée.
"$REC¦    sans_question = sorted(f for f in memo - DERIVES if f not in vocabulaire)¦    sans_question = []¦rend CE champ orphelin, et lui seul"
# Le référentiel rend un vocabulaire VIDE sans lever. §B ne peut pas l'attraper (T7 est vrai sur
# zéro question) : c'est la garde de non-vacuité de §1 qui doit rougir, et elle seule le peut.
"$REC¦    return {q.chemin_indexation: f.id for f in fichier.frameworks for q in f.questions}¦    return {}¦le vocabulaire des QUESTIONS est non vide"
# Un champ déclaré DÉRIVÉ qui n'est plus une feuille du mémo : une dispense qui ne dispense plus
# rien, et qui masquerait le jour où un champ homonyme réapparaît.
"$REC¦    \"moat.score\",¦    \"moat.score_supprime_du_contrat\",¦les DÉRIVÉS sont un sous-ensemble strict"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
