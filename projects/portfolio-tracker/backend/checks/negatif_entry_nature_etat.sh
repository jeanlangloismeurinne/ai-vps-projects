#!/usr/bin/env bash
# TEST NÉGATIF de `check_entry_nature.py` §7 (ÉTAT PERSISTÉ) — le seul point de lecture réel.
#
#   bash checks/negatif_entry_nature_etat.sh
#
# POURQUOI CE TEST EXISTE. §7 a été re-mesuré le 2026-09-12 : l'ancien `== 13` (décompte du banc
# d'essai promu en cible, interdit par §0.6) est remplacé par l'invariant #51 sur l'état —
# « tout fait à RECETTE DÉTERMINISTE (un `metric` dans `content_structured`) est `mesure` », plus
# une garde de non-vacuité. Un assert re-mesuré n'est ACQUIS qu'après avoir viré au ROUGE pour la
# bonne raison (`feedback_test_negatif_obligatoire`) : quatre asserts jamais mis en défaut se lisent
# comme un dispositif et ne sont qu'un décor.
#
# LES DEUX SENS (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — la base non mutée passe (exit 0). Sans ça, quatre rouges prouveraient
#     seulement que §7 ne peut jamais être vert.
#   · DISCRIMINATION — une mutation PAR ASSERT, et c'est l'assert VISÉ qui rougit, nommé dans le
#     message. Un rouge sur un autre assert ne prouve rien de celui qu'on croyait éprouver
#     (3ᵉ faux vert : l'assert à côté de son point de lecture).
#
# LA FIXTURE EST COPIÉE DU RÉEL (`feedback_fixture_copiee_du_reel`) : la base scratch est un
# `pg_dump` de `db_portfolio`, jamais un schéma fabriqué. Une fixture plus favorable que la prod
# serait aveugle au vert — et la satisfiabilité ci-dessus prouve qu'elle est fidèle ET discriminante.
#
# ⚠️ Jamais `psql << EOF` via `docker exec` : ça échoue EN SILENCE. `docker cp` n'est pas requis ici
# (les mutations sont des `-c` courts), mais la même prudence vaut : `-v ON_ERROR_STOP=1`.
set -u
cd "$(dirname "$0")/.." || exit 1

PG=shared-postgres
SRC=db_portfolio
TPL=db_entrynat_tpl
SCRATCH=db_entrynat_neg
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
# L'URL scratch = celle de prod, nom de base échangé. `portfolio_user` a déjà ses GRANT (le dump les
# porte) et CONNECT est public par défaut sur une base neuve — pas besoin de credentials admin côté
# client. Le check strippe `+asyncpg` lui-même.
BASEURL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)
SCRATCHURL=${BASEURL/\/$SRC/\/$SCRATCH}

psql_adm() { docker exec "$PG" psql -U admin -d postgres -v ON_ERROR_STOP=1 -q "$@"; }
psql_mut() { docker exec "$PG" psql -U admin -d "$SCRATCH" -v ON_ERROR_STOP=1 -q "$@"; }

OUTFILE=$(mktemp)
RC=0
run_check() {  # écrit la sortie dans $OUTFILE et le rc dans $RC (jamais via $(...), qui masque $?)
  docker run --rm --network coolify -v "$PWD:/app:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
        -e CHECK_DB_URL="$SCRATCHURL" "$IMG" python checks/check_entry_nature.py > "$OUTFILE" 2>&1
  RC=$?
}

reset_scratch() {  # scratch = copie fraîche du gabarit, avant chaque scénario
  psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "CREATE DATABASE $SCRATCH TEMPLATE $TPL;" || exit 1
}

# ── Le gabarit : une copie du réel, faite UNE fois ────────────────────────────────────────────
echo "── fixture : copie de $SRC vers le gabarit $TPL"
psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" -c "CREATE DATABASE $TPL;" || exit 1
docker exec "$PG" sh -c "pg_dump -U admin -d $SRC | psql -U admin -q -d $TPL" >/dev/null 2>&1 || {
  echo "ERREUR : la restauration du gabarit a échoué"; exit 1; }
