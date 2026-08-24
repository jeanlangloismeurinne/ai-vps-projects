"""
Module Slack Bolt (HTTP Events API).
Gère : messages journal (thread replies) + slash commands kanban.
HTTP Events API = Slack envoie des POST vers /slack/events (plus fiable que Socket Mode).
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta

import httpx
from slack_bolt.async_app import AsyncApp

from app.config import settings
from app.handlers import agent_chat, journal_kb
from app.services import journal as journal_svc
from app.services import kanban as kanban_svc
from app.services import slack_client
from app.services import slack_dedup

logger = logging.getLogger(__name__)

bolt = AsyncApp(token=settings.SLACK_BOT_TOKEN, signing_secret=settings.SLACK_SIGNING_SECRET)


# ─── Journal — réponses en thread ─────────────────────────────────────────────

@bolt.event("message")
async def on_message(event: dict, **_):
    """Dispatcher explicite. L'ordre des branches est normatif (#1787559677482) : le premier
    match gagne. Les branches 3 à 5 écrivent en base et passent donc par la garde d'idempotence.
    """
    bot_id = event.get("bot_id")
    subtype = event.get("subtype")
    thread_ts = event.get("thread_ts")
    user_id = event.get("user", "")
    msg_id = event.get("client_msg_id", "—")
    event_ts = event.get("ts", "—")
    channel = event.get("channel", settings.JOURNAL_CHANNEL_ID)
    text = event.get("text", "")
    logger.info(f"on_message reçu: user={user_id} thread={thread_ts} ts={event_ts} msg_id={msg_id} bot_id={bot_id} subtype={subtype} channel={channel}")

    # ── Branche 1 — messages de bot / à sous-type : jamais traités (anti-boucle) ──
    if bot_id:
        logger.debug(f"on_message: ignoré (bot_id={bot_id})")
        return
    if subtype:
        logger.debug(f"on_message: ignoré (subtype={subtype})")
        return
    # ── Branche 2 — réponse en thread : chaîne journal existante, inchangée ──
    if thread_ts:
        await _handle_thread_message(event, thread_ts, user_id, channel, text, msg_id)
        return

    # ── Branches 3 à 5 — messages parents. Effets de bord ⇒ garde d'idempotence d'abord. ──
    if not user_id:
        # Sans auteur humain identifié, on ne peut pas garantir que ce n'est pas notre propre envoi.
        logger.debug(f"on_message: message parent ignoré (aucun user, ts={event_ts})")
        return

    directive = agent_chat.detect_directive(text)
    if directive:
        target = ("directive", directive)
    elif channel == settings.JOURNAL_CHANNEL_ID:
        target = ("journal_kb", None)
    elif channel == settings.ASSISTANT_CHANNEL_ID:
        target = ("agent_chat", None)
    else:
        # ── Branche 6 — hors périmètre ──
        logger.debug(f"on_message: message parent hors périmètre (channel={channel} ts={event_ts})")
        return

    if not await slack_dedup.claim_event(event):
        return

    # Slack exige un 200 sous 3 s ; classifieur et agent dépassent ce budget.
    asyncio.create_task(_run_parent_branch(target, event))


async def _run_parent_branch(target: tuple, event: dict) -> None:
    """Exécute la branche retenue en tâche de fond. Toute exception doit être tracée : une
    tâche asyncio qui meurt en silence est invisible en production."""
    kind, arg = target
    try:
        if kind == "directive":
            await agent_chat.handle_directive(event, arg)
        elif kind == "journal_kb":
            await journal_kb.handle_free_note(event)
        elif kind == "agent_chat":
            await agent_chat.handle_conversation_turn(event)
    except Exception:
        logger.exception(
            f"on_message: échec de la branche {kind} (ts={event.get('ts')} channel={event.get('channel')})"
        )


async def _handle_thread_message(event: dict, thread_ts: str, user_id: str, channel: str, text: str, msg_id: str) -> None:
    # Session journal v2 active sur ce fil ?
    try:
        from app.handlers.journal_slack import handle_thread_reply
        from app.services import journal_v2 as svc_v2
        session = await svc_v2.get_slack_session_by_thread(thread_ts)
        if session:
            logger.info(f"on_message: session v2 trouvée (id={session['id']} q_index={session['question_index']}), traitement réponse")
            await handle_thread_reply(
                thread_ts=thread_ts,
                user_id=user_id,
                text=text,
                channel=channel,
            )
            return
        else:
            logger.info(f"on_message: aucune session v2 pour thread={thread_ts}, vérification ancien journal")
    except Exception:
        logger.exception(f"on_message: erreur lors du traitement session journal (thread={thread_ts})")
        return

    # Ancien journal libre (thread du prompt quotidien)
    is_old_journal = await journal_svc.is_journal_thread(thread_ts)
    logger.info(f"on_message: ancien journal → is_journal_thread={is_old_journal} (thread={thread_ts})")
    if is_old_journal:
        await journal_svc.store_entry(text, event["ts"])
        logger.info(f"on_message: entrée ancien journal enregistrée (thread={thread_ts})")
    else:
        logger.warning(f"on_message: message non traité — ni session v2 ni fil journal connu (user={user_id} thread={thread_ts} msg_id={msg_id})")


@bolt.action(re.compile(r"^jrn_"))
async def action_journal_answer(ack, body, client, **_):
    await ack()
    action = body["actions"][0]
    raw_value = action["value"]
    parts = raw_value.split("|", 2)
    if len(parts) != 3:
        return
    objectif_id, q_index_str, answer_val = parts
    try:
        q_index = int(q_index_str)
    except ValueError:
        return

    container = body.get("container", {})
    thread_ts = container.get("thread_ts") or body.get("message", {}).get("thread_ts", "")
    channel = container.get("channel_id") or body.get("channel", {}).get("id", settings.JOURNAL_CHANNEL_ID)
    user_id = body.get("user", {}).get("id", "")
    msg_ts = body.get("message", {}).get("ts", "")

    from app.handlers.journal_slack import handle_block_action, _display_value
    display = _display_value(answer_val)

    # Mettre à jour le message avec la réponse sélectionnée avant de traiter
    if msg_ts and channel:
        original_blocks = body.get("message", {}).get("blocks", [])
        question_text = ""
        if original_blocks and original_blocks[0].get("type") == "section":
            question_text = original_blocks[0].get("text", {}).get("text", "")
        try:
            await client.chat_update(
                channel=channel,
                ts=msg_ts,
                text=f"✅ {question_text} — {display}",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": question_text},
                    },
                    {
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"✅ *{display}*"}],
                    },
                ],
            )
        except Exception:
            logger.warning("action_journal_answer: impossible de mettre à jour le message boutons")

    await handle_block_action(
        objectif_id=objectif_id,
        q_index=q_index,
        raw_value=answer_val,
        user_id=user_id,
        channel=channel,
        thread_ts=thread_ts,
    )


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
    "ev-prices",
    "feedback-module",
    "hello-world",
    "homepage",
    "portfolio-tracker",
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
            await slack_client.post_message(
                channel=channel_id,
                text=f"💡 *Feedback {svc['name']}* : {text}",
            )
            await respond(response_type="ephemeral", text="✅ Feedback enregistré. Merci !")
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
    channel_id: str = body.get("channel", {}).get("id", "")
    try:
        await _submit_feedback(project_name, message, "slack://direct")
        await respond(replace_original=True, text=f"✅ Feedback enregistré pour *{project_name}*. Merci !")
        if channel_id:
            await slack_client.post_message(
                channel=channel_id,
                text=f"💡 *Feedback {project_name}* : {message}",
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


# ─── bank-review — import avec question vacances ──────────────────────────────

async def _update_bank_question(client, body, note: str) -> None:
    """Remplace les boutons de la question vacances par une ligne de statut."""
    msg = body.get("message", {})
    channel = body.get("channel", {}).get("id") or body.get("container", {}).get("channel_id")
    ts = msg.get("ts")
    if not channel or not ts:
        return
    blocks = msg.get("blocks", [])
    section = blocks[0] if blocks else {"type": "section", "text": {"type": "mrkdwn", "text": note}}
    try:
        await client.chat_update(
            channel=channel,
            ts=ts,
            text=note,
            blocks=[section, {"type": "context", "elements": [{"type": "mrkdwn", "text": note}]}],
        )
    except Exception:
        logger.warning("bank vacances: chat_update échoué")


# Références aux tâches d'import en cours (évite un GC prématuré des tasks détachées).
_bank_import_tasks: set = set()


def _run_bank_import_bg(payload: dict, vacation_ranges: str) -> None:
    from app.handlers import bank_review as br
    task = asyncio.create_task(
        br.run_import_and_report(
            channel_id=payload["c"],
            filename=payload["f"],
            file_path=payload["p"],
            mime_type=payload["m"],
            uploaded_by=payload["u"],
            vacation_ranges=vacation_ranges,
        )
    )
    _bank_import_tasks.add(task)
    task.add_done_callback(_bank_import_tasks.discard)


@bolt.action("bank_import_novac")
async def action_bank_import_novac(ack, body, client, **_):
    await ack()
    from app.handlers import bank_review as br
    payload = br.decode_payload(body["actions"][0]["value"])
    await _update_bank_question(client, body, ":hourglass_flowing_sand: Import lancé (sans vacances)…")
    _run_bank_import_bg(payload, "")


@bolt.action("bank_import_vac")
async def action_bank_import_vac(ack, body, client, **_):
    await ack()
    from app.handlers import bank_review as br
    value = body["actions"][0]["value"]
    try:
        await client.views_open(trigger_id=body["trigger_id"], view=br.vacation_modal_view(value))
    except Exception:
        logger.exception("bank vacances: views_open échoué")


_agent_decision_tasks: set = set()


async def _run_agent_decision(client, body, action: str, proposal_id: str, user_id: str) -> None:
    """Applique la décision puis réécrit le message : les boutons disparaissent, ce qui rend un
    second clic impossible côté UI — l'idempotence côté base reste la garantie réelle."""
    from app.handlers import agent_approval
    text = await agent_approval.handle_decision(action, proposal_id, user_id)
    try:
        await client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            text=text,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
        )
    except Exception:
        logger.exception("agent_doc: chat_update échoué après décision")


