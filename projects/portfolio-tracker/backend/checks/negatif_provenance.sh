#!/usr/bin/env bash
# TEST NÉGATIF de `check_provenance.py`, §9-§12 — `focus` (le search-worker peut dire ce qu'il
# cherche DANS un document, dans les mots du document ; la moitié du budget lui est dédiée — prompt
# search-worker règle 12, `document_search.select_relevant`). Une mutation par DÉCISION, chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_provenance.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_provenance.py"
DS="app/knowledge/document_search.py"
WS="app/knowledge/websearch.py"
T="app/agents/v2/tools.py"
mutations=(
# le classement par `focus` est débranché entièrement (comportement = sans `focus`)
"$DS¦    if focus_clean:¦    if False:¦ligne de tableau EST sélectionnée"
# le classement par `focus` existe mais perd son alternance : seule la question compte
"$DS¦    requetes.append((\"chercher\", focus_clean))¦    pass¦la question ET un du focus"
# les chunks sont réembeddés (coût multiplié) au lieu d'un seul appel pour toutes les requêtes
"$DS¦        sample_vecs = await embeddings.embed_texts([c.text for c in sample])¦        sample_vecs = await embeddings.embed_texts([c.text for c in sample]); await embeddings.embed_texts([c.text for c in sample])¦embeddés qu'UNE fois"
"$DS¦        qvecs = await embeddings.embed_texts(list(queries), is_query=True)¦        qvecs = await embeddings.embed_texts(list(queries))¦l'instruction de requête"
"$DS¦        for i in range(len(rankings)):¦        for i in range(1):¦la question ET un du focus"
# la règle de budget (cost > budget) est retirée de l'allocation par alternance
"$DS¦            if cost > budget:¦            if False:¦reste sous le budget avec"
# \`_finalise\` ne transmet plus \`chercher\` à select_relevant
"$WS¦    sel = await select_relevant(full, query, max_chars=limit, focus=chercher)¦    sel = await select_relevant(full, query, max_chars=limit)¦atteint select_relevant"
# l'exécuteur d'outil oublie \`chercher\` avant d'appeler fetch_url
"$T¦    chercher = (args.get(\"chercher\") or \"\").strip()[:200] or None¦    chercher = None¦transmis tel quel à fetch_url"
# le schéma d'outil (migration 025) perd la propriété \`chercher\` (clef renommée, donc absente)
"app/db/migrations/_gen_025.py¦                    \"chercher\": {¦                    \"chercher_retire\": {¦tools_json fetch_url déclare"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
