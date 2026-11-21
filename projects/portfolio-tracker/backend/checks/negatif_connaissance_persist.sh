#!/usr/bin/env bash
# TEST NÉGATIF de `check_connaissance_persist.py` — le rangement en base de la lecture (M3) et du
# déclencheur (migration 065). Deux parties, sur une base JETABLE (`db_065_neg`, recréée vide, 063 et
# 064 appliquées d'abord — 065 en dépend) :
#
#   1. le CODE du rangement est muté (`connaissance/depot_base.py`, `etude/depot_base.py`, harnais
#      `_negatif.sh`), le contrôle joué sur la base jetable où 063, 064 et 065 sont appliquées ;
#   2. la MIGRATION 065 est mutée et appliquée sur la base jetable recréée : le contrôle doit rougir
#      sur l'assert visé, ou la migration se refuser elle-même par sa garde [065/K1].
#
#   bash checks/negatif_connaissance_persist.sh
#
# Sur le VPS : rien à régler (`shared-postgres`, image de `portfolio-backend`, `DATABASE_URL` du
# `.env`, dont seul le nom de base change). Ailleurs : mêmes variables que `negatif_recueil_persist.sh`
# (CHECK_DB_URL, ADM_CONTENEUR, ADM_UTILISATEUR, NET).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_connaissance_persist.py"
SQL="app/db/migrations/065_v3_connaissance_etude.sql"
SCRATCH="${SCRATCH_DB:-db_065_neg}"
KD="app/modules/connaissance/depot_base.py"
TD="app/modules/etude/depot_base.py"

IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}' 2>/dev/null)
if [ -z "${CHECK_DB_URL:-}" ] && [ -f .env ]; then
  CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
fi
[ -n "${CHECK_DB_URL:-}" ] || { echo "FAIL CHECK_DB_URL absente : rien ne serait mesuré"; exit 1; }
SCRATCH_URL="${CHECK_DB_URL%/*}/$SCRATCH"
ADM_CONTENEUR="${ADM_CONTENEUR:-shared-postgres}"
ADM_UTILISATEUR="${ADM_UTILISATEUR:-admin}"
NET="${NET:-coolify}"
psql_adm() { docker exec -i "$ADM_CONTENEUR" psql -U "$ADM_UTILISATEUR" -v ON_ERROR_STOP=1 -q "$@"; }

appliquer() {  # $1 = motif, $2 = remplaçant (vides : 065 intacte) ; exit ≠ 0 si une migration lève
  psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH;" >/dev/null 2>&1 \
    || { echo "ERREUR : base jetable"; return 2; }
  for f in 063_v3_emetteurs_et_chef_de_dossier 064_v3_recueil; do
    psql_adm -d "$SCRATCH" < "app/db/migrations/$f.sql" >/dev/null 2>&1 || { echo "ERREUR : $f préalable"; return 2; }
  done
  python3 -c "
import sys, pathlib
s = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
if sys.argv[2] and sys.argv[2] not in s:
    sys.exit(3)
sys.stdout.write(s.replace(sys.argv[2], sys.argv[3], 1) if sys.argv[2] else s)
" "$SQL" "$1" "$2" > /tmp/065_mutee.sql || { echo "MOTIF INTROUVABLE"; return 3; }
  psql_adm -d "$SCRATCH" < /tmp/065_mutee.sql 2>&1
}

