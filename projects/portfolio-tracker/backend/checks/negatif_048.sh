#!/usr/bin/env bash
# TEST NÉGATIF de la migration 048 (registre du comité) — éprouvé AVANT application, sur une COPIE de
# `db_portfolio`.
#
#   bash checks/negatif_048.sh
#
# SATISFIABILITÉ : la 048 non mutée passe sur la copie du réel, et le rôle APPLICATIF y inscrit une
# acceptation (sur une vraie réponse courante) et un renvoi (sur un vrai mandat).
# DISCRIMINATION : chaque CHECK refuse sa forme interdite PAR SON NOM (un refus prononcé par une autre
# contrainte est un faux vert — cf. #83, PostgreSQL teste les CHECK par ordre alphabétique) ; le rôle
# applicatif ne peut ni modifier ni supprimer une décision ; le trigger refuse même au propriétaire ;
# [K1] une 048 privée de son REVOKE doit LEVER nommément.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`, jamais un
# heredoc via `docker exec` (il échoue en silence).
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_048_neg
SQL=app/db/migrations/048_v2_registre_du_comite.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/048.sql" >/dev/null
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }

# refuse <contrainte ou motif attendu> <label> <sql> — exécuté par le rôle APPLICATIF.
refuse() {
  local attendu=$1 label=$2 sql=$3 out
  if out=$(app -c "$sql" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | head -1)"; fi
}

echo "── [sat] la 048 non mutée, sur la copie du réel"
fixture
if ! out=$(q -f /tmp/048.sql 2>&1); then
  fail "satisfiabilité — la 048 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $((ko)) FAIL ==="; exit 1
fi
REP=$(q -c "SELECT id||'|'||ticker_id||'|'||framework||'|'||framework_version||'|'||question_id FROM framework_answers WHERE superseded_by IS NULL ORDER BY id LIMIT 1")
MANDAT=$(q -c "SELECT id FROM framework_mandates ORDER BY id LIMIT 1")
[ -n "$REP" ] && [ -n "$MANDAT" ] || { echo "ERREUR : aucune réponse / aucun mandat réel — vraie par dégénérescence"; exit 2; }
IFS='|' read -r AID TK FW FV QID <<<"$REP"
BASE="INSERT INTO comite_decisions (ticker_id, framework_id, framework_version, question_id, action, answer_id, mandat_id, auteur, motif, ancre_etat, fait_connu_publie_le, fait_connu_resume) VALUES ('$TK','$FW','$FV','$QID'"
if app -c "$BASE,'acquitter',$AID,NULL,'membre','on décide sans la marge des pairs','found','2026-08-26','8-K du 2026-08-26')" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit une ACCEPTATION sur la réponse courante #$AID ($TK · $QID)"
else fail "le rôle applicatif n'inscrit pas une acceptation valide"; fi
if app -c "$BASE,'renvoyer',NULL,$MANDAT,'membre','la marge citée date de 2024','none',NULL,NULL)" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit un RENVOI (mandat réel #$MANDAT, aucun fait important connu)"
else fail "le rôle applicatif n'inscrit pas un renvoi valide"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse comite_decisions_forme "acquitter SANS réponse (la version du dossier lue) est refusé" \
  "$BASE,'acquitter',NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_forme "acquitter avec des faits importants ILLISIBLES est refusé" \
  "$BASE,'acquitter',$AID,NULL,'membre','motif','unavailable',NULL,NULL)"
refuse comite_decisions_forme "renvoyer SANS mandat (Écart B) est refusé" \
  "$BASE,'renvoyer',NULL,NULL,'membre','motif','none',NULL,NULL)"
refuse comite_decisions_texte "une justification BLANCHE est refusée (arbitrage n°1)" \
  "$BASE,'acquitter',$AID,NULL,'membre','   ','none',NULL,NULL)"
refuse comite_decisions_texte "un PV non SIGNÉ est refusé" \
  "$BASE,'acquitter',$AID,NULL,'','motif','none',NULL,NULL)"
refuse comite_decisions_ancre "une ancre « trouvée » sans fait cité est refusée (#49)" \
  "$BASE,'acquitter',$AID,NULL,'membre','motif','found',NULL,NULL)"
refuse comite_decisions_ancre "un fait cité sous une ancre « aucun fait » est refusé (#49)" \
  "$BASE,'acquitter',$AID,NULL,'membre','motif','none','2026-08-26','8-K')"
refuse comite_decisions_action "une action hors vocabulaire est refusée" \
  "$BASE,'dispenser',$AID,NULL,'membre','motif','none',NULL,NULL)"

echo "── [PV] un procès-verbal ne se réécrit pas"
refuse "permission denied" "le rôle applicatif ne MODIFIE pas une décision" \
  "UPDATE comite_decisions SET motif = 'réécrit'"
refuse "permission denied" "le rôle applicatif ne SUPPRIME pas une décision" \
  "DELETE FROM comite_decisions"
if out=$(q -c "UPDATE comite_decisions SET motif = 'réécrit'" 2>&1); then
  fail "le PROPRIÉTAIRE a réécrit une décision — le trigger ne garde rien"
elif printf '%s' "$out" | grep -q "procès-verbal"; then
  pass "même le propriétaire ne réécrit pas le PV (trigger nommé)"
else fail "réécriture refusée, mais pas par le trigger : $(printf '%s' "$out" | head -1)"; fi

echo "── [K1] une 048 privée de son REVOKE → 048/K1 doit lever"
fixture
docker exec "$PG" sh -c "sed 's/^REVOKE ALL ON public.comite_decisions FROM portfolio_user;/-- mutation: REVOKE retiré/' /tmp/048.sql > /tmp/048_mut.sql"
docker exec "$PG" grep -q '^-- mutation: REVOKE retiré' /tmp/048_mut.sql \
  || { echo "ERREUR : la mutation n'a rien remplacé"; exit 2; }
if out=$(q -f /tmp/048_mut.sql 2>&1); then
  fail "[K1] la 048 mutée est passée — les privilèges par défaut laissent réécrire le PV sans que la garde le voie"
elif printf '%s' "$out" | grep -q '048/K1'; then pass "[K1] rouge sur sa garde nommée"
else fail "[K1] a levé, mais pas sur 048/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
