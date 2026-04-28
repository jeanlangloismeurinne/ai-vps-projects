import json
import logging
from datetime import date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.routes.auth import require_auth
from app.services import journal_v2 as svc

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_auth)])

# ── CSS / Shell (même thème que settings) ─────────────────────────────────────

_CSS = """
:root{--bg:#0f1117;--card:#1a1d27;--border:#1e2130;--text:#e8e8ea;--muted:#888;
      --accent:#4f6ef7;--danger:#e05252;--success:#2da862;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;}
header{padding:1rem 2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
header h1{font-size:1.1rem;font-weight:600;}
nav{display:flex;gap:1.5rem;font-size:.9rem;}
nav a{color:var(--muted);text-decoration:none;}
nav a:hover{color:var(--text);}
main{max-width:760px;margin:0 auto;padding:2rem 1.5rem;}
h2{font-size:1.3rem;font-weight:700;margin-bottom:1.5rem;}
h3{font-size:1rem;font-weight:600;margin-bottom:.75rem;}
.back{display:inline-flex;align-items:center;gap:.3rem;color:var(--muted);text-decoration:none;font-size:.9rem;margin-bottom:1.5rem;}
.back:hover{color:var(--text);}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.5rem;margin-bottom:1rem;}
.flex{display:flex;align-items:center;gap:.75rem;}
.flex-between{display:flex;align-items:center;justify-content:space-between;gap:1rem;}
label{font-size:.88rem;color:var(--muted);display:block;margin-bottom:.3rem;}
input[type=text],input[type=number],input[type=date],textarea,select{
  background:#0f1117;border:1px solid var(--border);border-radius:6px;
  color:var(--text);padding:.5rem .75rem;font-size:.9rem;width:100%;font-family:inherit;}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent);}
textarea{resize:vertical;min-height:100px;}
.btn{display:inline-flex;align-items:center;gap:.35rem;padding:.5rem 1.1rem;
     border-radius:7px;font-size:.9rem;font-weight:500;cursor:pointer;border:none;
     text-decoration:none;font-family:inherit;}
.btn-primary{background:var(--accent);color:#fff;}
.btn-primary:hover{background:#3d5de0;}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text);}
.btn-ghost:hover{background:var(--card);}
.empty{text-align:center;color:var(--muted);padding:2.5rem;font-style:italic;}
.badge{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.72rem;font-weight:500;}
.badge-done{background:#0d2a1a;color:var(--success);border:1px solid #1a4a2a;}
.badge-pending{background:#1a1d27;color:var(--muted);border:1px solid var(--border);}
.badge-skip{background:#1a1a1a;color:var(--muted);border:1px solid #333;}
.question-block{margin-bottom:2rem;padding-bottom:2rem;border-bottom:1px solid var(--border);}
.question-block:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0;}
.question-label{font-size:1rem;font-weight:500;margin-bottom:1rem;line-height:1.4;}
.note-btns{display:flex;gap:.5rem;flex-wrap:wrap;}
.note-btn{background:#0f1117;border:1px solid var(--border);color:var(--text);
          padding:.55rem 1.1rem;border-radius:7px;cursor:pointer;font-size:.95rem;font-weight:500;
          font-family:inherit;transition:all .15s;}
.note-btn:hover,.note-btn.selected{background:var(--accent);border-color:var(--accent);color:#fff;}
.scale-wrap{display:flex;flex-direction:column;gap:.5rem;}
.scale-labels{display:flex;justify-content:space-between;font-size:.78rem;color:var(--muted);}
input[type=range]{width:100%;accent-color:var(--accent);}
.choice-list{display:flex;flex-direction:column;gap:.4rem;}
.choice-opt{display:flex;align-items:center;gap:.6rem;padding:.5rem .75rem;
            border-radius:7px;border:1px solid var(--border);cursor:pointer;
            background:#0f1117;transition:border-color .15s;}
.choice-opt:hover{border-color:var(--accent);}
.choice-opt input{width:auto;margin:0;}
.other-input{margin-top:.5rem;display:none;}
.history-item{display:flex;justify-content:space-between;align-items:start;
              padding:.6rem 0;border-bottom:1px solid var(--border);gap:1rem;}
.history-item:last-child{border-bottom:none;}
.history-date{font-size:.8rem;color:var(--muted);flex-shrink:0;}
.history-val{font-size:.9rem;flex:1;}
.progress-bar{height:4px;background:var(--border);border-radius:2px;margin-bottom:1.5rem;}
.progress-fill{height:100%;background:var(--accent);border-radius:2px;transition:width .3s;}
"""

