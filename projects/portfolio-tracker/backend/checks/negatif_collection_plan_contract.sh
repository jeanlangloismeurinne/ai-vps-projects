#!/usr/bin/env bash
# TEST NÉGATIF de `check_collection_plan_contract.py` — BIDIRECTIONNEL.
#
# POURQUOI CE FICHIER EST VERSIONNÉ, ET PAS DANS /tmp. Un check neuf n'est éprouvé qu'après avoir
# viré au ROUGE au moins une fois : tant qu'il n'a jamais rougi, « 22 vérifications OK » ne
# distingue pas un contrat solide d'un fichier d'asserts qui ne mesurent rien.
#
# BIDIRECTIONNEL, dans l'ordre (`feedback_acceptation_rouge_bidirectionnelle`) :
#   0. SATISFIABILITÉ — le check NON muté est vert. Sans cette preuve, « rouge sur chaque mutation »
#      pourrait n'être qu'un check cassé qui rougit sur tout ;
#   puis une MUTATION PAR GARDE du validateur, chacune exigeant les trois conditions :
#     1. le check sort en ÉCHEC (exit ≠ 0) ;
#     2. l'assert ATTENDU, nommé, porte le FAIL — pas un autre (4ᵉ faux vert : l'assert à côté) ;
#     3. le script atteint quand même sa ligne de BILAN (2ᵉ faux vert : script mort avant ses asserts).
#
# ⚠️ Une mutation qui retire une garde fait ACCEPTER l'objet que le cas `rejete()` visait : le FAIL
# porte alors le LABEL du cas, pas le message du contrat. Les `attendu` ci-dessous sont donc des
# fragments de LABELS.
#
#   bash checks/negatif_collection_plan_contract.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/contracts/collection_plan_schema.py"
PONT="app/agents/v2/frameworks.py"
CHECK="checks/check_collection_plan_contract.py"

run_check() {  # $1 = racine backend à monter
  docker run --rm --network none -v "$1:/app:ro" \
    -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
    "$IMG" python "$CHECK" 2>&1
}

# ── 0. satisfiabilité : le check non muté DOIT être vert ────────────────────────────────────────
base=$(run_check "$PWD"); base_rc=$?
base_bilan=$(printf '%s' "$base" | grep -E 'vérifications OK')
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation : rien ne peut être prouvé"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$base_bilan"

# ── Les mutations : fichier ¦ motif remplacé ¦ remplaçant ¦ assert (fragment de LABEL) qui rougit ─
# Chaque mutation défait UNE garde et une seule. Les `("metrique", self.metrique)` du bloc `traduit`
# précèdent ceux du bloc `inobtenable` : `.replace(..., 1)` vise donc bien l'obligation, pas
# l'interdiction. Backticks échappés (\`) — sinon le shell les prendrait pour une substitution.
mutations=(
"$SRC¦(\"metrique\", self.metrique),¦(\"metrique\", \"present\"),¦'traduit' sans \`metrique\`"
"$SRC¦(\"source_pressentie\", self.source_pressentie),¦(\"source_pressentie\", \"present\"),¦'traduit' sans \`source_pressentie\`"
"$SRC¦(\"ancre\", self.ancre)) if not val]¦(\"ancre\", \"present\")) if not val]¦'traduit' sans \`ancre\`"
"$SRC¦            if self.motif:¦            if False:¦'traduit' qui porte un \`motif\`"
"$SRC¦            if not self.motif:¦            if True is False:¦'inobtenable' sans \`motif\`"
"$SRC¦            if porte:¦            if False and porte:¦'inobtenable' qui porte une \`metrique\`"
"$SRC¦        default=None, min_length=3,¦        default=None, min_length=1,¦\`metrique\` trop courte"
"$SRC¦        if len(set(couples)) != len(couples):¦        if False:¦deux lignes sur le même"
"$SRC¦    statut: Literal[\"traduit\", \"inobtenable\"]¦    statut: Literal[\"traduit\", \"inobtenable\"]\n    plancher_tier: Optional[str] = None¦l'absence est structurelle"
# ── le PONT (§6) — les invariants relationnels que le contrat NE PEUT PAS voir (#37) ────────────
"$PONT¦    if fw is None:¦    if False:¦[N] framework inconnu"
"$PONT¦    if plan.framework_version != fichier.schema_version:¦    if False:¦[N] version divergente"
"$PONT¦    if plan.archetype not in set(fichier.archetypes):¦    if False:¦[O] archétype non déclaré"
"$PONT¦        if q is None:¦        if False:¦[P] question absente"
"$PONT¦        if it.ingredient_id not in ingredients:¦        if False:¦[P] ingrédient inventé"
"$PONT¦        if q.variables_par_archetype[plan.archetype].mode == \"sans_objet\":¦        if False:¦[Q] question SANS OBJET"
"$PONT¦            if i.essentiel and (q.id, i.id) not in couples:¦            if False:¦[R] essentiel omis"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/.git" 2>/dev/null
  # Purge de TOUS les __pycache__ : une invalidation `(mtime, size)` est aveugle à une édition
  # même-taille en conteneur, et le runtime exécuterait alors l'ancien .pyc (`feedback_pycache_faux_vert`).
  find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  cible="$tmp/backend/$fichier"

  # Mutation par python (pas `sed`) : elle DOIT échouer bruyamment si le motif a disparu, sinon une
  # mutation caduque se lirait « le check a rougi » pour une tout autre raison.
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
