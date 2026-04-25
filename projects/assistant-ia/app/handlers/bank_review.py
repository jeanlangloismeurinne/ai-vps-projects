import logging
from pathlib import Path

from app.config import settings
from app.services import bank_review_client, slack_client

logger = logging.getLogger(__name__)

_ACCEPTED_MIMES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


async def handle_file_stored(payload: dict) -> None:
    channel_id = payload.get("channel_id", "")
    if channel_id != settings.BANK_REVIEW_CHANNEL_ID:
        return

    mime_type = payload.get("mime_type", "")
    filename = payload.get("filename", "file")
    file_path = payload.get("path", "")
    uploaded_by = payload.get("uploaded_by", "")

    if not _is_accepted_file(filename, mime_type):
        await slack_client.post_message(
            channel=channel_id,
            text=f":x: <@{uploaded_by}> Format non supporté pour l'import bancaire (`{filename}`). Envoie un fichier CSV ou XLSX.",
            blocks=[],
        )
        return

    try:
        content = Path(file_path).read_bytes()
    except Exception as e:
        logger.error("Impossible de lire le fichier %s : %s", file_path, e)
        await slack_client.post_message(
            channel=channel_id,
            text=f":x: <@{uploaded_by}> Impossible de lire le fichier stocké : {e}",
            blocks=[],
        )
        return

    await slack_client.post_message(
        channel=channel_id,
        text=f":hourglass_flowing_sand: Import de `{filename}` en cours…",
        blocks=[],
    )

    try:
        result = await bank_review_client.import_file(filename, content, mime_type)
    except Exception as e:
        logger.error("Erreur import bank-review : %s", e)
        await slack_client.post_message(
            channel=channel_id,
            text=f":x: <@{uploaded_by}> Erreur lors de l'import : {e}",
            blocks=[],
        )
        return

    session_id = result.get("session_id")
    added = result.get("added", 0)
    date_min = result.get("date_min", "")
    date_max = result.get("date_max", "")

    base = settings.BANK_REVIEW_BASE_URL
    expenses_url = f"{base}/import/history/{session_id}"
    budget_url = f"{base}/budget"

    period = f"{date_min} → {date_max}" if date_min and date_max else "période inconnue"

    blocks = _build_result_blocks(
        user=uploaded_by,
        filename=filename,
        added=added,
        period=period,
        expenses_url=expenses_url,
        budget_url=budget_url,
        new_year=result.get("new_year"),
    )
    await slack_client.post_message(
        channel=channel_id,
        text=f":white_check_mark: Import `{filename}` terminé — {added} transaction(s) ajoutée(s).",
        blocks=blocks,
    )


def _is_accepted_file(filename: str, mime_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in {".csv", ".xlsx", ".xls"} or mime_type in _ACCEPTED_MIMES


def _build_result_blocks(
    user: str, filename: str, added: int, period: str,
    expenses_url: str, budget_url: str, new_year: dict | None,
) -> list:
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":white_check_mark: *Import terminé* — <@{user}>\n"
                    f"• Fichier : `{filename}`\n"
                    f"• Transactions ajoutées : *{added}*\n"
                    f"• Période : {period}"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📋 Voir les dépenses"},
                    "url": expenses_url,
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 Suivi budget"},
                    "url": budget_url,
                },
            ],
        },
    ]

    if new_year:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":sparkles: Nouvelle année fiscale créée : *{new_year.get('year_label', '')}*",
                }
            ],
        })

    return blocks
