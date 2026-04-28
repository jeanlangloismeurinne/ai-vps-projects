import json
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.routes.auth import require_auth
from app.services import journal_v2 as svc

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_auth)])

# ── CSS / Shell ───────────────────────────────────────────────────────────────

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
main{max-width:860px;margin:0 auto;padding:2rem 1.5rem;}
h2{font-size:1.3rem;font-weight:700;margin-bottom:1.5rem;}
h3{font-size:1rem;font-weight:600;margin-bottom:.75rem;}
.back{display:inline-flex;align-items:center;gap:.3rem;color:var(--muted);text-decoration:none;font-size:.9rem;margin-bottom:1.5rem;}
.back:hover{color:var(--text);}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1rem;}
.flex{display:flex;align-items:center;gap:.75rem;}
.flex-between{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;}
label{font-size:.85rem;color:var(--muted);display:block;margin-bottom:.25rem;}
input[type=text],input[type=number],input[type=time],textarea,select{
  background:#0f1117;border:1px solid var(--border);border-radius:6px;
  color:var(--text);padding:.5rem .75rem;font-size:.9rem;width:100%;font-family:inherit;}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent);}
textarea{resize:vertical;min-height:70px;}
.btn{display:inline-flex;align-items:center;gap:.35rem;padding:.45rem 1rem;
     border-radius:7px;font-size:.88rem;font-weight:500;cursor:pointer;border:none;
     text-decoration:none;font-family:inherit;transition:background .15s;}
