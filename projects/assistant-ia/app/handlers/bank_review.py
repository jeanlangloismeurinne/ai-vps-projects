import json
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

# 3 périodes de vacances possibles dans la modale ; la 1re est requise, les autres optionnelles.
_VAC_RANGE_BLOCKS = [
    ("vac_start_1", "vac_end_1", False),
    ("vac_start_2", "vac_end_2", True),
    ("vac_start_3", "vac_end_3", True),
]


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

    # Au lieu d'importer directement, on demande d'abord s'il y a eu des vacances (comme le web).
    value = encode_payload(file_path, filename, mime_type, uploaded_by, channel_id)
    await slack_client.post_message(
        channel=channel_id,
        text=f":page_facing_up: Fichier `{filename}` reçu — indiquez les vacances éventuelles.",
        blocks=vacation_prompt_blocks(value, filename, uploaded_by),
    )


# ─── Exécution effective de l'import (appelée par les handlers de boutons/modale) ──

async def run_import_and_report(
    channel_id: str,
    filename: str,
    file_path: str,
    mime_type: str,
    uploaded_by: str,
    vacation_ranges: str = "",
) -> None:
    """Lit le fichier stocké, lance l'import bank-review (avec vacances éventuelles) et
    poste le compte-rendu dans le channel Slack."""
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

    has_vac = bool(vacation_ranges) and vacation_ranges not in ("[]", "")
    vac_note = " (avec vacances)" if has_vac else ""
    await slack_client.post_message(
        channel=channel_id,
        text=f":hourglass_flowing_sand: Import de `{filename}`{vac_note} en cours…",
        blocks=[],
    )

    try:
        result = await bank_review_client.import_file(
            filename, content, mime_type, vacation_ranges=vacation_ranges
        )
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
        has_vacations=has_vac,
    )
    await slack_client.post_message(
        channel=channel_id,
        text=f":white_check_mark: Import `{filename}` terminé — {added} transaction(s) ajoutée(s).",
        blocks=blocks,
    )


# ─── Payload encodé dans les boutons / la private_metadata de la modale ───────────

def encode_payload(path: str, filename: str, mime: str, user: str, channel: str) -> str:
    return json.dumps({"p": path, "f": filename, "m": mime, "u": user, "c": channel})


def decode_payload(value: str) -> dict:
    return json.loads(value)


# ─── Block Kit : question vacances + modale ───────────────────────────────────────

def vacation_prompt_blocks(payload_value: str, filename: str, user: str) -> list:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":page_facing_up: Fichier `{filename}` reçu — <@{user}>\n"
                    ":palm_tree: Y a-t-il eu des *vacances* sur la période ? "
                    "(elles ajustent la classification, comme sur le site web)"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Non, importer"},
                    "style": "primary",
                    "action_id": "bank_import_novac",
                    "value": payload_value,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Oui, préciser"},
                    "action_id": "bank_import_vac",
                    "value": payload_value,
                },
            ],
        },
    ]


def vacation_modal_view(payload_value: str) -> dict:
    def range_blocks(idx: int, optional: bool) -> list:
        return [
            {
                "type": "input",
                "block_id": f"vac_start_{idx}",
                "optional": optional,
                "label": {"type": "plain_text", "text": f"Début période {idx}"},
                "element": {
                    "type": "datepicker",
                    "action_id": "d",
                    "placeholder": {"type": "plain_text", "text": "AAAA-MM-JJ"},
                },
            },
            {
                "type": "input",
                "block_id": f"vac_end_{idx}",
                "optional": optional,
                "label": {"type": "plain_text", "text": f"Fin période {idx}"},
                "element": {
                    "type": "datepicker",
                    "action_id": "d",
                    "placeholder": {"type": "plain_text", "text": "AAAA-MM-JJ"},
                },
            },
        ]

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Indiquez les périodes de vacances sur la période du relevé (jusqu'à 3). "
                    "La *période 1* est requise ; les suivantes sont optionnelles."
                ),
            },
        }
    ]
    blocks += range_blocks(1, False)
    blocks += [{"type": "divider"}]
    blocks += range_blocks(2, True)
    blocks += [{"type": "divider"}]
    blocks += range_blocks(3, True)

    return {
        "type": "modal",
        "callback_id": "bank_vac_modal",
        "private_metadata": payload_value,
        "title": {"type": "plain_text", "text": "Vacances"},
        "submit": {"type": "plain_text", "text": "Importer"},
        "close": {"type": "plain_text", "text": "Annuler"},
        "blocks": blocks,
    }


def parse_modal_vacations(view: dict) -> tuple[str | None, dict]:
    """Extrait les plages de la modale. Retourne (vacation_ranges_json, errors).
    `errors` (bloc_id → message) non vide ⇒ la soumission doit être rejetée."""
    values = view.get("state", {}).get("values", {})
    ranges: list[list[str]] = []
    errors: dict[str, str] = {}
    for start_bid, end_bid, optional in _VAC_RANGE_BLOCKS:
        s = values.get(start_bid, {}).get("d", {}).get("selected_date")
        e = values.get(end_bid, {}).get("d", {}).get("selected_date")
        if not s and not e:
            if not optional:
                errors[start_bid] = "Indiquez au moins une période de vacances."
            continue
        if not s:
            errors[start_bid] = "Date de début manquante."
            continue
        if not e:
            errors[end_bid] = "Date de fin manquante."
            continue
        if s > e:
            errors[end_bid] = "La date de fin doit être postérieure au début."
            continue
        ranges.append([s, e])
    if errors:
        return None, errors
    return json.dumps(ranges), {}


def _is_accepted_file(filename: str, mime_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in {".csv", ".xlsx", ".xls"} or mime_type in _ACCEPTED_MIMES


def _build_result_blocks(
    user: str, filename: str, added: int, period: str,
    expenses_url: str, budget_url: str, new_year: dict | None,
    has_vacations: bool = False,
) -> list:
    vac_line = "\n• Vacances prises en compte : *oui*" if has_vacations else ""
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
                    f"{vac_line}"
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
