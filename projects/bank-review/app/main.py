from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

from app.routes import auth, analyze
from app.routes import import_route
from app.routes import budget as budget_route
from app.routes import feedback as feedback_route

load_dotenv()

app = FastAPI(title="Bank Review", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    max_age=3600 * 8,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 global helpers
_templates = Jinja2Templates(directory="app/templates")

def _m_status(m: dict, is_income: bool) -> str:
    if m.get("is_future") or m.get("actual", 0) == 0:
        return ""
    v = m.get("variance", 0)
    if v >= 0:
        return "cell-green"
    if v >= -m.get("budget", 1) * 0.2:
        return "cell-yellow"
    return "cell-red"

_templates.env.globals["m_status"] = _m_status

app.include_router(auth.router)
app.include_router(analyze.router, prefix="/api")
app.include_router(import_route.router)
app.include_router(budget_route.router)
app.include_router(feedback_route.router)
