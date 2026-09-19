#!/usr/bin/env bash
# TEST NÉGATIF de `check_appariement_feed.py` — BIDIRECTIONNEL.
#   0. SATISFIABILITÉ (le check non muté est vert) ; puis une MUTATION PAR GARDE, chacune exigeant
#      exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte.
#   bash checks/negatif_appariement_feed.sh
#
# ⚠️ POURQUOI CERTAINES MUTATIONS VISENT `formule_grammaire.py` ET NON LE PRODUCTEUR. Deux des quatre
# refus (dimensions incohérentes, division par zéro) sont DÉLÉGUÉS à la grammaire, qui en est le
# détenteur unique (#46). Muter le producteur pour les éprouver ne dirait rien : c'est le détenteur
# qu'il faut désarmer pour savoir si le check le voit. Une garde déléguée se teste chez son détenteur.
#
# ⚠️ CE QU'AUCUNE MUTATION ICI NE PEUT MONTRER. Ce fichier éprouve la MÉCANIQUE du producteur, pas
# qu'il collecte quoi que ce soit sur un vrai émetteur. Le chiffre « lignes COLLECTÉES depuis le
# dépôt » se mesure à l'acceptation, contre l'inventaire réel — jamais ici (#71).
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/knowledge/appariement_feed.py"
GRAM="app/contracts/formule_grammaire.py"
CHECK="checks/check_appariement_feed.py"

run_check() { docker run --rm --network none -v "$1:/app:ro" -w /app -e PYTHONPATH=/app \
    --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1; }

base=$(run_check "$PWD"); base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

