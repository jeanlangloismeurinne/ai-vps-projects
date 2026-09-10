#!/usr/bin/env bash
# Produit `036_v2_archive_devocabularisation.sql` à partir de TROIS instantanés de la base.
#
#   bash app/db/migrations/_gen_036.sh
#
# POURQUOI DES INSTANTANÉS PLUTÔT QU'UNE CONNEXION. Même motif que `_gen_035.sh` : un générateur
# qui parle à la base n'est pas rejouable, et son entrée n'est pas citable dans la revue. Ici
# l'entrée est en plus la seule chose qui empêche de RÉÉCRIRE le DDL à la main — et un DDL réécrit
# à la main est un jumeau de la table qu'il prétend recréer (#46). `pg_dump --schema-only` EST le
# détenteur : il rend les noms d'index, de contraintes et de séquences à l'identique.
#
# ⚠️ Les trois instantanés sont load-bearing et leur absence sort en ERREUR, jamais en saut de
# section (`feedback_check_degrade_en_sortant_a_zero`).
set -euo pipefail
cd "$(dirname "$0")/../../.." || exit 1

PG=shared-postgres
DB=db_portfolio
OUT=/tmp/gen_036
mkdir -p "$OUT"

# La liste des tables est DÉRIVÉE (`grappe_v2()`, une table V2 = une table créée par une migration
# `*_v2_*.sql`), jamais recopiée ici : ce shell ne fait que la traduire en options `-t`.
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
TABLES=$(docker run --rm --network none -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app "$IMG" \
         python -c "from tools.inventaire_grappe_v2 import grappe_v2; print(' '.join(grappe_v2()[0]))")
echo "grappe dérivée : $TABLES" >&2

OPTS=""
for t in $TABLES; do OPTS="$OPTS -t public.$t"; done

# ── 1. le DDL des 15 tables, noms préservés ───────────────────────────────────────────────────
# shellcheck disable=SC2086
docker exec "$PG" pg_dump -U admin -d "$DB" --schema-only --no-owner --no-acl --no-comments \
  $OPTS > "$OUT/ddl.sql"

# ── 2. les arêtes FK ENTRANTES (hors-grappe → grappe) : les seules que l'archivage casse ──────
docker exec "$PG" psql -U admin -d "$DB" -tAF'|' -c "
WITH grappe AS (SELECT unnest(string_to_array('$(echo "$TABLES" | tr ' ' ',')', ',')) AS t)
SELECT c.conrelid::regclass::text, a.attname, c.conname, c.confrelid::regclass::text
  FROM pg_constraint c
  JOIN unnest(c.conkey) WITH ORDINALITY k(attnum, ord) ON TRUE
  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
 WHERE c.contype = 'f'
   AND c.confrelid::regclass::text IN (SELECT t FROM grappe)
   AND c.conrelid::regclass::text NOT IN (SELECT t FROM grappe)
 ORDER BY 1, 2" > "$OUT/fk_entrantes.txt"

# ── 3. les VUES adossées à la grappe — une vue suit la table par OID, PAS par schéma ─────────
# Mesuré le 2026-09-10 sur une base sonde : après `SET SCHEMA`, `public.vv` rendait encore la
# ligne de `arc.t` (v=7) pendant que `public.t` neuve en portait une autre (v=99). La vue répond,
# sur un corpus gelé pour toujours. §3 de l'inventaire ne le voyait pas : ce n'est pas une FK.
docker exec "$PG" psql -U admin -d "$DB" -tA -c "
SELECT DISTINCT v.relname || E'\t' || replace(pg_get_viewdef(v.oid, true), E'\n', ' ')
  FROM pg_depend d
  JOIN pg_rewrite r ON r.oid = d.objid
  JOIN pg_class v ON v.oid = r.ev_class
  JOIN pg_class t ON t.oid = d.refobjid
 WHERE d.classid = 'pg_rewrite'::regclass AND d.refclassid = 'pg_class'::regclass
   AND v.relkind = 'v' AND t.relkind = 'r' AND v.relname <> t.relname
   AND t.relname = ANY(string_to_array('$(echo "$TABLES" | tr ' ' ',')', ','))
 ORDER BY 1" > "$OUT/vues.txt"

wc -l "$OUT"/*.sql "$OUT"/*.txt >&2

# ⚠️ Écriture ATOMIQUE, via un temporaire. Le générateur écrit sur `sys.stdout` au fil de l'eau :
# une redirection directe laisserait, sur échec, une migration TRONQUÉE au dernier `out()` réussi.
# Ce n'est pas théorique — c'est arrivé le 2026-09-10, et le fichier partiel portait un
# `CREATE TABLE archive_v2.liens_entrants` que `grappe_v2()` relisait au run suivant : le
# générateur se donnait sa propre sortie en entrée. Sur échec, la migration précédente reste.
docker run --rm --network none -v "$PWD:/app:ro" -v "$OUT:/snap:ro" -w /app -e PYTHONPATH=/app \
  "$IMG" python app/db/migrations/_gen_036.py \
    --ddl /snap/ddl.sql --fk /snap/fk_entrantes.txt --vues /snap/vues.txt \
  > "$OUT/036.sql"

mv "$OUT/036.sql" app/db/migrations/036_v2_archive_devocabularisation.sql
wc -l app/db/migrations/036_v2_archive_devocabularisation.sql >&2
