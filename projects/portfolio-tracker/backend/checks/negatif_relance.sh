#!/usr/bin/env bash
# TEST NÉGATIF de `check_relance.py` — une mutation par DÉCISION de la relance bornée et de la
# réinitialisation (#137, point 17 et 17-bis), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ +
# bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_relance.sh
#
# Mutées : la règle d'ouverture (filtre « écrite après », stricte postériorité, refus d'une acceptation
# passée comme ouvrante, branchement dans l'alerte), le périmètre (ouvert = manque), le contrat (pas
# de mandat), les actions qui rouvrent, l'ordre du passage de chapitre, le refus d'une question
# close nommée, l'arrêt de la recherche en cours, le filtre des applicables, et les écrans.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_relance.py"
WITH_FRONT=1
P="app/agents/v2/parcours.py"
C="app/agents/v2/comite.py"
S="app/contracts/comite_schema.py"
X="tools/executer_chaine.py"
A="app/api/parcours_v2.py"
REG="FRONT:components/v2/RegistreComite.js"
PAR="FRONT:components/v2/parcours.js"
mutations=(
# ── la règle d'ouverture (manque_de_la_question, 1ter) ────────────────────────────────────────
"$P¦                    if r.cree_le is not None and r.cree_le > decision_ouvrante.decide_le]¦                    if True]  # mutation: les réponses antérieures comptent¦une réponse antérieure qui tenait ne ferme plus"
"$P¦                    if r.cree_le is not None and r.cree_le > decision_ouvrante.decide_le]¦                    if r.cree_le is not None and r.cree_le >= decision_ouvrante.decide_le]  # mutation¦au MÊME instant que le geste"
"$P¦            raise ValueError(f\"décision \`{decision_ouvrante.action}\` passée comme ouvrante\")¦            pass  # mutation¦passée comme décision ouvrante est refusée"
"$P¦            cause = \"renvoi_comite\" if decision_ouvrante.action == \"renvoyer\" else \"reinitialisation\"¦            cause = \"reinitialisation\"  # mutation: le renvoi perd sa cause¦RENVOYÉE PAR LE COMITÉ"
"$P¦                                      f\"{decision_ouvrante.decide_le:%Y-%m-%d} : \"¦                                      f\"{decision_ouvrante.decide_le:%Y} : \"  # mutation: la date du geste est tronquée¦dit QUI, QUAND et POURQUOI"
"$P¦                                   and position.derniere.action in ACTIONS_OUVRANTES else None),¦                                   and False else None),  # mutation: l'alerte ignore le geste¦la question RÉINITIALISÉE est refaite"
# ── le périmètre ──────────────────────────────────────────────────────────────────────────────
"$P¦        elif lq.manque is not None:¦        elif lq.applicable:  # mutation: tout l'applicable est refait¦ouvertes = non fondée + réinitialisée"
"$P¦        elif _acceptee(lq):¦        elif False:  # mutation: l'acceptation n'est pas dite¦la question ACCEPTÉE n'est pas refaite"
"$P¦    if etat.applicables.get(f.id) is None:¦    if False:  # mutation: non classé lu comme « rien d'applicable »¦un émetteur NON CLASSÉ est refusé"
# ── le contrat ────────────────────────────────────────────────────────────────────────────────
"$S¦            if self.mandat_id is not None:  # une remise à zéro n'ouvre aucune recherche¦            if False:  # mutation¦porterait un mandat est refusée"
"$S¦ACTIONS_OUVRANTES = (\"renvoyer\", \"reinitialiser\")¦ACTIONS_OUVRANTES = (\"renvoyer\", \"reinitialiser\", \"acquitter\")¦renvoyer et réinitialiser ROUVRENT"
# ── le passage de chapitre ────────────────────────────────────────────────────────────────────
"$X¦            perimetre = frozenset(relance.ouvertes)¦            perimetre = frozenset(relance.closes) | frozenset(relance.ouvertes)  # mutation¦le périmètre EST l'ouvert"
"$X¦            fermees = sorted(demandees & set(relance.closes))¦            fermees = []  # mutation: une close nommée passe¦une question close nommée"
"$X¦        _titre(0, \"notes flash — les dépôts à qualifier publiés depuis la dernière lecture\")¦        relance = questions_a_relancer(None, framework_id)\n        _titre(0, \"notes flash — les dépôts à qualifier publiés depuis la dernière lecture\")¦PUIS calcule son périmètre"
# ── la réinitialisation ───────────────────────────────────────────────────────────────────────
"$C¦    arrete = await _arreter_la_recherche_en_cours(  # remise à zéro : la recherche en cours s'arrête¦    arrete = await _sans_effet(  # mutation: la recherche continue¦ARRÊTE la recherche en cours"
"$A¦        questions = [q.id for q in questions_applicables(fichier, framework_id, classement[0])]¦        questions = [q.id for f in fichier.frameworks if f.id == framework_id for q in f.questions]  # mutation¦que les questions APPLICABLES"
# ── les écrans ────────────────────────────────────────────────────────────────────────────────
"$REG¦  reinitialiser: { label: 'Remise à zéro', variant: 'amber' },¦¦nomme la réinitialisation"
"$PAR¦  rouverte_comite: 'Rouverte par le comité',¦¦nomme la question rouverte"
# ── #138 « pas encore observable » ────────────────────────────────────────────────────────────
"$P¦                and r.servie.gap.attente.revoir_le > jour]¦                and True]  # mutation: une attente ne s'échoit jamais¦au jour de la revue, l'attente est ÉCHUE"
"$P¦    if attentes:¦    if False:  # mutation: l'attente se confond avec la collecte¦une attente non échue RESTE à l'alerte"
"$P¦                                   f\"#{att.piece_du_fait}). Il faudra : {att.historique_requis}. \"¦                                   f\"). Il faudra : {att.historique_requis}. \"  # mutation: la pièce disparaît¦porte la justification ENTIÈRE"
"$P¦        if lq.manque is not None and lq.manque.nature == \"pas_encore_observable\":¦        if False:  # mutation: la relance recollecte l'attente¦NE recollecte PAS une attente"
"$PAR¦      {m.attente && <AttenteBloc a={m.attente} />}¦¦montre la justification ENTIÈRE d'une attente"
"$PAR¦      <dt className=\"text-gray-500\">Cause</dt><dd className=\"text-gray-200\">{a.cause}</dd>¦¦montre la justification ENTIÈRE d'une attente"
"$P¦        n_pas_encore_observable=sum(1 for lq in lignes if lq.manque is not None¦        n_pas_encore_observable=0 * sum(1 for lq in lignes if lq.manque is not None¦COMPTE ses attentes"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
