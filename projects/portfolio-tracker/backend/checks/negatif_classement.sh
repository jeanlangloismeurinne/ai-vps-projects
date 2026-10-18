#!/usr/bin/env bash
# TEST NÉGATIF de `check_classement.py` — une mutation par DÉCISION du classement par le comité et de la
# recommandation de « changement de stade » (#139), chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ +
# bilan atteint (harnais `_negatif.sh`).
#
#   bash checks/negatif_classement.sh
#
# Mutées : le catalogue (recommandation, table de réouverture), le contrat et le pont [W], la règle de la
# recommandation (classement d'origine qui ne tranche rien, décision qui ferme, premier fait, type exigé),
# les relations du geste (archétype, dépôt du fil, même jour, futur, lecture obtenue, pièce, date d'effet),
# le niveau 1 (complétude suspendue, champs servis) et l'écran.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_classement.py"
WITH_FRONT=1
CL="app/agents/v2/classement.py"
P="app/agents/v2/parcours.py"
F="app/agents/v2/frameworks.py"
S="app/contracts/framework_definition_schema.py"
Y="app/frameworks/frameworks.yaml"
ECR="FRONT:components/v2/ClassementEmetteur.js"
mutations=(
# ── le catalogue ──────────────────────────────────────────────────────────────────────────────
"$Y¦      pre_revenus: rentable¦      pre_revenus: financiere¦recommande « sans revenus » → « commerciale »"
"$Y¦        rouverte_par: [financement, resultats, surprise_allocation, changement_de_stade]¦        rouverte_par: [financement, resultats, surprise_allocation]¦EXACTEMENT la table validée"
# ── le contrat et le pont ─────────────────────────────────────────────────────────────────────
"$S¦        if self.reclasse is not None and self.origine != \"emetteur\":¦        if False:  # mutation¦type EXTÉRIEUR qui recommanderait"
"$F¦            if de not in declares or vers not in declares:¦            if False:  # mutation¦une cible hors des archétypes"
"$F¦            if de == vers:¦            if False:  # mutation¦recommandation de ne rien changer"
# ── la recommandation ─────────────────────────────────────────────────────────────────────────
"$CL¦    seuil = classement.effective_from if classement.declencheur_accession else None¦    seuil = classement.effective_from  # mutation: un classement d'origine tranche¦classée d'origine le 24/09 APRÈS"
"$CL¦(seuil is not None and fait <= seuil)¦False¦ferme les faits survenus"
"$CL¦    return min(candidats, key=lambda r: (r.fait_du, r.accession)) if candidats else None¦    return max(candidats, key=lambda r: (r.fait_du, r.accession)) if candidats else None¦le PREMIER est retenu"
"$CL¦            if t.id not in q.types or fait is None¦            if fait is None¦seul (un essai réussi) ne recommande rien"
# ── le geste ──────────────────────────────────────────────────────────────────────────────────
"$CL¦    if archetype not in set(fichier.archetypes):¦    if False:  # mutation¦un archétype inconnu est refusé"
"$CL¦if e.accession == accession), None)¦if True), None)  # mutation¦absent du fil de l'émetteur"
"$CL¦    if courant is not None and courant.effective_from >= jour:¦    if courant is not None and courant.effective_from > jour:¦seconde décision le même jour"
"$CL¦    if event.event_date > jour:¦    if False:  # mutation¦postérieur au jour du geste"
"$CL¦    if lecture.entry_id is None:¦    if False:  # mutation¦sans lecture du dépôt, pas de décision"
"$CL¦effective_from=jour, piece_id=lecture.entry_id,¦effective_from=jour, piece_id=None,¦reclasser écrit la pièce"
"$CL¦effective_from=jour, piece_id=lecture.entry_id,¦effective_from=event.event_date, piece_id=lecture.entry_id,¦reclasser écrit la pièce"
# ── le niveau 1 ───────────────────────────────────────────────────────────────────────────────
"$P¦    elif etat.recommandation is not None:¦    elif False:  # mutation¦empêche « dossier complet »"
"$P¦                        reclassement_recommande=_recommandation_servie(etat.recommandation))¦                        reclassement_recommande=None)  # mutation¦sont SERVIS au niveau 1"
"$P¦                           auteur=c.auteur, piece_id=c.piece_id,¦                           auteur=None, piece_id=c.piece_id,¦servie avec sa pièce, son auteur"
# ── l'écran ───────────────────────────────────────────────────────────────────────────────────
"$ECR¦          <p className=\"text-xs text-gray-400 italic\">{r.resume}</p>¦¦l'écran rend \`r.resume\`"
"$ECR¦geste === 'reclasser' ? r.vers : r.de¦r.vers¦envoie reclasser (vers) ou maintenir"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
