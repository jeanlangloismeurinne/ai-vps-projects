"""Le rangement en base de la collecte (tables de la migration 064).

Seul fichier du système à nommer ces cinq tables. Il reçoit une connexion qu'il ne possède pas :
l'appelant tient la transaction (`async with conn.transaction():`), comme les dépôts base de
M1/M0. Le JSON voyage en TEXTE (`::text::jsonb` à l'écriture, `::text` à la lecture) : ce dépôt
rend le même résultat que la connexion ait ou non un codec JSON installé.

Trois registres en AJOUT SEUL (`recueil_documents`, `recueil_contenus`, `recueil_reponses`) — la
base elle-même refuse UPDATE/DELETE (trigger de la migration 064) ; deux états modifiables
(`recueil_travaux`, `recueil_sources_rencontrees`) qui reproduisent EXACTEMENT la sémantique du
`DepotMemoire` du contrat : `noter_source_rencontree` ne fusionne que les adresses (dédupliquées,
anciennes d'abord), jamais le reste de l'état ; `marquer_source` fusionne les champs donnés sur
l'état existant.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


class DepotBase:
    def __init__(self, connexion: Any) -> None:
        self._c = connexion

    # ── Les documents et leur contenu (AJOUT SEUL) ──────────────────────────────────────────

    async def document(self, empreinte: str) -> Mapping[str, Any] | None:
        ligne = await self._c.fetchrow(
            "SELECT fiche::text AS fiche FROM recueil_documents WHERE empreinte = $1", empreinte)
        return None if ligne is None else json.loads(ligne["fiche"])

    async def contenu(self, empreinte: str) -> bytes | None:
        brut = await self._c.fetchval(
            "SELECT contenu FROM recueil_contenus WHERE empreinte = $1", empreinte)
        return None if brut is None else bytes(brut)

    async def ranger_document(self, fiche_document: Mapping[str, Any], contenu: bytes) -> bool:
        """Range le document ET son contenu dans la même écriture logique. `False` sur un
        doublon (`ON CONFLICT ... DO NOTHING`) : un document rangé ne se réécrit jamais, et son
        contenu n'est alors pas touché non plus."""
        fiche = dict(fiche_document)
        empreinte = fiche["empreinte"]
        provenance = fiche.get("provenance") or {}
        ecrit = await self._c.fetchval(
            "INSERT INTO recueil_documents (empreinte, emetteur, adaptateur, identifiant, partie, fiche) "
            "VALUES ($1, $2, $3, $4, $5, $6::text::jsonb) "
            "ON CONFLICT (empreinte) DO NOTHING RETURNING empreinte",
            empreinte, fiche["emetteur"], provenance.get("adaptateur", ""),
            provenance.get("identifiant", "") or "", provenance.get("partie", "") or "",
            json.dumps(fiche, ensure_ascii=False))
        if ecrit is None:
            return False            # déjà rangé : ni le document ni son contenu ne sont réécrits
        await self._c.execute(
            "INSERT INTO recueil_contenus (empreinte, contenu) VALUES ($1, $2)", empreinte, bytes(contenu))
        return True

    async def parties_rangees(self, emetteur: str, adaptateur: str, identifiant: str) -> Mapping[str, str]:
        if not identifiant:
            return {}
        lignes = await self._c.fetch(
            "SELECT partie, empreinte FROM recueil_documents "
            "WHERE emetteur = $1 AND adaptateur = $2 AND identifiant = $3",
            emetteur, adaptateur, identifiant)
        return {l["partie"]: l["empreinte"] for l in lignes}

    # ── Les réponses (AJOUT SEUL ; `rang` = ordre d'ajout) ──────────────────────────────────

    async def ajouter_reponse(self, reponse: Mapping[str, Any]) -> None:
        rep = dict(reponse)
        await self._c.execute(
            "INSERT INTO recueil_reponses (emetteur, contenu) VALUES ($1, $2::text::jsonb)",
            rep["demande"]["emetteur"], json.dumps(rep, ensure_ascii=False))

    async def reponses(self, emetteur: str) -> Sequence[Mapping[str, Any]]:
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM recueil_reponses WHERE emetteur = $1 ORDER BY rang",
            emetteur)
        return [json.loads(l["contenu"]) for l in lignes]

    # ── Le travail en cours (ÉTAT : `ecrire_travail` REMPLACE) ──────────────────────────────

    async def travaux(self, emetteur: str | None = None) -> Sequence[Mapping[str, Any]]:
        """Ordonné par `rang` (première écriture) — comme l'ordre d'insertion du dict Python du
        `DepotMemoire` : un remplacement (`ecrire_travail`) ne déplace jamais une ligne."""
        if emetteur is None:
            lignes = await self._c.fetch(
                "SELECT contenu::text AS contenu FROM recueil_travaux ORDER BY rang")
        else:
            lignes = await self._c.fetch(
                "SELECT contenu::text AS contenu FROM recueil_travaux WHERE emetteur = $1 ORDER BY rang",
                emetteur)
        return [json.loads(l["contenu"]) for l in lignes]

    async def ecrire_travail(self, travail: Mapping[str, Any]) -> None:
        t = dict(travail)
        await self._c.execute(
            "INSERT INTO recueil_travaux (cle, emetteur, contenu) VALUES ($1, $2, $3::text::jsonb) "
            "ON CONFLICT (cle) DO UPDATE SET contenu = EXCLUDED.contenu, range_le = now()",
            t["cle"], t["demande"]["emetteur"], json.dumps(t, ensure_ascii=False))

    # ── Les sources inconnues rencontrées (ÉTAT : fusion) ───────────────────────────────────

    async def sources_rencontrees(self) -> Sequence[Mapping[str, Any]]:
        """Ordonné par `rang` (première rencontre) — comme l'ordre d'insertion du dict Python du
        `DepotMemoire` : une fusion (`noter_source_rencontree`, `marquer_source`) ne déplace
        jamais une ligne."""
        lignes = await self._c.fetch(
            "SELECT contenu::text AS contenu FROM recueil_sources_rencontrees ORDER BY rang")
        return [json.loads(l["contenu"]) for l in lignes]

    async def noter_source_rencontree(self, ligne: Mapping[str, Any]) -> None:
        """Une source déjà notée GARDE son état : seules ses adresses s'ajoutent, dédupliquées
        dans l'ordre (les anciennes d'abord) — exactement `DepotMemoire.noter_source_rencontree`."""
        neuve = dict(ligne)
        source = neuve["source"]
        anc_texte = await self._c.fetchval(
            "SELECT contenu::text FROM recueil_sources_rencontrees WHERE source = $1 FOR UPDATE", source)
        if anc_texte is None:
            await self._c.execute(
                "INSERT INTO recueil_sources_rencontrees (source, emetteur, contenu) "
                "VALUES ($1, $2, $3::text::jsonb)",
                source, neuve["emetteur"], json.dumps(neuve, ensure_ascii=False))
            return
        anc = json.loads(anc_texte)
        vues = list(dict.fromkeys(list(anc["adresses"]) + list(neuve["adresses"])))
        fusionne = {**anc, "adresses": vues}
        await self._c.execute(
            "UPDATE recueil_sources_rencontrees SET contenu = $2::text::jsonb WHERE source = $1",
            source, json.dumps(fusionne, ensure_ascii=False))

    async def marquer_source(self, source: str, champs: Mapping[str, Any]) -> None:
        """Fusionne `champs` sur l'état existant — exactement `DepotMemoire.marquer_source`."""
        anc_texte = await self._c.fetchval(
            "SELECT contenu::text FROM recueil_sources_rencontrees WHERE source = $1 FOR UPDATE", source)
        if anc_texte is None:
            raise KeyError(f"source jamais rencontrée : {source}")
        fusionne = {**json.loads(anc_texte), **dict(champs)}
        await self._c.execute(
            "UPDATE recueil_sources_rencontrees SET contenu = $2::text::jsonb WHERE source = $1",
            source, json.dumps(fusionne, ensure_ascii=False))
