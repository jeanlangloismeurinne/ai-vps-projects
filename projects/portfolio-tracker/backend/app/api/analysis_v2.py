"""
API V2 — chaîne d'analyse (flow_version='v2', espace disjoint de la V1).

Expose le parcours curator → research → bull/bear → réfutation → synthèse (§15). Les endpoints
orchestrent les agents V2 (app/agents/v2/) ; toute la logique métier / validation de contrat vit dans
ces agents, le router ne fait que router + traduire les erreurs.

Erreurs : NotReadyError → 409 (gate §7 non franchi) ; AgentNotFoundError → 404 (agent v2 absent en
DB / migration 025) ; RuntimeError (provider/validation) → 502.

Lot 9 (sortie / calibration / débat, migration 032) : un refus de PONT — sortie sans antécédent,
post-mortem qui n'épuise pas les hypothèses figées, résolution incompatible avec les seuils figés —
part en **422** comme les refus du monitoring : la requête est valide, c'est la sortie du modèle qui
ne l'est pas. Un état qui interdit l'acte (thèse sans verdict de sortie, tranche déjà exécutée, ordre
hors séquence) part en **409**.
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
from app.agents.v2.debate import (
    DebateNotFound,
    DebateRefused,
    ThesisNotDebatable,
    close_debate,
    run_debate,
)
from app.agents.v2.decision import AlreadyValidated, DecisionRefused, ThesisNotFound
from app.agents.v2.exit import (
    ExitPlanNotFound,
    ExitRefused,
    ThesisNotExitable,
    TrancheConflict,
    calibration_summary,
    create_exit_alert,
    execute_tranche,
    run_exit_agent,
)
from app.agents.v2.monitoring import MonitoringRefused, ThesisNotActive, run_monitoring
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
    if isinstance(e, ThesisNotActive):
        return HTTPException(status_code=409, detail=str(e))
    # Lot 9 — l'état de la thèse interdit l'acte (pas de verdict de sortie, position déjà soldée,
    # post-mortem avant la sortie…) : 409, comme ThesisNotActive.
    if isinstance(e, (ThesisNotExitable, ThesisNotDebatable, TrancheConflict)):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, (ExitPlanNotFound, DebateNotFound)):
        return HTTPException(status_code=404, detail=str(e))
    # 422 et non 400 : la requête est valide, c'est la SORTIE DU MODÈLE qui est incohérente avec la
    # thèse figée (hypothèse inventée, revue incomplète). Rien à corriger côté client — on relance.
    # ExitRefused/DebateRefused doivent passer AVANT le ValueError générique dont ils héritent.
    if isinstance(e, (MonitoringRefused, ExitRefused, DebateRefused)):
        return HTTPException(status_code=422, detail=str(e))
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


@router.get("/v2/theses")
async def list_theses_v2(ticker_id: Optional[str] = None):
    """Listing des thèses V2 avec agrégats (position, monitoring, exit_plan, post_mortem).

    Paramètre optionnel `?ticker_id=` pour filtrer sur un ticker.
    Tri par id DESC (thèse la plus récente en tête).

    `valuation_range_figee` est la fourchette telle qu'elle a été figée au validate
    (lue depuis `validation_json->'valuation_range'`) — elle peut différer de `valuation_range`
    (colonne réactualisée par les revues annuelles). C'est ce champ que la calibration A5 doit relire.
    """
    where = "WHERE t.ticker_id = $1" if ticker_id else ""
    params = [ticker_id] if ticker_id else []
    sql = f"""
        SELECT
            t.id,
            t.ticker_id,
            tk.ticker_symbol,
            t.status,
            t.verdict,
            t.position_sizing_pct,
            t.valuation_range,
            t.validation_json -> 'valuation_range' AS valuation_range_figee,
            t.validated_at,
            t.created_at,
            -- nb_hypotheses : longueur du tableau JSONB ou 0 si null
            CASE WHEN t.hypotheses IS NULL THEN 0
                 ELSE jsonb_array_length(t.hypotheses)
            END AS nb_hypotheses,
            -- hypotheses_par_statut : {statut: count}
            (
                SELECT jsonb_object_agg(statut, cnt)
                FROM (
                    SELECT h->>'statut' AS statut, count(*) AS cnt
                    FROM jsonb_array_elements(COALESCE(t.hypotheses, '[]'::jsonb)) h
                    GROUP BY h->>'statut'
                ) sub
            ) AS hypotheses_par_statut,
            -- position V2 (au plus une, discriminant thesis_v2_id)
            (
                SELECT jsonb_build_object(
                    'id', pp.id,
                    'shares', pp.shares,
                    'purchase_price_eur', pp.purchase_price_eur,
                    'purchase_date', pp.purchase_date,
                    'status', pp.status
                )
                FROM portfolio_positions pp
                WHERE pp.thesis_v2_id = t.id
                LIMIT 1
            ) AS position,
            -- nb de sessions de monitoring
            (
                SELECT count(*)
                FROM monitoring_sessions_v2 ms
                WHERE ms.thesis_v2_id = t.id
            ) AS nb_monitoring_sessions,
            -- dernière session
            (
                SELECT jsonb_build_object(
                    'id', ms.id,
                    'mode', ms.mode,
                    'status', ms.status,
                    'alert_level', ms.alert_level,
                    'verdict', ms.verdict,
                    'created_at', ms.created_at
                )
                FROM monitoring_sessions_v2 ms
                WHERE ms.thesis_v2_id = t.id
                ORDER BY ms.created_at DESC
                LIMIT 1
            ) AS derniere_session,
            -- exit_plan actif (au plus un ouvert par garde-fou uq_exit_plan_actif)
            (
                SELECT jsonb_build_object('id', ep.id, 'exit_status', ep.exit_status)
                FROM exit_plans ep
                WHERE ep.thesis_v2_id = t.id
                  AND ep.status = 'completed'
                ORDER BY ep.created_at DESC
                LIMIT 1
            ) AS exit_plan,
            -- post_mortem_id
            (
                SELECT pm.id
                FROM post_mortems_v2 pm
                WHERE pm.thesis_v2_id = t.id
                  AND pm.status = 'completed'
                LIMIT 1
            ) AS post_mortem_id
        FROM theses_v2 t
        JOIN tickers tk ON tk.id = t.ticker_id
        {where}
        ORDER BY t.id DESC
    """
    async with get_db_session() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


@router.get("/v2/theses/{thesis_id}")
async def get_thesis_v2(thesis_id: int):
    """Thèse V2 complète — enrichie de façon strictement additive : ticker_symbol, position,
    exit_plan, post_mortem_id, valuation_range_figee.
    """
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM theses_v2 WHERE id=$1", thesis_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Thèse V2 introuvable.")
        out = dict(row)
        # ticker_symbol
        tk = await conn.fetchrow("SELECT ticker_symbol FROM tickers WHERE id=$1", out["ticker_id"])
        out["ticker_symbol"] = tk["ticker_symbol"] if tk else None
        # position V2
        pos = await conn.fetchrow(
            "SELECT id, shares, purchase_price_eur, purchase_date, status "
            "FROM portfolio_positions WHERE thesis_v2_id=$1 LIMIT 1",
            thesis_id,
        )
        out["position"] = dict(pos) if pos else None
        # exit_plan
        ep = await conn.fetchrow(
            "SELECT id, exit_status FROM exit_plans "
            "WHERE thesis_v2_id=$1 AND status='completed' ORDER BY created_at DESC LIMIT 1",
            thesis_id,
        )
        out["exit_plan"] = dict(ep) if ep else None
        # post_mortem_id
        pm = await conn.fetchrow(
            "SELECT id FROM post_mortems_v2 WHERE thesis_v2_id=$1 AND status='completed' LIMIT 1",
            thesis_id,
        )
        out["post_mortem_id"] = pm["id"] if pm else None
        # valuation_range_figee : lu depuis validation_json, pas depuis la colonne réactualisée
        vj = out.get("validation_json")
        out["valuation_range_figee"] = vj.get("valuation_range") if isinstance(vj, dict) else None
    return out


# ── Monitoring V2 (§10/§11, lot 8) ───────────────────────────────────────────
class MonitoringRunBody(BaseModel):
    """Ce que l'appelant peut fournir : le mode et le CONTEXTE de déclenchement — rien du jugement.

    Même règle qu'au validate (convention #36) : ni `alert_level`, ni `verdict`, ni statut
    d'hypothèse n'est acceptable en entrée. Ils sont produits par l'agent, contraints par le contrat
    du mode, puis bornés en base par les CHECKs de la migration 031.
    """
    mode: Literal[1, 2, 3, 4, 5, 6]
    trigger_label: str = ""
    calendar_event_id: Optional[int] = None
    peer_ticker: Optional[str] = None     # mode 4 : le pair dont les résultats déclenchent le pulse
    source_mode: Optional[Literal[2, 4]] = None   # mode 5 : d'où vient l'alerte à router


@router.post("/v2/theses/{thesis_id}/monitoring")
async def run_monitoring_v2(thesis_id: int, body: MonitoringRunBody):
    """Exécute une session de monitoring V2 (modes 1-6) sur une thèse ACTIVE."""
    try:
        return await run_monitoring(
            thesis_id, body.mode,
            trigger_type="manual",
            trigger_label=body.trigger_label,
            calendar_event_id=body.calendar_event_id,
            peer_ticker=body.peer_ticker,
            source_mode=body.source_mode,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("monitoring v2 mode %s thèse #%s", body.mode, thesis_id)
        raise _agent_error(e)


@router.get("/v2/theses/{thesis_id}/monitoring")
async def list_monitoring_v2(thesis_id: int):
    """Historique de suivi d'une thèse V2 — sans `context_sent`/`raw_content` (volumineux)."""
    async with get_db_session() as conn:
        rows = await conn.fetch(
            "SELECT id, mode, trigger_type, trigger_label, calendar_event_id, alert_level, verdict, "
            "routing_suggestion, status, model_used, tokens_in, tokens_out, cost_usd, "
            "created_at, completed_at FROM monitoring_sessions_v2 "
            "WHERE thesis_v2_id = $1 ORDER BY created_at DESC",
            thesis_id,
        )
    return [dict(r) for r in rows]


