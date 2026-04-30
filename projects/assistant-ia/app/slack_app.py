"""
Module Slack Bolt (Socket Mode).
Gère : messages journal (thread replies) + slash commands kanban.
Socket Mode = pas de Request URL à exposer, la connexion WebSocket est initiée par le bot.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from app.config import settings
from app.services import journal as journal_svc
from app.services import kanban as kanban_svc

logger = logging.getLogger(__name__)

# ── App Bolt — sans signing_secret car on n'utilise pas l'Events API HTTP ──
bolt = AsyncApp(token=settings.SLACK_BOT_TOKEN)
_handler: AsyncSocketModeHandler | None = None


# ─── Journal — réponses en thread ─────────────────────────────────────────────

@bolt.event("message")
async def on_message(event: dict, **_):
    # Ignorer les messages de bots et les sous-types (edited, deleted…)
    if event.get("bot_id") or event.get("subtype"):
        return
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return
    if await journal_svc.is_journal_thread(thread_ts):
        await journal_svc.store_entry(event.get("text", ""), event["ts"])
        logger.info(f"Journal entry saved from Slack thread {thread_ts}")


# ─── /tache ───────────────────────────────────────────────────────────────────

@bolt.command("/tache")
async def cmd_tache(ack, body, respond):
    await ack()
    text = (body.get("text") or "").strip()
    if not text:
        await respond("Usage : `/tache Titre` ou `/tache Titre @board Colonne`")
        return

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
            await respond(f"Board « {board_name} » introuvable.")
            return
    else:
        board = await kanban_svc.get_default_board()

    if not board:
        await respond("Aucun board par défaut. Créez-en un depuis l'interface web `/kanban`.")
        return

    columns = await kanban_svc.list_columns(str(board["id"]))
    if not columns:
        await respond("Ce board n'a aucune colonne.")
        return

    col = None
    if column_name:
        col = next((c for c in columns if c["name"].lower() == column_name.lower()), None)
        if not col:
            await respond(f"Colonne « {column_name} » introuvable.")
            return
    else:
        col = columns[0]

    await kanban_svc.create_card(str(col["id"]), title)
    await respond(
        response_type="in_channel",
        text=f"✅ Tâche créée : *{title}* dans *{board['name']}* / *{col['name']}*",
    )


# ─── /taches ──────────────────────────────────────────────────────────────────

@bolt.command("/taches")
async def cmd_taches(ack, body, respond):
    await ack()
    arg = (body.get("text") or "").strip().lower()
    now = datetime.now(timezone.utc)

    if arg == "semaine":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = "cette semaine"
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        label = "aujourd'hui"

    cards = await kanban_svc.list_cards_due_between(start, end)
    if not cards:
        await respond(f"Aucune tâche due {label}.")
        return

    def fmt(c):
        due = f" — *due* {c['due_date'].strftime('%d/%m %H:%M')}" if c.get("due_date") else ""
        return f"• *{c['title']}*{due} [{c['column_name']}]"

    lines = [f"📋 *Tâches dues {label}* ({len(cards)})"] + [fmt(c) for c in cards]
    await respond("\n".join(lines))


# ─── /feature ─────────────────────────────────────────────────────────────────

# Liste des dossiers projets — à incrémenter à chaque nouveau projet (voir CLAUDE.md)
_KNOWN_PROJECTS = [
    "assistant-ia",
    "bank-review",
    "feedback-module",
    "hello-world",
    "homepage",
    "tool-file-intake",
]


async def _submit_feedback(project_name: str, message: str, source_url: str) -> None:
    from app.services import registry as svc_registry
    from app.config import settings

    svc = svc_registry.by_name(project_name)
    if svc:
        url = svc["base_url"].rstrip("/") + svc["feedback_path"]
        headers = {"X-Internal-Api-Key": svc["api_key"]} if svc.get("api_key") else {}
    else:
        url = settings.ASSISTANT_BASE_URL.rstrip("/") + f"/api/feedback/{project_name}"
        headers = {"X-Internal-Api-Key": settings.ASSISTANT_INTERNAL_API_KEY} if settings.ASSISTANT_INTERNAL_API_KEY else {}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"type": "suggestion", "message": message, "url": source_url},
            headers=headers,
            timeout=8.0,
        )
    resp.raise_for_status()


def _project_selector_blocks(message: str) -> list:
    preview = message[:200]
    buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": p},
            "action_id": "feedback_project_select",
            "value": f"{p}|{message}",
        }
        for p in _KNOWN_PROJECTS
    ]
    buttons.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "➕ Nouveau projet"},
        "action_id": "feedback_new_project",
        "value": message,
        "style": "primary",
    })
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"Pour quel projet ce feedback ?\n> {preview}"},
        },
        {"type": "actions", "elements": buttons},
    ]


@bolt.command("/feature")
async def cmd_feedback(ack, body, respond):
    await ack()
    from app.services import registry as svc_registry

    channel_id: str = body.get("channel_id", "")
    channel_name: str = body.get("channel_name", "")
    text: str = (body.get("text") or "").strip()

    if not text:
        await respond(response_type="ephemeral", text="Usage : `/feature votre message`")
        return

    svc = svc_registry.by_channel(channel_id)
    if svc:
        try:
            await _submit_feedback(svc["name"], text, f"slack://#{channel_name}")
            await respond(
                response_type="ephemeral",
                text=f"✅ Feedback enregistré pour *{svc['name']}*. Merci !",
            )
        except Exception as exc:
            logger.error("cmd_feedback direct error: %s", exc)
            await respond(response_type="ephemeral", text="❌ Impossible d'enregistrer le feedback. Réessayez.")
        return

    await respond(
        response_type="ephemeral",
        blocks=_project_selector_blocks(text),
        text="Pour quel projet ce feedback ?",
    )


@bolt.action("feedback_project_select")
async def action_feedback_project(ack, body, respond):
    await ack()
    value: str = body["actions"][0]["value"]
    project_name, _, message = value.partition("|")
    try:
        await _submit_feedback(project_name, message, "slack://direct")
        await respond(
            replace_original=True,
            text=f"✅ Feedback enregistré pour *{project_name}*. Merci !",
        )
    except Exception as exc:
        logger.error("action_feedback_project error: %s", exc)
        await respond(replace_original=True, text="❌ Impossible d'enregistrer le feedback. Réessayez.")


@bolt.action("feedback_new_project")
async def action_feedback_new_project(ack, body, respond):
    await ack()
    message = body["actions"][0]["value"]
    preview = message[:200]
    await respond(
        replace_original=True,
        text=f"🆕 *Nouveau projet* noté. On définira la structure ensemble via Claude Code.\n> {preview}",
    )


# ─── /vue ─────────────────────────────────────────────────────────────────────

@bolt.command("/vue")
async def cmd_vue(ack, body, respond):
    await ack()
    text = (body.get("text") or "").strip()

    board = await kanban_svc.get_default_board()
    if not board:
        await respond("Aucun board par défaut.")
        return
    board_id = str(board["id"])

    if text.lower().startswith("ajouter "):
        remainder = text[8:].strip()
        parts = remainder.split(None, 1)
        if len(parts) < 2:
            await respond("Usage : `/vue ajouter Nom champ`")
            return
        name, group_by = parts[0], parts[1]
        await kanban_svc.create_grouping(board_id, name, group_by)
        await respond(
            response_type="in_channel",
            text=f"✅ Vue « {name} » créée (regroupement : {group_by}).",
        )
        return

    g = await kanban_svc.get_grouping_by_name(board_id, text)
    if not g:
        await respond(f"Vue « {text} » introuvable.")
        return
    await kanban_svc.activate_grouping(str(g["id"]), board_id)
    await respond(response_type="in_channel", text=f"✅ Vue « {text} » activée.")


# ─── Démarrage / arrêt ────────────────────────────────────────────────────────

async def start():
    global _handler
    _handler = AsyncSocketModeHandler(bolt, settings.SLACK_APP_TOKEN)
    await _handler.start_async()


async def stop():
    global _handler
    if _handler:
        await _handler.close_async()
        _handler = None
