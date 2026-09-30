"""Préparer le dossier que l'analyste lit — DÉTENTEUR UNIQUE, pour la chaîne et pour le bouclage (#106).

Les deux chemins qui font répondre l'analyste (`tools/executer_chaine.py`, `bouclage.boucler_renvois`)
faisaient la même séquence à la main : charger le dossier, puis calculer les faits postérieurs aux
comptes (#103). Deux recopies divergent au premier correctif (#46) ; et le correctif est arrivé :

Comme un vrai fonds, avant de rédiger, l'analyste LIT les dépôts publiés depuis les derniers comptes
qui rouvrent ses questions et les range au dossier. Le système le fait ici — `lecture_depot` dépose le
texte du dépôt, tel quel, sans modèle — et ces lectures sont jointes d'office au dossier : sans elles,
le fait n'est pas montré à l'analyste (#103 ne montre un fait que si une pièce tirée du dépôt est
citable), et sa réponse naît périmée (réponse RVMD qf_4 #976, 2026-09-30).

Ce module ÉCRIT (les lectures de dépôts) : c'est le seul pas d'écriture avant l'analyste, gratuit
(EDGAR), idempotent (un dépôt se lit une fois).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.agents.v2.dossier import Dossier, charger_dossier
from app.agents.v2.parcours import faits_posterieurs_du_titre, horloge_du_titre
from app.knowledge.lecture_depot import Lecture, assurer_lectures, ids_des_lectures


@dataclass(frozen=True)
class DossierPrepare:
    dossier: Dossier
    faits: dict[str, list]          # par question : les faits postérieurs aux comptes à lire (#103)
    lectures: list[Lecture]         # les dépôts lus (ou non, avec leur motif) pour ces faits


async def preparer_dossier_analyste(
    conn, *, ticker_id: str, framework_id: str, fichier: Any, plafond: int,
    questions: Optional[Iterable[str]] = None,
) -> DossierPrepare:
    """Faits postérieurs → lectures des dépôts (écrites si absentes) → dossier avec ces lectures jointes.

    `questions` restreint les faits (et donc les dépôts lus) aux questions du passage ; `None` = toutes
    les questions du framework."""
    perimetre = None if questions is None else set(questions)
    faits = await faits_posterieurs_du_titre(conn, ticker_id, fichier, framework_id)
    evenements = [e for qid, evs in faits.items() if perimetre is None or qid in perimetre for e in evs]
    lectures: list[Lecture] = []
    if evenements:
        ancre, _notes = await horloge_du_titre(conn, ticker_id, fichier)
        lectures = await assurer_lectures(conn, ticker_id, ancre.cik, evenements)
    dossier = await charger_dossier(
        conn, ticker_id=ticker_id, framework_id=framework_id,
        framework_version=fichier.schema_version, plafond=plafond,
        joindre=ids_des_lectures(lectures))
    return DossierPrepare(dossier=dossier, faits=faits, lectures=lectures)
