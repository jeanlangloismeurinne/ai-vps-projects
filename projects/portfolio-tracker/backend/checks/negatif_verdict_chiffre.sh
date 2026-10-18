#!/usr/bin/env bash
# TEST NÉGATIF de `check_verdict_chiffre.py` — une mutation par DÉCISION de la règle « un verdict ne
# contredit jamais le chiffre qui le porte » (#139 ter), chacune exigeant exit≠0 + FAIL sur l'assert
# NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_verdict_chiffre.sh
#
# Mutées : l'issue d'un chiffre absent et la pente qui hérite du non défini ; les trois branches du
# détenteur ; ses deux lecteurs (pont [S bis], contrôleur ② et la revue qui lui passe la question) ; le
# verdict écrit par le code, la question retirée du contexte, la fermeture de `repondu` faute de chiffre,
# la porte jugée avant la restriction, le sens « n.s. » caché au modèle ; le contrat du référentiel.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_verdict_chiffre.py"
R="app/knowledge/ratios_maison.py"
F="app/agents/v2/frameworks.py"
M="app/agents/v2/manager.py"
A="app/agents/v2/analyste.py"
S="app/contracts/framework_definition_schema.py"
mutations=(
"$R¦    return NON_SIGNIFICATIF if m.startswith(_PREFIXES_NON_SIGNIFICATIF) else MANQUE¦    return MANQUE¦« non calculable » et « non défini » sont NON SIGNIFICATIFS"
"$R¦            if any(issue_du_motif(m) == NON_SIGNIFICATIF for _f, m in absents):¦            if False:¦la pente de RVMD hérite du rendement NON DÉFINI"
"$F¦        if sens != SENS_NON_SIGNIFICATIF:¦        if False:¦verdict sur un chiffre non significatif (le cas #1688) → contradiction"
"$F¦    if issue_du_motif(ligne.motif_absence) == NON_SIGNIFICATIF:¦    if True:¦verdict sur un chiffre qui manque → contradiction"
"$F¦        if sens == SENS_NON_SIGNIFICATIF:¦        if False:¦« non significatif » sur un chiffre établi → contradiction"
"$F¦        raise FrameworkAnswerRefused(f\"[S bis] {contradiction}\")¦        pass¦pont : verdict sur un chiffre non significatif"
"$M¦    contradiction = motif_verdict_contredit_son_chiffre(answer, sens_lu_sur)¦    contradiction = None¦contrôleur (à la lecture) : verdict sur un chiffre non significatif"
"$M¦            sens_lu_sur=qdef_lue.sens_lu_sur if qdef_lue is not None else None,¦            sens_lu_sur=None,¦la revue du chapitre passe"
"$A¦                question_id=q.id, statut=\"repondu\", sens=SENS_NON_SIGNIFICATIF,¦                question_id=q.id, statut=\"repondu\", sens=\"en_erosion\",¦RVMD qf_5 : écrit « non significatif » par le code"
"$A¦            continue  # #139 ter : le code écrit le verdict « non significatif » (cf. \`repondre\`)¦            pass¦le modèle ne les voit pas"
"$A¦    if lecture is not None and lecture[0] == \"manque\":¦    if False:¦chiffre manquant : \`repondu\`/\`approxime\` FERMÉS"
"$A¦        if aucune_reponse_possible(statuts_admissibles(q, citables)[0]):¦        if aucune_reponse_possible(statuts_ouverts(q, citables, entries)[0]):¦la question RESTE posée"
"$A¦            \"sens_admis\": [s for s in q.sens_admis if s != SENS_NON_SIGNIFICATIF],¦            \"sens_admis\": list(q.sens_admis),¦n'est JAMAIS montré au modèle"
"$A¦                if not pieces or set(e.types) & TYPES_QUI_TOUCHENT_LES_COMPTES_CLOS:¦                if not pieces:¦un RETRAITEMENT des comptes n'est jamais déclaré lu"
"$A¦                cited_entry_ids=[lecture[2]], faits_posterieurs=lus,¦                cited_entry_ids=[lecture[2]],¦un communiqué trimestriel (écarts) est LU"
"$S¦        if (self.sens_lu_sur is not None) != (SENS_NON_SIGNIFICATIF in self.sens_admis):¦        if False:¦sans chiffre porteur est refusé"
"$S¦            if lu is None or lu.socle is None:¦            if False:¦ne nomme aucun chiffre des comptes est refusé"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
