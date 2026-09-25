#!/usr/bin/env bash
# TEST NÉGATIF de `check_bouclage.py` — une mutation par GARANTIE, chacune exigeant exit≠0 + FAIL sur
# l'assert NOMMÉ + ligne de bilan atteinte. La boucle vit dans `_negatif.sh` (détenteur unique, #65).
#   bash checks/negatif_bouclage.sh
#
# LES DEUX MUTATIONS QUI COMPTENT LE PLUS sont les « EXERCÉ » (#71) : retirer l'appel de production à
# `serve_mandate` / `read_open_mandates` dans `bouclage.py`. Une garde de COMPORTEMENT resterait verte
# (le décideur avait 0 appelant le 2026-09-25, tous ses tests au vert) — seule une garde qui COMPTE
# LES APPELANTS en production rougit. C'est la leçon de `feedback_controle_au_point_de_lecture`.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_bouclage.py"
SCH="app/contracts/bouclage_schema.py"
BCL="app/agents/v2/bouclage.py"
FWK="app/agents/v2/frameworks.py"
TRA="app/agents/v2/traducteur.py"

mutations=(
# ── §1 CONTRAT : `acquis` avec statut_apres non_fondable n'est plus refusé ─────────────────────────
"$SCH¦        if acquis and not fonde:¦        if False:  # mutation: acquis+non_fondable accepté¦acquis\` avec statut_apres non_fondable est REFUSÉ"
# ── §1 CONTRAT : un sort non fondé avec statut_apres fondé n'est plus refusé ───────────────────────
"$SCH¦        if not acquis and fonde:¦        if False:  # mutation: sort non fondé + fondé accepté¦avec statut_apres fondé est REFUSÉ"
# ── §2 DOCTRINE : la dispense ne prime plus sur la collecte tentée ─────────────────────────────────
"$BCL¦    if dispensee:¦    if False:  # mutation: la dispense ne prime plus¦DISPENSE prime"
# ── §2 ATTEIGNABILITÉ : un sort n'est plus jamais produit ──────────────────────────────────────────
"$BCL¦    return \"mandat_non_executable\"¦    return \"collecte_insuffisante\"  # mutation: mandat_non_executable inatteignable¦les quatre sorts sont atteignables"
# ── §3 ORIGINE : une source qui a déçu (echec_collecte) n'est plus « tentée » ──────────────────────
"$BCL¦            tente[qid] = True¦            tente[qid] = False  # mutation: echec_collecte non tenté¦echec_collecte→tenté"
# ── §4 EXERCÉ : l'appel de production à serve_mandate disparaît ────────────────────────────────────
"$BCL¦                await serve_mandate(¦                await serve_mandate_DESARME(¦serve_mandate\` a un appelant de production"
# ── §4 EXERCÉ : l'appel de production à read_open_mandates disparaît ───────────────────────────────
"$BCL¦        ouverts = await read_open_mandates(¦        ouverts = await read_open_mandates_DESARME(¦read_open_mandates\` a un appelant de production"
# ── §5 SCOPE [R] : le scope n'allège plus l'exigence (toutes les questions redeviennent requises) ──
"$FWK¦        if questions is not None and q.id not in questions:¦        if False and q.id not in questions:  # mutation: [R] ignore le scope¦le plan scopé qf_1 est refusé à tort"
# ── §5 SCOPE [P] : une ligne hors scope n'est plus refusée ────────────────────────────────────────
"$FWK¦        if questions is not None and it.question_id not in questions:¦        if False and it.question_id not in questions:  # mutation: [P] tolère hors scope¦une ligne HORS du scope"
# ── §5 SCOPE contexte : un scope hors des questions applicables n'est plus refusé (#32) ────────────
"$TRA¦        if hors:¦        if False:  # mutation: scope hors-applicable toléré¦un scope nommant une question SANS OBJET"
# ── §6 MOTIFS : deux sorts partagent un motif (un lecteur ne peut plus dire POURQUOI) ──────────────
"$BCL¦    \"acquis\": \"la re-collecte a fondé la question (statut passé au-dessus de non_fondable)\",¦    \"acquis\": \"le comité a accepté le trou — une dispense active couvre la question\",  # mutation: motif dupliqué¦les quatre motifs sont distincts"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
