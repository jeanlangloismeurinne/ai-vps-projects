"""Dépouiller un source de sa prose — détenteur unique (#46).

POURQUOI CE FICHIER EXISTE. Un garde-fou écrit en `grep` de token se trompe DANS LES DEUX SENS
(#56) : un grep d'*absence* est mis en défaut par la prose — le token interdit est dans le
commentaire qui l'interdit, faux ROUGE
(`feedback_grep_interdit_lit_sa_propre_enonciation`) — et un grep de *présence* est satisfait par
elle, faux VERT. Le remède du premier sens est de retirer commentaires et docstrings avant de
chercher, puis d'asserter l'interdit **en positif** (« la prose NOMME le détenteur »).

Ce dépouillement vivait dans `check_framework_contract.py`. Le lot 2b en a eu besoin dans
`check_search_worker.py`, et une deuxième copie serait exactement ce que #46 décrit : deux
implémentations d'accord aujourd'hui, divergentes au prochain correctif, en silence. Elle vit donc
ici, et les checks l'importent.

⚠️ `tokenize`, jamais un `split('\"\"\"')` : mesuré, la 1ʳᵉ version coupait au `\"\"\"` du module,
donc ne retirait que la docstring de module, et rougissait sur un token cité dans la docstring
d'une classe plus bas.
"""
from __future__ import annotations

import io
import tokenize


def code_seul(source: str) -> str:
    """Le source privé de ses commentaires et de toutes ses chaînes (donc de ses docstrings).

    Les jetons restants sont recollés séparés par une espace : on cherche des NOMS dedans, pas de
    la syntaxe. `x=1` y devient `x = 1`, ce qui est sans effet sur un `"foo" in code_seul(src)`
    portant sur un identifiant, mais casserait un motif à ponctuation collée — chercher `covers=`
    sur le résultat ne trouverait rien même si le code le contient. Chercher le NOM, pas le signe.
    """
    morceaux: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        morceaux.append(tok.string)
    return " ".join(morceaux)
