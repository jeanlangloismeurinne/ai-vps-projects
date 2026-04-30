import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
app.include_router(api_router)
app.include_router(pages_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
