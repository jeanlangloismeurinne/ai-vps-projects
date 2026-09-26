#!/usr/bin/env bash
# TEST NÉGATIF de la migration 050 (les notes flash) — éprouvé AVANT application, sur une COPIE de
# `db_portfolio`.
#
#   bash checks/negatif_050.sh
#
# SATISFIABILITÉ : la 050 non mutée passe sur la copie du réel ; le rôle applicatif ÉCRIT une note
# lisible et une note illisible, et les RELIT.
# DISCRIMINATION : le rôle applicatif ne réécrit ni n'efface ; le trigger refuse la réécriture même au
# propriétaire ; une seconde note du même dépôt sous la même version est refusée ; chaque forme
# interdite est refusée par SA contrainte (nommée) ; la garde K1 lève quand on lui ouvre l'UPDATE.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_050_neg
SQL=app/db/migrations/050_v3_notes_flash.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
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

COLS="ticker_id, cik, accession, form, items, event_date, filing_date, catalogue_version, lisible, types, elements, motif, documents, modele"
DOCS="'[{\"type\":\"8-K\",\"nom\":\"rvmd-20260826.htm\"}]'"
LISIBLE="'RVMD', 1628171, 'acc-1', '8-K', '{8.01}', '2026-08-26', '2026-08-26', '1.0.0', true, '{reglementaire_favorable}', '[{\"type\":\"reglementaire_favorable\",\"passage\":\"the FDA approved RASONQUE\"}]', NULL, $DOCS, 'm'"
ILLISIBLE="'RVMD', 1628171, 'acc-2', '8-K', '{8.01}', '2026-04-13', '2026-04-13', '1.0.0', false, '{a_qualifier}', '[]', 'page de signature seule', $DOCS, 'm'"

echo "── [sat] la 050 non mutée, sur la copie du réel"
fixture
docker cp "$SQL" "$PG:/tmp/050.sql" >/dev/null
if ! out=$(q -f /tmp/050.sql 2>&1); then
  fail "satisfiabilité — la 050 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $ko FAIL ==="; exit 1
fi
pass "la 050 s'applique sur la copie du réel"
app -c "INSERT INTO notes_flash ($COLS) VALUES ($LISIBLE)" >/dev/null \
  && pass "le rôle applicatif ÉCRIT une note lisible" || fail "le rôle applicatif n'écrit pas une note lisible"
app -c "INSERT INTO notes_flash ($COLS) VALUES ($ILLISIBLE)" >/dev/null \
  && pass "le rôle applicatif ÉCRIT une note illisible (motivée)" || fail "note illisible refusée"
[ "$(app -c "SELECT count(*) FROM notes_flash")" = 2 ] \
  && pass "le rôle applicatif RELIT les notes" || fail "le rôle applicatif ne relit pas"
app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$LISIBLE" | sed "s/'1.0.0'/'1.1.0'/"))" >/dev/null \
  && pass "le même dépôt se RELIT sous une autre version du catalogue" || fail "relecture sous version neuve refusée"

echo "── [ACL] append-only"
refuse "permission denied" "le rôle applicatif ne réécrit pas une note (UPDATE)" \
  app -c "UPDATE notes_flash SET types = '{routine}'"
refuse "permission denied" "le rôle applicatif n'efface pas une note (DELETE)" \
  app -c "DELETE FROM notes_flash"
refuse "ne se réécrit ni ne se supprime" "le trigger refuse la réécriture même au propriétaire" \
  q -c "UPDATE notes_flash SET types = '{routine}'"
refuse "ne se réécrit ni ne se supprime" "le trigger refuse l'effacement même au propriétaire" \
  q -c "DELETE FROM notes_flash"

echo "── [forme] chaque forme interdite est refusée par SA contrainte"
refuse "notes_flash_une_lecture" "une seconde note du même dépôt sous la même version" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($LISIBLE)"
refuse "notes_flash_forme" "une note lisible qui garde « à qualifier »" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$LISIBLE" | sed "s/acc-1/acc-3/; s/{reglementaire_favorable}/{reglementaire_favorable,a_qualifier}/"))"
refuse "notes_flash_forme" "une note lisible sans élément cité" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$LISIBLE" | sed "s/acc-1/acc-4/; s/'\[{[^]]*}\]'/'[]'/"))"
refuse "notes_flash_forme" "une note illisible sans motif" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$ILLISIBLE" | sed "s/acc-2/acc-5/; s/'page de signature seule'/'  '/"))"
refuse "notes_flash_forme" "une note illisible qui range quand même le dépôt" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$ILLISIBLE" | sed "s/acc-2/acc-6/; s/{a_qualifier}/{routine}/"))"
refuse "notes_flash_documents" "une note sans document lu" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$LISIBLE" | sed "s/acc-1/acc-7/; s/'\[{\"type\":\"8-K\"[^]]*\]'/'[]'/"))"
refuse "notes_flash_ticker_id_fkey" "une note sur un titre inconnu" \
  app -c "INSERT INTO notes_flash ($COLS) VALUES ($(printf '%s' "$LISIBLE" | sed "s/acc-1/acc-8/; s/'RVMD'/'ZZZZ-INCONNU'/"))"

echo "── [K] la garde lève nommément"
fixture
python3 -c "import sys; s=open('$SQL').read(); o='GRANT SELECT, INSERT ON public.notes_flash TO portfolio_user;'; assert o in s; s=s.replace(o, 'GRANT SELECT, INSERT, UPDATE ON public.notes_flash TO portfolio_user;'); open('/tmp/050_mut.sql','w').write(s)" \
  || fail "mutation K1 non appliquée"
docker cp /tmp/050_mut.sql "$PG:/tmp/050_mut.sql" >/dev/null
refuse "050/K1" "050/K1 : une 050 qui ouvre l'UPDATE au rôle applicatif lève" q -f /tmp/050_mut.sql
fixture
python3 -c "import sys; s=open('$SQL').read(); o='GRANT SELECT, INSERT ON public.notes_flash TO portfolio_user;'; assert o in s; s=s.replace(o, 'GRANT SELECT ON public.notes_flash TO portfolio_user;'); open('/tmp/050_mut.sql','w').write(s)" \
  || fail "mutation K1 non appliquée"
docker cp /tmp/050_mut.sql "$PG:/tmp/050_mut.sql" >/dev/null
refuse "050/K1" "050/K1 : une 050 qui retire l'INSERT au rôle applicatif lève" q -f /tmp/050_mut.sql

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo; echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
