#!/usr/bin/env bash
# TEST NÉGATIF de `check_socle_comptes.py` — une mutation par règle du socle des comptes, chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#   bash checks/negatif_socle_comptes.sh
#
# ⚠️ Les règles de PÉRIODE (douze mois, exercice, instant) sont DÉLÉGUÉES à `appariement_feed` /
# `edgar_facts` : elles s'éprouvent chez leur détenteur (`negatif_appariement_feed.sh`). Ici on mute
# ce que le socle décide LUI-MÊME : le gabarit, le choix de recette, la résolution, les contrôles.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_socle_comptes.py"
SRC="app/knowledge/socle_comptes.py"
GAB="app/knowledge/socle_comptes.yaml"

mutations=(
# Gabarit : une ligne inconnue n'est plus refusée — l'équation lirait une ligne toujours vide.
"$SRC¦        raise GabaritInvalide(f\"{ou} : la ligne « {nom} » n'existe pas dans le gabarit\")¦        return Terme(nom, +1 if s[0] == \"+\" else -1)¦ligne inconnue dans une équation"
# Gabarit : un reste partagé — la même ligne « autres » servirait deux équations.
"$SRC¦                if reste.ligne in restes_vus:¦                if False:¦reste partagé par deux équations"
# Gabarit : flux et instant mêlés acceptés.
"$SRC¦            if len(cadrages) != 1:¦            if False:¦flux et instant mêlés"
# Gabarit : une ligne toujours vide acceptée.
"$SRC¦    if orphelines:¦    if False:¦ligne toujours vide"
# Recette : la première recette déposée À UNE AUTRE PÉRIODE gagne — NVDA perd ses placements 2026.
"$SRC¦    for recette in ligne.recettes:¦    for recette in ligne.recettes[:1]:¦placements sous un AUTRE concept"
# Résolution : un contrôle qui ÉCHOUE est absorbé (tolérance infinie) — l'écart MSFT disparaît.
"$SRC¦    return max(TOLERANCE_ABSOLUE, TOLERANCE_RELATIVE * max((abs(m) for m in montants), default=0.0))¦    return float(\"inf\")¦l'écart est publié"
# Résolution : une ligne « absent vaut zéro » est déduite par différence au lieu de rester comptée
# zéro — l'écart de change de MSFT devient un faux « effet de change » calculé.
"$SRC¦            elif ligne.absent_vaut_zero:¦            elif False:¦comptée zéro"
# Zéro fabriqué : une ligne absente publie 0.0 au lieu de None.
"$SRC¦                locales[ligne.id] = Cellule(ligne.id, periode.id, \"compte_zero\")¦                locales[ligne.id] = Cellule(ligne.id, periode.id, \"compte_zero\", 0.0)¦AUCUNE valeur publiée"
# Le reste ne nomme plus ce qu'il absorbe.
"$SRC¦                absorbe = [t.ligne for t in eq.composantes¦                absorbe = [] and [t.ligne for t in eq.composantes¦ABSORBE la ligne manquante"
# Douze mois : repli sur l'exercice clos quand un terme manque (le chiffre qu'on retire).
"$SRC¦            val, composantes = douze_mois_glissants(pts, fin, concept)¦            try:\n                val, composantes = douze_mois_glissants(pts, fin, concept)\n            except AppariementInexecutable:\n                return float(serie[-1][\"val\"]), [_lecture(concept, serie[-1])]¦l'exercice clos ne remplace pas"
# Périodes : plus de colonne douze mois.
"$SRC¦    if derniere and derniere > fins[-1]:¦    if False:¦flux d'exploitation sur douze mois"
# Données : le gabarit perd la recette des convertibles.
"$GAB¦          - [ConvertibleLongTermNotesPayable]¦¦convertibles au dernier bilan"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
