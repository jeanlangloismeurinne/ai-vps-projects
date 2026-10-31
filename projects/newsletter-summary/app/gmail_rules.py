"""Règles de transfert Gmail : validation, écriture via le script signé, réconciliation, alertes, rotation.

La base est la source de vérité ; le filtre Gmail n'en est que la projection. Toute écriture suit le
même ordre : intention enregistrée en base (`pending`) → appel signé → `synced` / `error` selon la
réponse AUTHENTIQUE du script. Une issue inconnue (délai, réponse non signée) laisse la règle en
`pending` : jamais `synced` par hypothèse. Contrat : docs/gmail-forward/SPEC.md.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select

from app import aliases as al
from app.config import settings
from app.gmail_client import (ScriptClient, ScriptError, ScriptSignatureError, ScriptUnreachable, payload_hash)
from app.models import GmailAudit, GmailRule, GmailSetting

logger = logging.getLogger(__name__)

MAX_RULES = 50
MAX_SENDERLESS = 5
SECRET_MAX_AGE_DAYS = 183
AUDIT_RETENTION_DAYS = 365
AUTH_FAILURES_ALERT = 3
ADDR_CACHE_S = 300

# Même liste que apps-script/Code.gs (PUBLIC_SUFFIXES) : refus des suffixes publics comme domaine entier.
PUBLIC_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "me.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp", "ne.jp",
    "or.jp", "com.br", "com.mx", "com.ar", "co.za", "co.in", "com.cn", "com.hk", "com.sg", "com.tr", "co.kr",
    "com.tw",
}
_FROM_RE = re.compile(r"^(@[a-z0-9-]+(\.[a-z0-9-]+)+|[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+)$")
_DEST_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$")
_TEXT_EXTRA = set(" .,:'’!?%€_-")

# Substituable par les checks (transport simulé). None = transport réseau réel.
_transport = None
_write_lock = asyncio.Lock()
_addr_cache: dict = {"at": 0.0, "data": None}


class RuleError(Exception):
    """Refus de validation côté VPS. `code` est stable (l'interface s'en sert), `status` le code HTTP."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ── Réglages ─────────────────────────────────────────────────────────────────────────────────

async def get_setting(db, key: str) -> str | None:
    row = await db.get(GmailSetting, key)
    return row.value if row else None


async def set_setting(db, key: str, value: str | None) -> None:
    row = await db.get(GmailSetting, key)
    if value is None:
        if row:
            await db.delete(row)
    elif row:
        row.value, row.updated_at = value, datetime.utcnow()
    else:
        db.add(GmailSetting(key=key, value=value))
    await db.commit()


def csv(value: str) -> list[str]:
    return [s.strip().lower().lstrip("@") for s in (value or "").split(",") if s.strip()]


def allowed_dest_domains() -> list[str]:
    return csv(settings.DEST_ALLOWED_DOMAINS) or [settings.INBOUND_DOMAIN.lower()]


async def current_secret(db) -> str:
    return (await get_setting(db, "secret")) or settings.GMAIL_SCRIPT_SECRET


async def make_client(db, secret: str | None = None) -> ScriptClient:
    return ScriptClient(settings.GMAIL_SCRIPT_URL, secret or await current_secret(db), transport=_transport)


# ── Validation ───────────────────────────────────────────────────────────────────────────────

def _text(value, label: str, maxlen: int) -> str:
    t = str(value or "").strip()
    if len(t) > maxlen:
        raise RuleError("invalid_field", f"{label} : {maxlen} caractères au plus")
    if not all(ch.isalnum() or ch in _TEXT_EXTRA for ch in t):
        raise RuleError("invalid_field", f"{label} : lettres, chiffres et . , : ' ! ? % € _ - seulement")
    return t


