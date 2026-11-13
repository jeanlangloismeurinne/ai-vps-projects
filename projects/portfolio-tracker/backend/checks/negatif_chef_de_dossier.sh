#!/usr/bin/env bash
# TEST NÉGATIF de `check_chef_de_dossier.py` — une mutation par règle du chef de dossier (module M0),
# chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
# Le module est pur bibliothèque standard : sans conteneur, le harnais tourne sur l'hôte et le dit.
#   bash checks/negatif_chef_de_dossier.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_chef_de_dossier.py"
HOTE_SI_SANS_CONTENEUR=1
AUT="app/modules/chef_de_dossier/automate.py"
CTR="app/modules/chef_de_dossier/contrat.py"

mutations=(
# [D1] un pas déclaré deux fois n'est plus refusé : le second serait ignoré en silence.
"$AUT¦    if doublons:¦    if False:¦[D1] pas déclaré deux fois refusé"
# [D2] un pas humain est franchi sans vous : la carte serait « validée » par l'automate.
"$AUT¦            return _arreter(etat, parcours, ARRET_ACTE_HUMAIN, pas=pas.nom, cle=pas.nom, acte=pas.acte)¦            etat = replace(etat, faits=etat.faits + (pas.nom,))\n            continue¦[D2] trois arrêts"
# [D3] le palier n'arrête plus rien : la dépense s'emballe sans pause.
"$AUT¦>= palier_usd - _EPS:¦>= palier_usd * 1000:¦[D3] pause dès que 1 \$ est consommé"
# [D3] le coût restant compte aussi les pas déjà faits : l'estimation jusqu'au comité serait gonflée.
"$AUT¦for p in parcours if p.nom not in etat.faits), 6)¦for p in parcours), 6)¦[D3] la pause dit le coût restant estimé"
# [D3] avancer lève tout seul un arrêt : une pause ne tiendrait qu'un tour.
"$AUT¦    if etat.arret is not None:¦    if False:¦[D3] avancer sur un dossier en pause ne fait rien"
# [D4] on insiste sans fin sur un pas qui échoue.
"$AUT¦ECHECS_AVANT_ARRET = 2 ¦ECHECS_AVANT_ARRET = 99¦[D4] deux échecs de suite"
# [D5] « source indisponible » redevient un échec : la société sans dépôt ne traverserait plus.
"$AUT¦        if rendu.issue in (FAIT, INDISPONIBLE):¦        if rendu.issue in (FAIT,):¦[D5] la réserve reste au dossier"
# [D6] par défaut on ne lit plus rien : l'automatisation deviendrait la règle, la lecture l'exception.
"$AUT¦    return True if lecture_humaine is None else¦    return False if lecture_humaine is None else¦[D6] par défaut, la première sortie de module attend votre lecture"
# [D6] un module oublié dans la table des interrupteurs n'est plus lu.
"$AUT¦lecture_humaine.get(pas.module, True))¦lecture_humaine.get(pas.module, False))¦[D6] un module absent de la table est lu"
# [D7] un état d'une autre version de contrat est lu « au mieux ».
"$CTR¦        if version != VERSION_CONTRAT:¦        if False:¦[D7] un état d'une autre version de contrat est refusé"
# [D8] les recherches web sortent du total : le coût complet d'un dossier redevient invisible.
"$CTR¦        return _usd(self.modeles_usd + self.web_usd)¦        return _usd(self.modeles_usd)¦[D8] le journal porte chaque dépense"
# [D8] un essai échoué n'est plus compté : un abandon serait gratuit (convention #41).
"$AUT¦        etat = _ajouter_depense(etat, pas.nom, rendu.depense)¦        etat = _ajouter_depense(etat, pas.nom, rendu.depense if rendu.issue != ECHEC else Depense())¦[D8] un essai échoué est compté comme dépensé"
# [D9] n'importe quel acte lève l'arrêt en cours.
"$AUT¦    if cle != a.cle:¦    if False:¦[D9] on n'enregistre pas un autre acte que celui attendu"
# [D10] l'automate se met à parler au réseau.
"$AUT¦from dataclasses import replace¦from dataclasses import replace\nimport urllib.request¦[D10] automate.py importe \`urllib.request\`"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
