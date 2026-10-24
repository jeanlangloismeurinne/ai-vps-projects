#!/usr/bin/env bash
# Test négatif de `checks/check_inventaire.py` (maillon 1 du découpage, plan B4g, 2026-10-24) : chaque
# garde de `verifier_inventaire`, du contrat et du prompt, mutée une à une, doit faire rougir L'ASSERT
# qui la nomme (`feedback_test_negatif_obligatoire`, `feedback_test_negatif_trois_faux_verts`).
set -u
cd "$(dirname "$0")/.." || exit 1

I="app/modele_entreprise/inventaire.py"
C="app/contracts/inventaire_schema.py"
CHECK="checks/check_inventaire.py"
NET=none

mutations=(
  "$I¦        hors = [p for p in f.pieces if p not in entries]¦        hors = []¦pièce hors du dossier : écartée"
  "$I¦        textes = [_texte_piece(entries[p]) for p in f.pieces]¦        textes = [_texte_piece(e) for e in entries.values()]¦pas dans la pièce CITÉE"
  "$I¦        if cle in par_cle:¦        if False:¦FUSIONNÉ"
  "$I¦        if not dans(f.extrait):¦        if False:¦extrait paraphrasé"
  "$I¦            _forme_lisible(_PARENTHESE.sub(\" \", f.marche_vise or \"\")))¦            \"\")¦DEUX marchés"
  "$I¦    return _forme_comparable(_MISE_EN_FORME.sub(\" \", texte))¦    return \" \".join(texte.split())¦casse, espaces"
  "$I¦            if not any(_forme_lisible(f.nom) in _texte_piece(e) for e in entries.values()):¦            if False:¦nom absent du dossier"
  "$I¦            inv.signaux.append(f\"« {f.nom} » : nom absent des pièces citées {f.pieces}, présent ailleurs au dossier\")¦            pass¦alias"
  "$I¦        if f.marche_vise and not dans(f.marche_vise):¦        if False:¦marché visé reformulé"
  "$I¦    return (_forme_lisible(_PARENTHESE.sub(\" \", f.nom)),¦    return (_forme_lisible(f.nom),¦entre parenthèses"
  "$I¦        if hors or not any(¦        if False and not any(¦relevé des non nommés inventé"
  "$C¦    nombre: Annotated[int, Field(ge=1)]¦    nombre: int¦\`nombre\` = 0 de non nommés"
  "$C¦    origine: Literal[\"interne\", \"acquisition\", \"licence\", \"partenariat\", \"non_dit\"]¦    origine: str¦\`origine\` = 'inconnue'"
  "$C¦    extrait: Annotated[str, Field(min_length=20)]¦    extrait: str¦\`extrait\` = 'trop court'"
  "$I¦UNITÉ — une fiche par ÉLÉMENT × MARCHÉ¦UNITÉ¦l'unité est FIXÉE"
  "$I¦    \"élément cité partout. Ne classe pas¦    \"élément cité partout. Classe aussi¦relever sans classer"
  "$I¦MODELE_INVENTAIRE = \"deepseek-ai/DeepSeek-V4.1-Flash-1017\"¦MODELE_INVENTAIRE = \"deepseek-ai/DeepSeek-V4.1-Flash\"¦version FIGÉE"
  "$I¦        date = e.get(\"date_du_document\") or e.get(\"source_date\")¦        date = e.get(\"source_date\")¦date du document"
  "$I¦    for i in sorted(entries):¦    for i in sorted(entries, reverse=True):¦dans l'ordre"
  "$I¦    return _forme_comparable(_MISE_EN_FORME.sub(\" \", texte))¦    return _forme_comparable(texte)¦pièce en gras Markdown"
  "$I¦NE TRADUIS PAS¦traduis si besoin¦ne pas traduire"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