def normalize_fields(data: dict) -> dict:
    """Valide et normalise les champs d'une règle (sans toucher à la base). Mêmes refus que le script."""
    name = str(data.get("name") or "").strip()
    if len(name) > 80:
        raise RuleError("invalid_field", "nom : 80 caractères au plus")
    frm = str(data.get("from") if data.get("from") is not None else data.get("from_addr") or "").strip().lower()
    if frm:
        if "*" in frm:
            raise RuleError("criteria_too_broad", "expéditeur : le joker * est refusé")
        if not _FROM_RE.match(frm):
            raise RuleError("criteria_too_broad", "expéditeur : adresse (a@b.fr) ou domaine entier (@b.fr), pas de domaine nu")
        domain = frm.split("@", 1)[1]
        if any(domain == d or domain.endswith("." + d) for d in csv(settings.DENY_FROM)):
            raise RuleError("criteria_too_broad", f"expéditeur : le domaine {domain} figure dans les domaines interdits")
        if frm.startswith("@") and domain in PUBLIC_SUFFIXES:
            raise RuleError("criteria_too_broad", f"expéditeur : @{domain} est un suffixe public, il couvrirait un pays entier")
    subject = _text(data.get("subject_contains"), "sujet", 120)
    if not frm and len(subject) < 6:
        raise RuleError("criteria_too_broad", "il faut un expéditeur, ou un sujet de 6 caractères au moins")
    exclude = _text(data.get("exclude_words"), "mots à exclure", 120)
    dest = str(data.get("destination") or "").strip().lower()
    if not _DEST_RE.match(dest):
        raise RuleError("invalid_field", "destination : adresse invalide")
    if dest.split("@", 1)[1] not in allowed_dest_domains():
        raise RuleError("destination_not_allowed", "destination : domaine non autorisé")
    return {"name": name, "from_addr": frm, "subject_contains": subject, "exclude_words": exclude,
            "skip_inbox": bool(data.get("skip_inbox", False)), "destination": dest}


async def check_limits(db, f: dict, *, enabled: bool, confirm_broad: bool, exclude_id: str | None = None) -> None:
    if not f["from_addr"] and not confirm_broad:
        raise RuleError("confirmation_required",
                        "règle sans expéditeur : elle peut transférer des mails de n'importe quel expéditeur — confirmation requise")
    dup = await db.execute(select(GmailRule.id).where(
        GmailRule.from_addr == f["from_addr"], GmailRule.subject_contains == f["subject_contains"],
        GmailRule.destination == f["destination"], *( [GmailRule.id != exclude_id] if exclude_id else [])))
    if dup.first():
        raise RuleError("duplicate", "une règle existe déjà pour ce expéditeur + sujet + destination", 409)
    if enabled:
        q = select(func.count()).select_from(GmailRule).where(GmailRule.enabled.is_(True))
        if exclude_id:
            q = q.where(GmailRule.id != exclude_id)
        if (await db.execute(q)).scalar_one() >= MAX_RULES:
            raise RuleError("rule_limit", f"{MAX_RULES} règles actives au plus", 409)
        if not f["from_addr"]:
            q2 = q.where(GmailRule.from_addr == "")
            if (await db.execute(q2)).scalar_one() >= MAX_SENDERLESS:
                raise RuleError("rule_limit", f"{MAX_SENDERLESS} règles sans expéditeur au plus", 409)


async def engine_warnings(db, f: dict) -> list[str]:
    """La destination est (en général) un alias du moteur : prévient si le mail transféré serait refusé ou mal rangé."""
    dest_local, _, dest_domain = f["destination"].partition("@")
    if dest_domain != settings.INBOUND_DOMAIN.lower():
        return []
    aliases = await al.list_aliases(db)
    by_local = {a.local_part: a for a in aliases}
    alias = by_local.get(dest_local)
    if alias is None:
        default = next((a for a in aliases if a.is_default), None)
        return [f"« {dest_local} » n'est pas un alias du moteur : ces mails iront à l'alias par défaut"
                + (f" « {default.local_part} »." if default else " (aucun configuré).")]
    out = []
    if not alias.enabled:
        out.append(f"l'alias « {alias.local_part} » est désactivé : ces mails seront refusés.")
    elif not alias.open_senders:
        allowed = [s.lower() for s in (alias.allowed_senders or [])]
        frm = f["from_addr"]
        if not frm:
            out.append(f"l'alias « {alias.local_part} » n'accepte que des expéditeurs listés : vérifiez qu'ils le sont.")
        elif frm.startswith("@"):
            if not any(s.endswith(frm) for s in allowed):
                out.append(f"aucun expéditeur de {frm} n'est dans la liste blanche de l'alias « {alias.local_part} ».")
        elif frm not in allowed:
            out.append(f"{frm} n'est pas dans la liste blanche de l'alias « {alias.local_part} » : ses mails seront refusés.")
    return out