@router.get("/v2/monitoring/{session_id}")
async def get_monitoring_v2(session_id: int):
    """Session complète + refs figées : ce qui a été envoyé, ce qui a été rendu, sur quoi ça s'appuie."""
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM monitoring_sessions_v2 WHERE id = $1", session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Session de monitoring V2 introuvable.")
        refs = await conn.fetch(
            "SELECT entry_id, entry_version, reliability_at_use, field_path, content_snapshot "
            "FROM analysis_knowledge_refs WHERE analysis_id = $1 AND analysis_kind = 'monitoring' "
            "ORDER BY entry_id",
            session_id,
        )
    out = dict(row)
    out["knowledge_refs"] = [dict(r) for r in refs]
    return out


# ── Sortie / calibration (§11/§12/A5, lot 9) ─────────────────────────────────
# Aucun corps sur les trois POST d'agent : le mode est dans le CHEMIN, et il n'y a rien d'autre à
# fournir. Origine de sortie, hypothèses invalidées, performance réalisée, valeurs prédites — tout
# est lu en base (thèse figée, sessions, position, exécutions). Convention #36 poussée à sa limite :
# le corps le plus sûr est celui qui n'existe pas.
@router.post("/v2/theses/{thesis_id}/exit-plan")
async def create_exit_plan(thesis_id: int):
    """Produit le plan de sortie par tranches d'une thèse dont le monitoring a conclu REDUIRE/SORTIR."""
    try:
        return await run_exit_agent(thesis_id, "exit_plan")
    except Exception as e:  # noqa: BLE001
        logger.exception("exit plan thèse #%s", thesis_id)
        raise _agent_error(e)


