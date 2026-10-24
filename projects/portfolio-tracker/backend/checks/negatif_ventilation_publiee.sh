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
PERI="app/knowledge/perimetre.py"
XBRL="app/knowledge/ventilation_xbrl.py"
FEED="app/knowledge/ventilation_feed.py"
APPAR="app/knowledge/appariement_feed.py"

mutations=(
# Qualificateur neutre non retiré : les faits `secteurs` (toujours qualifiés par
# `ConsolidationItemsAxis=OperatingSegmentsMember`) portent alors « un axe de plus » et sont
# disqualifiés — l'axe secteurs perd ses cellules.
"$SRC¦    restants = [(a, m) for (a, m) in membres if (a, m) not in neutres]¦    restants = list(membres)¦[V1]"
# Hiérarchie ignorée (raccords de la VUE, lot P1 §8 point 2) : les enfants de Data Center rejoignent
# le premier niveau au cumul du 10-Q — la somme dépasse le total publié, le raccord ne boucle plus.
"$PERI¦        pn = premier_niveau_de(membres, parent_de)¦        pn = set(membres)¦[V15ter]"
# Tolérance de bouclage multipliée par 1 000 : l'écart réel de resultat_exploitation (−8 910 M$)
# est absorbé, le raccord devient « boucle » au lieu de « non_ventile ».
"$PERI¦            statut = \"boucle\" if abs(reste) <= tolerance_bouclage(total, somme) else \"non_ventile\"¦            statut = \"boucle\" if abs(reste) <= tolerance_bouclage(total, somme) * 1000 else \"non_ventile\"¦[V4]"
# `xsi:nil` lu comme zéro : un fait sans texte (nil ou vide) est désormais lu « 0 » au lieu
# d'être écarté — le garde-fou visible de `lire_instance` (le test `xsi:nil`) reste en place, mais
# la valeur par défaut qu'il protégeait est maintenant fabriquée juste avant lui.
"$XBRL¦        texte = (el.text or \"\").strip()¦        texte = (el.text or \"\").strip() or \"0\"¦[V9]"
# Sous-détail relevé : un axe en trop (non déclaré qualificateur) n'exclut plus le fait — la
# provision CCB × Apple Card de JPM devient un fait ordinaire au lieu d'un sous-détail.
"$SRC¦        if hors:¦        if False:¦[V10]"
# Douze mois glissants remplacés par le premier terme lu (l'exercice) : Data Center au 2026-07-26
# redevient 193 737 M$ au lieu de 277 798 M$ (l'identité à trois points, calculée sur la série).
"$PERI¦                    valeur, compo = douze_mois_glissants(pts, fin_ttm, f\"{axe}:{ligne}:{membre}\")¦                    valeur, compo = pts[0][\"val\"], douze_mois_glissants(pts, fin_ttm, f\"{axe}:{ligne}:{membre}\")[1]¦[V5]"
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
# Lot P1 tranche B — le regroupement cesse d'être une addition vérifiée : Edge Computing perd son
# historique (FY2024-FY2026), les douze mois par marché ne bouclent plus.
"$PERI¦_ADDITIONS = (\"renommage\", \"regroupement\")¦_ADDITIONS = (\"renommage\",)¦[V13]"
# Un membre au contenu CHANGÉ redevient continu : le semestre 2024 des pays (ancien critère
# d'attribution) serait servi dans le découpage de référence comme publié.
"$PERI¦            return None   # perturbé : cette valeur directe n'est PAS une continuité fiable¦            pass¦[V13d]"
# Le rendu tait l'addition vérifiée : un chiffre reconstitué se lirait comme publié.
"$SRC¦                    origine = (f\" — addition vérifiée : {_libs(c['passage_de'])}\" if c.get(\"passage_de\")¦                    origine = (\"\" if c.get(\"passage_de\")¦[V13b] Edge Computing FY2024"
# Le relevé brut redevient rendable : un lecteur additionnerait deux découpages.
"$SRC¦    if not vue.get(\"vue\"):¦    if False:¦[V13c]"
# Les cumuls ne sont plus relevés pour tous les membres : Hyperscale/AI Clouds/Edge Computing (et
# Data Center au même cumul) perdent leur valeur.
"$SRC¦                    if pid is None and fait.debut in debuts_cumul_valides:¦                    if False:¦[V15]"
# Conflits de hiérarchie non filtrés : le bruit des lignes de bilan et pays fiscaux revient.
"$SRC¦        if (m := re.match(r\"« ([^»]+) »\", c)) and m.group(1) in membres_en_usage¦        if True¦[V16]"
# Grandeur de concentration ignorée : une part des créances redevient « du chiffre d'affaires ».
"$SRC¦            grandeur = GRANDEURS_DE_CONCENTRATION.get(reference) if reference else None¦            grandeur = \"du chiffre d'affaires\"¦[V17]"
# Signal d'acquisition significative (§4 bis) : le chiffre d'affaires de l'exercice de référence
# n'est plus transmis au producteur du signal — une acquisition au-dessus du seuil (part du CA) ne
# peut plus être comparée à rien, le signal disparaît en silence.
"$SRC¦    dernier_exercice_fin = max(fin_vers_fy, default=None)¦    dernier_exercice_fin = None¦[V18bis]"
# Garde (iv), lot P1 §8 — la régression EXACTE de `c551003`, rejouée là où elle vivrait désormais :
# la série du découpage de référence prendrait la version d'ORIGINE (le jumeau, le dépôt le plus
# ancien) au lieu de la version RETRAITÉE au semestre 2025. Σ pays des douze mois = 323 559 M$ ≠
# 302 970 M$ : l'invariant de l'agrégat SUR LA VUE SERVIE doit rougir NOMMÉMENT ([V19]).
# (L'ancienne mutation de `appariement_feed._choisir_terme` est devenue inerte ICI : les douze mois
# de la vue se calculent sur une série à UNE valeur par période ; elle reste gardée par
# `check_appariement*` pour le socle.)
"$PERI¦    cellules_ref = [c for c in cellules if c.depot in depots_ref]¦    cellules_ref = list(reversed(cellules))  # MUTATION : origine au lieu du retraité¦[V19]"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
