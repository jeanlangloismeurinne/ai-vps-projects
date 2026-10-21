#!/usr/bin/env bash
# TEST NÉGATIF de la migration 061 (classeur de l'entreprise : architecture, fourchettes,
# scénarios, déplacements) — éprouvé AVANT application, sur une COPIE de `db_portfolio` (motif de
# `negatif_051.sh`).
#
#   bash checks/negatif_061.sh
#
# SATISFIABILITÉ : la 061 non mutée passe sur la copie du réel, et le rôle APPLICATIF y inscrit une
# architecture, une fourchette, un scénario nommé à deux déplacements, et une branche à probabilité.
# DISCRIMINATION : chaque CHECK refuse sa forme interdite PAR SON NOM (PostgreSQL teste les CHECK par
# ordre alphabétique : un refus prononcé par une autre contrainte est un faux vert, cf. #83) ; le rôle
# applicatif ne peut ni modifier ni supprimer une ligne des QUATRE registres ; le trigger refuse même
# au propriétaire ; [K1] une 061 privée d'un de ses REVOKE doit LEVER nommément.
#
# Fixture copiée du réel (`pg_dump`), jamais écrite à la main. `docker cp` + `psql -f`, jamais un
# heredoc via `docker exec` (il échoue en silence).
set -u
cd "$(dirname "$0")/.." || exit 1
PG=shared-postgres; SRC=db_portfolio; SCRATCH=db_061_neg
SQL=app/db/migrations/061_v3_classeur_entreprise.sql
psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
q()   { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
app() { docker exec "$PG" psql -U portfolio_user -d "$SCRATCH" -v ON_ERROR_STOP=1 -tA "$@"; }
fixture() {
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" || exit 2
  docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $SCRATCH" >/dev/null 2>&1 \
    || { echo "ERREUR : restauration"; exit 2; }
}
docker cp "$SQL" "$PG:/tmp/061.sql" >/dev/null
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

echo "── [sat] la 061 non mutée, sur la copie du réel"
fixture
if ! out=$(q -f /tmp/061.sql 2>&1); then
  fail "satisfiabilité — la 061 lève sur le réel :"; printf '%s\n' "$out" | tail -3
  echo; echo "=== $ok ok / $((ko)) FAIL ==="; exit 1
fi
TK=$(q -c "SELECT id FROM tickers WHERE id = 'NVDA'")
[ "$TK" = NVDA ] || { echo "ERREUR : NVDA absent de la copie — vraie par dégénérescence"; exit 2; }

c() { printf '{"ticker_id":"%s","version":%s,"schema_version":"architecture-1.0.0"}' "$1" "$2"; }
A="INSERT INTO architectures_modele (ticker_id, version, schema_version, version_referentiel, auteur, contenu) VALUES"
F="INSERT INTO modele_fourchettes (architecture_id, bloc, variable, periode_debut, periode_fin, bas, haut, methode, contenu, auteur) VALUES"
S="INSERT INTO modele_scenarios (architecture_id, nom, nature, probabilite, contenu, auteur) VALUES"
D="INSERT INTO modele_deplacements (scenario_id, bloc, variable, periode_debut, periode_fin, cible, valeur_dite, motif, source_entry_refs) VALUES"

if A1=$(app -c "$A ('NVDA', 1, 'architecture-1.0.0', '1.0.0', 'agent', '$(c NVDA 1)') RETURNING id" 2>&1) \
   && A2=$(app -c "$A ('NVDA', 2, 'architecture-1.0.0', '1.0.0', 'agent', '$(c NVDA 2)') RETURNING id" 2>&1); then
  A1=${A1%%$'\n'*}; A2=${A2%%$'\n'*}
  pass "le rôle applicatif inscrit deux ARCHITECTURES proposées (#$A1, #$A2)"
else fail "le rôle applicatif n'inscrit pas une architecture valide : $A1 $A2"; exit 1; fi

fc() { printf '{"bloc":"%s","variable":"%s","periode_debut":"FY2025","periode_fin":"FY2027","bas":%s,"haut":%s,"methode":"dispersion_observee"}' "$1" "$2" "$3" "$4"; }
if FID=$(app -c "$F ($A1, 'bloc_x', 'croissance_du_marche', 'FY2025', 'FY2027', 0.0, 0.3, 'dispersion_observee', '$(fc bloc_x croissance_du_marche 0.0 0.3)', 'analyste') RETURNING id" 2>&1); then
  FID=${FID%%$'\n'*}
  pass "le rôle applicatif inscrit une FOURCHETTE (#$FID)"
else fail "le rôle applicatif n'inscrit pas une fourchette valide : $FID"; exit 1; fi

sc() { printf '{"nom":"%s","nature":"%s"}' "$1" "$2"; }
if SID1=$(app -c "$S ($A1, 'scenario_nomme_test', 'nomme', NULL, '$(sc scenario_nomme_test nomme)', 'constructeur') RETURNING id" 2>&1); then
  SID1=${SID1%%$'\n'*}
  pass "le rôle applicatif inscrit un SCÉNARIO NOMMÉ, sans probabilité (#$SID1)"
else fail "le rôle applicatif n'inscrit pas un scénario nommé valide : $SID1"; exit 1; fi
if SID2=$(app -c "$S ($A1, 'scenario_branche_test', 'branche', 0.4, '$(sc scenario_branche_test branche)', 'constructeur') RETURNING id" 2>&1); then
  SID2=${SID2%%$'\n'*}
  pass "le rôle applicatif inscrit une BRANCHE, avec sa probabilité (#$SID2)"
else fail "le rôle applicatif n'inscrit pas une branche valide : $SID2"; exit 1; fi
if app -c "$D ($SID1, 'bloc_x', 'croissance_du_marche', 'FY2025', 'FY2026', 'borne_basse', NULL, 'Motif du déplacement teste, assez long pour la contrainte.', '{}')" >/dev/null 2>&1 \
   && app -c "$D ($SID1, 'bloc_commun', 'couts_communs', 'FY2025', 'FY2026', 'valeur_dite', 500.0, 'Motif du second déplacement teste, assez long pour la contrainte.', '{501}')" >/dev/null 2>&1; then
  pass "le rôle applicatif inscrit DEUX déplacements pour le scénario nommé (borne basse, valeur dite)"
else fail "le rôle applicatif n'inscrit pas les deux déplacements valides"; fi

echo "── [CHK] chaque forme interdite est refusée par SA contrainte"
refuse architectures_modele_unique "deux lignes pour la MÊME version d'un titre sont refusées" \
  "$A ('NVDA', 1, 'architecture-1.0.0', '1.0.0', 'agent', '$(c NVDA 1)')"
refuse architectures_modele_contenu "un contenu d'un AUTRE titre est refusé" \
  "$A ('NVDA', 3, 'architecture-1.0.0', '1.0.0', 'agent', '$(c RVMD 3)')"
refuse architectures_modele_contenu "un contenu d'une AUTRE version est refusé" \
  "$A ('NVDA', 3, 'architecture-1.0.0', '1.0.0', 'agent', '$(c NVDA 4)')"
refuse architectures_modele_contenu "un contenu d'un autre SCHÉMA est refusé" \
  "$A ('NVDA', 3, 'architecture-1.0.0', '1.0.0', 'agent', '{\"ticker_id\":\"NVDA\",\"version\":3,\"schema_version\":\"architecture-2.0.0\"}')"
refuse architectures_modele_version "une version 0 est refusée" \
  "$A ('NVDA', 0, 'architecture-1.0.0', '1.0.0', 'agent', '$(c NVDA 0)')"
refuse architectures_modele_auteur "une proposition SANS auteur est refusée" \
  "$A ('NVDA', 3, 'architecture-1.0.0', '1.0.0', '  ', '$(c NVDA 3)')"
refuse modele_fourchettes_ordonnee "une fourchette bas > haut est refusée" \
  "$F ($A1, 'bloc_x', 'test_ordonnee', 'FY2025', 'FY2027', 0.9, 0.1, 'dispersion_observee', '$(fc bloc_x test_ordonnee 0.9 0.1)', 'analyste')"
refuse modele_fourchettes_contenu "un contenu dont le bloc diffère de la colonne est refusé" \
  "$F ($A1, 'bloc_y', 'test_contenu', 'FY2025', 'FY2027', 0.0, 0.3, 'dispersion_observee', '$(fc bloc_x test_contenu 0.0 0.3)', 'analyste')"
refuse modele_fourchettes_auteur "une fourchette SANS auteur est refusée" \
  "$F ($A1, 'bloc_x', 'test_auteur', 'FY2025', 'FY2027', 0.0, 0.3, 'dispersion_observee', '$(fc bloc_x test_auteur 0.0 0.3)', '   ')"
refuse modele_scenarios_nature "une nature hors vocabulaire est refusée" \
  "$S ($A1, 'scenario_test_nature', 'central', NULL, '$(sc scenario_test_nature central)', 'constructeur')"
refuse modele_scenarios_probabilite "une branche SANS probabilité est refusée" \
  "$S ($A1, 'scenario_test_proba', 'branche', NULL, '$(sc scenario_test_proba branche)', 'constructeur')"
refuse modele_scenarios_probabilite "un nommé AVEC probabilité est refusé" \
  "$S ($A1, 'scenario_test_proba2', 'nomme', 0.5, '$(sc scenario_test_proba2 nomme)', 'constructeur')"
refuse modele_scenarios_probabilite "une probabilité hors [0,1] est refusée" \
  "$S ($A1, 'scenario_test_proba3', 'branche', 1.5, '$(sc scenario_test_proba3 branche)', 'constructeur')"
refuse modele_scenarios_auteur "un scénario SANS auteur est refusé" \
  "$S ($A1, 'scenario_test_auteur', 'nomme', NULL, '$(sc scenario_test_auteur nomme)', '')"
refuse modele_deplacements_cible "une cible hors vocabulaire est refusée" \
  "$D ($SID1, 'bloc_x', 'test_cible', 'FY2025', 'FY2026', 'borne_moyenne', NULL, 'Motif du déplacement teste, assez long.', '{}')"
refuse modele_deplacements_valeur_dite "une cible valeur_dite SANS valeur_dite est refusée" \
  "$D ($SID1, 'bloc_x', 'test_vd1', 'FY2025', 'FY2026', 'valeur_dite', NULL, 'Motif du déplacement teste, assez long.', '{}')"
refuse modele_deplacements_valeur_dite "une borne AVEC valeur_dite est refusée" \
  "$D ($SID1, 'bloc_x', 'test_vd2', 'FY2025', 'FY2026', 'borne_basse', 12.0, 'Motif du déplacement teste, assez long.', '{}')"
refuse modele_deplacements_motif "un motif BLANC est refusé" \
  "$D ($SID1, 'bloc_x', 'test_motif', 'FY2025', 'FY2026', 'borne_basse', NULL, '   ', '{}')"

echo "── [PV] les registres ne se réécrivent pas"
colonne_reecrite() { case "$1" in modele_deplacements) echo motif ;; *) echo auteur ;; esac; }
for T in architectures_modele modele_fourchettes modele_scenarios modele_deplacements; do
  COL=$(colonne_reecrite "$T")
  refuse "permission denied" "le rôle applicatif ne MODIFIE pas $T" "UPDATE $T SET $COL = 'réécrit'"
  refuse "permission denied" "le rôle applicatif ne SUPPRIME pas $T" "DELETE FROM $T"
  if out=$(q -c "UPDATE $T SET $COL = 'réécrit'" 2>&1); then
    fail "le PROPRIÉTAIRE a réécrit $T — le trigger ne garde rien"
  elif printf '%s' "$out" | grep -q "est un registre"; then
    pass "même le propriétaire ne réécrit pas $T (trigger nommé)"
  else fail "réécriture de $T refusée, mais pas par le trigger : $(printf '%s' "$out" | head -1)"; fi
done

echo "── [K1] une 061 privée d'un REVOKE → 061/K1 doit lever"
for T in architectures_modele modele_fourchettes modele_scenarios modele_deplacements; do
  fixture
  docker exec "$PG" sh -c "sed 's/^REVOKE ALL ON public.$T FROM portfolio_user;/-- mutation: REVOKE retiré/' /tmp/061.sql > /tmp/061_mut.sql"
  docker exec "$PG" grep -q '^-- mutation: REVOKE retiré' /tmp/061_mut.sql \
    || { echo "ERREUR : la mutation n'a rien remplacé ($T)"; exit 2; }
  if out=$(q -f /tmp/061_mut.sql 2>&1); then
    fail "[K1] la 061 sans REVOKE sur $T est passée — les privilèges par défaut laissent réécrire le registre"
  elif printf '%s' "$out" | grep -q "061/K1.*$T"; then pass "[K1] sans REVOKE sur $T : rouge sur sa garde nommée"
  else fail "[K1] ($T) a levé, mais pas sur 061/K1 : $(printf '%s' "$out" | grep -m1 ERROR)"; fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null
echo
echo "=== $ok ok / $ko FAIL ==="
[ "$ko" -eq 0 ]
