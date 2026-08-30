"""Digest matinal : résume toutes les mails non traitées, envoie l'e-mail récap, marque 'summarized'."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.models import Email
from app.database import AsyncSessionLocal
from app.config import settings
from app import resend, summarizer
from app import comms_client

logger = logging.getLogger(__name__)

PARIS_TZ = timezone(timedelta(hours=1))  # Hiver ; géré via heure système Europe/Paris du container


async def run_daily_digest(trigger: str = "scheduled") -> dict:
    """Résume les emails status='new' puis envoie le digest à RECIPIENT_EMAIL."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Email).where(Email.status == "new").order_by(Email.received_at.asc())
        )
        emails = list(result.scalars().all())

        if not emails:
            logger.info("Digest : aucun email en attente — rien à envoyer.")
            return {"sent": False, "count": 0}

        # 1) Résumer chaque mail
        blocks = []
        for email in emails:
            try:
                email.summary = await summarizer.summarize(email)
            except Exception as exc:  # ne bloque pas le digest sur un mail
                logger.exception("Résumé échoué pour email %s — inclus brut", email.message_id)
                email.summary = f"[Résumé indisponible — erreur : {exc}]"
            blocks.append(email)
        await db.commit()

        # 2) Composer le corps
        today = datetime.now(PARIS_TZ).strftime("%A %d %B %Y")
        lines = [
            f"Résumé quotidien des newsletters — {today}",
            f"{len(blocks)} newsletter(s) reçue(s).",
            "",
        ]
        for email in blocks:
            lines.append("─" * 40)
            lines.append(f"■ {email.from_addr} — {email.subject}")
            lines.append("")
            lines.append(email.summary or "(vide)")
            lines.append("")
        body = "\n".join(lines)

        # 3) Envoyer — via le comms-gateway (le projet ne détient plus de clé Resend)
        await comms_client.get_client().send_email(
            to=settings.RECIPIENT_EMAIL,
            subject=f"📬 Résumé hebdo-news — {len(blocks)} newsletter(s) — {today}",
            body=body,
        )

        # 4) Marquer traité
        for email in blocks:
            email.status = "summarized"
            email.summarized_at = datetime.utcnow()
        await db.commit()

        logger.info("Digest envoyé — %d newsletter(s) marquées summarized.", len(blocks))
        return {"sent": True, "count": len(blocks)}
