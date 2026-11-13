"""Garde des accès entre modules — la charte d'un module (`roadmap/V3/07-avant-comite.md`) tenue par
la STRUCTURE du code, pas par la discipline de celui qui l'écrit.

CE QU'IL TIENT (chaque invariant sur un assert NOMMÉ, préfixe stable) :
  [C0] prérequis : `app/modules/` et son registre existent, se chargent, et la sélection n'est pas
       vide (un contrôle qui ne lit rien ne doit jamais sortir vert).
  [C1] bijection registre ↔ disque : tout sous-dossier de `app/modules/` est déclaré, et
       réciproquement ; le registre est cohérent avec lui-même.
  [C2] un contrat par module : `contrat.py` existe et expose `VERSION_CONTRAT` (chaîne).
  [C3] un module n'importe d'un autre que son `contrat`, et seulement s'il le déclare (`lit`).
  [C4] un module n'importe pas l'ancien code, sauf les chemins listés dans ses `reprises`.
  [C5] l'ancien code (`app/` hors `app/modules/`) ne lit d'un module que son `contrat`.
  [C6] un module possède ses tables : aucun nom de table à son préfixe dans une chaîne littérale
       hors de son dossier (`app/` et `tools/`) ; préfixes sans collision.
  [C7] rien de propre à une juridiction ou à une société dans le cœur d'un module. La liste de
       jetons est un FILET, pas une preuve : elle attrape l'oubli grossier, pas le sens.

POURQUOI PUR FILESYSTEM/AST : bibliothèque standard + `_harness`, sans importer `app` (le registre
est chargé par son chemin de fichier). Il tourne à l'identique en conteneur et sur l'hôte.
Prouvé rouge par `negatif_charte_modules.sh` (au moins une mutation par invariant).

CE QU'IL NE VOIT PAS : `app/modules/ARCHITECTURE.md`, § « Limites ».
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402

# Chemins résolus depuis __file__ → conteneur (/app) comme hôte (<repo>/…/backend).
_HERE = Path(__file__).resolve()
BACKEND = _HERE.parent.parent
APP = BACKEND / "app"
MODULES_DIR = APP / "modules"
REGISTRE = MODULES_DIR / "registre.py"
TOOLS = BACKEND / "tools"

RACINE = "app.modules"
LIBRE = f"{RACINE}.registre"          # importable par tous
SOUS_DOSSIER_ADAPTATEURS = "adaptateurs"  # ce qui est propre à une SOURCE vit là, et seulement là

# [C7] Filet, volontairement court et explicite. Une frontière = « ni lettre ni chiffre » (le
# souligné n'en est pas une : `cik_emetteur` et `nvda_cas` sont attrapés). Insensible à la casse.
JETONS_JURIDICTION = ("10-K", "10-Q", "8-K", "DEF 14A", "EDGAR", "us-gaap", "cik")
SYMBOLES_SOCIETE = ("NVDA", "RVMD", "MSFT")


def _motif(jeton: str) -> re.Pattern[str]:
    corps = r"\s+".join(re.escape(m) for m in jeton.split())
    return re.compile(rf"(?<![A-Za-z0-9]){corps}(?![A-Za-z0-9])", re.IGNORECASE)


MOTIFS_JURIDICTION = [(j, _motif(j)) for j in JETONS_JURIDICTION]
MOTIFS_SOCIETE = [(s, _motif(s)) for s in SYMBOLES_SOCIETE]


def _rel(p: Path) -> str:
    return p.relative_to(BACKEND).as_posix()


def _fichiers_py(racine: Path) -> list[Path]:
    return sorted(p for p in racine.rglob("*.py") if "__pycache__" not in p.parts)


def _nom_pointe(fichier: Path) -> tuple[str, ...]:
    """`app/modules/x/a.py` → (app, modules, x, a) ; le paquet d'un `__init__.py` est son dossier."""
    parts = fichier.relative_to(BACKEND).with_suffix("").parts
    return parts[:-1] if parts[-1] == "__init__" else parts


