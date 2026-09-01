import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import init_db, get_db, AsyncSessionLocal
from app.models import Email
from app import resend, digest, comms_client
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


async def _backfill_body(row_id: int, email_id: str) -> dict:
    """Rapatrie le corps du mail via le gateway (→ API Resend Received) et met à jour la ligne.

    Le webhook Resend ne livre ni text/html ; on les récupère donc via email_id.
    Retries courtes : Resend peut mettre un instant à indexer le mail reçu (404).
    """
    attempts = 3
    for i in range(attempts):
        try:
            data = await comms_client.get_client().fetch_inbound_email(email_id)
            break
        except comms_client.CommsError as exc:
            if i < attempts - 1:
                await asyncio.sleep(0.8 * (i + 1))
                continue
            logger.warning("Corps non rapatriable pour email_id=%s : %s", email_id, exc)
            return {"ok": False, "reason": str(exc)}

    if not data:
        return {"ok": False, "reason": "no data"}

    async with AsyncSessionLocal() as db:
        row = await db.get(Email, row_id)
        if row is None:
            return {"ok": False, "reason": "ligne absente"}
        if not row.text_body and data.get("text"):
            row.text_body = data.get("text") or ""
        if not row.html_body and data.get("html"):
            row.html_body = data.get("html") or ""
        if not row.email_id:
            row.email_id = email_id
        # Backfill métadonnées si le webhook ne les avait pas livrées.
        if not row.from_addr and data.get("from"):
            row.from_addr = data.get("from") or ""
        if not row.subject and data.get("subject"):
            row.subject = data.get("subject") or ""
        await db.commit()
    logger.info(
        "Backfill corps OK — row=%d email_id=%s text_len=%d",
        row_id, email_id, len(data.get("text") or ""),
    )
    return {"ok": True, "has_body": bool(data.get("text") or data.get("html"))}


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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

        email = Email(**fields)
        db.add(email)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return {"status": "duplicate", "message_id": fields["message_id"]}
        row_id = email.id
        email_id = fields.get("email_id") or ""

    # Rapatrier le corps (le webhook ne livre que les métadonnées). Non bloquant :
    # si ça échoue, la ligne reste metadata-only et le digest signalera « Corps non reçu ».
    backfill = {"ok": False, "reason": "pas d'email_id"}
    if email_id:
        try:
            backfill = await _backfill_body(row_id, email_id)
        except Exception as exc:
            logger.exception("Backfill corps exceptionnellement en erreur")
            backfill = {"ok": False, "reason": str(exc)}

    return {"status": "stored", "message_id": fields["message_id"],
            "backfill": backfill, "email_id": email_id}


@app.post("/webhook/resend/test")
async def webhook_resend_test(request: Request):
    """Endpoint de test (sans contrainte de token) pour vérifier le routage Traefik réel."""
    payload = await request.json()
    return {"status": "ok", "received": True, "keys": list(payload.keys())}
