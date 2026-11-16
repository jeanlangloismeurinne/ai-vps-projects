#!/usr/bin/env bash
# TEST NÉGATIF de `check_recueil_persist.py` — le rangement en base du module M2 « recueil »
# (migration 064). Deux parties :
#
#   1. le CODE du rangement est muté (`app/modules/recueil/depot_base.py`, harnais `_negatif.sh`),
#      le contrôle joué sur la base où 063 ET 064 sont déjà appliquées ;
#   2. la MIGRATION est mutée : chaque version mutée est appliquée sur une base JETABLE
#      (`db_064_neg`, créée vide après 063 — 064 en dépend pour `chef_de_dossier`/`emetteurs`,
#      mais recueil_persist ne lit pas ces tables), et le contrôle doit rougir sur l'assert visé,
#      ou la migration se refuser elle-même par sa garde [K1].
#
#   bash checks/negatif_recueil_persist.sh
#
# Sur le VPS : rien à régler (`shared-postgres`, image de `portfolio-backend`, `DATABASE_URL` du
# `.env`) — MÊME convention que `negatif_emetteurs_persist.sh`. Sans conteneur de production
# disponible pour l'administration (bac à sable, sandbox CI) : fournir les adresses ET le
# conteneur/utilisateur d'administration en variables :
#   CHECK_DB_URL=postgresql://…           # base où 063 ET 064 sont déjà appliquées
#   SCRATCH_URL=postgresql://…            # base jetable, vide (sera DROP/CREATE à chaque mutation)
#   ADM_CONTENEUR=mon_postgres_jetable    # défaut : shared-postgres
#   ADM_UTILISATEUR=mon_superutilisateur  # défaut : admin
#   NET=mon_reseau_docker                 # défaut : coolify
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_recueil_persist.py"
SQL="app/db/migrations/064_v3_recueil.sql"
SCRATCH="${SCRATCH_DB:-db_064_neg}"
DEPOT="app/modules/recueil/depot_base.py"

IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}' 2>/dev/null)
if [ -z "${CHECK_DB_URL:-}" ] && [ -f .env ]; then
  CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
fi
export CHECK_DB_URL="${CHECK_DB_URL:-}"
[ -n "$CHECK_DB_URL" ] || { echo "FAIL CHECK_DB_URL absente : rien ne serait mesuré"; exit 1; }
SCRATCH_URL="${SCRATCH_URL:-${CHECK_DB_URL%/*}/$SCRATCH}"
ADM_CONTENEUR="${ADM_CONTENEUR:-shared-postgres}"
ADM_UTILISATEUR="${ADM_UTILISATEUR:-admin}"

if docker inspect "$ADM_CONTENEUR" >/dev/null 2>&1; then
  psql_adm() { docker exec -i "$ADM_CONTENEUR" psql -U "$ADM_UTILISATEUR" -v ON_ERROR_STOP=1 -q "$@"; }
else
  psql_adm() { su postgres -c "psql -v ON_ERROR_STOP=1 -q $(printf '%q ' "$@")"; }
fi

