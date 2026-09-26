#!/usr/bin/env bash
# TEST NÉGATIF de `check_memo_projete.py` — une mutation par critère.
#
# Les trois conditions, tenues par le harnais (`checks/_negatif.sh`), jamais une seule :
#   1. le check sort en ÉCHEC (exit ≠ 0) ;
#   2. l'assert ATTENDU, nommé, porte le FAIL — pas un autre ;
#   3. le script atteint quand même sa ligne de BILAN.
#
# ⚠️ LA MUTATION QUI COMPTE EST CELLE DE §4. Toutes les autres éprouvent des gardes ordinaires ;
# celle-là éprouve la GARANTIE DU LOT. Elle fait exactement ce que le lot interdit : elle transforme
# le projecteur en projecteur des DEUX pilotes (`fichier.frameworks[:2]`). Le référentiel augmenté
# charge toujours, la note sort toujours complète, les deux rubriques pilotes sont toujours justes —
# et pourtant le troisième chapitre reste « sans méthodologie approuvée ». Si ce check restait vert
# là-dessus, il ne mesurerait que le présent, jamais la croissance.
#
#   bash checks/negatif_memo_projete.sh
set -u
cd "$(dirname "$0")/.." || exit 1

BLOCS="app/contracts/memo_blocs.py"
NOTE="app/contracts/memo_projete_schema.py"
PROJ="app/agents/v2/projection_memo.py"
PONT="app/agents/v2/frameworks.py"

# ── fichier ¦ motif remplacé ¦ remplaçant ¦ assert qui DOIT rougir ──────────────────────────────
mutations=(
# §1 — l'ordre du jour est dérivé, et complet
"$BLOCS¦    \"posture\": \"verrou Q2 (aucun verdict dans le mémo) — une propriété du mémo\",¦    # un méta-champ qui cesse d'être déclaré¦recouvre EXACTEMENT les champs"
"$BLOCS¦    \"schema_version\": \"version du contrat — une propriété du mémo, pas de l'émetteur\",¦    \"schema_version\": \"meta\",¦porte le MOTIF qui l'exclut"
"$BLOCS¦            out.add(f\"{prefixe}.{nom}\")¦            out.add(nom)¦les feuilles sont préfixées par un bloc"
"$BLOCS¦BLOCS_MEMO: dict[str, type] = _deriver_blocs()¦BLOCS_MEMO: dict[str, type] = {n: c for n, c in _deriver_blocs().items()}¦est DÉRIVÉ de"

# §2 — le contrat de la note. ⚠️ Les DEUX états du milieu, séparément : fusionnés, c'est le faux
# mesuré sur RVMD le 2026-09-24, et c'est la raison d'être du quatrième état.
# ⚠️ Le motif s'arrête à la parenthèse fermante : il ne vise donc QUE `ETATS_RUBRIQUE`, pas le
# `Literal` de la ligne suivante (le harnais ne convertit pas `\n` dans le motif, et `replace`
# n'opère qu'une fois). Deux asserts rougissent alors, ce qui est juste : retirer un état d'un seul
# des deux détenteurs, c'est les faire diverger.
"$NOTE¦    \"instruite\", \"sans_acquittement\", \"non_revalidable\", \"pas_de_methodologie_approuvee\")¦    \"instruite\", \"sans_acquittement\", \"pas_de_methodologie_approuvee\")¦les deux états du milieu existent"
"$NOTE¦        if self.etat in (\"sans_acquittement\", \"non_revalidable\") and self.points:¦        if self.etat == \"sans_acquittement\" and self.points:¦\`non_revalidable\` qui porte quand même un point"
"$NOTE¦        if self.etat == \"instruite\" and not self.points:¦        if False:¦\`instruite\` SANS aucun point"
"$NOTE¦        if not acquitte:¦        if False:¦publie une réponse NON acquittée"
"$NOTE¦        if self.answer.question_id != self.question_id:¦        if False:¦un point MAL ÉTIQUETÉ"
"$NOTE¦        if manquants:¦        if False:¦ne dit PAS à quelle méthodologie"
"$NOTE¦            if portes:¦            if False:¦qui nomme quand même un framework"
"$NOTE¦            if self.points or self.reponses_non_acquittees:¦            if self.points:¦qui compte des réponses au dossier"
"$NOTE¦        if set(vus) != attendus:¦        if False:¦une note à qui il MANQUE un chapitre"
"$NOTE¦        if len(set(vus)) != len(vus):¦        if False:¦DEUX fois le même chapitre"

# §3 — le projecteur refuse plutôt que de sauter, et produit ses quatre états
"$PROJ¦        if a.ticker_id != ticker_id:¦        if False:¦une réponse d'un AUTRE émetteur"
"$PROJ¦        if f is None:¦        if f is None and False:¦rattachée à un framework ABSENT"
"$PROJ¦        if a.framework_version != fichier.schema_version:¦        if False:¦une version PÉRIMÉE du référentiel"
"$PROJ¦        if a.question_id not in {q.id for q in f.questions}:¦        if False:¦dont la question est inconnue de SON framework"
"$PROJ¦        if archetype is None:¦        if False:¦émetteur NON CLASSÉ"
"$PROJ¦        non_acquittees = len(du_framework) - len(publiees)¦        non_acquittees = 0¦le renvoi n'est pas publié mais il est COMPTÉ"
"$PROJ¦        publiees.sort(key=lambda p: (rang[p[0].answer.question_id], p[0].answer.analyste))¦        publiees.sort(key=lambda p: (rang[p[0].answer.question_id],))¦un ordre décidé par le référentiel + l'analyste"

# §4 — ⚠️ LA PREUVE DU LOT. Un projecteur qui ne connaîtrait que les deux pilotes.
"$PROJ¦    par_bloc = {f.bloc_memo: f for f in fichier.frameworks}¦    par_bloc = {f.bloc_memo: f for f in fichier.frameworks[:2]}¦le chapitre est instruit par le YAML"
"$PONT¦        if f.bloc_memo in revendique:¦        if False:¦croître sur un chapitre DÉJÀ revendiqué"

# §5 — le versant statique : un nom de framework qui se glisse dans le code, une écriture qui
# s'y glisse. Les deux sont MORTS (personne ne les appelle) et c'est le point : §5 doit rougir sur
# la seule PRÉSENCE, sans qu'aucun comportement ne change.
"$PROJ¦__all__ = [\"AnswerLue\", \"ProjectionRefusee\", \"projeter_memo\", \"memo_de_l_etat\"]¦__all__ = [\"AnswerLue\", \"ProjectionRefusee\", \"projeter_memo\", \"memo_de_l_etat\"]\n_PILOTES = (\"qualite_financiere\", \"defendabilite\")¦aucun id de framework ni nom de chapitre"
"$PROJ¦__all__ = [\"AnswerLue\", \"ProjectionRefusee\", \"projeter_memo\", \"memo_de_l_etat\"]¦__all__ = [\"AnswerLue\", \"ProjectionRefusee\", \"projeter_memo\", \"memo_de_l_etat\"]\n_TRACE = \"INSERT INTO memo_trace (ticker_id) VALUES (\$1)\"¦n'ÉCRIT rien"
)

CHECK="checks/check_memo_projete.py"
source "$(dirname "$0")/_negatif.sh"
run_mutations
