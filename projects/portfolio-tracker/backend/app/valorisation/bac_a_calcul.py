"""Le BAC À CALCUL — où s'exécute la mécanique de valorisation propre à une entreprise (#96).

L'ARBITRAGE (utilisateur, 2026-09-28)
-------------------------------------
« On a besoin d'une mécanique libre car la typologie des entreprises à analyser est très large.
Pourtant je veux que le comité puisse juger un tableau d'hypothèses chiffrées et sourcées. Il faut que
l'agent décrive la mécanique qu'il va utiliser. Et pour l'implémenter, il pourrait avoir accès à une
sandbox python très simple qui fait des opérations mathématiques simples. »

Ce que ferait un vrai fonds : l'analyste construit le modèle propre au dossier (somme des programmes
pour RVMD, segments pour NVDA) sur les gabarits maison, le directeur de la recherche le signe, et la
MÉCANIQUE est conservée d'une révision à l'autre — seules les hypothèses changent. Le comité juge le
tableau d'hypothèses ; la mécanique, il la lit décrite en prose par l'analyste.

D'où la séparation que ce module impose : les HYPOTHÈSES entrent par `hypotheses` (le tableau signé,
chaque valeur sourcée ailleurs) ; la MÉCANIQUE est `code` ; le programme n'a PAS LE DROIT de réécrire
une hypothèse (une mécanique qui écrase le taux signé par le comité falsifierait le tableau qu'il a lu).
Changer une hypothèse recalcule sans aucun appel au modèle : c'est l'acceptation de la capacité 4 bis.

⚠️ ICI, C'EST UNE FRONTIÈRE DE SÉCURITÉ — À L'INVERSE DE `formule_grammaire.py`
------------------------------------------------------------------------------
La grammaire de #72 prévient qu'elle n'est pas un bac à sable : ses formules n'ont que des noms et
quatre opérateurs. Ici, la mécanique est ÉCRITE PAR L'AGENT après qu'il a lu du web — un texte hostile
lu en collecte peut donc finir dans le code. La défense tient en trois décisions :

  1. **Rien n'est jamais confié à Python** : ni `eval`, ni `exec`, ni `compile`. Le code est PARSÉ
     (`ast.parse`), puis cet interprète parcourt l'arbre et calcule lui-même. Le seul Python exécuté
     est celui des fonctions de la liste blanche (`FONCTIONS`) — les gabarits de `calculs.py` et
     quelques primitives numériques réécrites ici.
  2. **Liste BLANCHE de constructions**, jamais noire (même raison qu'en #72 : une liste noire laisse
     passer ce qu'elle n'a pas prévu). Pas d'attribut (donc aucun chemin vers `__class__`), pas de
     `def`/`lambda`/`import`/`while`/`try`/`with`, pas de chaîne formatée, et une fonction n'est pas
     une valeur (on ne peut que l'APPELER par son nom).
  3. **Tout est borné** : taille du code, nombre d'opérations (`budget`), taille des listes, nombres
     finis. Une boucle infinie n'existe pas (pas de `while`) ; une boucle très longue épuise le budget.

Contrat de sortie : `executer` rend un `ResultatCalcul`, ou lève `ErreurCalcul` — JAMAIS une autre
exception (prouvé par la batterie hostile de `checks/check_bac_a_calcul.py` §3). L'agent qui écrit la
mécanique lit le motif et corrige ; le comité ne voit jamais une trace Python.

Ce qui est admis : affectation (y compris `a, b = …` et `d["clé"] = …` sur un conteneur créé par le
programme), `+=`…, `for` sur une liste finie, `if`/`elif`/`else`, expressions arithmétiques
(`+ - * / // % **`), comparaisons, `and`/`or`/`not`, `x if c else y`, listes, tuples, dictionnaires,
indices et tranches, compréhensions, et les appels à `FONCTIONS`. Les sorties sont les variables
affectées dont le nom ne commence pas par `_`.

Module PUR : aucune IO, aucun réseau. Cible : Python 3.12 (conteneur backend).
"""
from __future__ import annotations

import ast
import copy
import keyword
import math
from dataclasses import dataclass
from typing import Any

from app.valorisation.calculs import CATALOGUE, ErreurCalcul