echo "── 1. le code du rangement (depot_base.py), muté"
NET="${NET:-coolify}"
HOTE_SI_SANS_CONTENEUR=1
mutations=(
# [R1] les réponses sont relues à l'envers : « la dernière » serait la première ajoutée.
"$DEPOT¦WHERE emetteur = \$1 ORDER BY rang\",¦WHERE emetteur = \$1 ORDER BY rang DESC\",¦[R1] FICTIVE-ANCIENNE : lire_recueil identique en base et en mémoire"
# [R3] un doublon ÉCRASE le document déjà rangé au lieu d'être ignoré — le rôle applicatif n'a
# pas le privilège UPDATE (063/064 §K1) : la tentative échoue bruyamment plutôt que silencieusement.
"$DEPOT¦ON CONFLICT (empreinte) DO NOTHING RETURNING empreinte\",¦ON CONFLICT (empreinte) DO UPDATE SET fiche = EXCLUDED.fiche RETURNING empreinte\",¦section interrompue — InsufficientPrivilegeError"
# [R3] le contenu rangé n'est plus celui reçu (corruption détectable octet pour octet).
"$DEPOT¦empreinte, bytes(contenu))¦empreinte, bytes(contenu)[::-1])¦[R3] le contenu relu est identique octet pour octet (binaire)"
# [R4] un travail déjà rangé ne se remplace plus : la reprise ne fait plus avancer le dossier.
"$DEPOT¦\"ON CONFLICT (cle) DO UPDATE SET contenu = EXCLUDED.contenu, range_le = now()\",¦\"ON CONFLICT (cle) DO NOTHING\",¦[R4] en base : le dossier termine son parcours après la reprise"
# [R5] une source déjà notée ne garde plus son état — la colonne `emetteur` (SQL) et celle du
# JSON divergent alors, et la contrainte de cohérence de la migration 064 refuse l'écriture.
"$DEPOT¦        fusionne = {**anc, \"adresses\": vues}¦        fusionne = {**neuve, \"adresses\": vues}¦section interrompue — InFailedSQLTransactionError"
# [R5] marquer_source écrase l'état au lieu de fusionner les champs donnés (perd « emetteur »,
# relu ensuite par `lire_recueil`/`vue_ecran`).
"$DEPOT¦        fusionne = {**json.loads(anc_texte), **dict(champs)}¦        fusionne = dict(champs)¦section interrompue — KeyError"
# [R6] le JSON n'est plus passé en texte : avec le codec du service, il serait encodé deux fois.
"$DEPOT¦VALUES (\$1, \$2, \$3, \$4, \$5, \$6::text::jsonb) \"¦VALUES (\$1, \$2, \$3, \$4, \$5, \$6::jsonb) \"¦section interrompue (codec JSON)"
)
source "$(dirname "$0")/_negatif.sh"
( run_mutations ); partie1=$?

echo
echo "── 2. la migration 064, mutée (base jetable $SCRATCH)"
ok=0; ko=0
lancer_check() {  # joue le contrôle NON muté contre la base jetable
  if [ -n "$IMG" ]; then
    docker run --rm --network "$NET" -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app \
      --env-file checks/env.checks -e "CHECK_DB_URL=$SCRATCH_URL" "$IMG" python "$CHECK" 2>&1
  else
    CHECK_DB_URL="$SCRATCH_URL" PYTHONDONTWRITEBYTECODE=1 python3 "$CHECK" 2>&1
  fi
}
appliquer() {  # $1 = motif, $2 = remplaçant ; rend la sortie de psql, exit ≠ 0 si la migration lève
  psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" >/dev/null 2>&1 \
    || { echo "ERREUR : base jetable"; return 2; }
  docker cp "app/db/migrations/063_v3_emetteurs_et_chef_de_dossier.sql" "$ADM_CONTENEUR:/tmp/_neg_063.sql" 2>/dev/null \
    || cp "app/db/migrations/063_v3_emetteurs_et_chef_de_dossier.sql" /tmp/_neg_063.sql
  if docker inspect "$ADM_CONTENEUR" >/dev/null 2>&1; then
    psql_adm -d "$SCRATCH" -f /tmp/_neg_063.sql >/dev/null 2>&1 || { echo "ERREUR : 063 préalable"; return 2; }
  else
    psql_adm -d "$SCRATCH" -f /tmp/_neg_063.sql >/dev/null 2>&1 || { echo "ERREUR : 063 préalable"; return 2; }
  fi
  python3 -c "
import sys, pathlib
s = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
if sys.argv[2] and sys.argv[2] not in s:
    print('MOTIF INTROUVABLE'); sys.exit(3)
sys.stdout.write(s.replace(sys.argv[2], sys.argv[3], 1) if sys.argv[2] else s)
" "$SQL" "$1" "$2" > /tmp/064_mutee.sql || { echo "MOTIF INTROUVABLE"; return 3; }
  psql_adm -d "$SCRATCH" < /tmp/064_mutee.sql 2>&1
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
  elif printf '%s' "$out" | grep -q '064/K1'; then echo "  ok   $3"; ok=$((ok+1))
  else echo "  FAIL $3 — refusée, mais pas par [K1] : $(printf '%s' "$out" | tail -1)"; ko=$((ko+1)); fi
}
retire_trigger() {  # $1 = table, $2 = motif SQL (le bloc CREATE TRIGGER), $3 = libellé
  # Le rôle applicatif (portfolio_user) n'a de toute façon pas le privilège UPDATE/DELETE sur les
  # trois registres (REVOKE de la migration) : rejouer `check_recueil_persist.py` ne DISCRIMINE
  # donc PAS un trigger retiré (le refus vient alors du privilège, pas du trigger — même angle
  # mort que `negatif_emetteurs_persist.sh`, qui ne teste cet invariant que par le catalogue). On
  # vérifie directement le catalogue, sous l'administrateur, qui bypasse les privilèges de rôle.
  local out rc n
  out=$(appliquer "$2" ""); rc=$?
  if [ "$rc" -ne 0 ]; then echo "  FAIL $3 — la migration mutée ne s'applique pas : $(printf '%s' "$out" | tail -1)"; ko=$((ko+1)); return; fi
  n=$(psql_adm -d "$SCRATCH" -tA -c "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'public.$1'::regclass AND NOT tgisinternal")
  if [ "$n" = "0" ]; then echo "  ok   $3"; ok=$((ok+1))
  else echo "  FAIL $3 — le trigger est toujours au catalogue après la mutation (motif erroné ?)"; ko=$((ko+1)); fi
}