def _imports(tree: ast.AST, fichier: Path) -> list[tuple[int, str, tuple[str, ...]]]:
    """Tous les imports d'un arbre : (ligne, énoncé lisible, chemins candidats).

    Un `from B import n` désigne soit le module `B`, soit le sous-module `B.n` — impossible à
    trancher sans exécuter : les DEUX candidats sont rendus, et chaque règle dit lequel elle retient.
    Un import relatif est résolu contre le paquet du fichier.
    """
    est_paquet = fichier.name == "__init__.py"
    paquet = _nom_pointe(fichier) if est_paquet else _nom_pointe(fichier)[:-1]
    trouves: list[tuple[int, str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                trouves.append((node.lineno, f"import {alias.name}", (alias.name,)))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = paquet[: len(paquet) - (node.level - 1)] if node.level > 1 else paquet
                base = ".".join(base_parts + tuple((node.module or "").split(".") if node.module else ()))
            else:
                base = node.module or ""
            for alias in node.names:
                cands = (base,) if alias.name == "*" else (base, f"{base}.{alias.name}")
                trouves.append((node.lineno, f"from {base} import {alias.name}", cands))
    return trouves


def _sous(chemin: str, racine: str) -> bool:
    return chemin == racine or chemin.startswith(racine + ".")


def _chaines_hors_docstrings(tree: ast.AST) -> list[tuple[int, str]]:
    """Les chaînes littérales d'un arbre (morceaux fixes de f-strings compris), sans les docstrings
    ni les chaînes posées seules sur une ligne — de la prose, pas un accès."""
    prose: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            prose.add(id(node.value))
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose
    ]


def _charger_registre():
    """Charge `registre.py` par son chemin, sans importer `app`."""
    spec = importlib.util.spec_from_file_location("_registre_des_modules", REGISTRE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # `dataclass` + annotations différées : le module doit être inscrit
    spec.loader.exec_module(mod)
    return mod


def _version_contrat(tree: ast.AST) -> bool:
    """Vrai si le module affecte, à son niveau, une chaîne non vide à `VERSION_CONTRAT`."""
    for node in getattr(tree, "body", []):
        cibles, valeur = [], None
        if isinstance(node, ast.Assign):
            cibles, valeur = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            cibles, valeur = [node.target], node.value
        if any(isinstance(c, ast.Name) and c.id == "VERSION_CONTRAT" for c in cibles):
            return isinstance(valeur, ast.Constant) and isinstance(valeur.value, str) \
                and bool(valeur.value.strip())
    return False


def main() -> int:
    b = Bilan()

    # ── [C0] Prérequis : un absent sort en ÉCHEC nommé, jamais en 0 ───────────────────────────
    if not b.check(MODULES_DIR.is_dir(), f"[C0] dossier app/modules/ présent ({MODULES_DIR})"):
        return b.summary() or 1
    if not b.check(REGISTRE.is_file(), f"[C0] registre présent ({REGISTRE})"):
        return b.summary() or 1
    try:
        registre = _charger_registre()
        modules = tuple(registre.MODULES)
        incoherences = list(registre.incoherences())
    except Exception as exc:  # noqa: BLE001 — tout défaut de chargement doit finir en FAIL nommé
        b.check(False, f"[C0] registre chargeable — {type(exc).__name__}: {exc}")
        return b.summary() or 1
    if not b.check(len(modules) >= 1, "[C0] le registre déclare au moins un module"):
        return b.summary() or 1
    par_nom = {m.nom: m for m in modules}

    # Lecture unique de chaque fichier ; un source illisible est un échec, pas un fichier ignoré.
    arbres: dict[Path, ast.AST] = {}
    textes: dict[Path, str] = {}

    illisibles: set[Path] = set()

    def lire(fichier: Path) -> ast.AST | None:
        if fichier in arbres:
            return arbres[fichier]
        if fichier in illisibles:
            return None
        try:
            textes[fichier] = fichier.read_text(encoding="utf-8")
            arbres[fichier] = ast.parse(textes[fichier])
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            illisibles.add(fichier)
            if TOOLS in fichier.parents and fichier in textes:
                # Un outil hors `app/` qui ne compile pas n'est pas l'affaire de cette garde ; il
                # n'en devient pas invisible : [C6] le lit en TEXTE BRUT (surdétecter, jamais sous-).
                print(f"  note : {_rel(fichier)} ne compile pas ({type(exc).__name__}) — lu en texte brut pour [C6]")
            else:
                b.check(False, f"[C0] source lisible : {_rel(fichier)} — {type(exc).__name__}")
            return None
        return arbres[fichier]

    # ── [C1] Bijection registre ↔ disque ─────────────────────────────────────────────────────
    sur_disque = {p.name for p in MODULES_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"}
    declares = set(par_nom)
    for d in incoherences:
        if "préfixes de tables" not in d:  # les collisions de préfixes sont jugées en [C6]
            b.check(False, f"[C1] registre incohérent : {d}")
    b.check(not [d for d in incoherences if "préfixes de tables" not in d],
            "[C1] le registre est cohérent avec lui-même")
    for nom in sorted(declares - sur_disque):
        b.check(False, f"[C1] module déclaré au registre mais absent du disque : {nom}")
    for nom in sorted(sur_disque - declares):
        b.check(False, f"[C1] dossier sur disque mais non déclaré au registre : app/modules/{nom}")
    b.check(declares == sur_disque, "[C1] bijection registre ↔ disque exacte")

    # Fichiers par module (ceux qui existent ET sont déclarés), puis le reste.
    fichiers_module: dict[str, list[Path]] = {
        nom: _fichiers_py(MODULES_DIR / nom) for nom in sorted(declares & sur_disque)
    }
    b.require(fichiers_module, len(modules), "[C0] modules scannés = modules déclarés")
    for nom in sorted(declares & sur_disque):
        b.check(len(fichiers_module[nom]) >= 1, f"[C0] {nom} : au moins un fichier Python lu")
    # Dossiers non déclarés : scannés quand même pour C7, jugés par C1.
    fichiers_orphelins = [f for nom in sorted(sur_disque - declares) for f in _fichiers_py(MODULES_DIR / nom)]
    fichiers_racine = sorted(p for p in MODULES_DIR.glob("*.py"))
    fichiers_ancien = [f for f in _fichiers_py(APP) if MODULES_DIR not in f.parents]
    fichiers_tools = _fichiers_py(TOOLS) if TOOLS.is_dir() else []
    b.check(len(fichiers_ancien) >= 1,
            f"[C0] ancien code scanné : au moins un fichier Python sous app/ hors modules "
            f"({len(fichiers_ancien)} lus)")

    # ── [C2] Un contrat par module ───────────────────────────────────────────────────────────
    for nom in sorted(declares & sur_disque):
        contrat = MODULES_DIR / nom / "contrat.py"
        if not b.check(contrat.is_file(), f"[C2] {nom} : contrat.py présent"):
            continue
        tree = lire(contrat)
        b.check(tree is not None and _version_contrat(tree),
                f"[C2] {nom} : contrat.py expose VERSION_CONTRAT (chaîne non vide, au niveau du module)")

    # ── [C3] & [C4] Ce qu'un module a le droit d'importer ────────────────────────────────────
    viol_c3 = viol_c4 = 0
    for nom, fichiers in fichiers_module.items():
        decl = par_nom[nom]
        soi = f"{RACINE}.{nom}"
        for fichier in fichiers:
            tree = lire(fichier)
            if tree is None:
                continue
            for ligne, enonce, cands in _imports(tree, fichier):
                if not any(_sous(c, "app") for c in cands):
                    continue  # bibliothèque standard ou tierce
                ou = f"{_rel(fichier)}:{ligne}"
                if all(_sous(c, soi) for c in cands) or LIBRE in cands:
                    continue  # son propre intérieur, ou le registre
                if any(_sous(c, RACINE) for c in cands):
                    # Un autre module : seul son contrat, et seulement s'il est déclaré lu.
                    autre = next((y for y in par_nom if y != nom
                                  and any(_sous(c, f"{RACINE}.{y}") for c in cands)), None)
                    if autre is None or f"{RACINE}.{autre}.contrat" not in cands:
                        viol_c3 += 1
                        b.check(False, f"[C3] accès interdit — {ou} : `{enonce}` "
                                       f"(d'un autre module, seul `{RACINE}.<module>.contrat` se lit)")
                    elif not (decl.lit_tous_les_contrats or autre in decl.lit):
                        viol_c3 += 1
                        b.check(False, f"[C3] lecture non déclarée — {ou} : `{enonce}` "
                                       f"({nom} ne déclare pas lire {autre} au registre)")
                    continue
                # Ancien code : permis seulement par une reprise déclarée.
                if not any(_sous(c, r) for c in cands for r in decl.reprises):
                    viol_c4 += 1
                    b.check(False, f"[C4] ancien code importé — {ou} : `{enonce}` "
                                   f"(absent des `reprises` de {nom} au registre)")
    # Le registre et le `__init__` du paquet n'importent rien de `app` (sinon la garde, qui charge
    # le registre par son chemin, ne le pourrait plus).
    for fichier in fichiers_racine:
        tree = lire(fichier)
        if tree is None:
            continue
        for ligne, enonce, cands in _imports(tree, fichier):
            if any(_sous(c, "app") for c in cands):
                viol_c4 += 1
                b.check(False, f"[C4] le registre reste autonome — {_rel(fichier)}:{ligne} : `{enonce}`")
    b.check(viol_c3 == 0, "[C3] un module n'importe d'un autre que son contrat, et le déclare")
    b.check(viol_c4 == 0, "[C4] un module n'importe l'ancien code que par ses reprises déclarées")

    # ── [C5] L'ancien code ne lit d'un module que son contrat ────────────────────────────────
    viol_c5 = 0
    for fichier in fichiers_ancien:
        tree = lire(fichier)
        if tree is None:
            continue
        for ligne, enonce, cands in _imports(tree, fichier):
            if not any(_sous(c, RACINE) for c in cands) or LIBRE in cands:
                continue
            if not any(c == f"{RACINE}.{y}.contrat" for c in cands for y in par_nom):
                viol_c5 += 1
                b.check(False, f"[C5] l'ancien code lit l'intérieur d'un module — "
                               f"{_rel(fichier)}:{ligne} : `{enonce}`")
    b.check(viol_c5 == 0, "[C5] l'ancien code ne lit d'un module que son contrat")

    # ── [C6] Un module possède ses tables ────────────────────────────────────────────────────
    collisions = [d for d in incoherences if "préfixes de tables" in d]
    for d in collisions:
        b.check(False, f"[C6] {d}")
    b.check(not collisions, "[C6] préfixes de tables uniques, aucun n'en prolonge un autre")
    prefixes = [(m.nom, re.compile(rf"\b{re.escape(m.prefixe_tables)}[a-z0-9_]+\b"))
                for m in modules if m.prefixe_tables]
    noms_modules = set(par_nom)  # un NOM de module n'est pas une table (`chef_de_dossier`)
    viol_c6 = 0
    for fichier in fichiers_ancien + fichiers_tools + fichiers_racine + fichiers_orphelins \
            + [f for fs in fichiers_module.values() for f in fs]:
        tree = lire(fichier)
        if tree is None and fichier not in textes:
            continue
        chaines = _chaines_hors_docstrings(tree) if tree is not None else [(0, textes[fichier])]
        for proprietaire, motif in prefixes:
            if MODULES_DIR / proprietaire in fichier.parents:
                continue
            for ligne, valeur in chaines:
                for nom_table in sorted(set(motif.findall(valeur)) - noms_modules):
                    viol_c6 += 1
                    b.check(False, f"[C6] table d'un autre — {_rel(fichier)}:{ligne} nomme "
                                   f"`{nom_table}` (préfixe de {proprietaire})")
    b.check(viol_c6 == 0, "[C6] aucune table d'un module nommée hors de son dossier")

    # ── [C7] Rien de propre à une juridiction ou à une société ───────────────────────────────
    viol_c7 = 0
    for fichier in fichiers_racine + fichiers_orphelins + [f for fs in fichiers_module.values() for f in fs]:
        if lire(fichier) is None:
            continue
        code = strip_code(textes[fichier])  # sans commentaires ni docstrings, chaînes gardées
        interne = fichier.relative_to(MODULES_DIR).parts
        adaptateur = len(interne) > 2 and interne[1] == SOUS_DOSSIER_ADAPTATEURS
        if not adaptateur:
            for jeton, motif in MOTIFS_JURIDICTION:
                if motif.search(code):
                    viol_c7 += 1
                    b.check(False, f"[C7] jeton de juridiction `{jeton}` dans {_rel(fichier)} "
                                   f"(sa place : un sous-dossier {SOUS_DOSSIER_ADAPTATEURS}/ ou un référentiel)")
        for symbole, motif in MOTIFS_SOCIETE:
            if motif.search(code):
                viol_c7 += 1
                b.check(False, f"[C7] symbole de société `{symbole}` dans {_rel(fichier)} "
                               f"(une société est une donnée, jamais du code)")
    b.check(viol_c7 == 0, "[C7] aucun jeton de juridiction ni symbole de société dans le cœur des "
                          "modules (liste = filet, pas preuve)")

    return b.summary()


if __name__ == "__main__":
    sys.exit(main())
