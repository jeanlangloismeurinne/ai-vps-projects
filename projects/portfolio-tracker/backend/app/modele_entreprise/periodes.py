"""Les PÉRIODES DU CLASSEUR — détenteur unique (lot M3, roadmap V3 `12-lot-M3-architecte.md` §3.4).

`PeriodeCellule` (contrat, `^(FY[0-9]{4}|sans_periode)$`) ne porte qu'une ANNÉE — plus courte que
l'id d'un exercice du socle des comptes (`FY2026-01-25`, daté de sa clôture, §4 de `socle_comptes.py`).
Ce module est le SEUL à faire la conversion : deux exercices qui tombent la même année civile (un
changement de date de clôture) donneraient deux fois le même id `FY####` — un refus nommé, jamais une
collision silencieuse qui écraserait l'un des deux dans `cellules_attendues`.

Pur, sans IO : l'horizon de projection est lu par l'appelant (`parametres_du_fonds.horizon_de_projection`,
§7 de la spec) et passé en paramètre.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

__all__ = ["PeriodesInvalides", "PeriodesDuClasseur", "periode_du_classeur", "periodes_du_classeur"]


class PeriodesInvalides(Exception):
    """Deux exercices du socle retombent sur le même id `FY####` — un changement de date de clôture
    qui écraserait silencieusement l'un des deux. Refus nommé, jamais une collision tue."""


@dataclass(frozen=True)
class PeriodesDuClasseur:
    historiques: tuple[str, ...]   # les exercices du socle, dans l'ordre croissant
    projetees: tuple[str, ...]     # les `horizon` exercices qui suivent le dernier historique


def periode_du_classeur(fin: date) -> str:
    """L'id `FY####` d'un exercice qui se clôt le `fin`.

    Un exercice de 52/53 semaines (calendrier fiscal US, comme NVDA : fin fin-janvier) qui tombe les
    PREMIERS JOURS de janvier appartient encore, en substance, à l'année qui s'achève — c'est
    l'exercice « FY2026 » de NVDA qui se clôt le 2026-01-25, pas un exercice « FY2025 » qui finirait
    la veille du nouvel an par un décalage d'une poignée de jours. On recule donc de sept jours avant
    de lire l'année : un 1ᵉʳ janvier recule sur l'année précédente (correct : la clôture EST de
    l'exercice qui s'achève), et aucune clôture usuelle (toujours à au moins huit jours du 1ᵉʳ
    janvier côté fin d'année civile, ou bien en plein milieu de l'année) ne change d'année par ce
    recul — sauf précisément le cas qu'il corrige.
    """
    return f"FY{(fin - timedelta(days=7)).year}"


def periodes_du_classeur(structure_du_socle: dict[str, Any], horizon: int) -> PeriodesDuClasseur:
    """Les périodes du classeur : les exercices du socle (historiques), convertis par
    `periode_du_classeur`, et les `horizon` exercices qui suivent (projetées) — les SEULES périodes
    admises dans `cellules_attendues` (§3.3 point 4 de la spec)."""
    if horizon < 1:
        raise PeriodesInvalides(f"horizon de projection invalide : {horizon} (doit être ≥ 1)")

    periodes_socle = structure_du_socle.get("periodes") or []
    exercices = [
        p for p in periodes_socle
        if p.get("cadrage") == "flux" and p.get("nature") == "exercice" and p.get("fin")
    ]
    exercices = sorted(exercices, key=lambda p: p["fin"])

    vus: dict[str, str] = {}
    historiques: list[str] = []
    for p in exercices:
        fin = date.fromisoformat(p["fin"])
        fy = periode_du_classeur(fin)
        if fy in vus and vus[fy] != p["fin"]:
            raise PeriodesInvalides(
                f"deux exercices du socle retombent sur `{fy}` : clôtures {vus[fy]} et {p['fin']} — "
                "un changement de date de clôture ne doit jamais écraser un exercice sous le nom "
                "d'un autre")
        vus[fy] = p["fin"]
        if fy not in historiques:
            historiques.append(fy)

    derniere_annee = int(historiques[-1][2:]) if historiques else date.today().year
    projetees = tuple(f"FY{derniere_annee + i}" for i in range(1, horizon + 1))

    return PeriodesDuClasseur(historiques=tuple(historiques), projetees=projetees)
