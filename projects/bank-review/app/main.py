from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

from app.routes import auth, upload, analyze
from app.routes import import_route

load_dotenv()

app = FastAPI(title="Bank Review", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    max_age=3600 * 8,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(analyze.router, prefix="/api")
app.include_router(import_route.router)
