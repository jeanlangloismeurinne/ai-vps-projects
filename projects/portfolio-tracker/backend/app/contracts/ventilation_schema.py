"""Contrat PYDANTIC strict du référentiel de VENTILATION PUBLIÉE (lot M2, roadmap V3 11).

POURQUOI CE CONTRAT. `ventilation_publiee.yaml` est une DONNÉE (comme `socle_comptes.yaml`) : ajouter
un axe ou un qualificateur ne touche aucun code. Ce contrat est la garde de RÉPLICABILITÉ au
chargement (#46) : aucun ticker, CIK, ou nom de segment/membre PROPRE À UN ÉMETTEUR ne peut y entrer,
parce que tout axe et tout membre doit porter un préfixe de taxonomie STANDARD (`us-gaap:`, `srt:`) —
une extension d'émetteur (`nvda:`, `jpm:`, `rvmd:`…) y serait refusée à la validation, pas seulement au
grep de `check_ventilation_publiee.py` [V12].

Validé par `charger_referentiel` (`app/knowledge/ventilation.py`), gardé par
`checks/check_ventilation_publiee.py` + `checks/negatif_ventilation_publiee.sh`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Taxonomies STANDARD admises pour un axe ou un membre du référentiel — jamais une extension
# d'émetteur (`nvda:`, `jpm:`, `rvmd:`…). C'est la garde de réplicabilité au CHARGEMENT (#46) :
# un ticker ne peut pas entrer dans ce fichier sans faire échouer la validation.
_PREFIXES_ADMIS = ("us-gaap:", "srt:")


def _exige_prefixe_standard(valeur: str, *, champ: str) -> str:
    if not valeur.startswith(_PREFIXES_ADMIS):
        raise ValueError(
            f"{champ} « {valeur} » hors des taxonomies standard {_PREFIXES_ADMIS} — un axe ou un "
            "membre du référentiel de ventilation ne nomme jamais une extension d'émetteur"
        )
    return valeur


class AxeVentilation(BaseModel):
    """Un axe de ventilation que le fonds relève. `raccord` fixe comment le premier niveau se
    rapproche du total publié : `total` (la somme se rapproche du total du gabarit) ou `aucun`
    (des proportions rapportées à des bases différentes — jamais sommées, §2 `clients`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    libelle: str
    axe: str
    raccord: Literal["total", "aucun"]
    concepts: tuple[str, ...] = ()
    qualificateurs: tuple[str, ...] = ()

    @field_validator("axe")
    @classmethod
    def _axe_standard(cls, v: str) -> str:
        return _exige_prefixe_standard(v, champ="axe")

    @field_validator("concepts")
    @classmethod
    def _concepts_standard(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for c in v:
            _exige_prefixe_standard(c, champ="concept")
        return v

    @field_validator("qualificateurs")
    @classmethod
    def _qualificateurs_standard(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for q in v:
            _exige_prefixe_standard(q, champ="qualificateur")
        return v

    @model_validator(mode="after")
    def _coherence_raccord(self) -> "AxeVentilation":
        if self.raccord == "aucun" and not self.concepts:
            raise ValueError(
                f"axe « {self.id} » : raccord `aucun` exige des `concepts` déclarés — sans eux rien "
                "ne dit quel concept porte la proportion (ex. `clients`)"
            )
        if self.raccord == "total" and self.concepts:
            raise ValueError(
                f"axe « {self.id} » : raccord `total` lit les concepts des RECETTES du gabarit "
                "(détenteur unique, #46) — il ne porte pas sa propre liste de concepts"
            )
        if self.qualificateurs and self.raccord != "aucun":
            raise ValueError(
                f"axe « {self.id} » : des `qualificateurs` n'ont de sens que pour un axe `raccord: "
                "aucun` (une base de proportion) — un axe à `raccord: total` n'en a pas besoin"
            )
        return self


class QualificateurNeutre(BaseModel):
    """Un (axe, membre) qui ne change pas le sens d'un fait — ignoré pour le classement (§4.1)."""

    model_config = ConfigDict(extra="forbid")

    axe: str
    membre: str

    @field_validator("axe")
    @classmethod
    def _axe_standard(cls, v: str) -> str:
        return _exige_prefixe_standard(v, champ="qualificateur_neutre.axe")

    @field_validator("membre")
    @classmethod
    def _membre_standard(cls, v: str) -> str:
        return _exige_prefixe_standard(v, champ="qualificateur_neutre.membre")


class VentilationReferentiel(BaseModel):
    """Le référentiel entier — `version` clefe les pièces publiées (`version_referentiel`)."""

    model_config = ConfigDict(extra="forbid")

    version: str
    axes: tuple[AxeVentilation, ...]
    qualificateurs_neutres: tuple[QualificateurNeutre, ...] = ()
    membres_secteur_unique: tuple[str, ...] = ()
    # Le SEUIL du signal d'acquisition significative (§4 bis, lot P1) — paramètre du FONDS, pas un
    # seuil calé sur un émetteur : 5 % du chiffre d'affaires de l'exercice (ou, faute de chiffre
    # d'affaires acquis publié, 5 % de la contrepartie rapportée à la capitalisation) par défaut.
    seuil_acquisition_significative: float = 0.05

    @field_validator("seuil_acquisition_significative")
    @classmethod
    def _seuil_acquisition_borne(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError(
                f"seuil_acquisition_significative = {v} hors de (0, 1] — c'est une PART du chiffre "
                "d'affaires ou de la capitalisation, jamais un montant ni un pourcentage sur 100")
        return v

    @field_validator("membres_secteur_unique")
    @classmethod
    def _membres_secteur_unique_standard(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for m in v:
            _exige_prefixe_standard(m, champ="membres_secteur_unique")
        return v

    @model_validator(mode="after")
    def _unicite(self) -> "VentilationReferentiel":
        ids = [a.id for a in self.axes]
        if len(ids) != len(set(ids)):
            raise ValueError(f"ids d'axe en double : {ids}")
        bruts = [a.axe for a in self.axes]
        if len(bruts) != len(set(bruts)):
            raise ValueError(f"axe XBRL déclaré par deux fiches à la fois : {bruts}")
        return self