def _shell(title: str, body: str, back_url: str = "", back_label: str = "") -> str:
    back = f'<a href="{back_url}" class="back">← {back_label}</a>' if back_url else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Journal</title>
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
{back}
{body}
</main>
<script src="/public/feedback-widget.js" data-api="" data-project="journal" defer></script>
</body>
</html>"""


def _render_question(q) -> str:
    qid = str(q["id"])
    texte = q["texte"]
    type_ = q["type"]
    cfg = q["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)

    name = f"q_{qid}"
    html = f'<div class="question-block" data-question="{qid}">'
    html += f'<div class="question-label">{texte}</div>'

    if type_ in ("text",):
        html += f'<textarea name="{name}" rows="4" placeholder="Ta réponse…"></textarea>'

    elif type_ == "short_text":
        html += f'<input type="text" name="{name}" placeholder="Ta réponse…">'

    elif type_ == "note":
        mn, mx = cfg.get("min", 1), cfg.get("max", 5)
        btns = "".join(
            f'<button type="button" class="note-btn" data-name="{name}" data-val="{v}" onclick="selectNote(this)">{v}</button>'
            for v in range(mn, mx + 1)
        )
        html += f'<div class="note-btns">{btns}</div>'
        html += f'<input type="hidden" name="{name}" id="hidden_{name}">'

    elif type_ == "scale":
        mn, mx = cfg.get("min", 1), cfg.get("max", 10)
        lbl_min = cfg.get("label_min", str(mn))
        lbl_max = cfg.get("label_max", str(mx))
        mid = (mn + mx) // 2
        html += f"""
        <div class="scale-wrap">
          <input type="range" name="{name}" min="{mn}" max="{mx}" value="{mid}"
                 oninput="document.getElementById('sv_{name}').textContent=this.value">
          <div class="scale-labels">
            <span>{lbl_min}</span>
            <span id="sv_{name}" style="color:var(--accent);font-weight:600">{mid}</span>
            <span>{lbl_max}</span>
          </div>
        </div>"""

    elif type_ == "single_choice":
        opts = cfg.get("options", [])
        allow_other = cfg.get("allow_other", False)
        choices = ""
        for opt in opts:
            choices += f"""
            <label class="choice-opt">
              <input type="radio" name="{name}" value="{opt}" onchange="handleOther('{name}',this)">
              {opt}
            </label>"""
        if allow_other:
            choices += f"""
            <label class="choice-opt">
              <input type="radio" name="{name}" value="__other__" onchange="handleOther('{name}',this)">
              Autre (préciser)
            </label>
            <div class="other-input" id="other_{name}">
              <input type="text" name="{name}_other" placeholder="Précisez…">
            </div>"""
        html += f'<div class="choice-list">{choices}</div>'

    elif type_ == "multiple_choice":
        opts = cfg.get("options", [])
        allow_other = cfg.get("allow_other", False)
        choices = ""
        for opt in opts:
            choices += f"""
            <label class="choice-opt">
              <input type="checkbox" name="{name}[]" value="{opt}">
              {opt}
            </label>"""
        if allow_other:
            choices += f"""
            <label class="choice-opt">
              <input type="checkbox" name="{name}[]" value="__other__"
                     onchange="document.getElementById('other_{name}').style.display=this.checked?'block':'none'">
              Autre (préciser)
            </label>
            <div class="other-input" id="other_{name}">
              <input type="text" name="{name}_other" placeholder="Précisez…">
            </div>"""
        html += f'<div class="choice-list">{choices}</div>'

    elif type_ == "yes_no":
        html += f"""
        <div class="note-btns">
          <button type="button" class="note-btn" data-name="{name}" data-val="true" onclick="selectNote(this)">Oui</button>
          <button type="button" class="note-btn" data-name="{name}" data-val="false" onclick="selectNote(this)">Non</button>
        </div>
        <input type="hidden" name="{name}" id="hidden_{name}">"""

    elif type_ == "date":
        today = date.today().isoformat()
        html += f'<input type="date" name="{name}" value="{today}">'

    elif type_ == "duration":
        unit = cfg.get("unit", "minutes")
        unit_lbl = "minutes" if unit == "minutes" else "heures"
        html += f"""
        <div class="flex" style="gap:.5rem;align-items:center">
          <input type="number" name="{name}" min="0" step="1" style="width:120px" placeholder="0">
          <span style="color:var(--muted);font-size:.9rem">{unit_lbl}</span>
          <input type="hidden" name="{name}_unit" value="{unit}">
        </div>"""

    elif type_ == "ranking":
        items = cfg.get("items", [])
        html += '<div style="color:var(--muted);font-size:.85rem;margin-bottom:.5rem">Classez du plus important au moins important :</div>'
        for idx, item in enumerate(items, 1):
            html += f"""
            <div class="flex" style="margin-bottom:.4rem;gap:.5rem">
              <span style="color:var(--muted);min-width:1.2rem">{idx}.</span>
              <select name="{name}[]" style="flex:1">
                {''.join(f'<option value="{it}">{it}</option>' for it in items)}
              </select>
            </div>"""

    html += "</div>"
    return html


# ── Page principale — liste des objectifs du jour ─────────────────────────────

@router.get("/journal/fill", response_class=HTMLResponse)
async def fill_index():
    today = date.today()
    due = await svc.get_due_objectifs_today()

    if not due:
        body = """
        <h2>Journal du jour</h2>
        <p class="empty">Aucun objectif à remplir aujourd'hui.<br>
        Configurez vos <a href="/journal/settings" style="color:var(--accent)">parcours de progression</a>.</p>"""
        return HTMLResponse(_shell("Journal", body))

    total = len(due)
    done_count = 0
    cards = ""
    for o in due:
        done = await svc.is_objectif_complete(str(o["id"]), today)
        if done:
            done_count += 1
        status_cls = "badge-done" if done else "badge-pending"
        status_lbl = "Complété" if done else "À remplir"
        parcours_nom = o.get("parcours_nom", "")
        btn = (
            f'<a href="/journal/fill/{o["id"]}" class="btn btn-ghost" style="font-size:.85rem">Revoir →</a>'
            if done else
            f'<a href="/journal/fill/{o["id"]}" class="btn btn-primary" style="font-size:.85rem">Remplir →</a>'
        )
        cards += f"""
        <div class="card">
          <div class="flex-between">
            <div>
              <div class="flex" style="gap:.6rem;margin-bottom:.25rem">
                <span style="font-weight:600">{o['nom']}</span>
                <span class="badge {status_cls}">{status_lbl}</span>
              </div>
              <div style="font-size:.8rem;color:var(--muted)">{parcours_nom}</div>
            </div>
            {btn}
          </div>
        </div>"""

    pct = int(done_count / total * 100) if total else 0
    progress = f"""
    <div style="margin-bottom:1.5rem">
      <div class="flex-between" style="margin-bottom:.4rem">
        <span style="font-size:.85rem;color:var(--muted)">{done_count}/{total} objectif(s) complété(s)</span>
        <span style="font-size:.85rem;color:var(--accent)">{pct}%</span>
      </div>
      <div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>
    </div>"""

    date_str = today.strftime("%A %d %B %Y").capitalize()
    body = f"<h2>📅 {date_str}</h2>{progress}{cards}"
    return HTMLResponse(_shell("Journal du jour", body))


# ── Formulaire de remplissage d'un objectif ───────────────────────────────────

@router.get("/journal/fill/{objectif_id}", response_class=HTMLResponse)
async def fill_objectif(objectif_id: str):
    today = date.today()
    o = await svc.get_objectif(objectif_id)
    if not o:
        return RedirectResponse("/journal/fill", status_code=303)

    questions = await svc.list_active_questions(objectif_id)
    answered_ids = await svc.get_session_answered_ids(objectif_id, today)

    if not questions:
        body = f"""
        <h2>{o['nom']}</h2>
        <p class="empty">Aucune question active pour cet objectif.<br>
        <a href="/journal/settings/objectifs/{objectif_id}" style="color:var(--accent)">Ajouter des questions →</a></p>"""
        return HTMLResponse(_shell(o["nom"], body, "/journal/fill", "Retour"))

    q_blocks = "".join(_render_question(q) for q in questions)
    already_done = all(str(q["id"]) in answered_ids for q in questions)

    warning = ""
    if already_done:
        warning = '<div style="background:#1a2a1a;border:1px solid #2a4a2a;border-radius:8px;padding:1rem;margin-bottom:1.5rem;color:#5aba7a;font-size:.9rem">✓ Cet objectif a déjà été rempli aujourd\'hui. Tu peux soumettre à nouveau si tu veux corriger.</div>'

    body = f"""
    <h2>{o['nom']}</h2>
    {warning}
    <form method="post" action="/journal/fill/{objectif_id}" id="fill-form">
      {q_blocks}
      <div style="margin-top:2rem;display:flex;gap:1rem">
        <button type="submit" class="btn btn-primary">Enregistrer les réponses</button>
        <a href="/journal/fill" class="btn btn-ghost">Retour</a>
      </div>
    </form>

    <script>
    function selectNote(btn){{
      const name = btn.dataset.name;
      document.querySelectorAll(`[data-name="${{name}}"]`).forEach(b=>b.classList.remove('selected'));
      btn.classList.add('selected');
      document.getElementById('hidden_'+name).value = btn.dataset.val;
    }}
    function handleOther(name, radio){{
      const otherDiv = document.getElementById('other_'+name);
      if(otherDiv) otherDiv.style.display = radio.value==='__other__' ? 'block' : 'none';
    }}
    </script>"""

    return HTMLResponse(_shell(o["nom"], body, "/journal/fill", "Journal du jour"))


@router.post("/journal/fill/{objectif_id}")
async def submit_objectif(objectif_id: str, request: Request):
    today = date.today()
    o = await svc.get_objectif(objectif_id)
    if not o:
        return RedirectResponse("/journal/fill", status_code=303)

    questions = await svc.list_active_questions(objectif_id)
    form = await request.form()

    for q in questions:
        qid = str(q["id"])
        name = f"q_{qid}"
        type_ = q["type"]
        cfg = q["config"]
        if isinstance(cfg, str):
            cfg = json.loads(cfg)

        valeur: dict = {}

        if type_ in ("text", "short_text"):
            v = form.get(name, "").strip()
            if v:
                valeur = {"text": v}

        elif type_ in ("note", "scale"):
            v = form.get(name, "")
            if v:
                try:
                    valeur = {"value": int(v)}
                except ValueError:
                    pass

        elif type_ == "yes_no":
            v = form.get(name, "")
            if v in ("true", "false"):
                valeur = {"value": v == "true"}

        elif type_ == "single_choice":
            v = form.get(name, "")
            if v:
                other = form.get(f"{name}_other", "").strip() if v == "__other__" else None
                valeur = {"choice": v, "other": other}

        elif type_ == "multiple_choice":
            choices = form.getlist(f"{name}[]")
            other = form.get(f"{name}_other", "").strip() if "__other__" in choices else None
            clean = [c for c in choices if c != "__other__"]
            if choices:
                valeur = {"choices": clean, "other": other}

        elif type_ == "date":
            v = form.get(name, "")
            if v:
                valeur = {"value": v}

        elif type_ == "duration":
            v = form.get(name, "")
            unit = form.get(f"{name}_unit", cfg.get("unit", "minutes"))
            if v:
                try:
                    valeur = {"value": int(v), "unit": unit}
                except ValueError:
                    pass

        elif type_ == "ranking":
            items = form.getlist(f"{name}[]")
            if items:
                valeur = {"order": items}

        if valeur:
            await svc.store_reponse(qid, objectif_id, valeur, today)
            logger.info(f"Réponse stockée: question={qid}, objectif={objectif_id}")

    return RedirectResponse("/journal/fill", status_code=303)


# ── Historique ────────────────────────────────────────────────────────────────

@router.get("/journal/history", response_class=HTMLResponse)
async def history_index():
    questions = await svc.get_all_questions_with_stats()

    if not questions:
        body = """
        <h2>Historique</h2>
        <p class="empty">Aucune question enregistrée. <a href="/journal/settings" style="color:var(--accent)">Créez un parcours →</a></p>"""
        return HTMLResponse(_shell("Historique", body))

    current_parcours = None
    current_objectif = None
    cards = ""

    for q in questions:
        if q["parcours_nom"] != current_parcours:
            if current_parcours:
                cards += "</div>"
            cards += f'<h3 style="margin-top:1.5rem;margin-bottom:.75rem;color:var(--muted);font-size:.82rem;text-transform:uppercase;letter-spacing:.05em">{q["parcours_nom"]}</h3><div>'
            current_parcours = q["parcours_nom"]
            current_objectif = None

        if q["objectif_nom"] != current_objectif:
            if current_objectif:
                cards += '<hr style="border-color:var(--border);margin:.5rem 0">'
            cards += f'<div style="font-size:.85rem;color:var(--muted);margin-bottom:.5rem;padding-left:.1rem">{q["objectif_nom"]}</div>'
            current_objectif = q["objectif_nom"]

        nb = q["nb_reponses"] or 0
        last = q["last_answered"].strftime("%d/%m/%Y") if q["last_answered"] else "—"
        dep = ' <span class="badge badge-skip">Archivée</span>' if q["deprecated_at"] else ""
        inactive = ' <span class="badge badge-skip">Inactive</span>' if not q["is_active"] and not q["deprecated_at"] else ""

        cards += f"""
        <a href="/journal/history/{q['id']}" style="display:block;text-decoration:none;color:var(--text);
           padding:.6rem .75rem;border-radius:7px;margin-bottom:.25rem;border:1px solid transparent;
           transition:border-color .15s" onmouseover="this.style.borderColor='var(--border)'"
           onmouseout="this.style.borderColor='transparent'">
          <div class="flex-between">
            <span style="font-size:.9rem">{q['texte']}{dep}{inactive}</span>
            <span style="font-size:.8rem;color:var(--muted);flex-shrink:0;margin-left:.5rem">{nb} réponse(s) · {last}</span>
          </div>
        </a>"""

    if current_parcours:
        cards += "</div>"

    body = f"<h2>Historique des réponses</h2><div class='card'>{cards}</div>"
    return HTMLResponse(_shell("Historique", body))


@router.get("/journal/history/{question_id}", response_class=HTMLResponse)
async def history_question(question_id: str):
    q = await svc.get_question(question_id)
    if not q:
        return RedirectResponse("/journal/history", status_code=303)

    reponses = await svc.get_reponses(question_id)

    def _fmt_valeur(valeur, type_: str, cfg: dict) -> str:
        if isinstance(valeur, str):
            valeur = json.loads(valeur)
        if type_ in ("text", "short_text"):
            return valeur.get("text", "")
        if type_ in ("note", "scale"):
            v = valeur.get("value", "")
            if type_ == "note":
                mn, mx = cfg.get("min", 1), cfg.get("max", 5)
                filled = "●" * v + "○" * (mx - mn + 1 - v)
                return f"{v}/{mx} {filled}"
            return str(v)
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
            order = valeur.get("order", [])
            return " → ".join(order)
        return str(valeur)

    cfg = q["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)

    rows = ""
    for r in reponses:
        d = r["session_date"].strftime("%d/%m/%Y")
        val = _fmt_valeur(r["valeur"], q["type"], cfg)
        rows += f"""
        <div class="history-item">
          <span class="history-date">{d}</span>
          <span class="history-val">{val}</span>
        </div>"""

    if not rows:
        rows = '<p class="empty">Aucune réponse enregistrée.</p>'

    type_labels = {
        "text": "Texte libre", "short_text": "Texte court", "note": "Note",
        "scale": "Échelle", "single_choice": "Choix unique",
        "multiple_choice": "Choix multiple", "yes_no": "Oui / Non",
        "date": "Date", "duration": "Durée", "ranking": "Classement",
    }
    type_lbl = type_labels.get(q["type"], q["type"])

    body = f"""
    <h2 style="line-height:1.35">{q['texte']}</h2>
    <p style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem">{type_lbl} · {len(reponses)} réponse(s)</p>
    <div class="card">{rows}</div>"""

    return HTMLResponse(_shell("Historique", body, "/journal/history", "Historique"))
