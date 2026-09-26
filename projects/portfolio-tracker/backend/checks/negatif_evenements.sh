#!/usr/bin/env bash
# TEST NÉGATIF de `check_evenements.py` — une mutation par DÉCISION de la taxonomie (#89), chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_evenements.sh
#
# Les gardes du RÉFÉRENTIEL ([Q]/[R], `rouverte_par` requis) sont éprouvées chez leur détenteur, par
# `negatif_frameworks_definitions.sh` — pas ici (#72 : une garde déléguée se mute où la règle vit).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_evenements.py"
EV="app/knowledge/evenements.py"
ME="app/knowledge/material_events.py"
AC="app/knowledge/actualite.py"
PA="app/agents/v2/parcours.py"
API="app/api/parcours_v2.py"
mutations=(
# §1 — la forme ne décide que ce qu'elle décide
"$EV¦        return frozenset({A_QUALIFIER})¦        return frozenset({ROUTINE})¦« sans item » n'est pas « sans substance »"
"$EV¦            types.add(TYPE_PAR_ITEM.get(item, A_QUALIFIER))¦            types.add(TYPE_PAR_ITEM.get(item, ROUTINE))¦item inconnu — jamais ignoré"
"$EV¦            types.add(\"financement\" if _PREUVES_DE_FINANCEMENT & set(items) else A_QUALIFIER)¦            types.add(\"financement\")¦1.01 SANS obligation ni émission"
"$EV¦        return frozenset({A_QUALIFIER if \"7.01\" in items else ROUTINE})¦        return frozenset({ROUTINE})¦7.01 SEUL"
"$EV¦_ACCESSOIRES = frozenset({\"9.01\", \"7.01\"})¦_ACCESSOIRES = frozenset({\"9.01\"})¦7.01 accessoire du financement"
# §2/§3 — l'horloge par question
"$EV¦        touches = types & rouvrent¦        touches = types¦mo_1 (la barrière) s'ancre au 8.01 du 26/08"
"$PA¦            answer_id=i, servie=servir_answer(a, ancre=ancre_de(a.question_id), entries=entries),¦            answer_id=i, servie=servir_answer(a, ancre=ancre, entries=entries),¦chaque réponse est servie contre l'ancre de SA question"
"$PA¦                                      ancre=ancre_de(cle[1]))¦                                      ancre=ancre)¦la position du comité se juge contre l'ancre de SA question"
"$PA¦                ancre, rouvrent=types_qui_rouvrent(fichier, question_id))¦                ancre, rouvrent=frozenset({\"financement\"}))¦filtrée par \`types_qui_rouvrent\`"
"$API¦                ancre, rouvrent=types_qui_rouvrent(load_frameworks(), question_id))¦                ancre, rouvrent=frozenset())¦inscrit au PV l'ancre de SA question"
# §4 — les états traversent, un « aucun » filtré se dit
"$EV¦    if lookup.status != \"found\":¦    if lookup.status == \"none\":¦\`unavailable\` traverse"
"$AC¦                   if ancre.filtre else¦                   if False else¦le motif ne prétend pas que l'émetteur n'a rien publié"
# §5 — le motif dit pourquoi
"$ME¦        return f\"{base} — rouvre au titre de : {', '.join(self.types)}\" if self.types else base¦        return base¦se nomme par son type"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
