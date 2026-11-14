#!/usr/bin/env bash
# TEST NÉGATIF de `check_emetteurs.py` — au moins une mutation par ligne d'acceptation du module M1
# (`roadmap/V3/M1-fiche-emetteur.md` §2), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan
# atteint (harnais `_negatif.sh`). Le module est pur bibliothèque standard : sans conteneur, le
# harnais tourne sur l'hôte et le dit.
#   bash checks/negatif_emetteurs.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_emetteurs.py"
HOTE_SI_SANS_CONTENEUR=1
REG="app/modules/emetteurs/regles.py"
CTR="app/modules/emetteurs/contrat.py"

mutations=(
# [A1] n'importe quelle chaîne devient un identifiant maison.
"$REG¦    if not _IDENTIFIANT.match(emetteur or \"\"):¦    if False:¦[A1] un identifiant maison mal formé est refusé"
# [A1] « www. » reste dans l'adresse rangée : le même site aurait deux écritures.
"$REG¦    if hote.startswith(\"www.\"):¦    if False:¦[A1] les lieux de publication sont rangés sans protocole"
# [A2] le pays devient obligatoire : une société dont on ne sait pas le pays n'aurait plus de fiche.
"$REG¦    if pays and not _PAYS.match(pays):¦    if not _PAYS.match(pays):¦[A2]"
# [A3] la spécialité n'ouvre plus ses sources.
"$REG¦    if contenu[\"specialite\"]:¦    if False:¦[A3] avec spécialité : générale + spécialité + propre à l'émetteur"
# [A3] toutes les sources valent pour tout le monde : la portée ne filtre plus.
"$REG¦        sources=tuple(s for s in admises.values() if s.portee in portees),¦        sources=tuple(admises.values()),¦[A3] sans spécialité, la fiche porte les sources générales"
# [A4] redire la même fiche empile des révisions vides.
"$REG¦    if rangees and all(rangees[-1].get(k) == v for k, v in declare.items()):¦    if False:¦[A4] redire exactement la même fiche"
# [A4] une révision passe sans motif.
"$REG¦\"motif\": _texte(motif, \"motif\"), \"le\": _date(le)}¦\"motif\": motif, \"le\": _date(le)}¦[A4] une révision sans motif est refusée"
# [A5] une source admise pour une nature vaut pour toutes.
"$REG¦        if nature in s.natures:¦        if True:¦[A5] la même page n'est pas admise pour une mesure"
# [A5] un chemin voisin passe pour celui des relations investisseurs.
"$REG¦chemin.startswith(chemin_lieu + \"/\")¦chemin.startswith(chemin_lieu)¦[A5] un chemin qui ressemble"
# [A5] le lieu le MOINS précis l'emporte : les relations investisseurs tombent au niveau du site.
"$REG¦        lieu = max(lieux, key=lambda x: (x[0], x[1]))[2]¦        lieu = min(lieux, key=lambda x: (x[0], x[1]))[2]¦[A5] les pages de relations investisseurs"
# [A6] le système admet sans citer de critère.
"$REG¦            if not critere:¦            if False:¦[A6]"
# [A6] le système accorde plus que le plafond de son critère.
"$REG¦            if _rang_niveau(niveau) < _rang_niveau(regle[\"niveau_max\"]):¦            if False:¦[A6] le système n'accorde pas plus que le plafond"
# [A6] le système admet pour une nature que son critère ne couvre pas.
"$REG¦            if hors:¦            if False:¦[A6] le système n'admet pas pour une nature"
# [A6] une page passe pour une source.
"$REG¦    if hc is None or hc[1]:¦    if hc is None:¦[A6] une source se nomme par son domaine"
# [A6] une admission vise un émetteur qui n'existe pas.
"$REG¦        if not await depot.fiches(emetteur):¦        if False:¦[A6] une portée sur un émetteur sans fiche"
# [A6] une admission passe sans date.
"$REG¦    le = _date(le)¦    le = le¦[A6] une admission sans date est refusée"
# [A7] celui qui utilise une source la qualifie.
"$REG¦    if role in referentiel()[\"roles_qui_utilisent_les_sources\"]:¦    if False:¦[A7] le rôle « collecteur »"
# [A8] le système revient sur la décision de l'utilisateur.
"$REG¦        if dernier.get(cle) == UTILISATEUR:¦        if False:¦[A8] le système ne réadmet pas"
# [A9] la révocation signale aussi les pièces d'une autre nature d'information.
"$REG¦            touchee = _couvre(r.source, hc[0]) and o.nature in r.natures¦            touchee = _couvre(r.source, hc[0])¦[A9] une seule pièce"
# [A9] une pièce encore couverte par une autre admission est signalée à tort.
"$REG¦            if touchee and not qualifier(fiche, o.adresse, o.nature).admise:¦            if touchee:¦[A9] une pièce couverte par une autre admission"
# [A9] la révocation ne retire rien : la source reste admise.
"$REG¦            retiree = admises.pop(cle, None)¦            retiree = admises.get(cle)¦[A9] une seule pièce"
# [A10] un domaine qui finit comme une source admise passe pour elle.
"$REG¦    return hote == domaine or hote.endswith(\".\" + domaine)¦    return hote.endswith(domaine)¦[A10] un domaine qui ressemble"
# [A10] une adresse illisible est rangée au niveau d'une source inconnue mais nommée.
"$REG¦        return Qualification(False, ref[\"niveau_adresse_illisible\"],¦        return Qualification(False, plancher,¦[A10] une adresse illisible"
# [A6] un domaine mal formé est rangé « au mieux ».
"$REG¦    if not _DOMAINE.match(hote):¦    if not hote:¦[A6] une source qui n'est pas un domaine"
# [A11] sans fiche, le dossier avance quand même.
"$CTR¦        if fiche is None:¦        if False:¦[A11] sans fiche, le chef de dossier s'arrête"
# [A11] la fiche d'une société fait avancer le dossier d'une autre.
"$CTR¦        if fiche.emetteur != contexte.dossier:¦        if False:¦[A11] la fiche d'une société ne fait pas avancer"
# [A16] n'importe quel premier élément de nom de domaine passe pour une page de relations investisseurs.
"$REG¦    if hote.split(\".\", 1)[0] not in referentiel()[\"prefixes_relations_investisseurs\"]:¦    if False:¦[A16] seules les adresses DÉDIÉES"
# [A16] un domaine entier (« investors.example ») passe pour la section d'une société.
"$REG¦    if hote.count(\".\") < 2:¦    if False:¦[A16] seules les adresses DÉDIÉES"
# [A16] le système rétablit une page que l'utilisateur a révoquée.
"$REG¦        if dernier.get(cle) == UTILISATEUR:  # l'utilisateur a statué : on n'y revient pas¦        if False:¦[A16]"
# [A16] le geste ne reconnaît plus une page déjà admise : le second passage tombe sur un refus.
"$REG¦        if cle in admises:¦        if False:¦[A16] section interrompue"
# [A16] le geste du système ne cite plus son critère : l'admission serait refusée, rien n'entre.
"$REG¦critere=CRITERE_PAGES_INVESTISSEURS,¦critere=\"\",¦[A16]"
# [A0] le module se met à parler au réseau.
"$REG¦import json¦import json\nimport socket¦[A0] regles.py importe \`socket\`"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
