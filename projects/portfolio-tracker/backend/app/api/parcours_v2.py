"""Le PARCOURS DU COMITÉ — les trois niveaux de drill-down (chantier v3, lot 6 maillon 2, spec §8.1).

  GET /v2/tickers/{ticker_id}/dossier                                   NIVEAU 1 — peut-on décider ?
  GET /v2/tickers/{ticker_id}/frameworks/{framework_id}                 NIVEAU 2 — une méthodologie
  GET /v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id} NIVEAU 3 — la preuve

Aucune règle ici : tout est dressé par `agents/v2/parcours.py` (détenteur unique), recalculé à la
lecture, et RIEN n'est écrit — ni avis, ni mandat, ni note (#53/#54/#77). Un GET qui servirait une
ligne stockée servirait le verdict d'avant le dernier fait important publié.

Un framework ou une question inconnus rendent 404, jamais un niveau vide : un écran vide se lirait
« rien au dossier ». Un titre inconnu aussi — un dossier vide pour un titre qui n'existe pas se lirait
« aucune question applicable ».
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.v2.parcours import (
    ReferenceInconnue, charger_etat_dossier, dresser_niveau1, dresser_niveau2, dresser_niveau3)
from app.agents.v2.projection_memo import AnswerLue, projeter_memo
from app.contracts.parcours_schema import DossierTitre, FrameworkDuDossier, PreuvesQuestion
from app.db.database import get_db_session

router = APIRouter(tags=["parcours-v2"])


async def _etat(ticker_id: str):
    async with get_db_session() as conn:
        existe = await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id)
        if not existe:
            raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")
        return await charger_etat_dossier(conn, ticker_id)


@router.get("/v2/tickers/{ticker_id}/dossier", response_model=DossierTitre)
async def dossier_niveau1(ticker_id: str) -> DossierTitre:
    etat = await _etat(ticker_id)
    memo = projeter_memo(
        ticker_id=ticker_id, archetype=etat.archetype, fichier=etat.fichier,
        lues=[AnswerLue(answer_id=r.answer_id, answer=r.servie) for r in etat.reponses])
    return dresser_niveau1(etat, memo)


@router.get("/v2/tickers/{ticker_id}/frameworks/{framework_id}", response_model=FrameworkDuDossier)
async def dossier_niveau2(ticker_id: str, framework_id: str) -> FrameworkDuDossier:
    etat = await _etat(ticker_id)
    try:
        return dresser_niveau2(etat, framework_id)
    except ReferenceInconnue as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}",
            response_model=PreuvesQuestion)
async def dossier_niveau3(ticker_id: str, framework_id: str, question_id: str) -> PreuvesQuestion:
    etat = await _etat(ticker_id)
    try:
        return dresser_niveau3(etat, framework_id, question_id)
    except ReferenceInconnue as e:
        raise HTTPException(status_code=404, detail=str(e))
