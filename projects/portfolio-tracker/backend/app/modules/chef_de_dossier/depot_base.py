"""Le rangement en base de l'état d'un dossier (table de la migration 063).

L'automate est synchrone et sans entrée-sortie : la base reste À SES BORDS. On charge l'état dans
un `DepotMemoire` (`ouvrir`), l'automate avance dessus, puis on range (`refermer`). Deux passages
partis de la même lecture ne s'écrasent pas : le second est refusé (`EcritureConcurrente`).

Seul fichier du système à nommer cette table. Il reçoit une connexion qu'il ne possède pas. Le
JSON voyage en texte : même résultat avec ou sans codec JSON sur la connexion.
"""
from __future__ import annotations

import json
from typing import Any

from .contrat import DepotMemoire, EcritureConcurrente


class DepotBase:
    def __init__(self, connexion: Any) -> None:
        self._c = connexion
        self._lues: dict[str, int] = {}

    async def ouvrir(self, dossier: str) -> DepotMemoire:
        """Charge l'état rangé (ou rien, pour un titre qui vient d'entrer) dans un dépôt en mémoire."""
        ligne = await self._c.fetchrow(
            "SELECT etat::text AS etat, revision FROM chef_etats WHERE dossier = $1", dossier)
        depot = DepotMemoire()
        self._lues[dossier] = 0 if ligne is None else int(ligne["revision"])
        if ligne is not None:
            depot.ranger(dossier, json.loads(ligne["etat"]))
        return depot

    async def refermer(self, dossier: str, depot: DepotMemoire) -> None:
        """Range l'état du dépôt en mémoire. Refuse si la base a bougé depuis `ouvrir`."""
        if dossier not in self._lues:
            raise EcritureConcurrente(f"dossier {dossier} : rangé sans avoir été ouvert")
        etat = depot.charger(dossier)
        if etat is None:
            return
        lue = self._lues[dossier]
        texte = json.dumps(dict(etat), ensure_ascii=False)
        if lue == 0:
            ecrit = await self._c.fetchval(
                "INSERT INTO chef_etats (dossier, etat, revision) VALUES ($1, $2::text::jsonb, 1) "
                "ON CONFLICT (dossier) DO NOTHING RETURNING revision", dossier, texte)
        else:
            ecrit = await self._c.fetchval(
                "UPDATE chef_etats SET etat = $2::text::jsonb, revision = revision + 1, range_le = now() "
                "WHERE dossier = $1 AND revision = $3 RETURNING revision", dossier, texte, lue)
        if ecrit is None:
            raise EcritureConcurrente(
                f"dossier {dossier} : un autre passage a rangé son état depuis la lecture (révision {lue})")
        self._lues[dossier] = int(ecrit)
