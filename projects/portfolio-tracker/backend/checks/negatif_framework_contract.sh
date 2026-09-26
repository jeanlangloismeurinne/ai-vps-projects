#!/usr/bin/env bash
# TEST NÉGATIF de `check_framework_contract.py` — une mutation par critère.
#
# La boucle de mutation (copie temp, application par python, docker run, classement, bilan) vit dans
# `_negatif.sh` (détenteur unique, #46). Ici : seulement les mutations et le check visé. Chaque
# mutation défait UN invariant et un seul — une mutation qui en casserait deux ne dirait pas lequel
# des deux asserts discrimine.
#
#   bash checks/negatif_framework_contract.sh
set -u
cd "$(dirname "$0")/.." || exit 1

CHECK="checks/check_framework_contract.py"
WITH_FROZEN=1

SRC="app/contracts/framework_answer_schema.py"
TOOL="tools/acceptation_frameworks.py"
PONT="app/agents/v2/frameworks.py"

# fichier ¦ motif remplacé ¦ remplaçant ¦ assert qui DOIT rougir  (FROZEN:<f> vise un doc figé)
mutations=(
"$SRC¦        interdits = [b for b in tous¦        interdits = [b for b in ()¦\`non_fondable\` qui publie quand même une réponse"
"$SRC¦    aucun_substitut: bool¦    aucun_substitut: bool = False¦\`aucun_substitut\` n'a pas de défaut"
"$SRC¦    cited_entry_ids: list[int] = Field(min_length=1)¦    cited_entry_ids: list[int] = Field(min_length=1)\n    actualite: Optional[str] = None¦\`Fondation\` (émise/persistée) REFUSE un champ"
"$SRC¦            if self.mandat_de_recherche_id is None:¦            if False:¦un renvoi SANS mandat"
"$SRC¦    mandat_de_recherche_id: Optional[int] = None¦    mandat_de_recherche_id: Optional[int] = None\n    reponse: Optional[Reponse] = None¦le bloc manager n'a aucun champ de réponse ni de rang"
"$SRC¦\"fondation.rang_derive\"¦\"fondation.rang_derivee\"¦colonne \`rang_degrade\`"
"$SRC¦            if vaut_sans_objet != (self.statut != \"approxime\"):¦            if vaut_sans_objet and False:¦\`honnetete_approximation='ok'\` sur une réponse qui n'approxime pas"
"$SRC¦    actualite: Literal[\"courante\", \"perimee\", \"indeterminable\"]¦    actualite: Literal[\"courante\", \"perimee\", \"indeterminable\", \"inconnue\"]¦le vocabulaire de l'axe servi est EXACTEMENT celui du détenteur"
"$SRC¦        if self.statut == \"approxime\" and self.fondation.nature_effective != \"interpretation\":¦        if False:¦une approximation présentée comme une \`mesure\`"
"$TOOL¦from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES¦# import retiré par la mutation¦IMPORTE la table plutôt que de deviner"
# ── le PONT (§8) — les invariants que le contrat NE PEUT PAS vérifier (#37) ────────────────────
"$PONT¦    if answer.question_id not in questions:¦    if False:¦[A] une question inconnue du framework"
"$PONT¦        hors_corpus = [i for i in cites if i not in entries]¦        hors_corpus = []¦[B] une entry citée hors du corpus fourni"
"$PONT¦        if answer.fondation.rang_derive != attendu:¦        if False:¦[C] un rang auto-déclaré meilleur que ses sources"
"$PONT¦        if plancher is not None and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦        if False and _TIER_RANK.get(attendu, len(TIER_ORDER)) > _TIER_RANK.get(¦[D] un rang sous le plancher"
"$PONT¦                and not nature_satisfait(effective, attendue)):¦                and False):¦[E] la nature attendue n'est portée par aucune entry citée"
"$PONT¦    return effective == attendue¦    return True¦MÉLANGE ne concède pas la nature forte"
"$PONT¦        return effective in NATURES¦        return effective == attendue¦JUGEMENT fondée sur des FAITS mesurés"
"$PONT¦    if cible.question_id == answer.question_id:¦    if False:¦[F] un substitut qui pointe une réponse à LA MÊME question"
"$PONT¦        if answer.reponse.sens not in admis:¦        if False:¦[S] un \`sens\` hors du vocabulaire fermé"
"$PONT¦    if admis and answer.reponse is not None:¦    if admis and answer.reponse is not None and answer.reponse.sens:¦[S] … et le silence n'est pas une échappatoire"
"$PONT¦    donnees[\"fondation\"] = {**donnees[\"fondation\"], \"actualite\": act.etat,¦    donnees[\"fondation\"] = {**donnees[\"fondation\"], \"actualite\": \"courante\",¦une panne de flux ne se lit JAMAIS"
# ── §9 la bijection champ ↔ pixel, éprouvée DANS LES DEUX SENS ────────────────────────────────
"$SRC¦    analyste: str = Field(min_length=1)¦    analyste: str = Field(min_length=1)\n    champ_fantome: Optional[str] = None¦tout champ du contrat a son pixel"
"FROZEN:framework_screen_niveau3.md¦⟦manager.motif⟧¦⟦manager.motif_invente⟧¦tout pixel rend un champ RÉEL"
"$PONT¦def _plus_faible(tiers: list[str]) -> str:¦_NOTCH_BELOW = {}\n\n\ndef _plus_faible(tiers: list[str]) -> str:¦le pont ne recopie pas la table des crans"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
