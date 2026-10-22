#!/usr/bin/env bash
# TEST NÉGATIF de la migration 062 (procès-verbal de l'architecture) — éprouvé AVANT application,
# sur une COPIE de `db_portfolio` (motif de `negatif_061.sh`). La 061 est déjà appliquée en prod
# (table `architectures_modele` existante, 0 ligne) : la copie la porte déjà, on y insère une
# architecture de test pour avoir un `architecture_id` à décider.
#
#   bash checks/negatif_062.sh
#
# SATISFIABILITÉ : la 062 non mutée passe sur la copie du réel, et le rôle APPLICATIF y inscrit une
# signature puis une seconde décision (sur une AUTRE architecture) écartée.
# DISCRIMINATION : chaque CHECK refuse sa forme interdite PAR SON NOM ; le rôle applicatif ne peut ni
# modifier ni supprimer une ligne du registre ; le trigger refuse même au propriétaire ; [K1] une 062
# privée de son REVOKE doit LEVER nommément.
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_062_neg
SQL=app/db/migrations/062_v3_signature_architecture.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/062.sql" >/dev/null
ok=0; ko=0
pass() { echo "  ok   $1"; ok=$((ok+1)); }
fail() { echo "  FAIL $1"; ko=$((ko+1)); }

refuse() {
  local attendu=$1 label=$2 sql=$3 out
  if out=$(app -c "$sql" 2>&1); then fail "$label — ACCEPTÉ"
  elif printf '%s' "$out" | grep -q "$attendu"; then pass "$label"
  else fail "$label — refusé, mais pas par « $attendu » : $(printf '%s' "$out" | head -1)"; fi
}

echo "── [sat] la 062 non mutée, sur la copie du réel (061 déjà en place)"
fixture
if ! out=$(q -f /tmp/062.sql 2>&1); then
  fail "satisfiabilité — la 062 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $((ko)) FAIL ==="; exit 1
fi
TK=$(q -c "SELECT id FROM tickers WHERE id = 'NVDA'")
[ "$TK" = NVDA ] || { echo "ERREUR : NVDA absent de la copie — vraie par dégénérescence"; exit 2; }

c() { printf '{"ticker_id":"%s","version":%s,"schema_version":"architecture-1.1.0"}' "$1" "$2"; }
A="INSERT INTO architectures_modele (ticker_id, version, schema_version, version_referentiel, auteur, contenu) VALUES"
D="INSERT INTO architectures_modele_decisions (architecture_id, action, auteur, motif, signaux) VALUES"

if A1=$(q -c "$A ('NVDA', 1, 'architecture-1.1.0', '1.1.0', 'architecte (test)', '$(c NVDA 1)') RETURNING id" 2>&1) \
   && A2=$(q -c "$A ('NVDA', 2, 'architecture-1.1.0', '1.1.0', 'architecte (test)', '$(c NVDA 2)') RETURNING id" 2>&1); then
  A1=${A1%%$'\n'*}; A2=${A2%%$'\n'*}
  pass "deux ARCHITECTURES proposées pour avoir de quoi décider (#$A1, #$A2)"
else fail "préparation : impossible d'inscrire deux architectures de test : $A1 $A2"; exit 1; fi

if DID=$(app -c "$D ($A1, 'signer', 'comité (test)', 'Architecture signée pour ce test, motif de longueur suffisante.', '[\"[S3b] signal de test\"]') RETURNING id" 2>&1); then
  DID=${DID%%$'\n'*}
  pass "le rôle applicatif inscrit une SIGNATURE avec ses signaux (#$DID)"
else fail "le rôle applicatif n'inscrit pas une signature valide : $DID"; exit 1; fi

if app -c "$D ($A2, 'ecarter', 'comité (test)', 'Architecture écartée pour ce test, motif de longueur suffisante.', '[]')" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit un ÉCART (signaux vides, []) sur une AUTRE architecture"
else fail "le rôle applicatif n'inscrit pas un écart valide"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse architectures_modele_decisions_unique "une SECONDE décision pour la même architecture est refusée" \
  "$D ($A1, 'ecarter', 'comité (test)', 'Seconde décision refusée pour ce test, motif suffisant.', '[]')"
refuse architectures_modele_decisions_action "une action hors vocabulaire est refusée" \
  "$D ($A2, 'reporter', 'comité (test)', 'Action hors vocabulaire pour ce test, motif suffisant.', '[]')"
refuse architectures_modele_decisions_texte "une décision SANS auteur est refusée" \
  "$D ($A2, 'signer', '  ', 'Motif suffisant pour ce test, mais auteur blanc.', '[]')"
refuse architectures_modele_decisions_texte "une décision SANS motif est refusée" \
  "$D ($A2, 'signer', 'comité (test)', '   ', '[]')"
refuse architectures_modele_decisions_signaux "des signaux qui ne sont pas un tableau sont refusés" \
  "$D ($A2, 'signer', 'comité (test)', 'Motif suffisant, mais signaux mal formés pour ce test.', '{\"x\":1}')"
refuse "violates foreign key" "un architecture_id inconnu est refusé" \
  "$D (999999, 'signer', 'comité (test)', 'Motif suffisant pour une architecture inexistante.', '[]')"

echo "── [PV] le registre ne se réécrit pas"
refuse "permission denied" "le rôle applicatif ne MODIFIE pas architectures_modele_decisions" \
  "UPDATE architectures_modele_decisions SET motif = 'réécrit'"
refuse "permission denied" "le rôle applicatif ne SUPPRIME pas architectures_modele_decisions" \
  "DELETE FROM architectures_modele_decisions"
if out=$(q -c "UPDATE architectures_modele_decisions SET motif = 'réécrit'" 2>&1); then
  fail "le PROPRIÉTAIRE a réécrit architectures_modele_decisions — le trigger ne garde rien"
elif printf '%s' "$out" | grep -q "est le procès-verbal"; then
  pass "même le propriétaire ne réécrit pas architectures_modele_decisions (trigger nommé)"
else fail "réécriture refusée, mais pas par le trigger : $(printf '%s' "$out" | head -1)"; fi

echo "── [K1] une 062 privée de son REVOKE → 062/K1 doit lever"
fixture
docker exec "$PG" sh -c "sed 's/^REVOKE ALL ON public.architectures_modele_decisions FROM portfolio_user;/-- mutation: REVOKE retiré/' /tmp/062.sql > /tmp/062_mut.sql"
docker exec "$PG" grep -q '^-- mutation: REVOKE retiré' /tmp/062_mut.sql \
  || { echo "ERREUR : la mutation n'a rien remplacé"; exit 2; }
if out=$(q -f /tmp/062_mut.sql 2>&1); then
  fail "[K1] la 062 sans REVOKE est passée — les privilèges par défaut laissent réécrire le registre"
elif printf '%s' "$out" | grep -q "062/K1"; then pass "[K1] sans REVOKE : rouge sur sa garde nommée"
else fail "[K1] a levé, mais pas sur 062/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
