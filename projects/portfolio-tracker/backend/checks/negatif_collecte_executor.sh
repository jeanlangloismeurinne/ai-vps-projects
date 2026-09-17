#!/usr/bin/env bash
# TEST NÉGATIF de `check_collecte_executor.py` — BIDIRECTIONNEL.
#   0. SATISFIABILITÉ (le check non muté est vert) ; puis une MUTATION PAR GARDE, chacune exigeant
#      exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte.
#   bash checks/negatif_collecte_executor.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/collecte_executor.py"
CHECK="checks/check_collecte_executor.py"

run_check() { docker run --rm --network none -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1; }

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

# Chaque mutation désarme UNE garde ; l'assert nommé (attendu) doit rougir.
mutations=(
# §2 ─ le véto `_est_derivee` : le retirer laisse FCF mapper sur operating_cash_flow → edgar
"$SRC¦    if _est_derivee(_norm(metrique)):¦    if False:  # mutation: supprime le véto dérivée¦FCF ≠ OCF"
# §1 ─ le filtre source SEC : le retirer laisse un communiqué aller chez EDGAR
'app/agents/v2/collecte_executor.py¦    if not _FORME_SEC.search(_norm(ligne.source_pressentie)):\n        return "web"¦    if False:  # mutation: supprime le filtre source SEC\n        return "web"¦le poste est juste, mais la source pressentie'
# §1 ─ le filtre catalogue POSTES : le retirer laisse `ebitda` (inventé) aller chez EDGAR
"$SRC¦    if not poste or poste not in _TOUS_POSTES:¦    if not poste:  # mutation: retire le filtre catalogue¦hors catalogue"
# §4 ─ la déduction de type d'entry : la supprimer → tout devient fact_qualitative
"$SRC¦    if any(j in n for j in _JETONS_FINANCIERS):¦    if False:¦trimestrielle (cash burn)"
# §5 ─ reliability_min permissif : le durcir → le check detect la violation
"$SRC¦        reliability_min=0.40,¦        reliability_min=0.85,¦le collecteur ne juge pas la valeur"
# §5 ─ field_path absent : en injecter un → ré-ancrerait la question
"$SRC¦        output_schema=OutputSchema(entry_type=entry_type_pour_metrique(ligne.metrique)),¦        output_schema=OutputSchema(entry_type=entry_type_pour_metrique(ligne.metrique), field_path=\"qf_1.revenue\"),¦ancrerait la question"
# §6 ─ la porte d'erreur générique : la restreindre → l'exception propage
"$SRC¦    except Exception as e:  # timeout fournisseur / sortie non conforme / réseau → #25, jamais un crash¦    except KeyboardInterrupt as e:  # timeout fournisseur / sortie non conforme / réseau → #25, jamais un crash¦jamais une exception qui tue le lot"
# §7 ─ le câblage carte : court-circuiter le check `indisponible` → la carte est ignorée
'app/agents/v2/collecte_executor.py¦        return "web" if carte_statut == "indisponible" else "edgar"¦        return "edgar"  # mutation: ignore carte_statut indisponible¦l'"'"'inventaire n'"'"'a pas le concept'
# §7 ─ le câblage carte : court-circuiter la branche `carte_statut is not None` avec `if False:`
# → repli sur poste_retenu() même avec une carte `exact` → le check rougit (pas de poste passé)
'app/agents/v2/collecte_executor.py¦    if carte_statut is not None:¦    if False:  # mutation: désactive la branche carte_statut¦court-circuite poste_retenu'
# §8 ─ le câblage dans COLLECTER_UN : retirer carte_statut du router_source → le chemin de production
# ignore la carte. Une ligne `indisponible` part à EDGAR au lieu du web — §8 rougit.
"$SRC¦    route = router_source(ligne, carte_statut=carte_statut)¦    route = router_source(ligne)  # mutation: carte_statut non passé à router_source¦carte \`indisponible\` : la même ligne prend le chemin WEB"
# §9 ─ LA RÉGRESSION QU'ON VIENT DE CORRIGER, REFABRIQUÉE À L'IDENTIQUE : l'exécuteur repuise la
# date de revérification dans la table de la carte et la repasse à `lire_carte`. La comparaison
# devient `X < X`, donc toujours fausse — le code REDEVIENT vert fonctionnellement, aucun test de
# routage ne bouge, et c'est exactement pour ça que la garde doit être STRUCTURELLE. Deux mutations,
# parce que les deux moitiés se réintroduisent séparément : la sentinelle remplacée par une date lue,
# et le `SELECT` qui la fournit.
"$SRC¦            depot_courant=_SANS_REVERIFICATION,¦            depot_courant=\"2026-06-30\",  # mutation: une date plausible au lieu de l'aveu¦est la SENTINELLE nommée"
"$SRC¦        carte = await lire_carte(¦        await conn.fetchrow(\"SELECT dernier_depot_vu FROM appariement_cartes WHERE ticker_id = \$1\", plan.ticker_id)\n        carte = await lire_carte(¦n'émet AUCUN \`SELECT\` sur \`appariement_cartes\`"
# §9 ─ la sentinelle dégradée en date plausible : elle cesse d'avouer, et `<` peut redevenir vraie.
"$SRC¦_SANS_REVERIFICATION = \"0000-00-00 (aucune date de dépôt courante : âge non revérifié ici)\"¦_SANS_REVERIFICATION = \"1970-01-01\"¦plus petite que toute date ISO"
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
