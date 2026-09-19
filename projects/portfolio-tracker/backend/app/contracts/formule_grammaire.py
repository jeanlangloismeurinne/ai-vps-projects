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

  · une RÉFÉRENCE TEMPORELLE `Concept[k]` (voir la section suivante), qui désigne le même concept à
    un exercice antérieur.

Tout le reste est REFUSÉ : un appel de fonction, un accès d'attribut, une comparaison, un `if`, une
virgule (qui ferait un tuple), un mot de français (qui ne parse pas), une puissance, un modulo.
La liste est une LISTE BLANCHE de types de nœuds, jamais une liste noire de motifs interdits : une
liste noire laisse passer ce qu'elle n'a pas prévu, et ce qu'elle n'a pas prévu est exactement ce
qu'un modèle écrira la fois suivante.

LE TEMPOREL EST UNE PROPRIÉTÉ DE LA RÉFÉRENCE, PAS UN CONCEPT NEUF
------------------------------------------------------------------
`Concept[k]` (k entier <= 0) réfère au concept à un exercice DÉCALÉ : `Concept` ou `Concept[0]` est
l'exercice le plus récent, `Concept[-1]` le précédent, `Concept[-2]` celui d'avant. C'est ce que la
grammaire ne savait pas dire, et son absence coulait tout l'archétype `rentable` : une question de
CROISSANCE (« progression de l'activité, exercice par exercice ») n'a pas de forme sans référence à
la période antérieure, alors le modèle inventait un concept `Revenues_previous_year` — un nom que
l'émetteur ne dépose pas, donc un refus [V]/[W] qui, faute de refus PAR INGRÉDIENT, jetait la carte
entière (NVDA/MSFT `carte=aucune`, mesuré le 2026-09-19).

Deux décisions de forme, chacune contre une tentation plus simple et fausse :

  · L'offset porte sur le NOM, il ne crée pas un nom. `noms_de_la_formule` rend `Revenues` pour
    `Revenues[-1]` comme pour `Revenues` : le pont [V]/[W] confronte donc à l'inventaire un concept
    RÉELLEMENT déposé, et il n'y a jamais de `Revenues_previous_year` à inventer. C'est #57 appliqué
    à la formule — la période est une propriété de la RELATION (fait ↔ exercice), pas une syllabe du
    concept. L'évaluateur, lui, lit le grain fin `(concept, offset)` via `references_de_la_formule`.
  · L'offset est RELATIF, jamais absolu (`Concept[-1]`, pas `Concept@FY2024`). Une carte se recalcule
    à chaque nouveau dépôt (#67) : `[-1]` désigne toujours « l'exercice d'avant » quelle que soit
    l'année du calcul, là où une année en dur pointerait un exercice figé et se périmerait en
    silence au dépôt suivant. Et il est <= 0 : un exercice postérieur au plus récent n'existe pas.

Un `Subscript` n'est admis que sur un NOM et avec un indice entier <= 0 : `(Assets - Cash)[-1]` ou
`Revenues[k]` (k variable) sont refusés à la forme, avant toute évaluation.

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
    "references_de_la_formule",
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
    ast.Subscript,          # `Concept[-1]` — la référence temporelle, contrainte par `_offset_du_subscript`
    ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.UAdd, ast.USub,
)

GRAMMAIRE_ADMISE = (
    "noms de concepts déposés (avec un décalage d'exercice optionnel `Concept[-1]`), nombres "
    "littéraux, opérateurs `+ - * /`, signe unaire et parenthèses"
)


def _refuser_noeud(noeud: ast.AST, formule: str) -> FormuleInexecutable:
    """Le message nomme le nœud REFUSÉ et la grammaire admise. Un « formule invalide » nu serait
    illisible pour le modèle au tour de réparation, qui ne saurait pas quoi retirer."""
    return FormuleInexecutable(
        f"« {formule} » n'est pas une expression de calcul : elle emploie "
        f"`{type(noeud).__name__}`, hors grammaire. Une formule ne contient que {GRAMMAIRE_ADMISE} — "
        "aucun mot de français, aucune énumération, aucune explication (celles-ci vont dans "
        "`hypotheses`, dont c'est exactement le rôle)")


def _offset_du_subscript(noeud: ast.Subscript, formule: str) -> int:
    """L'offset d'exercice d'une référence temporelle `Concept[k]`. Pur. Lève `FormuleInexecutable`.

    Détenteur UNIQUE de « ce qu'est une référence temporelle » : la validation de forme
    (`analyser_formule`), le relevé des références (`references_de_la_formule`), l'évaluation
    (`_calculer`) et la dimension (`_dimension`) l'appellent tous, pour que « ce qui passe le
    contrat » et « ce que le code lit » ne puissent pas diverger.

    Contraint : la base est un NOM (`Revenues[-1]`, pas `(Assets - Cash)[-1]`), l'indice est un
    ENTIER littéral (négatif via `[-1]`, ou `0`), et il est <= 0 — un exercice postérieur au plus
    récent n'existe pas.
    """
    if not isinstance(noeud.value, ast.Name):
        raise FormuleInexecutable(
            f"« {formule} » indexe une expression qui n'est pas un concept : seul un NOM peut porter "
            "un décalage d'exercice (`Revenues[-1]`), jamais un calcul entre parenthèses")
    nom = noeud.value.id
    sl = noeud.slice
    if (isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub)
            and isinstance(sl.operand, ast.Constant)
            and isinstance(sl.operand.value, int) and not isinstance(sl.operand.value, bool)):
        return -sl.operand.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int) and not isinstance(sl.value, bool):
        if sl.value > 0:
            raise FormuleInexecutable(
                f"« {formule} » emploie un décalage POSITIF `{nom}[{sl.value}]` : un exercice "
                "postérieur au plus récent n'existe pas. Les décalages vont vers le PASSÉ "
                "(`[0]` = dernier exercice, `[-1]` = précédent, `[-2]` celui d'avant)")
        return sl.value  # 0
    raise FormuleInexecutable(
        f"« {formule} » indexe `{nom}` par autre chose qu'un entier d'exercice : un décalage temporel "
        "est un entier <= 0 (`[-1]`, `[-2]`), jamais un nom, un décimal ni une expression")


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
        if isinstance(noeud, ast.Subscript):
            # La FORME du décalage est vérifiée ici, avant toute évaluation : un `Revenues[2]` (futur)
            # ou un `(a+b)[0]` parse (ses nœuds sont admis) mais ne décrit pas une référence temporelle.
            _offset_du_subscript(noeud, texte)
        if isinstance(noeud, ast.Constant):
            # `True`/`False` sont des `int` en Python — les laisser passer ferait entrer un booléen
            # dans une somme et produirait 0 ou 1 sans erreur visible. Une chaîne, elle, se
            # concaténerait avec `+` : deux montants « additionnés » donneraient un texte.
            if isinstance(noeud.value, bool) or not isinstance(noeud.value, (int, float)):
                raise FormuleInexecutable(
                    f"« {texte} » porte le littéral {noeud.value!r}, qui n'est pas un nombre : un "
                    "calcul n'additionne ni des textes ni des booléens")
    return arbre


