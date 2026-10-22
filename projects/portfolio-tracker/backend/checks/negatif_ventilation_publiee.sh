#!/usr/bin/env bash
# TEST NÉGATIF de `check_ventilation_publiee.py` — une mutation par règle de la ventilation publiée,
# chacune exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#   bash checks/negatif_ventilation_publiee.sh
#
# ⚠️ ÉCART À LA SPEC (§7), signalé : la spec demande « tolérance mise à zéro OU multipliée par
# 1 000 (deux mutations, les deux sens) ». Mesuré : dans les TROIS fixtures réelles (NVDA/RVMD/JPM),
# tout raccord `boucle` retombe EXACTEMENT sur zéro (les segments XBRL sont déposés pour sommer
# pile sur le total) — une tolérance mise à ZÉRO ne fait donc rougir AUCUNE assertion ([V1]-[V12]) :
# ce n'est pas la garde qui est fausse, c'est qu'aucun cas réel n'est sensible à cette direction.
# Seule la mutation « × 1 000 » (qui absorbe le vrai écart non nul de [V4], −8 910 M$) est gardée.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_ventilation_publiee.py"
SRC="app/knowledge/ventilation.py"
XBRL="app/knowledge/ventilation_xbrl.py"
FEED="app/knowledge/ventilation_feed.py"
APPAR="app/knowledge/appariement_feed.py"

