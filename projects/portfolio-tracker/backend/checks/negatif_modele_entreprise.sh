#!/usr/bin/env bash
# TEST NÉGATIF de `check_modele_entreprise.py` (lot M1, roadmap 09 §9/§12) — sur le harnais existant
# (`_negatif.sh`, détenteur unique, #65).
#
#   bash checks/negatif_modele_entreprise.sh
#
# SATISFIABILITÉ — le check non muté est VERT (mesuré avant toute mutation). DISCRIMINATION — une
# mutation par garde du contrat, du pont et des contrôles, et c'est l'assert VISÉ qui rougit.
#
# Les gardes de déduplication (`_sans_doublon`) et de forme de bloc (`Bloc._maille_correspond_au_
# rattachement`) sont PARTAGÉES par plusieurs cas du check (#46, détenteur unique) : une seule
# mutation les éprouve, visée sur UN des cas qu'elle couvre — les autres rougissent aussi, ce qui
# n'est pas un faux vert (la garde est bien UNIQUE).
set -u
cd "$(dirname "$0")/.." || exit 1

S="app/contracts/modele_entreprise_schema.py"
R="app/modele_entreprise/referentiel.py"
C="app/modele_entreprise/controles.py"
SC="app/modele_entreprise/scenarios.py"
Y="app/frameworks/modele_entreprise.yaml"

CHECK="checks/check_modele_entreprise.py"
NET=none