def _references(noeud: ast.AST, formule: str) -> set[tuple[str, int]]:
    """Les couples (concept, offset) sous un nœud validé. Récursif, JAMAIS `ast.walk` : un
    `Subscript` porte un `Name` que `ast.walk` verrait à part, et le compterait alors deux fois — une
    fois comme référence temporelle, une fois comme offset 0. La descente contrôlée l'évite."""
    if isinstance(noeud, ast.Subscript):
        return {(noeud.value.id, _offset_du_subscript(noeud, formule))}  # type: ignore[union-attr]
    if isinstance(noeud, ast.Name):
        return {(noeud.id, 0)}
    if isinstance(noeud, ast.Constant):
        return set()
    if isinstance(noeud, ast.UnaryOp):
        return _references(noeud.operand, formule)
    if isinstance(noeud, ast.BinOp):
        return _references(noeud.left, formule) | _references(noeud.right, formule)
    return set()   # inatteignable après `analyser_formule` — garde de forme


def references_de_la_formule(formule: str) -> set[tuple[str, int]]:
    """Les références (concept, offset d'exercice) d'une formule. Pure, lue depuis l'ARBRE.

    `Revenues` → `(Revenues, 0)` ; `Revenues[-1]` → `(Revenues, -1)`. C'est le grain que l'évaluateur
    emploie : un même concept peut figurer à DEUX exercices (une croissance annuelle), et il faut
    alors deux valeurs distinctes. `noms_de_la_formule` en est la projection sur les concepts.
    """
    return _references(analyser_formule(formule).body, formule)


