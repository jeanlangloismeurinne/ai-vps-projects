"""
Adaptateur Slack Bolt : gestion des événements fichiers, actions Block Kit et modals.

Flux :
  1. message avec fichier → proposition de chemin (Block Kit)
  2. bouton "Confirmer"   → stockage immédiat
  3. bouton "Autre dossier" → modal avec arborescence + saisie chemin
  4. soumission modal     → stockage dans le chemin choisi
  5. confirmation Slack   + notification agent IA
"""
import json
import logging
from pathlib import Path

import httpx
from slack_bolt.async_app import AsyncApp

from config import settings
from services import explorer, indexer, storage
from utils.tree_formatter import format_tree

logger = logging.getLogger(__name__)


def create_slack_app() -> AsyncApp:
    # Socket Mode : pas de signing secret — la connexion est initiée par nous via WebSocket
    app = AsyncApp(token=settings.SLACK_BOT_TOKEN)

    # ── Événement : fichier partagé dans un message ──────────────────────────

    @app.event("message")
    async def on_message_with_file(event, client, say, ack):
        files = event.get("files") or []
        if not files:
            return

        for file_info in files:
            await _propose_storage(file_info, event, say)

    # ── Action : confirmer le chemin suggéré ─────────────────────────────────

    @app.action("confirm_storage")
    async def on_confirm(ack, body, client, respond):
        await ack()
        meta = json.loads(body["actions"][0]["value"])
        await _do_store(meta, meta["suggested_path"], client, respond, body)

    # ── Action : ouvrir le modal de sélection de dossier ─────────────────────

    @app.action("choose_folder")
    async def on_choose_folder(ack, body, client):
        await ack()
        meta = json.loads(body["actions"][0]["value"])
        trigger_id = body["trigger_id"]

        tree_text = format_tree()
        await client.views_open(
            trigger_id=trigger_id,
            view=_build_folder_modal(meta, tree_text),
        )

    # ── Soumission du modal ───────────────────────────────────────────────────

    @app.view("folder_selection")
    async def on_folder_submit(ack, body, client, view):
        await ack()
        meta = json.loads(view["private_metadata"])
        chosen = view["state"]["values"]["folder_input"]["folder_path"]["value"].strip()

        channel = meta.get("channel")
        user = meta.get("user_id")

        try:
            path = storage.safe_join(settings.STORAGE_BASE, chosen)
        except ValueError as e:
            if channel:
                await client.chat_postMessage(
                    channel=channel,
                    text=f":warning: <@{user}> Chemin invalide : {e}",
                )
            return

        await _do_store(meta, chosen, client, None, body, channel=channel)

    return app


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _propose_storage(file_info: dict, event: dict, say) -> None:
    filename = file_info.get("name", "fichier")
    file_id = file_info.get("id")
    mime_type = file_info.get("mimetype", "")
    file_size = file_info.get("size", 0)
    user_id = event.get("user", "")
    channel = event.get("channel", "")
    suggested = storage.default_relative_path()

    size_mb = file_size / 1024 / 1024
    size_str = f"{size_mb:.1f} Mo" if size_mb >= 0.1 else f"{file_size} octets"

    meta = {
        "file_id": file_id,
        "filename": filename,
        "mime_type": mime_type,
        "file_size": file_size,
        "user_id": user_id,
        "channel": channel,
        "suggested_path": suggested,
    }

    await say(
        blocks=_build_proposal_blocks(filename, size_str, mime_type, suggested, meta),
        text=f"Fichier reçu : {filename}",
    )


