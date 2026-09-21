#!/usr/bin/env bash
# TEST NÉGATIF de `check_manager.py` — une mutation par GARANTIE, chacune exigeant exit≠0 + FAIL sur
# l'assert NOMMÉ + ligne de bilan atteinte. La boucle vit dans `_negatif.sh` (détenteur unique, #65).
#   bash checks/negatif_manager.sh
#
# LES QUATRE CONTRÔLES d'abord : chaque mutation DÉSARME un contrôle (il rend `ok` là où il devait
# `ko`), et le check doit rougir sur l'assert « … ko » correspondant. Le contrôle ④ est muté CHEZ SON
# DÉTENTEUR (`frameworks.motif_substitut_hors_sujet`), partagé avec le pont — une garde déléguée
# s'éprouve là où la règle vit, jamais chez son appelant (#46, #72).
#
# PUIS L'ORCHESTRATION : un renvoi qui ne produit plus de mandat (l'Écart B rouvert), les questions
# manquantes qui s'évaporent, une dispense ignorée.
#
# ⚠️ Les asserts STRUCTURELS (§3 imports #46, §5 « ne construit pas de Reponse ») ne sont pas mutés
# ici : les désarmer casse l'import du module (le symbole disparaît), ce que la boucle classe en
# « script MORT » — un autre canal, tout aussi rouge, mais pas « rouge sur l'assert ». Ils sont
# gardés par construction (AST + grep sur le code dépouillé).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_manager.py"
MGR="app/agents/v2/manager.py"
FWK="app/agents/v2/frameworks.py"

mutations=(
# ── ① COMPLÉTUDE — une question inapplicable répondue passe (le défaut T4, entry #190) ─────────────
"$MGR¦    if not applicable and answer.statut != \"sans_objet\":¦    if False:  # mutation: une question inapplicable répondue passe¦question inapplicable répondue"
# ── ② FONDATION — le grounding ne refuse plus une citation hors corpus ────────────────────────────
"$MGR¦    if violations:¦    if False:  # mutation: le grounding ne refuse plus rien¦citation #99 hors"
# ── ③ HONNÊTETÉ — un rang non dégradé n'est plus refusé ────────────────────────────────────────────
"$MGR¦    if answer.fondation.rang_derive != degrade:¦    if False:  # mutation: le rang non dégradé passe¦gardant le rang A"
# ── ④ NON-SUBSTITUTION — muté CHEZ SON DÉTENTEUR : un substitut vers sa PROPRE question est toléré ──
"$FWK¦    if cible.question_id == answer.question_id:¦    if False:  # mutation: substitut vers la même question toléré¦vers une réponse à la MÊME question"
# ── ÉCART B — un renvoi ne produit plus de mandat ─────────────────────────────────────────────────
"$MGR¦                motif=f\"{', '.join(kos)} ko — {motif}\", mandat=mandat)¦                motif=f\"{', '.join(kos)} ko — {motif}\", mandat=None)  # mutation: renvoi sans mandat¦un renvoi PORTE un FrameworkMandate"
# ── ① framework — les questions applicables sans réponse ne sont plus manquantes ──────────────────
"$MGR¦    manquantes = [q.id for q in applicables if q.id not in answered and q.id not in dispenses]¦    manquantes = []  # mutation: aucune question jamais manquante¦sont listées manquantes"
# ── ① framework — une dispense n'est plus honorée (une question dispensée redevient manquante) ─────
"$MGR¦if q.id not in answered and q.id not in dispenses]¦if q.id not in answered]  # mutation: dispenses ignorées¦dispensée n'est ni manquante"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
