"""L'ATELIER DE VALORISATION vu du comité (roadmap 05 capacité 4 bis, migration 051).

  GET  /v2/tickers/{ticker_id}/valorisation                        le modèle signé, la version en attente
  POST /v2/tickers/{ticker_id}/valorisation/v/{version}/signer     le comité SIGNE la version en attente
  POST /v2/tickers/{ticker_id}/valorisation/v/{version}/ecarter    le comité l'ÉCARTE, motif écrit

Aucune règle ici : tout passe par `valorisation/signature.py` (détenteur unique des registres et de ce
qui est servi), rejoué contre le dossier DU JOUR — rien n'est lu comme un verdict stocké (#53). Les
deux POST rendent l'atelier recalculé : le comité voit tout de suite l'effet de sa décision.

Un refus (version déjà décidée, remplacée par une plus récente, modèle qui ne tient plus contre le
dossier) est un 409 qui dit pourquoi ; une version ou un titre inconnus, un 404. Il n'y a pas de POST
« proposer » : proposer est le geste de l'agent qui écrit le modèle (pas encore construit) ; un membre
du comité qui change une hypothèse proposera par le même chemin, quand l'écran existera.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.signature_modele_schema import AtelierServi, DemandeDecisionModele
from app.db.database import get_db_session
from app.valorisation.signature import (
    ActeRefuse, charger_dossier_valorisation, ecarter, lire_atelier, servir_atelier, signer)

router = APIRouter(tags=["valorisation-v2"])


async def _titre_connu(conn, ticker_id: str) -> None:
    if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id):
        raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")


async def _servir(conn, ticker_id: str) -> AtelierServi:
    versions, pv = await lire_atelier(conn, ticker_id)
    return servir_atelier(versions, pv, await charger_dossier_valorisation(conn, ticker_id))


@router.get("/v2/tickers/{ticker_id}/valorisation", response_model=AtelierServi)
async def atelier(ticker_id: str) -> AtelierServi:
    async with get_db_session() as conn:
        await _titre_connu(conn, ticker_id)
        return await _servir(conn, ticker_id)


async def _decider(ticker_id: str, version: int, demande: DemandeDecisionModele, geste: str) -> AtelierServi:
    async with get_db_session() as conn:
        await _titre_connu(conn, ticker_id)
        try:
            if geste == "signer":
                await signer(conn, ticker_id=ticker_id, version=version, demande=demande,
                             dossier=await charger_dossier_valorisation(conn, ticker_id))
            else:
                await ecarter(conn, ticker_id=ticker_id, version=version, demande=demande)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ActeRefuse as e:
            raise HTTPException(status_code=409, detail=str(e))
        return await _servir(conn, ticker_id)


@router.post("/v2/tickers/{ticker_id}/valorisation/v/{version}/signer", response_model=AtelierServi)
async def signer_version(ticker_id: str, version: int, demande: DemandeDecisionModele) -> AtelierServi:
    return await _decider(ticker_id, version, demande, "signer")


@router.post("/v2/tickers/{ticker_id}/valorisation/v/{version}/ecarter", response_model=AtelierServi)
async def ecarter_version(ticker_id: str, version: int, demande: DemandeDecisionModele) -> AtelierServi:
    return await _decider(ticker_id, version, demande, "ecarter")
