#!/usr/bin/env bash
# TEST NÉGATIF de `check_emetteurs_persist.py` — le rangement en base des modules M1 et M0
# (migration 063). Deux parties :
#
#   1. le CODE du rangement est muté (harnais `_negatif.sh`), le contrôle joué sur la base où la
#      063 est appliquée ;
#   2. la MIGRATION est mutée : chaque version mutée est appliquée sur une base JETABLE
#      (`db_063_neg`, créée vide — la 063 ne dépend d'aucune autre table), et le contrôle doit
#      rougir sur l'assert visé, ou la migration se refuser elle-même par sa garde [K1].
#
#   bash checks/negatif_emetteurs_persist.sh
#
# Sur le VPS : rien à régler (`shared-postgres`, image de `portfolio-backend`, `DATABASE_URL` du
# `.env`). Sans conteneur (bac à sable) : PostgreSQL local, et les deux adresses en variables :
#   CHECK_DB_URL=postgresql://portfolio_user:…@127.0.0.1/<base avec la 063>
#   SCRATCH_URL=postgresql://portfolio_user:…@127.0.0.1/db_063_neg
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_emetteurs_persist.py"
SQL="app/db/migrations/063_v3_emetteurs_et_chef_de_dossier.sql"
SCRATCH=db_063_neg
EME="app/modules/emetteurs/depot_base.py"
CHEF="app/modules/chef_de_dossier/depot_base.py"

IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}' 2>/dev/null)
if [ -z "${CHECK_DB_URL:-}" ] && [ -f .env ]; then
  CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
fi
export CHECK_DB_URL="${CHECK_DB_URL:-}"
[ -n "$CHECK_DB_URL" ] || { echo "FAIL CHECK_DB_URL absente : rien ne serait mesuré"; exit 1; }
SCRATCH_URL="${SCRATCH_URL:-${CHECK_DB_URL%/*}/$SCRATCH}"

if docker inspect shared-postgres >/dev/null 2>&1; then
  psql_adm() { docker exec -i shared-postgres psql -U admin -v ON_ERROR_STOP=1 -q "$@"; }
else
  psql_adm() { su postgres -c "psql -v ON_ERROR_STOP=1 -q $(printf '%q ' "$@")"; }
fi

echo "── 1. le code du rangement, muté"
NET=coolify
HOTE_SI_SANS_CONTENEUR=1
mutations=(
# [B1] les révisions sont relues à l'envers : la fiche « en vigueur » serait la première.
"$EME¦WHERE emetteur = \$1 ORDER BY revision\"¦WHERE emetteur = \$1 ORDER BY revision DESC\"¦[B1] FICTIVE-BASE-1 : la fiche relue en base"
# [B3] un doublon n'est plus reconnu : le refus nommé devient une erreur brute de la base.
"$EME¦    return getattr(exc, \"sqlstate\", None) == \"23505\"¦    return False¦[B3] une révision déjà rangée ne s'écrase pas"
# [B7] le JSON n'est plus passé en texte : avec le codec du service, il serait encodé deux fois.
"$EME¦VALUES (\$1, \$2, \$3::text::jsonb)\"¦VALUES (\$1, \$2, \$3::jsonb)\"¦section interrompue (codec JSON)"
# [B6] un dossier déjà rangé s'écrase sans regarder la révision lue.
"$CHEF¦\"WHERE dossier = \$1 AND revision = \$3 RETURNING revision\"¦\"WHERE dossier = \$1 AND \$3 > 0 RETURNING revision\"¦[B6] dossier déjà rangé"
# [B6] un dossier neuf rangé deux fois : le second écrase le premier.
"$CHEF¦\"ON CONFLICT (dossier) DO NOTHING RETURNING revision\"¦\"ON CONFLICT (dossier) DO UPDATE SET etat = EXCLUDED.etat RETURNING revision\"¦[B6] dossier neuf"
# [B5] l'état relu n'est pas celui qu'on a rangé.
"$CHEF¦            depot.ranger(dossier, json.loads(ligne[\"etat\"]))¦            pass¦[B5] l'état rangé en base se relit identique"
)
source "$(dirname "$0")/_negatif.sh"
( run_mutations ); partie1=$?

