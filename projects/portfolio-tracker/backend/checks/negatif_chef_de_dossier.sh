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
"$AUT¦if p.nature == HUMAIN and p.nom in etat.actes_accomplis), None)¦if p.nature == HUMAIN), None)¦[D2] trois arrêts"
# [D3] le palier n'arrête plus rien : la dépense s'emballe sans pause.
"$AUT¦>= palier_usd - _EPS:¦>= palier_usd * 1000:¦[D3] pause dès que 1 \$ est consommé"
# [D3] le coût restant compte aussi les pas déjà faits : l'estimation jusqu'au comité serait gonflée.
"$AUT¦for p in parcours if p.nom not in etat.faits), 6)¦for p in parcours), 6)¦[D3] la pause dit le coût restant estimé"
# [D3] avancer lève tout seul un arrêt : une pause ne tiendrait qu'un tour.
"$AUT¦etat.arret.motif in (ARRET_PAUSE_DEPENSE, ARRET_PARCOURS_TERMINE):¦etat.arret.motif in (ARRET_PARCOURS_TERMINE,):¦[D12] toujours en pause : avancer ne fait rien"
# [D4] on insiste sans fin sur un pas qui échoue.
"$AUT¦ECHECS_AVANT_ARRET = 2 ¦ECHECS_AVANT_ARRET = 99¦[D4] deux échecs de suite"
# [D5] « source indisponible » redevient un échec : la société sans dépôt ne traverserait plus.
"$AUT¦    if rendu.issue in (FAIT, INDISPONIBLE):¦    if rendu.issue in (FAIT,):¦[D5] la réserve reste au dossier"
# [D6] par défaut on ne lit plus rien : l'automatisation deviendrait la règle, la lecture l'exception.
"$AUT¦    return True if lecture_humaine is None else¦    return False if lecture_humaine is None else¦[D6] par défaut, la première sortie de module attend votre lecture"
# [D6] un module oublié dans la table des interrupteurs n'est plus lu.
"$AUT¦lecture_humaine.get(pas.module, True))¦lecture_humaine.get(pas.module, False))¦[D6] un module absent de la table est lu"
# [D7] un état d'une autre version de contrat est lu « au mieux ».
"$CTR¦        if version != VERSION_CONTRAT:¦        if False:¦[D7] un état d'une autre version de contrat est refusé"
# [D8] les recherches web sortent du total : le coût complet d'un dossier redevient invisible.
"$CTR¦        return _usd(self.modeles_usd + self.web_usd)¦        return _usd(self.modeles_usd)¦[D8] le journal porte chaque dépense"
# [D8] un essai échoué n'est plus compté : un abandon serait gratuit (convention #41).
"$AUT¦    etat = _ajouter_depense(etat, pas.nom, rendu.depense)¦    etat = _ajouter_depense(etat, pas.nom, rendu.depense if rendu.issue != ECHEC else Depense())¦[D8] un essai échoué est compté comme dépensé"
# [D9] n'importe quel acte lève l'arrêt en cours.
"$AUT¦lambda a: a.cle == cle, cle)¦lambda a: True, cle)¦[D9] on n'enregistre pas un autre acte que celui attendu"
# [D10] l'automate se met à parler au réseau.
"$AUT¦from dataclasses import replace¦from dataclasses import replace\nimport urllib.request¦[D10] automate.py importe \`urllib.request\`"
# [D11] ce qui dépend d'une collecte part avant qu'elle aboutisse : les comptes seraient faits sans les pièces.
"$AUT¦    return all(n in etat.faits and¦    return all((n in etat.faits or n in dict(etat.en_cours)) and¦[D11] ce qui dépend de la collecte n'est pas lancé"
# [D11] on attend la collecte en ne faisant RIEN d'autre : on ne parallélise plus.
"$AUT¦        a_lancer = [p for p in prets if p.nature != HUMAIN]¦        a_lancer = [p for p in prets if p.nature != HUMAIN] if not etat.en_cours else []¦[D11] ce qui ne dépend pas de la collecte avance"
# [D11] chaque passage « toujours en cours » écrit une ligne : le journal grossit pendant l'attente.
"$AUT¦        if suivi and deja_en_cours and rendu.depense.total_usd == 0:¦        if False:¦[D11] cinquante passages sans fin de collecte"
# [D11] le défaut trouvé le 2026-11-14 : relancer remet le compteur à zéro, la collecte en échec tourne sans fin.
"$AUT¦        return replace(etat, en_cours=en_cours)¦        return replace(etat, en_cours=en_cours, echecs=_sans(etat.echecs, pas.nom))¦[D11] deuxième échec de la collecte"
# [D11] « en cours » accepté d'un pas qui ne sait pas se suivre.
"$AUT¦    if rendu.issue == EN_COURS and pas.suivre is None:¦    if False:¦[D11] « en cours » sans moyen de suivre"
# [D11] un acte humain qu'on prétend « suivre ».
"$CTR¦        if self.nature == HUMAIN and (self.executer is not None or self.suivre is not None¦        if self.nature == HUMAIN and (self.executer is not None¦[D11] un acte qui vous revient ne se « suit » pas"
# [D11] les attentes ne survivent pas au rangement : relu, le dossier ne sait plus ce qu'il attend.
"$CTR¦\"attentes\": tuple(Attente(**x) for x in arret[\"attentes\"])¦\"attentes\": ()¦[D11] un dossier en attente se range et se relit"
# [D12] l'arrêt ne dit que la première chose attendue.
"$AUT¦    return tuple(actes + echecs + travaux)¦    return tuple((actes + echecs + travaux)[:1])¦[D12] l'arrêt énumère TOUT"
# [D12] un acte attendu fige tout le dossier, même la branche qui n'en dépend pas.
"$AUT¦        a_lancer = [p for p in prets if p.nature != HUMAIN]¦        a_lancer = [p for p in prets if p.nature != HUMAIN] if not any(p.nature == HUMAIN for p in prets) else []¦[D12] un acte en attente ne retient pas la branche"
# [D12] un acte fait pendant une pause lève la pause.
"$AUT¦    if a is not None and a.motif == ARRET_PAUSE_DEPENSE:¦    if False:¦[D12] un acte fait pendant une pause est enregistré, la pause reste"
# [D12] « relancer b » relance le premier en échec, quel qu'il soit.
"$AUT¦lambda a: pas is None or a.pas == pas¦lambda a: True¦[D12] la relance vise le pas nommé"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
