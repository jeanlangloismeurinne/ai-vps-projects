#!/usr/bin/env bash
# TEST NÉGATIF de `check_manager_persist.py` — BIDIRECTIONNEL, et il touche la BASE.
#   0. SATISFIABILITÉ (le check non muté est vert) ; puis une MUTATION PAR GARDE, chacune exigeant
#      exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte.
#   Deux familles :
#     · SRC (`manager_persist.py`) — on casse l'idempotence, la garde de non-re-consommation, les
#       entries produites, ou on fait fuiter un servi dans `read_open_mandates` — et la relecture
#       rougit sur l'assert visé ;
#     · CHECK (`check_manager_persist.py` §5) — on rend LICITE l'insertion que la base doit refuser
#       (dernier rempart) : la base ACCEPTE alors, et `_rejette` doit rougir. Preuve que §5
#       discrimine, pas seulement qu'elle passe.
#   Exige le réseau `coolify` + `CHECK_DB_URL` : tout tourne dans une transaction ROLLBACK, AUCUN
#   résidu en base.
#   bash checks/negatif_manager_persist.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/manager_persist.py"
CHECK="checks/check_manager_persist.py"
DBURL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)

run_check() { docker run --rm --network coolify -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks -e "CHECK_DB_URL=$DBURL" "$IMG" python "$CHECK" 2>&1; }

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

mutations=(
"$SRC¦        if existant is not None:¦        if existant is not None and False:¦un seul mandat ouvert sur qf_5"
"$SRC¦        \"consomme_at = now(), entry_ids_produits = \$4 WHERE id = \$1 AND statut = 'ouvert'\",¦        \"consomme_at = now(), entry_ids_produits = \$4 WHERE id = \$1\",¦un mandat déjà servi ne se re-sert pas"
"$SRC¦        mandate_id, statut_avant, statut_apres, entry_ids_produits)¦        mandate_id, statut_avant, statut_apres, [])¦l'après, l'instant et les entries"
"$SRC¦        \"AND origine IN ('manager_renvoi', 'comite') AND statut = 'ouvert' ORDER BY id\",¦        \"AND origine IN ('manager_renvoi', 'comite') AND statut IN ('ouvert','servi') ORDER BY id\",¦seul le mandat manager ouvert (qf_5) est rendu"
"$CHECK¦'inventee', 'ouvert', \$3, 'md')\", FW, FV, ticker)¦'comite', 'ouvert', \$3, 'md')\", FW, FV, ticker)¦hors vocabulaire fermé est REFUSÉE"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/.git" 2>/dev/null
  find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

  if ! python3 -c "
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
vieux, neuf = sys.argv[2], sys.argv[3].replace('\\\\n', chr(10))
if vieux not in s:
    print('MOTIF INTROUVABLE'); sys.exit(1)
p.write_text(s.replace(vieux, neuf, 1), encoding='utf-8')
" "$tmp/backend/$fichier" "$vieux" "$neuf"; then
    printf '  ?? %-58.58s MUTATION CADUQUE (motif absent du source)\n' "$attendu"
    ratees=$((ratees + 1)); rm -rf "$tmp"; continue
  fi

  out=$(run_check "$tmp/backend"); rc=$?
  rm -rf "$tmp"
  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK')
  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F "$attendu")

  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan\n' "$attendu"
    printf '%s\n' "$out" | tail -4; ratees=$((ratees + 1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"; ratees=$((ratees + 1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
    printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'; ratees=$((ratees + 1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"; passes=$((passes + 1))
  fi
done

echo; echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s)"
[ "$ratees" -eq 0 ] || exit 1
