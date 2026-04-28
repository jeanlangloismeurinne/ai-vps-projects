import logging
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.routes.auth import require_auth
from app.services import journal as journal_svc
from app.services import journal_v2 as svc_v2

logger = logging.getLogger(__name__)
router = APIRouter()

_CSS = """
:root{--bg:#0f1117;--card:#1a1d27;--border:#1e2130;--text:#e8e8ea;--muted:#888;
      --accent:#4f6ef7;--success:#2da862;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
header{padding:1rem 2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
header h1{font-size:1.1rem;font-weight:600;}
nav{display:flex;gap:1.5rem;font-size:.9rem;}
nav a{color:var(--muted);text-decoration:none;}
nav a:hover{color:var(--text);}
main{max-width:760px;margin:0 auto;padding:2rem 1.5rem;}
h2{font-size:1.3rem;font-weight:700;margin-bottom:1.5rem;}
h3{font-size:.85rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:.75rem;}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1rem;}
.actions{display:flex;gap:.75rem;margin-bottom:2rem;flex-wrap:wrap;}
.btn{display:inline-flex;align-items:center;gap:.35rem;padding:.55rem 1.1rem;border-radius:8px;
     font-size:.9rem;font-weight:500;cursor:pointer;border:none;text-decoration:none;font-family:inherit;}
.btn-primary{background:var(--accent);color:#fff;}
.btn-primary:hover{background:#3d5de0;}
.btn-ghost{background:var(--card);border:1px solid var(--border);color:var(--text);}
.btn-ghost:hover{background:#22253a;}
.flex-between{display:flex;align-items:center;justify-content:space-between;gap:1rem;}
.badge{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.72rem;font-weight:500;}
.badge-done{background:#0d2a1a;color:var(--success);border:1px solid #1a4a2a;}
.badge-pending{background:#1a1d27;color:var(--muted);border:1px solid var(--border);}
.progress-bar{height:4px;background:var(--border);border-radius:2px;margin-bottom:1.5rem;}
.progress-fill{height:100%;background:var(--accent);border-radius:2px;}
.empty{text-align:center;color:var(--muted);padding:2rem;font-style:italic;}
.entry time{font-size:.8rem;color:var(--muted);display:block;margin-bottom:.3rem;}
.entry p{font-size:.9rem;line-height:1.6;white-space:pre-wrap;color:#ccc;}
hr{border:none;border-top:1px solid var(--border);margin:2rem 0;}
details summary{cursor:pointer;color:var(--muted);font-size:.85rem;}
details[open] summary{margin-bottom:1rem;}
"""


@router.get("/journal", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def journal_page():
    today = date.today()
    due = await svc_v2.get_due_objectifs_today()

    # Calcul progression du jour
    total = len(due)
    done_count = 0
    objectif_cards = ""
    for o in due:
        done = await svc_v2.is_objectif_complete(str(o["id"]), today)
        if done:
            done_count += 1
        status_cls = "badge-done" if done else "badge-pending"
        status_lbl = "Complété" if done else "À remplir"
        parcours_nom = o.get("parcours_nom", "")
        btn = (
            f'<a href="/journal/fill/{o["id"]}" class="btn btn-ghost" style="font-size:.82rem;padding:.3rem .7rem">Revoir</a>'
            if done else
            f'<a href="/journal/fill/{o["id"]}" class="btn btn-primary" style="font-size:.82rem;padding:.3rem .7rem">Remplir →</a>'
        )
        objectif_cards += f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:.65rem 0;border-bottom:1px solid var(--border);gap:1rem">
          <div>
            <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.15rem">
              <span style="font-size:.92rem">{o['nom']}</span>
              <span class="badge {status_cls}">{status_lbl}</span>
            </div>
            <div style="font-size:.78rem;color:var(--muted)">{parcours_nom}</div>
          </div>
          {btn}
        </div>"""

    if not objectif_cards:
        objectif_cards = '<p class="empty" style="padding:1.5rem">Aucun objectif aujourd\'hui — <a href="/journal/settings" style="color:var(--accent)">configurer les parcours</a></p>'

    pct = int(done_count / total * 100) if total else 0
    progress_bar = f"""
    <div style="margin-bottom:1rem">
      <div style="display:flex;justify-content:space-between;font-size:.8rem;color:var(--muted);margin-bottom:.35rem">
        <span>{done_count}/{total} objectif(s) complété(s) aujourd'hui</span>
        <span style="color:var(--accent)">{pct}%</span>
      </div>
      <div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>
    </div>""" if total else ""

    date_str = today.strftime("%A %d %B %Y").capitalize()

    # Journal libre Slack (archive)
    entries = await journal_svc.get_all_entries()
    slack_rows = ""
    for e in entries:
        dt = e["created_at"].strftime("%d/%m/%Y %H:%M")
        content = e["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        slack_rows += f'<div class="entry" style="margin-bottom:1rem"><time>{dt}</time><p>{content}</p></div>'
    if not slack_rows:
        slack_rows = '<p style="color:var(--muted);font-size:.85rem;font-style:italic">Aucune entrée Slack.</p>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Journal — Assistant IA</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>📔 Journal</h1>
  <nav>
    <a href="/journal/fill">Remplir</a>
    <a href="/journal/history">Historique</a>
    <a href="/journal/settings">Paramètres</a>
    <a href="/">Hub</a>
  </nav>
</header>
<main>
  <h2>📅 {date_str}</h2>

  <div class="actions">
    <a href="/journal/fill" class="btn btn-primary">Remplir le journal →</a>
    <a href="/journal/history" class="btn btn-ghost">Historique</a>
    <a href="/journal/settings" class="btn btn-ghost">Paramètres</a>
  </div>

  <div class="card">
    <h3>Aujourd'hui</h3>
    {progress_bar}
    {objectif_cards}
  </div>

  <hr>

  <details>
    <summary>Journal libre Slack ({len(entries)} entrée(s))</summary>
    <div style="margin-top:1rem">{slack_rows}</div>
  </details>
</main>
<script src="/public/feedback-widget.js" data-api="" data-project="journal" defer></script>
</body>
</html>"""
    return HTMLResponse(content=html)
