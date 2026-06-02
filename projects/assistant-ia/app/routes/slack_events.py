import json
import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from app.slack_app import bolt

logger = logging.getLogger(__name__)

handler = AsyncSlackRequestHandler(bolt)
router = APIRouter()

_FILE_INTAKE_URL = "http://tool-file-intake:8000/slack/events"
_FILE_ACTIONS = {"confirm_storage", "choose_folder"}


def _is_file_related(data: dict) -> bool:
    payload_type = data.get("type", "")
    if payload_type == "event_callback":
        event = data.get("event", {})
        return bool(event.get("files")) or event.get("subtype") == "file_share"
    if payload_type == "block_actions":
        return any(a.get("action_id") in _FILE_ACTIONS for a in data.get("actions", []))
    if payload_type == "view_submission":
        return data.get("view", {}).get("callback_id") == "folder_selection"
    return False


@router.post("/slack/events")
async def slack_events(req: Request):
    body = await req.body()

    try:
        data = json.loads(body)
    except Exception:
        return await handler.handle(req)

    if data.get("type") == "url_verification":
        return await handler.handle(req)

    if _is_file_related(data):
        logger.debug("Proxy fichier → tool-file-intake")
        headers = {k: v for k, v in req.headers.items() if k.lower() not in ("host", "content-length")}
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.post(_FILE_INTAKE_URL, content=body, headers=headers)
                return Response(content=resp.content, status_code=resp.status_code)
        except Exception as e:
            logger.warning("Proxy tool-file-intake échoué : %s", e)
            return Response(status_code=200)

    return await handler.handle(req)
