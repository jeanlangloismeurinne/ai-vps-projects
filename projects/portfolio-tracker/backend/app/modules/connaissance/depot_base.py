"""Le rangement en base de la base de connaissance (tables `connaissance_*` de la migration 065).

Seul fichier du système à nommer ces trois tables. Il reçoit une connexion qu'il ne possède pas :
l'appelant tient la transaction, comme les dépôts base de M0-M2. Le JSON voyage en TEXTE
(`::text::jsonb` à l'écriture, `::text` à la lecture) : même résultat que la connexion ait ou non un
codec JSON installé. Tout est en AJOUT SEUL (la base refuse UPDATE et DELETE) : un doublon rend
`False` et ne touche à rien, exactement comme le `DepotMemoire` du contrat.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


class DepotBase:
    def __init__(self, connexion: Any) -> None:
        self._c = connexion

    async def ranger_lecture(self, lecture: Mapping[str, Any], lignes: Sequence[str]) -> bool:
        """Range la lecture ET ses lignes. `False` sur un doublon : ni l'une ni les autres ne sont
        réécrites."""
        lec = dict(lecture)
        ecrit = await self._c.fetchval(
            "INSERT INTO connaissance_lectures (empreinte, lecteur, emetteur, fiche) "
            "VALUES ($1, $2, $3, $4::text::jsonb) "
            "ON CONFLICT (empreinte, lecteur) DO NOTHING RETURNING empreinte",
            lec["empreinte"], lec["lecteur"], lec["emetteur"], json.dumps(lec, ensure_ascii=False))
        if ecrit is None:
            return False
        await self._c.execute(
            "INSERT INTO connaissance_lignes (empreinte, lecteur, lignes) VALUES ($1, $2, $3::text[])",
            lec["empreinte"], lec["lecteur"], list(lignes))
        return True

    async def lectures(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        """Dans l'ordre de mise en lecture (`rang`), comme le dict du `DepotMemoire`."""
        lignes = await self._c.fetch(
            "SELECT fiche::text AS fiche FROM connaissance_lectures WHERE emetteur = $1 "
            "ORDER BY rang", emetteur)
        return [json.loads(l["fiche"]) for l in lignes]

    async def lignes(self, empreinte: str, lecteur: str) -> Sequence[str] | None:
        brut = await self._c.fetchval(
            "SELECT lignes FROM connaissance_lignes WHERE empreinte = $1 AND lecteur = $2", empreinte, lecteur)
        return None if brut is None else tuple(brut)

    async def ranger_piece(self, piece: Mapping[str, Any]) -> bool:
        p = dict(piece)
        ecrit = await self._c.fetchval(
            "INSERT INTO connaissance_pieces (identifiant, emetteur, empreinte, lecteur, contenu) "
            "VALUES ($1, $2, $3, $4, $5::text::jsonb) "
            "ON CONFLICT (identifiant) DO NOTHING RETURNING identifiant",
            p["identifiant"], p["emetteur"], p["empreinte"], p["lecteur"],
            json.dumps(p, ensure_ascii=False))
        return ecrit is not None

    async def pieces(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        """Dans l'ordre où elles ont été citées (`rang`), comme le dict du `DepotMemoire`."""
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM connaissance_pieces WHERE emetteur = $1 ORDER BY rang",
            emetteur)
        return [json.loads(l["contenu"]) for l in lignes]
