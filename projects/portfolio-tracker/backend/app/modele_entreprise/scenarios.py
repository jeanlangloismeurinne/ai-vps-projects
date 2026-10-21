"""L'application des déplacements d'un scénario sur les cellules centrales (§5, lot M1 — 09 §12.2).

`appliquer_scenario` est la CHARNIÈRE du moteur de scénarios : le central est une copie à
l'identique des valeurs centrales ; un scénario nommé ou une branche déplace seulement les
cellules que ses déplacements touchent, vers une borne de fourchette ou une valeur dite — jamais
une formule (09 §12.2). Pure, déterministe, sans appel de modèle.

⚠️ RIEN N'APPELLE ENCORE CETTE FONCTION hors des checks : M7 la branchera sur `evaluer_modele`.
Elle est écrite et éprouvée dès M1 pour que brancher le moteur de scénarios (M6) n'ait rien à
réécrire ici ni dans la valorisation — mais tant que M6/M7 ne l'appellent pas, aucun lecteur ne
doit la croire déjà branchée (voir `ARCHITECTURE.md`).
"""
from __future__ import annotations

from typing import Mapping, Sequence

from app.contracts.modele_entreprise_schema import Deplacement, Fourchette, Scenario, annee_de_periode

__all__ = ["ScenarioInapplicable", "Cle", "appliquer_scenario"]

# (bloc, variable, période) — la clé d'une cellule centrale.
Cle = tuple[str, str, str]


class ScenarioInapplicable(Exception):
    """Un déplacement ne trouve aucune fourchette qui le couvre, ou ne touche AUCUNE cellule
    centrale — « un risque cité qui ne bouge rien » (09 §6)."""


def _dans_plage(periode: str, debut: str, fin: str) -> bool:
    a = annee_de_periode(periode)
    ad, af = annee_de_periode(debut), annee_de_periode(fin)
    if a is None or ad is None or af is None:
        return periode == debut == fin == "sans_periode"
    return ad <= a <= af


def appliquer_scenario(
    centrales: Mapping[Cle, float], scenario: Scenario, fourchettes: Sequence[Fourchette],
) -> dict[Cle, float]:
    """Projette `scenario` sur `centrales`. Lève `ScenarioInapplicable` (motif nommé) si un
    déplacement ne touche aucune cellule, ou si une borne qu'il vise n'a pas de fourchette qui la
    couvre. Les clés non visées par aucun déplacement restent au central."""
    if scenario.nature == "central":
        return dict(centrales)

    resultat: dict[Cle, float] = dict(centrales)
    for d in scenario.deplacements:
        cles = [cle for cle in centrales
                if cle[0] == d.bloc and cle[1] == d.variable and _dans_plage(cle[2], d.periode_debut, d.periode_fin)]
        if not cles:
            raise ScenarioInapplicable(
                f"le déplacement du scénario `{scenario.nom}` sur (`{d.bloc}`, `{d.variable}`, "
                f"`{d.periode_debut}`..`{d.periode_fin}`) ne touche AUCUNE cellule centrale — un "
                "risque cité qui ne bouge rien")
        for cle in cles:
            if d.cible == "valeur_dite":
                resultat[cle] = d.valeur_dite  # type: ignore[assignment]
                continue
            fourchette = next(
                (f for f in fourchettes
                 if f.bloc == d.bloc and f.variable == d.variable and _dans_plage(cle[2], f.periode_debut, f.periode_fin)),
                None)
            if fourchette is None:
                raise ScenarioInapplicable(
                    f"le déplacement du scénario `{scenario.nom}` sur (`{d.bloc}`, `{d.variable}`, "
                    f"`{cle[2]}`) vise `{d.cible}`, mais aucune fourchette ne couvre cette cellule")
            resultat[cle] = fourchette.bas if d.cible == "borne_basse" else fourchette.haut
    return resultat
