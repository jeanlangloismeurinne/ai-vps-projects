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


async def summarize_html(email: Email, *, prompt: str | None = None) -> str:
    """Résume le mail en un BLOC HTML autonome (styles inline) via DeepInfra.

    Ce bloc est destiné à être inséré tel quel dans l'email HTML assemblé par digest.py.
    `prompt` est le prompt actif (éditable via le Hub) ; s'il est absent, on retombe sur
    le défaut `SUMMARIZE_HTML_PROMPT`. Le message système porte — côté code, donc toujours
    garanties même si le prompt est librement réédité — les exigences « en français » et
    « exclure les publicités ».
    """
    plain = _to_plain(email)
    if not plain:
        logger.warning("Email %s sans contenu texte — résumé HTML vide.", email.message_id)
        return ""

    template = prompt or settings.SUMMARIZE_HTML_PROMPT
    # Garde : même si un prompt édité retire le marqueur {email}, on injecte toujours le
    # contenu du mail — sinon le résumé n'aurait aucune matière à résumer.
    if "{email}" in template:
        prompt_final = template.format(email=plain)
    else:
        prompt_final = template.rstrip() + "\n\nEMAIL À RÉSUMER :\n" + plain
    system = (
        "Tu rédiges des blocs HTML de résumé d'emails, propres, lisibles, fidèles, aux styles inline. "
        "Rédige TOUJOURS en français. "
        "EXCLUS TOUJOURS toute publicité, bandeau promo, offre sponsorisée, encart commercial ou lien "
        "de parrainage : ne garde que le contenu éditorial du mail."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt_final},
    ]
    result = await deepinfra_client.chat(
        messages,
        model=settings.DEEPINFRA_MODEL,
        temperature=0.2,
        max_tokens=2500,
    )
    return result.strip()
