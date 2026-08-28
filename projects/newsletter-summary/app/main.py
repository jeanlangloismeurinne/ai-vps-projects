import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import init_db, get_db, AsyncSessionLocal
from app.models import Email
from app import resend, digest
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


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
    fields = resend.parse_inbound(payload)

    if not fields["message_id"]:
        # Resend peut ne pas peupler Message-ID sur certains mails ; génère une clé de
        # dédup stable si nécessaire.
        fields["message_id"] = (
            f"{fields['from_addr']}|{fields['subject']}|{fields['received_at'] or ''}"
        )

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

    return {"status": "stored", "message_id": fields["message_id"]}


@app.post("/webhook/resend/test")
async def webhook_resend_test(request: Request):
    """Endpoint de test (sans contrainte de token) pour vérifier le routage Traefik réel."""
    payload = await request.json()
    return {"status": "ok", "received": True, "keys": list(payload.keys())}