mutations=(
  # ── FicheVariable (contrat, §2.1) ─────────────────────────────────────────────────────────────
  "$S¦    if \"__\" in v:¦    if False:¦id avec double tiret bas"
  "$S¦    if len(set(valeurs)) != len(valeurs):¦    if False:¦origines_admises en double"
  "$S¦        if self.controle == \"part_calculee\" and list(self.origines_admises) != [\"calcul\"]:¦        if False:¦part_calculee sans origines"

  # ── FamilleDeComptes ───────────────────────────────────────────────────────────────────────────
  "$S¦        if not (sans_gabarit == a_motif == lignes_vides):¦        if False:¦gabarit ET motif_absence tous deux présents"

  # ── ReferentielModele (cohérence interne) ─────────────────────────────────────────────────────
  "$S¦                if f not in self.familles_de_comptes:¦                if False:¦famille non déclarée sur une fiche"
  "$S¦            if v.controle is not None and v.controle not in self.controles:¦            if False:¦contrôle non déclaré sur une fiche"
  "$S¦                if m not in self.methodes_de_fourchette:¦                if False:¦méthode non déclarée sur une fiche"
  "$S¦            if famille not in self.familles_de_comptes:¦            if False:¦famille_par_archetype vise une famille non déclarée"
  "$S¦            if nom_patron not in self.famille_par_archetype:¦            if False:¦un patron ne correspond à aucun archétype"
  "$S¦                    if fiche is None:¦                    if False:¦un patron retient une variable absente du catalogue"
  "$S¦                    if famille_archetype not in fiche.familles:¦                    if False:¦un patron retient une variable sans sens dans sa famille"

  # ── OrigineCalcul / PassageAgrege (grammaire fermée) ──────────────────────────────────────────
  "$S¦    def _formule_valide(self) -> \"OrigineCalcul\":¦    def _formule_valide(self) -> \"OrigineCalcul\":\n        return self  # mutation de test¦OrigineCalcul — formule hors grammaire"
  "$S¦    def _formule_valide(self) -> \"PassageAgrege\":¦    def _formule_valide(self) -> \"PassageAgrege\":\n        return self  # mutation de test¦PassageAgrege — formule hors grammaire"

  # ── Bloc ───────────────────────────────────────────────────────────────────────────────────────
  "$S¦        if (self.maille == \"publie\") != est_publie:¦        if False:¦maille publie avec un rattachement parent"

  # ── Architecture (cohérence interne) ──────────────────────────────────────────────────────────
  "$S¦                if b.rattachement.bloc == b.id:¦                if False:¦un bloc se rattache à lui-même"
  "$S¦                if b.rattachement.bloc not in par_bloc:¦                if False:¦un bloc parent vise un bloc non déclaré"
  "$S¦                if cur.id in vus:¦                if False:¦cycle de rattachement parent"
  "$S¦                if \"__\" not in nom:¦                if False:¦formule de passage sans séparateur bloc__variable"
  "$S¦                if bloc is None:¦                if False:¦formule de passage vise un bloc non déclaré"
  "$S¦                if var_id not in bloc.variables:¦                if False:¦formule de passage vise une variable que le bloc ne retient pas"
  "$S¦                if cle in vues:¦                if False:¦deux cellules attendues pour la même adresse"
  "$S¦                raise ValueError(f\"une cellule attendue vise le bloc \`{c.bloc}\`, non déclaré\")¦                pass  # mutation de test¦cellule attendue vise un bloc non déclaré"
  "$S¦            if c.variable not in bloc.variables:¦            if False:¦cellule attendue vise une variable que le bloc ne retient pas"

  # ── Fourchette ─────────────────────────────────────────────────────────────────────────────────
  "$S¦        if self.bas > self.haut:¦        if False:¦Fourchette — bas > haut"
  "$S¦        if (ad is None) != (af is None):¦        if False:¦Fourchette — periode_debut/fin de formes différentes"
  "$S¦        if ad is not None and af is not None and ad > af:¦        if False:¦Fourchette — periode_debut postérieure à periode_fin"

  # ── Deplacement ────────────────────────────────────────────────────────────────────────────────
  "$S¦        if (self.valeur_dite is not None) != (self.cible == \"valeur_dite\"):¦        if False:¦Deplacement — valeur_dite hors cible"
  "$S¦        if self.cible == \"valeur_dite\" and not self.source_entry_refs:¦        if False:¦Deplacement — valeur_dite sans pièce"

  # ── Scenario (les raises PORTENT un texte unique : on les cible directement, le mot-clef `if`
  #    « un scénario `central`… » / « un scénario `nomme`… » étant partagé entre deux branches) ──
  "$S¦                raise ValueError(\"un scénario \`central\` ne déplace rien\")¦                pass  # mutation de test¦central avec un déplacement"
  "$S¦                raise ValueError(\"un scénario \`central\` ne porte pas de probabilité\")¦                pass  # mutation de test¦central avec une probabilité"
  "$S¦                raise ValueError(\"un scénario \`nomme\` porte au moins un déplacement\")¦                pass  # mutation de test¦nomme sans déplacement"
  "$S¦                raise ValueError(\"un scénario \`nomme\` ne porte pas de probabilité\")¦                pass  # mutation de test¦nomme avec une probabilité"
  "$S¦                raise ValueError(\"une \`branche\` porte au moins un déplacement\")¦                pass  # mutation de test¦branche sans déplacement"
  "$S¦            if self.probabilite is None:¦            if False:¦branche sans probabilité"
  "$S¦                if d1.bloc == d2.bloc and d1.variable == d2.variable and _chevauchent(d1, d2):¦                if False:¦deux déplacements qui se chevauchent"

  # ── Le pont du référentiel [R1]-[R5] ──────────────────────────────────────────────────────────
  "$R¦    if archetypes_fw != archetypes_ref:¦    if False:¦[R1] archétypes incomplets"
  "$R¦            if qid not in questions_connues:¦            if False:¦[R2] question source inconnue"
  "$R¦            if ligne not in lignes_gabarit:¦            if False:¦[R3] ligne absente du gabarit"
  "$R¦    if set(ref.controles) != noms_controles:¦    if False:¦[R4] contrôle sans fonction"
  "$R¦            if not porte_un_encadre:¦            if False:¦[R5] reponse_reprise sans encadré"

  # ── Le pont de l'architecture [P1]-[P5] ───────────────────────────────────────────────────────
  "$R¦    if famille_attendue is None:¦    if False:¦archétype absent du référentiel"
  "$R¦    if arch.famille != famille_attendue:¦    if False:¦famille différente de celle de l'archétype"
  "$R¦        raise ArchitectureRefusee(f\"[P1] {famille.motif_absence}\")¦        pass  # mutation de test¦famille bancaire, sans gabarit"
  "$R¦    if arch.version_referentiel != ref.version:¦    if False:¦version_referentiel différente du référentiel chargé"
  "$R¦            if fiche is None:¦            if False:¦variable retenue ni fiche ni propre"
  "$R¦            if est_fiche_catalogue and arch.famille not in fiche.familles:¦            if False:¦fiche sans sens dans la famille de l'architecture"
  "$R¦        if p.ligne not in famille.lignes_du_business_plan:¦        if False:¦ligne de passage hors du business plan"
  "$R¦            if c.periodes != [\"sans_periode\"]:¦            if False:¦cellule à exercice pour une variable sans_periode"
  "$R¦        elif \"sans_periode\" in c.periodes:¦        elif False:¦cellule sans_periode pour une variable à exercice"
  "$R¦        if isinstance(c.auteur, AuteurQuestion) and c.auteur.question_id not in fiche.questions_sources:¦        if False:¦cellule attribuée à une question qui n'est pas source"

  # ── Le pont de la cellule [C1]-[C5] ───────────────────────────────────────────────────────────
  "$R¦    if (cellule.bloc, cellule.variable, cellule.periode) not in attendues:¦    if False:¦cellule non attendue par l'architecture"
  "$R¦    if cellule.origine.type not in fiche.origines_admises:¦    if False:¦origine hors de origines_admises de la fiche"
  "$R¦    if cellule.unite != fiche.unite:¦    if False:¦unité différente de celle de la fiche"
  "$R¦        if motif is not None:¦        if False:¦[C4] contrôle \`positif_ou_nul\`"
  "$R¦        if hors:¦        if False:¦[C5] formule hors des variables du bloc"

  # ── Les contrôles (§4) ────────────────────────────────────────────────────────────────────────
  "$C¦    if cellule.valeur > 0:¦    if True:¦positif — valeur nulle refusée"
  "$C¦    if cellule.valeur >= 0:¦    if True:¦positif_ou_nul — valeur négative refusée"
  "$C¦    if 0.0 <= cellule.valeur <= 100.0:¦    if True:¦proportion — hors [0,100] refusée"
  "$C¦    if 0.0 <= cellule.valeur <= 1.0:¦    if True:¦probabilite — hors [0,1] refusée"
  "$C¦    if v == int(v) and 1900 <= int(v) <= 2100:¦    if True:¦annee — non entière refusée"
  "$C¦    if ctx.dernier_exercice_publie is None:¦    if False:¦part_calculee — sans exercice publié connu"
  "$C¦    if cellule.periode > ctx.dernier_exercice_publie:¦    if False:¦part_calculee — mesurée après le dernier exercice publié"

  # ── appliquer_scenario (§5) ───────────────────────────────────────────────────────────────────
  # ⚠️ Pas de mutation sur `if scenario.nature == "central": return dict(centrales)` : pour
  # `SCENARIO_CENTRAL` (déplacements = [], contrat §2.5), le chemin général (`for d in
  # scenario.deplacements`, boucle vide) produit EXACTEMENT le même résultat — aucune entrée ne
  # peut discriminer cette garde en boîte noire. Fusionnée comme la garde « réponse reprise non
  # acquittée » de `negatif_modele_valorisation.sh`.
  "$SC¦        if not cles:¦        if False:¦déplacement qui ne touche rien"
  "$SC¦            if d.cible == \"valeur_dite\":¦            if False:¦valeur dite : la cellule prend la valeur dite"
  "$SC¦            if fourchette is None:¦            if False:¦déplacement sans fourchette couvrante"

  # ── Réplicabilité (§9) ────────────────────────────────────────────────────────────────────────
  "$Y¦version: \"1.0.0\"¦version: \"1.0.0\"\n# NVDA (mutation de test — la garde de réplicabilité doit rougir)¦réplicabilité"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