# ── Appels au script (journalisés) ───────────────────────────────────────────────────────────

async def _audit(db, *, action, rule_id=None, crid=None, ok, code=None, payload=None, detail=None, actor="hub"):
    db.add(GmailAudit(actor=actor, action=action, rule_id=rule_id, client_request_id=crid, ok=ok,
                      error_code=code, payload_hash=payload_hash(payload) if payload is not None else None,
                      detail=(detail or None)))
    await db.commit()


async def _note_auth(db, failed: bool) -> None:
    n = int(await get_setting(db, "auth_failures") or 0)
    if not failed:
        if n:
            await set_setting(db, "auth_failures", "0")
            await set_setting(db, "auth_alerted", None)
        return
    n += 1
    await set_setting(db, "auth_failures", str(n))
    if n >= AUTH_FAILURES_ALERT and not await get_setting(db, "auth_alerted"):
        await set_setting(db, "auth_alerted", "1")
        await send_alert(f"{n} échecs d'authentification consécutifs du script Gmail",
                         "Le script Apps Script refuse les appels signés du VPS (signature, horloge ou secret désaccordé). "
                         "Si ce n'est pas une rotation en cours, quelqu'un a peut-être modifié le secret côté Google. "
                         "Page Gmail du Hub → « Tester la connexion ».")


async def call_script(db, action: str, payload: dict | None = None, *, rule_id=None, crid=None,
                      client: ScriptClient | None = None, actor="hub"):
    """Appel signé + journal + compteur d'échecs d'authentification. Relève l'exception du client telle quelle."""
    client = client or await make_client(db)
    try:
        result = await client.call(action, payload)
    except ScriptError as exc:
        await _audit(db, action=action, rule_id=rule_id, crid=crid, ok=False, code=exc.code, payload=payload,
                     detail=None if exc.signed else "réponse non signée", actor=actor)
        await _note_auth(db, exc.is_auth)
        raise
    except ScriptSignatureError as exc:
        await _audit(db, action=action, rule_id=rule_id, crid=crid, ok=False, code="bad_response_signature",
                     payload=payload, detail=str(exc), actor=actor)
        raise
    except ScriptUnreachable as exc:
        await _audit(db, action=action, rule_id=rule_id, crid=crid, ok=False, code="unreachable", payload=payload,
                     detail=str(exc), actor=actor)
        raise
    await _audit(db, action=action, rule_id=rule_id, crid=crid, ok=True, payload=payload, actor=actor)
    await _note_auth(db, False)
    return result


def _script_payload(rule: GmailRule, crid: str) -> dict:
    return {"client_request_id": crid, "from": rule.from_addr, "subject_contains": rule.subject_contains,
            "exclude_words": rule.exclude_words, "skip_inbox": rule.skip_inbox, "destination": rule.destination}


def _failure_message(exc: Exception) -> str:
    if isinstance(exc, ScriptError):
        return f"{exc.code}" + (f" — {exc.message}" if exc.message else "")
    if isinstance(exc, ScriptSignatureError):
        return f"réponse du script rejetée ({exc}) : issue inconnue"
    return f"script injoignable ({exc}) : issue inconnue"


async def _run_op(db, rule: GmailRule) -> GmailRule:
    """Exécute l'écriture voulue (`rule.pending_op`) et range la règle selon l'issue. Ne lève pas pour une panne du script."""
    op = rule.pending_op
    try:
        if op == "create":
            res = await call_script(db, "create_rule", _script_payload(rule, rule.client_request_id),
                                    rule_id=rule.id, crid=rule.client_request_id)
            rule.gmail_filter_id = res["gmail_filter_id"]
        elif op == "replace":
            p = {**_script_payload(rule, rule.client_request_id), "gmail_filter_id": rule.gmail_filter_id}
            res = await call_script(db, "replace_rule", p, rule_id=rule.id, crid=rule.client_request_id)
            rule.gmail_filter_id = res["gmail_filter_id"]
        elif op in ("delete", "remove"):
            await call_script(db, "delete_rule", {"gmail_filter_id": rule.gmail_filter_id}, rule_id=rule.id)
            rule.gmail_filter_id = None
        else:
            return rule
    except ScriptError as exc:
        # Refus authentique → error ; un défaut d'authentification, lui, n'a rien décidé → pending.
        rule.sync_status = "pending" if exc.is_auth or not exc.signed else "error"
        rule.last_error = _failure_message(exc)
        rule.updated_at = datetime.utcnow()
        await db.commit()
        return rule
    except (ScriptUnreachable, ScriptSignatureError) as exc:
        rule.sync_status, rule.last_error = "pending", _failure_message(exc)
        rule.updated_at = datetime.utcnow()
        await db.commit()
        return rule
    if op == "remove":
        await db.delete(rule)
        await db.commit()
        return rule
    rule.pending_op, rule.sync_status, rule.drift_kind, rule.last_error = None, "synced", None, None
    rule.updated_at = datetime.utcnow()
    await db.commit()
    return rule


