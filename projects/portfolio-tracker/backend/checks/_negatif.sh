#!/usr/bin/env bash
# HARNAIS de test négatif — DÉTENTEUR UNIQUE de la boucle de mutation (#46 appliqué à la méthode).
#
# POURQUOI CE FICHIER. La même boucle (~40 lignes) était recopiée dans chaque `negatif_*.sh` :
# appliquer une mutation, rejouer le check, classer le résultat en quatre issues, tenir le bilan.
# Une méthode recopiée re-diverge au correctif suivant — exactement ce que #46 interdit. Ici, un
# seul endroit encode les TROIS exigences d'une mutation, jamais une seule :
#   1. le check sort en ÉCHEC (exit ≠ 0) ;
#   2. l'assert ATTENDU, nommé, porte le FAIL — pas un autre (4ᵉ faux-vert : l'assert à côté) ;
#   3. le script atteint quand même sa ligne de BILAN (2ᵉ faux-vert : mort avant ses asserts).
#
# USAGE (depuis un negatif_*.sh, cwd = backend/) :
#   CHECK="checks/check_xxx.py"          # obligatoire — le check à éprouver
#   WITH_FROZEN=1                        # défaut 0 — monte ../roadmap/V3/provenance-cards en /contract_frozen
#   NET=none                             # défaut none — ou "coolify" (+ CHECK_DB_URL) pour les checks d'état
#   WITH_FRONT=1                         # défaut 0 — copie pages/ + components/ du frontend en /frontend
#   mutations=( "fichier¦vieux¦neuf¦assert attendu" … )   # FROZEN:<f> vise un doc figé, FRONT:<f> un écran
#   source "$(dirname "$0")/_negatif.sh"
#   run_mutations                        # imprime le bilan, exit 1 si une mutation échappe
#
# La mutation est appliquée par PYTHON, pas `sed` : le remplacement ÉCHOUE bruyamment si le motif
# n'existe plus, sinon une mutation caduque se lirait « le check a rougi » pour une autre raison.
#
# ⚠️ `\n` n'est converti que dans le REMPLAÇANT, pas dans le motif : un motif multi-ligne se cherche
# donc littéralement et sort en MUTATION CADUQUE. Viser une ligne unique et faire porter le
# multi-ligne au remplaçant (insérer avant/après) suffit dans tous les cas rencontrés.

run_mutations() {
  : "${CHECK:?run_mutations: CHECK (chemin du check) est requis}"
  local with_frozen="${WITH_FROZEN:-0}" net="${NET:-none}"
  local frozen_src="${FROZEN_SRC:-../roadmap/V3/provenance-cards}"
  local img; img=$(docker inspect portfolio-backend --format '{{.Config.Image}}')

  local passes=0 ratees=0 m fichier vieux neuf attendu tmp cible out rc bilan rouge
  local mounts extra
  for m in "${mutations[@]}"; do
    IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
    tmp=$(mktemp -d)
    cp -r . "$tmp/backend" 2>/dev/null
    # ⚠️ TOUS les `__pycache__`, pas seulement celui de `checks/`. Les premières mutations du
    # harnais ne portaient que sur `checks/` ; celles du lot 5 visent `app/contracts/` et
    # `app/agents/v2/`, dont le bytecode était copié dans le bac à sable. L'invalidation de Python
    # est un couple `(mtime, size)` : elle est aveugle à une édition qui ne change ni l'un ni
    # l'autre, et le conteneur exécuterait alors un AUTRE code que celui qu'on vient de muter —
    # « le check reste VERT » se lirait « ce critère ne garde rien » (`feedback_pycache_faux_vert`).
    find "$tmp/backend" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
    rm -rf "$tmp/backend/.git" 2>/dev/null
    mounts=(-v "$tmp/backend:/app:ro" -v "$PWD/../roadmap:/roadmap:ro")
    # `/frontend` (lot 6) : les écrans du parcours sont des points de lecture gardés comme du code.
    # On ne copie que `pages/` et `components/` — jamais `node_modules`.
    if [ "${WITH_FRONT:-0}" = "1" ]; then
      mkdir -p "$tmp/frontend" && cp -r ../frontend/pages ../frontend/components "$tmp/frontend/"
      mounts+=(-v "$tmp/frontend:/frontend:ro")
    fi
    if [ "$with_frozen" = "1" ]; then
      cp -r "$frozen_src" "$tmp/frozen" 2>/dev/null
      mounts+=(-v "$tmp/frozen:/contract_frozen:ro")
    fi
    extra=()
    [ "$net" = "coolify" ] && extra=(-e "CHECK_DB_URL=${CHECK_DB_URL:-}")

    cible="$tmp/backend/$fichier"
    case "$fichier" in
      FROZEN:*) cible="$tmp/frozen/${fichier#FROZEN:}" ;;
      FRONT:*)  cible="$tmp/frontend/${fichier#FRONT:}" ;;
    esac

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

    out=$(docker run --rm --network "$net" "${mounts[@]}" \
          -w /app -e PYTHONPATH=/app --env-file checks/env.checks "${extra[@]}" \
          "$img" python "$CHECK" 2>&1)
    rc=$?
    rm -rf "$tmp"

    # Bilan reconnu par sa FORME (trois dialectes historiques), comme run_all.sh.
    bilan=$(printf '%s' "$out" | grep -E 'vérifications OK|[0-9]+ ok / [0-9]+ FAIL|[0-9]+ OK / [0-9]+ KO' | tail -1)
    rouge=$(printf '%s' "$out" | grep -E 'FAIL|KO' | grep -F "$attendu")

    if [ -z "$bilan" ]; then
      printf '  FAIL %-56.56s script MORT avant son bilan (2ᵉ faux vert)\n' "$attendu"
      printf '%s\n' "$out" | tail -4; ratees=$((ratees + 1))
    elif [ "$rc" -eq 0 ]; then
      printf '  FAIL %-56.56s le check reste VERT — ce critère ne garde rien\n' "$attendu"
      ratees=$((ratees + 1))
    elif [ -z "$rouge" ]; then
      printf '  FAIL %-56.56s rouge, mais PAS sur l'\''assert visé\n' "$attendu"
      printf '%s\n' "$out" | grep -E 'FAIL|KO' | head -3 | sed 's/^/         /'; ratees=$((ratees + 1))
    else
      printf '  ok   %-56.56s rouge sur son assert · %s\n' "$attendu" "$bilan"
      passes=$((passes + 1))
    fi
  done

  echo
  echo "============================================================"
  echo "$passes mutations correctement détectées, $ratees échec(s)"
  [ "$ratees" -eq 0 ] || exit 1
}
