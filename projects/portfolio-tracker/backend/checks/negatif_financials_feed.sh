#!/usr/bin/env bash
# TEST NÉGATIF de `check_financials_feed.py` — BIDIRECTIONNEL.
#
#   bash checks/negatif_financials_feed.sh
#
# POURQUOI CE FICHIER EXISTE, ET POURQUOI SI TARD. Ce feed est l'un des plus anciens modules du
# dépôt et n'avait jamais eu de test négatif. Le 2026-09-24 on a découvert pourquoi c'était grave :
# son check portait l'assert « ROIC négatif publié tel quel (−90,7 %) », qui VERROUILLAIT un faux.
# Un check sans test négatif ne garde pas une règle — il fige le comportement du jour où il a été
# écrit, défaut compris. Et le défaut, ici, s'était REPRODUIT : #190 (archivé) → #231 → #274 → #549
# → #656, quatre générations de la même entry tier A. Supprimer la ligne en base n'aurait rien
# réglé ; le détenteur est le producteur (#46).
#
# ⚠️ LA MUTATION QUI COMPTE EST LA n°1 : elle restaure exactement l'état d'avant, c'est-à-dire un
# ROIC publié pour un émetteur qui n'a pas d'exploitation. Si le check restait vert là-dessus, tout
# le reste de ce fichier serait du décor.
#
# ⚠️ CE QUE LES MUTATIONS 2 ET 3 AJOUTENT, ET QU'AUCUNE AUTRE NE DIT. Une garde doit DISCRIMINER,
# pas punir (leçon de `negatif_datation.sh` n°15). Une garde qui refuserait le ROIC à tout le monde
# satisferait la mutation 1 sans rien valoir. Le ROIC doit donc disparaître quand le CA est déposé à
# ZÉRO, rester publié quand le CA est simplement NON RÉSOLU — et, dans ce dernier cas, DIRE que
# l'hypothèse n'a pas pu être vérifiée. Trois états, jamais deux.
#
# ⚠️ CIBLAGE PAR PREMIÈRE OCCURRENCE (mutation 7). La ligne `etat="non_defini")` est un JUMEAU
# exact : elle apparaît pour le ROIC puis pour l'intensité capex, même texte, même indentation. Le
# remplacement ne vise que la 1ʳᵉ — donc le ROIC, qui vient en premier dans le fichier. Si le
# ciblage dérivait, le harnais le dirait : le rouge tomberait sur l'assert du capex, pas sur celui
# qui est nommé ici.
set -u
cd "$(dirname "$0")/.." || exit 1

SRC="app/knowledge/financials_feed.py"
CHECK="checks/check_financials_feed.py"
NET=none

# ── SATISFIABILITÉ ────────────────────────────────────────────────────────────────────────────────
# Une acceptation qui ne peut pas virer au vert n'éprouve rien. On le MESURE ici plutôt que de s'en
# remettre au souvenir d'un `run_all.sh` vert (`feedback_ligne_de_base_est_une_mesure`).
_IMG=$(docker inspect portfolio-backend --format '{{.Config.Image}}')
_base=$(docker run --rm --network "$NET" -v "$PWD:/app:ro" \
        -w /app -e PYTHONPATH=/app --env-file checks/env.checks \
        "$_IMG" python "$CHECK" 2>&1); _rc=$?
if [ "$_rc" -ne 0 ] || ! printf '%s' "$_base" | grep -q 'vérifications OK'; then
  echo "  FAIL satisfiabilité — le check rougit AVANT toute mutation"
  printf '%s\n' "$_base" | grep -E 'FAIL' | head -5
  exit 1
fi
printf '  ok   satisfiabilité · %s\n\n' "$(printf '%s' "$_base" | grep -E 'vérifications OK')"