def noms_de_la_formule(formule: str) -> set[str]:
    """Les CONCEPTS référencés par la formule, offset projeté. Pure, lue depuis l'ARBRE.

    Sous la grammaire fermée, tout nom d'une formule est un concept : il n'y a ni fonction, ni
    variable locale, ni mot-clef. C'est ce qui permet au pont [W] de comparer cet ensemble aux
    `concepts` déclarés et d'être exhaustif. Un décalage d'exercice NE crée PAS de concept :
    `Revenues[-1]` rend `Revenues`, donc le pont confronte à l'inventaire un concept réellement
    déposé, et il n'y a jamais de `Revenues_previous_year` inventé à refuser (la faute qui coulait
    l'archétype `rentable`).
    """
    return {c for c, _ in references_de_la_formule(formule)}


def evaluer_formule(formule: str, valeurs: Mapping[tuple[str, int], float]) -> float:
    """Calcule la formule sur les valeurs fournies. Pure. Lève `FormuleInexecutable`.

    `valeurs` est keyée par (concept, offset) — le grain de `references_de_la_formule` : une même
    formule peut lire un concept à deux exercices (`Revenues[0]` et `Revenues[-1]`). Une valeur y est
    donc une PÉRIODE d'un concept, pas un concept.

    N'emploie PAS `eval()` : l'arbre est parcouru et chaque nœud calculé ici. Ce n'est pas une
    précaution de sécurité (cf. l'en-tête) — c'est ce qui garantit que le seul calcul possible est
    celui que la grammaire décrit, et donc que « le contrat accepte » et « le code calcule » ne
    peuvent pas diverger.
    """
    return _calculer(analyser_formule(formule).body, valeurs, formule)


def _valeur_reference(cle: tuple[str, int], valeurs: Mapping[tuple[str, int], float],
                      formule: str) -> float:
    concept, offset = cle
    if cle not in valeurs:
        libelle = concept if offset == 0 else f"{concept}[{offset}]"
        raise FormuleInexecutable(
            f"« {formule} » référence `{libelle}`, sans valeur résolue. Ce n'est PAS un zéro : un "
            "concept qu'on n'a pas su lire dans le dépôt (ou pas à cet exercice-là) est un trou, et "
            "le combler par zéro inverserait le signe de toute soustraction où il figure (#32)")
    return float(valeurs[cle])


def _calculer(noeud: ast.AST, valeurs: Mapping[tuple[str, int], float], formule: str) -> float:
    if isinstance(noeud, ast.Constant):
        return float(noeud.value)
    if isinstance(noeud, ast.Subscript):
        return _valeur_reference(
            (noeud.value.id, _offset_du_subscript(noeud, formule)), valeurs, formule)  # type: ignore[union-attr]
    if isinstance(noeud, ast.Name):
        return _valeur_reference((noeud.id, 0), valeurs, formule)
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


def _dimension_nom(nom: str, unites: Mapping[str, str], formule: str) -> Counter:
    # L'unité est keyée par CONCEPT : un décalage d'exercice ne change pas l'unité d'un concept
    # (`Revenues[-1]` est en `USD` comme `Revenues`), donc `Revenues[0] - Revenues[-1]` est
    # dimensionnellement homogène et une croissance `.../Revenues[-1]` est bien « sans dimension ».
    unite = unites.get(nom)
    if unite is None:
        raise FormuleInexecutable(
            f"« {formule} » référence `{nom}`, dont l'unité n'a pas été résolue")
    return Counter({unite: 1})


def _dimension(noeud: ast.AST, unites: Mapping[str, str], formule: str) -> Counter:
    if isinstance(noeud, ast.Constant):
        return Counter()
    if isinstance(noeud, ast.Subscript):
        return _dimension_nom(noeud.value.id, unites, formule)  # type: ignore[union-attr]
    if isinstance(noeud, ast.Name):
        return _dimension_nom(noeud.id, unites, formule)
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
