#!/usr/bin/env bash
# TEST NÉGATIF de `check_frameworks_definitions.py` — une mutation par critère.
#
# Les trois conditions, jamais une seule (cf. `negatif_framework_contract.sh` pour le raisonnement) :
#   1. le check sort en ÉCHEC (exit ≠ 0) ;
#   2. l'assert ATTENDU, nommé, porte le FAIL — pas un autre ;
#   3. le script atteint quand même sa ligne de BILAN.
#
# ⚠️ Les mutations portent ici sur les DONNÉES autant que sur le code, et c'est le point : le
# référentiel est un fichier de données, donc la question « qu'est-ce qui garde ces données ? » ne
# se répond qu'en les abîmant. Une mutation du YAML qui laisserait le check vert dirait que le
# fichier n'est gardé par rien — et un fichier de données non gardé dérive plus vite que du code,
# parce que personne ne le relit.
#
#   bash checks/negatif_frameworks_definitions.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
YAML="app/frameworks/frameworks.yaml"
DEF="app/contracts/framework_definition_schema.py"
PONT="app/agents/v2/frameworks.py"

# ── fichier ¦ motif remplacé ¦ remplaçant ¦ assert qui DOIT rougir ──────────────────────────────
mutations=(
# §1 — le référentiel charge, et il charge inerte
"$PONT¦    brut = yaml.safe_load(p.read_text(encoding=\"utf-8\"))¦    brut = yaml.load(p.read_text(encoding=\"utf-8\"), Loader=yaml.SafeLoader)¦le chargeur utilise \`yaml.safe_load\`"
# ⚠️ La question surnuméraire s'appelle `qf_8`, pas `qf_7_bis` : le `pattern` d'id du contrat
# (`^[a-z]{2}_[0-9]+$`) refusait `qf_7_bis` AVANT que l'assert de comptage soit atteint — la
# mutation prouvait le pattern, pas le comptage. Mesuré, pas prévu (1ᵉʳ faux vert, sens rouge).
"$YAML¦      - id: qf_7¦      - id: qf_8\n        enonce: Une quatorzième question surnuméraire glissée dans le référentiel\n        chemin_indexation: qualite_financiere.surnumeraire\n        nature_attendue: mesure\n        plancher_tier: A\n        actualite_bloquante: true\n        sens_admis: [oui, non]\n        ingredients_requis:\n          - id: quelque_chose\n            libelle: Un ingrédient dont le libellé est assez long pour passer\n            essentiel: true\n        variables_par_archetype:\n          rentable: {mode: variable, variable: Une variable licite}\n          pre_revenus: {mode: variable, variable: Une variable licite}\n          financiere: {mode: variable, variable: Une variable licite}\n      - id: qf_7¦le référentiel porte les 2 pilotes et leurs 13 questions"
# §2 — le contrat refuse les définitions creuses
"$DEF¦        if not any(i.essentiel for i in self.ingredients_requis):¦        if False:¦une question sans aucun ingrédient ESSENTIEL"
"$DEF¦        if self.plancher_tier in PLANCHERS_DESSERRES and not self.motif_plancher:¦        if False:¦un plancher desserré SANS motif déclaré"
"$DEF¦            if bool(self.substitut_question_id) == bool(self.aucun_substitut):¦            if False:¦ne dit NI son substitut NI son absence"
"$DEF¦            if not self.motif_gabarit:¦            if False:¦un \`sans_objet\` sans motif"
"$DEF¦    enonce: str = Field(min_length=30)¦    enonce: str = Field(min_length=1)¦un énoncé écrit en artefact comptable"
# §3 — les invariants relationnels
"$PONT¦        if q.id in vus:¦        if False:¦[G] deux frameworks qui déclarent la MÊME question"
"$PONT¦        if q.chemin_indexation in chemins:¦        if False:¦[H] deux frameworks dont deux questions partagent"
"$PONT¦        if couverts != attendus:¦        if False:¦[I] une question MUETTE sur un archétype déclaré"
"$PONT¦            if cible not in vus:¦            if False:¦[J] un substitut qui pointe une question inexistante"
"$PONT¦    if fichier.schema_version != FRAMEWORK_DEFINITION_SCHEMA_VERSION:¦    if False:¦[M] un fichier dont la version ne correspond pas"
# §4 — les clefs que le pont LIT (le mode de panne est un SAUT, pas une erreur)
"$PONT¦CLEFS_PROFIL_LUES = (\"plancher_tier\", \"nature_attendue\")¦CLEFS_PROFIL_LUES = (\"plancher_tier\",)¦les clefs réellement lues par le pont sont celles déclarées"
"$PONT¦        if plancher is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦        if profil.get(\"plancher_tier_typo\") is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦les clefs réellement lues par le pont sont celles déclarées"
# §5 — la garde de l'ORDRE questions → données. Le cœur du lot.
"$YAML¦            libelle: Provisions constituées ou reprises, et dépréciations d'actifs, avec leur justification¦            libelle: Notes annexes sur les provisions et dépréciations d'inventaire, entry 33¦aucun énoncé, ingrédient ou gabarit ne nomme"
"$YAML¦        enonce: Combien de temps l'entreprise peut-elle tenir sans accès au marché des capitaux ?¦        enonce: Combien de mois de trésorerie restent à NVDA sans accès au marché ?¦aucun énoncé, ingrédient ou gabarit ne nomme"
"$YAML¦            libelle: Trésorerie et placements immédiatement mobilisables¦            libelle: Trésorerie déposée au 10-K le plus récent chez EDGAR¦aucun énoncé, ingrédient ou gabarit ne nomme"
# ⚠️ Le libellé injecté est GUILLEMETÉ : en YAML, un ` #` non quoté ouvre un commentaire, donc la
# valeur parsée était « Voir entry » — refusée par `min_length=20`, et la mutation n'injectait
# jamais le motif qu'elle prétendait injecter (fixture non discriminante, 1ᵉʳ faux vert).
"$YAML¦            libelle: Résultat net de l'exercice¦            libelle: \"Voir les entry #4 et #5 du corpus courant pour le détail\"¦aucun champ ne référence une entry par son numéro"
# §6 — les vocabulaires et leur détenteur
"$DEF¦    nature_attendue: Literal[\"mesure\", \"evenement\", \"interpretation\"]¦    nature_attendue: Literal[\"mesure\", \"evenement\", \"interpretation\", \"rumeur\"]¦\`nature_attendue\` (contrat de définition) == \`common.NATURES\`"
"$DEF¦PLANCHERS_DESSERRES = (\"B\", \"B-\", \"C+\", \"C\")¦PLANCHERS_DESSERRES = (\"B\", \"B-\", \"C+\", \"C\", \"D\")¦sous-ensemble STRICT de \`TIER_ORDER\`"
# §7 — la spec et le référentiel ne divergent pas (mutation côté DONNÉES et côté SPEC)
"$YAML¦        plancher_tier: B+\n        actualite_bloquante: false\n        sens_admis: [part_faible¦        plancher_tier: A\n        actualite_bloquante: false\n        sens_admis: [part_faible¦nature, plancher et actualité bloquante coïncident"
"FROZEN:03-spec-frameworks.md¦| \`qf_7\` | Combien de temps l'entreprise peut-elle **tenir sans accès au marché des capitaux** ? | \`mesure\` | A |¦| \`qf_7\` | Combien de temps l'entreprise peut-elle **tenir sans accès au marché des capitaux** ? | \`interpretation\` | A |¦nature, plancher et actualité bloquante coïncident"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/checks/__pycache__" "$tmp/backend/app/__pycache__" "$tmp/backend/.git" 2>/dev/null
  # La spec est copiée elle aussi : sans cela §7 ne pourrait rougir que d'un côté, et un critère
  # qu'aucune mutation n'atteint dans les deux sens n'est éprouvé qu'à moitié.
  cp -r ../roadmap "$tmp/roadmap" 2>/dev/null
  cible="$tmp/backend/$fichier"
  case "$fichier" in FROZEN:*) cible="$tmp/roadmap/${fichier#FROZEN:}" ;; esac

  if ! python3 -c "
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
vieux, neuf = sys.argv[2].replace('\\\\n', chr(10)), sys.argv[3].replace('\\\\n', chr(10))
if vieux not in s:
    print('MOTIF INTROUVABLE'); sys.exit(1)
p.write_text(s.replace(vieux, neuf, 1), encoding='utf-8')
" "$cible" "$vieux" "$neuf"; then
    printf '  ??   %-58.58s MUTATION CADUQUE (motif absent du source)\n' "$attendu"
    ratees=$((ratees + 1)); rm -rf "$tmp"; continue
  fi

  out=$(docker run --rm --network none -v "$tmp/backend:/app:ro" \
        -v "$tmp/roadmap:/roadmap:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
        "$IMG" python checks/check_frameworks_definitions.py 2>&1)
  rc=$?
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
