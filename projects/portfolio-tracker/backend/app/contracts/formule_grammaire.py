"""La GRAMMAIRE FERMÉE d'une formule d'appariement — ce qui la rend EXÉCUTABLE (#72, maillon 4).

POURQUOI LA FORME DE `formule` DEVIENT UNE CONTRAINTE DE CONTRAT
-----------------------------------------------------------------
Jusqu'au maillon 4, `formule` n'était qu'une chaîne de ≥3 caractères, écrite pour être **lue** : elle
servait à ce que le lecteur puisse CONTESTER l'hypothèse (#67), et le pont ne lui demandait que de
nommer exactement les mêmes concepts que `concepts` ([W]). Une prose (« Pour chaque exercice, les
actifs moins les dettes ») y passait donc sans rien casser, et le remède a été deux fois un
durcissement de prompt — dont la mesure du 2026-09-18 a montré qu'il tient **un passage sur deux**
(rouge sur MSFT au passage 1, vert au passage 2 sur le même corpus,
`feedback_jugement_modele_instable_entre_passages`).

Le maillon 4 change la CHARGE du champ : la formule n'est plus seulement lue, elle est **évaluée**.
Une prose n'y devient pas « moins lisible », elle devient **inexécutable** — et une ligne
inexécutable repart au web chercher un nombre que l'émetteur dépose, en tier B, sous un log de repli.
Le geste est donc celui que le 00-REPRISE nomme d'avance : contraindre la FORME dans le contrat, et
non re-durcir le prompt une troisième fois.

CE QUE LA GRAMMAIRE ADMET — ET RIEN D'AUTRE
--------------------------------------------
  · des NOMS (identifiants), qui sont les concepts déposés — le pont [V]/[W] vérifie, lui, qu'ils
    sont réellement déposés et tous déclarés ; ici on ne regarde que la forme ;
  · des NOMBRES littéraux (entiers de conversion, et les décimaux que [X] refuse sur un
    `deterministe=True`) ;
  · les opérateurs binaires `+ - * /`, le `+`/`-` unaire, et les parenthèses.

Tout le reste est REFUSÉ : un appel de fonction, un accès d'attribut, une comparaison, un `if`, une
virgule (qui ferait un tuple), un mot de français (qui ne parse pas), une puissance, un modulo.
La liste est une LISTE BLANCHE de types de nœuds, jamais une liste noire de motifs interdits : une
liste noire laisse passer ce qu'elle n'a pas prévu, et ce qu'elle n'a pas prévu est exactement ce
qu'un modèle écrira la fois suivante.

⚠️ CE N'EST PAS UN BAC À SABLE D'EXÉCUTION, ET IL NE FAUT PAS LE LIRE COMME TEL. `evaluer_formule`
n'appelle JAMAIS `eval()` : elle parcourt l'arbre et calcule elle-même. La liste blanche n'est donc
pas une défense contre du code hostile (il n'y en a pas : la formule vient de notre propre modèle
sur notre propre inventaire) — c'est une garantie que **ce qui passe le contrat se calcule**, ce qui
est une propriété de complétude, pas de sécurité. Les confondre mènerait à relâcher la liste « puisque
ce n'est pas dangereux », et à retrouver des formules qui valident sans s'exécuter.

LES UNITÉS SONT UNE PROPRIÉTÉ DE L'ARBRE, PAS DES CONCEPTS
-----------------------------------------------------------
`dimension_formule` existe parce qu'un contrôle plus simple — « tous les concepts d'une formule
partagent la même unité » — aurait refusé les seuls cas où le calcul apporte quelque chose. Un
résultat par action (`USD / shares`) mélange légitimement deux unités ; une soustraction de deux
unités différentes, elle, ne veut rien dire et produirait un nombre d'apparence normale. Le
discriminant n'est donc pas « combien d'unités » mais **quel opérateur les rassemble** — et cela ne
se lit que sur l'arbre. Une addition exige deux dimensions égales ; un produit les compose.

Cible : pydantic v2 / Python 3.12 (container backend). Module PUR : aucune IO, rejouable hors-ligne.
"""
from __future__ import annotations

import ast
from collections import Counter
from typing import Mapping, Optional

__all__ = [
    "FormuleInexecutable",
    "DimensionIncoherente",
    "GRAMMAIRE_ADMISE",
    "analyser_formule",
    "noms_de_la_formule",
    "evaluer_formule",
    "dimension_formule",
    "rendre_dimension",
]


class FormuleInexecutable(ValueError):
    """La formule ne se calcule pas : forme hors grammaire, nom sans valeur, division par zéro.

    Hérite de `ValueError` délibérément — le contrat `AppariementItem` la laisse remonter telle
    quelle à pydantic, donc un refus de forme emprunte le tour de réparation déjà en place
    (`run_json_agent` réinjecte l'erreur de validation) au lieu d'ouvrir un second chemin de refus.
    """


