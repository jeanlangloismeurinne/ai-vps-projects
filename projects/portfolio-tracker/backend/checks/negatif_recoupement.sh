#!/usr/bin/env bash
# TEST NÉGATIF de `check_recoupement.py` — « tout chiffre renvoie à une pièce » (#136). Une mutation par
# RÈGLE du détenteur `recoupement.py` et par branchement au point de lecture, chacune exigeant exit≠0 +
# FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_recoupement.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_recoupement.py"
RC="app/agents/v2/recoupement.py"
FW="app/agents/v2/frameworks.py"
mutations=(
# ce qui établit un chiffre
"$RC¦    return [v for fr in (False, True) for _, lect, _ in nombres(texte, fr) for v, _ in lect]¦    return [v for fr in (False,) for _, lect, _ in nombres(texte, fr) for v, _ in lect]¦une fiche rédigée en français"
"$RC¦            if retrouve(lect, encadre):¦            if False:¦la dette brute et la trésorerie de l'ENCADRÉ"
"$RC¦            if resultats and retrouve(lect, resultats):¦            if False:¦un calcul MONTRÉ et juste"
# ce qui écarte un calcul
"$RC¦        if t[\"entry_id\"] not in cites:¦        if False:¦tiré d'une pièce NON CITÉE"
"$RC¦        if not (retrouve(lect, pieces.get(t[\"entry_id\"], [])) or retrouve(lect, encadre)):¦        if False:¦un terme ABSENT de sa pièce"
"$RC¦    if noms != set(termes):¦    if False:¦ne nomme pas exactement ses termes"
"$RC¦    if any(o != 0 for _, o in refs):¦    if False:¦un exercice décalé"
# ce qui n'est pas un chiffre à sourcer
"$RC¦    return (debut > 0 and txt[debut - 1].isalpha()) or bool(_APRES_LIBELLE.match(txt, fin))¦    return False¦un libellé collé"
"$RC¦            if p != annee:¦            if False:¦un libellé collé"
"$RC¦            if p != annee:¦            if True:¦l'ANNÉE d'une date en est un"
"$RC¦            if any(d == 0 and int(v) in cites for v, d in lect):¦            if False:¦le numéro d'une pièce citée"
# ce qui est contrôlé
"$RC¦    if ap.get(\"methode\"):¦    if False:¦mais la MÉTHODE l'est"
"$RC¦        parts.append((f\"fait {f.get('depot')}\", f.get(\"effet\") or \"\"))¦        pass¦l'effet d'un fait postérieur est contrôlé"
"$RC¦        parts.append((\"approximation.methode\", str(ap[\"methode\"])))¦        parts.append((\"approximation.methode\", str(ap[\"methode\"]) + \" \" + \" \".join(ap.get(\"hypotheses_explicites\") or [])))¦une hypothèse DÉCLARÉE"
# le point de lecture
"$FW¦    donnees[\"chiffres_sans_piece\"] = [c.lisible() for c in recouper(answer, entries).sans_piece]¦    donnees[\"chiffres_sans_piece\"] = []¦rend les chiffres sans pièce"
"$FW¦    donnees[\"chiffres_sans_piece\"] = [c.lisible() for c in recouper(answer, entries).sans_piece]¦    donnees[\"chiffres_sans_piece\"] = [c.lisible() for c in recouper(answer, {}).sans_piece]¦RECALCULÉS contre le dossier du moment"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
