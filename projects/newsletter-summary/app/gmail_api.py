"""Routes /api/gmail/* (appelées par le Hub). Toute écriture passe par gmail_rules, qui journalise."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app import gmail_rules as gr
from app.config import settings
from app.database import AsyncSessionLocal
from app.gmail_client import ScriptError, ScriptSignatureError, ScriptUnreachable


def require_hub_token_strict(x_hub_token: str | None = Header(default=None)):
    """Ces routes pilotent l'accès au courrier : contrairement au reste de l'API, jamais ouvertes sans jeton."""
    if not settings.HUB_API_TOKEN:
        raise HTTPException(status_code=503, detail={"code": "no_token", "message": "HUB_API_TOKEN non configuré"})
    if x_hub_token != settings.HUB_API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


router = APIRouter(prefix="/api/gmail", dependencies=[Depends(require_hub_token_strict)])


def _rule_json(r) -> dict:
    return {"id": r.id, "name": r.name, "enabled": r.enabled, "from": r.from_addr, "subject_contains": r.subject_contains,
            "exclude_words": r.exclude_words, "skip_inbox": r.skip_inbox, "destination": r.destination,
            "gmail_filter_id": r.gmail_filter_id, "sync_status": r.sync_status, "drift_kind": r.drift_kind,
            "pending_op": r.pending_op, "last_error": r.last_error,
            "created_at": r.created_at, "updated_at": r.updated_at}


def _guard(exc: Exception):
    if isinstance(exc, gr.RuleError):
        return HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ScriptError):
        return HTTPException(status_code=502, detail={"code": exc.code, "message": exc.message or exc.code})
    if isinstance(exc, (ScriptSignatureError, ScriptUnreachable)):
        return HTTPException(status_code=502, detail={"code": "script_unavailable", "message": str(exc)})
    return exc


async def _run(coro):
    try:
        return await coro
    except (gr.RuleError, ScriptError, ScriptSignatureError, ScriptUnreachable) as exc:
        raise _guard(exc)


@router.get("/status")
async def status():
    async with AsyncSessionLocal() as db:
        return await gr.status(db)


@router.get("/rules")
async def rules():
    async with AsyncSessionLocal() as db:
        return {"rules": [_rule_json(r) for r in await gr.list_rules(db)]}


@router.post("/rules")
async def rule_create(payload: dict):
    async with AsyncSessionLocal() as db:
        rule, warnings = await _run(gr.create_rule(db, payload, enabled=bool(payload.get("enabled", True)),
                                                   confirm_broad=bool(payload.get("confirm_broad", False))))
        return {"rule": _rule_json(rule), "warnings": warnings}


@router.put("/rules/{rule_id}")
async def rule_update(rule_id: str, payload: dict):
    async with AsyncSessionLocal() as db:
        rule, warnings = await _run(gr.update_rule(db, rule_id, payload, confirm_broad=bool(payload.get("confirm_broad", False))))
        return {"rule": _rule_json(rule), "warnings": warnings}


@router.patch("/rules/{rule_id}/enabled")
async def rule_enabled(rule_id: str, payload: dict):
    async with AsyncSessionLocal() as db:
        return {"rule": _rule_json(await _run(gr.set_enabled(db, rule_id, bool(payload.get("enabled")))))}


@router.delete("/rules/{rule_id}")
async def rule_delete(rule_id: str):
    async with AsyncSessionLocal() as db:
        return await _run(gr.remove_rule(db, rule_id))


@router.post("/rules/{rule_id}/retry")
async def rule_retry(rule_id: str):
    async with AsyncSessionLocal() as db:
        return {"rule": _rule_json(await _run(gr.retry_rule(db, rule_id)))}


@router.post("/rules/{rule_id}/fix")
async def rule_fix(rule_id: str):
    async with AsyncSessionLocal() as db:
        return {"rule": _rule_json(await _run(gr.fix_rule(db, rule_id)))}


@router.post("/preview")
async def preview(payload: dict):
    """Validation sans écriture : refus immédiat + avertissements du croisement avec les alias du moteur."""
    async with AsyncSessionLocal() as db:
        try:
            f = gr.normalize_fields(payload)
            await gr.check_limits(db, f, enabled=bool(payload.get("enabled", True)),
                                  confirm_broad=bool(payload.get("confirm_broad", False)), exclude_id=payload.get("id"))
        except gr.RuleError as exc:
            raise _guard(exc)
        return {"ok": True, "warnings": await gr.engine_warnings(db, f)}


@router.get("/forwarding-addresses")
async def forwarding_addresses(refresh: bool = False):
    async with AsyncSessionLocal() as db:
        return await _run(gr.forwarding_addresses(db, refresh=refresh))


@router.post("/sync")
async def sync():
    async with AsyncSessionLocal() as db:
        return await _run(gr.sync(db))


@router.post("/orphans/{filter_id}/delete")
async def orphan_delete(filter_id: str):
    async with AsyncSessionLocal() as db:
        return await _run(gr.delete_orphan(db, filter_id))


@router.post("/orphans/{filter_id}/adopt")
async def orphan_adopt(filter_id: str):
    async with AsyncSessionLocal() as db:
        return {"rule": _rule_json(await _run(gr.adopt_orphan(db, filter_id)))}


@router.get("/audit")
async def audit(action: str | None = None, rule_id: str | None = None, ok: bool | None = None, limit: int = 100):
    async with AsyncSessionLocal() as db:
        rows = await gr.audit_rows(db, action=action, rule_id=rule_id, ok=ok, limit=limit)
        return {"audit": [{"id": a.id, "at": a.at, "actor": a.actor, "action": a.action, "rule_id": a.rule_id,
                           "client_request_id": a.client_request_id, "ok": a.ok, "error_code": a.error_code,
                           "payload_hash": a.payload_hash, "detail": a.detail} for a in rows]}


@router.post("/script/ping")
async def script_ping():
    async with AsyncSessionLocal() as db:
        return await gr.ping(db)


@router.post("/secret/rotate")
async def secret_rotate():
    async with AsyncSessionLocal() as db:
        return {"secret": await gr.rotate_start(db)}


@router.post("/secret/confirm")
async def secret_confirm():
    async with AsyncSessionLocal() as db:
        await _run(gr.rotate_confirm(db))
        return {"ok": True}


@router.post("/secret/cancel")
async def secret_cancel():
    async with AsyncSessionLocal() as db:
        await gr.rotate_cancel(db)
        return {"ok": True}
