#!/usr/bin/env bash
# TEST NÉGATIF de `check_note_flash.py` — une mutation par DÉCISION de la note flash (#90), chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_note_flash.sh
#
# Ce que la note flash CHANGE au point de lecture (l'horloge par question) est éprouvé par
# `negatif_evenements.sh`, chez son détenteur `evenements.py` — pas ici (#72).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_note_flash.py"
NF="app/agents/v2/note_flash.py"
SC="app/contracts/note_flash_schema.py"
mutations=(
# §1/§2 — le contrat, le type dérivé
"$SC¦            if self.cause is None:¦            if False:¦une surprise SANS cause est refusée"
"$SC¦    return \"surprise_\" + (\"concurrence\" if element.cause == \"non_dite\" else element.cause)¦    return \"surprise_\" + element.cause¦cause non dite ⟹ \`surprise_concurrence\`"
# §3 — ce qu'on lit
"$NF¦_TYPES_LUS = re.compile(r\"^(8-K|8-K/A|6-K|6-K/A|EX-99(\\.\\d+)?)\$\")¦_TYPES_LUS = re.compile(r\"^(8-K|8-K/A|6-K|6-K/A|EX-99(\\.\\d+)?|EX-5\\.1)\$\")¦l'avis juridique EX-5.1"
"$NF¦        brut = _EN_TETE_XBRL.sub(\" \", brut)¦        pass¦un 6-K (sans item) : l'en-tête XBRL masqué"
"$NF¦            texte = texte[debut.start():] if debut else texte¦            pass¦la page de garde du formulaire"
# §4 — ce que le modèle voit
"$NF¦    out = [{\"id\": t.id, \"libelle\": t.libelle} for t in fichier.types_evenement¦    out = [{\"id\": t.id, \"libelle\": t.libelle, \"portee\": t.portee} for t in fichier.types_evenement¦le modèle ne voit NI la portée"
"$NF¦           if t.id != A_QUALIFIER and not t.id.startswith(\"surprise_\")]¦           if not t.id.startswith(\"surprise_\")]¦catalogue proposé"
# §5 — le pont
"$NF¦            if cite is not None and _normaliser(cite) not in corpus:¦            if False:¦une PARAPHRASE est refusée"
"$NF¦    return re.sub(r\"\\s+\", \" \", t).strip().casefold()¦    return t.strip().casefold()¦une citation littérale (espaces normalisés) passe"
"$NF¦    permis = {t[\"id\"] for t in types_proposables(fichier)}¦    permis = {t.id for t in fichier.types_evenement}¦\`a_qualifier\` n'est pas un type"
"$NF¦    types = tuple(sorted({type_derive(el) for el in sortie.elements}))¦    types = tuple(sorted({el.type for el in sortie.elements}))¦les types retenus sont ceux que le CODE dérive"
# §6 — quels dépôts lire
"$NF¦            and (e.accession not in qualifications or qualifications[e.accession].a_relire)¦            and True¦un dépôt déjà lu"
"$NF¦            if e.event_date >= depuis and e.accession¦            if e.accession¦depuis la date"
"$NF¦            and (e.accession not in qualifications or qualifications[e.accession].a_relire)¦            and e.accession not in qualifications¦une note écrite sous une AUTRE version du catalogue est relue"
"$NF¦    a_relire = version != fichier.types_evenement_version¦    a_relire = False¦une note d'une ancienne version COMPTE encore"
"$NF¦                       catalogue_version=fichier.types_evenement_version, note=note,¦                       catalogue_version=fichier.schema_version, note=note,¦une lecture juste : 1 appel"
# §7 — la relecture
"$NF¦    if not types <= connus:¦    if False:¦un type que le référentiel ne connaît plus"
# §8 — la rédaction
"$NF¦    for essai in (1, 2):¦    for essai in (2,):¦renvoyée UNE fois"
"$NF¦    if not documents:¦    if False:¦AVANT tout appel modèle"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
