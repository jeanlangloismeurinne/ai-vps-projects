"""Le rangement en base des fiches et du journal des sources (tables de la migration 063).

Seul fichier du système à nommer ces deux tables. Il reçoit une connexion qu'il ne possède pas :
l'appelant tient la transaction. Les deux tables sont en ajout seul ; la clé unique de chacune fait
de deux écritures concurrentes une écriture et un refus, jamais un écrasement.

Le JSON voyage en TEXTE (`::text::jsonb` à l'écriture, `::text` à la lecture) : ce dépôt rend le
même résultat que la connexion ait ou non un codec JSON installé.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .contrat import EcritureConcurrente


def _est_un_doublon(exc: Exception) -> bool:
    """Violation d'unicité (code SQL 23505), reconnue sans importer le pilote de la base."""
    return getattr(exc, "sqlstate", None) == "23505"


class DepotBase:
    def __init__(self, connexion: Any) -> None:
        self._c = connexion

    async def emetteurs(self) -> Sequence[str]:
        lignes = await self._c.fetch("SELECT DISTINCT emetteur FROM emetteurs_fiches ORDER BY emetteur")
        return [l["emetteur"] for l in lignes]

    async def fiches(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM emetteurs_fiches WHERE emetteur = $1 ORDER BY revision",
            emetteur)
        return [json.loads(l["contenu"]) for l in lignes]

    async def ajouter_fiche(self, emetteur: str, revision: int, contenu: Mapping[str, Any]) -> None:
        try:
            await self._c.execute(
                "INSERT INTO emetteurs_fiches (emetteur, revision, contenu) VALUES ($1, $2, $3::text::jsonb)",
                emetteur, revision, json.dumps(dict(contenu), ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001 — seul le doublon est requalifié, le reste remonte
            if _est_un_doublon(exc):
                raise EcritureConcurrente(
                    f"fiche {emetteur} : la révision {revision} existe déjà") from exc
            raise

    async def actes(self) -> Sequence[Mapping[str, Any]]:
        lignes = await self._c.fetch(
            "SELECT rang, acte, source, portee, natures::text AS natures, niveau, critere, auteur, "
            "motif, le::text AS le, evaluation::text AS evaluation FROM emetteurs_sources_actes ORDER BY rang")
        return [{**dict(l), "natures": json.loads(l["natures"]), "evaluation": json.loads(l["evaluation"])}
                for l in lignes]

    async def ajouter_acte(self, rang: int, acte: Mapping[str, Any]) -> None:
        try:
            await self._c.execute(
                "INSERT INTO emetteurs_sources_actes "
                "(rang, acte, source, portee, natures, niveau, critere, auteur, motif, le, evaluation) "
                "VALUES ($1, $2, $3, $4, $5::text::jsonb, $6, $7, $8, $9, $10::text::date, $11::text::jsonb)",
                rang, acte["acte"], acte["source"], acte["portee"],
                json.dumps(list(acte["natures"])), acte["niveau"], acte["critere"], acte["auteur"],
                acte["motif"], acte["le"], json.dumps(dict(acte.get("evaluation") or {}), ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            if _est_un_doublon(exc):
                raise EcritureConcurrente(f"journal des sources : le rang {rang} existe déjà") from exc
            raise
