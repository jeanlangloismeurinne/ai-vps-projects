from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import os
import bcrypt

from app.routes import auth, analyze
from app.routes import upload as upload_route
from app.routes import import_route
from app.routes import budget as budget_route
from app.routes import feedback as feedback_route
from app.routes import admin as admin_route

load_dotenv()

app = FastAPI(title="Bank Review", docs_url="/api/docs", redoc_url="/api/redoc")


class DBURLMiddleware(BaseHTTPMiddleware):
    """Inject the current user's db_url into the asyncpg contextvar for each request."""
    async def dispatch(self, request: Request, call_next):
        from app.services.database import set_current_db_url, reset_db_url, _dsn
        db_url = request.session.get("db_url") or _dsn()
        token = set_current_db_url(db_url)
        try:
            response = await call_next(request)
        finally:
            reset_db_url(token)
        return response


# Order matters: SessionMiddleware wraps DBURLMiddleware so session is available first.
app.add_middleware(DBURLMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    max_age=3600 * 8,
)


@app.on_event("startup")
async def startup():
    from app.services.database import (
        migrate_classifier_tables, create_users_table,
        user_exists, create_user_record, db_url_for_user,
    )

    # Ensure users table exists (central DB)
    await create_users_table()

    # Seed first admin user (Jean) if no users exist
    if not await user_exists():
        first_name = os.getenv("FIRST_USER_NAME", "jean")
        first_pwd = os.getenv("APP_PASSWORD", "bank2024")
        pwd_hash = bcrypt.hashpw(first_pwd.encode(), bcrypt.gensalt()).decode()
        # Jean's data is already in db_bank — use central DB as his DB
        from app.services.database import _dsn
        import re
        db_name = re.search(r"/([^/]+)$", _dsn()).group(1)
        await create_user_record(first_name, pwd_hash, db_name, is_admin=True)

    # Run business table migrations for the central DB (Jean's DB)
    await migrate_classifier_tables()


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
app.include_router(upload_route.router)
app.include_router(analyze.router, prefix="/api")
app.include_router(import_route.router)
app.include_router(budget_route.router)
app.include_router(feedback_route.router)
app.include_router(admin_route.router)
