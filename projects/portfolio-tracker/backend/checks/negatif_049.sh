#!/usr/bin/env bash
# TEST NÉGATIF de la migration 049 (registre des pièces écartées) — éprouvé AVANT application, sur une
# COPIE de `db_portfolio`.
#
#   bash checks/negatif_049.sh
#
# SATISFIABILITÉ : la 049 non mutée passe sur la copie du réel ; les 5 pièces Ryvu quittent le dossier
# RVMD, arrivent au registre ENTIÈRES (contenu identique octet pour octet) avec leurs 2 rattachements ;
# la #664 (juste) reste ; le reste du corpus RVMD est intact.
# DISCRIMINATION : le rôle applicatif ne peut rien écrire au registre ; le trigger refuse la réécriture
# même au propriétaire ; chaque garde (K1, K2, K3) LÈVE nommément quand on la prive de ce qu'elle garde.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_049_neg
SQL=app/db/migrations/049_v3_pieces_ecartees.sql
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
IDS="665,666,667,671,672"

# refuse <motif attendu> <label> <commande…>
refuse() {
  local attendu=$1 label=$2; shift 2; local out
  if out=$("$@" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | grep -m1 ERROR)"; fi
}

echo "── [sat] la 049 non mutée, sur la copie du réel"
fixture
AVANT_HASH=$(q -c "SELECT md5(string_agg(content, '|' ORDER BY id)) FROM knowledge_entries WHERE id IN ($IDS)")
AVANT_RVMD=$(q -c "SELECT count(*) FROM knowledge_entries WHERE ticker_id='RVMD'")
docker cp "$SQL" "$PG:/tmp/049.sql" >/dev/null
if ! out=$(q -f /tmp/049.sql 2>&1); then
  fail "satisfiabilité — la 049 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $ko FAIL ==="; exit 1
fi
pass "la 049 s'applique sur la copie du réel"
[ "$(q -c "SELECT count(*) FROM knowledge_entries WHERE id IN ($IDS)")" = 0 ] \
  && pass "les 5 pièces Ryvu ont quitté le dossier" || fail "une pièce Ryvu est restée au dossier"
[ "$(q -c "SELECT md5(string_agg(piece->>'content', '|' ORDER BY entry_id)) FROM pieces_ecartees")" = "$AVANT_HASH" ] \
  && pass "le registre conserve les 5 pièces ENTIÈRES (contenu identique)" || fail "contenu altéré au registre"
[ "$(q -c "SELECT count(*) FROM knowledge_entries WHERE id = 664 AND superseded_by IS NULL")" = 1 ] \
  && pass "la #664 (juste sur RVMD) reste au dossier" || fail "la #664 a été emportée"
[ "$(q -c "SELECT count(*) FROM knowledge_entries WHERE ticker_id='RVMD'")" = "$((AVANT_RVMD - 5))" ] \
  && pass "le reste du dossier RVMD est intact ($AVANT_RVMD → $((AVANT_RVMD - 5)))" || fail "autre chose a bougé au dossier RVMD"
[ "$(q -c "SELECT count(*) FROM pieces_ecartees p, jsonb_array_elements(p.couvertures) c WHERE c->>'question_id' = 'mo_3'")" = 2 ] \
  && pass "les 2 rattachements à mo_3 sont conservés au registre" || fail "rattachements perdus"
[ "$(app -c "SELECT count(*) FROM pieces_ecartees")" = 5 ] \
  && pass "le rôle applicatif LIT le registre" || fail "le rôle applicatif ne lit pas le registre"

echo "── [ACL] le registre est append-only, et fermé à l'application"
refuse "permission denied" "le rôle applicatif ne peut pas ÉCARTER une pièce (INSERT)" \
  app -c "INSERT INTO pieces_ecartees (entry_id, ticker_id, ecartee_par, motif, piece) VALUES (1,'RVMD','x','y','{\"id\":1,\"content\":\"c\"}')"
refuse "permission denied" "le rôle applicatif ne peut pas RÉÉCRIRE un écart (UPDATE)" \
  app -c "UPDATE pieces_ecartees SET motif = 'autre'"
refuse "permission denied" "le rôle applicatif ne peut pas EFFACER un écart (DELETE)" \
  app -c "DELETE FROM pieces_ecartees"
refuse "est un registre" "le trigger refuse la réécriture même au propriétaire" \
  q -c "UPDATE pieces_ecartees SET motif = 'autre'"
refuse "est un registre" "le trigger refuse l'effacement même au propriétaire" \
  q -c "DELETE FROM pieces_ecartees"
refuse "pieces_ecartees_texte" "un écart sans motif est refusé par SA contrainte" \
  q -c "INSERT INTO pieces_ecartees (entry_id, ticker_id, ecartee_par, motif, piece) VALUES (1,'RVMD','x','  ','{\"id\":1,\"content\":\"c\"}')"

# muter <label> <motif attendu> <python de mutation sur le SQL> [préparation SQL de la fixture]
muter() {
  local label=$1 attendu=$2 py=$3 prep=${4:-}
  fixture
  [ -n "$prep" ] && q -c "$prep" >/dev/null
  python3 -c "import sys; s=open('$SQL').read(); $py; open('/tmp/049_mut.sql','w').write(s)" || { fail "$label — mutation non appliquée"; return; }
  docker cp /tmp/049_mut.sql "$PG:/tmp/049_mut.sql" >/dev/null
  refuse "$attendu" "$label" q -f /tmp/049_mut.sql
}
echo "── [K] chaque garde lève nommément"
muter "049/K1 : une 049 privée de son REVOKE lève" "049/K1" \
  "o='REVOKE ALL ON public.pieces_ecartees FROM portfolio_user;'; assert o in s; s=s.replace(o,'')"
muter "049/K2 : une pièce déjà remplacée (état changé depuis la mesure) fait lever" "049/K2" \
  "pass" "UPDATE knowledge_entries SET superseded_by = 664 WHERE id = 665"
muter "049/K2 : une pièce désignée comme remplaçante fait lever" "049/K2" \
  "pass" "UPDATE knowledge_entries SET superseded_by = 665 WHERE id = (SELECT min(id) FROM knowledge_entries WHERE superseded_by IS NULL AND id <> 665)"
muter "rattachements laissés derrière : la clé étrangère refuse la suppression" "question_coverage_entry_id_fkey" \
  "o='DELETE FROM public.question_coverage WHERE entry_id IN (665, 666, 667, 671, 672);'; assert o in s; s=s.replace(o,'')"
muter "049/K3 : des rattachements perdus (non recopiés au registre) font lever" "049/K3" \
  "import re; s2=re.sub(r'COALESCE\(\(SELECT jsonb_agg.*?\x27\[\]\x27::jsonb\)\n', '\x27[]\x27::jsonb\n', s, count=1, flags=re.S); assert s2!=s; s=s2"
muter "049/K3 : une pièce copiée au registre mais restée au dossier fait lever" "049/K3" \
  "o='DELETE FROM public.knowledge_entries WHERE id IN (665, 666, 667, 671, 672);'; assert o in s; s=s.replace(o,'')"

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo; echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
