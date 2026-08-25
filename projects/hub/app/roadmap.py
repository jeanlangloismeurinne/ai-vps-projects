import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

PROJECTS_BASE = Path(os.environ.get("PROJECTS_DIR", "/projects"))

STATUS_LABEL = {"draft": "Brouillon", "spec-ready": "Spec prête", "tickets-created": "Tickets créés", "en-cours": "En cours", "done": "Terminé"}
STATUS_COLOR = {"draft": "#6b7280", "spec-ready": "#ca8a04", "tickets-created": "#4f6ef7", "en-cours": "#0ea5e9", "done": "#2da862"}

router = APIRouter(prefix="/roadmap")


# ── Filesystem helpers ─────────────────────────────────────────────────────────

def _roadmap_dir(project: str) -> Path:
    base = project.split("~")[0]
    d = PROJECTS_BASE / base / "roadmap"
    d.mkdir(exist_ok=True)
    return d


def _item_path(project: str, item_id: str) -> Optional[Path]:
    rd = _roadmap_dir(project)
    # Doc libre référencé par son nom de fichier (stem)
    direct = rd / f"{item_id}.md"
    if direct.exists():
        return direct
    # Legacy : roadmap-{id}-{slug}.md, référencé par l'{id} numérique
    for f in rd.glob(f"roadmap-{item_id}-*.md"):
        return f
    # Filet : n'importe quel .md dont le stem correspond
    for f in rd.glob("*.md"):
        if f.stem == item_id:
            return f
    return None


def _parse_item(filepath: Path) -> dict:
    raw = filepath.read_text()
    fm: dict = {}
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    body = raw
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
        body = raw[m.end():].strip()
    fm["body"] = body
    fm["file"] = filepath.name
    # L'id de routage = TOUJOURS le nom de fichier (stem). Il résout de façon fiable via
    # _item_path, qu'il y ait ou non un `id:` dans le front-matter (docs libres compris).
    fm["id"] = filepath.stem
    # Date de secours pour les docs libres sans front-matter : mtime du fichier.
    fm.setdefault("created", datetime.fromtimestamp(filepath.stat().st_mtime).isoformat())

    # Aperçu : section « Direction (utilisateur) » si présente (## ou ###), sinon 1re ligne utile.
    user_m = re.search(r"##+ Direction ?(?:/ Feature )?\(utilisateur\)\n([\s\S]*?)(?:\n##|\Z)", body)
    if user_m:
        fm["preview"] = user_m.group(1).strip()[:120]
    else:
        preview = ""
        for ln in body.split("\n"):
            s = ln.strip()
            if not s or s.startswith(("#", ">", "---", "```", "|")):
                continue
            preview = s
            break
        fm["preview"] = (preview or body.strip())[:120]

    # Tickets liés : compter les références #id où qu'elles soient (sprints inclus), format-agnostique.
    fm["tickets_count"] = len(set(re.findall(r"#(\d{6,})", body)))

    return fm


def _parse_sprints(body: str) -> list[dict]:
    """Extrait les sprints d'un chantier : les `### …` sous la section `## Sprints`, avec leurs
    items de checklist. C'est la base de l'ordre de sprint généré pour Claude Code."""
    m = re.search(r"\n##\s+Sprints\s*\n(.*?)(?:\n##\s|\Z)", "\n" + body, re.S)
    if not m:
        return []
    section = m.group(1)
    sprints = []
    for part in re.split(r"\n###\s+", "\n" + section)[1:]:
        head, _, rest = part.partition("\n")
        items = [ln.rstrip() for ln in rest.split("\n") if re.match(r"\s*-\s*\[[ xX]\]", ln)]
        sprints.append({"name": head.strip(), "items": items})
    return sprints


