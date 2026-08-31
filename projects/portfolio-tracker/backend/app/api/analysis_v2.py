"""
API V2 — chaîne d'analyse (flow_version='v2', espace disjoint de la V1).

Expose le parcours curator → research → bull/bear → réfutation → synthèse (§15). Les endpoints
orchestrent les agents V2 (app/agents/v2/) ; toute la logique métier / validation de contrat vit dans
ces agents, le router ne fait que router + traduire les erreurs.

Erreurs : NotReadyError → 409 (gate §7 non franchi) ; AgentNotFoundError → 404 (agent v2 absent en
DB / migration 025) ; RuntimeError (provider/validation) → 502.
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.providers import AgentNotFoundError
from app.agents.v2 import analysis as A
from app.agents.v2 import decision as D
from app.agents.v2.analysis import NotReadyError
from app.agents.v2.curator import run_readiness
from app.agents.v2.decision import AlreadyValidated, DecisionRefused, ThesisNotFound
from app.db.database import get_db_session

router = APIRouter(tags=["analysis-v2"])
logger = logging.getLogger(__name__)


def _agent_error(e: Exception) -> HTTPException:
    if isinstance(e, NotReadyError):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, ThesisNotFound):
        return HTTPException(status_code=404, detail=str(e))
    if isinstance(e, AlreadyValidated):
        # 409 et non 400 : la requête est bien formée, c'est l'état qui l'interdit (non rejouable).
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, AgentNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    # DecisionRefused hérite de ValueError : refus MÉTIER du contrat, rendu tel quel à l'UX (400)
    # pour qu'elle affiche le motif du contrat au lieu de le reformuler.
    if isinstance(e, (DecisionRefused, ValueError)):
        return HTTPException(status_code=400, detail=str(e))
    return HTTPException(status_code=502, detail=f"Agent V2 : {e}")


# ── Curator (gate GO/NO-GO) ──────────────────────────────────────────────────
@router.post("/tickers/{ticker_id}/curator/readiness")
async def curator_readiness(ticker_id: str):
    """Recompute la readiness (MVDD 2 couvertures) + context_pack si ready. Persiste le rapport."""
    try:
        return await run_readiness(ticker_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("curator.readiness %s", ticker_id)
        raise _agent_error(e)


@router.get("/tickers/{ticker_id}/curator/readiness")
async def latest_readiness(ticker_id: str):
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT id, verdict, report_json, context_pack_entry_id, created_at "
            "FROM knowledge_curator_reports WHERE ticker_id=$1 AND report_type='readiness' "
            "ORDER BY created_at DESC LIMIT 1",
            ticker_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Aucune readiness pour ce ticker.")
    return dict(row)


# ── Research (base neutre) ───────────────────────────────────────────────────
@router.post("/tickers/{ticker_id}/research")
async def create_research(ticker_id: str):
    try:
        return await A.run_research(ticker_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("research %s", ticker_id)
        raise _agent_error(e)


@router.get("/tickers/{ticker_id}/research")
async def list_research(ticker_id: str):
    async with get_db_session() as conn:
        rows = await conn.fetch(
            "SELECT id, status, cost_usd, created_at FROM research_memos "
            "WHERE ticker_id=$1 ORDER BY created_at DESC",
            ticker_id,
        )
    return [dict(r) for r in rows]


@router.get("/research/{memo_id}")
async def get_research(memo_id: int):
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM research_memos WHERE id=$1", memo_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Memo introuvable.")
    return dict(row)


# ── Analyses bull / bear / réfutation / synthèse ─────────────────────────────
class CaseBody(BaseModel):
    type: Literal["bull", "bear"]
    research_memo_id: int


@router.post("/tickers/{ticker_id}/analyses")
async def create_case(ticker_id: str, body: CaseBody):
    fn = A.run_bull if body.type == "bull" else A.run_bear
    try:
        return await fn(ticker_id, body.research_memo_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("analysis %s %s", body.type, ticker_id)
        raise _agent_error(e)


class RebuttalBody(BaseModel):
    bull_analysis_id: int
    bear_analysis_id: int


@router.post("/tickers/{ticker_id}/analyses/rebuttal")
async def create_rebuttal(ticker_id: str, body: RebuttalBody):
    try:
        return await A.run_rebuttal(ticker_id, body.bull_analysis_id, body.bear_analysis_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("rebuttal %s", ticker_id)
        raise _agent_error(e)


class SynthesisBody(BaseModel):
    bull_analysis_id: int
    bear_analysis_id: int
    research_memo_id: int


@router.post("/tickers/{ticker_id}/analyses/synthesis")
async def create_synthesis(ticker_id: str, body: SynthesisBody):
    try:
        return await A.run_synthesis(
            ticker_id, body.bull_analysis_id, body.bear_analysis_id, body.research_memo_id
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("synthesis %s", ticker_id)
        raise _agent_error(e)


@router.get("/tickers/{ticker_id}/analyses")
async def list_analyses(ticker_id: str, analysis_type: Optional[str] = None):
    async with get_db_session() as conn:
        if analysis_type:
            rows = await conn.fetch(
                "SELECT id, analysis_type, round, status, cost_usd, created_at FROM investment_analyses "
                "WHERE ticker_id=$1 AND analysis_type=$2 ORDER BY created_at DESC",
                ticker_id, analysis_type,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, analysis_type, round, status, cost_usd, created_at FROM investment_analyses "
                "WHERE ticker_id=$1 ORDER BY created_at DESC",
                ticker_id,
            )
    return [dict(r) for r in rows]


# ── Décision & validation de thèse (§9, lot 7) ───────────────────────────────
# Route PRÉFIXÉE /v2 : `POST /theses/{id}/validate` existe déjà côté V1 (api/thesis_v2.py — où « v2 »
# désigne la 2ᵉ version du fichier V1, pas le flux V2) avec un corps dépourvu des garde-fous G2.
class DraftThesisBody(BaseModel):
    research_memo_id: int
    synthesis_analysis_id: int


@router.post("/v2/tickers/{ticker_id}/theses")
async def create_thesis_v2(ticker_id: str, body: DraftThesisBody):
    """Ouvre une thèse V2 en `draft` sur une synthèse — l'objet que le validate acquittera."""
    try:
        return await D.create_thesis_draft(ticker_id, body.research_memo_id, body.synthesis_analysis_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("thesis draft v2 %s", ticker_id)
        raise _agent_error(e)


class RiskAckBody(BaseModel):
    risk_index: int
    accepted: bool


class ValidateV2Body(BaseModel):
    """Ce que l'UTILISATEUR fournit — et rien de plus (G2).

    Ni la synthèse, ni le sizing, ni les conditions d'entrée : ils sont lus en base depuis l'analyse.
    Un sizing autre que le recommandé se trace en amont dans la synthèse (override A7), pas ici.
    `risk_matrix_acked` n'est pas demandé : la bijection des acquittements en tient lieu.
    """
    risk_acks: list[RiskAckBody]
    pre_mortem_acked: bool
    shares: float
    purchase_price: float        # en EUR (cash réellement débité)
    purchase_date: str           # ISO 'YYYY-MM-DD'


@router.post("/v2/theses/{thesis_id}/validate")
async def validate_thesis_v2(thesis_id: int, body: ValidateV2Body):
    """Fige la décision (contrat ThesisValidation) puis exécute l'entrée en position, atomiquement."""
    try:
        return await D.validate_thesis(
            thesis_id,
            risk_acks=[a.model_dump() for a in body.risk_acks],
            pre_mortem_acked=body.pre_mortem_acked,
            shares=body.shares,
            purchase_price=body.purchase_price,
            purchase_date=body.purchase_date,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("validate thesis v2 #%s", thesis_id)
        raise _agent_error(e)


@router.get("/v2/theses/{thesis_id}")
async def get_thesis_v2(thesis_id: int):
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id=$1", thesis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Thèse V2 introuvable.")
    return dict(row)


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: int):
    """Analyse + ses refs figées (snapshot A1/A2, auditabilité)."""
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM investment_analyses WHERE id=$1", analysis_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Analyse introuvable.")
        refs = await conn.fetch(
            "SELECT entry_id, entry_version, reliability_at_use, field_path, content_snapshot "
            "FROM analysis_knowledge_refs WHERE analysis_id=$1 AND analysis_kind='analysis' "
            "ORDER BY entry_id",
            analysis_id,
        )
    out = dict(row)
    out["knowledge_refs"] = [dict(r) for r in refs]
    return out
