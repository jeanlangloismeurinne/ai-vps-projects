"""Digest matinal : résume toutes les mails non traitées, envoie l'e-mail récap, marque 'summarized'."""
from __future__ import annotations

import html as html_mod
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

# Conversion HTML → texte pour le corps *plain* (fallback clients sans HTML / lisible).
_html2text = None  # init paresseuse pour éviter un import lourd au chargement


def _summary_to_text(html_block: str) -> str:
    """Convertit un bloc de résumé HTML en texte brut lisible (pour le fallback email)."""
    global _html2text
    if not html_block:
        return ""
    if _html2text is None:
        import html2text
        _html2text = html2text.HTML2Text()
        _html2text.ignore_links = False
        _html2text.body_width = 0
    return _html2text.handle(html_block).strip()


def _esc(value: str) -> str:
    return html_mod.escape(value or "", quote=True)


# --- Coquille HTML minimale (enveloppe uniquement) : le contenu de chaque carte est
# --- généré par DeepSeek (bloc HTML autonome, cf. summarize_html). C'est l'« Option B » :
# --- le LLM pilote la mise en page de chaque carte, le code ne fournit que l'encadrement.
_ENVELOPPE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Résumé quotidien des newsletters</title>
</head>
<body style="margin:0;padding:0;background-color:#eef1f5;font-family:Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;">
  <div style="max-width:640px;margin:0 auto;padding:24px 16px;">
    <div style="background:#1f2937;color:#ffffff;border-radius:12px 12px 0 0;padding:20px 24px;">
      <h1 style="margin:0;font-size:20px;line-height:1.3;">📬 Résumé quotidien des newsletters</h1>
      <p style="margin:8px 0 0;font-size:13px;opacity:.85;">{date} — {count} newsletter(s)</p>
    </div>
    <div style="background:#ffffff;border-radius:0 0 12px 12px;padding:20px 24px;">
{cards}
    </div>
    <p style="text-align:center;color:#9ca3af;font-size:11px;margin:16px 0 0;">
      Newsletter Summary · généré automatiquement chaque matin
    </p>
  </div>
</body>
</html>"""


def _fallback_card(email: Email, error: str = "") -> str:
    """Carte de secours quand le résumé HTML est absent ou invalide."""
    msg = "⚠ Résumé indisponible." if not error else f"⚠ Résumé en échec — {_esc(error)}"
    return f"""<div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin:0 0 18px;background:#fafafa;">
  <div style="font-size:13px;color:#6b7280;margin-bottom:4px;">{_esc(email.from_addr or '')}</div>
  <div style="font-weight:bold;font-size:15px;color:#111827;margin-bottom:10px;">{_esc(email.subject or '(sans objet)')}</div>
  <p style="margin:0;font-size:14px;color:#374151;">{msg}</p>
</div>"""


def _card_html(email: Email) -> str:
    """Bloc de la newsletter : le résumé HTML du LLM, sinon une carte de secours échappée."""
    s = email.summary or ""
    if s.strip().startswith("<"):
        return s.strip()
    error = getattr(email, "_summary_error", "") or ""
    return _fallback_card(email, error=error)


async def run_daily_digest(trigger: str = "scheduled") -> dict:
    """Résume les emails status='new' puis envoie le digest (HTML) à RECIPIENT_EMAIL."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Email).where(Email.status == "new").order_by(Email.received_at.asc())
        )
        emails = list(result.scalars().all())

        if not emails:
            logger.info("Digest : aucun email en attente — rien à envoyer.")
            return {"sent": False, "count": 0}

        # 1) Résumer chaque mail en HTML
        blocks = []
        for email in emails:
            try:
                email.summary = await summarizer.summarize_html(email)
            except Exception as exc:  # ne bloque pas le digest sur un mail
                logger.exception("Résumé HTML échoué pour email %s", email.message_id)
                email.summary = None
                email._summary_error = str(exc)  # type: ignore[attr-defined]
            blocks.append(email)
        await db.commit()

        # 2) Composer les corps
        today = datetime.now(PARIS_TZ).strftime("%A %d %B %Y")

        # 2a) Corps HTML — enveloppe + cartes DeepSeek
        cards = "\n".join(_card_html(email) for email in blocks)
        html_body = _ENVELOPPE_HTML.format(
            date=_esc(today), count=len(blocks), cards=cards,
        )

        # 2b) Corps texte (fallback : clients non-HTML, lisibilité)
        lines = [
            f"Résumé quotidien des newsletters — {today}",
            f"{len(blocks)} newsletter(s) reçue(s).",
            "",
        ]
        for email in blocks:
            lines.append("─" * 40)
            lines.append(f"■ {email.from_addr} — {email.subject}")
            lines.append("")
            summary_text = _summary_to_text(email.summary) if email.summary else ""
            if summary_text:
                lines.append(summary_text)
            elif not email.text_body and not email.html_body:
                lines.append("⚠ Corps non reçu — Resend n'a transmis que les métadonnées (pas de text/html).")
            else:
                lines.append("(vide)")
            lines.append("")
        plain_body = "\n".join(lines)

        # 3) Envoyer — via le comms-gateway (le projet ne détient plus de clé Resend)
        await comms_client.get_client().send_email(
            to=settings.RECIPIENT_EMAIL,
            subject=f"📬 Résumé hebdo-news — {len(blocks)} newsletter(s) — {today}",
            body=plain_body,
            html=html_body,
        )

        # 4) Marquer traité
        for email in blocks:
            email.status = "summarized"
            email.summarized_at = datetime.utcnow()
        await db.commit()

        logger.info("Digest envoyé — %d newsletter(s) marquées summarized.", len(blocks))
        return {"sent": True, "count": len(blocks)}
