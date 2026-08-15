import os
import re
import bcrypt
import asyncpg
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates
from app.routes.auth import is_authenticated, is_admin
from app.services.database import (
    get_all_users, create_user_record, run_all_migrations,
    db_url_for_user, _dsn,
)

router = APIRouter()


def _require_admin(request: Request):
    return is_authenticated(request) and is_admin(request)


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    if not _require_admin(request):
        return RedirectResponse("/", status_code=302)
    users = await get_all_users()
    return templates.TemplateResponse(request, "admin_users.html", {
        "users": users, "error": None, "success": None,
    })


@router.post("/admin/users", response_class=HTMLResponse)
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    if not _require_admin(request):
        return RedirectResponse("/", status_code=302)

    users = await get_all_users()

    def _err(msg):
        return templates.TemplateResponse(request, "admin_users.html", {
            "users": users, "error": msg, "success": None,
        })

    username = username.strip().lower()
    if not re.match(r"^[a-z0-9_]{2,30}$", username):
        return _err("Identifiant invalide — lettres minuscules, chiffres et _ uniquement (2–30 caractères).")
    if any(u["username"] == username for u in users):
        return _err(f"L'identifiant « {username} » existe déjà.")
    if password != password_confirm:
        return _err("Les mots de passe ne correspondent pas.")
    if len(password) < 6:
        return _err("Mot de passe trop court (6 caractères minimum).")

    db_name = f"db_bank_{username}"
    db_url = db_url_for_user(db_name)

    # Create the PostgreSQL database as admin
    admin_url = os.getenv("POSTGRES_ADMIN_URL")
    if not admin_url:
        return _err("POSTGRES_ADMIN_URL non configuré — impossible de créer la base de données.")

    bank_user = _dsn().split("//")[1].split(":")[0]
    try:
        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            await conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{bank_user}"')
        except asyncpg.DuplicateDatabaseError:
            pass  # DB already exists — continue
        finally:
            await conn.close()
    except Exception as e:
        return _err(f"Erreur lors de la création de la base de données : {e}")

    # Grant schema-level CREATE in the new DB (requires admin connection to that specific DB)
    admin_new_db_url = admin_url.rsplit("/", 1)[0] + "/" + db_name
    try:
        admin_conn = await asyncpg.connect(admin_new_db_url)
        try:
            await admin_conn.execute(f'GRANT CREATE ON SCHEMA public TO "{bank_user}"')
            await admin_conn.execute(f'GRANT ALL ON SCHEMA public TO "{bank_user}"')
            await admin_conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{bank_user}"')
            await admin_conn.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{bank_user}"')
        finally:
            await admin_conn.close()
    except Exception as e:
        return _err(f"Erreur lors de la configuration des droits schema : {e}")

    # Run all table migrations in the new DB
    try:
        await run_all_migrations(db_url)
    except Exception as e:
        return _err(f"Erreur lors de l'initialisation de la base de données : {e}")

    # Create user record in central DB
    pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    await create_user_record(username, pwd_hash, db_name, is_admin=False)

    users = await get_all_users()
    return templates.TemplateResponse(request, "admin_users.html", {
        "users": users,
        "error": None,
        "success": f"Compte « {username} » créé avec succès.",
    })
