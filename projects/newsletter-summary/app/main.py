import hashlib
import json
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import init_db, get_db, AsyncSessionLocal
from app.models import Email, KbDocument
from app import resend, backfill
from app import aliases as al
from app.prompts import get_active_html_prompt, list_versions, create_version, activate_version, seed_default
from app.kb import envelope_to_dict
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def _derive_message_id(payload: dict, fields: dict) -> str:
    """Génère un identifiant de dédup STABLE et UNIQUE pour un payload sans Message-ID.

    Corrige un bug de perte de données : l'ancien fallback constant
    `from|subject|received_at` (qui valait "||" quand le payload était mal parsé)
    faisait COLLABER toutes les newsletters distinctes → la 1ère était stockée,
    les suivantes silencieusement rejetées en "duplicate".

    Désormais on hashe le payload complet : deux RETRAITS du MÊME webhook produisent
    le même hash (donc toujours dédupliqués), mais deux mails différents ne se
    collisionnent plus.
    """
    raw = json.dumps(payload, sort_keys=True, default=str)
    return "derived:" + hashlib.sha256(raw.encode()).hexdigest()[:40]


def require_hub_token(x_hub_token: str | None = Header(default=None)):
    """Garde des endpoints /api/* appelés par le Hub sur le réseau Docker.

    Lit le header `x-hub-token`. Si HUB_API_TOKEN n'est pas défini, l'accès reste ouvert
    (réseau interne de confiance).
    """
    if settings.HUB_API_TOKEN and x_hub_token != settings.HUB_API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Alias par défaut (la newsletter) + rattachement des mails/versions d'avant les alias, PUIS
    # une v1 du prompt (défaut d'env) si l'éditeur n'a jamais rien enregistré : l'éditeur n'est pas
    # vide et le moteur dispose toujours d'une version persistée.
    async with AsyncSessionLocal() as db:
        try:
            await al.seed_default_alias(db)
            await seed_default(db)
        except Exception:
            logger.exception("Amorçage de l'alias par défaut / du prompt initial en échec")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/resend")
async def webhook_resend(request: Request):
    """Reçoit un mail transféré sur *@oozeenaru.resend.app (POST inbound Resend)."""
    # Authentification minimale : token en query (défense en profondeur)
    token = request.query_params.get("token")
    if settings.WEBHOOK_TOKEN and token != settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    payload = await request.json()
    # Diagnostic : loguer le payload brut sur chaque réception — indispensable pour
    # confirmer le vrai format Resend (les champs arrivent actuellement à vide).
    logger.info("Webhook Resend reçu — clés: %s", list(payload.keys()))
    logger.info("Payload brut: %s", json.dumps(payload, default=str, ensure_ascii=False)[:8000])

    # Trier entrant / sortant AVANT toute écriture (cf. resend.is_inbound_event : le digest
    # se mangeait lui-même via les événements de son propre envoi).
    if not resend.is_inbound_event(payload):
        event_type = payload.get("type")
        logger.info("Événement Resend ignoré (sortant) — type=%s", event_type)
        return {"status": "ignored", "type": event_type}

    fields = resend.parse_inbound(payload)
    logger.info(
        "Parsed — from=%r subject=%r message_id=%r text_len=%d",
        fields["from_addr"], fields["subject"], fields["message_id"], len(fields["text_body"]),
    )

    if not fields["message_id"]:
        # Resend peut ne pas peupler Message-ID au niveau attendu ; génère une clé de
        # dédup stable ET unique (cf. _derive_message_id) pour ne jamais perdre de mail.
        fields["message_id"] = _derive_message_id(payload, fields)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(Email).where(Email.message_id == fields["message_id"])
        )
        if existing.scalar_one_or_none() is not None:
            return {"status": "duplicate", "message_id": fields["message_id"]}

        # Routage : alias dont la partie locale correspond EXACTEMENT au destinataire, sinon l'alias
        # par défaut (la newsletter — le catch-all d'avant les alias). Un `From` vide n'est pas
        # refusé ici (pas encore rapatrié) : le moteur re-contrôle à l'instant du traitement.
        alias = al.match_alias(await al.list_aliases(db), fields["to_addr"])
        admitted, refusal = al.admit(alias, fields["from_addr"], sender_known=False)
        email = Email(**fields, alias_id=alias.id if alias else None,
                      status="new" if admitted else "rejected",
                      last_error=None if admitted else refusal)
        db.add(email)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return {"status": "duplicate", "message_id": fields["message_id"]}
        row_id = email.id
        email_id = fields.get("email_id") or ""

    if not admitted:
        logger.info("Mail rejeté à la réception — alias=%s : %s", alias.local_part if alias else None, refusal)
        return {"status": "rejected", "reason": refusal}

    # Rapatrier le corps (le webhook ne livre que les métadonnées). Non bloquant :
    # si ça échoue, la ligne reste metadata-only et le digest signalera « Corps non reçu ».
    backfill_result = {"ok": False, "reason": "pas d'email_id"}
    if email_id:
        try:
            backfill_result = await backfill.backfill_body(row_id, email_id)
        except Exception as exc:
            logger.exception("Backfill corps exceptionnellement en erreur")
            backfill_result = {"ok": False, "reason": str(exc)}

    return {"status": "stored", "message_id": fields["message_id"],
            "backfill": backfill_result, "email_id": email_id,
            "alias": alias.local_part if alias else None}


