#!/usr/bin/env bash
# TEST NÉGATIF de `check_bac_a_calcul.py` (#96) — BIDIRECTIONNEL.
#
#   bash checks/negatif_bac_a_calcul.sh
#
# SATISFIABILITÉ — le check non muté est VERT : **255 vérifications OK, 0 échec** (mesuré avant toute
# mutation, hors ligne). DISCRIMINATION — une mutation par garde ci-dessous, et c'est l'assert VISÉ
# qui rougit.
#
# ⚠️ LES MUTATIONS QUI COMPTENT VRAIMENT sont celles du bac (1 à 13) : le bac est une frontière de
# SÉCURITÉ — la mécanique est écrite par un agent qui a lu du web. Chacune rouvre une porte précise
# (attribut, budget, coût d'appel, gel du tableau, taille des sorties…) et un programme de la batterie
# hostile doit alors PASSER, donc le check rougir.
#
# ⚠️ CE QUE LES MUTATIONS N'ONT PAS LE DROIT DE FAIRE : mettre le VPS à genoux (3,8 Go, 0 swap). Les
# cas hostiles qu'une mutation laisse passer sont donc choisis SANS danger une fois désarmés —
# `range(10 ** 6)` et non `10 ** 9`, une boucle de 10⁶ et non 10⁸. La puissance géante `10 ** 10 ** 10`
# n'est PAS rendue exécutable par une mutation : sans `math.pow`, elle calculerait un entier de dix
# milliards de chiffres. Sa mutation passe par la racine d'un négatif, que `math.pow` refuse aussi.
#
# Deux gardes ont été RETIRÉES à l'écriture parce qu'aucune mutation ne pouvait les faire rougir
# (6ᵉ faux vert) : le test de division par zéro de `_arith` (le filet de `executer` rend le même refus
# à la même ligne) et le refus explicite d'écrire dans un `_Gele` (le `_Gele` refuse lui-même).
set -u
cd "$(dirname "$0")/.." || exit 1

B="app/valorisation/bac_a_calcul.py"
C="app/valorisation/calculs.py"

CHECK="checks/check_bac_a_calcul.py"
NET=none

mutations=(
  # ── Le bac : la frontière de sécurité ──────────────────────────────────────────────────────
  "$B¦        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):¦        if isinstance(node, ast.Attribute):\n            return getattr(self.expr(node.value), node.attr)\n        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):¦hostile « attribut dunder »"
  "$B¦        if self.operations > self.budget:¦        if False:¦hostile « boucle qui épuise le budget »"
  "$B¦        cout = _COUT_APPEL.get(node.func.id, 1)¦        cout = 1¦hostile « croissance implicite en boucle »"
  "$B¦        propres[nom] = _geler(_valider_valeur(copy.deepcopy(v), nom))¦        propres[nom] = _valider_valeur(copy.deepcopy(v), nom)¦alias d'un dictionnaire signé"
  "$B¦    __setitem__ = __delitem__ = update = setdefault = pop = popitem = clear = _interdit  # type: ignore[assignment]¦    pass¦alias d'un dictionnaire signé"
  "$B¦    def _nom_affectable(self, nom: str) -> str:¦    def _nom_affectable(self, nom: str) -> str:\n        return nom¦réaffectation d'une hypothèse"
  "$B¦                if not _scalaire(gauche) or not (appartenance or _scalaire(droite)):¦                if False:¦hostile « comparaison de structures »"
  "$B¦        _compter(sorties, LIMITE_ELEMENTS * 10)¦        pass¦hostile « structure qui se partage elle-même »"
  "$B¦            self.portees.pop()¦            pass¦hostile « fuite de compréhension »"
  "$B¦    if isinstance(v, bool) or isinstance(v, str):¦    if True:¦une hypothèse porteuse de comportement est refusée"
  "$B¦    ast.Pow: lambda a, b: math.pow(a, b),¦    ast.Pow: lambda a, b: complex(a) ** b if a < 0 else math.pow(a, b),¦hostile « racine d'un négatif »"
  "$B¦    if isinstance(r, float) and not math.isfinite(r):¦    if False:¦hostile « débordement flottant »"
  "$B¦    if len(r) > LIMITE_ELEMENTS:¦    if False:¦le plafond de range refuse AVANT d'allouer"
  "$B¦        if not isinstance(v, bool):¦        if False:¦hostile « condition non booléenne »"
  "$B¦        if not isinstance(node.func, ast.Name) or node.func.id not in FONCTIONS:¦        if not isinstance(node.func, ast.Name):¦une fonction hors liste est refusée en la NOMMANT"
  "$B¦        if e.ligne is None:   # refus levé hors de l'interprète (hypothèse gelée) : on le situe¦        if False:¦un refus du tableau gelé est situé à sa ligne"

  # ── La structure du bac ────────────────────────────────────────────────────────────────────
  "$B¦    \"exp\": lambda x: math.exp(_num(x)),¦    \"exp\": lambda x: math.exp(_num(x)),\n    \"evalue\": lambda x: eval(str(x)),¦le bac n'emploie pas \`eval(\`"
  "$B¦import math¦import math\nimport os¦le bac n'importe que sa liste déclarée"

  # ── Les gabarits maison : une formule fausse mais plausible ────────────────────────────────
  "$C¦    return f * (1.0 + g) / (r - g)¦    return f / (r - g)¦Gordon"
  "$C¦        if valeur(milieu) < v:¦        if valeur(milieu) > v:¦aller-retour à 7 %"
  "$C¦    if not 0.0 <= p <= 1.0:¦    if not 0.0 <= p <= 2.0:¦probabilité > 1"
  "$C¦    if not b <= c <= h:¦    if False:¦fourchette croisée"
  "$C¦    return actualiser(fs, r) + vt / (1.0 + r) ** len(fs)¦    return actualiser(fs, r) + vt / (1.0 + r) ** (len(fs) - 1)¦DCF d'une perpétuité"
  "$C¦    return (v - _nombre(prix, \"prix\")) / v¦    return max(0.0, (v - _nombre(prix, \"prix\")) / v)¦marge négative, pas tronquée"
  "$C¦    return a + p¦    return a¦par action DILUÉE"
  "$C¦# Le catalogue exposé au bac à calcul¦def gabarit_oublie(x: float) -> float:\n    return x\n\n\n# Le catalogue exposé au bac à calcul¦catalogue = gabarits publics"
)

source "$(dirname "$0")/_negatif.sh"
run_mutations
