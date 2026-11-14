"""Registre des modules — DÉTENTEUR UNIQUE de leur déclaration.

Ce qu'un module rend, les tables qu'il possède, les contrats qu'il lit et l'ancien code qu'il
reprend sont écrits ICI et nulle part ailleurs. `checks/check_charte_modules.py` confronte ce
registre au disque et aux imports réels : une déclaration fausse rougit, un accès non déclaré aussi.

Bibliothèque standard seulement : la garde charge ce fichier par son chemin, sans importer `app`.
Rien de propre à une société, à un pays ou à une place de cotation n'a sa place ici.

Ajouter un module : `ARCHITECTURE.md` (même dossier), § « Ajouter un module ».
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    """Déclaration d'un module. `nom` est le nom de son sous-dossier dans `app/modules/`."""

    nom: str
    # Une phrase : l'objet de sortie, celui que `contrat.py` versionne et donne à lire.
    rend: str
    # Préfixe de TOUTES ses tables (se termine par « _ ») ; `None` s'il n'en possède aucune.
    prefixe_tables: str | None = None
    # Noms des modules dont il lit le contrat de sortie.
    lit: tuple[str, ...] = ()
    # Chemins d'import de l'ANCIEN code repris derrière le contrat (ex. `app.knowledge.perimetre`).
    # Dette visible : chaque entrée est un accès que la reconstruction n'a pas encore remplacé.
    reprises: tuple[str, ...] = ()
    # Réservé au chef de dossier : lit tous les contrats, n'en écrit aucun.
    lit_tous_les_contrats: bool = False


MODULES: tuple[Module, ...] = (
    Module(
        nom="chef_de_dossier",
        rend="L'état d'un dossier et son pas suivant, avec la dépense engagée.",
        prefixe_tables="chef_",
        lit_tous_les_contrats=True,
    ),
    Module(
        nom="emetteurs",
        rend="La fiche d'un émetteur : qui il est, où il publie, sa spécialité, et les sources "
             "admises ou révoquées qui valent pour lui.",
        prefixe_tables="emetteurs_",
        lit=("chef_de_dossier",),  # pour déclarer son pas (charte, point 8)
    ),
)


def noms() -> tuple[str, ...]:
    """Les noms des modules déclarés, dans l'ordre du registre."""
    return tuple(m.nom for m in MODULES)


def par_nom(nom: str) -> Module:
    """Le module déclaré sous ce nom. `KeyError` s'il ne l'est pas : pas de module implicite."""
    for m in MODULES:
        if m.nom == nom:
            return m
    raise KeyError(f"module non déclaré au registre : {nom!r}")


def incoherences() -> list[str]:
    """Les défauts du registre LUI-MÊME (sans regarder le disque) ; liste vide s'il est cohérent.

    Deux préfixes de tables égaux, ou dont l'un commence par l'autre, rendraient la propriété d'une
    table indécidable : ils sont refusés ici plutôt que découverts à la première collision.
    """
    defauts: list[str] = []
    vus: set[str] = set()
    for m in MODULES:
        if m.nom in vus:
            defauts.append(f"nom déclaré deux fois : {m.nom}")
        vus.add(m.nom)
        if not m.nom.isidentifier() or m.nom != m.nom.lower():
            defauts.append(f"{m.nom} : le nom doit être un identifiant en minuscules")
        if not m.rend.strip():
            defauts.append(f"{m.nom} : `rend` est vide")
        p = m.prefixe_tables
        if p is not None and not (len(p) > 1 and p.endswith("_") and p.islower() and p[0].isalpha()):
            defauts.append(f"{m.nom} : préfixe de tables mal formé ({p!r})")
    connus = set(noms())
    for m in MODULES:
        for cible in m.lit:
            if cible == m.nom:
                defauts.append(f"{m.nom} : se déclare lecteur de lui-même")
            elif cible not in connus:
                defauts.append(f"{m.nom} : lit un module non déclaré ({cible})")
        for chemin in m.reprises:
            if not chemin.startswith("app.") or chemin.startswith("app.modules"):
                defauts.append(f"{m.nom} : reprise hors de l'ancien code ({chemin})")
    avec = [m for m in MODULES if m.prefixe_tables]
    for i, a in enumerate(avec):
        for c in avec[i + 1:]:
            if a.prefixe_tables.startswith(c.prefixe_tables) or c.prefixe_tables.startswith(a.prefixe_tables):
                defauts.append(
                    f"préfixes de tables en collision : {a.nom} ({a.prefixe_tables}) "
                    f"et {c.nom} ({c.prefixe_tables})")
    return defauts
