"""LA FICHE DE L'ÉMETTEUR ET LES SOURCES vues de l'écran (module « Fiche de l'émetteur et sources »,
`roadmap/V3/M1-fiche-emetteur.md`, ligne d'acceptation A13).

  GET  /v2/emetteurs                                  la liste des émetteurs, le journal des sources,
                                                      le référentiel (natures, niveaux, critères écrits)
  GET  /v2/emetteurs/{emetteur}                       la fiche, ses révisions, ses sources ; 404 sans fiche
  PUT  /v2/emetteurs/{emetteur}                       établit la fiche ou la corrige (une révision de plus)
  POST /v2/sources/admettre                           admet une source pour des natures d'information
  POST /v2/sources/revoquer                           révoque une source admise
  GET  /v2/emetteurs/{emetteur}/qualification         cette adresse vaut-elle quelque chose, pour cette nature ?
  GET  /v2/emetteurs/{emetteur}/dossier               où en est le dossier chez le chef de dossier (lecture seule)

Aucune règle ici : tout passe par le `contrat` du module (seule surface importable). Les corps
n'acceptent NI auteur NI date (`extra="forbid"`) : l'auteur est toujours l'utilisateur, la date celle du
serveur — ce qui est signé ne se déclare pas dans le corps. Toute écriture est dans une transaction
explicite (`get_db_session` n'en ouvre aucune, convention #35).

Un refus du registre (règle enfreinte, rang déjà pris) est un 409 qui dit pourquoi ; un émetteur sans
fiche, un 404 ; une nature d'information inconnue, un 422.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.database import get_db_session
from app.modules.chef_de_dossier.contrat import depot_base as depot_chef, lire_etat
from app.modules.emetteurs import contrat

router = APIRouter(tags=["emetteurs-v2"])


class CorpsFiche(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raison_sociale: str
    motif: str
    pays: str = ""
    cotations: list[tuple[str, str]] = []
    references: list[tuple[str, str]] = []
    lieux: list[tuple[str, str]] = []
    specialite: str = ""


class CorpsAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    portee: str
    natures: list[str]
    niveau: str
    motif: str
    critere: str = ""


class CorpsRevocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    portee: str
    motif: str


def _aujourdhui() -> str:
    return date.today().isoformat()


def _refus(e: Exception) -> HTTPException:
    return HTTPException(status_code=409, detail=str(e))


@router.get("/v2/emetteurs")
async def liste_emetteurs() -> dict:
    async with get_db_session() as conn:
        return await contrat.vue_ecran(contrat.depot_base(conn))


@router.get("/v2/emetteurs/{emetteur}")
async def fiche_emetteur(emetteur: str) -> dict:
    async with get_db_session() as conn:
        try:
            return await contrat.vue_ecran(contrat.depot_base(conn), emetteur)
        except contrat.FicheAbsente:
            raise HTTPException(status_code=404, detail=f"Aucune fiche n'existe pour `{emetteur}`.")


@router.put("/v2/emetteurs/{emetteur}")
async def etablir_fiche(emetteur: str, corps: CorpsFiche) -> dict:
    async with get_db_session() as conn:
        depot = contrat.depot_base(conn)
        try:
            async with conn.transaction():
                await contrat.etablir_fiche(
                    depot, emetteur, raison_sociale=corps.raison_sociale, auteur=contrat.UTILISATEUR,
                    motif=corps.motif, le=_aujourdhui(), pays=corps.pays, cotations=corps.cotations,
                    references=corps.references, lieux=corps.lieux, specialite=corps.specialite)
        except (contrat.ActeRefuse, contrat.EcritureConcurrente) as e:
            raise _refus(e)
        return await contrat.vue_ecran(depot, emetteur)


@router.post("/v2/sources/admettre")
async def admettre_source(corps: CorpsAdmission) -> dict:
    async with get_db_session() as conn:
        try:
            async with conn.transaction():
                rang = await contrat.admettre_source(
                    contrat.depot_base(conn), source=corps.source, portee=corps.portee,
                    natures=corps.natures, niveau=corps.niveau, auteur=contrat.UTILISATEUR,
                    motif=corps.motif, le=_aujourdhui(), critere=corps.critere)
        except (contrat.ActeRefuse, contrat.EcritureConcurrente) as e:
            raise _refus(e)
        return {"rang": rang}


@router.post("/v2/sources/revoquer")
async def revoquer_source(corps: CorpsRevocation) -> dict:
    async with get_db_session() as conn:
        try:
            async with conn.transaction():
                rang = await contrat.revoquer_source(
                    contrat.depot_base(conn), source=corps.source, portee=corps.portee,
                    auteur=contrat.UTILISATEUR, motif=corps.motif, le=_aujourdhui())
        except (contrat.ActeRefuse, contrat.EcritureConcurrente) as e:
            raise _refus(e)
        return {"rang": rang}


@router.get("/v2/emetteurs/{emetteur}/qualification")
async def qualification(emetteur: str, adresse: str, nature: str) -> dict:
    async with get_db_session() as conn:
        try:
            fiche = await contrat.lire_fiche(contrat.depot_base(conn), emetteur)
        except contrat.FicheAbsente:
            raise HTTPException(status_code=404, detail=f"Aucune fiche n'existe pour `{emetteur}`.")
    try:
        return asdict(contrat.qualifier(fiche, adresse, nature))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/v2/emetteurs/{emetteur}/dossier")
async def dossier_emetteur(emetteur: str) -> dict:
    async with get_db_session() as conn:
        d = await depot_chef(conn).ouvrir(emetteur)
        return lire_etat(d, emetteur).vers_dict()