class DimensionIncoherente(FormuleInexecutable):
    """Une somme ou une différence entre deux unités différentes. Sous-classe, parce que du point de
    vue de l'appelant c'est le même verdict — « cette formule ne produit pas un nombre » — mais le
    motif est distinct, et le distinguer permet de le COMPTER : une carte qui accumule des
    incohérences d'unité dit quelque chose sur l'apparieur, pas sur l'émetteur."""


# La liste BLANCHE. `ast.Load` y figure parce que tout `Name` en porte un ; l'omettre ferait refuser
# toutes les formules, et le message d'erreur parlerait d'un nœud que personne n'a écrit.
_NOEUDS_ADMIS: tuple[type, ...] = (
    ast.Expression,
    ast.BinOp, ast.UnaryOp,
    ast.Name, ast.Load,
    ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.UAdd, ast.USub,
)

GRAMMAIRE_ADMISE = (
    "noms de concepts déposés, nombres littéraux, opérateurs `+ - * /`, signe unaire et parenthèses"
)


def _refuser_noeud(noeud: ast.AST, formule: str) -> FormuleInexecutable:
    """Le message nomme le nœud REFUSÉ et la grammaire admise. Un « formule invalide » nu serait
    illisible pour le modèle au tour de réparation, qui ne saurait pas quoi retirer."""
    return FormuleInexecutable(
        f"« {formule} » n'est pas une expression de calcul : elle emploie "
        f"`{type(noeud).__name__}`, hors grammaire. Une formule ne contient que {GRAMMAIRE_ADMISE} — "
        "aucun mot de français, aucune énumération, aucune explication (celles-ci vont dans "
        "`hypotheses`, dont c'est exactement le rôle)")


def analyser_formule(formule: str) -> ast.Expression:
    """La formule, parsée et vérifiée contre la grammaire fermée. Pure. Lève `FormuleInexecutable`.

    Détenteur UNIQUE de « ce qu'est une formule » (#46) : le contrat l'appelle pour REFUSER,
    l'évaluateur pour CALCULER, le pont pour LISTER les concepts référencés. Trois lecteurs, une
    règle — une deuxième analyse (un `re` qui cherche des CamelCase, par exemple) re-divergerait au
    premier correctif, et la divergence serait muette : le pont validerait un ensemble de concepts
    que l'évaluateur n'emploierait pas.
    """
    texte = (formule or "").strip()
    if not texte:
        raise FormuleInexecutable("formule vide : il n'y a rien à calculer")
    try:
        arbre = ast.parse(texte, mode="eval")
    except SyntaxError as e:
        raise FormuleInexecutable(
            f"« {texte} » ne se lit pas comme une expression de calcul ({e.msg}). Une formule ne "
            f"contient que {GRAMMAIRE_ADMISE} : un mot de français, une virgule d'énumération ou "
            "une phrase la rendent inanalysable") from e
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, _NOEUDS_ADMIS):
            raise _refuser_noeud(noeud, texte)
        if isinstance(noeud, ast.Constant):
            # `True`/`False` sont des `int` en Python — les laisser passer ferait entrer un booléen
            # dans une somme et produirait 0 ou 1 sans erreur visible. Une chaîne, elle, se
            # concaténerait avec `+` : deux montants « additionnés » donneraient un texte.
            if isinstance(noeud.value, bool) or not isinstance(noeud.value, (int, float)):
                raise FormuleInexecutable(
                    f"« {texte} » porte le littéral {noeud.value!r}, qui n'est pas un nombre : un "
                    "calcul n'additionne ni des textes ni des booléens")
    return arbre


def noms_de_la_formule(formule: str) -> set[str]:
    """Les identifiants référencés par la formule. Pure, et lue depuis l'ARBRE.

    Sous la grammaire fermée, TOUT nom d'une formule est un concept : il n'y a ni fonction, ni
    variable locale, ni mot-clef. C'est ce qui permet au pont [W] de comparer cet ensemble aux
    `concepts` déclarés et d'être exhaustif — un relevé lexical (`\\b[A-Z][A-Za-z0-9]*\\b`) laissait
    filer un nom en minuscule, qui échappait donc à la confrontation avec l'inventaire [V] tout en
    faisant échouer l'évaluation plus tard, loin de sa cause.
    """
    return {n.id for n in ast.walk(analyser_formule(formule)) if isinstance(n, ast.Name)}


def evaluer_formule(formule: str, valeurs: Mapping[str, float]) -> float:
    """Calcule la formule sur les valeurs fournies. Pure. Lève `FormuleInexecutable`.

    N'emploie PAS `eval()` : l'arbre est parcouru et chaque nœud calculé ici. Ce n'est pas une
    précaution de sécurité (cf. l'en-tête) — c'est ce qui garantit que le seul calcul possible est
    celui que la grammaire décrit, et donc que « le contrat accepte » et « le code calcule » ne
    peuvent pas diverger.
    """
    return _calculer(analyser_formule(formule).body, valeurs, formule)


