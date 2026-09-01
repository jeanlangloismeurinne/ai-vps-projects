"""
Adapter Resend — RÉCEPTION (inbound webhook) uniquement.

L'ENVOI passe désormais par le `comms-gateway` (via `app/comms_client.py`) : ce projet ne
détient plus de clé API Resend. Réception : Resend POSTe chaque mail reçu sur
*@oozeenaru.resend.app vers notre endpoint `POST /webhook/resend` avec un payload JSON
contenant headers, from, to, cc, bcc, subject, text, html, attachments, date, message_id.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _first(*values):
    """Renvoie la première valeur non vide (gère les champs à la racine ET dans `headers`)."""
    for v in values:
        if v:
            return v
    return ""


def parse_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise le payload inbound Resend en champs pour la table `emails`.

    Tolérant : lit d'abord les clés de premier niveau, puis retombe sur `headers`
    (Resend peut n'y placer que Message-ID / From / Subject / Date selon le mail).
    """
    headers = payload.get("headers") or {}

    message_id = _first(
        payload.get("Message-ID"), payload.get("message_id"),
        payload.get("id"),
        headers.get("Message-ID"), headers.get("message-id"),
    )
    subject = _first(payload.get("subject"), headers.get("Subject"), headers.get("subject"))
    from_addr = _first(payload.get("from"), headers.get("From"), headers.get("from"))
    to_val = payload.get("to") or headers.get("To") or headers.get("to")
    to_addr = ", ".join(to_val) if isinstance(to_val, list) else (to_val or "")
    text = payload.get("text") or ""
    html = payload.get("html") or ""

    received_at = payload.get("date") or headers.get("Date") or headers.get("date")
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
