from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/upload", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, password: str = Form(...)):
    expected = os.getenv("APP_PASSWORD", "bank2024")
    if password == expected:
        request.session["authenticated"] = True
        return RedirectResponse("/upload", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Mot de passe incorrect."})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
