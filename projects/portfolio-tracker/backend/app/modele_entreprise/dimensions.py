"""Les formules du classeur sont TYPÉES (lot M3 bis, roadmap V3 `13-lot-M3bis-structure.md` §5,
cause ④). NOUVEAU, PUR : aucune IO, rejouable hors-ligne.

POURQUOI UN MODULE À PART DE `app/contracts/formule_grammaire.py`. Cette grammaire-là calcule déjà
des formules d'APPARIEMENT sur des concepts XBRL, avec leurs propres unités brutes (`USD`,
`shares`…) traitées comme des atomes. Ici, les formules du classeur (`PassageAgrege.formule`) sont
des sommes de `bloc__variable` sur le catalogue MAISON (`modele_entreprise.yaml`), dont les unités
(`M$`, `%`, `$/unité`…) ne sont PAS des atomes isolés : elles se composent (`unités × $/unité = $`)
et portent une ÉCHELLE (`M$` = 10⁶ $) qu'une formule peut oublier de poser (`volume * prix_moyen`
rangé en `M$` sans `/ 1000000`). Ce module réutilise l'ARBRE de `formule_grammaire.analyser_formule`
(détenteur unique de la FORME d'une formule, #46) mais calcule sa propre DIMENSION PHYSIQUE —
montant, quantité, temps — et son échelle, lues dans la table `unites:` du référentiel maison.

CE QUI EST ARRÊTÉ (sur n'importe quel émetteur, principe fondateur n° 4) :
  · `…__cout_restant_de_developpement` (unité M$, `periode: sans_periode` — un STOCK) dans la
    formule d'une ligne `flux` (annuelle) du business plan ;
  · `…__part_de_marche` (unité `%`, sans dimension de montant) dans une ligne `chiffre_affaires`
    (unité M$) ;
  · `…__volume * …__prix_moyen` (unités, $/unité → $) rangé en M$ sans diviser par 10⁶.

LA PÉRIODE EST UNE PROPRIÉTÉ DU TERME ADDITIF, PAS DE L'ARBRE ENTIER. Dans un PRODUIT, un facteur
`sans_periode` est NEUTRE (`cout_restant_de_developpement * un_taux_sans_periode` ne change pas la
période du terme). Un terme ADDITIF (après aplatissement du chaînage `+`/`-` au premier niveau où
il apparaît — un terme sous parenthèses dans un produit, `a * (b + c)`, reste UN terme) de la
formule d'une ligne `flux` doit contenir au moins un facteur `exercice` et aucun `instant` ; d'une
ligne `instant`, l'inverse. Deux facteurs de périodes NON-NEUTRES différentes dans la même
expression (`+`, `-`, `*` ou `/`) sont déjà un refus (`FormuleInexecutable`), que la ligne cible
soit `flux` ou `instant` : un stock et un flux ne se mélangent jamais dans UN terme.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from app.contracts.formule_grammaire import FormuleInexecutable, analyser_formule

__all__ = [
    "DimensionIncoherente", "Dimension", "UniteInfo", "conversions_de", "dimension_de",
    "verifier_periode_ligne",
    "rendre_dimension",
]


class DimensionIncoherente(FormuleInexecutable):
    """Une somme ou une différence entre deux dimensions physiques (ou deux échelles) différentes
    du classeur — sous-classe de `FormuleInexecutable` (même verdict côté appelant : « cette
    formule ne produit pas un nombre »), distincte pour pouvoir COMPTER ce motif à part."""


# (exposant montant, exposant quantité, exposant temps) — canonique.
Dimension = tuple[int, int, int]

_NULLE: Dimension = (0, 0, 0)


@dataclass(frozen=True)
class UniteInfo:
    """Lue depuis `ReferentielModele.unites` (détenteur unique de la table, #46)."""
    dimension: Dimension
    echelle: float


def rendre_dimension(d: Dimension) -> str:
    """`montant^1`, `montant^1·quantite^-1`, `sans dimension` — pour que le motif d'un refus se lise."""
    if d == _NULLE:
        return "sans dimension"
    noms = ("montant", "quantite", "temps")
    parts = [f"{n}^{e}" for n, e in zip(noms, d) if e]
    return "·".join(parts)


def conversions_de(echelles: Iterable[float]) -> frozenset[float]:
    """Les facteurs de CONVERSION admis : les rapports entre deux échelles de la table `unites:`
    (`M$`/`$` = 10⁶, `%` → nombre = 100…), et leurs inverses. Un littéral d'une formule ne change
    l'échelle de lecture que s'il est l'un d'eux ; tout autre littéral (`0.9`, `2`) est un
    COEFFICIENT sans dimension, qui ne change ni la dimension ni l'échelle. Les deux lectures d'un
    même symbole sont structurellement indiscernables (#68) : c'est la table, détenteur unique,
    qui les sépare. Coût d'erreur nommé : un vrai coefficient égal à un rapport d'échelles
    (`× 100`) est lu comme une conversion et la formule est REFUSÉE (motif nommé, réécriture en
    décimal) — jamais acceptée à tort."""
    uniques = {e for e in echelles if e > 0}
    return frozenset(a / b for a in uniques for b in uniques if not math.isclose(a, b, rel_tol=1e-9))


def _est_conversion(v: float, conversions: frozenset[float]) -> bool:
    return any(math.isclose(v, c, rel_tol=1e-9) for c in conversions)


def _meme_echelle(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9)


def _dim_mult(a: Dimension, b: Dimension, signe: int) -> Dimension:
    return tuple(x + signe * y for x, y in zip(a, b))  # type: ignore[return-value]


def _bloc_variable(nom: str, formule: str) -> str:
    """La VARIABLE (après `bloc__`) d'un nom de formule — `partition`, jamais `rsplit` (cohérent
    avec `Architecture._coherence_interne`, qui lit `bloc_id, _, var_id = nom.partition("__")`)."""
    if "__" not in nom:
        raise FormuleInexecutable(
            f"« {formule} » référence `{nom}`, pas de la forme `bloc__variable` — une dimension ne "
            "se lit que sur une variable du catalogue")
    _bloc, _, var = nom.partition("__")
    return var


@dataclass(frozen=True)
class _Resultat:
    dimension: Dimension
    echelle: float
    periode: Optional[str]  # "exercice" | "instant" | None (sans_periode / neutre / littéral)
    # `valeur` est la VALEUR du nœud SI ET SEULEMENT SI c'est un littéral nu (ou son signe unaire) —
    # `None` sinon. Un littéral n'a pas de dimension propre (#5 de la spec), mais un `×`/`÷` par un
    # littéral est la façon dont une formule change d'ÉCHELLE DE LECTURE sans changer la grandeur
    # réelle qu'elle calcule (`/ 1000000` : le $ brut devient un M$ — la MÊME somme, relue en
    # millions). Un `×`/`÷` entre deux variables, lui, calcule une grandeur dérivée dont l'échelle
    # se COMPOSE normalement (`echelle_x × echelle_y`, `echelle_x / echelle_y` — un prix moyen =
    # chiffre d'affaires ÷ volume, une vraie division physique). Ce sont deux lectures différentes
    # du même symbole `/`, et seule la présence d'un littéral les distingue.
    valeur: Optional[float] = None


def _periode_combinee(a: Optional[str], b: Optional[str], formule: str) -> Optional[str]:
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    raise FormuleInexecutable(
        f"« {formule} » combine un facteur de période `{a}` et un facteur de période `{b}` dans "
        "une même expression — un stock (`sans_periode`/`instant`) et un flux (`exercice`) ne se "
        "mélangent jamais dans un même terme")


def _evaluer(noeud: ast.AST, unites: Mapping[str, UniteInfo], periodes: Mapping[str, Optional[str]],
            formule: str, conversions: frozenset[float] = frozenset()) -> _Resultat:
    if isinstance(noeud, ast.Constant):
        return _Resultat(_NULLE, 1.0, None, valeur=float(noeud.value))
    if isinstance(noeud, (ast.Name, ast.Subscript)):
        nom = noeud.value.id if isinstance(noeud, ast.Subscript) else noeud.id  # type: ignore[union-attr]
        var = _bloc_variable(nom, formule)
        info = unites.get(var)
        if info is None:
            raise FormuleInexecutable(
                f"« {formule} » référence `{nom}`, dont l'unité n'est pas résolue (variable `{var}` "
                "absente des fiches retenues par ce bloc)")
        periode = periodes.get(var)
        return _Resultat(info.dimension, info.echelle, periode)
    if isinstance(noeud, ast.UnaryOp):
        r = _evaluer(noeud.operand, unites, periodes, formule, conversions)
        if isinstance(noeud.op, ast.USub) and r.valeur is not None:
            return _Resultat(r.dimension, r.echelle, r.periode, valeur=-r.valeur)
        return r
    if isinstance(noeud, ast.BinOp):
        g = _evaluer(noeud.left, unites, periodes, formule, conversions)
        d = _evaluer(noeud.right, unites, periodes, formule, conversions)
        periode = _periode_combinee(g.periode, d.periode, formule)
        if isinstance(noeud.op, (ast.Add, ast.Sub)):
            if g.dimension != d.dimension or not _meme_echelle(g.echelle, d.echelle):
                raise DimensionIncoherente(
                    f"« {formule} » additionne ou soustrait {rendre_dimension(g.dimension)} "
                    f"(échelle {g.echelle}) et {rendre_dimension(d.dimension)} (échelle {d.echelle}) "
                    "— deux grandeurs de dimension ou d'échelle différentes ne s'ajoutent pas (un "
                    "coefficient s'écrit en décimal, `0.15` ; une conversion d'unité divise par le "
                    "rapport de deux échelles, `/ 1000000` pour des $ en M$)")
            return _Resultat(g.dimension, g.echelle, periode)
        if isinstance(noeud.op, ast.Mult):
            # Un littéral MULTIPLIE le nombre calculé — pour que la grandeur RÉELLE reste la même,
            # son échelle de lecture doit se DIVISER d'autant (`chiffre_affaires * 2` : le même
            # chiffre d'affaires réel, relu à une échelle deux fois plus fine, n'existe pas comme
            # cas utile ici, mais la règle reste symétrique et cohérente avec la division ci-dessous).
            # … mais SEULEMENT si le littéral est une conversion de la table : sinon c'est un
            # coefficient (`chiffre_affaires * 0.9`), neutre — même dimension, même échelle.
            if d.valeur is not None and g.valeur is None:
                return _Resultat(g.dimension, g.echelle / d.valeur
                                 if _est_conversion(d.valeur, conversions) else g.echelle, periode)
            if g.valeur is not None and d.valeur is None:
                return _Resultat(d.dimension, d.echelle / g.valeur
                                 if _est_conversion(g.valeur, conversions) else d.echelle, periode)
            return _Resultat(_dim_mult(g.dimension, d.dimension, 1), g.echelle * d.echelle, periode)
        # Division. Un littéral DIVISEUR (`… / 1000000`) ne calcule pas une grandeur dérivée : il
        # REDIT la même grandeur réelle à une échelle 1000000 fois plus grossière (le $ brut devient
        # un M$) — son échelle de lecture se MULTIPLIE donc par le littéral, à l'inverse d'une
        # division entre deux VRAIES variables (un prix moyen = chiffre d'affaires ÷ volume, une
        # grandeur dérivée dont l'échelle se compose normalement, `echelle_g / echelle_d`).
        # Même réserve : `/ 2` est un coefficient, `/ 1000000` une conversion.
        if d.valeur is not None and g.valeur is None:
            return _Resultat(g.dimension, g.echelle * d.valeur
                             if _est_conversion(d.valeur, conversions) else g.echelle, periode)
        return _Resultat(_dim_mult(g.dimension, d.dimension, -1), g.echelle / d.echelle, periode)
    raise FormuleInexecutable(f"« {formule} » n'est pas une expression de calcul (nœud non géré)")


def dimension_de(formule: str, unites: Mapping[str, UniteInfo],
                 conversions: frozenset[float]) -> tuple[Dimension, float]:
    """La DIMENSION et l'ÉCHELLE du résultat de `formule` (une `PassageAgrege.formule`, sur des noms
    `bloc__variable`). `unites` associe chaque VARIABLE (jamais le couple bloc+variable : la
    dimension d'une variable ne dépend pas du bloc qui la porte) à son `UniteInfo`. Lève
    `DimensionIncoherente`/`FormuleInexecutable`. `conversions` : `conversions_de(échelles de la
    table)` — obligatoire, pour qu'aucun appelant ne lise par défaut tout littéral comme un
    coefficient."""
    r = _evaluer(analyser_formule(formule).body, unites, {}, formule, conversions)
    return r.dimension, r.echelle


def _termes_additifs(noeud: ast.AST) -> list[ast.AST]:
    """Aplatit le chaînage `+`/`-` au premier niveau où il apparaît. Un terme sous parenthèses à
    l'intérieur d'un produit (`a * (b + c)`) N'EST PAS aplati ici : il reste UN terme de l'appelant,
    sa période se combine via `_periode_combinee` lors de l'évaluation du produit qui le contient."""
    if isinstance(noeud, ast.BinOp) and isinstance(noeud.op, (ast.Add, ast.Sub)):
        return _termes_additifs(noeud.left) + _termes_additifs(noeud.right)
    if isinstance(noeud, ast.UnaryOp):
        return _termes_additifs(noeud.operand)
    return [noeud]


def verifier_periode_ligne(formule: str, cadrage: str, unites: Mapping[str, UniteInfo],
                           periodes: Mapping[str, Optional[str]], *, ligne: str) -> None:
    """Pour une ligne `flux` : chaque terme additif de `formule` contient au moins un facteur de
    période `exercice` et aucun facteur `instant`. Pour une ligne `instant` : l'inverse. Un facteur
    `sans_periode` (ou un littéral) est NEUTRE dans un produit — il n'empêche ni ne satisfait la
    règle. Lève `FormuleInexecutable`, nommant la dimension trouvée et l'attendue."""
    if cadrage not in ("flux", "instant"):
        return
    attendu = "exercice" if cadrage == "flux" else "instant"
    arbre = analyser_formule(formule).body
    for terme in _termes_additifs(arbre):
        resultat = _evaluer(terme, unites, periodes, formule)
        if resultat.periode != attendu:
            trouve = resultat.periode or "sans période (neutre)"
            raise FormuleInexecutable(
                f"« {formule} » (ligne `{ligne}`, cadrage `{cadrage}`) : le terme "
                f"`{ast.unparse(terme)}` est de période {trouve}, attendue `{attendu}` — un "
                f"montant {'sans période ou instantané' if cadrage == 'flux' else 'annuel'} ne "
                f"se range jamais dans une ligne `{cadrage}` sans l'avoir ramené à l'exercice")