@router.get("/v2/theses/{thesis_id}/exit-plan")
async def get_exit_plan(thesis_id: int):
    """Plan de sortie actif + ses exécutions. Le plan seul ne dit pas où en est la vente."""
    async with get_db_session() as conn:
        plan = await conn.fetchrow(
            "SELECT * FROM exit_plans WHERE thesis_v2_id = $1 AND status = 'completed' "
            "ORDER BY created_at DESC LIMIT 1",
            thesis_id,
        )
        if plan is None:
            raise HTTPException(status_code=404, detail="Aucun plan de sortie pour cette thèse V2.")
        executions = await conn.fetch(
            "SELECT * FROM exit_executions WHERE exit_plan_id = $1 ORDER BY ordre", plan["id"]
        )
        alertes = await conn.fetch(
            "SELECT id, price, direction, label, active, alert_type, triggered_at FROM price_alerts "
            "WHERE exit_plan_id = $1 ORDER BY id",
            plan["id"],
        )
    out = dict(plan)
    out["executions"] = [dict(r) for r in executions]
    out["alerts"] = [dict(r) for r in alertes]
    return out


class ExecuteTrancheBody(BaseModel):
    """Des FAITS d'exécution, jamais un jugement (#36) — même esprit que le validate.

    `pct_a_vendre` et `declencheur` ne sont pas demandés : ils appartiennent au plan figé et sont
    recopiés depuis lui. Les accepter ici permettrait de vendre une autre quantité que celle décidée
    tout en la faisant passer pour la tranche décidée. `sell_price_eur` est en EUROS (comme
    `purchase_price` au validate) : c'est la trésorerie réelle qui fait foi.
    """
    ordre: int
    shares: float
    sell_price_eur: float
    sell_date: Optional[str] = None      # ISO 'YYYY-MM-DD', défaut aujourd'hui
    note: Optional[str] = None


