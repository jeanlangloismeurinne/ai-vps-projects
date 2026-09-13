#!/usr/bin/env bash
# TEST NÉGATIF de `check_architecture.py` — une mutation STRUCTURELLE par invariant.
#
# Contrairement aux autres negatif_*.sh (mutations de TEXTE dans un source), les invariants d'archi
# se cassent par des opérations de FICHIER (supprimer un doc, ajouter un orphelin, salir roadmap/).
# Mêmes trois exigences : (1) exit ≠ 0 ; (2) l'assert ATTENDU, nommé, porte le FAIL ; (3) le script
# atteint son bilan.
#
#   bash checks/negatif_architecture.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')

# mutation ¦ assert qui DOIT rougir
mutations=(
"del_doc¦doc déclaré dans la CIBLE mais absent du disque : app/api/ARCHITECTURE.md"
"add_doc_non_declare¦doc sur disque mais non déclaré dans la CIBLE : app/portfolio/ARCHITECTURE.md"
"pointeur_mort¦pointeur mort : \`check_inexistant_xyz.py\` cité par un doc"
"orphelin¦garde orpheline : \`check_bidon_xyz.py\` n'est cité par aucun"
"racine_sale¦racine roadmap/ : \`intrus.md\` hors de V3/ et archive/"
"autonomie¦autonomie /V3 : \`doctrine-trois-axes.md\` cite un ancien chemin \`roadmap/provenance-cards\`"
)

apply_mutation() {  # $1=id  $2=racine tmp (contient backend/ et roadmap/)
  local id="$1" t="$2"
  case "$id" in
    del_doc)             rm -f "$t/backend/app/api/ARCHITECTURE.md" ;;
    add_doc_non_declare) mkdir -p "$t/backend/app/portfolio"; echo "# stray" > "$t/backend/app/portfolio/ARCHITECTURE.md" ;;
    pointeur_mort)       sed -i 's/check_field_profiles\.py/check_inexistant_xyz.py/' "$t/backend/app/agents/v2/ARCHITECTURE.md" ;;
    orphelin)            echo "print('x')" > "$t/backend/checks/check_bidon_xyz.py" ;;
    racine_sale)         echo "# intrus" > "$t/roadmap/intrus.md" ;;
    autonomie)           printf '\nvoir roadmap/provenance-cards/x\n' >> "$t/roadmap/V3/doctrine-trois-axes.md" ;;
    *) return 1 ;;
  esac
}

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r id attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  cp -r ../roadmap "$tmp/roadmap" 2>/dev/null
  rm -rf "$tmp/backend/checks/__pycache__" "$tmp/backend/.git" 2>/dev/null

  if ! apply_mutation "$id" "$tmp"; then
    printf '  ?? %-58.58s MUTATION INCONNUE\n' "$attendu"; ratees=$((ratees+1)); rm -rf "$tmp"; continue
  fi

  out=$(docker run --rm --network none -v "$tmp/backend:/app:ro" -v "$tmp/roadmap:/roadmap:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
        "$IMG" python checks/check_architecture.py 2>&1)
  rc=$?
  rm -rf "$tmp"

  bilan=$(printf '%s' "$out" | grep -E 'vérifications OK')
  rouge=$(printf '%s' "$out" | grep -F 'FAIL' | grep -F "$attendu")

  if [ -z "$bilan" ]; then
    printf '  FAIL %-56.56s script MORT avant son bilan\n' "$attendu"; printf '%s\n' "$out" | tail -4; ratees=$((ratees+1))
  elif [ "$rc" -eq 0 ]; then
    printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"; ratees=$((ratees+1))
  elif [ -z "$rouge" ]; then
    printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"; printf '%s\n' "$out" | grep -F 'FAIL' | head -3 | sed 's/^/         /'; ratees=$((ratees+1))
  else
    printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"; passes=$((passes+1))
  fi
done

echo
echo "============================================================"
echo "$passes mutations correctement détectées, $ratees échec(s)"
[ "$ratees" -eq 0 ] || exit 1