__all__ = ["BUDGET_PAR_DEFAUT", "ErreurCalcul", "FONCTIONS", "ResultatCalcul", "executer"]

BUDGET_PAR_DEFAUT = 200_000
LIMITE_CODE = 20_000        # caractères — une mécanique d'entreprise tient en quelques dizaines de lignes
LIMITE_ELEMENTS = 10_000    # éléments d'une liste / d'un dictionnaire / d'un `range`
_ENTIER_EXACT = 2 ** 53     # au-delà, un entier passe en flottant : pas d'entier géant en mémoire


@dataclass(frozen=True)
class ResultatCalcul:
    sorties: dict[str, Any]
    operations: int


# ── Primitives numériques exposées (réécrites : aucune fonction native n'est exposée telle quelle) ──

def _num(v: object, quoi: str = "valeur") -> int | float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ErreurCalcul(f"{quoi} non numérique ({type(v).__name__})")
    return v


def _borne(r: object) -> object:
    if isinstance(r, int) and not isinstance(r, bool) and abs(r) > _ENTIER_EXACT:
        r = float(r)
    if isinstance(r, float) and not math.isfinite(r):
        raise ErreurCalcul("résultat non fini (débordement ou indétermination)")
    return r


def _nombres(args: tuple) -> list:
    seq = args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args
    if not seq:
        raise ErreurCalcul("aucun nombre fourni")
    return [_num(x) for x in seq]


def _sum(seq: object) -> int | float:
    if not isinstance(seq, (list, tuple)):
        raise ErreurCalcul(f"sum attend une liste de nombres (reçu : {type(seq).__name__})")
    return sum(_num(x) for x in seq)


def _range(*args: object) -> list[int]:
    bornes = []
    for a in args:
        n = _num(a, "borne de range")
        if n != int(n):
            raise ErreurCalcul("range attend des entiers")
        bornes.append(int(n))
    if not 1 <= len(bornes) <= 2:
        raise ErreurCalcul("range attend une ou deux bornes (pas de pas)")
    r = range(*bornes)
    if len(r) > LIMITE_ELEMENTS:
        raise ErreurCalcul(f"range de {len(r)} éléments (limite {LIMITE_ELEMENTS})")
    return list(r)


def _round(x: object, chiffres: object = 0) -> float:
    n = _num(chiffres, "nombre de décimales")
    if n != int(n) or not 0 <= n <= 12:
        raise ErreurCalcul("round attend un nombre de décimales entier entre 0 et 12")
    return round(float(_num(x)), int(n))


def _len(x: object) -> int:
    if not isinstance(x, (list, tuple, dict, str)):
        raise ErreurCalcul(f"len sur une valeur sans longueur ({type(x).__name__})")
    return len(x)


def _sqrt(x: object) -> float:
    v = _num(x)
    if v < 0:
        raise ErreurCalcul("racine d'un nombre négatif")
    return math.sqrt(v)


def _log(x: object) -> float:
    v = _num(x)
    if v <= 0:
        raise ErreurCalcul("logarithme d'un nombre ≤ 0")
    return math.log(v)


FONCTIONS: dict[str, Any] = {
    "abs": lambda x: abs(_num(x)),
    "min": lambda *a: min(_nombres(a)),
    "max": lambda *a: max(_nombres(a)),
    "sum": _sum,
    "round": _round,
    "len": _len,
    "range": _range,
    "sqrt": _sqrt,
    "log": _log,
    "exp": lambda x: math.exp(_num(x)),
    **CATALOGUE,
}


# ── L'interprète ─────────────────────────────────────────────────────────────────────────────────

# Coût propre (en opérations du budget) des gabarits itératifs : la bissection de la croissance
# implicite refait 200 DCF — elle ne peut pas coûter une opération.
_COUT_APPEL = {"croissance_implicite": 5_000}

_OPERATEURS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: math.pow(a, b),   # toujours flottant : jamais d'entier géant (10**10**10)
}

_COMPARAISONS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


