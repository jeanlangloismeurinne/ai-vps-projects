#!/usr/bin/env bash
# TEST NÉGATIF de la migration 060 (RÉTABLIR au PV du comité, point 13) — éprouvé AVANT application,
# sur une COPIE de `db_portfolio`. S'inspire de `negatif_058.sh`.
#
#   bash checks/negatif_060.sh
#
# SATISFIABILITÉ : la 060 non mutée passe sur la copie du réel ; le rôle APPLICATIF y inscrit un
# `retablir` complet (answer_id + retablie_depuis_id, sans mandat) et les trois gestes antérieurs
# (acquitter/renvoyer/reinitialiser) restent inscriptibles, TOUJOURS sans `retablie_depuis_id`.
# DISCRIMINATION : un `retablir` sans `retablie_depuis_id`, ou qui porterait un `mandat_id`, est
# refusé PAR `comite_decisions_forme` (un refus d'une autre contrainte est un faux vert, #83) ; une
# AUTRE action qui porterait `retablie_depuis_id` aussi ; une action hors vocabulaire par
# `comite_decisions_action` ; le PV ne se réécrit toujours pas ; [K1] une 060 qui rouvrirait l'UPDATE
# au rôle applicatif doit LEVER nommément.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_060_neg
SQL=app/db/migrations/060_v2_retablir_comite.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/060.sql" >/dev/null
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }

refuse() {
  local attendu=$1 label=$2 sql=$3 out
  if out=$(app -c "$sql" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | head -1)"; fi
}

echo "── [témoin] AVANT la 060, un rétablissement est refusé (la mesure part du réel)"
fixture
REP=$(q -c "SELECT id||'|'||ticker_id||'|'||framework||'|'||framework_version||'|'||question_id FROM framework_answers WHERE superseded_by IS NULL ORDER BY id LIMIT 1")
PREC=$(q -c "SELECT id FROM framework_answers WHERE superseded_by IS NOT NULL ORDER BY id LIMIT 1")
MANDAT=$(q -c "SELECT id FROM framework_mandates ORDER BY id LIMIT 1")
[ -n "$REP" ] && [ -n "$PREC" ] && [ -n "$MANDAT" ] || { echo "ERREUR : fixture insuffisante — vraie par dégénérescence"; exit 2; }
IFS='|' read -r AID TK FW FV QID <<<"$REP"
# AVANT la 060 : la colonne `retablie_depuis_id` n'existe pas encore — le témoin utilise le schéma
# de la 058 (sans elle), sinon l'INSERT échouerait sur « colonne inconnue », pas sur le vocabulaire.
BASE_AVANT="INSERT INTO comite_decisions (ticker_id, framework_id, framework_version, question_id, action, answer_id, mandat_id, auteur, motif, ancre_etat, fait_connu_publie_le, fait_connu_resume) VALUES ('$TK','$FW','$FV','$QID'"
refuse comite_decisions_action "sans la 060, \`retablir\` est hors vocabulaire (témoin)" \
  "$BASE_AVANT,'retablir',$AID,NULL,'comité','rétablissement (#1475)','none',NULL,NULL)"

echo "── [sat] la 060 non mutée, sur la copie du réel"
if ! out=$(q -f /tmp/060.sql 2>&1); then
  fail "satisfiabilité — la 060 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $ko FAIL ==="; exit 1
fi
# APRÈS la 060 : `retablie_depuis_id` existe — tous les tests suivants la portent.
BASE="INSERT INTO comite_decisions (ticker_id, framework_id, framework_version, question_id, action, answer_id, mandat_id, retablie_depuis_id, auteur, motif, ancre_etat, fait_connu_publie_le, fait_connu_resume) VALUES ('$TK','$FW','$FV','$QID'"
if app -c "$BASE,'retablir',$AID,NULL,$PREC,'comité','rétablissement (#$PREC, point 13)','none',NULL,NULL)" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit un RÉTABLISSEMENT (copie #$AID, précédente #$PREC)"
else fail "le rôle applicatif n'inscrit pas un rétablissement valide"; fi
if app -c "$BASE,'acquitter',$AID,NULL,NULL,'membre','on décide sans la marge des pairs','none',NULL,NULL)" >/dev/null 2>&1 \
   && app -c "$BASE,'renvoyer',NULL,$MANDAT,NULL,'membre','la marge citée date de 2024','none',NULL,NULL)" >/dev/null 2>&1 \
   && app -c "$BASE,'reinitialiser',$AID,NULL,NULL,'gérant','reconstruction du test','none',NULL,NULL)" >/dev/null 2>&1; then
  pass "les trois gestes antérieurs (acquitter, renvoyer, reinitialiser) restent inscriptibles"
else fail "la 060 a cassé un geste antérieur"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse comite_decisions_forme "un retablir SANS retablie_depuis_id est refusé" \
  "$BASE,'retablir',$AID,NULL,NULL,'comité','motif','none',NULL,NULL)"
refuse comite_decisions_forme "un retablir qui porterait un MANDAT est refusé" \
  "$BASE,'retablir',$AID,$MANDAT,$PREC,'comité','motif','none',NULL,NULL)"
refuse comite_decisions_forme "un retablir SANS answer_id (la copie) est refusé" \
  "$BASE,'retablir',NULL,NULL,$PREC,'comité','motif','none',NULL,NULL)"
refuse comite_decisions_forme "acquitter qui porterait un retablie_depuis_id reste refusé" \
  "$BASE,'acquitter',$AID,NULL,$PREC,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_forme "reinitialiser qui porterait un retablie_depuis_id reste refusé" \
  "$BASE,'reinitialiser',$AID,NULL,$PREC,'gérant','motif','none',NULL,NULL)"
refuse comite_decisions_forme "acquitter SANS réponse reste refusé" \
  "$BASE,'acquitter',NULL,NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_forme "renvoyer SANS mandat reste refusé (Écart B)" \
  "$BASE,'renvoyer',NULL,NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_texte "un retablir non MOTIVÉ est refusé" \
  "$BASE,'retablir',$AID,NULL,$PREC,'comité','  ','none',NULL,NULL)"
refuse comite_decisions_action "une action hors vocabulaire reste refusée" \
  "$BASE,'dispenser',$AID,NULL,NULL,'membre','motif','none',NULL,NULL)"

echo "── [PV] un procès-verbal ne se réécrit toujours pas"
refuse "permission denied" "le rôle applicatif ne MODIFIE pas un rétablissement" \
  "UPDATE comite_decisions SET motif = 'réécrit' WHERE action = 'retablir'"
refuse "permission denied" "le rôle applicatif ne SUPPRIME pas un rétablissement" \
  "DELETE FROM comite_decisions WHERE action = 'retablir'"

echo "── [K1] une 060 qui rouvrirait l'UPDATE au rôle applicatif → 060/K1 doit lever"
fixture
docker exec "$PG" sh -c "sed 's/^BEGIN;/BEGIN;\nGRANT UPDATE ON public.comite_decisions TO portfolio_user; -- mutation/' /tmp/060.sql > /tmp/060_mut.sql"
docker exec "$PG" grep -q -- '-- mutation' /tmp/060_mut.sql \
  || { echo "ERREUR : la mutation n'a rien inséré"; exit 2; }
if out=$(q -f /tmp/060_mut.sql 2>&1); then
  fail "[K1] la 060 mutée est passée — un PV réécrivable n'est pas vu"
elif printf '%s' "$out" | grep -q '060/K1'; then pass "[K1] rouge sur sa garde nommée"
else fail "[K1] a levé, mais pas sur 060/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
