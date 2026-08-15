import bcrypt
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from app.services.database import get_user_by_username, db_url_for_user

router = APIRouter()


def is_authenticated(request: Request) -> bool:
    return request.session.get("user_id") is not None


def is_admin(request: Request) -> bool:
    return request.session.get("is_admin") is True


@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/upload", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await get_user_by_username(username.strip().lower())
    if user:
        try:
            valid = bcrypt.checkpw(password.encode(), user["password_hash"].encode())
        except Exception:
            valid = False
        if valid:
            request.session["user_id"] = user["id"]
            request.session["username"] = user["username"]
            request.session["db_url"] = db_url_for_user(user["db_name"])
            request.session["is_admin"] = user["is_admin"]
            return RedirectResponse("/upload", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": "Identifiants incorrects."})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
