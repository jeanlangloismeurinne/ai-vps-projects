"""Stockage KB des résumés — enveloppe document commune (KNOWLEDGE_ARCHITECTURE.md §3).

Chaque mail résumé est persisté sous `KbDocument` dans le format pivot requis par la charte
(body Markdown + métadonnées). Exportable tel quel en JSON via GET /api/kb → prêt pour une
future ingestion dans l'index fédéré (pgvector) sans transformation.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Email, KbDocument

logger = logging.getLogger(__name__)

_html2text = None


def _summary_to_markdown(html_block: str) -> str:
    """Convertit le bloc de résumé HTML produit par DeepSeek en Markdown (pivot humain KB).

    Les liens sont volontairement ignorés dans le pivot : le corps de l'enveloppe doit rester
    du Markdown lisible ; les références canoniques restent portées par `uri`/`metadata`.
    """
    global _html2text
    if not html_block:
        return ""
    if _html2text is None:
        import html2text
        _html2text = html2text.HTML2Text()
        _html2text.ignore_links = True
        _html2text.body_width = 0
    return _html2text.handle(html_block).strip()


def build_envelope(email: Email) -> dict:
    """Construit l'enveloppe document §3 à partir d'un mail résumé.

    Les clés correspondent aux noms d'attributs du modèle `KbDocument` (donc `metadata_`
    pour la colonne « metadata »). La sérialisation JSON s'effectue dans `envelope_to_dict`.
    """
    body_md = _summary_to_markdown(email.summary or "")
    now = datetime.utcnow()
    received = email.received_at or now
    return {
        "doc_id": f"newsletter-summary:mailbox:{email.message_id}",
        "project": "newsletter-summary",
        "source": "mailbox",
        "uri": f"resend:{email.email_id or ''}",
        "title": email.subject or "(sans objet)",
        "body": body_md,
        "lang": "fr",
        "tags": [],
        "entities": {},
        "reliability": 0.70,
        "reliability_tier": "B",
        "visibility": "private",
        "created_at": received,
        "updated_at": now,
        "ingested_at": now,
        "content_hash": "sha256:" + hashlib.sha256(body_md.encode("utf-8")).hexdigest(),
        "metadata_": {
            "message_id": email.message_id,
            "email_id": email.email_id or "",
            "from_addr": email.from_addr or "",
        },
    }


def envelope_to_dict(kb: KbDocument) -> dict:
    """Sérialise une ligne KbDocument en enveloppe JSON (§3), clé `metadata` conforme."""
    return {
        "doc_id": kb.doc_id,
        "project": kb.project,
        "source": kb.source,
        "uri": kb.uri,
        "title": kb.title,
        "body": kb.body,
        "lang": kb.lang,
        "tags": kb.tags or [],
        "entities": kb.entities or {},
        "reliability": float(kb.reliability) if kb.reliability is not None else None,
        "reliability_tier": kb.reliability_tier,
        "visibility": kb.visibility,
        "created_at": kb.created_at,
        "updated_at": kb.updated_at,
        "ingested_at": kb.ingested_at,
        "content_hash": kb.content_hash,
        "metadata": kb.metadata_ or {},
    }


async def store_email_summary(email: Email) -> None:
    """Upsert de l'enveloppe KB du mail résumé (par doc_id stable)."""
    if not email.summary:
        return
    env = build_envelope(email)
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(KbDocument).where(KbDocument.doc_id == env["doc_id"])
        )
        row = existing.scalar_one_or_none()
        if row is None:
            db.add(KbDocument(**env))
        else:
            for key, value in env.items():
                setattr(row, key, value)
        await db.commit()
