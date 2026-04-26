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


# ─── /feedback ────────────────────────────────────────────────────────────────

def _build_feedback_channel_map() -> dict:
    """
    Construit le mapping channel_id → {name, url} pour la commande /feedback.
    Chaque service peut avoir plusieurs channels (principal + feedback-*).
    """
    mapping: dict = {}
    services = [
        {
            "name": "bank-review",
            "url": settings.BANK_REVIEW_BASE_URL,
            "channels_env": settings.FEEDBACK_CHANNELS_BANK_REVIEW,
            # channel principal toujours inclus
            "extra_channels": [settings.BANK_REVIEW_CHANNEL_ID],
        },
    ]
    for svc in services:
        ids = [c.strip() for c in svc["channels_env"].split(",") if c.strip()]
        ids += [c for c in svc["extra_channels"] if c]
        for cid in ids:
            if cid:
                mapping[cid] = {"name": svc["name"], "url": svc["url"]}
    return mapping


_FEEDBACK_MAP: dict = {}


@bolt.command("/feedback")
async def cmd_feedback(ack, body, respond):
    await ack()
    global _FEEDBACK_MAP
    if not _FEEDBACK_MAP:
        _FEEDBACK_MAP = _build_feedback_channel_map()

    channel_id: str = body.get("channel_id", "")
    text: str = (body.get("text") or "").strip()
    channel_name: str = body.get("channel_name", "")

    service = _FEEDBACK_MAP.get(channel_id)
    if not service:
        await respond(
            "Ce channel n'est pas associé à un service.\n"
            "Utilisez `/feedback` depuis un channel lié à un service (ex. `#bank-review`, `#feedback-bank-review`)."
        )
        return

    # Détection du type : "bug: ...", "feature: ...", "suggestion: ..."
    feedback_type = "suggestion"
    for t in ("bug", "feature", "suggestion", "error"):
        prefix = f"{t}:"
        if text.lower().startswith(prefix):
            feedback_type = t
            text = text[len(prefix):].strip()
            break
        prefix_space = f"{t} "
        if text.lower().startswith(prefix_space):
            feedback_type = t
            text = text[len(prefix_space):].strip()
            break

    if not text:
        await respond(
            "Usage : `/feedback [bug:|feature:|suggestion:] votre message`\n"
            "Exemples :\n"
            "• `/feedback Le bouton import ne fonctionne pas`\n"
            "• `/feedback bug: Erreur 500 sur /budget`\n"
            "• `/feedback feature: Ajouter un export PDF`"
        )
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{service['url']}/api/feedback",
                json={
                    "type": feedback_type,
                    "message": text,
                    "url": f"slack://#{channel_name}",
                },
                timeout=8.0,
            )
        if resp.status_code == 200:
            TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
            emoji = TYPE_EMOJI.get(feedback_type, "📝")
            await respond(
                response_type="ephemeral",
                text=f"{emoji} Feedback enregistré pour *{service['name']}* (`{feedback_type}`). Merci !",
            )
        else:
            await respond(f"❌ Erreur lors de l'enregistrement ({resp.status_code}).")
    except Exception as exc:
        logger.error("cmd_feedback error: %s", exc)
        await respond("❌ Impossible de joindre le service. Réessayez.")


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
