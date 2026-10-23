#!/usr/bin/env bash
# TEST NÉGATIF de `check_explorateur.py` — une mutation par RÈGLE du lot B4f (roadmap V3
# `16-lot-B4f-explorateur.md` §6) : état non rendu, pièce remplacée citable, borne levée, portée
# élargie, fusion des signaux. Chacune exige exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint
# (harnais `_negatif.sh`, détenteur unique de la boucle, #65).
#
#   bash checks/negatif_explorateur.sh
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_explorateur.py"
EXP="app/knowledge/explorateur.py"
mutations=(
# 1. État non rendu — `etat_piece` oublie la pièce REMPLACÉE, rend toujours « en vigueur ».
"$EXP¦    if p.superseded_by is None:¦    if True:¦remplacée par #3, datée de sa remplaçante"

# 2. Pièce remplacée citable — `ouvrir_piece` ne marque plus une pièce remplacée comme historique
#    (elle redeviendrait citable comme si elle fondait encore un bloc, §3 de la spec).
"$EXP¦    historique = p.superseded_by is not None¦    historique = False¦marquée historique, remplaçante nommée"

# 3. Borne levée — la pagination (200 lignes par appel, spec §2) n'est plus appliquée.
"$EXP¦    page_lignes = lignes[debut : debut + _LIGNES_PAR_PAGE]¦    page_lignes = lignes[debut:]¦page 1 — au plus 200 lignes"

# 4. Portée élargie — `rechercher` cesse de fermer le `ticker_id` sur l'émetteur du passage :
#    il interrogerait TOUS les titres, pas seulement celui du mandat (comme
#    `make_query_knowledge_executor`, spec §1).
"$EXP¦            rows = await query_knowledge(conn, ticker_id=ticker_id, query=sujet, limit=limite)¦            rows = await query_knowledge(conn, ticker_id=None, query=sujet, limit=limite)¦FERMÉ transmis à"

# 5. Fusion des signaux — `rendre_resultats_recherche` reclasse les lignes de `query_knowledge`
#    (détenteur unique du classement vectoriel/texte, #22) au lieu de rendre son ORDRE tel quel.
"$EXP¦    for r in rows[: max(1, min(limite, _RESULTATS_RECHERCHE))]:¦    for r in sorted(rows, key=lambda r: r.get('title') or '')[: max(1, min(limite, _RESULTATS_RECHERCHE))]:¦ORDRE d'entrée préservé"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