async def _do_store(
    meta: dict,
    relative_path: str,
    client,
    respond,
    body: dict,
    channel: str | None = None,
) -> None:
    file_id = meta["file_id"]
    filename = meta["filename"]
    mime_type = meta["mime_type"]
    user_id = meta["user_id"]
    dest_channel = channel or meta.get("channel")

    # Téléchargement
    try:
        content = await _download_slack_file(file_id, client)
    except Exception as e:
        logger.error("Erreur téléchargement %s : %s", file_id, e)
        msg = f":x: Impossible de télécharger `{filename}` : {e}"
        if respond:
            await respond(text=msg, replace_original=True)
        elif dest_channel:
            await client.chat_postMessage(channel=dest_channel, text=msg)
        return

    # Validation
    try:
        storage.validate_file(filename, content, mime_type)
    except ValueError as e:
        msg = f":x: Fichier refusé : {e}"
        if respond:
            await respond(text=msg, replace_original=True)
        elif dest_channel:
            await client.chat_postMessage(channel=dest_channel, text=msg)
        return

    sha = storage.compute_sha256(content)

    # Déduplication
    existing = indexer.find_by_sha256(sha)
    if existing:
        tree_text = format_tree()
        msg = (
            f":information_source: Ce fichier existe déjà : `{existing.stored_path}`\n"
            f"Aucun doublon créé.\n\n```{tree_text}```"
        )
        if respond:
            await respond(text=msg, replace_original=True)
        elif dest_channel:
            await client.chat_postMessage(channel=dest_channel, text=msg)
        return

    # Stockage
    try:
        dest_path = storage.store_file(content, filename, relative_path)
    except Exception as e:
        logger.error("Erreur stockage : %s", e)
        msg = f":x: Erreur lors du stockage : {e}"
        if respond:
            await respond(text=msg, replace_original=True)
        elif dest_channel:
            await client.chat_postMessage(channel=dest_channel, text=msg)
        return

    # Index BDD
    indexer.create_record(
        slack_file_id=file_id,
        original_name=filename,
        stored_path=str(dest_path),
        sha256=sha,
        mime_type=mime_type,
        file_size=len(content),
        uploaded_by=user_id,
    )

    # Confirmation Slack
    tree_text = format_tree()
    confirm_msg = (
        f":white_check_mark: *`{filename}`* stocké dans\n"
        f"`{dest_path.relative_to(settings.STORAGE_BASE.parent)}`\n\n"
        f"*Arborescence Documents :*\n```{tree_text}```"
    )
    if respond:
        await respond(text=confirm_msg, replace_original=True)
    elif dest_channel:
        await client.chat_postMessage(channel=dest_channel, text=confirm_msg)

    # Notification agent IA
    if settings.AGENT_WEBHOOK_URL:
        await _notify_agent(filename, str(dest_path), mime_type, sha, user_id)


async def _download_slack_file(file_id: str, client) -> bytes:
    info = await client.files_info(file=file_id)
    url = info["file"]["url_private_download"]
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(url, headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"})
        resp.raise_for_status()
        return resp.content


async def _notify_agent(filename: str, path: str, mime: str, sha256: str, user: str) -> None:
    payload = {
        "event": "file_stored",
        "filename": filename,
        "path": path,
        "mime_type": mime,
        "sha256": sha256,
        "uploaded_by": user,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            await http.post(settings.AGENT_WEBHOOK_URL, json=payload)
    except Exception as e:
        logger.warning("Notification agent échouée : %s", e)


# ── Constructeurs Block Kit ───────────────────────────────────────────────────


def _build_proposal_blocks(
    filename: str, size_str: str, mime_type: str, suggested: str, meta: dict
) -> list:
    meta_json = json.dumps(meta)
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":inbox_tray: *Fichier reçu*\n"
                    f"• Nom : `{filename}`\n"
                    f"• Type : `{mime_type}`\n"
                    f"• Taille : {size_str}\n\n"
                    f"Proposition de destination :\n"
                    f"`Documents/{suggested}/`"
                ),
            },
        },
        {
            "type": "actions",
            "block_id": "file_action",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Confirmer"},
                    "style": "primary",
                    "action_id": "confirm_storage",
                    "value": meta_json,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📁 Choisir un autre dossier"},
                    "action_id": "choose_folder",
                    "value": meta_json,
                },
            ],
        },
    ]


def _build_folder_modal(meta: dict, tree_text: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "folder_selection",
        "private_metadata": json.dumps(meta),
        "title": {"type": "plain_text", "text": "Choisir un dossier"},
        "submit": {"type": "plain_text", "text": "Stocker"},
        "close": {"type": "plain_text", "text": "Annuler"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Arborescence actuelle :*\n```{tree_text}```",
                },
            },
            {
                "type": "input",
                "block_id": "folder_input",
                "label": {"type": "plain_text", "text": "Chemin de destination"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "folder_path",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "ex: 2026/04/projets-clients",
                    },
                    "initial_value": meta.get("suggested_path", ""),
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Chemin relatif à Documents/ — les sous-dossiers sont créés automatiquement.",
                },
            },
        ],
    }
