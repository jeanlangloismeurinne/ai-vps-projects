"""
Monitoring Sessions V1 — suivi des thèses via MonitoringAgentV1.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_db_session

router = APIRouter(tags=["monitoring-v1"])
logger = logging.getLogger(__name__)


# ─────────────────────────── Pydantic schemas ────────────────────────────────

class SessionCreate(BaseModel):
    trigger_type: str = "manual"
    trigger_label: str = ""
    mode: int              # 1..5
    thesis_id: Optional[int] = None
    message: Optional[str] = None          # contexte libre si fourni directement
    private_metrics: Optional[dict] = None  # métriques opérationnelles (sociétés non cotées)
    private_metrics_text: Optional[str] = None  # version texte formatée pour l'agent
    calendar_event_id: Optional[int] = None  # renseigné pour sessions auto-scheduler


class ChatMessage(BaseModel):
    content: str


class SessionUpdate(BaseModel):
    status: str  # 'archived' | 'reviewed'


class ResultUpload(BaseModel):
    result_json: dict


# ─────────────────────────── Helpers ─────────────────────────────────────────

def _serialize(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def _get_session_or_404(db, session_id: int):
    row = await db.fetchrow("SELECT * FROM monitoring_sessions WHERE id=$1", session_id)
    if not row:
        raise HTTPException(404, f"Session #{session_id} introuvable")
    return row


def _normalize_monitoring_result(parsed: dict, thesis_json: dict | None) -> dict:
    """
    Fusionne hypothesis_reviews[] (agent) avec les hypothèses de la thèse.
    Produit hypotheses_reviewed[] utilisable directement par la Page 5.
    """
    if not parsed:
        return parsed
    reviews_raw = parsed.get("hypothesis_reviews", [])
    if not reviews_raw or not thesis_json:
        return parsed

    reviews_by_id = {}
    for r in reviews_raw:
        if not isinstance(r, dict):
            continue
        hid = str(r.get("hypothesis_id") or r.get("id") or "")
        reviews_by_id[hid] = r
        reviews_by_id[hid.replace("H", "")] = r  # tolère "H1" et "1"

    thesis_hyps = thesis_json.get("hypotheses", [])
    hypotheses_reviewed = []
    for h in thesis_hyps:
        hid_full = str(h.get("id", ""))         # "H1"
        hid_num  = hid_full.replace("H", "")    # "1"
        review = reviews_by_id.get(hid_full) or reviews_by_id.get(hid_num) or {}
        hypotheses_reviewed.append({
            "id":                     hid_full,
            "text":                   h.get("text", ""),
            "weight":                 h.get("weight", ""),
            "kpi_metric":             h.get("kpi_metric", ""),
            "kpi_unit":               h.get("kpi_unit", ""),
            "alert_threshold":        h.get("alert_threshold", {}),
            "invalidation_threshold": h.get("invalidation_threshold", {}),
            "status":                 review.get("status", "unverified"),
            "observation":            review.get("observation", ""),
        })

    out = dict(parsed)
    out["hypotheses_reviewed"] = hypotheses_reviewed
    return out


async def _build_monitoring_context(db, ticker_id: str, thesis_id: Optional[int], mode: int, trigger_label: str) -> str:
    """Construit le contexte texte envoyé à l'agent."""
    import json

    # Vérifie si la société est cotée ou non
    ticker_row = await db.fetchrow("SELECT company_type FROM tickers WHERE id=$1", ticker_id)
    company_type = (ticker_row["company_type"] if ticker_row else "public") or "public"

    parts = [f"Ticker : {ticker_id}", f"Trigger : {trigger_label}", f"Mode demandé : {mode}",
             f"company_type : {company_type}"]

    if thesis_id:
        thesis = await db.fetchrow("SELECT * FROM theses WHERE id=$1", thesis_id)
        if thesis:
            parts.append(f"Thèse — one_liner : {thesis['one_liner'] or '(non renseigné)'}")
            if thesis["thesis_json"]:
                parts.append(f"Thèse JSON :\n```json\n{json.dumps(thesis['thesis_json'], ensure_ascii=False, indent=2)}\n```")

    if company_type == "private":
        # Ajoute le profil private
        private_profile = await db.fetchrow(
            "SELECT * FROM private_company_profiles WHERE ticker_id=$1", ticker_id
        )
        if private_profile:
            profile_dict = dict(private_profile)
            for k, v in profile_dict.items():
                if hasattr(v, "isoformat"):
                    profile_dict[k] = v.isoformat()
            parts.append(
                f"### Type d'entreprise: Non cotée (PE/VC)\n"
                f"### Profil private:\n{json.dumps(profile_dict, ensure_ascii=False, indent=2)}"
            )
        else:
            parts.append("### Type d'entreprise: Non cotée (PE/VC)")
    else:
        # Données de marché (uniquement pour sociétés cotées)
        try:
            from app.data_collection.data_service import DataService
            from app.config import settings
            m1 = await DataService().get_m1(ticker_id, settings.FMP_API_KEY)
            parts.append(
                f"Données de marché : prix={m1.get('price')}, PER NTM={m1.get('forward_pe')}, "
                f"market_cap={m1.get('market_cap')}"
            )
        except Exception:
            pass

    return "\n\n".join(parts)


