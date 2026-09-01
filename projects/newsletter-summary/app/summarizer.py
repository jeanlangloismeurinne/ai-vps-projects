"""Génération du résumé de chaque mail (DeepInfra), le résumé suivant la structure du mail initial."""
from __future__ import annotations

import logging

import html2text

from app import deepinfra_client
from app.config import settings
from app.models import Email

logger = logging.getLogger(__name__)

_html2text = html2text.HTML2Text()
_html2text.ignore_links = False
_html2text.body_width = 0  # pas de césure automatique


def _to_plain(email: Email) -> str:
    """Préfère le corps texte ; sinon convertit le HTML en texte lisible."""
    if email.text_body and email.text_body.strip():
        return email.text_body.strip()
    if email.html_body and email.html_body.strip():
        return _html2text.handle(email.html_body).strip()
    return ""


async def summarize(email: Email) -> str:
    """Résume le mail via DeepInfra en appliquant SUMMARIZATION_PROMPT.

    Le prompt demande explicitement de suivre la structure du mail d'origine.
    """
    plain = _to_plain(email)
    if not plain:
        logger.warning("Email %s sans contenu texte — résumé vide.", email.message_id)
        return ""

    prompt = settings.SUMMARIZATION_PROMPT.format(email=plain)
    messages = [
        {"role": "system", "content": "Tu rédiges des résumés d'emails concis, fidèles et structurés."},
        {"role": "user", "content": prompt},
    ]
    result = await deepinfra_client.chat(
        messages,
        model=settings.DEEPINFRA_MODEL,
        temperature=0.2,
        max_tokens=1500,
    )
    return result.strip()


async def summarize_html(email: Email) -> str:
    """Résume le mail en un BLOC HTML autonome (styles inline) via DeepInfra.

    Ce bloc est destiné à être inséré tel quel dans l'email HTML assemblé par digest.py.
    Le prompt exige du HTML self-contained : pas de <html>/<head>/<body>/<style>, CSS inline,
    échappement correct — de sorte que le rendu final soit robuste dans les clients mail.
    """
    plain = _to_plain(email)
    if not plain:
        logger.warning("Email %s sans contenu texte — résumé HTML vide.", email.message_id)
        return ""

    prompt = settings.SUMMARIZE_HTML_PROMPT.format(email=plain)
    messages = [
        {"role": "system",
         "content": "Tu rédiges des blocs HTML de résumé d'emails, propres, lisibles, fidèles et aux styles inline."},
        {"role": "user", "content": prompt},
    ]
    result = await deepinfra_client.chat(
        messages,
        model=settings.DEEPINFRA_MODEL,
        temperature=0.2,
        max_tokens=2500,
    )
    return result.strip()