mutations=(
# Qualificateur neutre non retiré : les faits `secteurs` (toujours qualifiés par
# `ConsolidationItemsAxis=OperatingSegmentsMember`) portent alors « un axe de plus » et sont
# disqualifiés — l'axe secteurs perd ses cellules.
"$SRC¦    restants = [(a, m) for (a, m) in membres if (a, m) not in neutres]¦    restants = list(membres)¦[V1]"
# Hiérarchie ignorée : Compute et Networking rejoignent le premier niveau de `activites` — la somme
# dépasse le total publié, le raccord ne boucle plus. MOTIF RÉPARÉ (lot P1) : la ligne ciblait la
# comprehension D'AVANT la délégation à `perimetre.premier_niveau_de` (commit `c551003`, déjà
# fusionnée) — devenue CADUQUE (motif introuvable, [V2] jamais exercée depuis). Cible désormais
# l'APPEL du détenteur unique, même intention (aplatir au lieu de respecter la hiérarchie).
"$SRC¦        premier_niveau = set(premier_niveau_de(presents, parent_de))¦        premier_niveau = set(presents)¦[V2]"
# Tolérance de bouclage multipliée par 1 000 : l'écart réel de resultat_exploitation (−8 910 M$)
# est absorbé, le raccord devient « boucle » au lieu de « non_ventile ».
"$SRC¦                \"boucle\" if abs(reste) <= tolerance_bouclage(total, somme) else \"non_ventile\")¦                \"boucle\" if abs(reste) <= tolerance_bouclage(total, somme) * 1000 else \"non_ventile\")¦[V4]"
# `xsi:nil` lu comme zéro : un fait sans texte (nil ou vide) est désormais lu « 0 » au lieu
# d'être écarté — le garde-fou visible de `lire_instance` (le test `xsi:nil`) reste en place, mais
# la valeur par défaut qu'il protégeait est maintenant fabriquée juste avant lui.
"$XBRL¦        texte = (el.text or \"\").strip()¦        texte = (el.text or \"\").strip() or \"0\"¦[V9]"
# Sous-détail relevé : un axe en trop (non déclaré qualificateur) n'exclut plus le fait — la
# provision CCB × Apple Card de JPM devient un fait ordinaire au lieu d'un sous-détail.
"$SRC¦        if hors:¦        if False:¦[V10]"
# Douze mois glissants remplacés par l'exercice : Data Center au 2026-07-26 redevient 193 737 M$
# (l'exercice FY2026) au lieu de 277 798 M$ (l'identité à trois points).
"$SRC¦                valeur, _compo = douze_mois_glissants(pts, fin_ttm, f\"{axe_id}:{ligne}:{membre}\")¦                valeur = pts[0][\"val\"]¦[V5]"
# Un 10-K antérieur choisi au lieu du dernier.
"$FEED¦        return max(candidats, key=lambda c: (c[\"report\"], c[\"filed\"])) if candidats else None¦        return min(candidats, key=lambda c: (c[\"report\"], c[\"filed\"])) if candidats else None¦[V1]"
# Refus bancaire retiré : JPM (famille bancaire, 3 segments ventilés) tenterait d'écrire sans base.
"$FEED¦    if gabarit_famille is None:¦    if False:¦[V8]"
# Grep de réplicabilité sans dépouillement : les commentaires/docstrings du code livré nomment
# `nvda:`/`jpm:`/`rvmd:`/« Compute »/« Networking » en PROSE (ex. le contrat cite les préfixes
# interdits en exemple) — sans `strip_code`, le grep [V12] trouve ces mots et rougit à tort SUR SA
# PROPRE ASSERTION (mémoire « un grep d'interdit lit sa propre énonciation »).
"$CHECK¦    return strip_code(p.read_text(encoding=\"utf-8\"))¦    return p.read_text(encoding=\"utf-8\")¦[V12]"
# Revue du coordinateur (2026-10-21), quatre mutations de plus :
# Emboîtement aplati : Compute/Networking retrouvent le même niveau que Data Center — un lecteur
# les additionnerait deux fois.
"$SRC¦                prefixe = \"    \" + \"  \" * profondeur + (\"↳ \" if profondeur else \"\")¦                prefixe = \"    \"¦[V14]"
# Changement de découpage remis à « non_ventile » : le TTM activites (Gaming/ProViz/Auto/OEM
# absents du 10-Q) redevient un montant non affecté, faux sens pour un redécoupage d'axe.
"$SRC¦                        statut = \"decoupage_change\"¦                        statut = \"non_ventile\"¦[V13]"
# Membres nouveaux sans valeur : Hyperscale/AI Clouds/Edge Computing redeviennent un simple
# décompte, l'information la plus précieuse du dépôt disparaît.
"$SRC¦                    elif axe_def.raccord == \"total\" and fait.debut in debuts_cumul_valides and fait.fin:¦                    elif False:¦[V15]"
# Conflits de hiérarchie non filtrés : le bruit des lignes de bilan et pays fiscaux revient.
"$SRC¦        if (m := re.match(r\"« ([^»]+) »\", c)) and m.group(1) in membres_en_usage¦        if True¦[V16]"
# Grandeur de concentration ignorée : une part des créances redevient « du chiffre d'affaires ».
"$SRC¦            grandeur = GRANDEURS_DE_CONCENTRATION.get(reference) if reference else None¦            grandeur = \"du chiffre d'affaires\"¦[V17]"
"$SRC¦                    if r.get(\"statut\") == \"decoupage_change\":¦                    if False:¦[V13b] la ligne Σ du TTM"
"$SRC¦                if c.get(\"concept\") == CONCEPT_DOUZE_MOIS:¦                if False:¦[V13b] la période des douze mois glissants"
# Signal d'acquisition significative (§4 bis) : le chiffre d'affaires de l'exercice de référence
# n'est plus transmis au producteur du signal — une acquisition au-dessus du seuil (part du CA) ne
# peut plus être comparée à rien, le signal disparaît en silence.
"$SRC¦    dernier_exercice_fin = max(fin_vers_fy, default=None)¦    dernier_exercice_fin = None¦[V18bis]"
# Garde (iv), lot P1 §8 addendum : `_choisir_terme` prend le terme d'ORIGINE (le plus ANCIENNEMENT
# déposé) au lieu du terme RETRAITÉ (le plus RÉCEMMENT déposé) — régression EXACTE de `c551003`.
# Sur le cas réel NVDA (jumeau lu), les douze mois par pays prennent le semestre 2025 d'origine :
# Σ pays = 323 559 M$ ≠ total socle 302 970 M$ — l'invariant de l'agrégat SUR LA VUE SERVIE doit
# rougir NOMMÉMENT ([V19]), sans faire tomber [V19ter]/[V19quater] pour une autre raison.
"$APPAR¦    plus_recent_filed = max(str(p.get(\"filed\") or \"\") for p in candidats)¦    plus_recent_filed = min(str(p.get(\"filed\") or \"\") for p in candidats)  # MUTATION : origine au lieu du retraité¦[V19]"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
