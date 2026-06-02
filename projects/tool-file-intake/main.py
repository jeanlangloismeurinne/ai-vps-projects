import json
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from adapters.slack import create_slack_app
from config import settings
from services.indexer import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

_ASSISTANT_IA_URL = "http://assistant-ia:8000/slack/events"
_FILE_ACTIONS = {"confirm_storage", "choose_folder"}

slack_app = create_slack_app()
slack_handler = AsyncSlackRequestHandler(slack_app)


def _is_file_related(data: dict) -> bool:
    """Returns True for events/actions owned by this service (file intake)."""
    payload_type = data.get("type", "")
    if payload_type == "event_callback":
        event = data.get("event", {})
        return bool(event.get("files")) or event.get("subtype") == "file_share"
    if payload_type == "block_actions":
        return any(a.get("action_id") in _FILE_ACTIONS for a in data.get("actions", []))
    if payload_type == "view_submission":
        return data.get("view", {}).get("callback_id") == "folder_selection"
    return False


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Base de données initialisée")
    logger.info("Slack HTTP Events API prête sur /slack/events")
    yield


app = FastAPI(title="tool-file-intake", lifespan=lifespan)


@app.post("/slack/events")
async def slack_events(req: Request):
    body = await req.body()

    try:
        data = json.loads(body)
    except Exception:
        return await slack_handler.handle(req)

    # URL verification challenge (Slack setup)
    if data.get("type") == "url_verification":
        return await slack_handler.handle(req)

    if _is_file_related(data):
        logger.info("Événement fichier — traitement local")
        return await slack_handler.handle(req)

    # Tout le reste (journal, slash commands, kanban) → assistant-ia
    logger.debug("Proxy → assistant-ia : type=%s", data.get("type"))
    headers = {k: v for k, v in req.headers.items() if k.lower() not in ("host", "content-length")}
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(_ASSISTANT_IA_URL, content=body, headers=headers)
            return Response(content=resp.content, status_code=resp.status_code)
    except Exception as e:
        logger.warning("Proxy assistant-ia échoué : %s", e)
        return Response(status_code=200)  # toujours acquitter Slack


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
