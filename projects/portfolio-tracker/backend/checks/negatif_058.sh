#!/usr/bin/env bash
# TEST NÉGATIF de la migration 058 (réinitialisation au PV du comité) — éprouvé AVANT application, sur
# une COPIE de `db_portfolio`.
#
#   bash checks/negatif_058.sh
#
# SATISFIABILITÉ : la 058 non mutée passe sur la copie du réel ; le rôle APPLICATIF y inscrit une
# réinitialisation avec et sans réponse relevée, et les deux gestes de la 048 restent inscriptibles.
# DISCRIMINATION : une réinitialisation qui porterait un mandat est refusée PAR `comite_decisions_forme`
# (un refus d'une autre contrainte est un faux vert, #83) ; une action hors vocabulaire par
# `comite_decisions_action` ; le PV ne se réécrit toujours pas ; [K1] une 058 qui rouvrirait l'UPDATE
# au rôle applicatif doit LEVER nommément.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_058_neg
SQL=app/db/migrations/058_v2_reinitialisation_comite.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/058.sql" >/dev/null
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }

refuse() {
  local attendu=$1 label=$2 sql=$3 out
  if out=$(app -c "$sql" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | head -1)"; fi
}

echo "── [témoin] AVANT la 058, une réinitialisation est refusée (la mesure part du réel)"
fixture
REP=$(q -c "SELECT id||'|'||ticker_id||'|'||framework||'|'||framework_version||'|'||question_id FROM framework_answers WHERE superseded_by IS NULL ORDER BY id LIMIT 1")
MANDAT=$(q -c "SELECT id FROM framework_mandates ORDER BY id LIMIT 1")
[ -n "$REP" ] && [ -n "$MANDAT" ] || { echo "ERREUR : aucune réponse / aucun mandat réel — vraie par dégénérescence"; exit 2; }
IFS='|' read -r AID TK FW FV QID <<<"$REP"
BASE="INSERT INTO comite_decisions (ticker_id, framework_id, framework_version, question_id, action, answer_id, mandat_id, auteur, motif, ancre_etat, fait_connu_publie_le, fait_connu_resume) VALUES ('$TK','$FW','$FV','$QID'"
refuse comite_decisions_action "sans la 058, \`reinitialiser\` est hors vocabulaire (témoin)" \
  "$BASE,'reinitialiser',$AID,NULL,'gérant','reconstruction du test','none',NULL,NULL)"

echo "── [sat] la 058 non mutée, sur la copie du réel"
if ! out=$(q -f /tmp/058.sql 2>&1); then
  fail "satisfiabilité — la 058 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $ko FAIL ==="; exit 1
fi
if app -c "$BASE,'reinitialiser',$AID,NULL,'gérant','reconstruction du test (#127)','none',NULL,NULL)" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit une RÉINITIALISATION relevant la réponse courante #$AID ($TK · $QID)"
else fail "le rôle applicatif n'inscrit pas une réinitialisation valide"; fi
if app -c "$BASE,'reinitialiser',NULL,NULL,'gérant','question jamais instruite','unavailable',NULL,NULL)" >/dev/null 2>&1; then
  pass "… et sans réponse, même EDGAR injoignable (rien ne doit « tomber » ensuite)"
else fail "une réinitialisation sans réponse est refusée"; fi
if app -c "$BASE,'acquitter',$AID,NULL,'membre','on décide sans la marge des pairs','none',NULL,NULL)" >/dev/null 2>&1 \
   && app -c "$BASE,'renvoyer',NULL,$MANDAT,'membre','la marge citée date de 2024','none',NULL,NULL)" >/dev/null 2>&1; then
  pass "les gestes de la 048 (acquitter, renvoyer) restent inscriptibles"
else fail "la 058 a cassé acquitter ou renvoyer"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse comite_decisions_forme "une réinitialisation qui porterait un MANDAT est refusée" \
  "$BASE,'reinitialiser',NULL,$MANDAT,'gérant','motif','none',NULL,NULL)"
refuse comite_decisions_forme "acquitter SANS réponse reste refusé" \
  "$BASE,'acquitter',NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_forme "renvoyer SANS mandat reste refusé (Écart B)" \
  "$BASE,'renvoyer',NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_texte "une réinitialisation non MOTIVÉE est refusée" \
  "$BASE,'reinitialiser',NULL,NULL,'gérant','  ','none',NULL,NULL)"
refuse comite_decisions_action "une action hors vocabulaire reste refusée" \
  "$BASE,'dispenser',$AID,NULL,'membre','motif','none',NULL,NULL)"

echo "── [PV] un procès-verbal ne se réécrit toujours pas"
refuse "permission denied" "le rôle applicatif ne MODIFIE pas une réinitialisation" \
  "UPDATE comite_decisions SET motif = 'réécrit' WHERE action = 'reinitialiser'"
refuse "permission denied" "le rôle applicatif ne SUPPRIME pas une réinitialisation" \
  "DELETE FROM comite_decisions WHERE action = 'reinitialiser'"

echo "── [K1] une 058 qui rouvrirait l'UPDATE au rôle applicatif → 058/K1 doit lever"
fixture
docker exec "$PG" sh -c "sed 's/^BEGIN;/BEGIN;\nGRANT UPDATE ON public.comite_decisions TO portfolio_user; -- mutation/' /tmp/058.sql > /tmp/058_mut.sql"
docker exec "$PG" grep -q -- '-- mutation' /tmp/058_mut.sql \
  || { echo "ERREUR : la mutation n'a rien inséré"; exit 2; }
if out=$(q -f /tmp/058_mut.sql 2>&1); then
  fail "[K1] la 058 mutée est passée — un PV réécrivable n'est pas vu"
elif printf '%s' "$out" | grep -q '058/K1'; then pass "[K1] rouge sur sa garde nommée"
else fail "[K1] a levé, mais pas sur 058/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
