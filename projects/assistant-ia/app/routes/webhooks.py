import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app.handlers import bank_review as bank_review_handler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/file-stored")
async def file_stored(request: Request, background_tasks: BackgroundTasks):
    """Reçoit la notification de tool-file-intake quand un fichier est stocké."""
    payload = await request.json()
    if payload.get("event") != "file_stored":
        return JSONResponse({"ok": True})
    background_tasks.add_task(bank_review_handler.handle_file_stored, payload)
    return JSONResponse({"ok": True})
