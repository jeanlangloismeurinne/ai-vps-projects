"""Le rangement en base du déclencheur (tables `etude_*` de la migration 065) et son verrou.

Seul fichier du système à nommer ces deux tables. Il reçoit une connexion qu'il ne possède pas.
Le JSON voyage en texte : même résultat avec ou sans codec JSON sur la connexion. Études et passages
sont en AJOUT SEUL (la base refuse UPDATE et DELETE).

Le verrou « un passage tient ce dossier » est un verrou consultatif de SESSION
(`pg_try_advisory_lock`) : il tient d'une connexion à l'autre, ne dépend d'aucune transaction (un
ROLLBACK ne le relâche pas, `rendre` si), et la base le relâche d'elle-même si la connexion meurt —
un passage tué ne laisse jamais un dossier bloqué. Une même session peut reprendre un verrou qu'elle
tient déjà : le dépôt garde donc ce qu'il tient et refuse de le reprendre, comme le `DepotMemoire`.
Deux dossiers dont les noms se hachent pareil se gênent : le second attend le passage suivant (il
n'avance pas moins, il avance plus tard).
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

_ESPACE = "etude_dossier"     # l'espace de noms du verrou (première clé)


class DepotBase:
    def __init__(self, connexion: Any) -> None:
        self._c = connexion
        self._tenus: set[str] = set()

    async def etudes(self) -> Sequence[Mapping[str, Any]]:
        """Triées par dossier, octet par octet (`COLLATE "C"`) : l'ordre de Python, pas celui de la
        langue de la base."""
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM etude_etudes ORDER BY dossier COLLATE \"C\"")
        return [json.loads(l["contenu"]) for l in lignes]

    async def etude(self, dossier: str) -> Mapping[str, Any] | None:
        texte = await self._c.fetchval("SELECT contenu::text FROM etude_etudes WHERE dossier = $1", dossier)
        return None if texte is None else json.loads(texte)

    async def ajouter_etude(self, etude: Mapping[str, Any]) -> bool:
        e = dict(etude)
        ecrit = await self._c.fetchval(
            "INSERT INTO etude_etudes (dossier, contenu) VALUES ($1, $2::text::jsonb) "
            "ON CONFLICT (dossier) DO NOTHING RETURNING dossier",
            e["dossier"], json.dumps(e, ensure_ascii=False))
        return ecrit is not None

    async def noter_passage(self, passage: Mapping[str, Any]) -> None:
        p = dict(passage)
        await self._c.execute(
            "INSERT INTO etude_passages (dossier, contenu) VALUES ($1, $2::text::jsonb)",
            p["dossier"], json.dumps(p, ensure_ascii=False))

    async def passages(self, dossier: str) -> Sequence[Mapping[str, Any]]:
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM etude_passages WHERE dossier = $1 ORDER BY rang", dossier)
        return [json.loads(l["contenu"]) for l in lignes]

    async def prendre(self, dossier: str) -> bool:
        if dossier in self._tenus:
            return False
        pris = await self._c.fetchval(
            "SELECT pg_try_advisory_lock(hashtext($1), hashtext($2))", _ESPACE, dossier)
        if pris:
            self._tenus.add(dossier)
        return bool(pris)

    async def rendre(self, dossier: str) -> None:
        if dossier not in self._tenus:
            return
        self._tenus.discard(dossier)
        await self._c.fetchval("SELECT pg_advisory_unlock(hashtext($1), hashtext($2))", _ESPACE, dossier)
