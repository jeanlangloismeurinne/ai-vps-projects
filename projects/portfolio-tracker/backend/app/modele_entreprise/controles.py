"""Les CONTRÔLES déterministes d'une cellule du classeur de l'entreprise (§4, lot M1).

Vocabulaire FERMÉ, détenu par `app/frameworks/modele_entreprise.yaml` (`controles:`) — le pont
[R4] (`app/modele_entreprise/referentiel.py`) vérifie que ce fichier et celui-là se répondent
exactement, dans les deux sens : un nom du référentiel sans fonction ici serait un contrôle qui ne
contrôle jamais rien ; une fonction ici sans nom au référentiel serait du code mort.

Chaque contrôle est PUR : `(Cellule, ContexteControle) -> Optional[str]`, `None` si la cellule
tient, sinon le motif du refus — jamais une exception, jamais un booléen nu qui perdrait le motif.

`part_calculee` est le seul contrôle qui a besoin d'un CONTEXTE (`dernier_exercice_publie`) : la
part prise se mesure sur des revenus publiés, jamais sur des revenus futurs (09 §6, un marché
d'extension pris pour plafond du bloc actuel est le cas que ce contrôle arrête). Une absence
d'exercice connu n'est JAMAIS un vert par défaut (`feedback_check_degrade_en_sortant_a_zero`) : elle
refuse, nommément.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from app.contracts.formule_grammaire import (
    FormuleInexecutable, denominateurs_de_la_formule, noms_de_la_formule,
)
from app.contracts.modele_entreprise_schema import Cellule, OrigineCalcul

__all__ = ["ContexteControle", "CONTROLES"]


@dataclass(frozen=True)
class ContexteControle:
    """Ce qu'un contrôle a besoin de connaître AU-DELÀ de la cellule elle-même. Pour l'instant,
    seul `dernier_exercice_publie` (`FY####` ou `None`) — lu par `part_calculee`."""
    dernier_exercice_publie: Optional[str] = None


def _positif(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    if cellule.valeur > 0:
        return None
    return f"`{cellule.variable}` doit être strictement positive, vaut {cellule.valeur}"


def _positif_ou_nul(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    if cellule.valeur >= 0:
        return None
    return f"`{cellule.variable}` doit être positive ou nulle, vaut {cellule.valeur}"


def _proportion(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    if 0.0 <= cellule.valeur <= 100.0:
        return None
    return f"`{cellule.variable}` doit être une proportion entre 0 et 100 (%), vaut {cellule.valeur}"


def _probabilite(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    if 0.0 <= cellule.valeur <= 1.0:
        return None
    return f"`{cellule.variable}` doit être une probabilité entre 0 et 1, vaut {cellule.valeur}"


def _annee(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    v = cellule.valeur
    if v == int(v) and 1900 <= int(v) <= 2100:
        return None
    return f"`{cellule.variable}` doit être une année entière entre 1900 et 2100, vaut {cellule.valeur}"


def _part_calculee(cellule: Cellule, ctx: ContexteControle) -> Optional[str]:
    if not isinstance(cellule.origine, OrigineCalcul):
        return f"`{cellule.variable}` : la part prise doit être CALCULÉE, pas d'origine `{cellule.origine.type}`"
    formule = cellule.origine.formule
    try:
        noms = noms_de_la_formule(formule)
        denominateurs = denominateurs_de_la_formule(formule)
    except FormuleInexecutable as e:
        return f"`{cellule.variable}` : formule inexécutable — {e}"
    if "chiffre_affaires_du_bloc" not in noms or "taille_du_marche" not in denominateurs:
        return (f"`{cellule.variable}` : la formule « {formule} » doit porter `chiffre_affaires_du_bloc` "
                "au numérateur et `taille_du_marche` au dénominateur")
    if ctx.dernier_exercice_publie is None:
        return f"`{cellule.variable}` : exercice publié inconnu — la part prise ne peut pas être contrôlée"
    if cellule.periode > ctx.dernier_exercice_publie:
        return (f"`{cellule.variable}` : la part prise est mesurée à `{cellule.periode}`, postérieure au "
                f"dernier exercice publié `{ctx.dernier_exercice_publie}` — jamais sur des revenus futurs "
                "(09 §6)")
    return None


CONTROLES: dict[str, Callable[[Cellule, ContexteControle], Optional[str]]] = {
    "positif": _positif,
    "positif_ou_nul": _positif_ou_nul,
    "proportion": _proportion,
    "probabilite": _probabilite,
    "annee": _annee,
    "part_calculee": _part_calculee,
}
