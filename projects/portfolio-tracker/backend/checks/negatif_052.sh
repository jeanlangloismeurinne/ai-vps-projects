#!/usr/bin/env bash
# TEST NÉGATIF de la migration 052 (période d'une ligne de plan, #113) — sur une COPIE de `db_portfolio`.
#   bash checks/negatif_052.sh
# SATISFIABILITÉ : la 052 passe sur la copie du réel ; les lignes existantes restent sans période (NULL).
# DISCRIMINATION : la contrainte refuse une période hors vocabulaire et une période sur une ligne
# `inobtenable` ; elle accepte une période du vocabulaire sur une ligne `traduit` ; la garde K3 LÈVE
# quand une ligne antérieure porte déjà une période (on la prive de ce qu'elle garde).
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_052_neg
SQL=app/db/migrations/052_v3_periode_ligne_de_plan.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q() { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }
refuse() {
  local attendu=$1 label=$2; shift 2; local out
  if out=$("$@" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | grep -m1 ERROR)"; fi
}
docker cp "$SQL" "$PG:/tmp/052.sql" >/dev/null

echo "── [sat] la 052 non mutée, sur la copie du réel"
fixture
N=$(q -c "SELECT count(*) FROM collection_plan_items")
if ! out=$(q -f /tmp/052.sql 2>&1); then fail "la 052 lève sur le réel : $(printf '%s' "$out" | tail -1)"
else pass "la 052 s'applique sur la copie du réel"; fi
[ "$(q -c "SELECT count(*) FROM collection_plan_items WHERE periode IS NULL")" = "$N" ] \
  && pass "les $N lignes antérieures restent sans période" || fail "une ligne antérieure a reçu une période"
T=$(q -c "SELECT id FROM collection_plan_items WHERE statut='traduit' LIMIT 1")
I=$(q -c "SELECT id FROM collection_plan_items WHERE statut='inobtenable' LIMIT 1")
q -c "UPDATE collection_plan_items SET periode='douze_mois_glissants' WHERE id=$T" >/dev/null 2>&1 \
  && pass "une ligne traduite accepte une période du vocabulaire" || fail "période du vocabulaire refusée"
refuse collection_plan_items_periode "période hors vocabulaire refusée" \
  q -c "UPDATE collection_plan_items SET periode='trimestre' WHERE id=$T"
refuse collection_plan_items_periode "période sur une ligne inobtenable refusée" \
  q -c "UPDATE collection_plan_items SET periode='exercice_clos' WHERE id=$I"

echo "── [K3] une ligne antérieure qui porte déjà une période fait LEVER la garde"
fixture
q -c "ALTER TABLE collection_plan_items ADD COLUMN periode TEXT NULL" >/dev/null
q -c "UPDATE collection_plan_items SET periode='exercice_clos' WHERE id=(SELECT min(id) FROM collection_plan_items WHERE statut='traduit')" >/dev/null
sed 's/^ALTER TABLE public.collection_plan_items ADD COLUMN periode TEXT NULL;//' "$SQL" > /tmp/052_k3.sql
docker cp /tmp/052_k3.sql "$PG:/tmp/052_k3.sql" >/dev/null
refuse "052/K3" "K3 lève sur une période préexistante" q -f /tmp/052_k3.sql

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo; echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