class _Gele(dict):
    """Un dictionnaire d'hypothèse SIGNÉE : lisible, jamais modifiable — même par un alias
    (`x = marges; x["a"] = 0.9` réécrirait le tableau que le comité a lu). Les listes signées,
    elles, deviennent des tuples."""

    def _interdit(self, *_a: object, **_k: object) -> None:
        raise ErreurCalcul("une hypothèse du tableau signé ne se modifie pas")

    __setitem__ = __delitem__ = update = setdefault = pop = popitem = clear = _interdit  # type: ignore[assignment]

    def __deepcopy__(self, memo: dict) -> dict:
        return {k: copy.deepcopy(v, memo) for k, v in self.items()}


def _geler(v: object) -> object:
    if isinstance(v, (list, tuple)):
        return tuple(_geler(x) for x in v)
    if isinstance(v, dict):
        return _Gele({k: _geler(x) for k, x in v.items()})
    return v


def _scalaire(v: object) -> bool:
    return isinstance(v, (bool, int, float, str))


def _compter(v: object, reste: int) -> int:
    """Nombre de valeurs d'une structure, SANS mémo : une structure qui se partage elle-même
    (`x = [x, x]` trente fois) est petite en mémoire mais exponentielle à sérialiser."""
    reste -= 1
    if reste < 0:
        raise ErreurCalcul(f"sorties de plus de {LIMITE_ELEMENTS * 10} valeurs")
    if isinstance(v, (list, tuple)):
        for x in v:
            reste = _compter(x, reste)
    elif isinstance(v, dict):
        for x in v.values():
            reste = _compter(x, reste)
    return reste


def _valider_valeur(v: object, chemin: str) -> object:
    """Une hypothèse n'est admise que faite de nombres finis, booléens, textes, listes et
    dictionnaires à clés texte — rien qui porte un comportement."""
    if isinstance(v, bool) or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return _borne(v)
    if isinstance(v, (list, tuple)):
        if len(v) > LIMITE_ELEMENTS:
            raise ErreurCalcul(f"hypothèse `{chemin}` : plus de {LIMITE_ELEMENTS} éléments")
        return [_valider_valeur(x, f"{chemin}[{i}]") for i, x in enumerate(v)]
    if isinstance(v, dict):
        if len(v) > LIMITE_ELEMENTS:
            raise ErreurCalcul(f"hypothèse `{chemin}` : plus de {LIMITE_ELEMENTS} éléments")
        if not all(isinstance(k, str) for k in v):
            raise ErreurCalcul(f"hypothèse `{chemin}` : clés non textuelles")
        return {k: _valider_valeur(x, f"{chemin}.{k}") for k, x in v.items()}
    raise ErreurCalcul(f"hypothèse `{chemin}` : type non admis ({type(v).__name__})")