lignes=$(docker exec "$PG" psql -U admin -d "$TPL" -tAc "SELECT count(*) FROM knowledge_entries")
echo "   gabarit prêt · knowledge_entries = $lignes lignes"
[ "${lignes:-0}" -gt 0 ] || { echo "ERREUR : gabarit VIDE — un test sur zéro ligne est vert par dégénérescence"; exit 1; }

# ── SATISFIABILITÉ ────────────────────────────────────────────────────────────────────────────
reset_scratch
run_check; sortie=$(cat "$OUTFILE")
if [ "$RC" -eq 0 ]; then
  echo "  ok   satisfiabilité — la base non mutée passe (exit 0)"
  sat_ok=1; sat_ko=0
else
  echo "  FAIL satisfiabilité — la base non mutée ROUGIT, la fixture n'est pas fidèle :"
  printf '%s\n' "$sortie" | grep -E 'FAIL|Error|Traceback' | head -5 | sed 's/^/         /'
  sat_ok=0; sat_ko=1
fi

# ── DISCRIMINATION : une mutation par assert de §7 ────────────────────────────────────────────
# Format : label¦substring-attendu-dans-le-FAIL¦SQL-de-mutation
mutations=(
"nature NULL¦aucune entry active sans¦ALTER TABLE knowledge_entries ALTER COLUMN nature DROP NOT NULL; UPDATE knowledge_entries SET nature=NULL WHERE id=(SELECT id FROM knowledge_entries WHERE superseded_by IS NULL ORDER BY id LIMIT 1);"
"nature hors vocab¦hors vocabulaire¦ALTER TABLE knowledge_entries DROP CONSTRAINT knowledge_entries_nature_check; UPDATE knowledge_entries SET nature='bidon' WHERE id=(SELECT id FROM knowledge_entries WHERE superseded_by IS NULL ORDER BY id LIMIT 1);"
"vacuité déterministe¦il existe des faits à recette déterministe¦UPDATE knowledge_entries SET content_structured = content_structured - 'metric' WHERE content_structured ? 'metric';"
"invariant #51¦est \`mesure\`¦UPDATE knowledge_entries SET nature='interpretation' WHERE id=(SELECT id FROM knowledge_entries WHERE superseded_by IS NULL AND entry_type IN ('fact_financial','fact_statistical') AND content_structured->>'metric' IS NOT NULL ORDER BY id LIMIT 1);"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r label attendu sql <<< "$m"
  reset_scratch
  if ! psql_mut -c "$sql" >/dev/null 2>&1; then
    printf '  FAIL %-22s la mutation SQL a échoué — scénario caduc\n' "$label"
    ratees=$((ratees+1)); continue
  fi
  run_check; sortie=$(cat "$OUTFILE")
  vise=$(printf '%s' "$sortie" | grep -E '^\s*FAIL' | grep -F "$attendu")
  if [ "$RC" -eq 0 ]; then
    printf '  FAIL %-22s §7 VERT malgré la mutation — cet assert ne garde rien\n' "$label"
    ratees=$((ratees+1))
  elif [ -z "$vise" ]; then
    printf '  FAIL %-22s rouge, mais PAS sur l'\''assert visé :\n' "$label"
    printf '%s\n' "$sortie" | grep -E '^\s*FAIL' | head -3 | sed 's/^/         /'
    ratees=$((ratees+1))
  else
    printf '  ok   %-22s %s\n' "$label" "$(printf '%s' "$vise" | head -1 | sed 's/^ *//' | cut -c1-70)"
    passes=$((passes+1))
  fi
done

psql_adm -c "DROP DATABASE IF EXISTS $SCRATCH;" -c "DROP DATABASE IF EXISTS $TPL;" >/dev/null 2>&1

echo
echo "============================================================"
echo "satisfiabilité : $sat_ok ok / $sat_ko FAIL · discrimination : $passes ok / $ratees FAIL"
[ "$sat_ko" -eq 0 ] && [ "$ratees" -eq 0 ] || exit 1
rm -f "$OUTFILE"
