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
GRAM="app/contracts/formule_grammaire.py"

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
# ── §10 L'inventaire comme OUTIL DE LECTURE : le rendu est un producteur ──────
# Ces mutations gardent un PRODUCTEUR, pas une règle : ce que le rendu omet, le modèle le lit comme
# une propriété de l'émetteur. Que ce ne soit pas théorique est MESURÉ — le rendu « un point par
# concept » a fait écrire six `indisponible` motivés par « pas de série de plusieurs exercices » sur
# MSFT, sur des concepts dont `companyfacts` porte la série entière. Chaque mutation ci-dessous
# refabrique une omission de cette famille et exige qu'un assert la NOMME.
"$PONT¦    for concept in sorted(facts):¦    for concept in sorted(facts)[1:]:¦égalité d'ensembles"
"$PONT¦    for concept in sorted(facts):¦    for concept in list(facts):¦tri ALPHABÉTIQUE"
"$PONT¦        dates = {str(p.get(\"end\")) for p in utiles}¦        dates = [str(p.get(\"end\")) for p in utiles]¦compte les DATES DISTINCTES"
"$PONT¦            nb_exercices=len({str(p.get(\"end\")) for p in utiles if is_annual_flow(p)}),¦            nb_exercices=len([str(p.get(\"end\")) for p in utiles if is_annual_flow(p)]),¦exercices ANNUELS distincts"
# #46 sur le rendu : la borne « ce point couvre-t-il un exercice ? » RECOPIÉE au lieu d'être appelée.
# La mutation est volontairement JUSTE sur la fixture (350-370 englobe 365) : elle ne fausse aucune
# valeur, elle ne crée qu'un second détenteur — c'est-à-dire la faute qui ne se voit pas avant le
# correctif suivant. Seul un assert d'ÉNONCÉ peut la voir.
"$PONT¦for p in utiles if is_annual_flow(p)}),¦for p in utiles if 350 <= (duree_jours(p) or 0) <= 370}),¦est APPELÉE — un seul détenteur"
"$PONT¦            premier_end=min(dates),¦            premier_end=max(dates),¦bornée par ses deux extrémités"
# LA MUTATION CENTRALE — elle reproduit à l'identique le défaut mesuré sur MSFT : la profondeur
# CALCULÉE mais pas imprimée. Elle doit rougir sur un assert qui lit le TEXTE, pas le résumé (#54).
"$PONT¦        profondeur = (f\"  · {l.nb_dates} dates depuis {l.premier_end}\" if l.nb_dates > 1¦        profondeur = (\"\" if l.nb_dates > 1¦porte la profondeur de la série"
"$PONT¦                      else \"  · 1 seule date\")¦                      else \"\")¦profondeur de 1 est imprimée EXPLICITEMENT"
"$PONT¦            cadre += f\"+A×{l.nb_exercices}\"¦            cadre += \"+A\"¦le NOMBRE d'exercices annuels"
"$PONT¦        if l.nb_exercices:¦        if l.nb_exercices > 1:¦annonce quand même son annuel"
"$PONT¦            out.append(f\"  {l.concept:<58} aucun point exploitable ({l.nb_points} point(s) déposé(s))\")¦            pass¦sans point chiffré reste NOMMÉ"
"$PONT¦{cadre:<18} {l.dernier_end}  \"¦{cadre:<18}  \"¦n'est pas gardé, il est LISIBLE"
"$PONT¦            if d <= limite:¦            if True:¦période ENTIÈREMENT future est écartée"
"$PONT¦            f = p.get(\"filed\")¦            f = p.get(\"end\")¦, JAMAIS max "
# `raise` → `return` d'une date FABRIQUÉE, et non suppression du `if` : une carte indatable qui
# reçoit `1970-01-01` se relit « très vieille » au lieu d'« indatable », donc se revérifie pour
# toujours sans jamais alerter. Le vert qui masque la perte, pas un plantage.
"$PONT¦        raise AppariementSansObjet(¦        return \"1970-01-01\" or (¦doit lever, pas rendre une date fabriquée"
"$PONT¦    return {m.lower() for m in re.findall(r\"[A-Z][a-z0-9]*|[a-z0-9]+\", concept)}¦    return {concept.lower()}¦découpe le CamelCase en mots"
"$PONT¦    return [c for _, c in sorted(scores)[:limite]]¦    return [c for _, c in sorted(scores)[:limite]] + list(inventaire)¦partageant un mot avec l'absent"
"$PONT¦    return sorted({c for it in carte.items for c in it.concepts if c not in depose})¦    return []¦nomme ce que [V] a refusé"
# Deux phrases de légende sur quatre : celle qui DÉCLARE la colonne neuve, et celle qui énonce la
# règle de péremption — la seule des deux qu'aucun code ne garde, donc celle dont la disparition
# serait la plus silencieuse.
"$PONT¦\"PROFONDEUR de la série.¦\"profondeur de la serie.¦(« PROFONDEUR…"
"$PONT¦n'est PLUS ALIMENTÉ¦n'est plus alimenté¦(« PLUS ALIMENTÉ…"
# ── §11 La référence temporelle `Concept[-1]` — la grammaire qui débloque l'archétype `rentable` ──
# Le garde de FORME est chez son détenteur (`formule_grammaire.py`), pas dans le check : muter le
# check ne dirait rien, c'est la grammaire qu'il faut désarmer (#46, une garde se teste chez son
# détenteur). Un décalage POSITIF accepté = un exercice futur qui n'existe pas.
"$GRAM¦        if sl.value > 0:¦        if False:  # mutation: un décalage POSITIF (exercice futur) est accepté¦POSITIF"
# L'offset PERDU : `Revenues[-1]` devient l'exercice courant. `references_de_la_formule` cesse de
# porter le grain fin (concept, offset), donc une croissance lirait deux fois le même exercice — le
# fait faux et rassurant (0 %) que la grammaire existe pour éviter.
"$GRAM¦        return {(noeud.value.id, _offset_du_subscript(noeud, formule))}  # type: ignore[union-attr]¦        return {(noeud.value.id, 0)}  # mutation: l'offset est perdu¦grain fin (concept, offset)"
# La notation N'EST PLUS ENSEIGNÉE au modèle : sans elle, il ne peut pas exprimer une croissance et
# réinvente `Revenues_previous_year`. C'est une garde sur l'ÉNONCÉ du prompt (comme la limite de §9).
"$PONT¦(\`Revenues_previous_year\` n'existe¦(\`RevenuePrecedent\` n'existe¦le prompt ENSEIGNE"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
