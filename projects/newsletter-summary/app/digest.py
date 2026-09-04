"""Digest matinal : résume toutes les mails non traitées, envoie l'e-mail récap, marque 'summarized'."""
from __future__ import annotations

import html as html_mod
import logging
import re
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.models import Email
from app.database import AsyncSessionLocal
from app.config import settings
from app import resend, summarizer
from app import comms_client
from app.prompts import get_active_html_prompt
from app.kb import store_email_summary

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
  <div style="max-width:640px;margin:0 auto;padding:0;">
    <div style="background:#1f2937;color:#ffffff;padding:18px 16px;">
      <h1 style="margin:0;font-size:20px;line-height:1.3;">📬 Résumé quotidien des newsletters</h1>
      <p style="margin:8px 0 0;font-size:13px;opacity:.85;">{date} — {count} newsletter(s)</p>
    </div>
    <div style="background:#ffffff;padding:12px 0;">
{cards}
    </div>
    <p style="text-align:center;color:#9ca3af;font-size:11px;margin:16px 0 0;">
      Newsletter Summary · généré automatiquement chaque matin
    </p>
  </div>
</body>
</html>"""


# --- Carte : ouverture/fermeture DÉTERMINISTES côté code (le modèle ne produit
# --- QUE le corps du résumé). L'en-tête expéditeur/sujet est lui aussi rendu par le
# --- code — le modèle n'a donc plus à émettre le moindre <div> d'encadrement.
# --- Conséquence : une carte ne peut JAMAIS en avaler une autre, même si la sortie du
# --- modèle est malformée ou incomplète. Marges latérales nulles (plein écran mobile),
# --- padding interne conservé pour que le texte ne colle pas au bord.
_CARD_OPEN = (
    '<div style="background:#f6f8fa;border:1px solid #e5e7eb;border-radius:8px;'
    'padding:16px 18px;margin:0 0 16px;">'
)
_CARD_CLOSE = "</div>"


def _card_header(email: Email) -> str:
    """En-tête de carte (expéditeur + sujet), rendu par le code — pas par le modèle."""
    return (
        f'<div style="font-size:12px;color:#6b7280;margin:0 0 2px;word-break:break-word;">'
        f'{_esc(email.from_addr or "")}</div>'
        f'<div style="font-weight:bold;font-size:16px;color:#111827;line-height:1.35;'
        f'margin:0 0 10px;">{_esc(email.subject or "(sans objet)")}</div>'
    )


def _fallback_inner(email: Email, error: str = "") -> str:
    """Corps de secours (sans carte ni en-tête : ajoutés par le code) si le résumé manque."""
    msg = "⚠ Résumé indisponible." if not error else f"⚠ Résumé en échec — {_esc(error)}"
    return f'<p style="margin:0;font-size:14px;color:#374151;">{msg}</p>'


def _sanitize_inner(raw: str) -> str:
    """Neutralise le corps produit par le modèle pour qu'il ne puisse PAS casser la carte.

    - retire un éventuel bloc de code Markdown (```html … ```) ;
    - si le modèle a malgré tout enveloppé son corps dans un <div> de carte, on le
      déballe (le cadre est fourni par le code) ;
    - coupe une balise finale non terminée (sortie tronquée) ;
    - ÉQUILIBRE les <div> : ajoute les fermetures manquantes / retire les fermetures en
      trop, pour que le corps soit strictement neutre et ne déborde jamais de la carte.
    """
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    # Déballe un unique <div>…</div> enveloppant tout le corps (le modèle désobéit).
    m = re.match(r"^<div\b[^>]*>(.*)</div>\s*$", s, re.IGNORECASE | re.DOTALL)
    if m:
        s = m.group(1).strip()
    # Coupe une balise ouverte non terminée en fin de chaîne (troncature).
    lt, gt = s.rfind("<"), s.rfind(">")
    if lt > gt:
        s = s[:lt].rstrip()
    # Équilibre les <div>.
    opens = len(re.findall(r"<div\b", s, re.IGNORECASE))
    closes = len(re.findall(r"</div\s*>", s, re.IGNORECASE))
    if opens > closes:
        s += "</div>" * (opens - closes)
    elif closes > opens:
        for _ in range(closes - opens):
            s = re.sub(r"</div\s*>\s*$", "", s, count=1).rstrip()
    return s


def _card_html(email: Email) -> str:
    """Carte d'une newsletter : ouverture + en-tête + corps + fermeture, tout côté code.

    Le modèle ne fournit que le corps (`email.summary`), passé au sanitizer. Les balises de
    carte (`_CARD_OPEN`/`_CARD_CLOSE`) et l'en-tête sont déterministes : aucune sortie du
    modèle, même tronquée, ne peut faire déborder une carte sur la suivante.
    """
    s = email.summary or ""
    if s.strip():
        body = _sanitize_inner(s)
    else:
        error = getattr(email, "_summary_error", "") or ""
        body = _fallback_inner(email, error=error)
    return f"{_CARD_OPEN}{_card_header(email)}{body}{_CARD_CLOSE}"


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

        # 1) Résumer chaque mail en HTML — un appel DeepInfra PAR MAIL (bloc HTML autonome
        #    distinct), avec le prompt actif (éditable via le Hub) relu à chaque exécution.
        prompt = await get_active_html_prompt(db)
        blocks = []
        for email in emails:
            try:
                email.summary = await summarizer.summarize_html(email, prompt=prompt)
            except Exception as exc:  # ne bloque pas le digest sur un mail
                logger.exception("Résumé HTML échoué pour email %s", email.message_id)
                email.summary = None
                email._summary_error = str(exc)  # type: ignore[attr-defined]
            blocks.append(email)
        await db.commit()

        # 1b) Persister chaque résumé dans la KB (enveloppe KNOWLEDGE_ARCHITECTURE §3).
        #     Un échec d'écriture ne bloque pas l'envoi du digest.
        for email in blocks:
            if email.summary:
                try:
                    await store_email_summary(email)
                except Exception as exc:
                    logger.exception("Écriture KB échouée pour email %s", email.message_id)

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