class _Interprete:
    def __init__(self, hypotheses: dict[str, Any], budget: int) -> None:
        self.hypotheses = hypotheses
        self.variables: dict[str, Any] = {}
        self.portees: list[dict[str, Any]] = []   # variables locales des compréhensions
        self.budget = budget
        self.operations = 0
        self.ligne: int | None = None

    # ── outillage ──
    def _tic(self, node: ast.stmt | ast.expr) -> None:
        self.ligne = node.lineno
        self.operations += 1
        if self.operations > self.budget:
            raise ErreurCalcul(f"budget de calcul épuisé ({self.budget} opérations)", self.ligne)

    def _refus(self, node: ast.stmt | ast.expr) -> ErreurCalcul:
        return ErreurCalcul(f"construction non admise : {type(node).__name__}", node.lineno)

    def _lire(self, nom: str) -> Any:
        for portee in reversed(self.portees):
            if nom in portee:
                return portee[nom]
        if nom in self.variables:
            return self.variables[nom]
        if nom in self.hypotheses:
            return self.hypotheses[nom]
        if nom in FONCTIONS:
            raise ErreurCalcul(f"`{nom}` est une fonction : elle s'appelle, elle ne se manipule pas", self.ligne)
        raise ErreurCalcul(f"nom inconnu : `{nom}` (ni hypothèse, ni variable déjà calculée)", self.ligne)

    def _nom_affectable(self, nom: str) -> str:
        if nom in self.hypotheses:
            raise ErreurCalcul(
                f"`{nom}` est une hypothèse du tableau signé : la mécanique ne la réécrit pas", self.ligne
            )
        if nom in FONCTIONS:
            raise ErreurCalcul(f"`{nom}` est un gabarit du fonds : il ne se réaffecte pas", self.ligne)
        return nom

    def _lier(self, cible: ast.AST, valeur: Any, portee: dict[str, Any]) -> None:
        if isinstance(cible, ast.Name):
            portee[self._nom_affectable(cible.id)] = valeur
            return
        if isinstance(cible, ast.Tuple) and all(isinstance(e, ast.Name) for e in cible.elts):
            if not isinstance(valeur, (list, tuple)) or len(valeur) != len(cible.elts):
                raise ErreurCalcul("décomposition impossible : nombre de valeurs différent", self.ligne)
            for e, v in zip(cible.elts, valeur):
                portee[self._nom_affectable(e.id)] = v
            return
        raise self._refus(cible)

    # ── instructions ──
    def bloc(self, instructions: list[ast.stmt]) -> None:
        for i in instructions:
            self.instruction(i)

    def instruction(self, node: ast.stmt) -> None:
        self._tic(node)
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise ErreurCalcul("une seule cible par affectation", node.lineno)
            valeur = self.expr(node.value)
            cible = node.targets[0]
            if isinstance(cible, ast.Subscript):
                self._affecter_indice(cible, valeur)
            else:
                self._lier(cible, valeur, self.variables)
        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name) or type(node.op) not in _OPERATEURS:
                raise self._refus(node)
            nom = self._nom_affectable(node.target.id)
            self.variables[nom] = self._arith(node.op, self._lire(nom), self.expr(node.value))
        elif isinstance(node, ast.For):
            if node.orelse:
                raise self._refus(node)
            iterable = self._iterable(self.expr(node.iter))
            for element in iterable:
                self._tic(node)
                self._lier(node.target, element, self.variables)
                self.bloc(node.body)
        elif isinstance(node, ast.If):
            self.bloc(node.body if self._booleen(self.expr(node.test)) else node.orelse)
        elif isinstance(node, ast.Pass):
            pass
        else:
            raise self._refus(node)

    def _affecter_indice(self, cible: ast.Subscript, valeur: Any) -> None:
        if not isinstance(cible.value, ast.Name) or isinstance(cible.slice, ast.Slice):
            raise self._refus(cible)
        nom = cible.value.id
        self._nom_affectable(nom)
        if nom not in self.variables:
            raise ErreurCalcul(f"`{nom}` n'est pas un conteneur créé par la mécanique", self.ligne)
        conteneur, cle = self.variables[nom], self.expr(cible.slice)
        if isinstance(conteneur, dict):
            if not isinstance(cle, str):
                raise ErreurCalcul("clé de dictionnaire non textuelle", self.ligne)
            if cle not in conteneur and len(conteneur) >= LIMITE_ELEMENTS:
                raise ErreurCalcul(f"dictionnaire de plus de {LIMITE_ELEMENTS} éléments", self.ligne)
            conteneur[cle] = valeur
        elif isinstance(conteneur, list):
            conteneur[self._indice(cle)] = valeur
        else:
            raise ErreurCalcul(f"`{nom}` n'accepte pas d'affectation par indice", self.ligne)

    # ── expressions ──
    def expr(self, node: ast.expr) -> Any:
        self._tic(node)
        if isinstance(node, ast.Constant):
            if node.value is None or not isinstance(node.value, (bool, int, float, str)):
                raise self._refus(node)
            return _borne(node.value)
        if isinstance(node, ast.Name):
            return self._lire(node.id)
        if isinstance(node, ast.BinOp):
            if type(node.op) not in _OPERATEURS:
                raise self._refus(node)
            return self._arith(node.op, self.expr(node.left), self.expr(node.right))
        if isinstance(node, ast.UnaryOp):
            v = self.expr(node.operand)
            if isinstance(node.op, ast.Not):
                return not self._booleen(v)
            if isinstance(node.op, ast.USub):
                return _borne(-_num(v))
            if isinstance(node.op, ast.UAdd):
                return _num(v)
            raise self._refus(node)
        if isinstance(node, ast.BoolOp):
            est_et = isinstance(node.op, ast.And)
            for v in node.values:
                if self._booleen(self.expr(v)) != est_et:
                    return not est_et
            return est_et
        if isinstance(node, ast.Compare):
            gauche = self.expr(node.left)
            for op, droite_n in zip(node.ops, node.comparators):
                if type(op) not in _COMPARAISONS:
                    raise self._refus(node)
                droite = self.expr(droite_n)
                appartenance = isinstance(op, (ast.In, ast.NotIn))
                if not _scalaire(gauche) or not (appartenance or _scalaire(droite)):
                    raise ErreurCalcul("on ne compare que des nombres ou des textes", self.ligne)
                if not _COMPARAISONS[type(op)](gauche, droite):
                    return False
                gauche = droite
            return True
        if isinstance(node, ast.IfExp):
            return self.expr(node.body) if self._booleen(self.expr(node.test)) else self.expr(node.orelse)
        if isinstance(node, (ast.List, ast.Tuple)):
            if any(isinstance(e, ast.Starred) for e in node.elts):
                raise self._refus(node)
            return self._taille([self.expr(e) for e in node.elts])
        if isinstance(node, ast.Dict):
            if any(k is None for k in node.keys):
                raise self._refus(node)
            d = {}
            for k, v in zip(node.keys, node.values):
                cle = self.expr(k)
                if not isinstance(cle, str):
                    raise ErreurCalcul("clé de dictionnaire non textuelle", self.ligne)
                d[cle] = self.expr(v)
            return self._taille(d)
        if isinstance(node, ast.Subscript):
            return self._indicer(self.expr(node.value), node.slice)
        if isinstance(node, ast.Call):
            return self._appel(node)
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            return self._comprehension(node, lambda: self.expr(node.elt))
        raise self._refus(node)

    def _arith(self, op: ast.operator, a: Any, b: Any) -> Any:
        a, b = _num(a, "opérande"), _num(b, "opérande")
        return _borne(_OPERATEURS[type(op)](a, b))

    def _booleen(self, v: Any) -> bool:
        if not isinstance(v, bool):
            raise ErreurCalcul(f"une condition doit être vraie ou fausse (reçu : {type(v).__name__})", self.ligne)
        return v

    def _iterable(self, v: Any) -> list:
        if isinstance(v, (list, tuple, str)):
            return list(v)
        if isinstance(v, dict):
            return list(v.keys())
        raise ErreurCalcul(f"on ne parcourt pas une valeur de type {type(v).__name__}", self.ligne)

    def _taille(self, c: Any) -> Any:
        if len(c) > LIMITE_ELEMENTS:
            raise ErreurCalcul(f"conteneur de plus de {LIMITE_ELEMENTS} éléments", self.ligne)
        return c

    def _indice(self, i: Any) -> int:
        n = _num(i, "indice")
        if n != int(n):
            raise ErreurCalcul("indice non entier", self.ligne)
        return int(n)

    def _indicer(self, conteneur: Any, tranche: ast.expr) -> Any:
        if isinstance(tranche, ast.Slice):
            if tranche.step is not None or not isinstance(conteneur, (list, tuple)):
                raise self._refus(tranche)
            bas = None if tranche.lower is None else self._indice(self.expr(tranche.lower))
            haut = None if tranche.upper is None else self._indice(self.expr(tranche.upper))
            return list(conteneur[bas:haut])
        cle = self.expr(tranche)
        if isinstance(conteneur, dict):
            if cle not in conteneur:
                raise ErreurCalcul(f"clé absente : {cle!r}", self.ligne)
            return conteneur[cle]
        if isinstance(conteneur, (list, tuple)):
            return conteneur[self._indice(cle)]
        raise ErreurCalcul(f"on n'indice pas une valeur de type {type(conteneur).__name__}", self.ligne)

    def _appel(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name) or node.func.id not in FONCTIONS:
            nom = node.func.id if isinstance(node.func, ast.Name) else type(node.func).__name__
            raise ErreurCalcul(f"fonction non admise : `{nom}` (seuls les gabarits du fonds s'appellent)", node.lineno)
        if any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords):
            raise self._refus(node)
        args = [self.expr(a) for a in node.args]
        kwargs = {k.arg: self.expr(k.value) for k in node.keywords}
        # Un appel coûte ce qu'il parcourt : la taille de ses arguments, plus le coût propre d'un
        # gabarit itératif — sinon une boucle d'appels contournerait le budget.
        cout = _COUT_APPEL.get(node.func.id, 1)
        for a in (*args, *kwargs.values()):
            if isinstance(a, (list, tuple, dict)):
                cout += len(a)
        self.operations += cout
        self._tic(node)
        # Aucune copie des arguments : une hypothèse signée arrive GELÉE (tuple, `_Gele`), un gabarit
        # ne peut donc pas la modifier même s'il le tentait.
        try:
            resultat = FONCTIONS[node.func.id](*args, **kwargs)
        except ErreurCalcul as e:
            raise ErreurCalcul(f"{node.func.id} : {e.motif}", node.lineno) from None
        except TypeError as e:
            raise ErreurCalcul(f"{node.func.id} : appel mal formé ({e})", node.lineno) from None
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            raise ErreurCalcul(f"{node.func.id} : calcul impossible ({e})", node.lineno) from None
        return _valider_valeur(resultat, node.func.id)

    def _comprehension(self, node: ast.ListComp | ast.GeneratorExp, element) -> list:
        if len(node.generators) != 1 or node.generators[0].is_async:
            raise self._refus(node)
        gen = node.generators[0]
        sortie: list = []
        self.portees.append({})
        try:
            for v in self._iterable(self.expr(gen.iter)):
                self._tic(node)
                self._lier(gen.target, v, self.portees[-1])
                if all(self._booleen(self.expr(c)) for c in gen.ifs):
                    sortie.append(element())
                    self._taille(sortie)
        finally:
            self.portees.pop()
        return sortie


