#!/usr/bin/env bash
# TEST NÉGATIF de `check_perimetre.py` — une mutation par règle du périmètre (lot P1), chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#   bash checks/negatif_perimetre.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_perimetre.py"
SRC="app/knowledge/perimetre.py"

mutations=(
# [P1] ordre_des_periodes : retour à la PREMIÈRE date trouvée (le DÉBUT d'un cumul) au lieu de la
# plus grande (la FIN) — un cumul se classerait avant l'exercice qu'il recouvre.
"$SRC¦    if dates:¦    if dates:\n        return (1, min(dates), periode)  # MUTATION\n    if False:¦[P1]"
# [P2]/detail_ajoute : la détection globale par paire de dépôts ne regarde plus les enfants
# nouveaux — un redécoupage qui ne touche QUE le détail (sans aucun autre mouvement) disparaît.
"$SRC¦                if enfants_nouveaux and cle not in vus:¦                if False:¦[P2]"
# [P3]/renommage : la tolérance de bouclage n'est plus appliquée au test d'égalité — un renommage
# dont les deux valeurs diffèrent d'un centime serait quand même accepté, MAIS ici on casse le
# sens inverse : aucun renommage n'est plus jamais reconnu (comparaison à zéro strict impossible).
"$SRC¦        candidats = [a for a in disparus if a in restants_a and abs(restants_a[a] - restants_n[n]) <= tol]¦        candidats = []¦[P3]"
# [P4]/[P5] regroupement/scission : la recherche de partition est désactivée (rend toujours
# « aucune partition ») — un redécoupage vérifiable devient une rupture non reconnue.
"$SRC¦    if not trouvees:¦    return None, False\n    if not trouvees:¦[P4]"
# [P6] meme_nom_contenu_change : la comparaison de valeur au recouvrement est retirée — un même
# identifiant à deux valeurs différentes serait traité comme une continuité silencieuse.
"$SRC¦    mnc = {m for m in memes_id if abs(pn_a[m] - pn_n[m]) > tol}¦    mnc = set()¦[P6]"
# [P7] rupture (aucun recouvrement) : le motif cesse de NOMMER l'absence de recouvrement — un
# lecteur ne saurait plus distinguer cette rupture-ci d'une rupture par passage non vérifié.
"$SRC¦            motif=\"aucune période n'est publiée dans les deux régimes : pas de recouvrement pour \"¦            motif=\"aucune période n'est publiée dans les deux régimes : incohérence \"¦[P7]"
# [P8] passage AMBIGU : la détection d'ambiguïté (plusieurs partitions bouclent) est retirée — la
# PREMIÈRE partition trouvée serait acceptée en silence.
"$SRC¦    if len(trouvees) > 1:¦    if False:¦[P8]"
# [P9] borne MAX_MEMBRES_PARTITION ignorée — une recherche de partition SANS FIN serait tentée
# (un blocage muet, #73) au lieu d'un refus nommé.
"$SRC¦MAX_MEMBRES_PARTITION = 8¦MAX_MEMBRES_PARTITION = 999999¦[P9]"
# [P11]/[P13] répartition par hypothèse : le montant du GROUPE n'est plus conservé — la valeur de
# chaque nouveau membre est inventée au prorata SANS passer par le montant ancien.
"$SRC¦            montant_groupe = sum(vals_periode[a] for a in groupe_ancien)¦            montant_groupe = 0.0¦[P11]"
# [P16]/[P17] invariant de l'agrégat : la tolérance de bouclage n'est plus appliquée — un écart
# minime entre Σ premier niveau et la ligne du socle serait accepté sans jamais être nommé... et
# RÉCIPROQUEMENT, retirer le contrôle entier fait disparaître l'ERREUR nommée attendue par [P17].
"$SRC¦        if abs(total - somme) > tol:¦        if False:¦[P17]"
# [P19]/[P20] douze mois — cohérence de régime : le contrôle de passage vérifié est retiré — deux
# régimes incohérents seraient acceptés même SANS aucune transition de passage.
"$SRC¦            if not passage_ok:¦            if False:¦[P19]"
# [P21] douze mois — retraitement ambigu : la détection de deux valeurs à la MÊME date de dépôt
# est retirée — un retraitement ambigu serait accepté en silence.
"$SRC¦                if len(autres_memes_filed) > 1 and len({p.get(\"val\") for p in autres_memes_filed}) > 1:¦                if False:¦[P21]"
# [P23] identifier_jumeau_candidat : le filtre « déposé AVANT l'ancien régime » est retiré — un
# dépôt POSTÉRIEUR pourrait être pris pour le jumeau, contre le sens même de « publié dans
# l'ancien découpage ».
"$SRC¦        if f.filed < ancien.filed and f.accn not in (recent.accn, ancien.accn)¦        if f.accn not in (recent.accn, ancien.accn)¦[P23]"
# [P24] regime_a_change : la comparaison axe par axe est remplacée par un « toujours faux » — un
# redécoupage réel ne déclencherait plus jamais la lecture du jumeau.
"$SRC¦    return any(premier_niveau_ancien.get(a) != premier_niveau_recent.get(a) for a in axes)¦    return False¦[P24]"
# [P25]/[P26] signal d'acquisition significative : le seuil n'est plus comparé — TOUTE acquisition
# deviendrait un signal, y compris sous le seuil.
"$SRC¦        if part >= seuil:¦        if True:¦[P25]"
# [P27] sans chiffre d'affaires acquis : le repli sur la capitalisation est retiré — une
# acquisition sans CA publié ne serait plus jamais signalée.
"$SRC¦        elif capitalisation:¦        elif False:¦[P27]"
# [P28]/[P29] RÉEL (NVDA) : la détection detail_ajoute ET regroupement reposent sur la même
# recherche de partition bornée — la neutraliser fait disparaître les DEUX transitions attendues
# sur le cas réel figé.
"$SRC¦    noms = sorted(candidats)¦    return None, False\n    noms = sorted(candidats)¦[P29bis]"
# [P30]/[P31] invariant de l'agrégat sur le cas RÉEL : retirer le passage de la chaîne (l'identité
# triviale) casse la reconstruction de Data Center ET l'invariant qui en dépend.
"$SRC¦    if not perturbe and membre_ref in vals_periode:¦    if False:¦[P30]"
# [P32] garde de détention : `premier_niveau_de` cesse d'exclure les enfants dont le parent est
# présent — un lecteur externe qui recopierait ce calcul passerait inaperçu du grep de détention.
"$SRC¦    return frozenset(m for m in presents if parent_de.get(m) not in presents)¦    return frozenset(presents)¦[P32bis]"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