@router.post("/v2/exit-plans/{exit_plan_id}/execute-tranche")
async def execute_exit_tranche(exit_plan_id: int, body: ExecuteTrancheBody):
    """Exécute une tranche : vente, encaissement, position, plan, thèse — atomiquement. Zéro appel modèle."""
    try:
        return await execute_tranche(
            exit_plan_id, body.ordre, body.shares, body.sell_price_eur,
            sell_date=body.sell_date, note=body.note,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("execute tranche %s du plan #%s", body.ordre, exit_plan_id)
        raise _agent_error(e)


class ExitAlertBody(BaseModel):
    """Le prix chiffré vient de l'investisseur, le LIBELLÉ du plan (cf. `create_exit_alert`).

    `label` n'est pas exposé : il est composé depuis le `declencheur` figé de la tranche ou de la
    condition accélérée. Une alerte dont on choisirait le motif ne rappellerait plus la raison de
    vendre, seulement le prix.
    """
    price: float
    direction: Literal["above", "below"]
    ordre: Optional[int] = None
    condition_index: Optional[int] = None


@router.post("/v2/exit-plans/{exit_plan_id}/alerts")
async def create_exit_plan_alert(exit_plan_id: int, body: ExitAlertBody):
    """Arme une alerte de prix rattachée à une tranche ou à une condition accélérée du plan."""
    try:
        return await create_exit_alert(
            exit_plan_id, body.price, body.direction,
            ordre=body.ordre, condition_index=body.condition_index,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("alerte de sortie plan #%s", exit_plan_id)
        raise _agent_error(e)


@router.post("/v2/theses/{thesis_id}/post-mortem")
async def create_post_mortem(thesis_id: int):
    """Post-mortem de la position soldée : sort de thèse par hypothèse + leçons versées à la KB."""
    try:
        return await run_exit_agent(thesis_id, "post_mortem")
    except Exception as e:  # noqa: BLE001
        logger.exception("post-mortem thèse #%s", thesis_id)
        raise _agent_error(e)


@router.get("/v2/theses/{thesis_id}/post-mortem")
async def get_post_mortem(thesis_id: int):
    """Post-mortem abouti + les paires de calibration qui en sont sorties."""
    async with get_db_session() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM post_mortems_v2 WHERE thesis_v2_id = $1 AND status = 'completed'",
            thesis_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Aucun post-mortem abouti pour cette thèse V2.")
        paires = await conn.fetch(
            "SELECT metric, predite, realisee, ecart FROM calibration_registry "
            "WHERE thesis_v2_id = $1 ORDER BY metric",
            thesis_id,
        )
    out = dict(row)
    out["calibration"] = [dict(r) for r in paires]
    return out


@router.post("/v2/theses/{thesis_id}/calibration")
async def create_calibration(thesis_id: int):
    """Verse les paires prédit/réalisé de la thèse au registre A5. Les `predite` sont FIGÉES, pas déclarées."""
    try:
        return await run_exit_agent(thesis_id, "calibration")
    except Exception as e:  # noqa: BLE001
        logger.exception("calibration thèse #%s", thesis_id)
        raise _agent_error(e)


@router.get("/v2/calibration/summary")
async def get_calibration_summary():
    """Biais systématique par métrique. `lisible` dit s'il y a assez de recul pour en tirer quoi que ce soit."""
    return await calibration_summary()


# ── Débat de conviction (§9 option C, lot 9) ─────────────────────────────────
class DebateRunBody(BaseModel):
    """Le CONTEXTE du déclenchement, pas la conclusion (#36).

    Ni `resolution_suggeree`, ni `escalade_recommandee`, ni les seuils : la résolution est produite
    par l'agent sous la contrainte anti-complaisance, et les seuils sont réécrits depuis la thèse
    figée. Un corps qui porterait `seuil_invalidation` désarmerait le garde-fou de tout le lot.
    """
    motif: str = ""
    monitoring_session_v2_id: Optional[int] = None


@router.post("/v2/theses/{thesis_id}/debate")
async def create_debate(thesis_id: int, body: DebateRunBody):
    """Soumet la conviction de MAINTIEN au test le plus dur. Le débat naît `open` — l'utilisateur tranche."""
    try:
        return await run_debate(
            thesis_id, motif=body.motif, monitoring_session_v2_id=body.monitoring_session_v2_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("débat thèse #%s", thesis_id)
        raise _agent_error(e)


@router.get("/v2/theses/{thesis_id}/debate")
async def list_debates(thesis_id: int):
    """Historique des débats — sans `context_sent`/`raw_content` (volumineux)."""
    async with get_db_session() as conn:
        rows = await conn.fetch(
            "SELECT id, monitoring_session_v2_id, challenge_json, resolution_suggeree, "
            "escalade_recommandee, invalidation_franchie, status, closure_note, closed_at, "
            "model_used, tokens_in, tokens_out, cost_usd, created_at "
            "FROM conviction_debates_v2 WHERE thesis_v2_id = $1 ORDER BY created_at DESC",
            thesis_id,
        )
    return [dict(r) for r in rows]


class CloseDebateBody(BaseModel):
    """La seule route du lot où un jugement est un paramètre légitime : c'est celui de L'UTILISATEUR.

    #36 interdit de faire entrer par le corps HTTP ce que l'AGENT doit produire sous contrainte ; la
    clôture est l'acte souverain de l'investisseur, y compris contre la suggestion de l'agent — le
    désaccord est alors tracé à côté d'elle, et c'est la matière du post-mortem.
    """
    resolution: Literal["closed_pass", "closed_monitor", "closed_proceed"]
    note: str = ""


@router.post("/v2/debates/{debate_id}/close")
async def close_debate_v2(debate_id: int, body: CloseDebateBody):
    """Clôture le débat. Aucun appel modèle."""
    try:
        return await close_debate(debate_id, body.resolution, body.note)
    except Exception as e:  # noqa: BLE001
        logger.exception("clôture débat #%s", debate_id)
        raise _agent_error(e)


@router.get("/v2/debates/{debate_id}")
async def get_debate(debate_id: int):
    """Débat complet + refs figées."""
    async with get_db_session() as conn:
        row = await conn.fetchrow("SELECT * FROM conviction_debates_v2 WHERE id = $1", debate_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Débat V2 introuvable.")
        refs = await conn.fetch(
            "SELECT entry_id, entry_version, reliability_at_use, field_path, content_snapshot "
            "FROM analysis_knowledge_refs WHERE analysis_id = $1 AND analysis_kind = 'debate' "
            "ORDER BY entry_id",
            debate_id,
        )
    out = dict(row)
    out["knowledge_refs"] = [dict(r) for r in refs]
    return out


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
