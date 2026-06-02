import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from adapters.slack import create_slack_app
from config import settings
from services.indexer import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

slack_app = create_slack_app()
slack_handler = AsyncSlackRequestHandler(slack_app)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Base de données initialisée")
    logger.info("Slack HTTP Events API prête sur /slack/events")
    yield


app = FastAPI(title="tool-file-intake", lifespan=lifespan)


@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
