"""Contrat du module « Comptes et segments » (M4) — OUVERT AU REGISTRE AVEC SON SEUL BESOIN.

Ce que ferait un vrai fonds : le modélisateur demande les comptes parce qu'il doit modéliser ; ce n'est
pas la documentation qui décide quoi collecter. Tant que M4 n'est pas ouvert, ce module ne fait rien
d'autre que déclarer, en donnée (`referentiel.json`), ce qu'il demande pour ouvrir un dossier
(M3 §2, point 1).

L'objet de sortie de M4 (les comptes reconstitués) n'existe pas encore : ce contrat ne rend que les
besoins initiaux. Rien ici ne connaît une société, un pays ni un formulaire.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION_CONTRAT = "1.0.0"
NOM_DU_MODULE = "comptes"

_REFERENTIEL = Path(__file__).resolve().parent / "referentiel.json"


def besoins_initiaux() -> list[dict[str, Any]]:
    """Ce que le module demande pour ouvrir un dossier : une liste de genres de document (vocabulaire
    de la collecte), avec `depuis` pour un genre qui s'étend dans le temps. Une copie, jamais le
    référentiel lui-même."""
    with _REFERENTIEL.open(encoding="utf-8") as f:
        return [dict(b) for b in json.load(f)["besoins_initiaux"]]
