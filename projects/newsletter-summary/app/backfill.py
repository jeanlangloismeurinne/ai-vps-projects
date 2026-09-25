"""Rapatriement du corps d'un mail reçu (le webhook Resend ne livre que les métadonnées)."""
from __future__ import annotations

import asyncio
import logging

from app import comms_client
from app.database import AsyncSessionLocal
from app.models import Email

logger = logging.getLogger(__name__)


async def backfill_body(row_id: int, email_id: str) -> dict:
    """Rapatrie le corps du mail via le gateway (→ API Resend) et met à jour la ligne.

    Le webhook Resend ne livre ni text/html ; on les récupère donc via email_id.
    Retries courtes : Resend peut mettre un instant à indexer le mail reçu (404).
    (Déplacé tel quel de main.py — le moteur d'alias en a aussi besoin, et main.py importe
    le scheduler : le garder là aurait créé un import circulaire.)
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