# Satisfiabilité : la 064 non mutée s'applique sur 063 et le contrôle y est vert.
if out=$(appliquer "" "") && out=$(lancer_check); then echo "  ok   [sat] la 064 non mutée : contrôle vert"; ok=$((ok+1))
else echo "  FAIL [sat] la 064 non mutée ne passe pas : $(printf '%s' "$out" | tail -2)"; ko=$((ko+1)); fi

# Le trigger refuse même au propriétaire des trois registres.
for t in recueil_documents recueil_contenus recueil_reponses; do
  n=$(psql_adm -d "$SCRATCH" -tA -c "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'public.$t'::regclass AND NOT tgisinternal AND tgname = '${t}_immuable'")
  if [ "$n" = "1" ]; then echo "  ok   [B2] $t : le trigger d'ajout seul est posé"; ok=$((ok+1))
  else echo "  FAIL [B2] $t : trigger d'ajout seul absent"; ko=$((ko+1)); fi
done

retire_trigger recueil_documents "CREATE TRIGGER recueil_documents_immuable
    BEFORE UPDATE OR DELETE ON public.recueil_documents
    FOR EACH ROW EXECUTE FUNCTION public.recueil_registre_immuable();

" "[R2] recueil_documents : le trigger d'ajout seul retiré est absent du catalogue"
retire_trigger recueil_contenus "CREATE TRIGGER recueil_contenus_immuable
    BEFORE UPDATE OR DELETE ON public.recueil_contenus
    FOR EACH ROW EXECUTE FUNCTION public.recueil_registre_immuable();

" "[R2] recueil_contenus : le trigger d'ajout seul retiré est absent du catalogue"
retire_trigger recueil_reponses "CREATE TRIGGER recueil_reponses_immuable
    BEFORE UPDATE OR DELETE ON public.recueil_reponses
    FOR EACH ROW EXECUTE FUNCTION public.recueil_registre_immuable();

" "[R2] recueil_reponses : le trigger d'ajout seul retiré est absent du catalogue"
se_refuse "GRANT SELECT, INSERT ON public.recueil_documents, public.recueil_contenus, public.recueil_reponses
    TO portfolio_user;" \
          "GRANT SELECT, INSERT, UPDATE ON public.recueil_documents, public.recueil_contenus, public.recueil_reponses
    TO portfolio_user;" \
          "[K1] un registre réécrivable par le service : la migration se refuse"
se_refuse "GRANT SELECT, INSERT, UPDATE ON public.recueil_travaux, public.recueil_sources_rencontrees
    TO portfolio_user;" \
          "GRANT SELECT, INSERT, UPDATE, DELETE ON public.recueil_travaux, public.recueil_sources_rencontrees
    TO portfolio_user;" \
          "[K1] l'état supprimable par le service : la migration se refuse"

psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null 2>&1
rm -f /tmp/064_mutee.sql /tmp/_neg_063.sql
echo
echo "============================================================"
echo "partie 2 : $ok ok / $ko FAIL"
[ "$partie1" -eq 0 ] && [ "$ko" -eq 0 ] || exit 1
