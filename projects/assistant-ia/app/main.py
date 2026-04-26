import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from pathlib import Path

from app.routes import webhooks, journal, kanban, feedback as feedback_route
from app.routes.auth import HubAuthRequired, require_auth, LOGIN_URL
from app.db import close_pool, run_migrations
from app.jobs.journal_prompt import send_daily_prompt, send_reminder
from app.jobs.task_reminder import check_due_cards
from app import slack_app as slack

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

_paris = pytz.timezone("Europe/Paris")
_scheduler = AsyncIOScheduler(timezone=pytz.UTC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()

    _scheduler.add_job(send_daily_prompt, CronTrigger(hour=19, minute=0, timezone=_paris))
    _scheduler.add_job(send_reminder, CronTrigger(hour=22, minute=0, timezone=_paris))
    _scheduler.add_job(check_due_cards, CronTrigger(minute="*"))
    _scheduler.start()
    logger.info("Scheduler started")

    slack_task = asyncio.create_task(slack.start())
    logger.info("Slack Socket Mode started")

    yield

    slack_task.cancel()
    await slack.stop()
    _scheduler.shutdown()
    await close_pool()


app = FastAPI(title="assistant-ia", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.exception_handler(HubAuthRequired)
async def hub_auth_handler(request: Request, exc: HubAuthRequired):
    url = f"{LOGIN_URL}?next={exc.next_url}" if exc.next_url else LOGIN_URL
    return RedirectResponse(url, status_code=302)


_public = Path(__file__).parent.parent / "public"
if _public.exists():
    app.mount("/public", StaticFiles(directory=str(_public)), name="public")

app.include_router(webhooks.router)
app.include_router(journal.router)
app.include_router(kanban.router)
app.include_router(feedback_route.router)


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def landing():
    return HTMLResponse(_LANDING_HTML)


@app.get("/health")
async def health():
    return {"status": "ok"}


_LANDING_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assistant IA</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f1117; color: #e8e8ea; }
  a { color: #4f6ef7; text-decoration: none; }
  a:hover { text-decoration: underline; }

  header { padding: 1.5rem 2rem; border-bottom: 1px solid #1e2130; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  .hub-link { font-size: .85rem; color: #555; }
  .hub-link:hover { color: #e8e8ea; }

  main { max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem; }

  .hero { margin-bottom: 3rem; }
  .hero h2 { font-size: 2rem; font-weight: 700; margin-bottom: .5rem; }
  .hero p { color: #888; font-size: 1rem; }

  .section { margin-bottom: 2.5rem; }
  .section-header { display: flex; align-items: center; gap: .75rem; margin-bottom: 1.25rem; }
  .section-header .badge { font-size: 1.5rem; }
  .section-header h3 { font-size: 1.1rem; font-weight: 600; }
  .section-header .link-btn { margin-left: auto; background: #1e2130; border: 1px solid #2a2d3a;
    color: #e8e8ea; padding: .4rem .9rem; border-radius: 8px; font-size: .85rem; white-space: nowrap; }
  .section-header .link-btn:hover { background: #2a2d3a; text-decoration: none; }

  .desc { color: #999; font-size: .9rem; line-height: 1.6; margin-bottom: 1rem; }

  table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  th { text-align: left; color: #666; font-weight: 500; padding: .5rem .75rem; border-bottom: 1px solid #1e2130; }
  td { padding: .55rem .75rem; border-bottom: 1px solid #1a1d27; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  code { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 5px;
         padding: .15rem .45rem; font-family: monospace; font-size: .85rem; color: #c8d0f0; white-space: nowrap; }
  .note { background: #1a1d27; border-left: 3px solid #4f6ef7; border-radius: 0 8px 8px 0;
          padding: .75rem 1rem; font-size: .85rem; color: #888; margin-top: .75rem; }
</style>
</head>
<body>
<header>
  <h1>🤖 Assistant IA</h1>
  <a href="https://jlmvpscode.duckdns.org/" class="hub-link">← Hub</a>
</header>
<main>

  <div class="hero">
    <h2>Ton assistant personnel</h2>
    <p>Journal quotidien d'apprentissage et gestion de tâches Kanban, accessibles depuis Slack et le web.</p>
  </div>

  <!-- Journal -->
  <div class="section">
    <div class="section-header">
      <span class="badge">📔</span>
      <h3>Journal d'apprentissage</h3>
      <a href="/journal" class="link-btn">Voir les entrées →</a>
    </div>
    <p class="desc">
      Chaque jour à <strong>19h00</strong>, un message est envoyé dans <code>#journal</code> sur Slack.
      Réponds dans le <strong>thread</strong> pour enregistrer ton apprentissage du jour.
      Une relance est envoyée à <strong>22h00</strong> si aucune réponse n'a été reçue.
    </p>
    <div class="note">Aucune commande à retenir — il suffit de répondre dans le thread du message quotidien.</div>
  </div>

  <!-- Kanban -->
  <div class="section">
    <div class="section-header">
      <span class="badge">📋</span>
      <h3>Kanban</h3>
      <a href="/kanban" class="link-btn">Ouvrir le Kanban →</a>
    </div>
    <p class="desc">
      Gère tes tâches en colonnes depuis l'interface web ou directement depuis Slack.
      Les rappels sont envoyés automatiquement dans <code>#tasks</code> à l'heure exacte de l'échéance.
    </p>
    <table>
      <thead>
        <tr><th>Commande Slack</th><th>Action</th></tr>
      </thead>
      <tbody>
        <tr><td><code>/tache Titre</code></td><td>Crée une tâche dans la première colonne du board par défaut</td></tr>
        <tr><td><code>/tache Titre @Board Colonne</code></td><td>Crée une tâche dans un board et une colonne spécifiques</td></tr>
        <tr><td><code>/taches</code></td><td>Liste les tâches dont l'échéance est aujourd'hui</td></tr>
        <tr><td><code>/taches semaine</code></td><td>Liste les tâches dues cette semaine</td></tr>
        <tr><td><code>/vue Nom</code></td><td>Active un axe de regroupement existant</td></tr>
        <tr><td><code>/vue ajouter Nom champ</code></td><td>Crée un nouvel axe de regroupement</td></tr>
      </tbody>
    </table>
  </div>

</main>
</body>
</html>"""
