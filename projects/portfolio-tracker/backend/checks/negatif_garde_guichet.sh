#!/usr/bin/env bash
# TEST NÉGATIF de la GARDE DU GUICHET (#78) — `check_entry_nature.py` §5bis + `check_framework_contract` [E]/[E0].
#
#   bash checks/negatif_garde_guichet.sh
#
# POURQUOI CE TEST EXISTE. La garde est née d'un faux vert MESURÉ : le contrôle d'abord envisagé
# (« aucun nombre du verbatim absent des entries citées ») a été éprouvé VERT sur la réponse #475
# qui l'avait motivé, parce que le chiffre fabriqué était bel et bien dans l'entry citée. Une garde
# écrite pour un cas et verte sur ce cas est le pire des décors. Celle-ci doit donc prouver les deux
# sens (`feedback_acceptation_rouge_bidirectionnelle`) :
#   · SATISFIABILITÉ — le code non muté passe. `run_all.sh` s'en charge en continu ; ici, la
#     première mutation caduque le dirait bruyamment.
#   · DISCRIMINATION — une mutation PAR CRITÈRE, et c'est l'assert VISÉ, nommé, qui rougit.
#
# ⚠️ CHAQUE MUTATION VISE UN CRITÈRE DISTINCT, y compris les deux qui n'ont rien à voir avec la
# détection elle-même : la TRANSMISSION de `content` depuis chacun des deux sites d'appel. Une garde
# écrite chez son détenteur et jamais atteinte depuis le chemin d'écriture est un décideur sans
# producteur — 0 appel, 0 ligne, garde verte (`feedback_controle_au_point_de_lecture`).
set -u
cd "$(dirname "$0")/.." || exit 1

echo "── §5bis · la garde du guichet (check_entry_nature)"
CHECK="checks/check_entry_nature.py"
NET=coolify
CHECK_DB_URL=$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
export CHECK_DB_URL

mutations=(
  # 1. la branche de rétrogradation elle-même — le cœur de la garde.
  "app/agents/v2/common.py¦elif entry_type in _MEASURING_ENTRY_TYPES and marqueur is not None:¦elif False:¦qui ANNONCE son calcul"

  # 2. LA GARDE DOIT DISCRIMINER, pas punir. Rétrograder tout laisserait la mutation 1 verte par
  #    l'autre bout : un check qui n'éprouve que le refus est satisfait par un refus universel.
  "app/agents/v2/common.py¦elif entry_type in _MEASURING_ENTRY_TYPES and marqueur is not None:¦elif entry_type in _MEASURING_ENTRY_TYPES:¦sans annonce de calcul reste"

  # 3. L'AMPUTATION DU VOCABULAIRE FERMÉ. Le parcours jeton par jeton de §5bis est GÉNÉRÉ depuis le
  #    détenteur : retirer un jeton retire AUSSI son assert, donc il ne peut pas voir ce cas (un
  #    assert écrit depuis sa propre constante). C'est §7bis qui le tient, en ancrant le vocabulaire
  #    sur le corpus réel via les ids de la migration 044 — d'où l'assert visé ici.
  "app/agents/v2/common.py¦    \"par différence\",¦¦du corpus réel ANNONCE son calcul"

  # 4. l'insensibilité à la casse — les producteurs écrivent « Calcul : » en tête de phrase.
  "app/agents/v2/common.py¦bas = content.lower()¦bas = content¦insensible à la CASSE"

  # 5. rendre le marqueur, pas un booléen : sans lui le motif ne peut pas le nommer, et un refus
  #    qui ne dit pas sur quoi condamne le producteur à deviner (#63).
  "app/agents/v2/common.py¦return next((m for m in _MARQUEURS_DE_DERIVATION if m in bas), None)¦return \"\" if any(m in bas for m in _MARQUEURS_DE_DERIVATION) else None¦rend le marqueur, pas un booléen"

  # 6. le motif doit NOMMER le marqueur trouvé.
  "app/agents/v2/common.py¦propre dérivation (« {marqueur} »)¦propre dérivation (« … »)¦le motif NOMME le marqueur"

  # 7. TRANSMISSION, site 1 : l'écriture. `content` retiré → la garde existe et n'est jamais atteinte.
  "app/knowledge/service.py¦entry_type=entry_type, content=content, nature_declaree=nature_declaree,¦entry_type=entry_type, nature_declaree=nature_declaree,¦\`store_knowledge\` transmet"

  # 8. TRANSMISSION, site 2 : le search-worker, qui qualifie AVANT le filtre de plancher. Les deux
  #    sites appellent la même fonction ; c'est ce qui les empêche de diverger, à condition qu'ils
  #    lui passent les mêmes ingrédients.
  "app/agents/v2/worker.py¦        content=content,¦¦(search-worker)\` transmet"

  # 9. LES DEUX AXES NE SE MÉLANGENT PAS (#50). La rétrogradation de nature ne doit jamais toucher
  #    au source_type, donc au tier : le dépôt reste un dépôt.
  "app/knowledge/source_registry.py¦    if source_type != _PROMOUVABLE:¦    if nature == \"interpretation\":\n        source_type = \"web_search_generic\"\n    if source_type != _PROMOUVABLE:¦sans toucher au \`source_type\`"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
