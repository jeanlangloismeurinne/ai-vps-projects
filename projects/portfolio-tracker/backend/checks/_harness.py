"""Harnais des checks — DÉTENTEUR UNIQUE des garde-fous anti-faux-verts (#46 appliqué à la
méthode de test elle-même).

POURQUOI CE FICHIER. Chaque check ré-implémentait les mêmes protections, et une protection recopiée
re-diverge au correctif suivant. Les trois pièges qu'il neutralise, chacun mesuré sur ce projet :

  1. **Un grep d'interdit lit sa propre énonciation** — le token interdit vit dans la docstring qui
     l'interdit → `strip_code()` retire commentaires ET docstrings par `tokenize` (jamais un
     `split('\"\"\"')` qui ne coupe que la docstring de module). Cf. `feedback_grep_interdit_lit_sa_propre_enonciation`.
  2. **Un grep de présence est satisfait par la prose** — « le fichier importe X » écrit
     `"X" in source` reste vrai si X survit dans un commentaire → `imports_symbol()` interroge la
     STRUCTURE (`ast`), qu'aucun texte ne peut satisfaire. Cf. convention #56.
  3. **Un assert `all(...)` sur une liste VIDE est vert sur rien** — `Bilan.require()` exige la
     cardinalité attendue avant de juger. Cf. le 5ᵉ faux-vert de la convention #63.

Le bilan est reconnaissable à sa FORME (`N vérifications OK, M échec(s)`), lu par `run_all.sh`.
"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path


def strip_code(text: str) -> str:
    """Retourne le source privé de ses commentaires ET docstrings — pour chercher un interdit dans
    le CODE, jamais dans la prose qui l'explique. Robuste : `tokenize`, pas un découpage de chaînes.
    """
    out: list[str] = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError):
        # Un source illisible ne doit pas passer pour « aucun interdit trouvé » : on rend le texte
        # brut, quitte à ce que l'appelant surdétecte (faux rouge visible), jamais sous-détecter.
        return text
    prev_type = tokenize.INDENT
    prev_end = (1, 0)
    for tok in toks:
        if tok.type in (tokenize.COMMENT, tokenize.ENCODING, tokenize.NL):
            continue
        # Une STRING seule sur sa ligne logique (docstring / string-statement) est retirée.
        if tok.type == tokenize.STRING and prev_type in (
            tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT, tokenize.NL,
        ):
            prev_type = tok.type
            prev_end = tok.end
            continue
        srow, scol = tok.start
        prow, pcol = prev_end
        if srow > prow:
            out.append("\n" * (srow - prow))
            out.append(" " * scol)
        elif scol > pcol:
            out.append(" " * (scol - pcol))
        out.append(tok.string)
        prev_type = tok.type
        prev_end = tok.end
    return "".join(out)


def imports_symbol(path: str | Path, symbol: str, *, from_module: str | None = None) -> bool:
    """Vrai si `path` IMPORTE réellement `symbol` (via `ast`), pas s'il le mentionne. Si
    `from_module` est donné, exige `from <from_module> import <symbol>`."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if from_module is not None and node.module != from_module:
                continue
            for alias in node.names:
                if alias.name == symbol:
                    return True
        elif isinstance(node, ast.Import) and from_module is None:
            for alias in node.names:
                if alias.name == symbol or alias.asname == symbol:
                    return True
    return False


async def colonne_absente(conn, table: str, colonne: str) -> bool:
    """Vrai si `colonne` n'existe PAS encore sur `table` dans la base que `conn` interroge —
    DÉTENTEUR UNIQUE (#46) du garde-fou « cette migration additive est-elle appliquée ICI ? ».

    Une migration ADDITIVE (une colonne neuve sur une table lue par un chemin PARTAGÉ, comme
    `comite_decisions.retablie_depuis_id` au point 13) rend TOUT lecteur/écrivain de ce chemin
    dépendant d'elle, pas seulement le geste qui l'a motivée — exactement comme #139/migration 059
    pour `ticker_archetypes`. Tant qu'elle n'est pas appliquée (interdit explicite d'une session de
    validation), un check qui la suppose lève une `UndefinedColumnError` brute : un script mort
    avant son bilan, le 2ᵉ faux vert (`feedback_check_degrade_en_sortant_a_zero`). Ce garde-fou en
    fait un échec NOMMÉ à la place — jamais un saut muet, jamais une trace Python."""
    return not await conn.fetchval(
        "SELECT 1 FROM information_schema.columns WHERE table_name = $1 AND column_name = $2",
        table, colonne)


async def table_absente(conn, table: str) -> bool:
    """Vrai si `table` n'existe PAS encore dans la base que `conn` interroge — même rôle que
    `colonne_absente`, pour une migration additive qui crée des TABLES plutôt qu'une colonne sur une
    table partagée (061 : `architectures_modele` et ses trois registres). Tant qu'elle n'est pas
    appliquée, un check qui la suppose lève une `UndefinedTableError` brute : un script mort avant
    son bilan (2ᵉ faux vert, `feedback_check_degrade_en_sortant_a_zero`). Ce garde-fou en fait un
    échec NOMMÉ à la place."""
    return not await conn.fetchval(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1",
        table)


class Bilan:
    """Compteur d'assertions à bilan reconnaissable. `ok`/`fail` nomment toujours le critère ;
    `require(seq, n, …)` interdit le faux-vert de la sélection vide."""

    def __init__(self) -> None:
        self._ok = 0
        self._fail = 0

    def check(self, condition: bool, label: str) -> bool:
        if condition:
            self._ok += 1
        else:
            self._fail += 1
            print(f"  FAIL {label}")
        return condition

    def require(self, seq, n: int, label: str) -> bool:
        """Échoue si `len(seq) != n` — à mettre AVANT tout `all(...)`/`any(...)` sur une sélection,
        sinon l'assert est vert sur zéro élément."""
        got = len(list(seq))
        return self.check(got == n, f"{label} — cardinalité attendue {n}, obtenue {got}")

    def summary(self) -> int:
        print(f"\n{self._ok} vérifications OK, {self._fail} échec(s)")
        return 1 if self._fail else 0
