#!/usr/bin/env bash
# TEST NÉGATIF de `check_appariement.py` — BIDIRECTIONNEL (maillon 4bis, convention #67).
#
#   0. SATISFIABILITÉ — le check non muté est VERT. Une acceptation écrite avant sa capacité doit
#      d'abord prouver qu'elle PEUT virer au vert, sinon toutes les mutations qui suivent rougissent
#      sur un check déjà cassé et ne prouvent rien (`feedback_acceptation_rouge_bidirectionnelle`).
#   1. DISCRIMINATION — UNE MUTATION PAR GARDE, chacune exigeant les trois conditions que
#      `_negatif.sh` encode : exit ≠ 0, FAIL sur l'assert NOMMÉ (pas un autre), et bilan ATTEINT.
#
# Trois fichiers mutés, parce que la garde est répartie sur trois et qu'aucun ne suffit seul :
#   · `appariement_schema.py` — la charge des trois états, et les deux pièges de forme (`False` est
#     falsy, une liste non vide d'éléments vides) ;
#   · `apparieur.py` — le pont contre l'inventaire RÉEL, qui est la garde absente de `poste_retenu()` ;
#   · `synthesis_feed.py` — la règle de tier #67 et son unique discriminant.
#
# Sans réseau, sans base, sans modèle : `NET=none`.
#   bash checks/negatif_appariement.sh
set -u
cd "$(dirname "$0")/.." || exit 1

CHECK="checks/check_appariement.py"
NET=none

# ⚠️ Purge des `__pycache__` AVANT que `run_mutations` ne copie l'arbre. L'invalidation du cache
# Python se fait sur (mtime, size) : une mutation qui ne change pas la taille et retombe dans la
# même seconde laisserait le conteneur exécuter le `.pyc` d'AVANT — le check resterait vert, et la
# mutation serait comptée comme « ce critère ne garde rien » alors qu'elle n'a jamais été exécutée
# (`feedback_pycache_faux_vert`). Le plus sûr est qu'il n'y ait aucun `.pyc` à copier.
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
base=$(docker run --rm --network none -v "$PWD:/app:ro" -v "$PWD/../roadmap:/roadmap:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks "$IMG" python "$CHECK" 2>&1)
base_rc=$?
if [ "$base_rc" -ne 0 ] || printf '%s' "$base" | grep -q 'FAIL'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation ; rien de ce qui suit ne prouve quoi que ce soit"
  printf '%s\n' "$base" | grep -F 'FAIL' | head -5; exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$base" | grep -E 'vérifications OK')"

CONTRAT="app/contracts/appariement_schema.py"
PONT="app/agents/v2/apparieur.py"
TIERS="app/knowledge/synthesis_feed.py"

# ⚠️ L'`assert attendu` se cherche dans la LIGNE DE FAIL, qui porte le LIBELLÉ de l'assert — pas
# dans le message de l'exception refusée. Deux mutations ont d'abord été classées « rouge, mais pas
# sur l'assert visé » parce que leur motif était copié du `raise` du code au lieu du `label` du
# check : quand la mutation fait ACCEPTER l'objet, il n'y a plus d'exception du tout, donc plus de
# message. Un test négatif qui vise le mauvais texte se lit exactement comme une garde absente.
mutations=(
# ── Le contrat : la charge des trois états ───────────────────────────────────
"$CONTRAT¦            if len(self.concepts) != 1:¦            if len(self.concepts) > 99:¦à DEUX concepts"
"$CONTRAT¦            if manquants:¦            if False:¦sans hypothèse"
"$CONTRAT¦            porte = [nom for nom, val in ((\"concepts\", self.concepts),¦            porte = [nom for nom, val in ((\"concepts\", []),¦portant un concept"
"$CONTRAT¦        if len(set(couples)) != len(couples):¦        if False:¦deux appariements pour un même couple"
# Le piège falsy : `is not None` remplacé par la valeur de vérité rend la garde aveugle à
# `deterministe=False`, c'est-à-dire à exactement la moitié des cas qu'elle doit voir.
"$CONTRAT¦            if self.deterministe is not None:¦            if self.deterministe:¦la moitié falsy"
# La contrainte d'élément retirée : la liste redevient une `list[str]`, et `['']` la satisfait.
"$CONTRAT¦HypotheseEcrite = Annotated[str, Field(min_length=15)]¦HypotheseEcrite = str¦liste NON VIDE"
# ── Le pont : la garde qui manquait ──────────────────────────────────────────
"$PONT¦    absents = sorted(c for c in it.concepts if c not in depose)¦    absents = []¦[V] un concept VOISIN"
"$PONT¦    if not inventaire:¦    if False:¦inventaire VIDE"
"$PONT¦    hors_declaration = sorted(refs - declares)¦    hors_declaration = []¦QUE dans la formule"
"$PONT¦    inutilises = sorted(declares - refs)¦    inutilises = []¦absent de la formule pèse sur le tier"
"$PONT¦    if it.deterministe:¦    if False:¦formule à coefficient choisi"
"$PONT¦        manquants = sorted(traduits - apparies)¦        manquants = []¦SANS appariement"
"$PONT¦            if couple in inobtenables:¦            if False:¦apparier une ligne que le plan déclare"
"$PONT¦                plan.ticker_id, plan.framework_id, plan.framework_version):¦                carte.ticker_id, carte.framework_id, carte.framework_version):¦carte et plan sur des versions"
# La limite ÉCRITE. Si elle disparaît, un lecteur croira le pont sémantique et s'y fiera — c'est
# une garde sur l'ÉNONCÉ, et elle se teste comme les autres.
"$PONT¦n'attrape PAS le faux appariement SÉMANTIQUE¦n'attrape pas tous les cas¦la limite est ÉCRITE"
# ── La règle de tier : un seul discriminant ──────────────────────────────────
"$TIERS¦    if not deterministe:¦    if True:¦tier du plus faible, SANS cran"
"$TIERS¦        key=lambda ts: (_TIER_RANK.get(ts[0], len(TIER_ORDER)), -ts[1]))¦        key=lambda ts: (_TIER_RANK.get(ts[0], len(TIER_ORDER)),))¦ne dépend pas de l'ORDRE"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
