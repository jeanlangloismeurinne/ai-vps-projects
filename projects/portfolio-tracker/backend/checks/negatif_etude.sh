#!/usr/bin/env bash
# TEST NÉGATIF de `check_etude.py` — au moins une mutation par garde du déclencheur (M3 §3, K10 et K11
# sur société fictive ; arbitrage du 2026-11-21 sur la relecture humaine), chacune exigeant exit≠0 +
# FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`). Module pur bibliothèque standard :
# sans conteneur, le harnais tourne sur l'hôte et le dit. Les gardes déléguées (filtre par dossier de
# la collecte) se mutent chez leur détenteur.
#   bash checks/negatif_etude.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_etude.py"
HOTE_SI_SANS_CONTENEUR=1
C="app/modules/etude/coeur.py"
K="app/modules/etude/contrat.py"
J="app/modules/etude/referentiel.json"
CPT="app/modules/comptes/referentiel.json"
RC="app/modules/recueil/coeur.py"

mutations=(
# [T0] le cœur ouvre lui-même une connexion.
"$C¦import json¦import json\nimport urllib.request¦[T0] ni réseau, ni base, ni modèle"
# [K11] le besoin réel des comptes perd ses données structurées.
"$CPT¦    {\"genre\": \"donnees_comptables_structurees\"}¦    {\"genre\": \"comptes_intermediaires\", \"depuis\": \"2026-01-01\"}¦[K11] le besoin réel des comptes"
# [K11] le passage n'écoute plus les modules consommateurs.
"$C¦    return {COMPTES.NOM_DU_MODULE: COMPTES.besoins_initiaux()}¦    return {}¦[K11] le passage rassemble les besoins"
# [K11] le même genre demandé par deux modules est collecté deux fois.
"$C¦            demandes.setdefault(d.cle, d)¦            demandes[f\"{module}|{d.cle}\"] = d¦[K11] deux modules qui se recoupent"
# [K11] un genre inconnu passe (il planterait plus loin, sans nommer le module).
"$C¦            if genre is None:¦            if False:¦[K11] un besoin mal formé est refusé avec le module qui l'a déclaré (genre inconnu)"
# [K11] le refus ne nomme plus le module.
"$C¦f\"« {module} » déclare un genre de document inconnu¦f\"on déclare un genre de document inconnu¦[K11] un besoin mal formé est refusé avec le module qui l'a déclaré (genre inconnu)"
# [K11] un champ inconnu passe.
"$C¦            if inconnus or not str(¦            if not str(¦[K11] un besoin mal formé est refusé avec le module qui l'a déclaré (champ inconnu)"
# [K11] un genre « depuis » sans date passe.
"$C¦            if (genre[\"etendue\"] == \"depuis\") != bool(¦            if False and (genre[\"etendue\"] == \"depuis\") != bool(¦[K11] un besoin mal formé est refusé avec le module qui l'a déclaré (genre « depuis » sans date)"
# [K10] une société sans fiche se met à l'étude.
"$C¦    if await _fiche(monde, dossier) is None:¦    if False:¦[K10] une société sans fiche"
# [K10] une étude se réécrit (chez le détenteur de l'ajout seul).
"$K¦        if etude[\"dossier\"] in self._etudes:¦        if False:¦[K10] une seule étude par société"
# [K10] un dossier non mis à l'étude avance quand on passe dessus.
"$C¦    if await monde.etude.etude(dossier) is None:  # non étudié : rien ne se fait¦    if False:¦[K10] un dossier non mis à l'étude n'avance jamais"
# [K10] la tâche de fond ne relève plus les collectes.
"$C¦        if monde.outils is None:¦        if True:¦[K10] la tâche de fond relève les collectes lancées"
# [K10] les documents arrivés ne sont plus mis en lecture.
"$C¦            lectures = await K.lire_documents(¦            if False: lectures = await K.lire_documents(¦[K10] les documents arrivés sont mis en lecture"
# [K10] l'état et ce qu'il lance ne sont plus rangés ensemble.
"$C¦        async with monde.transaction():  # ensemble ou pas du tout¦        async with __import__(\"contextlib\").AsyncExitStack():¦[K10] l'état refusé : aucune demande de collecte n'est lancée"
# [K10] le refus de ranger ne se dit plus.
"$C¦        pannes.append(f\"avancement du dossier : {type(exc).__name__}: {exc}\")¦        pass¦[K10] le refus se dit dans le passage"
# [K10] un passage ne regarde plus si un autre tient le dossier.
"$C¦    if not await monde.etude.prendre(dossier):¦    if False:¦[K10] deux passages simultanés : le second ne relève rien"
# [K10] le dossier n'est jamais rendu.
"$C¦        await monde.etude.rendre(dossier)¦        pass¦[K10] le dossier rendu, le passage suivant reprend"
# [K10] la pause ne suspend plus le payant.
"$C¦    if not suspendu:¦    if True:¦[K10] rien de payant sur un dossier en pause"
# [K10] la pause de dépense n'est plus reconnue (terminé seul).
"$C¦    return etat.arret is not None and etat.arret.motif in (CD.ARRET_PAUSE_DEPENSE, CD.ARRET_PARCOURS_TERMINE)¦    return etat.arret is not None and etat.arret.motif in (CD.ARRET_PARCOURS_TERMINE,)¦[K10] rien de payant sur un dossier en pause"
# [K10] l'évaluation des sources n'est plus bornée au dossier.
"$C¦                        le=le, emetteur=dossier)¦                        le=le)¦[K10] le passage d'un autre dossier ne paie rien pour un dossier en pause"
# [K10] … ni chez son détenteur.
"$RC¦        if s[\"statut\"] != A_EVALUER or (emetteur is not None and s[\"emetteur\"] != emetteur):¦        if s[\"statut\"] != A_EVALUER:¦[K10] le passage d'un autre dossier ne paie rien pour un dossier en pause"
# [K10] lever la pause ne lève rien.
"$C¦                etat = CD.lever_pause(etat)¦                pass¦[K10] la pause levée, le travail payant reprend"
# [L1] l'évaluation des sources appelle une relecture de plus.
"$J¦    \"recueil:evaluation_des_sources\": false,¦    \"recueil:evaluation_des_sources\": true,¦[L1] un seul arrêt pour vous"
# [L1] les interrupteurs ne sont plus transmis : tout est relu.
"$C¦            apres = CD.avancer(avant, pas, lecture_humaine=referentiel()[\"lecture_humaine\"])¦            apres = CD.avancer(avant, pas, lecture_humaine=None)¦[L1] un seul arrêt pour vous"
# [L1] la collecte n'est plus relue.
"$J¦    \"recueil\": true,¦    \"recueil\": false,¦[L1] un seul arrêt pour vous"
# [T1] un geste sur une société non étudiée passe.
"$C¦        raise GesteRefuse(f\"« {dossier} » n'est pas à l'étude\")¦        pass¦[T1] un geste sur une société non étudiée est refusé"
# [T1] le refus du chef de dossier n'est plus traduit (il fuit tel quel).
"$C¦        except CD.GesteRefuse as exc:¦        except KeyError as exc:¦[T1] un acte non attendu est refusé"
# [T2] chaque passage est noté, même vide.
"$C¦    if a_bouge:¦    if True:¦[T2] seul un passage qui a fait quelque chose est noté"
# [T2] une panne de lecture se tait.
"$C¦        pannes.append(f\"mise en lecture : {type(exc).__name__}: {exc}\")¦        pass¦[T2] une panne en route se dit dans le passage"
# [T2] une panne de lecture arrête le passage.
"$C¦        pannes.append(f\"mise en lecture : {type(exc).__name__}: {exc}\")¦        return Passage(dossier=dossier, le=le, issue=AVANCE, detail=f\"mise en lecture : {exc}\")¦[T2] la panne n'empêche pas le dossier d'avancer"
# [T2] la lecture rend le premier passage, pas le dernier.
"$C¦_passage(passages[-1]) if passages else None¦_passage(passages[0]) if passages else None¦[T2] la lecture du module"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
