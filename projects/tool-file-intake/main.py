import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from adapters.slack import create_slack_app
from config import settings
from services.indexer import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

slack_app = create_slack_app()
_socket_handler: AsyncSocketModeHandler | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _socket_handler
    init_db()
    logger.info("Base de données initialisée")

    _socket_handler = AsyncSocketModeHandler(slack_app, settings.SLACK_APP_TOKEN)
    asyncio.create_task(_socket_handler.start_async())
    logger.info("Socket Mode Slack démarré")

    yield

    if _socket_handler:
        await _socket_handler.close_async()


app = FastAPI(title="tool-file-intake", lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