mutations=(
# ── §1 LA GARDE ROIC — le jumeau qui avait manqué quatre générations ──────────────────────────────
# 1. ⚠️ L'ÉTAT D'AVANT, RESTAURÉ. La garde ne mord plus : un émetteur sans exploitation reçoit de
#    nouveau un ROIC tier A. C'est #656 qui revient — « −49,7 % », qui se lit « détruit la moitié de
#    son capital par an en exploitant mal » là où le fait est « n'a pas commencé à exploiter ».
"$SRC¦        if operations is False:¦        if False:  # mutation: la garde ne mord plus¦émetteur pré-commercial : le ROIC n'est PAS chiffré"

# 2. LA GARDE PUNIT AU LIEU DE DISCRIMINER. Un CA non résolu est traité comme un CA nul : le ROIC
#    disparaît pour tout émetteur dont le concept XBRL du CA n'a pas répondu. La garde paraît « plus
#    stricte », et elle fabrique des trous là où la donnée existait.
"$SRC¦        operations = None if revenue is None else revenue > 0¦        operations = False if revenue is None else revenue > 0  # mutation: le doute vaut condamnation¦CA non résolu → le ROIC est tout de même CHIFFRÉ"

# 3. LE TROISIÈME ÉTAT REDEVIENT UN SILENCE. Le ratio sort, mais plus rien ne dit que l'hypothèse
#    « le résultat est dominé par l'exploitation » n'a pas pu être vérifiée. Un silence se relit
#    comme une propriété du sujet (`feedback_rendu_est_un_producteur`) : le lecteur croit l'hypothèse
#    tenue. C'est le mode de panne le plus discret du lot — tous les nombres restent justes.
"$SRC¦            reserve = (\"\" if operations else¦            reserve = (\"\" if True else  # mutation: la réserve n'est plus dite¦CA non résolu → le texte DIT que l'hypothèse n'a pas pu être vérifiée"

# 4. LE DRAPEAU DISPARAÎT DU STRUCTURÉ. Le texte le dit peut-être encore, mais rien n'est plus
#    interrogeable : un aval qui trie les ratios ne peut plus distinguer un ROIC vérifié d'un ROIC
#    sous réserve. Une prose ne se teste qu'au `in` — c'est précisément ce `in` qui a laissé passer
#    la contradiction du motif pendant vingt jours (cf. §3).
"$SRC¦                \"nopat_approx\": \"net_income\", \"operations_etablies\": operations,¦                \"nopat_approx\": \"net_income\",  # mutation: le drapeau n'est plus publié¦CA positif → ROIC publié, \`operations_etablies\` vrai"

# ── §2 DEUX ÉTATS DE REFUS, ET LES FONDRE EST LE DÉFAUT D'ORIGINE ─────────────────────────────────
# 5. ⚠️ LE DÉFAUT RÉEL, RESTAURÉ — il a vécu au vert du 2026-09-04 au 2026-09-24. Le préfixe
#    « intrant manquant » revient sur un ratio dont les intrants sont TOUS présents : le motif sort
#    « intrant manquant en base EDGAR : chiffre d'affaires NUL (déposé, pas manquant) », une phrase
#    qui se contredit dans sa propre longueur et qui envoie la chaîne chercher une source qu'elle ne
#    trouvera jamais.
"$SRC¦            \"non_defini\": \"ratio NON DÉFINI pour cet émetteur (intrants présents) : \",¦            \"non_defini\": \"intrant manquant en base EDGAR : \",  # mutation: les deux états refusionnent¦CA nul : le motif ne dit PAS « intrant manquant »"

# 6. L'ÉTAT CESSE D'ÊTRE STRUCTURÉ et redevient de la prose. C'est l'état d'avant le correctif :
#    la distinction existait dans la phrase, donc elle ne se testait qu'au `in` — et un `in` ne voit
#    jamais ce qui a été ajouté DEVANT lui.
"$SRC¦        unfounded.append({\"field\": f, \"etat\": etat, \"reason\": prefixe + need})¦        unfounded.append({\"field\": f, \"reason\": prefixe + need})  # mutation: l'état redevient prose¦CA nul → état \`non_defini\`"

# 7. LE REFUS PERD SES TAGS. Le texte est juste, le champ est bien non chiffré — et l'entry ne
#    supersede plus rien, parce que c'est le TAG qui apparie une génération à la précédente
#    (`_current_tagged_entry_id`). #656 resterait donc courante à côté de son propre démenti, et
#    aucun nombre n'aurait bougé pour le signaler. C'est le mode de panne que la forme « publier
#    le refus » introduit : elle ne vaut que par l'appariement.
"$SRC¦                fiscal_period=period, source_url=src, tags=_tags(\"roic_pct\"),¦                fiscal_period=period, source_url=src, tags=[\"financials\", \"note\"],  # mutation: le refus perd les tags qui l'apparient¦le refus porte les tags du champ"

# ── §3 LE JUMEAU D'ORIGINE — il tient toujours ────────────────────────────────────────────────────
# 8. LA GARDE FCF, elle, existait déjà. On la mute pour prouver que le lot ne l'a pas désarmée en
#    passant : le quotient de deux négatifs redevient publiable, et « +80,8 % de conversion » sort
#    tier A pour une société qui brûle 914 M\$ par an. C'est le même défaut que le ROIC, SIGNE
#    OPPOSÉ — et c'est pour ça que la garde ROIC avait manqué : on n'avait cherché que les nombres
#    flatteurs.
"$SRC¦        significatif = net_income > 0¦        significatif = True  # mutation: le quotient de deux négatifs redevient publiable¦fcf_conversion_pct est None, pas le quotient de deux négatifs"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