def executer(code: str, hypotheses: dict[str, Any], *, budget: int = BUDGET_PAR_DEFAUT) -> ResultatCalcul:
    """Exécute la mécanique `code` sur le tableau `hypotheses`. Rend les variables calculées
    (`sorties`, hors noms en `_`) ou lève `ErreurCalcul` — jamais une autre exception."""
    if not isinstance(code, str) or len(code) > LIMITE_CODE:
        raise ErreurCalcul(f"mécanique absente ou de plus de {LIMITE_CODE} caractères")
    if not isinstance(hypotheses, dict):
        raise ErreurCalcul("le tableau d'hypothèses doit être un dictionnaire")
    propres: dict[str, Any] = {}
    for nom, v in hypotheses.items():
        if not isinstance(nom, str) or not nom.isidentifier() or keyword.iskeyword(nom) or nom in FONCTIONS:
            raise ErreurCalcul(f"nom d'hypothèse non admis : {nom!r}")
        propres[nom] = _geler(_valider_valeur(copy.deepcopy(v), nom))

    interprete = _Interprete(propres, budget)
    try:
        arbre = ast.parse(code, mode="exec")
        interprete.bloc(arbre.body)
        sorties = {k: copy.deepcopy(v) for k, v in interprete.variables.items() if not k.startswith("_")}
        _compter(sorties, LIMITE_ELEMENTS * 10)
    except ErreurCalcul as e:
        if e.ligne is None:   # refus levé hors de l'interprète (hypothèse gelée) : on le situe
            raise ErreurCalcul(e.motif, interprete.ligne) from None
        raise
    except SyntaxError as e:
        raise ErreurCalcul(f"mécanique illisible : {e.msg}", e.lineno) from None
    except (RecursionError, MemoryError):
        raise ErreurCalcul("mécanique trop imbriquée", interprete.ligne) from None
    except ZeroDivisionError:
        raise ErreurCalcul("division par zéro", interprete.ligne) from None
    except OverflowError:
        raise ErreurCalcul("résultat non fini (débordement)", interprete.ligne) from None
    except ValueError as e:
        raise ErreurCalcul(f"calcul impossible ({e})", interprete.ligne) from None
    except (TypeError, IndexError, KeyError) as e:
        raise ErreurCalcul(f"opération invalide ({type(e).__name__} : {e})", interprete.ligne) from None

    return ResultatCalcul(sorties=sorties, operations=interprete.operations)
