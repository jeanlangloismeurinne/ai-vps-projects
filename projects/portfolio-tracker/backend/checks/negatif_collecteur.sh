#!/usr/bin/env bash
# TEST NÉGATIF de `check_collecteur.py` — BIDIRECTIONNEL.
#   0. SATISFIABILITÉ (le check non muté est vert) ; puis une MUTATION PAR GARDE, chacune exigeant
#      exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte.
#   bash checks/negatif_collecteur.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/collecteur.py"
CHECK="checks/check_collecteur.py"

run_check() { docker run --rm --network none -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1; }

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

mutations=(
"$SRC¦    ticker_id: str = Field(min_length=1)¦    ticker_id: str = Field(min_length=1)\n    question_id: str = \"x\"¦ne déclare aucun champ de question"
"$SRC¦        if (self.entry_id is None) == (self.echec is None):¦        if False:¦les deux à la fois"
"$SRC¦                   question_id=item.question_id, ingredient_id=item.ingredient_id)¦                   question_id=item.ingredient_id, ingredient_id=item.ingredient_id)¦clefé par la"
"$SRC¦origine=\"inobtenable\"))¦origine=\"echec_collecte\"))¦d'origine \`inobtenable\`"
"$SRC¦            res.mandats.append(MandatCollecte(**cle, motif=rc.echec, origine=\"echec_collecte\"))¦            pass  # évaporation¦ligne ne s'évapore"
"$SRC¦    entry_id: int¦    entry_id: int\n    colonne_en_trop: str = \"x\"¦EXACTEMENT les colonnes"
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
