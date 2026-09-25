#!/usr/bin/env bash
# TEST NÉGATIF de la migration 047 — éprouvé AVANT application, sur une COPIE de `db_portfolio`.
#
#   bash checks/negatif_047.sh
#
# SATISFIABILITÉ : la 047 non mutée passe sur la copie du réel, et chaque mandat de collecte y
# reçoit une cause (aucun NULL), dans la répartition annoncée par l'en-tête de la migration.
# DISCRIMINATION : [K1] on injecte un mandat au préfixe inconnu du producteur → la reprise ne le
# classe pas → `047/K1` doit LEVER, nommément. [CHK] après la 047, un échec sans cause est refusé.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`, jamais un
# heredoc via `docker exec` (il échoue en silence).
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_047_neg
SQL=app/db/migrations/047_v2_cause_du_manque.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q() { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/047.sql" >/dev/null
ok=0; ko=0

echo "── [sat] la 047 non mutée, sur la copie du réel"
fixture
n_coll=$(q -c "SELECT count(*) FROM framework_mandates WHERE origine IN ('inobtenable','echec_collecte')")
[ "${n_coll:-0}" -gt 0 ] || { echo "ERREUR : 0 mandat de collecte — vraie par dégénérescence"; exit 2; }
if out=$(q -f /tmp/047.sql 2>&1); then
  repart=$(q -c "SELECT string_agg(cause||'='||n, ' ' ORDER BY cause) FROM (SELECT cause, count(*) n FROM framework_mandates WHERE origine IN ('inobtenable','echec_collecte') GROUP BY cause) t")
  nulls=$(q -c "SELECT count(*) FROM framework_mandates WHERE origine IN ('inobtenable','echec_collecte') AND cause IS NULL")
  if [ "$nulls" = "0" ]; then echo "  ok   satisfiabilité · $n_coll mandats de collecte · $repart"; ok=$((ok+1))
  else echo "  FAIL satisfiabilité · $nulls sans cause"; ko=$((ko+1)); fi
  echo "── [CHK] après la 047, un échec de collecte sans cause est refusé"
  if q -c "INSERT INTO framework_mandates (framework_id, framework_version, question_id, ingredient_id, motif, origine) VALUES ('f','v','q','x','m','echec_collecte')" >/dev/null 2>&1; then
    echo "  FAIL [CHK] insertion acceptée"; ko=$((ko+1))
  else echo "  ok   [CHK] framework_mandates_cause refuse l'échec sans cause"; ok=$((ok+1)); fi
else
  echo "  FAIL satisfiabilité — la 047 lève sur le réel :"; printf '%s\n' "$out" | tail -3; ko=$((ko+1))
fi

echo "── [K1] un motif au préfixe inconnu du producteur → 047/K1 doit lever"
fixture
q -c "INSERT INTO framework_mandates (framework_id, framework_version, question_id, ingredient_id, motif, origine) VALUES ('f','v','q','x','un motif que nul producteur n''écrit','echec_collecte')" >/dev/null
if out=$(q -f /tmp/047.sql 2>&1); then
  echo "  FAIL [K1] la 047 est passée — la garde ne garde rien"; ko=$((ko+1))
elif printf '%s' "$out" | grep -q '047/K1'; then
  echo "  ok   [K1] rouge sur sa garde nommée"; ok=$((ok+1))
else
  echo "  FAIL [K1] rouge, mais pas sur 047/K1 :"; printf '%s\n' "$out" | tail -2; ko=$((ko+1))
fi
psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;"
echo "$ok ok / $ko FAIL"
[ "$ko" -eq 0 ]