def _calculer(noeud: ast.AST, valeurs: Mapping[str, float], formule: str) -> float:
    if isinstance(noeud, ast.Constant):
        return float(noeud.value)
    if isinstance(noeud, ast.Name):
        if noeud.id not in valeurs:
            raise FormuleInexecutable(
                f"« {formule} » référence `{noeud.id}`, sans valeur résolue. Ce n'est PAS un zéro : "
                "un concept qu'on n'a pas su lire dans le dépôt est un trou, et le combler par zéro "
                "inverserait le signe de toute soustraction où il figure (#32)")
        return float(valeurs[noeud.id])
    if isinstance(noeud, ast.UnaryOp):
        v = _calculer(noeud.operand, valeurs, formule)
        return -v if isinstance(noeud.op, ast.USub) else v
    if isinstance(noeud, ast.BinOp):
        g = _calculer(noeud.left, valeurs, formule)
        d = _calculer(noeud.right, valeurs, formule)
        if isinstance(noeud.op, ast.Add):
            return g + d
        if isinstance(noeud.op, ast.Sub):
            return g - d
        if isinstance(noeud.op, ast.Mult):
            return g * d
        if d == 0:
            # Un dénominateur nul est un fait sur l'émetteur (une biotech sans chiffre d'affaires),
            # pas une panne de calcul. On le NOMME : la ligne devient un mandat motivé, jamais un
            # `inf` ni un `None` qui se lirait comme « non collecté ».
            raise FormuleInexecutable(
                f"« {formule} » divise par zéro : le dénominateur vaut 0 chez cet émetteur. Le ratio "
                "n'existe pas pour lui — c'est une information sur l'entreprise, pas un échec de "
                "collecte, et la publier en `inf` ou en 0 dirait le contraire")
        return g / d
    raise _refuser_noeud(noeud, formule)   # inatteignable après `analyser_formule` — garde de forme


# ─────────────────────────────── les UNITÉS, lues sur l'arbre ───────────────────────────────────

# Une dimension = les unités au numérateur et au dénominateur, avec leur exposant. Canonique (triée,
# exposants nuls retirés) pour que l'égalité `==` soit celle qu'on croit : `USD/shares` obtenu par
# deux chemins différents doit se comparer égal, sinon l'addition de deux ratios identiques
# refuserait.
Dimension = tuple[tuple[str, int], ...]


def _canon(c: Counter) -> Dimension:
    return tuple(sorted((u, n) for u, n in c.items() if n))


def rendre_dimension(d: Dimension) -> str:
    """`USD/shares`, `USD`, `sans dimension`. Pour que le motif d'un refus se lise."""
    if not d:
        return "sans dimension"
    haut = [u if n == 1 else f"{u}^{n}" for u, n in d if n > 0]
    bas = [u if n == -1 else f"{u}^{-n}" for u, n in d if n < 0]
    return ("·".join(haut) or "1") + ("/" + "·".join(bas) if bas else "")


def dimension_formule(formule: str, unites: Mapping[str, str]) -> Dimension:
    """La dimension du résultat, dérivée des unités de chaque concept. Pure.

    `unites` = concept → unité du point retenu (`USD`, `shares`, `pure`…), telle que
    `companyfacts` la dépose. Lève `DimensionIncoherente` sur une somme d'unités différentes.

    ⚠️ Un littéral n'a AUCUNE dimension, et c'est délibéré : `Assets - 1` est donc refusé. Un
    nombre nu retranché d'un montant est soit une erreur de saisie, soit un facteur d'échelle mal
    placé ; l'admettre « parce que c'est inoffensif » ferait passer les deux.
    """
    return _canon(_dimension(analyser_formule(formule).body, unites, formule))


def _dimension(noeud: ast.AST, unites: Mapping[str, str], formule: str) -> Counter:
    if isinstance(noeud, ast.Constant):
        return Counter()
    if isinstance(noeud, ast.Name):
        unite = unites.get(noeud.id)
        if unite is None:
            raise FormuleInexecutable(
                f"« {formule} » référence `{noeud.id}`, dont l'unité n'a pas été résolue")
        return Counter({unite: 1})
    if isinstance(noeud, ast.UnaryOp):
        return _dimension(noeud.operand, unites, formule)
    if isinstance(noeud, ast.BinOp):
        g = _dimension(noeud.left, unites, formule)
        d = _dimension(noeud.right, unites, formule)
        if isinstance(noeud.op, (ast.Add, ast.Sub)):
            if _canon(g) != _canon(d):
                raise DimensionIncoherente(
                    f"« {formule} » additionne ou soustrait {rendre_dimension(_canon(g))} et "
                    f"{rendre_dimension(_canon(d))} : deux grandeurs d'unités différentes ne "
                    "s'ajoutent pas. Le nombre produit aurait l'air normal et ne voudrait rien dire")
            return g
        if isinstance(noeud.op, ast.Mult):
            return g + d
        out = Counter(g)
        out.subtract(d)
        return out
    raise _refuser_noeud(noeud, formule)   # inatteignable — garde de forme