# ── CRUD ─────────────────────────────────────────────────────────────────────────────────────

def _new_crid() -> str:
    return uuid.uuid4().hex


async def get_rule(db, rule_id: str) -> GmailRule:
    rule = await db.get(GmailRule, rule_id)
    if rule is None:
        raise RuleError("not_found", "règle introuvable", 404)
    return rule


async def list_rules(db) -> list[GmailRule]:
    return list((await db.execute(select(GmailRule).order_by(GmailRule.created_at.desc(), GmailRule.id))).scalars())


async def create_rule(db, data: dict, *, enabled: bool = True, confirm_broad: bool = False):
    f = normalize_fields(data)
    await check_limits(db, f, enabled=enabled, confirm_broad=confirm_broad)
    rule = GmailRule(id=str(uuid.uuid4()), enabled=enabled, **f, sync_status="pending" if enabled else "synced",
                     client_request_id=_new_crid() if enabled else None, pending_op="create" if enabled else None)
    db.add(rule)
    await db.commit()
    warnings = await engine_warnings(db, f)
    async with _write_lock:
        if enabled:
            await _run_op(db, rule)
    return rule, warnings


_CRITERIA = ("from_addr", "subject_contains", "exclude_words", "skip_inbox", "destination")


async def update_rule(db, rule_id: str, data: dict, *, confirm_broad: bool = False):
    rule = await get_rule(db, rule_id)
    f = normalize_fields(data)
    await check_limits(db, f, enabled=rule.enabled, confirm_broad=confirm_broad, exclude_id=rule.id)
    changed = any(getattr(rule, k) != f[k] for k in _CRITERIA)
    for k, v in f.items():
        setattr(rule, k, v)
    rule.updated_at = datetime.utcnow()
    if changed and rule.enabled:
        # Rien n'est « synced » tant que le script n'a pas confirmé la nouvelle projection.
        rule.pending_op = "replace" if rule.gmail_filter_id else "create"
        rule.client_request_id, rule.sync_status = _new_crid(), "pending"
    await db.commit()
    warnings = await engine_warnings(db, f)
    if changed and rule.enabled:
        async with _write_lock:
            await _run_op(db, rule)
    return rule, warnings


async def set_enabled(db, rule_id: str, enabled: bool):
    rule = await get_rule(db, rule_id)
    if rule.enabled == enabled:
        return rule
    if enabled:
        await check_limits(db, {"from_addr": rule.from_addr, "subject_contains": rule.subject_contains,
                                "destination": rule.destination}, enabled=True, confirm_broad=True, exclude_id=rule.id)
        rule.enabled, rule.client_request_id = True, _new_crid()
        rule.pending_op, rule.sync_status = ("replace" if rule.gmail_filter_id else "create"), "pending"
    else:
        rule.enabled = False
        if rule.gmail_filter_id:
            rule.pending_op, rule.sync_status = "delete", "pending"
        else:
            rule.pending_op, rule.sync_status, rule.client_request_id = None, "synced", None
    rule.updated_at = datetime.utcnow()
    await db.commit()
    async with _write_lock:
        await _run_op(db, rule)
    return rule


