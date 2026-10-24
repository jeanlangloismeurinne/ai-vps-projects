"""L'INVENTAIRE des éléments futurs d'une entreprise — plan « découpage » B4g, maillon 1 (2026-10-24).

Arbitrage de l'utilisateur du 2026-10-24 : séparer RELEVER (ce que le dossier nomme), CLASSER (l'arbre
de décision, un modèle) et CONSTRUIRE (l'architecture, du code). Ce contrat est le premier maillon : une
FICHE par élément × marché, des FAITS recopiés du dossier, AUCUN jugement de classement (ni « déjà
vendu », ni « génération suivante » — c'est le maillon 2).

Mesuré avant (`roadmap/V3/mesures/2026-10-24/me7-rejeux/`) : la réponse en texte de `me_7`, rejouée trois
fois sur les mêmes pièces, change de liste (NVDA 4/4/3, Vera CPU omis une fois) et d'UNITÉ (RVMD : la
molécule, puis l'essai clinique). D'où une unité FIXÉE (élément × marché) et des champs recopiés, que le
code vérifie contre les pièces (`app/modele_entreprise/inventaire.py`).
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import Field

from .analysis_v2_schemas import Strict

__all__ = ["JalonInventaire", "FicheElement", "ElementsNonNommes", "InventaireSortie"]


class JalonInventaire(Strict):
    libelle: Annotated[str, Field(min_length=3)]
    # Telle que le dossier l'écrit (« 2026-08-26 », « T4 2026 », « S1 2027 ») — `None` si non datée.
    date: Optional[Annotated[str, Field(min_length=4)]] = None


class FicheElement(Strict):
    """UN élément × UN marché. Une molécule dans deux indications = deux fiches, sous le MÊME `nom`."""
    # Le nom de l'élément, RECOPIÉ (molécule, produit, plateforme, acquisition, accord, initiative) —
    # le nom seul, sans sa description. Vérifié : figure littéralement dans une pièce citée.
    nom: Annotated[str, Field(min_length=1)]
    # Le marché visé, RECOPIÉ (maladie et ligne de traitement ; acheteurs ; type de clients ; zone) —
    # `None` si le dossier n'en nomme aucun. Vérifié : figure littéralement dans une pièce citée.
    marche_vise: Optional[Annotated[str, Field(min_length=2)]] = None
    # Le passage de la pièce qui parle de l'élément, RECOPIÉ mot pour mot. Vérifié littéralement.
    extrait: Annotated[str, Field(min_length=20)]
    stade: Optional[Annotated[str, Field(min_length=2)]] = None
    dernier_jalon: Optional[JalonInventaire] = None
    prochain_jalon: Optional[JalonInventaire] = None
    origine: Literal["interne", "acquisition", "licence", "partenariat", "non_dit"]
    pieces: Annotated[list[int], Field(min_length=1)]


class ElementsNonNommes(Strict):
    """Ce que le dossier COMPTE sans le nommer individuellement (recherche amont)."""
    nombre: Annotated[int, Field(ge=1)]
    extrait: Annotated[str, Field(min_length=20)]
    pieces: Annotated[list[int], Field(min_length=1)]


class InventaireSortie(Strict):
    fiches: list[FicheElement] = Field(default_factory=list)
    non_nommes: Optional[ElementsNonNommes] = None
