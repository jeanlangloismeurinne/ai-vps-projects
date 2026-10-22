"""L'ARCHITECTURE DU CLASSEUR vue du comité (lot M3, roadmap V3 `12-lot-M3-architecte.md` §6.3).
Calqué sur `valorisation_v2.py` (#46), monté comme lui.

  GET  /v2/tickers/{ticker_id}/architecture                        la signée, la version en attente,
                                                                     ce qui est EN VIGUEUR
  POST /v2/tickers/{ticker_id}/architecture/v/{version}/signer     le comité SIGNE la version en attente
  POST /v2/tickers/{ticker_id}/architecture/v/{version}/ecarter    le comité l'ÉCARTE, motif écrit

Aucune règle ici : tout passe par `modele_entreprise/signature.py` (détenteur unique des registres
et de ce qui est servi), rejoué contre la MATIÈRE DU JOUR (#53) — jamais un verdict stocké. Pas de
POST « proposer » : c'est le geste de l'agent architecte (`tools/architecte.sh`), pas du comité.

Un refus (version déjà décidée, remplacée par une plus récente, architecture qui ne tient plus
contre la matière) est un 409 qui dit pourquoi ; une version ou un titre inconnus, un 404.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.architecture_signature_schema import ArchitectureServie, DemandeDecisionArchitecture
from app.contracts.modele_entreprise_schema import Architecture
from app.db.database import get_db_session
from app.modele_entreprise.architecte import juger_architecture
from app.modele_entreprise.matiere import MatiereRefusee, charger_matiere
from app.modele_entreprise.referentiel import load_referentiel
from app.modele_entreprise.signature import ActeRefuse, ecarter, lire_registre, servir_architecture, signer

router = APIRouter(tags=["modele-entreprise-v2"])


async def _titre_connu(conn, ticker_id: str) -> None:
    if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id):
        raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")


async def _juger_du_jour(conn, ticker_id: str):
    """Charge la matière DU JOUR (à blanc — `juger` ne publie jamais) et rend un `Juger` synchrone,
    fermé sur cette matière : `servir_architecture` est pure, elle n'ouvre aucune IO."""
    ref = load_referentiel()
    try:
        matiere = await charger_matiere(conn, ticker_id, publier=False)
    except MatiereRefusee as e:
        motif = str(e)

        def _juger_refuse(arch: Architecture) -> tuple[bool, str, tuple[str, ...]]:
            return False, f"matière indisponible : {motif}", ()
        return _juger_refuse

    def _juger(arch: Architecture) -> tuple[bool, str, tuple[str, ...]]:
        return juger_architecture(arch, ref, matiere)
    return _juger


async def _servir(conn, ticker_id: str) -> ArchitectureServie:
    versions, pv = await lire_registre(conn, ticker_id)
    ref = load_referentiel()
    juger = await _juger_du_jour(conn, ticker_id)
    return servir_architecture(ticker_id, versions, pv, juger=juger,
                               interrupteur=ref.signature_de_l_architecture)


@router.get("/v2/tickers/{ticker_id}/architecture", response_model=ArchitectureServie)
async def architecture(ticker_id: str) -> ArchitectureServie:
    async with get_db_session() as conn:
        await _titre_connu(conn, ticker_id)
        return await _servir(conn, ticker_id)


async def _decider(ticker_id: str, version: int, demande: DemandeDecisionArchitecture,
                   geste: str) -> ArchitectureServie:
    async with get_db_session() as conn:
        await _titre_connu(conn, ticker_id)
        try:
            if geste == "signer":
                juger = await _juger_du_jour(conn, ticker_id)
                await signer(conn, ticker_id=ticker_id, version=version, demande=demande, juger=juger)
            else:
                await ecarter(conn, ticker_id=ticker_id, version=version, demande=demande)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ActeRefuse as e:
            raise HTTPException(status_code=409, detail=str(e))
        return await _servir(conn, ticker_id)


@router.post("/v2/tickers/{ticker_id}/architecture/v/{version}/signer", response_model=ArchitectureServie)
async def signer_version(ticker_id: str, version: int,
                         demande: DemandeDecisionArchitecture) -> ArchitectureServie:
    return await _decider(ticker_id, version, demande, "signer")


@router.post("/v2/tickers/{ticker_id}/architecture/v/{version}/ecarter", response_model=ArchitectureServie)
async def ecarter_version(ticker_id: str, version: int,
                          demande: DemandeDecisionArchitecture) -> ArchitectureServie:
    return await _decider(ticker_id, version, demande, "ecarter")
