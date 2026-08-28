"""
Adapter Resend — réception (inbound webhook) et envoi (API).

Réception : Resend POSTe chaque mail reçu sur *@oozeenaru.resend.app vers notre endpoint
`POST /webhook/resend` avec un payload JSON contenant headers, from, to, cc, bcc, subject,
text, html, attachments, date, message_id, etc. On en extrait ce qu'on stocke.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def parse_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise le payload inbound Resend en champs pour la table `emails`."""
    message_id = payload.get("Message-ID") or payload.get("message_id") or payload.get("id") or ""
    subject = payload.get("subject") or ""
    from_addr = payload.get("from") or ""
    to_addr = ", ".join(payload.get("to") or []) if isinstance(payload.get("to"), list) else (payload.get("to") or "")
    text = payload.get("text") or ""
    html = payload.get("html") or ""

    received_at = payload.get("date")
    if isinstance(received_at, str):
        try:
            received_at = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
        except ValueError:
            received_at = None
    # La colonne `emails.received_at` est naive (UTC). Resend envoie un offset ;
    # aligne sur l'UTC naive pour éviter « can't subtract offset-naive and aware ».
    if received_at is not None and received_at.tzinfo is not None:
        received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)

    return {
        "message_id": message_id,
        "from_addr": from_addr,
        "to_addr": to_addr,
        "subject": subject,
        "text_body": text,
        "html_body": html,
        "received_at": received_at,
    }


async def send_email(
    to: str,
    subject: str,
    body: str,
) -> None:
    """Envoie un email via l'API Resend (transactionnel)."""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": settings.SENDER_EMAIL,
        "to": [to],
        "subject": subject,
        "text": body,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
    if r.status_code >= 300:
        logger.error(
            "Resend send_email — HTTP %s: %s (subject=%r)",
            r.status_code, r.text[:300], subject,
        )
        raise RuntimeError(f"Resend send_email a échoué (HTTP {r.status_code}).")
    logger.info("Resend send_email OK — to=%s subject=%r", to, subject)
