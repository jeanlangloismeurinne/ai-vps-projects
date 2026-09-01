"""Détection statique des noms non résolus dans les f-strings — pur, sans réseau ni DB ni LLM.

Ce check existe à cause d'un bug réel constaté en production le 2026-09-01 (Convention #39).
Dans `backend/app/api/analysis_v2.py`, une requête SQL était construite par une f-string :

    sql = f\"\"\"
        SELECT ...
            -- hypotheses_par_statut : {statut: count}   <-- LE BUG
        {where}
    \"\"\"

Le commentaire SQL contenait des accolades. Python les a interprétées comme un champ de
remplacement de f-string (`statut` = nom de variable, `count` = format spec) → `NameError:
name 'statut' is not defined` à chaque appel de la route. Le module s'importait très bien
(une f-string n'est évaluée qu'à l'exécution de sa ligne) ; la suite de checks hors-ligne
passait à 100 % ; la route renvoyait 500 Internal Server Error en production.

Ce qu'on éprouve ici (analyse statique par `ast`, aucune exécution du code applicatif) :

  • Parcourir tous les .py sous backend/app/.
  • Pour chaque champ de remplacement d'une f-string, collecter les `ast.Name` libres.
  • Vérifier que chaque nom est lié dans sa portée (arguments de fonction, variables assignées,
    cibles de `for`/`with`/`except` [y compris les variantes async], compréhensions,
    `global`/`nonlocal`, imports, builtins).
  • Tout nom non résoluble = FAIL, avec chemin, ligne et nom incriminé.

Le check doit être vert sur le code actuel :
  - `{where}` dans analysis_v2.py est une variable locale légitime → doit passer.
  - `f"Agent V2 : {e}"` : `e` est lié par `except ... as e` → doit passer.
  - `[f"{x}" for x in ...]` : la variable de compréhension est liée → doit passer.
"""
import ast
import builtins
import sys
from pathlib import Path

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# ── Constantes ────────────────────────────────────────────────────────────────

BUILTINS = set(dir(builtins))


# ── Helpers d'extraction de noms liés ────────────────────────────────────────

def _targets(node):
    """Extrait les noms liés depuis un nœud cible (Name, Tuple, List — récursif)."""
    names = set()
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            names |= _targets(elt)
    return names


def _collect_stmts(stmts):
    """
    Collecte tous les noms liés dans une liste de statements, en descendant dans les blocs
    de contrôle (if/for/while/with/try/except — y compris les variantes async) mais PAS
    dans les sous-fonctions ni sous-classes (qui ouvrent leur propre portée Python).

    Traite : Assign, AnnAssign, AugAssign, NamedExpr, For, AsyncFor, With, AsyncWith,
    ExceptHandler, Try, If, While, Global, Nonlocal, Import, ImportFrom,
    FunctionDef (nom seulement), ClassDef (nom seulement).
    """
    names = set()

    def _walk(stmts_):
        for node in stmts_:
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    names.update(_targets(tgt))
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.NamedExpr):
                        names.update(_targets(sub.target))
            elif isinstance(node, ast.AnnAssign):
                if node.target:
                    names.update(_targets(node.target))
            elif isinstance(node, ast.AugAssign):
                names.update(_targets(node.target))
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                names.update(_targets(node.target))
                _walk(node.body)
                _walk(node.orelse)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars:
                        names.update(_targets(item.optional_vars))
                _walk(node.body)
            elif isinstance(node, ast.ExceptHandler):
                if node.name:
                    names.add(node.name)
                _walk(node.body)
            elif isinstance(node, ast.Try):
                _walk(node.body)
                for handler in node.handlers:
                    _walk([handler])
                _walk(node.orelse)
                if hasattr(node, "finalbody"):
                    _walk(node.finalbody)
            elif isinstance(node, ast.If):
                for sub in ast.walk(node.test):
                    if isinstance(sub, ast.NamedExpr):
                        names.update(_targets(sub.target))
                _walk(node.body)
                _walk(node.orelse)
            elif isinstance(node, ast.While):
                for sub in ast.walk(node.test):
                    if isinstance(sub, ast.NamedExpr):
                        names.update(_targets(sub.target))
                _walk(node.body)
                _walk(node.orelse)
            elif isinstance(node, ast.Global):
                names.update(node.names)
            elif isinstance(node, ast.Nonlocal):
                names.update(node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    bound = alias.asname if alias.asname else alias.name.split(".")[0]
                    names.add(bound)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    bound = alias.asname if alias.asname else alias.name
                    if bound != "*":
                        names.add(bound)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                names.add(node.name)
            elif isinstance(node, ast.Expr):
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.NamedExpr):
                        names.update(_targets(sub.target))

    _walk(stmts)
    return names


