#!/usr/bin/env bash
# TEST NÉGATIF de `check_appariement_persist.py` — BIDIRECTIONNEL, réseau coolify requis.
#
#   0. SATISFIABILITÉ — le check non muté est VERT. Une acceptation écrite avant sa capacité doit
#      d'abord prouver qu'elle PEUT virer au vert ; toute mutation appliquée sur un check déjà
#      cassé ne prouve rien (`feedback_acceptation_rouge_bidirectionnelle`).
#   1. DISCRIMINATION — UNE MUTATION PAR GARDE, chacune exigeant les trois conditions :
#        exit ≠ 0, FAIL sur l'assert NOMMÉ (pas un autre), bilan ATTEINT.
#
#   Deux familles de mutations :
#     · SRC (`appariement_persist.py`) — on neutralise une garde CODE (revérification à la
#       lecture, unicité UPSERT) et on vérifie que le check rougit sur l'assert visé.
#     · CHECK (`check_appariement_persist.py`) — on rend licite une insertion que la base doit
#       refuser (§4 gardes SQL) : la base ACCEPTE alors, et `_rejette` doit rougir. C'est la
#       preuve que la §4 discrimine, pas seulement qu'elle passe.
#
#   Tout tourne dans une transaction ROLLBACK — AUCUN résidu en base.
#   Exige le réseau `coolify` + `CHECK_DB_URL`.
#     bash checks/negatif_appariement_persist.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/appariement_persist.py"
CHECK="checks/check_appariement_persist.py"
DBURL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2-)

run_check() { docker run --rm --network coolify -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks -e "CHECK_DB_URL=$DBURL" "$IMG" python "$CHECK" 2>&1; }

# ── 0. SATISFIABILITÉ ──────────────────────────────────────────────────────────
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# ── 1. MUTATIONS ───────────────────────────────────────────────────────────────
# Format : fichier|vieux|neuf|assert attendu  (séparateur ¦ U+00A6)
# L'`assert attendu` est cherché dans la LIGNE DE FAIL (libellé du label check()), pas dans le
# message d'exception. Un motif copié du `raise` serait invisible quand la mutation fait ACCEPTER.
mutations=(
# §2 — revérification à la lecture (#54) : supprimer le test de péremption → la carte périmée
# est renvoyée comme valide, et l'assert §2 doit rougir.
'app/agents/v2/appariement_persist.py¦    if row["dernier_depot_vu"] < depot_courant:¦    if False:  # mutation: supprime la revérification¦carte périmée — #54'

# §2bis — la comparaison STRICTE (`<`) rendue non-stricte (`<=`) : une carte sur le même dépôt
# est traitée comme périmée, inutilement recalculée → l'assert §2bis rougit.
'app/agents/v2/appariement_persist.py¦    if row["dernier_depot_vu"] < depot_courant:¦    if row["dernier_depot_vu"] <= depot_courant:  # mutation¦revérification strictement <'

# §3 — on casse l'UPSERT : DO UPDATE SET ... → DO NOTHING, donc le second appel ne met pas à
# jour la ligne et retourne None (RETURNING id ne correspond à aucune ligne modifiée).
# L'assert "second persister_carte rend un id" rougit car isinstance(None, int) est False.
'app/agents/v2/appariement_persist.py¦        ON CONFLICT (ticker_id, framework_id, framework_version) DO UPDATE\n            SET dernier_depot_vu = EXCLUDED.dernier_depot_vu,\n                items             = EXCLUDED.items,\n                updated_at        = now()¦        ON CONFLICT (ticker_id, framework_id, framework_version) DO NOTHING¦second persister_carte sur même clef rend un id'

# §4a — on remplace l'array vide (qui viole items_non_vide) par [1] qui satisfait la contrainte
# (longueur > 0) : la base ACCEPTE l'insertion, et `_rejette` doit rougir.
"checks/check_appariement_persist.py¦\"VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '2025-01-01', '[]'::jsonb)\")¦\"VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '2025-01-01', '[1]'::jsonb)\")¦base REFUSE items JSON vide"

# §4b — on rend le format de date valide dans l'insertion de test : la base ACCEPTE la ligne
# interdite, et `_rejette` doit rougir sur "base REFUSE dernier_depot_vu au mauvais format".
"checks/check_appariement_persist.py¦\"VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '20250101', \"¦\"VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '2025-01-01', \"¦base REFUSE dernier_depot_vu au mauvais format"
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
vieux = sys.argv[2].replace('\\\\n', chr(10))
neuf  = sys.argv[3].replace('\\\\n', chr(10))
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
