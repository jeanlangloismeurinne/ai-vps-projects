#!/usr/bin/env bash
# TEST NÉGATIF de `check_fiche_lue.py` — l'ancien code lit la fiche de l'émetteur (A15 de M1).
# Une mutation par garde, chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint
# (harnais `_negatif.sh`).
#   bash checks/negatif_fiche_lue.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_fiche_lue.py"
AD="app/knowledge/fiche_emetteur.py"

mutations=(
# [F2] la fiche s'applique sans la nature de l'entrée : une source admise pour l'interprétation fonde une mesure.
"$AD¦    accorde = _source_type(fiche, q, nature)¦    accorde = _source_type(fiche, E.qualifier(fiche, url, \"interpretation\"), \"interpretation\")¦[F2] MÊME source + mesure"
# [F2/F7] le générique prend le MEILLEUR cas : la nature se dériverait d'une promotion (circularité).
"$AD¦    return min(_par_nature(fiche, url).values(), key=_rang)¦    return max(_par_nature(fiche, url).values(), key=_rang)¦[F7] le générique ignore une admission bornée"
# [F7] le plafond prend le pire cas : le modèle écarterait une source admise avant de la lire.
"$AD¦    return max(_par_nature(fiche, url).values(), key=_rang)¦    return min(_par_nature(fiche, url).values(), key=_rang)¦[F7] le plafond applique l'admission"
# [F4] la fiche requalifie aussi ce qu'un producteur déterministe a établi : démotion possible.
"$AD¦    if source_type != NON_ADMISE or not url:¦    if not url:¦[F4] une qualification déjà établie"
# [F8] le niveau de l'autorité publique est ignoré : un régulateur européen vaudrait un dépôt SEC.
"$AD¦    \"autorite_publique\": {\"A\": \"edgar_official\", \"A-\": \"regulator_filing_eu\"},¦    \"autorite_publique\": \"edgar_official\",¦[F4] régulateur européen"
# [F8] un critère inconnu reçoit un score par défaut au lieu de lever.
"$AD¦                raise CritereNonTraduit(f\"{s.source} : critère {s.critere!r} au niveau {s.niveau!r}\")¦                return NON_ADMISE¦[F8] un critère inconnu"
# [F8] le site de la société vaut ses pages investisseurs.
"$AD¦    \"site\": \"web_search_reputable\",¦    \"site\": \"company_ir_official\",¦[F8] le lieu \`site\`"
# [F5] la recherche d'origine reprend tous les sous-domaines.
"$AD¦    return tuple(sorted(d for d in domaines if not any(d.endswith(\".\" + autre) for autre in domaines)))¦    return tuple(sorted(domaines))¦[F5] la recherche d'origine"
# [F6] le service redevient un second chemin de qualification.
"app/knowledge/service.py¦    source_type, nature, nature_motif = fiche_emetteur.qualifier(¦    source_type, nature, nature_motif = fiche_emetteur.derive_nature(¦[F6] \`service\` appelle"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