async def remove_rule(db, rule_id: str) -> dict:
    rule = await get_rule(db, rule_id)
    if not rule.gmail_filter_id and rule.pending_op != "replace":
        # Aucun filtre connu. Un create resté `pending` peut pourtant avoir abouti côté script : la
        # réconciliation (crid) le retrouve en orphelin — on ne le perd pas, mais on ne bloque pas non plus.
        await _audit(db, action="remove_rule", rule_id=rule.id, ok=True, detail=f"sans filtre — {rule.name or rule.from_addr}")
        await db.delete(rule)
        await db.commit()
        return {"deleted": True}
    rule.pending_op, rule.sync_status, rule.updated_at = "remove", "pending", datetime.utcnow()
    await db.commit()
    async with _write_lock:
        await _run_op(db, rule)
    gone = await db.get(GmailRule, rule_id) is None
    return {"deleted": gone, "rule_id": rule_id, "error": None if gone else rule.last_error}


async def retry_rule(db, rule_id: str):
    rule = await get_rule(db, rule_id)
    if rule.pending_op is None:
        raise RuleError("nothing_to_retry", "aucune écriture en attente pour cette règle", 409)
    async with _write_lock:
        await _run_op(db, rule)
    return rule


# ── Adresses de transfert ────────────────────────────────────────────────────────────────────

async def forwarding_addresses(db, *, refresh: bool = False) -> dict:
    now = time.monotonic()
    fresh = _addr_cache["data"] is not None and now - _addr_cache["at"] < ADDR_CACHE_S
    stale = False
    if refresh or not fresh:
        try:
            _addr_cache["data"] = await call_script(db, "list_forwarding_addresses")
            _addr_cache["at"] = now
        except (ScriptError, ScriptSignatureError, ScriptUnreachable):
            if _addr_cache["data"] is None:
                raise
            stale = True
    aliases = {a.local_part: a for a in await al.list_aliases(db)}
    out = []
    for a in _addr_cache["data"]:
        local, _, domain = a["email"].partition("@")
        alias = aliases.get(local) if domain.lower() == settings.INBOUND_DOMAIN.lower() else None
        out.append({"email": a["email"], "status": a["status"], "selectable": a["status"] == "accepted"
                    and domain.lower() in allowed_dest_domains(),
                    "alias": {"id": alias.id, "local_part": alias.local_part, "frequency": alias.frequency,
                              "enabled": alias.enabled, "is_default": alias.is_default} if alias else None})
    return {"addresses": out, "stale": stale}


# ── Réconciliation ───────────────────────────────────────────────────────────────────────────

def _matches(f: dict, r: GmailRule) -> bool:
    c, a = f.get("criteria") or {}, f.get("action") or {}
    return ((c.get("from") or "").lower() == r.from_addr and (c.get("subject") or "") == r.subject_contains
            and (a.get("forward") or "").lower() == r.destination)


def classify(rules: list[GmailRule], filters: list[dict]) -> dict:
    """Compare la base à `list_rules` (filtres, étrangers compris). Fonction pure : ne touche à rien.

    Écarts : `missing` (filtre absent), `modified` (critères changés), `should_be_absent` (règle désactivée dont
    le filtre existe), `unrecorded` (le script a créé un filtre que la base n'a pas enregistré : réponse perdue,
    ou ancien filtre resté après un `replace_rule` interrompu). Orphelin = filtre géré qu'aucune règle ne revendique.
    """
    managed = [f for f in filters if f.get("managed")]
    by_id = {f["id"]: f for f in managed}
    by_crid = {f["client_request_id"]: f for f in managed if f.get("client_request_id")}
    claimed: set[str] = set()
    per_rule: dict[str, dict] = {}
    for r in rules:
        f = by_id.get(r.gmail_filter_id) if r.gmail_filter_id else None
        fresh = by_crid.get(r.client_request_id) if r.client_request_id else None
        state = {"kind": None, "ok": False}
        if r.enabled and fresh is not None and fresh["id"] != r.gmail_filter_id:
            state = {"kind": "unrecorded", "new_id": fresh["id"], "old_id": f["id"] if f else None, "ok": False}
            claimed.add(fresh["id"])
            if f:
                claimed.add(f["id"])
        elif r.enabled:
            if f is None:
                if r.gmail_filter_id:
                    state = {"kind": "missing", "ok": False}
            elif not _matches(f, r):
                state = {"kind": "modified", "ok": False}
            else:
                state = {"kind": None, "ok": True}
            if f:
                claimed.add(f["id"])
        else:
            if f is not None:
                state = {"kind": "should_be_absent", "ok": False}
                claimed.add(f["id"])
            else:
                state = {"kind": None, "ok": True}
        per_rule[r.id] = state
    orphans = [{"id": f["id"], "client_request_id": f.get("client_request_id"),
                "criteria": f.get("criteria") or {}, "action": f.get("action") or {}}
               for f in managed if f["id"] not in claimed]
    foreign = [{"id": f["id"], "criteria": f.get("criteria") or {}, "action": f.get("action") or {}}
               for f in filters if not f.get("managed")]
    return {"rules": per_rule, "orphans": orphans, "foreign": foreign}


