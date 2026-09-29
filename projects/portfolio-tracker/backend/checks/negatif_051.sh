#!/usr/bin/env bash
# TEST NÉGATIF de la migration 051 (modèle de valorisation : versions + PV de signature) — éprouvé
# AVANT application, sur une COPIE de `db_portfolio`.
#
#   bash checks/negatif_051.sh
#
# SATISFIABILITÉ : la 051 non mutée passe sur la copie du réel, et le rôle APPLICATIF y inscrit une
# version, une signature (fourchette ordonnée) et, sur une autre version, un écart.
# DISCRIMINATION : chaque CHECK refuse sa forme interdite PAR SON NOM (PostgreSQL teste les CHECK par
# ordre alphabétique : un refus prononcé par une autre contrainte est un faux vert, cf. #83) ; le rôle
# applicatif ne peut ni modifier ni supprimer une ligne des DEUX registres ; le trigger refuse même au
# propriétaire ; [K1] une 051 privée d'un de ses REVOKE doit LEVER nommément.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`, jamais un
# heredoc via `docker exec` (il échoue en silence).
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_051_neg
SQL=app/db/migrations/051_v3_modeles_valorisation.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/051.sql" >/dev/null
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

echo "── [sat] la 051 non mutée, sur la copie du réel"
fixture
if ! out=$(q -f /tmp/051.sql 2>&1); then
  fail "satisfiabilité — la 051 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $((ko)) FAIL ==="; exit 1
fi
TK=$(q -c "SELECT id FROM tickers WHERE id = 'RVMD'")
[ "$TK" = RVMD ] || { echo "ERREUR : RVMD absent de la copie — vraie par dégénérescence"; exit 2; }
c() { printf '{"ticker_id":"%s","version":%s,"schema_version":"modele-1.0.0"}' "$1" "$2"; }
V="INSERT INTO modeles_valorisation (ticker_id, version, schema_version, auteur, contenu) VALUES"
D="INSERT INTO modeles_valorisation_decisions (modele_id, action, auteur, motif, fourchette_bas, fourchette_central, fourchette_haut, par_evenement) VALUES"
if M1=$(app -c "$V ('RVMD', 1, 'modele-1.0.0', 'agent', '$(c RVMD 1)') RETURNING id" 2>&1) \
   && M2=$(app -c "$V ('RVMD', 2, 'modele-1.0.0', 'agent', '$(c RVMD 2)') RETURNING id" 2>&1); then
  M1=${M1%%$'\n'*}; M2=${M2%%$'\n'*}
  pass "le rôle applicatif inscrit deux VERSIONS proposées (#$M1, #$M2)"
else fail "le rôle applicatif n'inscrit pas une version valide : $M1 $M2"; exit 1; fi
if app -c "$D ($M1, 'signer', 'membre', 'modèle revu en séance', 20, 38, 61, '{\"succes_a\": [22, 70]}')" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit une SIGNATURE avec sa fourchette ordonnée"
else fail "le rôle applicatif n'inscrit pas une signature valide"; fi
if app -c "$D ($M2, 'ecarter', 'membre', 'la probabilité de phase 3 n''est pas ancrée', NULL, NULL, NULL, NULL)" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit un ÉCART sans fourchette"
else fail "le rôle applicatif n'inscrit pas un écart valide"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse modeles_valorisation_unique "deux lignes pour la MÊME version d'un titre sont refusées" \
  "$V ('RVMD', 1, 'modele-1.0.0', 'agent', '$(c RVMD 1)')"
refuse modeles_valorisation_contenu "un contenu d'un AUTRE titre est refusé" \
  "$V ('RVMD', 3, 'modele-1.0.0', 'agent', '$(c NVDA 3)')"
refuse modeles_valorisation_contenu "un contenu d'une AUTRE version est refusé" \
  "$V ('RVMD', 3, 'modele-1.0.0', 'agent', '$(c RVMD 4)')"
refuse modeles_valorisation_contenu "un contenu d'un autre SCHÉMA est refusé" \
  "$V ('RVMD', 3, 'modele-2.0.0', 'agent', '$(c RVMD 3)')"
