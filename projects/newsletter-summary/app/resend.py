"""
Adapter Resend — RÉCEPTION (inbound webhook) uniquement.

L'ENVOI passe désormais par le `comms-gateway` (via `app/comms_client.py`) : ce projet ne
détient plus de clé API Resend.

Réception — FORMAT REEL constaté en prod (2026-09) : Resend NE poste PAS un payload plano
avec text/html. Il poste son **enveloppe d'événement** `{type, created_at, data:{...}}`
(`type: "email.received"`) dont `data` ne contient QUE des métadonnées :
from, to, subject, message_id, email_id, received_for, cc, bcc, attachments, created_at.

NB : `data` ne contient PAS de `text`/`html` — le corps du mail n'est pas délivré par cette
enveloppe. Le parse extrait les métadonnées de façon tolérante et conserve le corps s'il
est présent (pour un éventuel parse inbound complet), sinon le corps reste vide et le
résumé signalera explicitement le défaut (cf. digest).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _first(*values):
    """Renvoie la première valeur non vide (gère la racine, `data` et `headers`)."""
    for v in values:
        if v:
            return v
    return ""


def _unwrap(payload: dict) -> dict:
    """Dé-emboîte l'enveloppe `{type, created_at, data:{...}}` de Resend si présente."""
    data = payload.get("data")
    if isinstance(data, dict) and ("message_id" in data or "email_id" in data or "from" in data):
        return data
    return payload


def is_inbound_event(payload: dict[str, Any]) -> bool:
    """Vrai si le payload est un mail REÇU, et non un événement de notre propre envoi.

    Une seule URL de webhook reçoit TOUS les événements Resend, entrants comme sortants. Sans
    ce tri, les `email.sent` / `email.delivered` / `email.opened` du digest qu'on vient
    d'envoyer étaient stockés comme des newsletters à résumer : le digest se mangeait lui-même,
    une ligne fantôme par jour (corps vide), ressortie le lendemain en carte vide dont l'en-tête
    affichait le sujet de la veille. Constaté sur le digest du 2026-09-05.

    Liste BLANCHE, pas liste noire : Resend ajoute des types (`bounced`, `clicked`,
    `complained`, `delivery_delayed`…) et chaque nouveau serait ingéré par défaut.
    Un payload SANS `type` reste accepté — c'est la forme « plano » que `parse_inbound`
    tolère déjà, et la refuser perdrait des mails.
    """
    event_type = payload.get("type")
    return event_type is None or event_type == "email.received"


def parse_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalise le payload inbound Resend en champs pour la table `emails`.

    Tolérant aux trois formes : payload plano, enveloppe `{type, created_at, data}`,
    et champs nichés dans `headers` (From/Subject/Message-ID/Date).
    """
    src = _unwrap(payload)
    headers = src.get("headers") or {}

    message_id = _first(
        src.get("Message-ID"), src.get("message_id"),
        src.get("id"), src.get("email_id"),
        headers.get("Message-ID"), headers.get("message-id"),
    )
    # email_id : identifiant Resend du mail reçu ; sert à rapatrier le corps via l'API
    # (le webhook ne livre ni text/html). Stocké pour traçabilité / re-fetch.
    email_id = src.get("email_id") or ""
    subject = _first(src.get("subject"), headers.get("Subject"), headers.get("subject"))
    from_addr = _first(src.get("from"), headers.get("From"), headers.get("from"))
    to_val = src.get("to") or src.get("received_for") or headers.get("To") or headers.get("to")
    to_addr = ", ".join(to_val) if isinstance(to_val, list) else (to_val or "")
    text = src.get("text") or ""
    html = src.get("html") or ""

    # Date : `date`, puis `created_at` (enveloppe Resend), puis header Date.
    received_at = src.get("date") or payload.get("created_at") or src.get("created_at") \
        or headers.get("Date") or headers.get("date")
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
        "email_id": email_id,
        "from_addr": from_addr,
        "to_addr": to_addr,
        "subject": subject,
        "text_body": text,
        "html_body": html,
        "received_at": received_at,
    }