.btn-primary{background:var(--accent);color:#fff;}
.btn-primary:hover{background:#3d5de0;}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text);}
.btn-ghost:hover{background:var(--card);}
.btn-danger{background:transparent;border:1px solid #4a2020;color:var(--danger);}
.btn-danger:hover{background:#2a1515;}
.btn-sm{padding:.28rem .65rem;font-size:.8rem;}
.form-group{margin-bottom:1rem;}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
.form-row-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;}
.hint{font-size:.78rem;color:var(--muted);margin-top:.2rem;}
.empty{text-align:center;color:var(--muted);padding:2.5rem;font-style:italic;}
.badge{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.72rem;font-weight:500;}
.badge-on{background:#0d2a1a;color:var(--success);border:1px solid #1a4a2a;}
.badge-off{background:#1a1a1a;color:var(--muted);border:1px solid #333;}
.type-tag{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.72rem;
          background:#1a1d40;color:#8899ff;border:1px solid #2a2d60;}
.toggle{position:relative;display:inline-block;width:34px;height:18px;flex-shrink:0;}
.toggle input{opacity:0;width:0;height:0;}
.slider{position:absolute;inset:0;background:#333;border-radius:18px;cursor:pointer;transition:.2s;}
.slider::before{content:"";position:absolute;height:12px;width:12px;left:3px;bottom:3px;
                background:#fff;border-radius:50%;transition:.2s;}
input:checked+.slider{background:var(--accent);}
input:checked+.slider::before{transform:translateX(16px);}
hr{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}
details summary{cursor:pointer;color:var(--accent);font-size:.9rem;}
details[open] summary{margin-bottom:1rem;}
.deprecated-section{opacity:.55;}
.option-row{display:flex;gap:.5rem;margin-bottom:.4rem;}
.option-row input{flex:1;}
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
</body>
</html>"""

def _type_label(t: str) -> str:
    labels = {
        "text": "Texte libre", "short_text": "Texte court", "note": "Note",
        "scale": "Échelle", "single_choice": "Choix unique",
        "multiple_choice": "Choix multiple", "yes_no": "Oui / Non",
        "date": "Date", "duration": "Durée", "ranking": "Classement",
    }
    return labels.get(t, t)

def _freq_label(f: str) -> str:
    return {"daily": "Quotidien", "weekly": "Hebdomadaire", "monthly": "Mensuel"}.get(f, f)

_JOURS_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

# ── Liste des parcours ────────────────────────────────────────────────────────

@router.get("/journal/settings", response_class=HTMLResponse)
async def settings_index():
    parcours_list = await svc.list_parcours()

    cards = ""
    for p in parcours_list:
        active_cls = "badge-on" if p["is_active"] else "badge-off"
        active_lbl = "Actif" if p["is_active"] else "Inactif"
        desc = p["description"] or ""
        cards += f"""
        <div class="card">
          <div class="flex-between">
            <div class="flex" style="gap:1rem">
              <a href="/journal/settings/parcours/{p['id']}" style="color:var(--text);text-decoration:none;font-weight:600">{p['nom']}</a>
              <span class="badge {active_cls}">{active_lbl}</span>
            </div>
            <div class="flex" style="gap:.5rem">
              <form method="post" action="/journal/settings/parcours/{p['id']}/toggle" style="display:inline">
                <button class="btn btn-ghost btn-sm" type="submit">
                  {'Désactiver' if p['is_active'] else 'Activer'}
                </button>
              </form>
              <a href="/journal/settings/parcours/{p['id']}" class="btn btn-ghost btn-sm">Ouvrir →</a>
            </div>
          </div>
          {f'<p style="color:var(--muted);font-size:.85rem;margin-top:.5rem">{desc}</p>' if desc else ''}
        </div>"""

    if not cards:
        cards = '<p class="empty">Aucun parcours. Créez-en un ci-dessous.</p>'

    form = """
    <details style="margin-top:1.5rem">
      <summary>+ Nouveau parcours</summary>
      <div class="card" style="margin-top:1rem">
        <form method="post" action="/journal/settings/parcours">
          <div class="form-group">
            <label>Nom du parcours</label>
            <input type="text" name="nom" required placeholder="ex : Humilité">
          </div>
          <div class="form-group">
            <label>Description (optionnelle)</label>
            <textarea name="description" placeholder="Objectif global de ce parcours…"></textarea>
          </div>
          <button type="submit" class="btn btn-primary">Créer le parcours</button>
        </form>
      </div>
    </details>"""

    body = f"<h2>Parcours de progression</h2>{cards}{form}"
    return HTMLResponse(_shell("Paramètres", body))


@router.post("/journal/settings/parcours")
async def create_parcours(request: Request):
    form = await request.form()
    await svc.create_parcours(form["nom"], form.get("description", ""))
    return RedirectResponse("/journal/settings", status_code=303)


@router.post("/journal/settings/parcours/{id}/toggle")
async def toggle_parcours(id: str):
    p = await svc.get_parcours(id)
    if p:
        await svc.toggle_parcours(id, not p["is_active"])
    return RedirectResponse("/journal/settings", status_code=303)

# ── Parcours → objectifs ──────────────────────────────────────────────────────

@router.get("/journal/settings/parcours/{id}", response_class=HTMLResponse)
async def parcours_detail(id: str):
    p = await svc.get_parcours(id)
    if not p:
        return RedirectResponse("/journal/settings", status_code=303)

    objectifs = await svc.list_objectifs(id)
    archived_objectifs = await svc.list_archived_objectifs(id)

    def _objectif_card(o, archived=False):
        raw = o["jours"]
        jours = raw if isinstance(raw, list) else json.loads(raw or "[]")
        jours_str = ""
        if o["frequence"] == "weekly":
            jours_str = " · " + " ".join(_JOURS_LABELS[j] for j in jours if 0 <= j <= 6)
        elif o["frequence"] == "monthly":
            jours_str = " · jours " + ", ".join(str(j) for j in jours)
        freq_str = _freq_label(o["frequence"]) + jours_str
        heure = str(o["heure_rappel"])[:5]
        active_cls = "badge-on" if o["is_active"] else "badge-off"
        active_lbl = "Actif" if o["is_active"] else "Inactif"
        desc = o["description"] or ""
        oid = o["id"]

        if archived:
            return f"""
        <div class="card" style="opacity:.65">
          <div class="flex-between">
            <div>
              <div style="font-weight:600;margin-bottom:.2rem">{o['nom']}</div>
              <div style="font-size:.82rem;color:var(--muted)">{freq_str} · {heure}</div>
              {f'<div style="font-size:.85rem;color:var(--muted);margin-top:.3rem">{desc}</div>' if desc else ''}
            </div>
            <form method="post" action="/journal/settings/objectifs/{oid}/restore" style="flex-shrink:0">
              <button class="btn btn-ghost btn-sm" type="submit">Restaurer</button>
            </form>
          </div>
        </div>"""

        return f"""
        <div class="card">
          <div class="flex-between" style="align-items:flex-start">
            <div>
              <div class="flex" style="gap:.75rem;margin-bottom:.3rem">
                <span style="font-weight:600">{o['nom']}</span>
                <span class="badge {active_cls}">{active_lbl}</span>
              </div>
              <div style="font-size:.82rem;color:var(--muted)">{freq_str} · {heure}</div>
              {f'<div style="font-size:.85rem;color:var(--muted);margin-top:.3rem">{desc}</div>' if desc else ''}
            </div>
            <div class="flex" style="gap:.5rem;flex-shrink:0">
              <form method="post" action="/journal/settings/objectifs/{oid}/toggle" style="display:inline">
                <button class="btn btn-ghost btn-sm" type="submit">
                  {'Désactiver' if o['is_active'] else 'Activer'}
                </button>
              </form>
              <a href="/journal/settings/objectifs/{oid}" class="btn btn-ghost btn-sm">Questions →</a>
            </div>
          </div>
          <details style="margin-top:.75rem">
            <summary style="font-size:.85rem;color:var(--muted);cursor:pointer">Éditer</summary>
            <div style="margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--border)">
              <form method="post" action="/journal/settings/objectifs/{oid}/update">
                <div class="form-group">
                  <label>Nom</label>
                  <input type="text" name="nom" value="{o['nom']}" required>
                </div>
                <div class="form-group">
                  <label>Description</label>
                  <textarea name="description">{desc}</textarea>
                </div>
                <div class="flex" style="gap:.75rem">
                  <button type="submit" class="btn btn-primary btn-sm">Enregistrer</button>
                </div>
              </form>
              <form method="post" action="/journal/settings/objectifs/{oid}/archive" style="margin-top:.6rem"
                    onsubmit="return confirm('Archiver cet objectif ? Il ne sera plus visible dans la liste.')">
                <button type="submit" class="btn btn-ghost btn-sm" style="color:var(--muted)">Archiver</button>
              </form>
            </div>
          </details>
        </div>"""

    cards = "".join(_objectif_card(o) for o in objectifs)
    if not cards:
        cards = '<p class="empty">Aucun objectif actif. Créez-en un ci-dessous.</p>'

    archived_cards = "".join(_objectif_card(o, archived=True) for o in archived_objectifs)
    archived_section = ""
    if archived_cards:
        archived_section = f"""
    <details style="margin-top:2rem">
      <summary style="font-size:.9rem;color:var(--muted);cursor:pointer">Objectifs archivés ({len(archived_objectifs)})</summary>
      <div style="margin-top:.75rem">{archived_cards}</div>
    </details>"""

    freq_options = '<option value="daily">Quotidien</option><option value="weekly">Hebdomadaire</option><option value="monthly">Mensuel</option>'

    jours_checks = "".join(
        f'<label style="display:inline-flex;align-items:center;gap:.3rem;margin-right:.75rem;font-size:.85rem;color:var(--text)">'
        f'<input type="checkbox" name="jours" value="{i}"> {_JOURS_LABELS[i]}</label>'
        for i in range(7)
    )

    form = f"""
    <details style="margin-top:1.5rem">
      <summary>+ Nouvel objectif</summary>
      <div class="card" style="margin-top:1rem">
        <form method="post" action="/journal/settings/objectifs">
          <input type="hidden" name="parcours_id" value="{id}">
          <div class="form-group">
            <label>Nom de l'objectif</label>
            <input type="text" name="nom" required placeholder="ex : Écoute active">
          </div>
          <div class="form-group">
            <label>Description (optionnelle)</label>
            <textarea name="description" placeholder="Ce que cet objectif cherche à développer…"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Fréquence</label>
              <select name="frequence" onchange="toggleJours(this.value)">{freq_options}</select>
            </div>
            <div class="form-group">
              <label>Heure du rappel Slack</label>
              <input type="time" name="heure_rappel" value="09:00">
            </div>
          </div>
          <div class="form-group" id="weekly-jours" style="display:none">
            <label>Jours de la semaine</label>
            <div style="margin-top:.4rem">{jours_checks}</div>
          </div>
          <div class="form-group" id="monthly-jours" style="display:none">
            <label>Jours du mois (ex : 1 15)</label>
            <input type="text" name="monthly_jours" placeholder="1 15">
            <div class="hint">Séparez les jours par un espace</div>
          </div>
          <button type="submit" class="btn btn-primary">Créer l'objectif</button>
        </form>
      </div>
    </details>
    <script>
    function toggleJours(v){{
      document.getElementById('weekly-jours').style.display = v==='weekly'?'block':'none';
      document.getElementById('monthly-jours').style.display = v==='monthly'?'block':'none';
    }}
    </script>"""

    edit_form = f"""
    <details style="margin-bottom:1rem">
      <summary>Modifier ce parcours</summary>
      <div class="card" style="margin-top:1rem">
        <form method="post" action="/journal/settings/parcours/{id}/update">
          <div class="form-group">
            <label>Nom</label>
            <input type="text" name="nom" value="{p['nom']}" required>
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea name="description">{p['description'] or ''}</textarea>
          </div>
          <div class="flex" style="gap:.75rem">
            <button type="submit" class="btn btn-primary btn-sm">Enregistrer</button>
            <form method="post" action="/journal/settings/parcours/{id}/delete" style="display:inline"
                  onsubmit="return confirm('Supprimer ce parcours et tous ses objectifs ?')">
              <button type="submit" class="btn btn-danger btn-sm">Supprimer</button>
            </form>
          </div>
        </form>
      </div>
    </details>"""

    body = f"""
    <h2>{p['nom']}</h2>
    {edit_form}
    <h3>Objectifs</h3>
    {cards}
    {archived_section}
    {form}"""
    return HTMLResponse(_shell(p["nom"], body, "/journal/settings", "Parcours"))


@router.post("/journal/settings/parcours/{id}/update")
async def update_parcours(id: str, request: Request):
    form = await request.form()
    await svc.update_parcours(id, form["nom"], form.get("description", ""))
    return RedirectResponse(f"/journal/settings/parcours/{id}", status_code=303)


@router.post("/journal/settings/parcours/{id}/delete")
async def delete_parcours(id: str):
    await svc.delete_parcours(id)
    return RedirectResponse("/journal/settings", status_code=303)


@router.post("/journal/settings/objectifs")
async def create_objectif(request: Request):
    form = await request.form()
    parcours_id = form["parcours_id"]
    frequence = form.get("frequence", "daily")

    if frequence == "weekly":
        jours = [int(j) for j in form.getlist("jours")]
    elif frequence == "monthly":
        raw = form.get("monthly_jours", "")
        jours = [int(x) for x in raw.split() if x.isdigit()]
    else:
        jours = []

    await svc.create_objectif(
        parcours_id, form["nom"], form.get("description", ""),
        frequence, jours, form.get("heure_rappel", "09:00"),
    )
    return RedirectResponse(f"/journal/settings/parcours/{parcours_id}", status_code=303)


@router.post("/journal/settings/objectifs/{id}/toggle")
async def toggle_objectif(id: str):
    o = await svc.get_objectif(id)
    if not o:
        return RedirectResponse("/journal/settings", status_code=303)
    await svc.toggle_objectif(id, not o["is_active"])
    return RedirectResponse(f"/journal/settings/parcours/{o['parcours_id']}", status_code=303)


@router.post("/journal/settings/objectifs/{id}/update")
async def update_objectif(id: str, request: Request):
    form = await request.form()
    o = await svc.get_objectif(id)
    if not o:
        return RedirectResponse("/journal/settings", status_code=303)
    await svc.rename_objectif(id, form["nom"], form.get("description", ""))
    return RedirectResponse(f"/journal/settings/parcours/{o['parcours_id']}", status_code=303)


@router.post("/journal/settings/objectifs/{id}/archive")
async def archive_objectif(id: str):
    o = await svc.get_objectif(id)
    if not o:
        return RedirectResponse("/journal/settings", status_code=303)
    await svc.archive_objectif(id)
    return RedirectResponse(f"/journal/settings/parcours/{o['parcours_id']}", status_code=303)


@router.post("/journal/settings/objectifs/{id}/restore")
async def restore_objectif(id: str):
    o = await svc.get_objectif(id)
    if not o:
        return RedirectResponse("/journal/settings", status_code=303)
    await svc.restore_objectif(id)
    return RedirectResponse(f"/journal/settings/parcours/{o['parcours_id']}", status_code=303)


# ── Objectif → questions ──────────────────────────────────────────────────────

@router.get("/journal/settings/objectifs/{id}", response_class=HTMLResponse)
async def objectif_detail(id: str):
    o = await svc.get_objectif(id)
    if not o:
        return RedirectResponse("/journal/settings", status_code=303)
    p = await svc.get_parcours(str(o["parcours_id"]))

    questions = await svc.list_questions(id, include_deprecated=True)
    active_qs = [q for q in questions if q["deprecated_at"] is None]
    deprecated_qs = [q for q in questions if q["deprecated_at"] is not None]

    def _q_card(q, show_actions=True) -> str:
        cfg = q["config"]
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        config_hint = ""
        if q["type"] == "note":
            config_hint = f" · {cfg.get('min',1)}–{cfg.get('max',5)}"
        elif q["type"] == "scale":
            config_hint = f" · {cfg.get('min',1)}–{cfg.get('max',10)}"
        elif q["type"] in ("single_choice", "multiple_choice"):
            opts = cfg.get("options", [])
            config_hint = f" · {len(opts)} option(s)"
            if cfg.get("allow_other"):
                config_hint += " + Autre"
        elif q["type"] == "ranking":
            config_hint = f" · {len(cfg.get('items', []))} item(s)"

        active_cls = "badge-on" if q["is_active"] else "badge-off"
        active_lbl = "Active" if q["is_active"] else "Inactive"
        actions = ""
        if show_actions:
            toggle_lbl = "Désactiver" if q["is_active"] else "Activer"
            actions = f"""
            <div class="flex" style="gap:.4rem;flex-shrink:0">
              <form method="post" action="/journal/settings/questions/{q['id']}/up" style="display:inline">
                <button class="btn btn-ghost btn-sm" type="submit" title="Monter">↑</button>
              </form>
              <form method="post" action="/journal/settings/questions/{q['id']}/down" style="display:inline">
                <button class="btn btn-ghost btn-sm" type="submit" title="Descendre">↓</button>
              </form>
              <form method="post" action="/journal/settings/questions/{q['id']}/toggle" style="display:inline">
                <button class="btn btn-ghost btn-sm" type="submit">{toggle_lbl}</button>
              </form>
              <form method="post" action="/journal/settings/questions/{q['id']}/deprecate" style="display:inline"
                    onsubmit="return confirm('Archiver cette question ? Les réponses passées sont conservées.')">
                <button class="btn btn-danger btn-sm" type="submit">Archiver</button>
              </form>
            </div>"""

        return f"""
        <div class="card" style="margin-bottom:.75rem">
          <div class="flex-between">
            <div>
              <div class="flex" style="gap:.5rem;margin-bottom:.3rem">
                <span class="type-tag">{_type_label(q['type'])}{config_hint}</span>
                <span class="badge {active_cls}">{active_lbl}</span>
              </div>
              <div style="font-size:.92rem">{q['texte']}</div>
            </div>
            {actions}
          </div>
        </div>"""

    cards = "".join(_q_card(q) for q in active_qs)
    if not cards:
        cards = '<p class="empty">Aucune question active. Créez-en une ci-dessous.</p>'

    deprecated_html = ""
    if deprecated_qs:
        items = "".join(_q_card(q, show_actions=False) for q in deprecated_qs)
        deprecated_html = f"""
        <details style="margin-top:1rem" class="deprecated-section">
          <summary>{len(deprecated_qs)} question(s) archivée(s)</summary>
          <div style="margin-top:1rem">{items}</div>
        </details>"""

    type_options = "".join(
        f'<option value="{v}">{_type_label(v)}</option>'
        for v in ["text","short_text","note","scale","single_choice","multiple_choice","yes_no","date","duration","ranking"]
    )

    new_q_form = f"""
    <details style="margin-top:1.5rem">
      <summary>+ Nouvelle question</summary>
      <div class="card" style="margin-top:1rem">
        <form method="post" action="/journal/settings/questions" id="qform">
          <input type="hidden" name="objectif_id" value="{id}">
          <div class="form-group">
            <label>Question</label>
            <textarea name="texte" required placeholder="Ex : Comment évalues-tu ton niveau d'écoute aujourd'hui ?"></textarea>
          </div>
          <div class="form-group">
            <label>Type de réponse</label>
            <select name="type" onchange="showTypeConfig(this.value)" required>{type_options}</select>
          </div>

          <div id="cfg-note" class="type-config" style="display:none">
            <div class="form-row">
              <div class="form-group"><label>Min</label><input type="number" name="note_min" value="1" min="0" max="100"></div>
              <div class="form-group"><label>Max</label><input type="number" name="note_max" value="5" min="1" max="100"></div>
            </div>
          </div>

          <div id="cfg-scale" class="type-config" style="display:none">
            <div class="form-row">
              <div class="form-group"><label>Min</label><input type="number" name="scale_min" value="1"></div>
              <div class="form-group"><label>Max</label><input type="number" name="scale_max" value="10"></div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>Étiquette min</label><input type="text" name="scale_label_min" placeholder="Pas du tout"></div>
              <div class="form-group"><label>Étiquette max</label><input type="text" name="scale_label_max" placeholder="Totalement"></div>
            </div>
          </div>

          <div id="cfg-choices" class="type-config" style="display:none">
            <div class="form-group">
              <label>Options</label>
              <div id="options-list">
                <div class="option-row"><input type="text" name="option" placeholder="Option 1"></div>
                <div class="option-row"><input type="text" name="option" placeholder="Option 2"></div>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" onclick="addOption()" style="margin-top:.4rem">+ Ajouter une option</button>
            </div>
            <div class="form-group">
              <label style="display:inline-flex;align-items:center;gap:.4rem;color:var(--text)">
                <input type="checkbox" name="allow_other" value="on"> Inclure l'option "Autre (préciser)"
              </label>
            </div>
          </div>

          <div id="cfg-ranking" class="type-config" style="display:none">
            <div class="form-group">
              <label>Éléments à classer</label>
              <div id="ranking-list">
                <div class="option-row"><input type="text" name="ranking_item" placeholder="Élément 1"></div>
                <div class="option-row"><input type="text" name="ranking_item" placeholder="Élément 2"></div>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" onclick="addRankingItem()" style="margin-top:.4rem">+ Ajouter un élément</button>
            </div>
          </div>

          <div id="cfg-duration" class="type-config" style="display:none">
            <div class="form-group">
              <label>Unité</label>
              <select name="duration_unit">
                <option value="minutes">Minutes</option>
                <option value="hours">Heures</option>
              </select>
            </div>
          </div>

          <button type="submit" class="btn btn-primary" style="margin-top:.5rem">Ajouter la question</button>
        </form>
      </div>
    </details>

    <script>
    function showTypeConfig(type){{
      document.querySelectorAll('.type-config').forEach(el=>el.style.display='none');
      if(type==='note') document.getElementById('cfg-note').style.display='block';
      else if(type==='scale') document.getElementById('cfg-scale').style.display='block';
      else if(type==='single_choice'||type==='multiple_choice') document.getElementById('cfg-choices').style.display='block';
      else if(type==='ranking') document.getElementById('cfg-ranking').style.display='block';
      else if(type==='duration') document.getElementById('cfg-duration').style.display='block';
    }}
    function addOption(){{
      const list=document.getElementById('options-list');
      const row=document.createElement('div');
      row.className='option-row';
      row.innerHTML='<input type="text" name="option" placeholder="Nouvelle option">';
      list.appendChild(row);
    }}
    function addRankingItem(){{
      const list=document.getElementById('ranking-list');
      const row=document.createElement('div');
      row.className='option-row';
      row.innerHTML='<input type="text" name="ranking_item" placeholder="Nouvel élément">';
      list.appendChild(row);
    }}
    </script>"""

    raw = o["jours"]
    jours = raw if isinstance(raw, list) else json.loads(raw or "[]")
    jours_str = ""
    if o["frequence"] == "weekly":
        jours_str = " · " + " ".join(_JOURS_LABELS[j] for j in jours if 0 <= j <= 6)
    elif o["frequence"] == "monthly":
        jours_str = " · j." + " ".join(str(j) for j in jours)
    freq_str = _freq_label(o["frequence"]) + jours_str
    heure = str(o["heure_rappel"])[:5]

    body = f"""
    <h2>{o['nom']}</h2>
    <p style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem">{freq_str} · rappel {heure}</p>
    <h3>Questions actives</h3>
    {cards}
    {deprecated_html}
    {new_q_form}"""
    back_url = f"/journal/settings/parcours/{o['parcours_id']}"
    return HTMLResponse(_shell(o["nom"], body, back_url, p["nom"] if p else "Parcours"))


@router.post("/journal/settings/questions")
async def create_question(request: Request):
    form = await request.form()
    objectif_id = form["objectif_id"]
    type_ = form["type"]

    config: dict = {}
    if type_ == "note":
        config = {"min": int(form.get("note_min", 1)), "max": int(form.get("note_max", 5))}
    elif type_ == "scale":
        config = {
            "min": int(form.get("scale_min", 1)),
            "max": int(form.get("scale_max", 10)),
            "label_min": form.get("scale_label_min", ""),
            "label_max": form.get("scale_label_max", ""),
        }
    elif type_ in ("single_choice", "multiple_choice"):
        opts = [o.strip() for o in form.getlist("option") if o.strip()]
        config = {"options": opts, "allow_other": form.get("allow_other") == "on"}
    elif type_ == "duration":
        config = {"unit": form.get("duration_unit", "minutes")}
    elif type_ == "ranking":
        items = [i.strip() for i in form.getlist("ranking_item") if i.strip()]
        config = {"items": items}

    await svc.create_question(objectif_id, form["texte"], type_, config)
    return RedirectResponse(f"/journal/settings/objectifs/{objectif_id}", status_code=303)


@router.post("/journal/settings/questions/{id}/toggle")
async def toggle_question(id: str):
    q = await svc.get_question(id)
    if not q:
        return RedirectResponse("/journal/settings", status_code=303)
    cfg = q["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    await svc.update_question(id, q["texte"], cfg, not q["is_active"])
    return RedirectResponse(f"/journal/settings/objectifs/{q['objectif_id']}", status_code=303)


@router.post("/journal/settings/questions/{id}/deprecate")
async def deprecate_question(id: str):
    q = await svc.get_question(id)
    if not q:
        return RedirectResponse("/journal/settings", status_code=303)
    objectif_id = q["objectif_id"]
    await svc.deprecate_question(id)
    return RedirectResponse(f"/journal/settings/objectifs/{objectif_id}", status_code=303)


@router.post("/journal/settings/questions/{id}/up")
async def question_up(id: str):
    q = await svc.get_question(id)
    if q:
        await svc.move_question(id, "up")
    return RedirectResponse(f"/journal/settings/objectifs/{q['objectif_id']}", status_code=303)


@router.post("/journal/settings/questions/{id}/down")
async def question_down(id: str):
    q = await svc.get_question(id)
    if q:
        await svc.move_question(id, "down")
    return RedirectResponse(f"/journal/settings/objectifs/{q['objectif_id']}", status_code=303)
