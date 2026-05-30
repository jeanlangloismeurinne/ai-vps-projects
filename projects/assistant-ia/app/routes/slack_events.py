from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from fastapi import APIRouter, Request

from app.slack_app import bolt

handler = AsyncSlackRequestHandler(bolt)
router = APIRouter()


@router.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)
