#!/usr/bin/env bash
# TEST NÉGATIF de la migration 059 (le classement de l'émetteur devient une décision du comité, #139) —
# éprouvé AVANT application, sur une COPIE de `db_portfolio`.
#
#   bash checks/negatif_059.sh
#
# SATISFIABILITÉ : la 059 passe sur la copie du réel ; les trois classements d'origine restent lisibles ;
# le rôle APPLICATIF inscrit une décision complète (pièce + auteur + dépôt) et un classement de la forme
# d'origine (rien des trois).
# DISCRIMINATION : chaque mélange est refusé PAR `ticker_archetypes_decision` (un refus d'une autre
# contrainte est un faux vert, #83) ; une pièce inexistante par la clé étrangère.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_059_neg
SQL=app/db/migrations/059_v2_classement_par_le_comite.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
docker cp "$SQL" "$PG:/tmp/059.sql" >/dev/null
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }
refuse() {
  local attendu=$1 label=$2 sql=$3 out
  if out=$(app -c "$sql" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | head -1)"; fi
}

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
  || { echo "ERREUR : restauration"; exit 2; }
PIECE=$(q -c "SELECT id FROM knowledge_entries WHERE ticker_id = 'RVMD' AND superseded_by IS NULL ORDER BY id LIMIT 1")
N0=$(q -c "SELECT count(*) FROM ticker_archetypes")
[ -n "$PIECE" ] && [ "${N0:-0}" -ge 1 ] || { echo "ERREUR : aucune pièce / aucun classement réel — vraie par dégénérescence"; exit 2; }
INS="INSERT INTO ticker_archetypes (ticker_id, archetype, effective_from, motif, piece_id, auteur, declencheur_accession) VALUES ('RVMD','rentable'"

echo "── [témoin] AVANT la 059, une décision avec pièce est impossible (la mesure part du réel)"
refuse "piece_id" "sans la 059, la colonne de la pièce n'existe pas (témoin)" \
  "$INS,'2026-10-18','reclassée',$PIECE,'gérant','0001193125-26-366931')"

echo "── [sat] la 059, sur la copie du réel"
if ! out=$(q -f /tmp/059.sql 2>&1); then
  fail "satisfiabilité — la 059 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $ko FAIL ==="; exit 1
fi
N1=$(q -c "SELECT count(*) FROM ticker_archetypes WHERE piece_id IS NULL AND auteur IS NULL AND declencheur_accession IS NULL")
[ "$N1" = "$N0" ] && pass "les $N0 classements d'origine restent tels quels (sans pièce ni auteur)" \
  || fail "classements d'origine altérés ($N1 / $N0)"
if app -c "$INS,'2026-10-18','reclassée au vu de l''approbation',$PIECE,'gérant','0001193125-26-366931')" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit une DÉCISION complète (pièce #$PIECE, auteur, dépôt)"
else fail "le rôle applicatif n'inscrit pas une décision complète"; fi
if app -c "$INS,'2026-10-19','forme d''origine',NULL,NULL,NULL)" >/dev/null 2>&1; then
  pass "… et un classement de la forme d'origine (rien des trois)"
else fail "un classement de la forme d'origine est refusé"; fi

echo "── [CHK] chaque mélange est refusé par SA contrainte"
refuse ticker_archetypes_decision "une pièce SANS auteur est refusée" \
  "$INS,'2026-10-20','x',$PIECE,NULL,'0001193125-26-366931')"
refuse ticker_archetypes_decision "un auteur BLANC est refusé" \
  "$INS,'2026-10-21','x',$PIECE,'  ','0001193125-26-366931')"
refuse ticker_archetypes_decision "une décision SANS dépôt déclencheur est refusée" \
  "$INS,'2026-10-22','x',$PIECE,'gérant',NULL)"
refuse ticker_archetypes_decision "un auteur SANS pièce est refusé" \
  "$INS,'2026-10-23','x',NULL,'gérant','0001193125-26-366931')"
refuse ticker_archetypes_piece_id_fkey "une pièce inexistante est refusée par la clé étrangère" \
  "$INS,'2026-10-24','x',999999999,'gérant','0001193125-26-366931')"

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
