"""Formatage des montants pour le corpus narratif — **détenteur unique** de la règle d'unité.

Pourquoi un module à part (F10, trouvé sur RVMD). La règle « un montant choisit son unité par
ordre de grandeur » a été écrite au correctif F9 dans `base_rate_corpus._mds`, et *seulement* là.
Ses deux voisins portaient le même défaut, non corrigé : `edgar_feed._md` et `financials_feed._md`
divisaient tous deux par 1e9 en dur. Sur RVMD, le capex FY2025 (15,99 M$) s'écrivait donc
« 0,0 MdUSD » — un agent lit *aucun investissement* — et l'entry `fcf_conversion_pct` publiait
« FCF -0,9 Md = cash-flow opérationnel -0,9 Md − capex 0,0 Md », dont l'arithmétique **paraît
juste** précisément parce que les deux termes sont écrasés à la même unité.

C'est le corollaire de méthode de la convention #43, appliqué à un format au lieu d'une clef de
supersedage : une règle recopiée dans trois producteurs n'est pas corrigée quand on corrige l'un
des trois. Elle vit ici, les trois l'importent.

Ce que la règle garantit, et qui est du fond, pas de la présentation :
  * **aucun montant non nul ne s'arrondit à zéro** — un montant arrondi à zéro n'est pas imprécis,
    il est faux (`0,0 Md$` de ventes se lit « aucune vente ») ;
  * **une absence n'est jamais un zéro** — `None` → `n/d` ;
  * **un vrai zéro se distingue d'un arrondi** — `0 USD`, qui ne peut se confondre avec aucun
    palier écrasé (même famille que #44 : calculé / non calculable / absent sont trois états) ;
  * **l'arrondi promeut l'unité** — choisir le palier avant d'arrondir écrit 999 999 $
    « 1000,0 k$ », l'arrondi faisant changer d'ordre de grandeur à la valeur sans que l'unité suive.
"""
from typing import Optional

# Paliers du plus petit au plus grand. Le préfixe est collé à la devise par l'appelant
# (`Md` + `USD` → `MdUSD`, `M` + `$` → `M$`), ce qui laisse chaque feed garder sa notation.
_PALIERS = ((1e3, "k"), (1e6, "M"), (1e9, "Md"))


def montant(v: Optional[float], devise: str = "", *, nd: int = 1) -> str:
    """Montant en format FR, unité choisie par l'ordre de grandeur **après** l'arrondi.

    `devise` est collée au préfixe d'unité (`montant(2.61e9, "USD")` → `2,61 MdUSD` avec `nd=2`,
    `montant(11.58e6, "$")` → `11,6 M$`). `nd` = décimales du mantisse : les feeds EDGAR en
    demandent 2 (un poste de bilan à 2,61 Md n'est pas 2,6 Md), les feeds dérivés 1.
    """
    if v is None:
        return "n/d"
    v = float(v)
    if v == 0:
        # Un vrai zéro n'est pas un arrondi : il s'écrit sans mantisse ni palier.
        return f"0 {devise}".rstrip()
    seuil, prefixe = 1.0, ""
    for s, p in _PALIERS:
        # On PROMEUT tant que l'arrondi ferait franchir le palier suivant.
        if round(abs(v) / s, nd) >= 1.0:
            seuil, prefixe = s, p
    if not prefixe:
        return f"{v:.0f} {devise}".rstrip()
    return f"{v / seuil:.{nd}f} {prefixe}{devise}".replace(".", ",")
