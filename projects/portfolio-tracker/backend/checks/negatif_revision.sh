#!/usr/bin/env bash
# TEST NÉGATIF de `check_revision.py` — la règle PURE de la révision à la baisse (point 13),
# `app/agents/v2/revision.py`.
#
#   bash checks/negatif_revision.sh
#
# NON MUTÉS, et c'est voulu (même doctrine que `negatif_parcours.sh` pour les refus du contrat :
# « script mort » n'est pas « rouge sur l'assert visé ») :
#   · `if precedente is None: return None` (§4) — le retirer lève un `AttributeError` sur
#     `precedente.statut_brut` ;
#   · le rang par défaut de `sans_objet` dans `RANG_FONDEMENT.get(...)` (§3) — le faire glisser
#     dans la comparaison fait ensuite chuter `_resume`/le calcul de `raison` sur un `.reponse` ou
#     un `.gap` absents (un `sans_objet` n'a NI l'un NI l'autre) : c'est la FORME de l'objet, pas
#     une branche de calcul, qui garantit que ces lignes ne sont jamais atteintes avec un
#     `sans_objet` — l'affaiblir casse l'invariant que tout le reste de la fonction suppose acquis.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_revision.py"
R="app/agents/v2/revision.py"
mutations=(
"$R¦RANG_FONDEMENT: dict[str, int] = {\"non_fondable\": 1, \"approxime\": 2, \"repondu\": 3}¦RANG_FONDEMENT: dict[str, int] = {\"non_fondable\": 1, \"approxime\": 3, \"repondu\": 2}  # mutation¦l'ordre de fondement est EXACTEMENT celui de la spec"
# §2 — l'égalité de fondement n'est pas une baisse.
"$R¦    if rang_courant >= rang_precedent:¦    if rang_courant > rang_precedent:  # mutation: l'égalité serait une baisse¦fondement ÉGAL"
# §5 — fin du signal : seule une décision POSTÉRIEURE à la courante l'éteint.
"$R¦    if any(d.decide_le > courante.cree_le for d in decisions):¦    if any(d.decide_le for d in decisions):  # mutation: n'importe quelle décision éteint le signal¦ANTÉRIEURE à la courante NE l'éteint PAS"
"$R¦    if any(d.decide_le > courante.cree_le for d in decisions):¦    if False:  # mutation: aucune décision n'éteint jamais le signal¦POSTÉRIEURE éteint le signal"
# §6 — le rétablissement et son motif.
"$R¦    retablissable = precedente.answer is not None¦    retablissable = True  # mutation: toujours rétablissable, même illisible¦NON rétablissable, et le motif renvoie vers #137"
"$R¦        return f\"réponse \`{r.statut_brut}\` écrite sous un contrat antérieur — illisible telle quelle\"¦        return \"texte deviné\"  # mutation: un verbatim deviné dans un JSON invalide¦le résumé de la précédente illisible le DIT"
"$R¦        raise ValueError(\"la réponse COURANTE doit toujours valider contre le contrat en vigueur — appel fautif\")¦        return None  # mutation: un silence au lieu de lever¦doit LEVER"
"$R¦        return FrameworkAnswer.model_validate(answer_json)¦        return None  # mutation: ne valide plus jamais¦qui valide contre le contrat en vigueur se relit"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