def _dispatch_agent_decision(client, body, action: str) -> None:
    proposal_id = body["actions"][0]["value"]
    user_id = (body.get("user") or {}).get("id")
    task = asyncio.create_task(_run_agent_decision(client, body, action, proposal_id, user_id))
    _agent_decision_tasks.add(task)
    task.add_done_callback(_agent_decision_tasks.discard)


@bolt.action("agent_doc_approve")
async def action_agent_doc_approve(ack, body, client, **_):
    await ack()
    _dispatch_agent_decision(client, body, "approve")


@bolt.action("agent_doc_reject")
async def action_agent_doc_reject(ack, body, client, **_):
    await ack()
    _dispatch_agent_decision(client, body, "reject")


@bolt.action("agent_doc_edit")
async def action_agent_doc_edit(ack, **_):
    # Bouton `url` : Slack ouvre la page lui-même, il faut juste acquitter pour éviter l'alerte.
    await ack()


_agent_tool_tasks: set = set()


async def _run_agent_tool_action(client, body, coro_factory) -> None:
    """Exécute une décision d'outil puis réécrit le message d'origine.

    Réécrire fait disparaître les boutons : un second clic devient impossible côté UI. La
    garantie réelle reste côté base (`resolved_at IS NULL` dans `audit.settle`), l'UI n'en est
    que le reflet.
    """
    try:
        text, blocks = await coro_factory()
    except Exception:
        logger.exception("agent_tools: traitement du clic en échec")
        text, blocks = ":warning: Le traitement de ce clic a échoué.", []
    try:
        await client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            text=text,
            blocks=blocks or [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
        )
    except Exception:
        logger.exception("agent_tools: chat_update échoué après clic")


