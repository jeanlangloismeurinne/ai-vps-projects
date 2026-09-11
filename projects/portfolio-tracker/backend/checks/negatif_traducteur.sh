#!/usr/bin/env bash
# TEST NÉGATIF de `check_traducteur.py` — BIDIRECTIONNEL (moitié déterministe du traducteur).
#
#   0. SATISFIABILITÉ — le check non muté est vert ;
#   puis une MUTATION PAR GARDE, chacune exigeant : (1) exit ≠ 0, (2) le FAIL sur l'assert NOMMÉ,
#   (3) la ligne de bilan atteinte (mêmes trois conditions que les autres négatifs).
#
#   bash checks/negatif_traducteur.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/traducteur.py"
CHECK="checks/check_traducteur.py"

run_check() {  # $1 = racine backend à monter
  docker run --rm --network none -v "$1:/app:ro" \
    -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
    "$IMG" python "$CHECK" 2>&1
}

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation : rien ne peut être prouvé"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# fichier ¦ motif remplacé ¦ remplaçant ¦ assert (fragment de LABEL) qui rougit — backticks échappés
mutations=(
"$SRC¦.mode == \"variable\"]¦.mode in (\"variable\", \"sans_objet\")]¦qf_1 (rendement du capital) est ABSENT"
"$SRC¦                \"variable_archetype\": q.variables_par_archetype[archetype].variable,¦                \"variable_archetype\": q.variables_par_archetype[archetype].variable,\n                \"plancher_tier\": q.plancher_tier,¦ne contient pas \`plancher_tier\`"
"$SRC¦    items: list[CollectionPlanItem] = Field(min_length=1)¦    items: list[CollectionPlanItem] = Field(min_length=1)\n    ticker_id: str = \"x\"¦n'a QUE"
"$SRC¦        framework_version=fichier.schema_version,¦        framework_version=archetype,¦pose lui-même"
"$SRC¦    if archetype not in set(fichier.archetypes):¦    if False:¦[O-tôt] archétype inconnu"
"$SRC¦    valider_pont_collection_plan(plan, fichier=fichier)¦    None  # pont retiré¦passe le plan au pont"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/.git" 2>/dev/null
  find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  cible="$tmp/backend/$fichier"

  if ! python3 -c "
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
vieux, neuf = sys.argv[2], sys.argv[3].replace('\\\\n', chr(10))
if vieux not in s:
    print('MOTIF INTROUVABLE'); sys.exit(1)
p.write_text(s.replace(vieux, neuf, 1), encoding='utf-8')
" "$cible" "$vieux" "$neuf"; then
    printf '  ?? %-58.58s MUTATION CADUQUE (motif absent du source)\n' "$attendu"
    ratees=$((ratees + 1)); rm -rf "$tmp"; continue
  fi

  out=$(run_check "$tmp/backend"); rc=$?
  rm -rf "$tmp"

  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK')
  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F "$attendu")

  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan (2ᵉ faux vert)\n' "$attendu"
    printf '%s\n' "$out" | tail -4
    ratees=$((ratees + 1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"
    ratees=$((ratees + 1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
    printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'
    ratees=$((ratees + 1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"
    passes=$((passes + 1))
  fi
done

echo
echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s)"
[ "$ratees" -eq 0 ] || exit 1