mutations=(
# ── §1 LES QUATRE REFUS ───────────────────────────────────────────────────────────────────────────
# Refus 1 désarmé : le calcul s'exécute alors que l'apparieur a NOMMÉ un terme manquant. Le nombre
# produit est amputé de ce terme, et il porte le tier A de ceux qui restent — le pire des deux.
"$SRC¦    if consigne.termes_web:¦    if False:  # mutation: le terme déclaré manquant est ignoré¦REFUS 1"
# Refus 2 désarmé par la TOLÉRANCE plutôt que par la branche : une tolérance de 2000 jours rend
# « commune » une ancre qui ne l'est pas. C'est la forme sournoise du défaut — la garde est toujours
# là, elle ne refuse simplement plus rien. Un solde de 2024 se soustrait à un solde de 2026.
"$SRC¦TOLERANCE_ANCRE_J = 20¦TOLERANCE_ANCRE_J = 2000  # mutation: la garde subsiste et ne refuse plus¦REFUS 2"
# Refus 3 désarmé CHEZ SON DÉTENTEUR : la dimension n'est plus calculée, donc USD + shares passe.
"$GRAM¦    return _canon(_dimension(analyser_formule(formule).body, unites, formule))¦    return ()  # mutation: plus aucun contrôle de dimension¦REFUS 3"
# Refus 4 désarmé CHEZ SON DÉTENTEUR, et de la façon la plus plausible : le ratio inexistant devient
# un zéro. « Pas de chiffre d'affaires » et « ratio nul » se mettent à se lire pareil.
"$GRAM¦        if d == 0:¦        if d == 0:\n            return 0.0  # mutation: le ratio inexistant devient un zéro¦REFUS 4"
# Le concept ABANDONNÉ : les points sans date ni valeur ne sont plus écartés, donc le motif cesse de
# nommer la cause — le mandat dira « ni exercice ni bilan » là où l'étiquette est morte.
"$SRC¦        if p.get(\"end\") is None or p.get(\"val\") is None:¦        if False:  # mutation: les points illisibles ne sont plus écartés¦signature d'une étiquette abandonnée"

# ── §2 LES CHOIX DÉTERMINISTES ────────────────────────────────────────────────────────────────────
# LE DÉPARTAGE ALPHABÉTIQUE RETIRÉ : à récence et longueur égales, `max` rend le PREMIER rencontré,
# donc le fait dépend de l'ordre d'itération d'un dict. Aucun assert de valeur ne bouge — seul le
# test de reproductibilité voit la différence, et c'est le module qui qualifie les calculs de
# déterministes qui cesse de l'être.
"$SRC¦        return (max(str(p[\"end\"]) for p in pts), len(pts), unite)¦        return (max(str(p[\"end\"]) for p in pts), len(pts))  # mutation: plus de départage¦donnent le MÊME choix quel que soit l'ordre"
# LE CADRAGE : tout est lu comme un instant. Un flux annuel devient un point de bilan, et le fait
# rapporte un trimestre là où l'on attend un exercice — sans erreur visible.
"$SRC¦    annuels = points_annuels(pts)¦    annuels = []  # mutation: plus aucun flux annuel reconnu¦lu comme un FLUX"

# ── §3 LE FAIT PRODUIT ────────────────────────────────────────────────────────────────────────────
# L'IDENTITÉ DU FAIT : le `metric` cesse d'être l'expression. Deux exécutions de la même formule
# n'écrivent plus le même `metric`, donc la seconde ne supersède plus la première : le corpus répond
# deux choses à la même question (#43).
"$SRC¦        metric=consigne.expression,¦        metric=libelle,  # mutation: l'identité du fait devient le libellé¦le \`metric\` du fait EST l'expression"
# LA PROVENANCE : le tag XBRL perd son espace de noms. « NetIncomeLoss » sans `us-gaap:` n'identifie
# plus rien d'ouvrable — la provenance redevient une promesse.
"$SRC¦            {\"concept\": p.concept, \"offset\": p.offset, \"xbrl_tag\": f\"us-gaap:{p.concept}\",¦            {\"concept\": p.concept, \"offset\": p.offset, \"xbrl_tag\": p.concept,  # mutation¦provenance est écrite CONCEPT PAR CONCEPT"
# LA DATE D'UN FAIT MIXTE : la plus ANCIENNE des deux ancres. Le fait naît vieux d'un exercice, et
# l'axe actualité — calculé à la lecture — travaillera sur une date fausse.
"$SRC¦    ancre_fait = max(dates)¦    ancre_fait = min(dates)  # mutation: le fait naît vieux¦PLUS RÉCENTE des deux ancres"
# LE CADRAGE DU FAIT : un solde de bilan déclaré flux. L'identité en base change de clef
# (`metric`+`end` au lieu de `metric`), donc les versions successives cessent de se remplacer.
"$SRC¦    flux = ancre_bilan is None                    # aucun poste de bilan → le fait est un flux pur¦    flux = True  # mutation: tout devient un flux¦marqué \`stock\` et non \`flow\`"
# LES HYPOTHÈSES effacées du structuré : l'approximation se relit comme une mesure.
"$SRC¦        \"hypotheses\": list(consigne.hypotheses),¦        \"hypotheses\": [],  # mutation: les hypothèses disparaissent¦hypothèses du calcul voyagent AVEC le fait"

# ── §4 LE TIER DÉRIVÉ ─────────────────────────────────────────────────────────────────────────────
# PLUS AUCUN TIER DÉRIVÉ : l'approximation retombe sur le score de sa SOURCE, donc tier A quel que
# soit son déterminisme. Un calcul non déterministe se publierait au tier d'un relevé.
"$SRC¦    if consigne.statut != \"approximation\":¦    if True:  # mutation: plus aucun tier dérivé¦approximation DÉTERMINISTE garde le tier"
# UN RELEVÉ TRAITÉ COMME UN CALCUL : un `exact` passe par `derive_tier_calcul` et hérite « du plus
# faible de ses ingrédients » alors qu'il n'en a aucun.
"$SRC¦    if consigne.statut != \"approximation\":¦    if consigne.statut == \"jamais\":  # mutation: un relevé devient un calcul¦\`exact\` ne dérive AUCUN tier"
# LE DÉTERMINISME IGNORÉ : la même formule déclarée non déterministe garde le tier du déterministe.
# C'est #67 annulé, et rien d'autre ne le verrait.
"$SRC¦    return derive_tier_calcul(ingredients, deterministe=bool(consigne.deterministe))¦    return derive_tier_calcul(ingredients, deterministe=True)  # mutation: le déterminisme ignoré¦descend d'un cran"

# ── §5 AUCUN SCORE ÉCRIT ICI ──────────────────────────────────────────────────────────────────────
# LA TROISIÈME TABLE : le (tier, score) est recopié au lieu d'être lu. Vert partout aujourd'hui, et
# divergent des deux autres au premier ajustement de la table (#46).
"$SRC¦    tier_a = RELIABILITY_TABLE[SOURCE_TYPE]                       # LU, jamais écrit ici (#46)¦    tier_a = (\"A\", 0.95)  # mutation: une troisième table¦aucun score en dur dans le module"

# ── §6 LE TEMPOREL — une croissance annuelle s'exécute, et le contenu ne ment pas sur le résultat ──
# LE RENDU D'UN RATIO SANS DIMENSION : repassé par `montant`, une croissance de 0,25 devient « 0 »
# (la mantisse de `montant` ne vaut que pour les paliers M/Md). Le nombre structuré reste juste et le
# CONTENU ment (#42/#45) — c'est le défaut que le temporel a rendu courant, donc gardé ici.
"$SRC¦    if not dimension:¦    if False:  # mutation: un ratio sans dimension est arrondi à 0 par montant¦SANS DIMENSION"
# L'OFFSET IGNORÉ : `Revenues[-1]` est résolu à l'exercice courant. Une croissance lit deux fois le
# même exercice → 0 %, le fait faux et rassurant que le décalage existe pour éviter.
"$SRC¦        cible = _decaler_annees(base, offset)¦        cible = _decaler_annees(base, 0)  # mutation: l'offset d'exercice est ignoré¦une croissance annuelle S'EXÉCUTE"
# LE REPLI SILENCIEUX : au lieu de REFUSER un exercice décalé absent, on se replie sur le point le
# plus récent (`period_end=None` → `point_pour_periode` rend le dernier). Une croissance sur un seul
# exercice devient alors 0 % au lieu d'un mandat — le fait faux et rassurant, jamais un « échec ».
"$SRC¦        p = point_pour_periode(series[concept], cible, tol_days=TOLERANCE_ANCRE_J)¦        p = point_pour_periode(series[concept], None, tol_days=TOLERANCE_ANCRE_J)  # mutation: repli sur le point courant¦un exercice décalé ABSENT"
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