async def sync(db, *, actor="hub") -> dict:
    """Synchronisation à la demande ET tâche quotidienne : DÉTECTE et range les statuts, ne corrige rien."""
    filters = await call_script(db, "list_rules", {"include_foreign": True}, actor=actor)
    rules = await list_rules(db)
    report = classify(rules, filters)
    for r in rules:
        st = report["rules"][r.id]
        if st["kind"]:
            r.sync_status, r.drift_kind = "drift", st["kind"]
        elif st["ok"] and (r.sync_status in ("drift", "synced")) and r.pending_op is None:
            r.sync_status, r.drift_kind = "synced", None
    await db.commit()
    summary = {"at": datetime.utcnow().isoformat(timespec="seconds"),
               "drift": [{"rule_id": r.id, "name": r.name or r.from_addr or r.subject_contains,
                          "kind": report["rules"][r.id]["kind"]} for r in rules if report["rules"][r.id]["kind"]],
               "orphans": report["orphans"], "foreign": report["foreign"], "rules": len(rules)}
    await set_setting(db, "last_sync", json.dumps(summary, ensure_ascii=False))
    return summary


async def fix_rule(db, rule_id: str) -> GmailRule:
    """Correction à la demande d'un écart : seule l'action de l'utilisateur déclenche une écriture."""
    rule = await get_rule(db, rule_id)
    async with _write_lock:
        await sync(db)
        await db.refresh(rule)
        kind = rule.drift_kind
        if rule.sync_status != "drift" or not kind:
            return rule
        if kind == "missing":
            rule.gmail_filter_id, rule.pending_op, rule.client_request_id = None, "create", _new_crid()
        elif kind == "modified":
            rule.pending_op, rule.client_request_id = "replace", _new_crid()
        elif kind == "should_be_absent":
            rule.pending_op = "delete"
        elif kind == "unrecorded":
            filters = await call_script(db, "list_rules", {"include_foreign": False})
            fresh = next((f for f in filters if f.get("client_request_id") == rule.client_request_id), None)
            if fresh is None:
                raise RuleError("state_changed", "l'état de Gmail a changé : relancez la synchronisation", 409)
            old = rule.gmail_filter_id
            rule.gmail_filter_id, rule.pending_op = fresh["id"], None
            rule.sync_status, rule.drift_kind, rule.last_error = "synced", None, None
            await db.commit()
            if old and old != fresh["id"]:
                try:
                    await call_script(db, "delete_rule", {"gmail_filter_id": old}, rule_id=rule.id)
                except (ScriptError, ScriptSignatureError, ScriptUnreachable) as exc:
                    rule.sync_status, rule.drift_kind, rule.last_error = "drift", "unrecorded", _failure_message(exc)
                    await db.commit()
            return rule
        rule.sync_status, rule.updated_at = "pending", datetime.utcnow()
        await db.commit()
        await _run_op(db, rule)
    return rule


async def delete_orphan(db, filter_id: str) -> dict:
    async with _write_lock:
        await call_script(db, "delete_rule", {"gmail_filter_id": filter_id})
    return {"deleted": True}


