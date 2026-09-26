#!/usr/bin/env bash
# TEST NÉGATIF de `check_note_flash_persist.py` — contre la VRAIE base, chaque passage en ROLLBACK.
#
#   bash checks/negatif_note_flash_persist.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_note_flash_persist.py"
NET=coolify
CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
NF="app/agents/v2/note_flash.py"
mutations=(
"$NF¦         WHERE cik = \$1¦         WHERE \$1::int IS NOT NULL¦aucune note n'est prêtée à un autre émetteur"
"$NF¦         ORDER BY accession, (catalogue_version = \$2) DESC, redigee_le DESC, id DESC¦         ORDER BY accession, redigee_le DESC, id DESC, (catalogue_version = \$2) DESC¦la note de la version COURANTE est servie"
"$NF¦    if not row[\"lisible\"]:¦    if False:¦la note illisible se relit"
"$NF¦        n.elements, n.motif, redigee.documents, redigee.modele)¦        __import__('json').dumps(n.elements), n.motif, redigee.documents, redigee.modele)¦éléments et documents en OBJETS JSON"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