def _dispatch_agent_tool_action(client, body, coro_factory) -> None:
    task = asyncio.create_task(_run_agent_tool_action(client, body, coro_factory))
    _agent_tool_tasks.add(task)
    task.add_done_callback(_agent_tool_tasks.discard)


@bolt.action("agent_tool_confirm")
async def action_agent_tool_confirm(ack, body, client, **_):
    # Ack immédiat (contrainte Slack des 3 s) : l'exécution part en tâche de fond, comme l'import
    # bancaire. Un outil qui écrit en base peut dépasser les 3 s.
    await ack()
    from app.handlers import agent_tool_actions as ata
    call_id = body["actions"][0]["value"]
    user_id = (body.get("user") or {}).get("id")
    _dispatch_agent_tool_action(client, body, lambda: ata.confirm_pending(call_id, user_id))


@bolt.action("agent_tool_cancel")
async def action_agent_tool_cancel(ack, body, client, **_):
    await ack()
    from app.handlers import agent_tool_actions as ata
    call_id = body["actions"][0]["value"]
    user_id = (body.get("user") or {}).get("id")
    _dispatch_agent_tool_action(client, body, lambda: ata.cancel_pending(call_id, user_id))


@bolt.action("agent_reminder_cancel")
async def action_agent_reminder_cancel(ack, body, client, **_):
    await ack()
    from app.handlers import agent_tool_actions as ata
    card_id = body["actions"][0]["value"]
    user_id = (body.get("user") or {}).get("id")
    _dispatch_agent_tool_action(client, body, lambda: ata.cancel_reminder(card_id, user_id))


