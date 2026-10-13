#!/usr/bin/env bash
# TEST NÉGATIF de `check_ratios_maison.py` — une mutation par convention des ratios maison, chacune
# exigeant exit≠0 + FAIL sur l'assert NOMMÉ + bilan atteint (harnais `_negatif.sh`).
#   bash checks/negatif_ratios_maison.sh
#
# ⚠️ Le CAPITAL EMPLOYÉ est une ligne du GABARIT (`socle_comptes.yaml`) : ses mutations vivent dans
# `negatif_socle_comptes.sh`. Les refus [U] du référentiel (ratio inconnu, unité convertie) vivent chez
# leur détenteur, `negatif_frameworks_definitions.sh`.
set -u
cd "$(dirname "$0")/.." || exit 1
CHECK="checks/check_ratios_maison.py"
SRC="app/knowledge/ratios_maison.py"

mutations=(
# Le rendement se rapporte au capital du SEUL jour de clôture, pas au capital moyen de l'exercice.
"$SRC¦        return _moyenne(_cellule(structure, ligne, ouverture[\"id\"]), _cellule(structure, ligne, cloture[\"id\"]))¦        return _cellule(structure, ligne, cloture[\"id\"])¦capital employé MOYEN de l'exercice"
# L'ouverture choisie est la clôture elle-même (comparaison large) — même faute, par une autre porte.
"$SRC¦    fins_avant = sorted(f for f in bilans if f < exercice[\"fin\"])¦    fins_avant = sorted(f for f in bilans if f <= exercice[\"fin\"])¦capital employé MOYEN de l'exercice"
# Un impôt négatif gonfle le résultat après impôt (taux non borné).
"$SRC¦        taux = Valeur(min(max(impot.valeur / rai.valeur, 0.0), 1.0))¦        taux = Valeur(impot.valeur / rai.valeur)¦impôt NÉGATIF"
# Un capital moyen négatif porte un rendement (de signe inversé).
"$SRC¦    if den.valeur <= 0:¦    if den.valeur == 0:¦capital employé moyen négatif"
# La conversion devient la moyenne des rapports annuels.
"$SRC¦        return sum(v.valeur for v in cfo) / s_rn * 100, f\"{_libelle_fenetre(exs)} — {source}\"¦        return sum(c.valeur / r.valeur for c, r in zip(cfo, rn)) / len(rn) * 100, f\"{_libelle_fenetre(exs)} — {source}\"¦Σ résultat net sur TROIS exercices"
# La conversion porte sur cinq exercices au lieu de trois.
"$SRC¦NB_EXERCICES_CONVERSION = 3¦NB_EXERCICES_CONVERSION = 5¦Σ résultat net sur TROIS exercices"
# Une perte cumulée « se convertit » (rapport de deux négatifs).
"$SRC¦        if s_rn <= 0:¦        if False:¦une perte cumulée ne se convertit pas"
# La pente n'est plus une régression : premier et dernier point seulement.
"$SRC¦        pente = sum((x - mx) * (y - my) for x, y in zip(xs, rdts)) / sum((x - mx) ** 2 for x in xs)¦        pente = (rdts[-1] - rdts[0]) / (xs[-1] - xs[0])¦régression linéaire (autre algorithme)"
# La moyenne se fait sur les rendements DISPONIBLES quand certains manquent (moyenne sur trois au lieu de cinq).
"$SRC¦        absents = [(l.fin, l.rendement_du_capital_employe.motif) for l in lignes¦        lignes = [l for l in lignes if l.rendement_du_capital_employe.valeur is not None]\n        absents = [(l.fin, l.rendement_du_capital_employe.motif) for l in lignes¦la moyenne cinq ans n'est pas établie"
# Le capital par point de croissance divise par un taux, pas par des points.
"$SRC¦    points = (ca[1].valeur / ca[0].valeur - 1) * 100¦    points = (ca[1].valeur / ca[0].valeur - 1)¦capital par point de croissance ≈"
# Une cellule absente vaut zéro (le zéro fabriqué).
"$SRC¦        return Valeur(None, f\"{ligne} absent du socle au {periode_id[-10:]}\")¦        return Valeur(0.0)¦la ligne NOMMÉE"
# Un ratio inconnu rend un None silencieux.
"$SRC¦        raise ValueError(f\"ratio maison « {ratio_id} » inconnu ({sorted(RATIOS)})\")¦        return None, \"non établi\"¦un ratio inconnu"
# Le texte du socle annonce un calcul (marqueur #78) — la pièce perdrait son tampon `mesure`.
"$SRC¦    out = [\"\", f\"Ratios maison (définitions¦    out = [\"\", f\"Ratios maison, calcul : (définitions¦reste tamponné \`mesure\`"
# La version des définitions sort de l'empreinte : en changer ne republierait pas la pièce.
"app/knowledge/socle_comptes.py¦    return (structure.get(\"version_gabarit\"), structure.get(\"version_ratios\"),¦    return (structure.get(\"version_gabarit\"), None,¦changer la version des définitions"
# L'encadré ne lit plus le ratio (le chiffre resterait « non établi » sur tout émetteur).
"app/agents/v2/frameworks.py¦                v, periode = ratio_du_socle(socle, d.socle.ratio)¦                v, periode = None, \"non établi : ratio non lu par l'encadré\"¦lu par le ratio"
)
source "$(dirname "$0")/_negatif.sh"
run_mutations
