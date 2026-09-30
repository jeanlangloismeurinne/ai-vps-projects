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
# ── L'ENCADRÉ DE CHIFFRES CLÉS (4 bis) — contrat, puis pont [K] ────────────────────────────────
"$SRC¦            if self.date_ou_periode is None:¦            if False:¦ne dit pas ce qu'il mesure est refusé"
"$SRC¦        elif self.motif_absence is None:¦        elif False:¦ni établi ni motivé est refusé"
"$SRC¦        elif self.date_ou_periode is not None:¦        elif False:¦absent mais daté est refusé"
"$SRC¦            if data.get(\"valeur\") is not None or data.get(\"unite\") is not None:¦            if False:¦jamais avalé en silence"
"$SRC¦        if len(set(ids)) != len(ids):¦        if False:¦deux lignes pour le même chiffre"
"$PONT¦        if manquants or inventes:¦        if inventes:¦un chiffre déclaré OMIS"
"$PONT¦        if manquants or inventes:¦        if manquants:¦un chiffre NON déclaré est refusé"
"$PONT¦        if mauvaises:¦        if False:¦dans une AUTRE unité"
"$PONT¦        if declares is None:¦        if False:¦un profil sans déclaration d'encadré"
# ── #101 : un chiffre CALCULÉ vaut sa formule (pont [K bis]) et c'est `completer_encadre` qui l'écrit ──
"$PONT¦        if faux:¦        if False:¦NE vaut PAS sa formule est refusé"
"$PONT¦            if (c.valeur is None) != (e.valeur is None) or (¦            if False or (¦ÉTABLI alors qu'un de ses termes ne l'est pas"
"$PONT¦    releves = [c for c in lignes if c.id not in ids_calcules]¦    releves = list(lignes)¦rend UNE ligne par chiffre"
"$PONT¦        absents = [n for n in noms if par_id.get(n) is None or par_id[n].valeur is None]¦        absents = [n for n in noms if par_id.get(n) is None]¦NON établi parce qu'un terme ne l'est pas"
"$PONT¦            sortie.append(ChiffreCle(id=d.id, unite=d.unite, motif_absence=f\"non calculable : {e}\"))¦            sortie.append(ChiffreCle(id=d.id, unite=d.unite, valeur=0.0, date_ou_periode=\"zéro\"))¦dénominateur NUL"
"$PONT¦        date = (f\"{periodes[0]} — calculé : {d.calcul}\" if len(periodes) == 1 else¦        date = (f\"{periodes[0]} — calculé : {d.calcul}\" if True else¦deux périodes différentes"
# ── #103 : un fait postérieur se lit DANS le dépôt (pont [P]) ; l'effet s'écrit (contrat) ──────────
"$PONT¦            if not any(provient_du_depot(entries.get(i, {}), fait.depot) for i in fait.cited_entry_ids):¦            if False:¦lu dans un ARTICLE qui parle du dépôt"
"$PONT¦            if hors_fondation:¦            if False:¦une lecture hors des citations"
"$PONT¦    return bool(depot) and depot.replace(\"-\", \"\") in str(entry.get(\"source_url\") or \"\")¦    return bool(depot)¦lu dans un ARTICLE qui parle du dépôt"
"$SRC¦    effet: str = Field(min_length=20)¦    effet: str = Field(min_length=1)¦un effet non écrit"
"$SRC¦        if len(set(depots)) != len(depots):¦        if False:¦le même dépôt lu deux fois"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