@bolt.action("agent_reminder_edit")
async def action_agent_reminder_edit(ack, body, client, **_):
    await ack()
    from app.handlers import agent_tool_actions as ata
    card_id = body["actions"][0]["value"]
    card = await kanban_svc.get_card(card_id)
    if not card:
        return
    try:
        await client.views_open(
            trigger_id=body["trigger_id"],
            view=ata.edit_modal_view(card, body["message"]["ts"], body["channel"]["id"]),
        )
    except Exception:
        logger.exception("agent_reminder_edit: views_open échoué")


@bolt.view("agent_reminder_edit_modal")
async def view_agent_reminder_edit(ack, view, client, **_):
    await ack()
    from app.handlers import agent_tool_actions as ata
    meta = json.loads(view["private_metadata"])
    values = view["state"]["values"]
    text, blocks = await ata.apply_edit(
        meta["card_id"],
        values["title"]["title"]["value"],
        values["date"]["date"]["selected_date"],
        values["time"]["time"]["selected_time"],
    )
    try:
        # On réécrit le message d'origine plutôt que d'en poster un nouveau : le fil garde une
        # seule ligne par rappel, à jour.
        await client.chat_update(
            channel=meta["channel"], ts=meta["ts"], text=text,
            blocks=blocks or [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
        )
    except Exception:
        logger.exception("agent_reminder_edit: chat_update échoué après édition")


@bolt.view("bank_vac_modal")
async def view_bank_vac_modal(ack, body, view, **_):
    from app.handlers import bank_review as br
    vacation_ranges, errors = br.parse_modal_vacations(view)
    if errors:
        await ack(response_action="errors", errors=errors)
        return
    await ack()
    payload = br.decode_payload(view["private_metadata"])
    _run_bank_import_bg(payload, vacation_ranges)