def _func_args(func_node):
    """Extrait tous les noms d'arguments d'une définition de fonction/lambda."""
    args = func_node.args
    names = set()
    for a in args.posonlyargs + args.args + args.kwonlyargs:
        names.add(a.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def _comp_vars(comp_node):
    """Noms liés par les générateurs d'une compréhension."""
    names = set()
    for gen in comp_node.generators:
        names.update(_targets(gen.target))
    return names


# ── Vérification d'une f-string dans un contexte de portée ───────────────────

def _visit_joinedstr(js_node, visible, errors):
    """
    Vérifie les champs de remplacement d'une f-string.
    `visible` : ensemble des noms connus à ce point (portée courante + builtins).
    """
    for child in js_node.values:
        if isinstance(child, ast.FormattedValue):
            _scan_expr_for_fstrings(child.value, visible, errors)


def _scan_expr_for_fstrings(expr, visible, errors):
    """
    Parcourt `expr` à la recherche de JoinedStr, en gérant les portées créées
    par les compréhensions et les lambdas. Toute JoinedStr rencontrée est vérifiée
    avec la portée `visible` étendue des variables locales à la compréhension/lambda.

    Appel récursif : ne descend jamais dans une FunctionDef/ClassDef (portée Python séparée).
    """
    if isinstance(expr, ast.JoinedStr):
        # On vérifie les champs de cette f-string avec la portée courante.
        _visit_joinedstr(expr, visible, errors)

    elif isinstance(expr, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        # Les cibles des générateurs sont liées dans la compréhension.
        comp_vis = visible | _comp_vars(expr)
        # iter du 1er générateur → portée extérieure ; conditionals et elt → comp_vis.
        for i, gen in enumerate(expr.generators):
            # L'iter du générateur n+1 voit les cibles des générateurs précédents.
            iter_vis = visible | _comp_vars_up_to(expr.generators, i)
            _scan_expr_for_fstrings(gen.iter, iter_vis, errors)
            for cond in gen.ifs:
                _scan_expr_for_fstrings(cond, comp_vis, errors)
        _scan_expr_for_fstrings(expr.elt, comp_vis, errors)

    elif isinstance(expr, ast.DictComp):
        comp_vis = visible | _comp_vars(expr)
        for i, gen in enumerate(expr.generators):
            iter_vis = visible | _comp_vars_up_to(expr.generators, i)
            _scan_expr_for_fstrings(gen.iter, iter_vis, errors)
            for cond in gen.ifs:
                _scan_expr_for_fstrings(cond, comp_vis, errors)
        _scan_expr_for_fstrings(expr.key, comp_vis, errors)
        _scan_expr_for_fstrings(expr.value, comp_vis, errors)

    elif isinstance(expr, ast.Lambda):
        # Lambda crée une portée propre.
        lambda_vis = visible | _func_args(expr)
        _scan_expr_for_fstrings(expr.body, lambda_vis, errors)

    else:
        # Descend dans les sous-expressions.
        for child in ast.iter_child_nodes(expr):
            if isinstance(child, ast.expr):
                _scan_expr_for_fstrings(child, visible, errors)
            elif isinstance(child, ast.keyword):
                _scan_expr_for_fstrings(child.value, visible, errors)


def _comp_vars_up_to(generators, n):
    """Noms liés par les n premiers générateurs (pour iter du (n+1)ème)."""
    names = set()
    for gen in generators[:n]:
        names.update(_targets(gen.target))
    return names


# ── Analyse récursive par portée (statements) ─────────────────────────────────

def _analyse_scope(stmts, outer_names, errors):
    """
    Analyse les f-strings dans `stmts` en tenant compte de la portée.

    `outer_names` : noms visibles depuis les portées englobantes (module + fonctions parentes).
    Pour chaque fonction/classe imbriquée, on relance récursivement avec la portée étendue.
    """
    local_names = _collect_stmts(stmts)
    visible = outer_names | local_names | BUILTINS

    def _visit_stmts(nodes):
        for node in nodes:
            _visit_node(node)

    def _visit_node(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_vis = visible | _func_args(node)
            _analyse_scope(node.body, fn_vis, errors)
            for deco in node.decorator_list:
                _scan_expr_for_fstrings(deco, visible, errors)

        elif isinstance(node, ast.ClassDef):
            _analyse_scope(node.body, visible, errors)
            for deco in node.decorator_list:
                _scan_expr_for_fstrings(deco, visible, errors)

        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _scan_expr_for_fstrings(node.iter, visible, errors)
            _visit_stmts(node.body)
            _visit_stmts(node.orelse)

        elif isinstance(node, ast.While):
            _scan_expr_for_fstrings(node.test, visible, errors)
            _visit_stmts(node.body)
            _visit_stmts(node.orelse)

        elif isinstance(node, ast.If):
            _scan_expr_for_fstrings(node.test, visible, errors)
            _visit_stmts(node.body)
            _visit_stmts(node.orelse)

        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                _scan_expr_for_fstrings(item.context_expr, visible, errors)
            _visit_stmts(node.body)

        elif isinstance(node, ast.Try):
            _visit_stmts(node.body)
            for handler in node.handlers:
                _visit_stmts(handler.body)
            _visit_stmts(node.orelse)
            if hasattr(node, "finalbody"):
                _visit_stmts(node.finalbody)

        elif isinstance(node, ast.Assign):
            _scan_expr_for_fstrings(node.value, visible, errors)

        elif isinstance(node, ast.AnnAssign):
            if node.value:
                _scan_expr_for_fstrings(node.value, visible, errors)

        elif isinstance(node, ast.AugAssign):
            _scan_expr_for_fstrings(node.value, visible, errors)

        elif isinstance(node, ast.Return):
            if node.value:
                _scan_expr_for_fstrings(node.value, visible, errors)

        elif isinstance(node, ast.Expr):
            _scan_expr_for_fstrings(node.value, visible, errors)

        elif isinstance(node, ast.Raise):
            if node.exc:
                _scan_expr_for_fstrings(node.exc, visible, errors)

        elif isinstance(node, ast.Assert):
            _scan_expr_for_fstrings(node.test, visible, errors)
            if node.msg:
                _scan_expr_for_fstrings(node.msg, visible, errors)

        elif isinstance(node, ast.Delete):
            for tgt in node.targets:
                _scan_expr_for_fstrings(tgt, visible, errors)

    _visit_stmts(stmts)


# ── Vérification des FormattedValue dans une f-string ────────────────────────

def _visit_joinedstr_fields(js_node, visible, errors):
    """
    Pour chaque champ `{expr}` d'une f-string, vérifie que les noms libres de `expr`
    sont dans `visible`. Un nom libre est un `ast.Name` qui n'est pas lié localement
    par une compréhension/lambda imbriquée dans l'expression elle-même.
    """
    for child in js_node.values:
        if isinstance(child, ast.FormattedValue):
            # Collecte les noms libres de l'expression du champ,
            # en tenant compte des compréhensions imbriquées.
            free = _free_names_in_expr(child.value, visible)
            unseen = free - BUILTINS
            for name in sorted(unseen):
                try:
                    snippet = ast.unparse(child.value)
                except Exception:
                    snippet = "???"
                errors.append((js_node.lineno, name, snippet))


def _free_names_in_expr(expr, outer_visible):
    """
    Retourne les noms libres dans `expr` : noms utilisés (ast.Name Load) qui ne sont
    pas liés par l'expression elle-même (via compréhension, lambda ou walrus) ET qui
    ne sont pas dans `outer_visible`.

    Gère correctement : compréhensions imbriquées, lambdas, walrus (:=), f-strings
    imbriquées, et toutes les expressions Python courantes.
    """
    free = set()

    def _walk(node, bound):
        """Parcours récursif avec l'ensemble `bound` des noms liés localement."""
        if isinstance(node, ast.Name):
            if node.id not in bound and node.id not in outer_visible:
                free.add(node.id)

        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            comp_bound = bound | _comp_vars(node)
            for i, gen in enumerate(node.generators):
                iter_bound = bound | _comp_vars_up_to(node.generators, i)
                _walk(gen.iter, iter_bound)
                for cond in gen.ifs:
                    _walk(cond, comp_bound)
            _walk(node.elt, comp_bound)

        elif isinstance(node, ast.DictComp):
            comp_bound = bound | _comp_vars(node)
            for i, gen in enumerate(node.generators):
                iter_bound = bound | _comp_vars_up_to(node.generators, i)
                _walk(gen.iter, iter_bound)
                for cond in gen.ifs:
                    _walk(cond, comp_bound)
            _walk(node.key, comp_bound)
            _walk(node.value, comp_bound)

        elif isinstance(node, ast.Lambda):
            lambda_bound = bound | _func_args(node)
            _walk(node.body, lambda_bound)

        elif isinstance(node, ast.NamedExpr):
            _walk(node.value, bound)
            # Le walrus lie dans la portée englobante — ici on l'ajoute à bound pour
            # les usages suivants dans la même expression.
            bound = bound | {node.target.id}

        elif isinstance(node, ast.JoinedStr):
            # F-string imbriquée : on visite chaque FormattedValue avec la portée courante.
            for child in node.values:
                if isinstance(child, ast.FormattedValue):
                    _walk(child.value, bound)

        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    _walk(child, bound)
                elif isinstance(child, ast.keyword):
                    _walk(child.value, bound)

    _walk(expr, set())
    return free


# ── Corrige _visit_joinedstr pour utiliser _visit_joinedstr_fields ────────────

# Redéfinir _visit_joinedstr pour utiliser la bonne fonction de vérification.
def _visit_joinedstr(js_node, visible, errors):
    _visit_joinedstr_fields(js_node, visible, errors)


# ── Analyse d'un fichier ──────────────────────────────────────────────────────

def _check_fstrings_in_file(path: Path) -> list:
    """
    Retourne une liste de (lineno, name, snippet) pour chaque nom non résolu
    dans une f-string du fichier. Retourne [] si le fichier est non-parseable.
    """
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    module_names = _collect_stmts(tree.body)
    errors = []
    _analyse_scope(tree.body, module_names, errors)
    return errors


# ── Point d'entrée ─────────────────────────────────────────────────────────────

APP_ROOT = Path("app")

print("§1 — Détection des noms non résolus dans les f-strings (backend/app/)")
print(f"     Répertoire analysé : {APP_ROOT.resolve()}\n")

py_files = sorted(APP_ROOT.rglob("*.py"))
total_errs = 0
total_files = 0

for py_file in py_files:
    errs = _check_fstrings_in_file(py_file)
    for lineno, name, snippet in errs:
        rel = py_file.relative_to(Path("."))
        print(f"  FAIL [{rel}:{lineno}] nom '{name}' non résolu dans f-string  {{{snippet}}}")
    total_errs += len(errs)
    total_files += 1

check(
    f"aucun nom non résolu dans les f-strings des {total_files} fichiers de backend/app/",
    total_errs == 0,
    f"— {total_errs} violation(s) trouvée(s)",
)


# ── §2 — Cas unitaires : vérifier les cas légitimes passent ──────────────────
print("\n§2 — Cas unitaires (légitimes)")

import tempfile


def _errs_from_src(src: str) -> list:
    """Lance le check sur un fragment de source temporaire."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(src)
        tmp = Path(f.name)
    try:
        return _check_fstrings_in_file(tmp)
    finally:
        tmp.unlink(missing_ok=True)


# Cas légitimes — doivent retourner 0 erreur
legit_cases = {
    "variable locale": "def f():\n    x = 1\n    return f'{x}'\n",
    "argument positionnel": "def f(a):\n    return f'{a}'\n",
    "argument *args/**kwargs": "def f(*args, **kw):\n    return f'{args}{kw}'\n",
    "except ... as e": (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception as e:\n"
        "        return f'err: {e}'\n"
    ),
    "cible de for": "def f():\n    for item in []:\n        print(f'{item}')\n",
    "cible de async for": (
        "async def f():\n"
        "    async for item in aiter():\n"
        "        print(f'{item}')\n"
    ),
    "async with body + usage outside": (
        "async def f():\n"
        "    async with ctx() as db:\n"
        "        r = await db.fetchrow('q')\n"
        "    return f'{r}'\n"
    ),
    "listcomp au niveau module": "result = [f'{x}' for x in range(10)]\n",
    "dictcomp au niveau module": "d = {k: f'{v}' for k, v in {}.items()}\n",
    "genexpr in f-string": "s = f\"{', '.join(str(i) for i in [1,2,3])}\"\n",
    "listcomp in f-string arg (cas thesis_chat.py)": (
        "def f(hyps):\n"
        "    return '\\n'.join([f'{h.get(\"x\")}' for h in hyps])\n"
    ),
    "walrus operator": "def f():\n    if (n := 10) > 5:\n        return f'{n}'\n",
    "variable globale dans fonction": "x = 42\ndef f():\n    return f'{x}'\n",
    "builtin len": "def f():\n    return f'{len([])!r}'\n",
    "import au module": "import os\ndef f():\n    return f'{os.sep}'\n",
    "where SQL (cas du bug corrigé)": (
        "def f(ticker_id=None):\n"
        "    where = 'WHERE t.ticker_id = $1' if ticker_id else ''\n"
        "    sql = f'SELECT * FROM t {where}'\n"
        "    return sql\n"
    ),
    "assign dans async with puis usage hors bloc": (
        "async def f():\n"
        "    async with ctx() as db:\n"
        "        session_id = 42\n"
        "    return f'id={session_id}'\n"
    ),
}

for label, src in legit_cases.items():
    errs = _errs_from_src(src)
    check(f"légitme — {label} résolu sans erreur", len(errs) == 0,
          f"— erreurs inattendues : {errs}")


print("\n§3 — Cas unitaires (illégitimes : le check doit échouer)")

# Cas illégitimes — doivent retourner ≥ 1 erreur sur le nom attendu
bad_cases = {
    "commentaire SQL {statut: count}": (
        "def f():\n"
        "    where = ''\n"
        "    sql = f'SELECT -- {statut: count}\\n{where}'\n"
        "    return sql\n",
        "statut",
    ),
    "nom purement inventé": (
        "def f():\n    return f'{toto_inexistant}'\n",
        "toto_inexistant",
    ),
}

for label, (src, expected_name) in bad_cases.items():
    errs = _errs_from_src(src)
    found = any(name == expected_name for _, name, _ in errs)
    check(
        f"illégal — {label} → nom '{expected_name}' bien détecté",
        found,
        f"— erreurs trouvées : {errs}",
    )


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