async def adopt_orphan(db, filter_id: str) -> GmailRule:
    async with _write_lock:
        filters = await call_script(db, "list_rules", {"include_foreign": False})
    f = next((x for x in filters if x["id"] == filter_id and x.get("managed")), None)
    if f is None:
        raise RuleError("not_found", "filtre géré introuvable (déjà supprimé ?)", 404)
    c, a = f.get("criteria") or {}, f.get("action") or {}
    dest = (a.get("forward") or "").lower()
    frm, subject = (c.get("from") or "").lower(), c.get("subject") or ""
    if not dest:
        raise RuleError("invalid_field", "ce filtre ne transfère pas : rien à adopter", 409)
    exists = await db.execute(select(GmailRule.id).where(GmailRule.from_addr == frm, GmailRule.subject_contains == subject,
                                                         GmailRule.destination == dest))
    if exists.first():
        raise RuleError("duplicate", "une règle équivalente existe déjà", 409)
    rule = GmailRule(id=str(uuid.uuid4()), name=f"Adoptée — {frm or subject}"[:80], enabled=True, from_addr=frm,
                     subject_contains=subject, exclude_words="", skip_inbox="INBOX" in (a.get("removeLabelIds") or []),
                     destination=dest, gmail_filter_id=f["id"], client_request_id=f.get("client_request_id"),
                     sync_status="synced")
    db.add(rule)
    await db.commit()
    await _audit(db, action="adopt_orphan", rule_id=rule.id, crid=rule.client_request_id, ok=True)
    return rule


# ── Alertes ──────────────────────────────────────────────────────────────────────────────────

async def send_alert(subject: str, body: str) -> bool:
    from app import comms_client   # import tardif : les checks substituent get_client
    try:
        await comms_client.get_client().send_email(settings.RECIPIENT_EMAIL, f"⚠️ Gmail — {subject}", body)
        return True
    except Exception:
        logger.exception("Alerte Gmail non envoyée : %s", subject)
        return False


async def secret_rotated_at(db) -> datetime:
    v = await get_setting(db, "secret_rotated_at") or settings.SECRET_ROTATED_AT
    if v:
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            logger.warning("SECRET_ROTATED_AT illisible : %r", v)
    first = await get_setting(db, "secret_first_seen")
    if not first:
        first = datetime.utcnow().isoformat(timespec="seconds")
        await set_setting(db, "secret_first_seen", first)
    return datetime.fromisoformat(first)


async def daily_check() -> dict:
    """Tâche quotidienne : détecte (jamais ne corrige), alerte sur un écart NOUVEAU, sur un secret trop vieux, purge le journal."""
    from app.database import AsyncSessionLocal
    out: dict = {"alerts": []}
    async with AsyncSessionLocal() as db:
        if not settings.GMAIL_SCRIPT_URL:
            return {"skipped": "script non configuré"}
        await db.execute(delete(GmailAudit).where(GmailAudit.at < datetime.utcnow() - timedelta(days=AUDIT_RETENTION_DAYS)))
        await db.commit()
        try:
            summary = await sync(db, actor="cron")
        except (ScriptError, ScriptSignatureError, ScriptUnreachable) as exc:
            day = datetime.utcnow().date().isoformat()
            if await get_setting(db, "alert_unreachable") != day:
                await set_setting(db, "alert_unreachable", day)
                await send_alert("synchronisation quotidienne impossible", f"Le script ne répond pas comme attendu : {_failure_message(exc)}")
                out["alerts"].append("unreachable")
        else:
            sig = json.dumps(sorted([f"{d['rule_id']}:{d['kind']}" for d in summary["drift"]]
                                    + [f"orphan:{o['id']}" for o in summary["orphans"]]))
            if sig != "[]" and sig != await get_setting(db, "alert_sig"):
                lines = [f"• règle « {d['name']} » : {KIND_LABEL[d['kind']]}" for d in summary["drift"]]
                lines += [f"• filtre orphelin {o['id']} (créé par le script, absent de la base)" for o in summary["orphans"]]
                await send_alert("écart non expliqué entre la base et Gmail",
                                 "La synchronisation quotidienne a relevé :\n" + "\n".join(lines)
                                 + "\n\nAucune correction n'a été faite : ouvrez la page Gmail du Hub pour décider.")
                out["alerts"].append("drift")
            await set_setting(db, "alert_sig", sig if sig != "[]" else None)
        age = (datetime.utcnow() - await secret_rotated_at(db)).days
        week = datetime.utcnow().strftime("%G-W%V")
        if age > SECRET_MAX_AGE_DAYS and await get_setting(db, "alert_secret_age") != week:
            await set_setting(db, "alert_secret_age", week)
            await send_alert("secret du script à renouveler", f"Le secret partagé a {age} jours (limite {SECRET_MAX_AGE_DAYS}). Page Gmail du Hub → Rotation.")
            out["alerts"].append("secret_age")
    return out