refuse modeles_valorisation_version "une version 0 est refusée" \
  "$V ('RVMD', 0, 'modele-1.0.0', 'agent', '$(c RVMD 0)')"
refuse modeles_valorisation_auteur "une proposition SANS auteur est refusée" \
  "$V ('RVMD', 3, 'modele-1.0.0', '  ', '$(c RVMD 3)')"
refuse modeles_valorisation_decisions_unique "une SECONDE décision sur une version déjà décidée est refusée" \
  "$D ($M1, 'ecarter', 'membre', 'on se ravise', NULL, NULL, NULL, NULL)"
M3=$(app -c "$V ('RVMD', 3, 'modele-1.0.0', 'agent', '$(c RVMD 3)') RETURNING id"); M3=${M3%%$'\n'*}
refuse modeles_valorisation_decisions_forme "signer SANS fourchette est refusé" \
  "$D ($M3, 'signer', 'membre', 'motif', NULL, NULL, NULL, NULL)"
refuse modeles_valorisation_decisions_forme "signer une fourchette CROISÉE (bas > central) est refusé" \
  "$D ($M3, 'signer', 'membre', 'motif', 40, 38, 61, NULL)"
refuse modeles_valorisation_decisions_forme "signer une fourchette CROISÉE (central > haut) est refusé" \
  "$D ($M3, 'signer', 'membre', 'motif', 20, 62, 61, NULL)"
refuse modeles_valorisation_decisions_forme "écarter AVEC une fourchette est refusé" \
  "$D ($M3, 'ecarter', 'membre', 'motif', 20, 38, 61, NULL)"
refuse modeles_valorisation_decisions_forme "écarter avec un détail par événement est refusé" \
  "$D ($M3, 'ecarter', 'membre', 'motif', NULL, NULL, NULL, '{}')"
refuse modeles_valorisation_decisions_texte "un motif BLANC est refusé" \
  "$D ($M3, 'ecarter', 'membre', '   ', NULL, NULL, NULL, NULL)"
refuse modeles_valorisation_decisions_texte "une décision NON SIGNÉE est refusée" \
  "$D ($M3, 'ecarter', '', 'motif', NULL, NULL, NULL, NULL)"
refuse modeles_valorisation_decisions_action "une action hors vocabulaire est refusée" \
  "$D ($M3, 'amender', 'membre', 'motif', NULL, NULL, NULL, NULL)"

echo "── [PV] les registres ne se réécrivent pas"
for T in modeles_valorisation modeles_valorisation_decisions; do
  refuse "permission denied" "le rôle applicatif ne MODIFIE pas $T" "UPDATE $T SET auteur = 'réécrit'"
  refuse "permission denied" "le rôle applicatif ne SUPPRIME pas $T" "DELETE FROM $T"
  if out=$(q -c "UPDATE $T SET auteur = 'réécrit'" 2>&1); then
    fail "le PROPRIÉTAIRE a réécrit $T — le trigger ne garde rien"
  elif printf '%s' "$out" | grep -q "est un registre"; then
    pass "même le propriétaire ne réécrit pas $T (trigger nommé)"
  else fail "réécriture de $T refusée, mais pas par le trigger : $(printf '%s' "$out" | head -1)"; fi
done

echo "── [K1] une 051 privée d'un REVOKE → 051/K1 doit lever"
for T in modeles_valorisation modeles_valorisation_decisions; do
  fixture
  docker exec "$PG" sh -c "sed 's/^REVOKE ALL ON public.$T FROM portfolio_user;/-- mutation: REVOKE retiré/' /tmp/051.sql > /tmp/051_mut.sql"
  docker exec "$PG" grep -q '^-- mutation: REVOKE retiré' /tmp/051_mut.sql \
    || { echo "ERREUR : la mutation n'a rien remplacé ($T)"; exit 2; }
  if out=$(q -f /tmp/051_mut.sql 2>&1); then
    fail "[K1] la 051 sans REVOKE sur $T est passée — les privilèges par défaut laissent réécrire le registre"
  elif printf '%s' "$out" | grep -q "051/K1.*$T"; then pass "[K1] sans REVOKE sur $T : rouge sur sa garde nommée"
  else fail "[K1] ($T) a levé, mais pas sur 051/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