echo
echo "── 2. la migration 063, mutée (base jetable $SCRATCH)"
ok=0; ko=0
lancer_check() {  # joue le contrôle NON muté contre la base jetable
  if [ -n "$IMG" ]; then
    docker run --rm --network coolify -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e "CHECK_DB_URL=$SCRATCH_URL" "$IMG" python "$CHECK" 2>&1
  else
    CHECK_DB_URL="$SCRATCH_URL" PYTHONDONTWRITEBYTECODE=1 python3 "$CHECK" 2>&1
  fi
}
appliquer() {  # $1 = motif, $2 = remplaçant ; rend la sortie de psql, exit ≠ 0 si la migration lève
  psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" >/dev/null 2>&1 \
    || { echo "ERREUR : base jetable"; return 2; }
  python3 -c "
import sys, pathlib
s = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
if sys.argv[2] and sys.argv[2] not in s:
    print('MOTIF INTROUVABLE'); sys.exit(3)
sys.stdout.write(s.replace(sys.argv[2], sys.argv[3], 1) if sys.argv[2] else s)
" "$SQL" "$1" "$2" > /tmp/063_mutee.sql || { echo "MOTIF INTROUVABLE"; return 3; }
  psql_adm -d "$SCRATCH" < /tmp/063_mutee.sql 2>&1
}
rougit() {  # $1 = motif SQL, $2 = remplaçant, $3 = assert attendu
  local out rc
  out=$(appliquer "$1" "$2"); rc=$?
  if [ "$rc" -ne 0 ]; then echo "  FAIL $3 — la migration mutée ne s'applique pas : $(printf '%s' "$out" | tail -1)"; ko=$((ko+1)); return; fi
  out=$(lancer_check); rc=$?
  if ! printf '%s' "$out" | grep -q 'vérifications OK'; then echo "  FAIL $3 — contrôle mort avant son bilan"; ko=$((ko+1))
  elif [ "$rc" -eq 0 ]; then echo "  FAIL $3 — le contrôle reste VERT"; ko=$((ko+1))
  elif printf '%s' "$out" | grep -F 'FAIL' | grep -qF -- "$3"; then echo "  ok   $3"; ok=$((ok+1))
  else echo "  FAIL $3 — rouge, mais pas sur l'assert visé : $(printf '%s' "$out" | grep -F FAIL | head -1)"; ko=$((ko+1)); fi
}
se_refuse() {  # $1 = motif SQL, $2 = remplaçant, $3 = libellé ; la migration doit LEVER par [K1]
  local out
  if out=$(appliquer "$1" "$2") ; then echo "  FAIL $3 — la migration mutée s'applique"; ko=$((ko+1))
  elif printf '%s' "$out" | grep -q '063/K1'; then echo "  ok   $3"; ok=$((ok+1))
  else echo "  FAIL $3 — refusée, mais pas par [K1] : $(printf '%s' "$out" | tail -1)"; ko=$((ko+1)); fi
}

# Satisfiabilité : la 063 non mutée s'applique sur une base vide et le contrôle y est vert.
if out=$(appliquer "" "") && out=$(lancer_check); then echo "  ok   [sat] la 063 non mutée : contrôle vert"; ok=$((ok+1))
else echo "  FAIL [sat] la 063 non mutée ne passe pas : $(printf '%s' "$out" | tail -2)"; ko=$((ko+1)); fi
# Le trigger refuse même au propriétaire des tables.
for t in emetteurs_fiches emetteurs_sources_actes; do
  if out=$(psql_adm -d "$SCRATCH" -c "UPDATE $t SET enregistre_le = now(); DELETE FROM $t;" 2>&1) \
     || ! psql_adm -d "$SCRATCH" -c "DO \$\$ BEGIN PERFORM 1; END \$\$;" >/dev/null 2>&1; then :; fi
  n=$(psql_adm -d "$SCRATCH" -tA -c "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'public.$t'::regclass AND NOT tgisinternal AND tgname = '${t}_immuable'")
  if [ "$n" = "1" ]; then echo "  ok   [B2] $t : le trigger d'ajout seul est posé"; ok=$((ok+1))
  else echo "  FAIL [B2] $t : trigger d'ajout seul absent"; ko=$((ko+1)); fi
done

rougit "contenu->>'emetteur' = emetteur AND (contenu->>'revision')::integer = revision)" "TRUE)" \
       "une fiche rangée sous un autre identifiant"
rougit "        AND btrim(coalesce(contenu->>'motif', '')) <> ''" "" "une révision sans motif est refusée par la base"
rougit "NOT (acte = 'admettre' AND auteur LIKE 'systeme:%' AND btrim(critere) = '')" "TRUE" \
       "une admission du système sans critère est refusée par la base"
rougit "(acte = 'revoquer' AND jsonb_array_length(natures) = 0 AND niveau = '' AND critere = '')" "(acte = 'revoquer')" \
       "une révocation qui porte un niveau"
rougit "(acte = 'admettre' AND jsonb_array_length(natures) >= 1 AND btrim(niveau) <> '')" "(acte = 'admettre')" \
       "une admission sans nature est refusée par la base"
rougit "    CONSTRAINT emetteurs_fiches_unique UNIQUE (emetteur, revision)," "" "une révision déjà rangée ne s'écrase pas"
rougit "    rang          integer     PRIMARY KEY," "    rang          integer     NOT NULL," \
       "un rang déjà pris au journal ne s'écrase pas"
rougit "        etat->>'dossier' = dossier AND" "        TRUE AND" "un état rangé sous un autre dossier"
se_refuse "GRANT SELECT, INSERT ON public.emetteurs_fiches, public.emetteurs_sources_actes TO portfolio_user;" \
          "GRANT SELECT, INSERT, UPDATE ON public.emetteurs_fiches, public.emetteurs_sources_actes TO portfolio_user;" \
          "[K1] un registre réécrivable par le service : la migration se refuse"
se_refuse "GRANT SELECT, INSERT, UPDATE ON public.chef_etats TO portfolio_user;" \
          "GRANT SELECT, INSERT, UPDATE, DELETE ON public.chef_etats TO portfolio_user;" \
          "[K1] l'état d'un dossier supprimable par le service : la migration se refuse"
se_refuse "REVOKE ALL ON public.emetteurs_fiches, public.emetteurs_sources_actes, public.chef_etats FROM portfolio_user;
GRANT SELECT, INSERT ON public.emetteurs_fiches, public.emetteurs_sources_actes TO portfolio_user;" \
          "GRANT ALL ON public.emetteurs_fiches, public.emetteurs_sources_actes TO portfolio_user;" \
          "[K1] sans le retrait des droits par défaut : la migration se refuse"

psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null 2>&1
rm -f /tmp/063_mutee.sql
echo
echo "============================================================"
echo "partie 2 : $ok ok / $ko FAIL"
[ "$partie1" -eq 0 ] && [ "$ko" -eq 0 ] || exit 1
