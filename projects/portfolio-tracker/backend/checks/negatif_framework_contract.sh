#!/usr/bin/env bash
# TEST NÉGATIF de `check_framework_contract.py` — une mutation par critère.
#
# POURQUOI CE FICHIER EST VERSIONNÉ, ET PAS DANS /tmp. Un check neuf n'est éprouvé qu'après avoir
# viré au ROUGE au moins une fois : tant qu'il n'a jamais rougi, « 66 vérifications OK » ne
# distingue pas un contrat solide d'un fichier d'asserts qui ne mesurent rien. Un test négatif
# jetable se réécrit à chaque session, et ses défauts reviennent avec lui.
#
# CE QU'IL EXIGE DE CHAQUE MUTATION — les trois conditions, jamais une seule :
#   1. le check sort en ÉCHEC (exit ≠ 0) ;
#   2. l'assert ATTENDU, nommé, porte le FAIL — pas un autre. Un check qui rougit ailleurs
#      signalerait que le critère visé n'est pas gardé (4ᵉ faux vert : l'assert à côté) ;
#   3. le script atteint quand même sa ligne de BILAN. Un script mort avant ses asserts ne prouve
#      rien, il ne fait que ne pas contredire (2ᵉ faux vert).
#
#   bash checks/negatif_framework_contract.sh
set -u
cd "$(dirname "$0")/.." || exit 1
IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
SRC="app/contracts/framework_answer_schema.py"
TOOL="tools/acceptation_frameworks.py"
PONT="app/agents/v2/frameworks.py"

# ── Les mutations : fichier ¦ motif remplacé ¦ remplaçant ¦ assert qui DOIT rougir ─────────────
# Chaque mutation défait UN invariant et un seul — une mutation qui en casserait deux ne dirait pas
# lequel des deux asserts discrimine.
mutations=(
"$SRC¦        interdits = [b for b in tous¦        interdits = [b for b in ()¦\`non_fondable\` qui publie quand même une réponse"
"$SRC¦    aucun_substitut: bool¦    aucun_substitut: bool = False¦\`aucun_substitut\` n'a pas de défaut"
"$SRC¦    cited_entry_ids: list[int] = Field(min_length=1)¦    cited_entry_ids: list[int] = Field(min_length=1)\n    actualite: Optional[str] = None¦\`Fondation\` (émise/persistée) REFUSE un champ"
"$SRC¦            if self.mandat_de_recherche_id is None:¦            if False:¦un renvoi SANS mandat"
"$SRC¦    mandat_de_recherche_id: Optional[int] = None¦    mandat_de_recherche_id: Optional[int] = None\n    reponse: Optional[Reponse] = None¦le bloc manager n'a aucun champ de réponse ni de rang"
"$SRC¦\"fondation.rang_derive\"¦\"fondation.rang_derivee\"¦colonne \`rang_degrade\`"
"$SRC¦            if vaut_sans_objet != (self.statut != \"approxime\"):¦            if vaut_sans_objet and False:¦\`honnetete_approximation='ok'\` sur une réponse qui n'approxime pas"
"$SRC¦    actualite: Literal[\"courante\", \"perimee\", \"indeterminable\"]¦    actualite: Literal[\"courante\", \"perimee\", \"indeterminable\", \"inconnue\"]¦le vocabulaire de l'axe servi est EXACTEMENT celui du détenteur"
"$SRC¦        if self.statut == \"approxime\" and self.fondation.nature_effective != \"interpretation\":¦        if False:¦une approximation présentée comme une \`mesure\`"
"$TOOL¦from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES¦# import retiré par la mutation¦IMPORTE la table plutôt que de deviner"
# ── le PONT (§8) — les invariants que le contrat NE PEUT PAS vérifier (#37) ────────────────────
"$PONT¦    if answer.question_id not in questions:¦    if False:¦[A] une question inconnue du framework"
"$PONT¦        hors_corpus = [i for i in cites if i not in entries]¦        hors_corpus = []¦[B] une entry citée hors du corpus fourni"
"$PONT¦        if answer.fondation.rang_derive != attendu:¦        if False:¦[C] un rang auto-déclaré meilleur que ses sources"
"$PONT¦        if plancher is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦        if False and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦[D] un rang sous le plancher"
"$PONT¦            if attendue not in portees and answer.statut != \"approxime\":¦            if False:¦[E] la nature attendue n'est portée par aucune entry citée"
"$PONT¦        if cible.question_id == answer.question_id:¦        if False:¦[F] un substitut qui pointe une réponse à LA MÊME question"
"$PONT¦    donnees[\"fondation\"] = {**donnees[\"fondation\"], \"actualite\": act.etat,¦    donnees[\"fondation\"] = {**donnees[\"fondation\"], \"actualite\": \"courante\",¦une panne de flux ne se lit JAMAIS"
# ── §9 la bijection champ ↔ pixel, éprouvée DANS LES DEUX SENS ────────────────────────────────
"$SRC¦    analyste: str = Field(min_length=1)¦    analyste: str = Field(min_length=1)\n    champ_fantome: Optional[str] = None¦tout champ du contrat a son pixel"
"FROZEN:framework_screen_niveau3.md¦⟦manager.motif⟧¦⟦manager.motif_invente⟧¦tout pixel rend un champ RÉEL"
"$PONT¦def _plus_faible(tiers: list[str]) -> str:¦_NOTCH_BELOW = {}\n\n\ndef _plus_faible(tiers: list[str]) -> str:¦le pont ne recopie pas la table des crans"
)

passes=0; ratees=0
for m in "${mutations[@]}"; do
  IFS='¦' read -r fichier vieux neuf attendu <<< "$m"
  tmp=$(mktemp -d)
  cp -r . "$tmp/backend" 2>/dev/null
  rm -rf "$tmp/backend/checks/__pycache__" "$tmp/backend/.git" 2>/dev/null
  # Les documents figés sont copiés EUX AUSSI : sans cela la maquette serait immuable, et §9 (« tout
  # pixel rend un champ réel ») ne pourrait jamais rougir — un critère qu'aucune mutation n'atteint
  # est un critère non éprouvé, même s'il est vert.
  cp -r ../roadmap/provenance-cards "$tmp/frozen" 2>/dev/null
  cible="$tmp/backend/$fichier"
  case "$fichier" in FROZEN:*) cible="$tmp/frozen/${fichier#FROZEN:}" ;; esac

  # La mutation est appliquée par python (pas `sed`) : le remplacement doit ÉCHOUER bruyamment si
  # le motif n'existe plus, sinon une mutation devenue caduque se lirait « le check a rougi » alors
  # qu'il aurait rougi pour une tout autre raison.
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

  out=$(docker run --rm --network none -v "$tmp/backend:/app:ro" \
        -v "$tmp/frozen:/contract_frozen:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
        "$IMG" python checks/check_framework_contract.py 2>&1)
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
