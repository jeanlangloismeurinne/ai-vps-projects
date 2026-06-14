"""Route publique du récapitulatif hebdomadaire journal (accès par token signé)."""
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import settings
from app.services import journal_v2 as svc

logger = logging.getLogger(__name__)
router = APIRouter()

_TOKEN_MAX_AGE = 60 * 24 * 3600  # 60 jours
_SALT = "journal-recap"

_JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

_CSS = """
:root{--bg:#0f1117;--card:#1a1d27;--border:#1e2130;--text:#e8e8ea;--muted:#888;--accent:#4f6ef7;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
header{padding:1rem 2rem;border-bottom:1px solid var(--border);}
header h1{font-size:1.1rem;font-weight:600;}
main{max-width:760px;margin:0 auto;padding:2rem 1.5rem;}
h2{font-size:1.3rem;font-weight:700;margin-bottom:.5rem;}
h3{font-size:1rem;font-weight:600;margin-bottom:.75rem;color:var(--muted);}
.nav-week{display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;padding:.75rem 1rem;
          background:var(--card);border:1px solid var(--border);border-radius:8px;}
.nav-week a{color:var(--accent);text-decoration:none;font-size:.9rem;}
.nav-week a:hover{text-decoration:underline;}
.nav-week span{font-size:.88rem;color:var(--muted);}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1.25rem;}
.entry{padding:.5rem 0;border-bottom:1px solid var(--border);display:flex;gap:1rem;}
.entry:last-child{border-bottom:none;}
.entry-date{font-size:.8rem;color:var(--muted);min-width:90px;flex-shrink:0;padding-top:.1rem;}
.entry-val{font-size:.9rem;flex:1;}
.empty{text-align:center;color:var(--muted);padding:3rem;font-style:italic;}
footer{margin-top:2rem;text-align:center;font-size:.85rem;color:var(--muted);}
footer a{color:var(--accent);text-decoration:none;}
.error{text-align:center;padding:4rem 2rem;}
.error h2{font-size:1.5rem;margin-bottom:.75rem;}
.error p{color:var(--muted);}
"""


def _make_token(objectif_id: str, semaine_iso: str) -> str:
    s = URLSafeTimedSerializer(settings.SESSION_SECRET, salt=_SALT)
    return s.dumps(f"{objectif_id}:{semaine_iso}")


def _verify_token(token: str, objectif_id: str, semaine_iso: str) -> bool:
    s = URLSafeTimedSerializer(settings.SESSION_SECRET, salt=_SALT)
    try:
        data = s.loads(token, max_age=_TOKEN_MAX_AGE)
        return data == f"{objectif_id}:{semaine_iso}"
    except (BadSignature, SignatureExpired):
        return False


def _semaine_dates(semaine_iso: str):
    year_str, week_str = semaine_iso.split("-W")
    lundi = datetime.strptime(f"{year_str}-W{int(week_str):02d}-1", "%G-W%V-%u").date()
    dimanche = lundi + timedelta(days=6)
    return lundi, dimanche


def _prev_next_semaine(semaine_iso: str):
    lundi, _ = _semaine_dates(semaine_iso)
    prev_lundi = lundi - timedelta(weeks=1)
    next_lundi = lundi + timedelta(weeks=1)
    prev_iso_year, prev_iso_week, _ = prev_lundi.isocalendar()
    next_iso_year, next_iso_week, _ = next_lundi.isocalendar()
    return (
        f"{prev_iso_year}-W{prev_iso_week:02d}",
        f"{next_iso_year}-W{next_iso_week:02d}",
    )


def _fmt_valeur(valeur: dict, type_: str) -> str:
    if type_ in ("text", "short_text"):
        return valeur.get("text", "")
    if type_ in ("note", "scale"):
        return str(valeur.get("value", ""))
    if type_ == "yes_no":
        return "Oui" if valeur.get("value") else "Non"
    if type_ == "single_choice":
        c = valeur.get("choice", "")
        o = valeur.get("other")
        return f"{c} — {o}" if c == "__other__" and o else c
    if type_ == "multiple_choice":
        choices = valeur.get("choices", [])
        other = valeur.get("other")
        parts = choices[:]
        if other:
            parts.append(f"Autre : {other}")
        return ", ".join(parts) if parts else "—"
    if type_ == "date":
        return valeur.get("value", "")
    if type_ == "duration":
        return f"{valeur.get('value', '')} {valeur.get('unit', '')}"
    if type_ == "ranking":
        return " → ".join(valeur.get("order", []))
    return str(valeur)


def _error_page(message: str, code: int) -> HTMLResponse:
    body = f"""<!DOCTYPE html><html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Récap Journal</title><style>{_CSS}</style></head>
<body><main><div class="error"><h2>🔒 Lien invalide</h2><p>{message}</p></div></main></body></html>"""
    return HTMLResponse(body, status_code=code)


@router.get("/journal/recap/{objectif_id}/{semaine_iso}", response_class=HTMLResponse)
async def recap_page(objectif_id: str, semaine_iso: str, request: Request):
    token = request.query_params.get("token", "")

    if not _verify_token(token, objectif_id, semaine_iso):
        return _error_page("Lien expiré ou invalide.", 403)

    o = await svc.get_objectif(objectif_id)
    if not o:
        return _error_page("Objectif introuvable.", 404)

    reponses = await svc.get_reponses_semaine(objectif_id, semaine_iso)

    lundi, dimanche = _semaine_dates(semaine_iso)
    periode = f"{lundi.strftime('%d/%m/%Y')} → {dimanche.strftime('%d/%m/%Y')}"

    prev_semaine, next_semaine = _prev_next_semaine(semaine_iso)
    prev_token = _make_token(objectif_id, prev_semaine)
    next_token = _make_token(objectif_id, next_semaine)
    prev_url = f"/journal/recap/{objectif_id}/{prev_semaine}?token={prev_token}"
    next_url = f"/journal/recap/{objectif_id}/{next_semaine}?token={next_token}"

    nav = f"""
    <div class="nav-week">
      <a href="{prev_url}">← Semaine précédente</a>
      <span>{semaine_iso.replace('-W', ' semaine ')}</span>
      <a href="{next_url}">Semaine suivante →</a>
    </div>"""

    if not reponses:
        content = '<p class="empty">Aucune réponse enregistrée cette semaine.</p>'
    else:
        content = ""
        for question_texte, entries in reponses.items():
            rows = ""
            for e in entries:
                d = e["session_date"]
                nom_jour = _JOURS_FR[d.weekday()]
                val = _fmt_valeur(e["valeur"], e["type"])
                rows += f"""
                <div class="entry">
                  <div class="entry-date">{nom_jour} {d.strftime('%d/%m')}</div>
                  <div class="entry-val">{val}</div>
                </div>"""
            content += f"""
            <div class="card">
              <h3>{question_texte}</h3>
              {rows}
            </div>"""

    fill_url = f"/journal/fill/{objectif_id}"

    body = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Récap — {o['nom']}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>📋 Récap Journal</h1>
</header>
<main>
  <h2>{o['nom']}</h2>
  <p style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem">{periode}</p>
  {nav}
  {content}
  <footer>
    <a href="{fill_url}">Remplir le journal aujourd'hui →</a>
  </footer>
</main>
</body>
</html>"""

    return HTMLResponse(body)