def _generate_sprint_order(project: str, chantier_file: str, sprint: dict) -> str:
    """Ordre de sprint = document de passage Hub → Claude Code. Mince, jetable, écrasé à chaque
    génération. Le statut ne vit jamais ici : la source de vérité est le chantier."""
    proj = project.split("~")[0]
    lines = [
        f"# Ordre de sprint — {proj}",
        f"Chantier : roadmap/{chantier_file}",
        f"Sprint   : {sprint['name']}",
        "",
        "## Items",
        *(sprint["items"] or ["- [ ] (aucun item listé — voir le chantier)"]),
        "",
        f"> Déclencheur Claude Code : « exécute le sprint en cours pour {proj} »",
        "> Source de vérité = le chantier ci-dessus. Ce fichier est jetable (écrasé au prochain ordre).",
        "",
    ]
    return "\n".join(lines)


def _list_items(project: str) -> list[dict]:
    rd = _roadmap_dir(project)
    items = []
    # Tout fichier .md du dossier roadmap est un item (docs libres compris), plus récent en tête.
    for f in sorted(rd.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            items.append(_parse_item(f))
        except Exception:
            pass
    return items


def _create_item(project: str, title: str, description: str, constraints: str) -> str:
    rd = _roadmap_dir(project)
    item_id = int(time.time() * 1000)
    slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", title[:40].lower()))
    filename = f"roadmap-{item_id}-{slug}.md"

    lines = [
        "---",
        f"id: roadmap-{item_id}",
        "status: draft",
        f"created: {datetime.now().isoformat()}",
        f"project: {project.split('~')[0]}",
        "---",
        "",
        f"# Chantier — {title}",
        "",
        "## Direction (utilisateur)",
        description.strip() or "_Aucune description_",
        "",
    ]
    if constraints.strip():
        lines += ["## Contraintes connues", constraints.strip(), ""]
    lines += [
        "## Décisions",
        "*(Claude Code : ce qui est tranché ET ce qui reste à trancher — surface de validation, courte)*",
        "",
        "## Sprints",
        "*(Claude Code : sprints segmentés par contexte partagé ; la checklist EST le statut)*",
        "",
        "### Sprint 1 — {nom} · contexte partagé : {quoi}",
        "- [ ] {item} → #{ticket_id si délégué}",
        "",
        "## Annexe — contrats / specs détaillés",
        "*(le contrat exhaustif vit ici, pas dans la surface de validation)*",
        "",
    ]
    (rd / filename).write_text("\n".join(lines))
    return str(item_id)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _base_road(title: str, body: str, project: str, breadcrumbs: str = "") -> str:
    display = project.replace("~", " / ")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Roadmap</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh;font-size:14px}}
  a{{color:inherit;text-decoration:none}}
  header{{padding:1rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
  .logo{{color:#888;font-size:.9rem}}
  .logo a:hover{{color:#e8e8ea}}
  .sep{{color:#444}}
  .breadcrumb{{color:#888;font-size:.9rem}}
  .container{{max-width:860px;margin:0 auto;padding:2rem 1.5rem}}
  .btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
        border:none;cursor:pointer;font-size:.85rem;font-weight:500;transition:opacity .15s;white-space:nowrap}}
  .btn:hover{{opacity:.85}}
  .btn-primary{{background:#4f6ef7;color:#fff}}
  .btn-secondary{{background:#1e2130;color:#e8e8ea;border:1px solid #2a2d3a}}
  .btn-danger{{background:#dc2626;color:#fff}}
  .btn-sm{{padding:.3rem .65rem;font-size:.78rem}}
  .tag{{display:inline-block;padding:.2rem .55rem;border-radius:20px;font-size:.75rem;font-weight:600}}
  .page-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;gap:.75rem}}
  .page-title{{font-size:1.2rem;font-weight:700}}
  .item-card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1rem 1.25rem;
              margin-bottom:.75rem;transition:border-color .15s}}
  .item-card:hover{{border-color:#4f6ef7}}
  .item-title{{font-size:.95rem;font-weight:600;margin-bottom:.35rem}}
  .item-preview{{font-size:.82rem;color:#888;margin-bottom:.5rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .item-meta{{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}}
  .item-date{{font-size:.72rem;color:#555}}
  label{{display:block;font-size:.75rem;color:#888;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.04em}}
  input[type=text],select,textarea{{width:100%;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;
    padding:.65rem .9rem;color:#e8e8ea;font-size:.9rem;outline:none;font-family:inherit}}
  input:focus,select:focus,textarea:focus{{border-color:#4f6ef7}}
  select option{{background:#1a1d27}}
  textarea{{resize:vertical;font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.6}}
  .form-group{{margin-bottom:1.1rem}}
  .section{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1.2rem;margin-bottom:1.1rem}}
  .section-title{{font-size:.78rem;font-weight:600;color:#888;margin-bottom:.9rem;text-transform:uppercase;letter-spacing:.06em}}
  .empty{{color:#555;font-size:.82rem;font-style:italic}}
  .alert{{padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.85rem}}
  .alert-success{{background:rgba(45,168,98,.12);border:1px solid rgba(45,168,98,.3);color:#2da862}}
  .divider{{border:none;border-top:1px solid #1e2130;margin:1.25rem 0}}
  pre{{background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:1rem;
       font-size:.78rem;line-height:1.6;overflow-x:auto;white-space:pre-wrap;color:#bbb}}
  .hint{{font-size:.78rem;color:#555;margin-top:.4rem}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <a href="/">JLM VPS</a> <span class="sep">/</span>
    <a href="/tickets">Tickets</a> <span class="sep">/</span>
    <a href="/tickets/{_e(project)}">{_e(display)}</a> <span class="sep">/</span>
    <span class="breadcrumb">Roadmap</span>
  </div>
  {breadcrumbs}
</header>
<div class="container">{body}</div>
</body>
</html>"""


def _status_badge(status: str) -> str:
    color = STATUS_COLOR.get(status, "#6b7280")
    label = STATUS_LABEL.get(status, status)
    return f'<span class="tag" style="background:{color}22;color:{color}">{_e(label)}</span>'


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except Exception:
        return iso


# ── Pages ──────────────────────────────────────────────────────────────────────

def _page_list(project: str, items: list) -> str:
    display = project.replace("~", " / ")

    by_status = {"draft": [], "spec-ready": [], "tickets-created": [], "done": []}
    for item in items:
        by_status.setdefault(item.get("status", "draft"), []).append(item)

    sections = ""
    for status, label in [
        ("draft", "📝 Brouillons"),
        ("spec-ready", "📐 Spec prête"),
        ("tickets-created", "🎫 Tickets créés"),
        ("done", "✅ Terminés"),
    ]:
        group = by_status.get(status, [])
        if not group:
            continue
        cards = ""
        for item in group:
            iid = item.get("id", "")
            preview = _e(item.get("preview", "")[:100])
            date = _fmt_date(item.get("created", ""))
            tc = item.get("tickets_count", 0)
            tc_html = f'<span class="tag" style="background:rgba(79,110,247,.12);color:#818cf8">{tc} ticket{"s" if tc!=1 else ""}</span>' if tc else ""
            cards += f"""
<a href="/roadmap/{_e(project)}/{_e(iid)}/edit" style="display:block">
  <div class="item-card">
    <div class="item-title">{_e(item.get("body","").split(chr(10))[0].lstrip("# ") or iid)}</div>
    <div class="item-preview">{preview}</div>
    <div class="item-meta">
      {_status_badge(status)}
      {tc_html}
      <span class="item-date">{date}</span>
    </div>
  </div>
</a>"""
        sections += f'<h3 style="font-size:.85rem;color:#888;margin:1.25rem 0 .6rem;text-transform:uppercase;letter-spacing:.05em">{label}</h3>{cards}'

    if not items:
        sections = '<p class="empty">Aucun item de roadmap pour ce projet.</p>'

    body = f"""
<div class="page-header">
  <div class="page-title">🗺 Roadmap — {_e(display)}</div>
  <div style="display:flex;gap:.5rem">
    <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Tickets</a>
    <a href="/roadmap/{_e(project)}/new" class="btn btn-primary">+ Nouvelle direction</a>
  </div>
</div>
<div class="alert" style="background:rgba(79,110,247,.08);border:1px solid rgba(79,110,247,.2);color:#818cf8;font-size:.82rem;margin-bottom:1.25rem">
  💡 Une direction devient un <strong>chantier</strong> : Claude y écrit les décisions puis le
  découpe en <strong>sprints</strong>. Ouvre un chantier, puis génère l'ordre du sprint à exécuter
  (écrit <code>SESSION.md</code>, déclenché ensuite dans Claude Code).
</div>
{sections}"""
    return _base_road(f"Roadmap — {display}", body, project)


def _page_new(project: str, error: str = "") -> str:
    err_html = f'<div class="alert" style="background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);color:#f87171">{_e(error)}</div>' if error else ""
    body = f"""
<div class="page-header">
  <div class="page-title">Nouvelle direction</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>
{err_html}
<form method="POST" action="/roadmap/{_e(project)}/new">
  <div class="section">
    <div class="form-group">
      <label>Titre</label>
      <input type="text" name="title" placeholder="ex: Refonte UX page budget — mobile + graphiques" required>
    </div>
    <div class="form-group">
      <label>Direction / Description</label>
      <textarea name="description" rows="6"
        placeholder="Décris ce que tu veux obtenir. Claude se chargera de définir comment.&#10;&#10;ex: Je veux que la page budget soit utilisable sur mobile avec des graphiques d'évolution mensuelle et une comparaison N/N-1."></textarea>
      <div class="hint">Pas besoin d'être précis — Claude analysera le code existant et proposera une spec détaillée.</div>
    </div>
    <div class="form-group">
      <label>Contraintes connues (optionnel)</label>
      <textarea name="constraints" rows="3"
        placeholder="ex: Pas de migration DB. Garder la compatibilité avec l'export Excel."></textarea>
    </div>
    <button type="submit" class="btn btn-primary">Créer</button>
  </div>
</form>"""
    return _base_road("Nouvelle direction", body, project)


def _page_edit(project: str, item: dict, flash: str = "") -> str:
    iid    = item.get("id", "")
    status = item.get("status", "draft")
    body_md = item.get("body", "")
    proj = project.split("~")[0]

    if flash == "saved":
        flash_html = '<div class="alert alert-success">✓ Sauvegardé.</div>'
    elif flash == "order":
        flash_html = (f'<div class="alert alert-success">✓ <code>SESSION.md</code> généré. '
                      f'Dans Claude Code : <strong>« exécute le sprint en cours pour {_e(proj)} »</strong></div>')
    else:
        flash_html = ""

    sprints = _parse_sprints(body_md)
    if sprints:
        rows = ""
        for s in sprints:
            n = len(s["items"])
            rows += f"""
<div style="display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;background:#0f1117;
     border:1px solid #2a2d3a;border-radius:8px;margin-bottom:.4rem">
  <div style="flex:1;min-width:0">
    <div style="font-size:.88rem;font-weight:600">{_e(s['name'])}</div>
    <div style="font-size:.75rem;color:#666">{n} item{'s' if n!=1 else ''}</div>
  </div>
  <form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/sprint-order" style="margin:0">
    <input type="hidden" name="sprint" value="{_e(s['name'])}">
    <button type="submit" class="btn btn-primary btn-sm">⚡ Générer l'ordre</button>
  </form>
</div>"""
        sprints_html = (f'<div class="section"><div class="section-title">'
                        f"Sprints — générer l'ordre (SESSION.md)</div>{rows}</div>")
    else:
        sprints_html = ('<div class="section"><div class="section-title">Sprints</div>'
                        '<p class="empty">Pas encore de sprints. Claude les ajoute dans la section '
                        '<code>## Sprints</code> du chantier.</p></div>')

    status_opts = "".join(
        f'<option value="{s}" {"selected" if s==status else ""}>{STATUS_LABEL[s]}</option>'
        for s in STATUS_LABEL
    )
    title_line = body_md.split("\n")[0].lstrip("# ").strip() if body_md else iid

    body = f"""
{flash_html}
<div class="page-header">
  <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
    <div class="page-title">{_e(title_line)}</div>
    {_status_badge(status)}
  </div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Roadmap</a>
</div>

{sprints_html}

<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/edit">
  <div class="section">
    <div class="section-title">Statut</div>
    <div class="form-group" style="max-width:220px">
      <select name="status">{status_opts}</select>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Contenu (Markdown)</div>
    <div class="hint" style="margin-bottom:.75rem">
      La section <code>### Spec générée</code> est remplie par Claude Code.
      La section <code>### Tickets créés</code> liste les tickets générés.
    </div>
    <div class="form-group">
      <textarea name="body" rows="28">{_e(body_md)}</textarea>
    </div>
  </div>
  <div style="display:flex;gap:.75rem;flex-wrap:wrap">
    <button type="submit" class="btn btn-primary">💾 Sauvegarder</button>
  </div>
</form>

<hr class="divider">
<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/delete"
      onsubmit="return confirm('Supprimer cet item de roadmap ?')">
  <button type="submit" class="btn btn-danger btn-sm">Supprimer cet item</button>
</form>"""
    return _base_road(title_line, body, project)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _require_auth(request: Request, settings):
    from app.auth import get_session, redirect_to_login
    if not get_session(request, settings.SESSION_SECRET):
        return redirect_to_login(str(request.url.path))
    return None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/{project}", response_class=HTMLResponse)
async def roadmap_list(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_list(project, _list_items(project)))


@router.get("/{project}/new", response_class=HTMLResponse)
async def roadmap_new_get(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_new(project))


@router.post("/{project}/new")
async def roadmap_new_post(
    request: Request, project: str,
    title: str = Form(...),
    description: str = Form(default=""),
    constraints: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if not title.strip():
        return HTMLResponse(_page_new(project, "Le titre est obligatoire."), status_code=400)
    iid = _create_item(project, title.strip(), description.strip(), constraints.strip())
    return RedirectResponse(f"/roadmap/{project}/{iid}/edit?flash=saved", status_code=303)


@router.get("/{project}/{item_id}/edit", response_class=HTMLResponse)
async def roadmap_edit_get(request: Request, project: str, item_id: str, flash: str = ""):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)
    return HTMLResponse(_page_edit(project, _parse_item(path), flash))


@router.post("/{project}/{item_id}/edit")
async def roadmap_edit_post(
    request: Request, project: str, item_id: str,
    status: str = Form(...), body: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)

    raw = path.read_text()
    fm: dict = {}
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()

    fm["status"] = status if status in STATUS_LABEL else fm.get("status", "draft")

    fm_lines = ["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", body.strip()]
    path.write_text("\n".join(fm_lines))
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=saved", status_code=303)


@router.post("/{project}/{item_id}/sprint-order")
async def roadmap_sprint_order(request: Request, project: str, item_id: str, sprint: str = Form(...)):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)
    item = _parse_item(path)
    match = next((s for s in _parse_sprints(item.get("body", "")) if s["name"] == sprint), None)
    if not match:
        return HTMLResponse(f"Sprint introuvable : {_e(sprint)}", status_code=404)
    content = _generate_sprint_order(project, path.name, match)
    (PROJECTS_BASE / project.split("~")[0] / "SESSION.md").write_text(content)
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=order", status_code=303)


@router.post("/{project}/{item_id}/delete")
async def roadmap_delete(request: Request, project: str, item_id: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if path and path.exists():
        path.unlink()
    return RedirectResponse(f"/roadmap/{project}", status_code=303)
