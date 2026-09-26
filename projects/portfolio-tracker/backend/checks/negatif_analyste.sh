#!/usr/bin/env bash
# TEST NÉGATIF de `check_analyste.py` — BIDIRECTIONNEL (moitié déterministe de l'analyste).
#
#   0. SATISFIABILITÉ — le check non muté est vert (sinon rien de ce qui suit ne prouve quoi que ce
#      soit : un check déjà rouge « détecte » toutes les mutations sans en garder aucune) ;
#   puis une MUTATION PAR GARDE, chacune exigeant : (1) exit ≠ 0, (2) le FAIL sur l'assert NOMMÉ,
#   (3) la ligne de bilan atteinte (le script n'est pas mort avant ses asserts).
#
#   bash checks/negatif_analyste.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/agents/v2/analyste.py"
PONT="app/agents/v2/frameworks.py"
CHECK="checks/check_analyste.py"

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
# ⚠️ `\n` est converti dans le motif COMME dans le remplaçant : deux gardes peuvent porter la même
# ligne (`if aucune_reponse_possible(ouverts):` aux deux sites d'appel), et seule la ligne qui la
# précède les distingue. Sans motif multi-ligne, la seconde serait inatteignable par mutation —
# donc non éprouvée, même verte (#56).
mutations=(
# §1 — le hors-sujet vient du référentiel, et les deux moitiés partitionnent le framework
"$SRC¦    return [q for q in fw.questions if q.id not in applicables]¦    return [q for q in fw.questions if q.id in applicables]¦partitionnent le framework"
"$SRC¦            motif=va.motif_gabarit,¦            motif=\"sans objet\",¦le motif est le"
"$SRC¦    if va.mode != \"sans_objet\":¦    if False:¦déclarer sans objet une question APPLICABLE"
# §2 — ce que le modèle voit : aucun levier, aucune note de source
"$SRC¦            \"variable_archetype\": q.variables_par_archetype[archetype].variable,¦            \"variable_archetype\": q.variables_par_archetype[archetype].variable,\n            \"plancher_tier\": q.plancher_tier,¦ne contient pas \`plancher_tier\`"
"$SRC¦                    \"titre\": e.get(\"title\"),¦                    \"titre\": e.get(\"title\"),\n                    \"reliability_tier\": e.get(\"reliability_tier\"),¦ne montre pas le \`reliability_tier\`"
"$SRC¦    return ouverts == [\"sans_fondement\"]¦    return False¦aucune question SANS corpus citable n'est montrée"
# §3 — le plancher est structurel
"$SRC¦        if _TIER_RANK.get(str(e.get(\"reliability_tier\")), len(TIER_ORDER)) <= plafond¦        if _TIER_RANK.get(str(e.get(\"reliability_tier\")), len(TIER_ORDER)) <= plafond + 1¦plancher A ne voit QUE"
"$SRC¦        if _TIER_RANK.get(str(e.get(\"reliability_tier\")), len(TIER_ORDER)) <= plafond¦        if _TIER_RANK.get(str(e.get(\"reliability_tier\")), 0) <= plafond¦SANS tier connu compte pour le pire"
# §4 — ce que le modèle ne peut pas émettre
"$SRC¦    statut: Literal[\"repondu\", \"approxime\", \"sans_fondement\"]¦    statut: Literal[\"repondu\", \"approxime\", \"sans_fondement\", \"non_fondable\"]¦ne peut émettre NI"
"$SRC¦        if not self.cited_entry_ids:¦        if False:¦réponse SANS citation est refusée"
# §5 — les deux axes sont dérivés, par leurs détenteurs
"$SRC¦    rang = derive_synthesis_reliability(tiers)[1] if approx else _plus_faible(tiers)¦    rang = _plus_faible(tiers)¦UN CRAN SOUS"
# (règle déléguée : elle se mute chez son détenteur, `frameworks.nature_effective_de`, #72)
"app/agents/v2/frameworks.py¦        return distinctes.pop()\n    return \"interpretation\"¦        return distinctes.pop()\n    return \"mesure\"¦nature forte n'est concédée"
"$SRC¦    return tier if tier in TIER_ORDER else TIER_ORDER[-1]¦    return tier if tier in TIER_ORDER else TIER_ORDER[0]¦tier inconnu vaut le PIRE tier connu"
# §6 — [S] et la copie des profils, dans le pont
"$PONT¦        if answer.reponse.sens not in admis:¦        if False:¦un sens plausible mais hors vocabulaire"
"$PONT¦                profil[clef] = list(valeur) if isinstance(valeur, list) else valeur¦                profil[clef] = valeur¦sont des COPIES"
# §7 — trois états nommés, et surtout : une panne d'agent n'est pas un manque de données
"$SRC¦            remede=\"collecte\",¦            remede=\"rafraichissement\",¦avec le remède"
"$SRC¦                resultat.refus.append((qid, _MOTIF_OMISSION))¦                resultat.answers.append(reponse_non_fondable(interrogeables[qid], **entete, manque=_MOTIF_OMISSION, citables=1, fournies=len(entries)))¦PAS en \`non_fondable\`"
"$SRC¦            if brute.question_id in vues:¦            if False:¦DEUXIÈME réponse du même analyste"
"$SRC¦    if perdues:¦    if False:¦NI en réponse NI en refus fait LEVER"
# §8 — les statuts admissibles, calculés AVANT la dépense (#40)
"$SRC¦            ouverts.append(\"approxime\")¦            pass¦\`approxime\` reste OUVERT"
"$SRC¦        if _TIER_RANK.get(cran, len(TIER_ORDER)) <= _TIER_RANK.get(¦        if True or _TIER_RANK.get(cran, len(TIER_ORDER)) <= _TIER_RANK.get(¦\`approxime\` est FERMÉ"
"$SRC¦    if any(nature_satisfait(nature_effective_de([e.get(\"nature\")], approximation=False),¦    if True or any(nature_satisfait(nature_effective_de([e.get(\"nature\")], approximation=False),¦\`repondu\` est FERMÉ sur une question de MESURE"
"$SRC¦    if any(nature_satisfait(nature_effective_de([e.get(\"nature\")], approximation=False),¦    if question.nature_attendue in natures and any(nature_satisfait(nature_effective_de([e.get(\"nature\")], approximation=False),¦\`repondu\` est OUVERT sur une question de JUGEMENT"
"$SRC¦    ouverts.append(\"sans_fondement\")¦    pass¦reste ouvert dans TOUS les cas"
"$SRC¦        _, cran, _ = derive_synthesis_reliability([meilleur])¦        cran = TIER_ORDER[min(_TIER_RANK[meilleur] + 1, len(TIER_ORDER) - 1)]¦règle du cran est réellement APPELÉE"
"$SRC¦    ouverts.append(\"sans_fondement\")¦    _cran_en_dur = \"A-\"\n    ouverts.append(\"sans_fondement\")¦aucun tier n'est écrit EN DUR"
"$SRC¦            \"statuts_admis\": ouverts,¦¦contexte porte \`statuts_admis\`"
"$SRC¦        ouverts, _ = statuts_admissibles(q, citables)\n        if aucune_reponse_possible(ouverts):¦        ouverts, _ = statuts_admissibles(q, citables)\n        if False:¦n'est pas montrée au modèle"
"$SRC¦        ouverts, ecartes = statuts_admissibles(q, citables)\n        if aucune_reponse_possible(ouverts):¦        ouverts, ecartes = statuts_admissibles(q, citables)\n        if False:¦SANS aucun appel modèle"
"$SRC¦        if not citables:¦        if False:¦DEUX causes ont DEUX motifs distincts"
"$SRC¦                manque=(f\"aucune réponse recevable n'est possible sur ce corpus pour \"¦                manque=(f\"aucune source fournie ne fonde « {q.enonce} » — pour \"¦DEUX causes ont DEUX motifs distincts"
"$SRC¦            if brute.statut not in admis[brute.question_id]:¦            if False:¦sort en refus nommé"
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
saut = lambda s: s.replace('\\\\n', chr(10))
vieux, neuf = saut(sys.argv[2]), saut(sys.argv[3])
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