echo "── 1. le code du rangement, muté (base jetable $SCRATCH, 063-065 intactes)"
appliquer "" "" >/dev/null || { echo "FAIL la base jetable ne se prépare pas"; exit 1; }
export CHECK_DB_URL="$SCRATCH_URL"
mutations=(
# [P1] les lignes rangées ne sont plus celles lues (relevé : une pièce au milieu d'un texte de trois
# lignes ne le voyait pas — d'où la comparaison directe des lignes).
"$KD¦lec[\"empreinte\"], lec[\"lecteur\"], list(lignes))¦lec[\"empreinte\"], lec[\"lecteur\"], list(lignes)[::-1])¦les lignes de chaque lecture : identiques en base"
# [K5] un doublon se dit « rangé » : la seconde citation rend une pièce neuve au lieu de la première.
"$KD¦        return ecrit is not None¦        return True¦[K5] citée deux fois : la même pièce"
# [P5] le JSON n'est plus passé en texte : avec le codec du service, il serait encodé deux fois.
"$KD¦VALUES (\$1, \$2, \$3, \$4::text::jsonb) \"¦VALUES (\$1, \$2, \$3, \$4::jsonb) \"¦(codec JSON)"
# [P1] l'ordre de la langue de la base au lieu de celui de Python.
"$TD¦ORDER BY dossier COLLATE \\\"C\\\"¦ORDER BY dossier¦[P1] les études se lisent dans le même ordre"
# [P1] le journal relu à l'envers : le « dernier passage » serait le premier.
"$TD¦WHERE dossier = \$1 ORDER BY rang\", dossier)¦WHERE dossier = \$1 ORDER BY rang DESC\", dossier)¦[P1] etudes : identique en base et en mémoire"
# [K10] l'état du dossier et ce qu'il lance ne sont plus rangés ensemble : seul le ROLLBACK de la base
# retirait les demandes écrites avant le refus.
"app/modules/etude/coeur.py¦        async with monde.transaction():  # ensemble ou pas du tout¦        if True:  # ensemble ou pas du tout¦[K10] état refusé : aucune demande de collecte en base"
# [P2] le caractère nul n'est plus remplacé : la base refuse de ranger la lecture.
"app/modules/connaissance/lecteur.py¦            return contenu.decode(enc).replace(\"\\x00\", \"\\ufffd\")¦            return contenu.decode(enc)¦[P2]"
# [K10] le verrou ne verrouille rien : deux passages simultanés relèvent tous deux.
"$TD¦SELECT pg_try_advisory_lock(hashtext(\$1), hashtext(\$2))¦SELECT true OR pg_try_advisory_lock(hashtext(\$1), hashtext(\$2))¦[K10] deux passages simultanés : le second ne relève rien"
# [K10] la même connexion reprend un dossier qu'elle tient (le verrou de session est réentrant).
"$TD¦        if dossier in self._tenus:¦        if False:¦[K10] une même connexion ne reprend pas"
# [K10] le verrou n'est jamais rendu : le dossier reste tenu après le passage.
"$TD¦        await self._c.fetchval(\"SELECT pg_advisory_unlock(hashtext(\$1), hashtext(\$2))\", _ESPACE, dossier)¦        pass¦[K10] le passage fini, il ne tient plus aucun verrou"
)
source "$(dirname "$0")/_negatif.sh"
( run_mutations ); partie1=$?

echo
echo "── 2. la migration 065, mutée (base jetable $SCRATCH)"
ok=0; ko=0
lancer_check() {
  docker run --rm --network "$NET" -v "$PWD:/app:ro" -w /app -e PYTHONPATH=/app -e PYTHONDONTWRITEBYTECODE=1 \
    --env-file checks/env.checks -e "CHECK_DB_URL=$SCRATCH_URL" "$IMG" python "$CHECK" 2>&1
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
se_refuse() {  # la migration mutée doit LEVER par sa garde [065/K1]
  local out
  if out=$(appliquer "$1" "$2"); then echo "  FAIL $3 — la migration mutée s'applique"; ko=$((ko+1))
  elif printf '%s' "$out" | grep -q '065/K1'; then echo "  ok   $3"; ok=$((ok+1))
  else echo "  FAIL $3 — refusée, mais pas par [065/K1] : $(printf '%s' "$out" | tail -1)"; ko=$((ko+1)); fi
}
if out=$(appliquer "" "") && out=$(lancer_check); then echo "  ok   [sat] la 065 non mutée : contrôle vert"; ok=$((ok+1))
else echo "  FAIL [sat] la 065 non mutée ne passe pas : $(printf '%s' "$out" | tail -2)"; ko=$((ko+1)); fi
for t in connaissance_lectures connaissance_lignes connaissance_pieces etude_etudes etude_passages; do
  n=$(psql_adm -d "$SCRATCH" -tA -c "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'public.$t'::regclass AND tgname = '${t}_immuable'")
  if [ "$n" = "1" ]; then echo "  ok   [P3] $t : le trigger d'ajout seul est posé"; ok=$((ok+1))
  else echo "  FAIL [P3] $t : trigger d'ajout seul absent"; ko=$((ko+1)); fi
done

rougit "    empreinte     text        NOT NULL REFERENCES public.recueil_documents (empreinte)," \
       "    empreinte     text        NOT NULL," \
       "[P4] une lecture d'un document jamais collecté : refusée par la base"
rougit "    FOREIGN KEY (empreinte, lecteur) REFERENCES public.connaissance_lectures (empreinte, lecteur),

    CONSTRAINT connaissance_pieces_texte" \
       "
    CONSTRAINT connaissance_pieces_texte" \
       "[P4] une pièce d'une lecture qui n'existe pas : refusée par la base"
se_refuse "GRANT SELECT, INSERT ON public.connaissance_lectures" \
          "GRANT SELECT, INSERT, UPDATE ON public.connaissance_lectures" \
          "[065/K1] un registre réécrivable par le service : la migration se refuse"

psql_adm -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH;" >/dev/null 2>&1
rm -f /tmp/065_mutee.sql
echo
echo "============================================================"
echo "partie 2 : $ok ok / $ko FAIL"
[ "$partie1" -eq 0 ] && [ "$ko" -eq 0 ] || exit 1