# ─────────────────────────── Sessions sous /tickers/{ticker_id}/monitoring ───

@router.get("/tickers/{ticker_id}/monitoring")
async def list_sessions(ticker_id: str):
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT * FROM monitoring_sessions WHERE ticker_id=$1 ORDER BY created_at DESC",
            ticker_id,
        )
    return [_serialize(r) for r in rows]


@router.post("/tickers/{ticker_id}/monitoring", status_code=201)
async def create_and_run_session(ticker_id: str, data: SessionCreate):
    """
    Crée une session de monitoring et la lance immédiatement via MonitoringAgentV1.
    Vérifie la sync de l'agent avant toute chose.
    """
    from app.agents.monitoring_agent_v1 import MonitoringAgentV1, AgentNotSyncedError

    if data.mode not in range(1, 6):
        raise HTTPException(400, "mode doit être entre 1 et 5")

    # Vérifie sync avant création
    try:
        agent = MonitoringAgentV1()
        # _check_sync lève AgentNotSyncedError si non synced
        from app.db.database import get_db_session as _gds
        async with _gds() as db:
            sync_row = await db.fetchrow(
                "SELECT synced, dust_agent_id FROM agent_prompts WHERE agent_name='monitoring-agent'"
            )
        if sync_row and not sync_row["synced"]:
            # Crée la session en status bloqué
            async with _gds() as db:
                session_row = await db.fetchrow(
                    """
                    INSERT INTO monitoring_sessions
                        (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                         calendar_event_id)
                    VALUES ($1,$2,$3,$4,$5,'blocked_sync',$6)
                    RETURNING *
                    """,
                    ticker_id, data.thesis_id, data.trigger_type, data.trigger_label,
                    data.mode, data.calendar_event_id,
                )
            return {
                "session": _serialize(session_row),
                "error": "Agent monitoring-agent non synchronisé. Sync requis avant exécution.",
                "status": "blocked_sync",
            }
    except Exception:
        pass

    # Vérifie dust_auto_enabled — si désactivé, crée une session pending_manual avec contexte
    async with get_db_session() as db:
        t = await db.fetchrow("SELECT id, company_type FROM tickers WHERE id=$1", ticker_id)
        if not t:
            raise HTTPException(404, f"Ticker '{ticker_id}' introuvable")

        ps_row = await db.fetchrow("SELECT dust_auto_enabled FROM portfolio_settings LIMIT 1")
        dust_enabled = bool(ps_row["dust_auto_enabled"]) if ps_row else True

        context_message = data.message
        if not context_message:
            context_message = await _build_monitoring_context(
                db, ticker_id, data.thesis_id, data.mode, data.trigger_label
            )

        # Injecte les métriques opérationnelles fournies via le formulaire (mode 2 private)
        if data.private_metrics_text:
            context_message += f"\n\n### Données opérationnelles fournies\n{data.private_metrics_text}"

        if not dust_enabled:
            # Dust désactivé → session pending_manual, contexte retourné pour copier-coller manuel
            session_row = await db.fetchrow(
                """
                INSERT INTO monitoring_sessions
                    (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                     calendar_event_id)
                VALUES ($1,$2,$3,$4,$5,'pending_manual',$6)
                RETURNING *
                """,
                ticker_id, data.thesis_id, data.trigger_type, data.trigger_label,
                data.mode, data.calendar_event_id,
            )
            return {
                **_serialize(session_row),
                "context_message": context_message,
            }

        # Crée la session en status 'running'
        session_row = await db.fetchrow(
            """
            INSERT INTO monitoring_sessions
                (ticker_id, thesis_id, trigger_type, trigger_label, mode, status,
                 calendar_event_id)
            VALUES ($1,$2,$3,$4,$5,'running',$6)
            RETURNING *
            """,
            ticker_id, data.thesis_id, data.trigger_type, data.trigger_label,
            data.mode, data.calendar_event_id,
        )
    session_id = session_row["id"]

    try:
        result = await agent.run(mode=data.mode, message=context_message)
    except AgentNotSyncedError as e:
        async with get_db_session() as db:
            await db.execute(
                "UPDATE monitoring_sessions SET status='blocked_sync' WHERE id=$1", session_id
            )
        raise HTTPException(503, str(e))
    except Exception as e:
        async with get_db_session() as db:
            await db.execute(
                "UPDATE monitoring_sessions SET status='completed', result_json=$2 WHERE id=$1",
                session_id, {"error": str(e)},
            )
        logger.error(f"MonitoringAgent error (session #{session_id}): {e}")
        raise HTTPException(502, f"Erreur agent: {e}")

    # Parse le JSON de résultat
    parsed = agent.extract_json(result["content"])

    # Normalise hypothesis_reviews[] → hypotheses_reviewed[]
    thesis_json_for_norm = None
    if data.thesis_id:
        async with get_db_session() as db:
            th = await db.fetchrow("SELECT thesis_json FROM theses WHERE id=$1", data.thesis_id)
            if th:
                thesis_json_for_norm = th["thesis_json"]
    if parsed:
        parsed = _normalize_monitoring_result(parsed, thesis_json_for_norm)

    alert_level = None
    routing_suggestion = None
    if parsed:
        alert_level = parsed.get("alert_level") or parsed.get("flag")
        routing_suggestion = parsed.get("routing_suggestion") or parsed.get("action")

    # Met à jour le profil private si l'agent a fourni une mise à jour de valorisation
    if parsed and parsed.get("private_valuation_update"):
        pvu = parsed["private_valuation_update"]
        pvu_next_event_date = pvu.get("next_event_date")
        if pvu_next_event_date and isinstance(pvu_next_event_date, str):
            from datetime import date as _date
            try:
                pvu_next_event_date = _date.fromisoformat(pvu_next_event_date)
            except ValueError:
                pvu_next_event_date = None
        pvu_last_val_date = pvu.get("last_valuation_date")
        if pvu_last_val_date and isinstance(pvu_last_val_date, str):
            from datetime import date as _date
            try:
                pvu_last_val_date = _date.fromisoformat(pvu_last_val_date)
            except ValueError:
                pvu_last_val_date = None
        try:
            async with get_db_session() as db:
                await db.execute(
                    """
                    UPDATE private_company_profiles SET
                        last_valuation_m = COALESCE($1, last_valuation_m),
                        last_valuation_date = COALESCE($2, last_valuation_date),
                        last_valuation_basis = COALESCE($3, last_valuation_basis),
                        current_ownership_pct = COALESCE($4, current_ownership_pct),
                        projected_valuation_next_event_m = COALESCE($5, projected_valuation_next_event_m),
                        next_event_date = COALESCE($6, next_event_date),
                        next_event_type = COALESCE($7, next_event_type),
                        updated_at = NOW()
                    WHERE ticker_id = $8
                    """,
                    pvu.get("last_valuation_m"),
                    pvu_last_val_date,
                    pvu.get("last_valuation_basis"),
                    pvu.get("current_ownership_pct"),
                    pvu.get("projected_valuation_next_event_m"),
                    pvu_next_event_date,
                    pvu.get("next_event_type"),
                    ticker_id,
                )
                # Met également à jour current_ownership_pct sur la position ouverte
                if pvu.get("current_ownership_pct"):
                    await db.execute(
                        """
                        UPDATE portfolio_positions SET current_ownership_pct = $1
                        WHERE ticker_id = $2 AND status = 'open'
                        """,
                        pvu["current_ownership_pct"], ticker_id,
                    )
        except Exception as e:
            logger.warning(f"Private valuation update failed for {ticker_id}: {e}")

    # Met à jour la session
    async with get_db_session() as db:
        updated_row = await db.fetchrow(
            """
            UPDATE monitoring_sessions
            SET status='completed', result_json=$2, alert_level=$3,
                routing_suggestion=$4, model_used=$5, completed_at=NOW()
            WHERE id=$1
            RETURNING *
            """,
            session_id,
            parsed or {"raw": result["content"]},
            alert_level,
            routing_suggestion,
            result.get("model"),
        )
        # Stocke les messages
        await db.execute(
            "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, context_message,
        )
        await db.execute(
            """
            INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
            VALUES ($1, 'agent', $2, $3)
            """,
            session_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    # Notification Slack si alerte
    if alert_level in ("REVIEW_REQUIRED", "CRITICAL"):
        try:
            from app.notifications.slack_webhook import SlackWebhook
            await SlackWebhook().send_monitoring_alert(
                ticker=ticker_id,
                alert_level=alert_level,
                mode=data.mode,
                label=data.trigger_label,
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Slack monitoring alert failed: {e}")

    return {
        "session": _serialize(updated_row),
        "alert_level": alert_level,
        "routing_suggestion": routing_suggestion,
        "tokens_input": result.get("tokens_input"),
        "tokens_output": result.get("tokens_output"),
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/tickers/{ticker_id}/monitoring/{session_id}")
async def get_session(ticker_id: str, session_id: int):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM monitoring_sessions WHERE id=$1 AND ticker_id=$2",
            session_id, ticker_id,
        )
    if not row:
        raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")
    return _serialize(row)


@router.post("/tickers/{ticker_id}/monitoring/{session_id}/upload-result")
async def upload_manual_result(ticker_id: str, session_id: int, data: ResultUpload):
    """Reçoit le JSON résultat collé depuis Dust pour une session pending_manual."""
    async with get_db_session() as db:
        session_row = await db.fetchrow(
            "SELECT * FROM monitoring_sessions WHERE id=$1 AND ticker_id=$2",
            session_id, ticker_id,
        )
    if not session_row:
        raise HTTPException(404, f"Session #{session_id} introuvable")
    if session_row["status"] != "pending_manual":
        raise HTTPException(
            400,
            f"Session #{session_id} n'est pas en attente manuelle (statut : {session_row['status']})",
        )

    parsed = data.result_json

    thesis_json_for_norm = None
    if session_row["thesis_id"]:
        async with get_db_session() as db:
            th = await db.fetchrow("SELECT thesis_json FROM theses WHERE id=$1", session_row["thesis_id"])
            if th:
                thesis_json_for_norm = th["thesis_json"]
    if parsed:
        parsed = _normalize_monitoring_result(parsed, thesis_json_for_norm)

    alert_level = (parsed.get("alert_level") or parsed.get("flag")) if parsed else None
    routing_suggestion = (parsed.get("routing_suggestion") or parsed.get("action")) if parsed else None

    # Met à jour le profil private si l'agent a fourni une mise à jour de valorisation
    if parsed and parsed.get("private_valuation_update"):
        pvu = parsed["private_valuation_update"]
        pvu_next_event_date = pvu.get("next_event_date")
        if pvu_next_event_date and isinstance(pvu_next_event_date, str):
            from datetime import date as _date
            try:
                pvu_next_event_date = _date.fromisoformat(pvu_next_event_date)
            except ValueError:
                pvu_next_event_date = None
        pvu_last_val_date = pvu.get("last_valuation_date")
        if pvu_last_val_date and isinstance(pvu_last_val_date, str):
            from datetime import date as _date
            try:
                pvu_last_val_date = _date.fromisoformat(pvu_last_val_date)
            except ValueError:
                pvu_last_val_date = None
        try:
            async with get_db_session() as db:
                await db.execute(
                    """
                    UPDATE private_company_profiles SET
                        last_valuation_m = COALESCE($1, last_valuation_m),
                        last_valuation_date = COALESCE($2, last_valuation_date),
                        last_valuation_basis = COALESCE($3, last_valuation_basis),
                        current_ownership_pct = COALESCE($4, current_ownership_pct),
                        projected_valuation_next_event_m = COALESCE($5, projected_valuation_next_event_m),
                        next_event_date = COALESCE($6, next_event_date),
                        next_event_type = COALESCE($7, next_event_type),
                        updated_at = NOW()
                    WHERE ticker_id = $8
                    """,
                    pvu.get("last_valuation_m"),
                    pvu_last_val_date,
                    pvu.get("last_valuation_basis"),
                    pvu.get("current_ownership_pct"),
                    pvu.get("projected_valuation_next_event_m"),
                    pvu_next_event_date,
                    pvu.get("next_event_type"),
                    ticker_id,
                )
                if pvu.get("current_ownership_pct"):
                    await db.execute(
                        """
                        UPDATE portfolio_positions SET current_ownership_pct = $1
                        WHERE ticker_id = $2 AND status = 'open'
                        """,
                        pvu["current_ownership_pct"], ticker_id,
                    )
        except Exception as e_pvu:
            logger.warning(f"Private valuation update failed for {ticker_id}: {e_pvu}")

    async with get_db_session() as db:
        updated = await db.fetchrow(
            """
            UPDATE monitoring_sessions
            SET status='completed', result_json=$2, alert_level=$3,
                routing_suggestion=$4, completed_at=NOW()
            WHERE id=$1
            RETURNING *
            """,
            session_id, parsed, alert_level, routing_suggestion,
        )

    return {"session": _serialize(updated), "alert_level": alert_level}


@router.patch("/tickers/{ticker_id}/monitoring/{session_id}")
async def update_session(ticker_id: str, session_id: int, data: SessionUpdate):
    """Met à jour le statut d'une session (ex: 'archived')."""
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM monitoring_sessions WHERE id=$1 AND ticker_id=$2",
            session_id, ticker_id,
        )
        if not row:
            raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")
        updated = await db.fetchrow(
            "UPDATE monitoring_sessions SET status=$1, updated_at=NOW() WHERE id=$2 RETURNING *",
            data.status, session_id,
        )
    return _serialize(updated)


@router.post("/tickers/{ticker_id}/monitoring/{session_id}/chat", status_code=201)
async def chat_in_session(ticker_id: str, session_id: int, data: ChatMessage):
    """Envoie un message supplémentaire dans une session existante (mode freeform)."""
    from app.agents.monitoring_agent_v1 import MonitoringAgentV1, AgentNotSyncedError

    async with get_db_session() as db:
        session = await _get_session_or_404(db, session_id)
        if session["ticker_id"] != ticker_id:
            raise HTTPException(404, f"Session #{session_id} introuvable pour ticker '{ticker_id}'")

        await db.execute(
            "INSERT INTO monitoring_messages (session_id, role, content) VALUES ($1,'user',$2)",
            session_id, data.content,
        )

    try:
        agent = MonitoringAgentV1()
        result = await agent.run(mode=session["mode"], message=data.content)
    except AgentNotSyncedError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Erreur agent: {e}")

    async with get_db_session() as db:
        msg_row = await db.fetchrow(
            """
            INSERT INTO monitoring_messages (session_id, role, content, raw_payload)
            VALUES ($1, 'agent', $2, $3)
            RETURNING *
            """,
            session_id, result["content"],
            {"tokens_input": result.get("tokens_input"), "tokens_output": result.get("tokens_output"),
             "cost_usd": result.get("cost_usd")},
        )

    return {
        "message": _serialize(msg_row),
        "content": result["content"],
        "cost_usd": result.get("cost_usd"),
    }


@router.get("/monitoring/{session_id}/messages")
async def get_session_messages(session_id: int):
    async with get_db_session() as db:
        await _get_session_or_404(db, session_id)
        rows = await db.fetch(
            "SELECT * FROM monitoring_messages WHERE session_id=$1 ORDER BY created_at",
            session_id,
        )
    return [_serialize(r) for r in rows]
