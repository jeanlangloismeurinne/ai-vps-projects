import logging
from fastapi import FastAPI
from app.routes import webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="assistant-ia", docs_url=None, redoc_url=None)
app.include_router(webhooks.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
