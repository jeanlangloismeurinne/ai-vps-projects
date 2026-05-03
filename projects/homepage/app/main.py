import secrets as _secrets
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic_settings import BaseSettings
from app.auth import (
    COOKIE_NAME, COOKIE_MAX_AGE,
    make_cookie_value, get_session, redirect_to_login,
)


class Settings(BaseSettings):
    WEB_USERNAME: str
    WEB_PASSWORD: str
    SESSION_SECRET: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(docs_url=None, redoc_url=None)

# ── Services ──────────────────────────────────────────────────────────────────
SERVICES = [
    {
        "id": "assistant",
        "emoji": "🤖",
        "name": "Assistant IA",
        "desc": "Journal quotidien · Kanban · Commandes Slack",
        "url": "https://assistant.jlmvpscode.duckdns.org/",
        "color": "#4f6ef7",
    },
    {
        "id": "bank",
        "emoji": "🏦",
        "name": "Bank Review",
        "desc": "Analyse de relevés bancaires · Suivi budget",
        "url": "https://bank.jlmvpscode.duckdns.org/",
        "color": "#2da862",
    },
    {
        "id": "ev-prices",
        "emoji": "⚡",
        "name": "EV Prices",
        "desc": "Suivi des prix véhicules électriques · 14 constructeurs",
        "url": "https://ev.jlmvpscode.duckdns.org/",
        "color": "#f59e0b",
    },
    {
        "id": "portfolio",
        "emoji": "📈",
        "name": "Portfolio Tracker",
        "desc": "Suivi investissement long terme · Agents IA · 3 régimes d'analyse",
        "url": "https://portfolio.jlmvpscode.duckdns.org/",
        "color": "#7c3aed",
    },
]

# ── Templates ─────────────────────────────────────────────────────────────────

def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f1117; color: #e8e8ea; min-height: 100vh; }}
  a {{ color: inherit; text-decoration: none; }}
</style>
</head>
<body>{body}</body>
</html>"""


def _login_page(error: str = "") -> str:
    err = f'<p class="error">{error}</p>' if error else ""
    return _base("Connexion", f"""
<style>
  .wrap {{ display:flex; align-items:center; justify-content:center; min-height:100vh; padding:1rem; }}
  .card {{ background:#1a1d27; border:1px solid #2a2d3a; border-radius:16px; padding:2.5rem 2rem; width:100%; max-width:360px; }}
  h1 {{ font-size:1.5rem; text-align:center; margin-bottom:2rem; }}
  .field {{ margin-bottom:1rem; }}
  label {{ display:block; font-size:.8rem; color:#888; margin-bottom:.4rem; letter-spacing:.05em; text-transform:uppercase; }}
  input {{ width:100%; background:#0f1117; border:1px solid #2a2d3a; border-radius:8px; padding:.7rem 1rem;
           color:#e8e8ea; font-size:.95rem; outline:none; }}
  input:focus {{ border-color:#4f6ef7; }}
  button {{ width:100%; background:#4f6ef7; color:#fff; border:none; border-radius:8px;
             padding:.8rem; font-size:1rem; font-weight:600; cursor:pointer; margin-top:.5rem; }}
  button:hover {{ background:#3a57d4; }}
  .error {{ color:#ff6b6b; font-size:.85rem; text-align:center; margin-bottom:1rem; }}
</style>
<div class="wrap">
  <div class="card">
    <h1>🔐 Connexion</h1>
    {err}
    <form method="POST" action="/login">
      <input type="hidden" name="next" id="next-field">
      <div class="field">
        <label>Identifiant</label>
        <input type="text" name="username" autofocus autocomplete="username">
      </div>
      <div class="field">
        <label>Mot de passe</label>
        <input type="password" name="password" autocomplete="current-password">
      </div>
      <button type="submit">Se connecter</button>
    </form>
  </div>
</div>
<script>
  const p = new URLSearchParams(location.search);
  if (p.get('next')) document.getElementById('next-field').value = p.get('next');
</script>""")


def _homepage() -> str:
    cards = ""
    for s in SERVICES:
        cards += f"""
        <a href="{s['url']}" class="card" style="--accent:{s['color']}">
          <div class="icon">{s['emoji']}</div>
          <div class="info">
            <div class="name">{s['name']}</div>
            <div class="desc">{s['desc']}</div>
          </div>
          <div class="arrow">→</div>
        </a>"""

    return _base("Hub — JLM VPS", f"""
<style>
  header {{ padding:2rem 1.5rem 1rem; border-bottom:1px solid #1e2130; }}
  header h1 {{ font-size:1.1rem; font-weight:600; color:#aaa; }}
  header .logout {{ float:right; color:#555; font-size:.85rem; }}
  header .logout:hover {{ color:#e8e8ea; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
           gap:1rem; padding:2rem 1.5rem; max-width:900px; margin:0 auto; }}
  .card {{ display:flex; align-items:center; gap:1rem; background:#1a1d27;
           border:1px solid #2a2d3a; border-radius:14px; padding:1.25rem 1.5rem;
           transition:border-color .2s, transform .15s; cursor:pointer;
           border-top:3px solid var(--accent); }}
  .card:hover {{ border-color:var(--accent); transform:translateY(-2px); }}
  .icon {{ font-size:2.2rem; flex-shrink:0; }}
  .info {{ flex:1; }}
  .name {{ font-size:1rem; font-weight:600; margin-bottom:.2rem; }}
  .desc {{ font-size:.8rem; color:#888; }}
  .arrow {{ color:#444; font-size:1.2rem; transition:color .2s; }}
  .card:hover .arrow {{ color:var(--accent); }}
</style>
<header>
  <h1>JLM VPS</h1>
  <a href="/logout" class="logout">Déconnexion</a>
</header>
<div class="grid">{cards}</div>""")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if not get_session(request, settings.SESSION_SECRET):
        return redirect_to_login()
    return HTMLResponse(_homepage())


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if get_session(request, settings.SESSION_SECRET):
        return RedirectResponse("/", 302)
    return HTMLResponse(_login_page())


@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default=""),
):
    ok_user = _secrets.compare_digest(username, settings.WEB_USERNAME)
    ok_pass = _secrets.compare_digest(password, settings.WEB_PASSWORD)
    if not (ok_user and ok_pass):
        return HTMLResponse(_login_page("Identifiant ou mot de passe incorrect."), status_code=401)

    token = make_cookie_value(username, settings.SESSION_SECRET)
    dest = next or "/"
    response = RedirectResponse(dest, status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        domain=".jlmvpscode.duckdns.org",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(COOKIE_NAME, domain=".jlmvpscode.duckdns.org")
    return response