KIND_LABEL = {"missing": "filtre absent de Gmail", "modified": "filtre modifié dans Gmail",
              "should_be_absent": "règle désactivée mais filtre encore présent",
              "unrecorded": "filtre créé par le script mais non enregistré en base"}


# ── Rotation du secret ───────────────────────────────────────────────────────────────────────

async def rotate_start(db) -> str:
    """Génère le prochain secret (affiché UNE fois) ; l'actuel reste actif jusqu'à la confirmation."""
    nxt = secrets.token_hex(32)
    await set_setting(db, "secret_next", nxt)
    await _audit(db, action="rotate_start", ok=True)
    return nxt


async def rotate_confirm(db) -> dict:
    """Après remplacement du secret dans le script : vérifie par un ping signé avec le NOUVEAU secret, puis le promeut."""
    nxt = await get_setting(db, "secret_next")
    if not nxt:
        raise RuleError("nothing_to_confirm", "aucune rotation en cours", 409)
    client = await make_client(db, secret=nxt)
    try:
        res = await call_script(db, "ping", client=client)
    except (ScriptError, ScriptSignatureError, ScriptUnreachable) as exc:
        raise RuleError("rotation_not_effective", f"le script n'accepte pas encore le nouveau secret ({_failure_message(exc)})", 409)
    await set_setting(db, "secret", nxt)
    await set_setting(db, "secret_next", None)
    await set_setting(db, "secret_rotated_at", datetime.utcnow().isoformat(timespec="seconds"))
    await set_setting(db, "alert_secret_age", None)
    await _audit(db, action="rotate_confirm", ok=True)
    return res


async def rotate_cancel(db) -> None:
    await set_setting(db, "secret_next", None)
    await _audit(db, action="rotate_cancel", ok=True)


# ── Statut, ping, journal ────────────────────────────────────────────────────────────────────

async def ping(db) -> dict:
    try:
        res = await call_script(db, "ping")
        info = {"ok": True, "version": res.get("version"), "enabled": res.get("enabled"), "time": res.get("time")}
    except (ScriptError, ScriptSignatureError, ScriptUnreachable) as exc:
        info = {"ok": False, "error": _failure_message(exc)}
    info["at"] = datetime.utcnow().isoformat(timespec="seconds")
    await set_setting(db, "last_ping", json.dumps(info, ensure_ascii=False))
    return info


async def status(db) -> dict:
    active = (await db.execute(select(func.count()).select_from(GmailRule).where(GmailRule.enabled.is_(True)))).scalar_one()
    senderless = (await db.execute(select(func.count()).select_from(GmailRule).where(
        GmailRule.enabled.is_(True), GmailRule.from_addr == ""))).scalar_one()
    rotated = await secret_rotated_at(db) if settings.GMAIL_SCRIPT_URL else None
    age = (datetime.utcnow() - rotated).days if rotated else None
    load = lambda v: json.loads(v) if v else None   # noqa: E731
    return {
        "configured": bool(settings.GMAIL_SCRIPT_URL and (settings.GMAIL_SCRIPT_SECRET or await get_setting(db, "secret"))),
        "active_rules": active, "max_rules": MAX_RULES, "senderless_rules": senderless, "max_senderless": MAX_SENDERLESS,
        "last_ping": load(await get_setting(db, "last_ping")), "last_sync": load(await get_setting(db, "last_sync")),
        "secret_rotated_at": rotated.isoformat(timespec="seconds") if rotated else None, "secret_age_days": age,
        "secret_too_old": bool(age is not None and age > SECRET_MAX_AGE_DAYS),
        "rotation_pending": bool(await get_setting(db, "secret_next")),
        "auth_failures": int(await get_setting(db, "auth_failures") or 0),
        "deny_from": csv(settings.DENY_FROM), "allowed_domains": allowed_dest_domains(),
    }


async def audit_rows(db, *, action=None, rule_id=None, ok=None, limit=100) -> list[GmailAudit]:
    q = select(GmailAudit).order_by(GmailAudit.id.desc()).limit(max(1, min(limit, 500)))
    if action:
        q = q.where(GmailAudit.action == action)
    if rule_id:
        q = q.where(GmailAudit.rule_id == rule_id)
    if ok is not None:
        q = q.where(GmailAudit.ok.is_(ok))
    return list((await db.execute(q)).scalars())
