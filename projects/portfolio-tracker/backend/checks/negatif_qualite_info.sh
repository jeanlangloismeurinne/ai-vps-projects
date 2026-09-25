#!/usr/bin/env bash
# TEST NÉGATIF de `check_qualite_info.py` — une mutation par DÉCISION de la dérivation, chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + ligne de bilan atteinte. La boucle vit dans
# `_negatif.sh` (détenteur unique, #65).
#   bash checks/negatif_qualite_info.sh
#
# ⚠️ CE QUI N'EST PAS MUTÉ ICI, ET POURQUOI (précédent `negatif_manager.sh`) — ces garanties sont
# tenues par le CONTRAT, pas par la dérivation : les désarmer fabrique un `QualiteInfo` invalide, que
# Pydantic REJETTE avant tout assert → « script mort », un autre canal que « rouge sur l'assert » :
#   · `sans_objet` HORS base / `non_fondable` DANS la base (§1①/§1④) — le validateur `_coherence`
#     recalcule `base` depuis les compteurs ; toute base incohérente LÈVE à la construction ;
#   · le troisième état (§2, `aucune_question_applicable` ⟺ score None) — le validateur interdit un
#     score sur base vide comme une base vide qui se score ;
#   · `rang_moyen` présent SSI au moins une réponse fondée (§3) — même verrou de contrat.
# On mute donc les décisions que la dérivation prend RÉELLEMENT (crédit, actualité, rang, regroupement)
# et la RÈGLE chez son détenteur (`FACTEUR_ACTUALITE` dans le contrat — #46, une garde déléguée
# s'éprouve là où la règle vit).
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_qualite_info.py"
MOD="app/agents/v2/qualite_info.py"
CTR="app/contracts/qualite_info_schema.py"

mutations=(
# ── §1② approxime décoté au statut (il ne vaut plus autant qu'un repondu) ──────────────────────────
"$MOD¦credit_total += FACTEUR_ACTUALITE[act]¦credit_total += FACTEUR_ACTUALITE[act] * (0.6 if a.statut == \"approxime\" else 1.0)  # mutation¦un dossier d'approximations courantes vaut autant"
# ── §1③ l'actualité n'est plus prise en compte (une périmée obtient plein crédit) ─────────────────
"$MOD¦credit_total += FACTEUR_ACTUALITE[act]¦credit_total += 1.0  # mutation: actualité ignorée¦la seule bascule d'actualité fait tomber le score"
# ── §1③/§5 la RÈGLE mutée chez son DÉTENTEUR : une périmée vaut désormais plein crédit (#46) ───────
"$CTR¦\"perimee\": 0.0,¦\"perimee\": 1.0,  # mutation: la péremption ne décote plus¦la seule bascule d'actualité fait tomber le score"
# ── §3 rang_moyen rend toujours le meilleur tier au lieu de la moyenne de position ────────────────
"$MOD¦idx = int(moyenne + 0.5)¦idx = 0  # mutation: rang_moyen toujours au meilleur¦rang_moyen(A, A-) = A-"
# ── §4 le regroupement oublie la version : deux versions se mêlent (écart V9 rouvert) ──────────────
"$MOD¦groupes[(a.framework_id, a.framework_version)].append(a)¦groupes[(a.framework_id, \"v3.0.0\")].append(a)  # mutation: version figée¦trois (framework, version) distincts"
# ── §6 la base du score est faussée (dénominateur décalé) ──────────────────────────────────────────
"$MOD¦score = round(credit_total / base, 4)¦score = round(credit_total / (base + 1), 4)  # mutation: base fausse¦score = crédit_total / base, au chiffre près"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
