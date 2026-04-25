import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from app.services import kanban as kanban_svc
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _fmt_card(card) -> str:
    due = ""
    if card.get("due_date"):
        due = f" — *due* {card['due_date'].strftime('%d/%m %H:%M')}"
    col = card.get("column_name", "")
    return f"• *{card['title']}*{due} [{col}]"


@router.post("/slack/commands")
async def slack_commands(
    command: str = Form(...),
    text: str = Form(default=""),
    response_url: str = Form(default=""),
):
    text = text.strip()

    # ─── /tache ───────────────────────────────────────────────────────────────
    if command == "/tache":
        if not text:
            return JSONResponse({"response_type": "ephemeral", "text": "Usage : `/tache Titre` ou `/tache Titre @board Colonne`"})

        board_name = None
        column_name = None
        title = text

        if "@" in text:
            parts = text.rsplit("@", 1)
            title = parts[0].strip()
            remainder = parts[1].strip().split(None, 1)
            board_name = remainder[0] if remainder else None
            column_name = remainder[1] if len(remainder) > 1 else None

        board = None
        if board_name:
            boards = await kanban_svc.list_boards()
            board = next((b for b in boards if b["name"].lower() == board_name.lower()), None)
            if not board:
                return JSONResponse({"response_type": "ephemeral", "text": f"Board « {board_name} » introuvable."})
        else:
            board = await kanban_svc.get_default_board()

        if not board:
            return JSONResponse({"response_type": "ephemeral", "text": "Aucun board par défaut. Créez-en un depuis l'interface web."})

        columns = await kanban_svc.list_columns(str(board["id"]))
        if not columns:
            return JSONResponse({"response_type": "ephemeral", "text": "Ce board n'a aucune colonne."})

        col = None
        if column_name:
            col = next((c for c in columns if c["name"].lower() == column_name.lower()), None)
            if not col:
                return JSONResponse({"response_type": "ephemeral", "text": f"Colonne « {column_name} » introuvable."})
        else:
            col = columns[0]

        card = await kanban_svc.create_card(str(col["id"]), title)
        return JSONResponse({
            "response_type": "in_channel",
            "text": f"✅ Tâche créée : *{title}* dans *{board['name']}* / *{col['name']}*",
        })

    # ─── /taches ──────────────────────────────────────────────────────────────
    if command == "/taches":
        now = datetime.now(timezone.utc)
        if text.lower() == "semaine":
            # Start of current week (Monday)
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            label = "cette semaine"
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            label = "aujourd'hui"

        cards = await kanban_svc.list_cards_due_between(start, end)
        if not cards:
            return JSONResponse({"response_type": "ephemeral", "text": f"Aucune tâche due {label}."})

        lines = [f"📋 *Tâches dues {label}* ({len(cards)})"] + [_fmt_card(c) for c in cards]
        return JSONResponse({"response_type": "ephemeral", "text": "\n".join(lines)})

    # ─── /vue ─────────────────────────────────────────────────────────────────
    if command == "/vue":
        board = await kanban_svc.get_default_board()
        if not board:
            return JSONResponse({"response_type": "ephemeral", "text": "Aucun board par défaut."})

        board_id = str(board["id"])

        if text.lower().startswith("ajouter "):
            remainder = text[8:].strip()
            parts = remainder.split(None, 1)
            if len(parts) < 2:
                return JSONResponse({"response_type": "ephemeral", "text": "Usage : `/vue ajouter Nom champ`"})
            name, group_by = parts[0], parts[1]
            g = await kanban_svc.create_grouping(board_id, name, group_by)
            return JSONResponse({"response_type": "in_channel", "text": f"✅ Vue « {name} » créée (regroupement : {group_by})."})

        # Activate existing grouping by name
        name = text
        g = await kanban_svc.get_grouping_by_name(board_id, name)
        if not g:
            return JSONResponse({"response_type": "ephemeral", "text": f"Vue « {name} » introuvable."})
        await kanban_svc.activate_grouping(str(g["id"]), board_id)
        return JSONResponse({"response_type": "in_channel", "text": f"✅ Vue « {name} » activée."})

    return JSONResponse({"response_type": "ephemeral", "text": "Commande inconnue."})