@app.post("/webhook/resend/test")
async def webhook_resend_test(request: Request):
    """Endpoint de test (sans contrainte de token) pour vérifier le routage Traefik réel."""
    payload = await request.json()
    return {"status": "ok", "received": True, "keys": list(payload.keys())}


# ── API des versions de prompt + KB (appelées par le Hub sur le réseau Docker) ──

@app.get("/api/prompt")
async def api_prompt(alias_id: int | None = None, _auth: bool = Depends(require_hub_token)):
    """État du prompt d'un alias (défaut : la newsletter) : version active + historique."""
    async with AsyncSessionLocal() as db:
        active_prompt = await get_active_html_prompt(db, alias_id)
        versions = await list_versions(db, alias_id)
    active_id = next((v.id for v in versions if v.is_active), None)
    return {
        "active_id": active_id,
        "active_prompt": active_prompt,
        "versions": [
            {
                "id": v.id,
                "created_at": v.created_at,
                "note": v.note,
                "prompt": v.prompt,
                "is_active": v.is_active,
            }
            for v in versions
        ],
    }


@app.post("/api/prompt/versions")
async def api_prompt_create(payload: dict, _auth: bool = Depends(require_hub_token)):
    """Enregistre une NOUVELLE version du prompt (append-only) et la rend active."""
    prompt = (payload.get("prompt") or "").strip()
    note = (payload.get("note") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt vide")
    async with AsyncSessionLocal() as db:
        row = await create_version(db, prompt=prompt, note=note, alias_id=payload.get("alias_id"))
    return {"ok": True, "id": row.id}


@app.post("/api/prompt/activate")
async def api_prompt_activate(payload: dict, _auth: bool = Depends(require_hub_token)):
    """Rend active une version antérieure (menu déroulant « Restaurer »)."""
    version_id = payload.get("version_id")
    if version_id is None:
        raise HTTPException(status_code=400, detail="version_id manquant")
    async with AsyncSessionLocal() as db:
        row = await activate_version(db, int(version_id), alias_id=payload.get("alias_id"))
    if row is None:
        raise HTTPException(status_code=404, detail="version introuvable")
    return {"ok": True, "id": row.id}


# ── API des alias (appelée par le Hub) ──

def _alias_json(a, counts: dict) -> dict:
    return {
        "id": a.id, "local_part": a.local_part, "address": al.full_address(a),
        "enabled": a.enabled, "frequency": a.frequency, "is_default": a.is_default,
        "recipient": a.recipient, "open_senders": a.open_senders,
        "allowed_senders": a.allowed_senders or [], "counts": counts,
    }


@app.get("/api/aliases")
async def api_aliases(_auth: bool = Depends(require_hub_token)):
    """Alias + décompte des mails par statut (en attente, échecs… — rien ne reste invisible)."""
    async with AsyncSessionLocal() as db:
        aliases = await al.list_aliases(db)
        rows = await db.execute(select(Email.alias_id, Email.status, func.count()).group_by(Email.alias_id, Email.status))
    counts: dict = defaultdict(dict)
    for alias_id, status, n in rows.all():
        counts[alias_id][status] = n
    return {"domain": settings.INBOUND_DOMAIN, "aliases": [_alias_json(a, counts.get(a.id, {})) for a in aliases]}


@app.post("/api/aliases")
async def api_alias_create(payload: dict, _auth: bool = Depends(require_hub_token)):
    async with AsyncSessionLocal() as db:
        try:
            a = await al.create_alias(
                db, payload.get("local_part", ""), frequency=payload.get("frequency", "minute"),
                allowed_senders=payload.get("allowed_senders"), open_senders=bool(payload.get("open_senders", False)),
                enabled=bool(payload.get("enabled", True)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "id": a.id, "address": al.full_address(a)}


@app.put("/api/aliases/{alias_id}")
async def api_alias_update(alias_id: int, payload: dict, _auth: bool = Depends(require_hub_token)):
    async with AsyncSessionLocal() as db:
        try:
            a = await al.update_alias(
                db, alias_id, frequency=payload.get("frequency"), allowed_senders=payload.get("allowed_senders"),
                open_senders=payload.get("open_senders"), enabled=payload.get("enabled"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    if a is None:
        raise HTTPException(status_code=404, detail="alias introuvable")
    return {"ok": True, "id": a.id}


@app.get("/api/aliases/{alias_id}/mails")
async def api_alias_mails(alias_id: int, limit: int = 20, _auth: bool = Depends(require_hub_token)):
    """Derniers mails d'un alias avec statut et dernière erreur nommée."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Email).where(Email.alias_id == alias_id).order_by(Email.id.desc()).limit(max(1, min(limit, 100)))
        )
        rows = list(res.scalars().all())
    return {"mails": [
        {"id": e.id, "received_at": e.received_at, "from_addr": e.from_addr, "subject": e.subject,
         "status": e.status, "attempts": e.attempts, "last_error": e.last_error, "summarized_at": e.summarized_at}
        for e in rows
    ]}


@app.get("/api/kb")
async def api_kb(_auth: bool = Depends(require_hub_token)):
    """Export des enveloppes KB (KNOWLEDGE_ARCHITECTURE §3), federation-ready JSON."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(KbDocument).order_by(KbDocument.ingested_at.desc())
        )
        docs = list(result.scalars().all())
    return {"documents": [envelope_to_dict(d) for d in docs]}
