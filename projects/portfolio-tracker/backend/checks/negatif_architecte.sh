#!/usr/bin/env bash
# TEST NÉGATIF de `check_architecte.py` (lot M3, roadmap V3 `12-lot-M3-architecte.md`) — sur le
# harnais existant (`_negatif.sh`, détenteur unique, #65).
#
#   bash checks/negatif_architecte.sh
#
# SATISFIABILITÉ — le check non muté est VERT (mesuré avant toute mutation). DISCRIMINATION — une
# mutation par règle ([S1]-[S9], la porte, l'interrupteur, le renvoi, la réplicabilité), et c'est
# l'assert VISÉ qui rougit. Chaque motif de mutation est une SOUS-CHAÎNE D'UNE SEULE LIGNE, unique
# dans le fichier muté (le harnais ne convertit `\n` que dans le REMPLAÇANT, jamais dans le motif
# cherché — un motif multi-ligne sort en MUTATION CADUQUE, cf. l'en-tête de `_negatif.sh`).
#
# ⚠️ Couverture partielle assumée (temps de la session) : les 7 lignes du tableau de la porte §3.1
# sont gardées par LA MÊME boucle `for … in cas_porte` dans le check — une mutation sur UNE branche
# de `_diagnostic` fait rougir TOUTES les lignes de cette branche à la fois, ce qui n'est pas un
# faux vert (la garde est bien PARTAGÉE, #46) ; chaque branche a néanmoins sa propre mutation.
set -u
cd "$(dirname "$0")/.." || exit 1

S="app/modele_entreprise/structure.py"
P="app/modele_entreprise/porte.py"
PE="app/modele_entreprise/periodes.py"
A="app/modele_entreprise/architecte.py"

CHECK="checks/check_architecte.py"
NET=none

mutations=(
  # ── [S1]-[S9] (structure.py) — chaque motif cible la CONDITION, jamais le `if` qui la partage ──
  "$S¦(b.rattachement.axe, b.rattachement.membre) not in adresses¦False¦[S1] — membre inventé refusé"
  "$S¦membres_vises <= membres¦True¦[S2] — découpage mixte refusé"
  "$S¦autre.rattachement.membre == ancetre¦False¦[S3] — Data Center et Compute côte à côte refusé"
  "$S¦len(axes) > 1:¦False:¦[S3] — un seul axe au premier niveau"
  "$S¦b.rattachement.ligne not in famille.lignes_du_business_plan¦False¦[S4] — bloc agrege hors du business plan refusé"
  "$S¦parent.role == \"commun\"¦False¦[S4] — bloc parent rattaché à un bloc commun refusé"
  "$S¦b.role != \"commun\" and b.maille != \"estime\"¦False¦[S5] — un bloc"
  "$S¦p not in matiere.pieces_citables¦False¦[S6] — pièce hors du dossier refusée"
  "$S¦if passage is None:¦if False:¦[S7] — aucune formule ne porte la ligne chiffre_affaires, refusé"
  "$S¦if noms != attendus:¦if False:¦[S7] — bloc oublié dans l'agrégé refusé"
  "$S¦if bloc_id in annonces:¦if False:¦[S8] — extension annoncée comptée"
  "$S¦p not in periodes_classeur¦False¦[S9] — période hors du classeur refusée"
  "$S¦manquantes = set(matiere.periodes_projetees) - couvertes¦manquantes = set()¦[S9] — période projetée non couverte refusée"

  # ── La porte (porte.py) ───────────────────────────────────────────────────────────────────────
  "$P¦    if applicable is None:¦    if False:¦émetteur non classé"
  "$P¦    if manque.nature == \"sans_reponse\":¦    if False:¦sans_reponse, toute cause"
  "$P¦    if manque.nature == \"rouverte_comite\":¦    if False:¦rouverte_comite"
  "$P¦échec technique : relancer avant de dessiner¦tout va bien, rien a signaler¦non_fondee, source_indisponible"

  # ── L'interrupteur `porte_admet_reponses_refusees` (arbitrage du 2026-10-22) ────────────────────
  "$P¦if ref.porte_admet_reponses_refusees:¦if not ref.porte_admet_reponses_refusees:¦interrupteur"

  # ── Les périodes (periodes.py) ──────────────────────────────────────────────────────────────
  "$PE¦vus[fy] != p[\"fin\"]¦False¦collision de deux exercices"

  # ── Le renvoi (architecte.py) — la PREMIÈRE occurrence de `if not tient:` (4 espaces, avant le
  # renvoi) ; `replace(..., 1)` prend le match le plus à GAUCHE dans le fichier, donc celui-ci,
  # même si la chaîne de 4 espaces est aussi une sous-chaîne de la seconde occurrence (8 espaces,
  # après le renvoi) plus bas dans le fichier. ─────────────────────────────────────────────────
  "$A¦    if not tient:¦    if False:¦renvoi — sortie refusée puis valide"

  # ── Réplicabilité (§9 du check — grep des `app/modele_entreprise/*.py` livrés) ─────────────────
  "$A¦__all__ = [¦_TICKER_DE_TEST = \"NVDA\"\n__all__ = [¦réplicabilité"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
