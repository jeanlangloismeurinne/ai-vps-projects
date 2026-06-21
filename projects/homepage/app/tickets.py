import os
import re
import time
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response

PROJECTS_BASE = Path(os.environ.get("PROJECTS_DIR", "/projects"))
MAX_SPEC_SIZE = 10 * 1024 * 1024  # 10 MB

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
TYPE_LABEL = {"bug": "Bug", "feature": "Feature", "suggestion": "Suggestion", "error": "Erreur JS"}
STATUS_COLOR = {"open": "#f59e0b", "closed": "#2da862"}
STATUS_LABEL = {"open": "Ouvert", "closed": "Fermé"}

router = APIRouter(prefix="/tickets")


# ── Filesystem helpers ─────────────────────────────────────────────────────────

def _feedback_dir(project: str) -> Optional[Path]:
    if "~" in project:
        base, sub = project.split("~", 1)
        d = PROJECTS_BASE / base / "feedback-tickets" / sub
    else:
        d = PROJECTS_BASE / project / "feedback-tickets"
    return d if d.is_dir() else None


def _ticket_path(project: str, ticket_id: str) -> Optional[Path]:
    fd = _feedback_dir(project)
    if not fd:
        return None
    for f in fd.glob(f"{ticket_id}-*.md"):
        return f
    return None


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    fm: dict = {}
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
        body = raw[m.end():].strip()
    else:
        body = raw.strip()
    return fm, body


def _build_file(fm: dict, body: str) -> str:
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def _parse_ticket(filepath: Path) -> dict:
    raw = filepath.read_text()
    fm, body = _parse_frontmatter(raw)
    fm["body"] = body
    fm["file"] = filepath.name
    fm.setdefault("id", filepath.stem.split("-")[0])
    desc_m = re.search(r"### Description\n\n([\s\S]*?)(?:\n###|\Z)", body)
    fm["description"] = desc_m.group(1).strip()[:150] if desc_m else ""
    return fm


def _list_tickets(project: str) -> list[dict]:
    fd = _feedback_dir(project)
    if not fd:
        return []
    tickets = []
    for f in sorted(fd.glob("*.md"), reverse=True):
        try:
            tickets.append(_parse_ticket(f))
        except Exception:
            pass
    return tickets


def _list_specs(project: str, ticket_id: str) -> list[str]:
    fd = _feedback_dir(project)
    if not fd:
        return []
    return sorted(f.name for f in fd.glob(f"{ticket_id}-spec-*"))


def _list_projects() -> list[dict]:
    if not PROJECTS_BASE.exists():
        return []
    projects = []
    for p in sorted(PROJECTS_BASE.iterdir()):
        if not p.is_dir():
            continue
        fd = p / "feedback-tickets"
        if not fd.is_dir():
            continue

        root_md = list(fd.glob("*.md"))
        if root_md:
            open_count = sum(1 for f in root_md if "status: open" in f.read_text())
            projects.append({
                "name": p.name,
                "total": len(root_md),
                "open": open_count,
                "closed": len(root_md) - open_count,
            })

        for sub in sorted(fd.iterdir()):
            if not sub.is_dir():
                continue
            sub_md = list(sub.glob("*.md"))
            if not sub_md:
                continue
            open_count = sum(1 for f in sub_md if "status: open" in f.read_text())
            projects.append({
                "name": f"{p.name}~{sub.name}",
                "total": len(sub_md),
                "open": open_count,
                "closed": len(sub_md) - open_count,
            })

    return projects


def _regenerate_tickets_md(project: str):
    fd = _feedback_dir(project)
    if not fd:
        return
    tickets = []
    for f in sorted(fd.glob("*.md"), reverse=True):
        try:
            tickets.append(_parse_ticket(f))
        except Exception:
            pass

    open_t = [t for t in tickets if t.get("status") == "open"]
    closed_t = [t for t in tickets if t.get("status") != "open"]

    def fmt_date(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return "?"

    def rows(items: list) -> str:
        if not items:
            return "_Aucun_\n"
        header = "| ID | Date | URL | Description |\n|---|---|---|---|\n"
        r = []
        for t in items:
            desc = (t.get("description") or "").replace("|", "\\|")[:80]
            url = (t.get("url") or "")[:50]
            r.append(f"| `{t.get('id','')}` | {fmt_date(t.get('date',''))} | `{url}` | {desc} |")
        return header + "\n".join(r) + "\n"

    def cnt(lst, typ): return sum(1 for t in lst if t.get("type") == typ)

    bugs = [t for t in open_t if t.get("type") in ("bug", "error")]
    features = [t for t in open_t if t.get("type") == "feature"]
    suggestions = [t for t in open_t if t.get("type") == "suggestion"]

    md = [
        f"# TICKETS — {project}",
        "",
        f"> Généré automatiquement le {datetime.now().strftime('%d/%m/%Y %H:%M')}. **Lire au début de chaque session.**",
        "",
        "## Résumé",
        "",
        "| Type | Ouverts | Fermés |",
        "|---|---|---|",
        f"| 🐛 Bugs | {cnt(open_t,'bug')} | {cnt(closed_t,'bug')} |",
        f"| 🔴 Erreurs JS | {cnt(open_t,'error')} | {cnt(closed_t,'error')} |",
        f"| ✨ Features | {cnt(open_t,'feature')} | {cnt(closed_t,'feature')} |",
        f"| 💡 Suggestions | {cnt(open_t,'suggestion')} | {cnt(closed_t,'suggestion')} |",
        "",
    ]
    if bugs:
        md += ["## 🐛 Bugs & Erreurs JS ouverts", "", rows(bugs)]
    if features:
        md += ["## ✨ Features demandées", "", rows(features)]
    if suggestions:
        md += ["## 💡 Suggestions ouvertes", "", rows(suggestions)]
    if closed_t:
        md += [f"## ✅ Fermés ({len(closed_t)})", "", rows(closed_t)]
    if not tickets:
        md += ["_Aucun ticket pour l'instant._", ""]

    tickets_md = PROJECTS_BASE / project / "TICKETS.md"
    tickets_md.write_text("\n".join(md))


def _create_ticket(project: str, type_: str, message: str, url: str) -> str:
    fd = _feedback_dir(project)
    if not fd:
        fd = PROJECTS_BASE / project / "feedback-tickets"
        fd.mkdir(parents=True, exist_ok=True)

    ticket_id = int(time.time() * 1000)
    slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", message[:40].lower()))
    filename = f"{ticket_id}-{type_}-{slug}.md"

    emoji = TYPE_EMOJI.get(type_, "📝")
    label = TYPE_LABEL.get(type_, type_)
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "---",
        f"id: {ticket_id}",
        f"type: {type_}",
        "status: open",
        f"date: {datetime.now().isoformat()}",
        f"project: {project}",
        f"url: {url}",
        "---",
        "",
        f"## {emoji} {label}",
        "",
        f"**Date** : {date_str}",
        f"**URL** : `{url or 'N/A'}`",
        "",
        "### Description",
        "",
        message or "_Aucune description_",
        "",
    ]
    (fd / filename).write_text("\n".join(lines))
    _regenerate_tickets_md(project)
    return str(ticket_id)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return (s
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;"))


def _base(title: str, body: str, breadcrumbs: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Tickets</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh;font-size:14px}}
  a{{color:inherit;text-decoration:none}}
  header{{padding:1rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem}}
  header .logo{{color:#888;font-size:.9rem}}
  header .logo a:hover{{color:#e8e8ea}}
  .sep{{color:#444}}
  .breadcrumb{{font-size:.9rem;color:#888}}
  .breadcrumb .current{{color:#e8e8ea;font-weight:600}}
  .container{{max-width:900px;margin:0 auto;padding:2rem 1.5rem}}
  .btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
        border:none;cursor:pointer;font-size:.85rem;font-weight:500;transition:opacity .15s}}
  .btn:hover{{opacity:.85}}
  .btn-primary{{background:#4f6ef7;color:#fff}}
  .btn-secondary{{background:#1e2130;color:#e8e8ea;border:1px solid #2a2d3a}}
  .btn-danger{{background:#dc2626;color:#fff}}
  .btn-success{{background:#2da862;color:#fff}}
  .tag{{display:inline-block;padding:.2rem .55rem;border-radius:20px;font-size:.75rem;font-weight:600;white-space:nowrap}}
  .tag-open{{background:rgba(245,158,11,.15);color:#f59e0b}}
  .tag-closed{{background:rgba(45,168,98,.15);color:#2da862}}
  .tag-bug{{background:rgba(220,38,38,.12);color:#f87171}}
  .tag-feature{{background:rgba(139,92,246,.12);color:#a78bfa}}
  .tag-suggestion{{background:rgba(59,130,246,.12);color:#60a5fa}}
  .tag-error{{background:rgba(220,38,38,.12);color:#f87171}}
  .filter-row{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.5rem}}
  .filter-btn{{padding:.35rem .8rem;border-radius:20px;font-size:.8rem;border:1px solid #2a2d3a;
               background:#1a1d27;color:#888;cursor:pointer;transition:all .15s}}
  .filter-btn.active{{background:#4f6ef7;color:#fff;border-color:#4f6ef7}}
  .filter-btn:hover:not(.active){{border-color:#4f6ef7;color:#e8e8ea}}
  .page-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem}}
  .page-title{{font-size:1.3rem;font-weight:700}}
  .card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1rem 1.25rem;
          margin-bottom:.75rem;transition:border-color .15s}}
  .card:hover{{border-color:#4f6ef7}}
  .card-row{{display:flex;align-items:center;gap:.75rem}}
  .card-meta{{font-size:.75rem;color:#666;white-space:nowrap}}
  .card-desc{{color:#bbb;font-size:.85rem;margin-top:.4rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .card-link{{display:block}}
  label{{display:block;font-size:.75rem;color:#888;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.04em}}
  input,select,textarea{{width:100%;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;
                         padding:.65rem .9rem;color:#e8e8ea;font-size:.9rem;outline:none;font-family:inherit}}
  input:focus,select:focus,textarea:focus{{border-color:#4f6ef7}}
  select option{{background:#1a1d27}}
  textarea{{resize:vertical;font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.5}}
  .form-group{{margin-bottom:1.25rem}}
  .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
  .section{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1.25rem;margin-bottom:1.25rem}}
  .section-title{{font-size:.85rem;font-weight:600;color:#aaa;margin-bottom:1rem;
                  text-transform:uppercase;letter-spacing:.05em}}
  .spec-list{{display:flex;flex-direction:column;gap:.5rem;margin-bottom:1rem}}
  .spec-item{{display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;
              background:#0f1117;border-radius:8px;border:1px solid #2a2d3a}}
  .spec-name{{flex:1;font-size:.85rem;color:#bbb}}
  .empty{{color:#555;font-size:.85rem;font-style:italic;padding:.5rem 0}}
  .project-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}}
  .project-card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:14px;padding:1.25rem 1.5rem;
                 transition:border-color .2s,transform .15s;cursor:pointer}}
  .project-card:hover{{border-color:#4f6ef7;transform:translateY(-2px)}}
  .project-name{{font-size:1rem;font-weight:600;margin-bottom:.5rem}}
  .project-counts{{display:flex;gap:.75rem}}
  .count-open{{font-size:.85rem;color:#f59e0b;font-weight:600}}
  .count-closed{{font-size:.85rem;color:#555}}
  .alert{{padding:.75rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.85rem}}
  .alert-success{{background:rgba(45,168,98,.12);border:1px solid rgba(45,168,98,.3);color:#2da862}}
  .alert-error{{background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);color:#f87171}}
  .ticket-actions{{display:flex;gap:.75rem;align-items:center}}
  .divider{{border:none;border-top:1px solid #1e2130;margin:1.5rem 0}}
  @media(max-width:600px){{.form-row{{grid-template-columns:1fr}}.project-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
  <div class="logo"><a href="/">JLM VPS</a> <span class="sep">/</span> <a href="/tickets">Tickets</a></div>
  {breadcrumbs}
</header>
<div class="container">{body}</div>
</body>
</html>"""


def _type_tag(type_: str) -> str:
    emoji = TYPE_EMOJI.get(type_, "📝")
    label = TYPE_LABEL.get(type_, type_)
    return f'<span class="tag tag-{_e(type_)}">{emoji} {_e(label)}</span>'


def _status_tag(status: str) -> str:
    label = STATUS_LABEL.get(status, status)
    cls = "tag-open" if status == "open" else "tag-closed"
    return f'<span class="tag {cls}">{_e(label)}</span>'


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso


# ── Page: projects list ────────────────────────────────────────────────────────

def _page_projects(projects: list) -> str:
    if not projects:
        cards = '<p class="empty">Aucun projet avec des tickets trouvé.</p>'
    else:
        cards = '<div class="project-grid">'
        for p in projects:
            display = _e(p['name'].replace("~", " / "))
        cards += f"""
        <a href="/tickets/{_e(p['name'])}" class="project-card">
          <div class="project-name">{display}</div>
          <div class="project-counts">
            <span class="count-open">{p['open']} ouvert{'s' if p['open']!=1 else ''}</span>
            <span class="count-closed">· {p['closed']} fermé{'s' if p['closed']!=1 else ''}</span>
          </div>
        </a>"""
        cards += "</div>"

    body = f"""
<div class="page-header">
  <div class="page-title">🎫 Gestion des tickets</div>
</div>
{cards}"""
    return _base("Tickets", body)


# ── Page: ticket list ──────────────────────────────────────────────────────────

def _page_ticket_list(project: str, tickets: list, status_f: str, type_f: str) -> str:
    def filter_url(s: str = None, t: str = None) -> str:
        s = s if s is not None else status_f
        t = t if t is not None else type_f
        params = []
        if s != "all":
            params.append(f"status={s}")
        if t != "all":
            params.append(f"type={t}")
        base = f"/tickets/{project}"
        return base + ("?" + "&".join(params) if params else "")

    filtered = tickets
    if status_f != "all":
        filtered = [t for t in filtered if t.get("status") == status_f]
    if type_f != "all":
        filtered = [t for t in filtered if t.get("type") == type_f]

    all_open = sum(1 for t in tickets if t.get("status") == "open")
    all_closed = len(tickets) - all_open

    def fbtn(label: str, s: str = None, t: str = None, active: bool = False) -> str:
        url = filter_url(s, t)
        cls = "filter-btn active" if active else "filter-btn"
        return f'<a href="{url}" class="{cls}">{label}</a>'

    status_btns = (
        fbtn(f"Tout ({len(tickets)})", s="all", t=type_f, active=status_f == "all") +
        fbtn(f"Ouverts ({all_open})", s="open", t=type_f, active=status_f == "open") +
        fbtn(f"Fermés ({all_closed})", s="closed", t=type_f, active=status_f == "closed")
    )

    type_counts = {}
    for t in tickets:
        tp = t.get("type", "")
        type_counts[tp] = type_counts.get(tp, 0) + 1

    type_btns = fbtn(f"Tous types ({len(tickets)})", t="all", s=status_f, active=type_f == "all")
    for tp in ["bug", "feature", "suggestion", "error"]:
        if tp in type_counts:
            emoji = TYPE_EMOJI[tp]
            label = TYPE_LABEL[tp]
            type_btns += fbtn(f"{emoji} {label} ({type_counts[tp]})", t=tp, s=status_f, active=type_f == tp)

    cards = ""
    if not filtered:
        cards = '<p class="empty">Aucun ticket pour ce filtre.</p>'
    else:
        for t in filtered:
            tid = t.get("id", "")
            type_ = t.get("type", "")
            status = t.get("status", "open")
            desc = _e(t.get("description", "")[:120])
            date = _fmt_date(t.get("date", ""))
            cards += f"""
<a href="/tickets/{_e(project)}/{_e(tid)}/edit" class="card-link">
  <div class="card">
    <div class="card-row">
      {_type_tag(type_)}
      {_status_tag(status)}
      <span class="card-meta" style="margin-left:auto">{_e(date)}</span>
    </div>
    {"" if not desc else f'<div class="card-desc">{desc}</div>'}
  </div>
</a>"""

    display = project.replace("~", " / ")
    breadcrumbs = f'<span class="sep">/</span> <span class="breadcrumb current">{_e(display)}</span>'
    body = f"""
<div class="page-header">
  <div class="page-title">{_e(display)}</div>
  <a href="/tickets/{_e(project)}/new" class="btn btn-primary">+ Nouveau ticket</a>
</div>
<div class="filter-row">{status_btns}</div>
<div class="filter-row">{type_btns}</div>
{cards}"""
    return _base(project, body, breadcrumbs)


# ── Page: new ticket ───────────────────────────────────────────────────────────

def _page_new(project: str, error: str = "") -> str:
    display = project.replace("~", " / ")
    err_html = f'<div class="alert alert-error">{_e(error)}</div>' if error else ""
    type_opts = "".join(
        f'<option value="{k}">{v} {TYPE_LABEL[k]}</option>'
        for k, v in TYPE_EMOJI.items()
    )
    breadcrumbs = (
        f'<span class="sep">/</span> <a href="/tickets/{_e(project)}" class="breadcrumb">{_e(display)}</a>'
        f' <span class="sep">/</span> <span class="breadcrumb current">Nouveau</span>'
    )
    body = f"""
<div class="page-header">
  <div class="page-title">Nouveau ticket — {_e(display)}</div>
  <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>
{err_html}
<form method="POST" action="/tickets/{_e(project)}/new">
  <div class="section">
    <div class="form-row">
      <div class="form-group">
        <label>Type</label>
        <select name="type">{type_opts}</select>
      </div>
      <div class="form-group">
        <label>URL (optionnel)</label>
        <input type="text" name="url" placeholder="https://...">
      </div>
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea name="message" rows="8" placeholder="Décrivez le bug, la feature ou la suggestion..."></textarea>
    </div>
    <button type="submit" class="btn btn-primary">Créer le ticket</button>
  </div>
</form>"""
    return _base("Nouveau ticket", body, breadcrumbs)


# ── Page: edit ticket ──────────────────────────────────────────────────────────

def _page_edit(project: str, ticket: dict, specs: list, flash: str = "") -> str:
    tid = ticket.get("id", "")
    type_ = ticket.get("type", "bug")
    status = ticket.get("status", "open")
    body_md = ticket.get("body", "")

    flash_html = ""
    if flash == "saved":
        flash_html = '<div class="alert alert-success">✓ Ticket sauvegardé.</div>'
    elif flash == "spec_uploaded":
        flash_html = '<div class="alert alert-success">✓ Fichier attaché.</div>'
    elif flash == "spec_deleted":
        flash_html = '<div class="alert alert-success">✓ Fichier supprimé.</div>'

    type_opts = "".join(
        f'<option value="{k}" {"selected" if k == type_ else ""}>{TYPE_EMOJI[k]} {TYPE_LABEL[k]}</option>'
        for k in TYPE_EMOJI
    )
    status_opts = "".join(
        f'<option value="{s}" {"selected" if s == status else ""}>{STATUS_LABEL[s]}</option>'
        for s in ["open", "closed"]
    )

    specs_html = ""
    if specs:
        items = ""
        for s in specs:
            display = s[len(f"{tid}-spec-"):]
            items += f"""
<div class="spec-item">
  <span class="spec-name">📎 {_e(display)}</span>
  <a href="/tickets/{_e(project)}/{_e(tid)}/spec/{_e(s)}" class="btn btn-secondary" style="padding:.3rem .7rem;font-size:.75rem">Télécharger</a>
  <form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/spec/{_e(s)}/delete" style="margin:0">
    <button type="submit" class="btn btn-danger" style="padding:.3rem .6rem;font-size:.75rem">✕</button>
  </form>
</div>"""
        specs_html = f'<div class="spec-list">{items}</div>'
    else:
        specs_html = '<p class="empty">Aucun fichier attaché.</p>'

    proj_display = project.replace("~", " / ")
    breadcrumbs = (
        f'<span class="sep">/</span> <a href="/tickets/{_e(project)}" class="breadcrumb">{_e(proj_display)}</a>'
        f' <span class="sep">/</span> <span class="breadcrumb current">#{_e(str(tid))}</span>'
    )
    body = f"""
{flash_html}
<div class="page-header">
  <div class="page-title"># {_e(str(tid))}</div>
  <div class="ticket-actions">
    {_type_tag(type_)} {_status_tag(status)}
    <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Retour</a>
  </div>
</div>

<form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/edit">
  <div class="section">
    <div class="section-title">Métadonnées</div>
    <div class="form-row">
      <div class="form-group">
        <label>Type</label>
        <select name="type">{type_opts}</select>
      </div>
      <div class="form-group">
        <label>Statut</label>
        <select name="status">{status_opts}</select>
      </div>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Contenu (Markdown)</div>
    <div class="form-group">
      <textarea name="body" rows="18">{_e(body_md)}</textarea>
    </div>
  </div>
  <button type="submit" class="btn btn-primary">💾 Sauvegarder</button>
</form>

<hr class="divider">

<div class="section">
  <div class="section-title">Specs / Documents attachés</div>
  {specs_html}
  <form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/spec" enctype="multipart/form-data">
    <div class="form-row" style="align-items:flex-end">
      <div class="form-group" style="margin-bottom:0">
        <label>Joindre un fichier (max 10 Mo)</label>
        <input type="file" name="file" accept="*/*">
      </div>
      <div>
        <button type="submit" class="btn btn-secondary">📎 Uploader</button>
      </div>
    </div>
  </form>
</div>"""
    return _base(f"#{tid}", body, breadcrumbs)


# ── Routes ─────────────────────────────────────────────────────────────────────

def _require_auth(request: Request, settings):
    from app.auth import get_session, redirect_to_login
    if not get_session(request, settings.SESSION_SECRET):
        return redirect_to_login(str(request.url.path))
    return None


@router.get("", response_class=HTMLResponse)
async def tickets_index(request: Request):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    projects = _list_projects()
    return HTMLResponse(_page_projects(projects))


@router.get("/{project}", response_class=HTMLResponse)
async def ticket_list(
    request: Request,
    project: str,
    status: str = "all",
    type: str = "all",
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    fd = _feedback_dir(project)
    if fd is None:
        return HTMLResponse(f"<h1>Projet introuvable : {_e(project)}</h1>", status_code=404)
    tickets = _list_tickets(project)
    return HTMLResponse(_page_ticket_list(project, tickets, status, type))


@router.get("/{project}/new", response_class=HTMLResponse)
async def ticket_new_get(request: Request, project: str):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    if _feedback_dir(project) is None:
        return HTMLResponse(f"Projet introuvable : {_e(project)}", status_code=404)
    return HTMLResponse(_page_new(project))


@router.post("/{project}/new")
async def ticket_new_post(
    request: Request,
    project: str,
    type: str = Form(...),
    message: str = Form(default=""),
    url: str = Form(default=""),
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    if type not in TYPE_EMOJI:
        return HTMLResponse(_page_new(project, "Type invalide."), status_code=400)
    if not message.strip() and type != "error":
        return HTMLResponse(_page_new(project, "La description est obligatoire."), status_code=400)
    tid = _create_ticket(project, type, message.strip(), url.strip())
    return RedirectResponse(f"/tickets/{project}/{tid}/edit?flash=saved", status_code=303)


@router.get("/{project}/{ticket_id}/edit", response_class=HTMLResponse)
async def ticket_edit_get(request: Request, project: str, ticket_id: str, flash: str = ""):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    path = _ticket_path(project, ticket_id)
    if not path:
        return HTMLResponse(f"Ticket introuvable : {_e(ticket_id)}", status_code=404)
    ticket = _parse_ticket(path)
    specs = _list_specs(project, ticket_id)
    return HTMLResponse(_page_edit(project, ticket, specs, flash))


@router.post("/{project}/{ticket_id}/edit")
async def ticket_edit_post(
    request: Request,
    project: str,
    ticket_id: str,
    type: str = Form(...),
    status: str = Form(...),
    body: str = Form(default=""),
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    path = _ticket_path(project, ticket_id)
    if not path:
        return HTMLResponse(f"Ticket introuvable : {_e(ticket_id)}", status_code=404)

    raw = path.read_text()
    fm, _ = _parse_frontmatter(raw)

    fm["type"] = type if type in TYPE_EMOJI else fm.get("type", "bug")

    prev_status = fm.get("status", "open")
    fm["status"] = status if status in ("open", "closed") else prev_status

    if status == "closed" and prev_status != "closed":
        fm["closed_at"] = datetime.now(timezone.utc).isoformat()
    elif status == "open" and "closed_at" in fm:
        del fm["closed_at"]

    path.write_text(_build_file(fm, body.strip()))
    _regenerate_tickets_md(project)

    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=saved", status_code=303)


@router.post("/{project}/{ticket_id}/spec")
async def ticket_spec_upload(
    request: Request,
    project: str,
    ticket_id: str,
    file: UploadFile = File(...),
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    fd = _feedback_dir(project)
    if not fd:
        return HTMLResponse("Projet introuvable", status_code=404)
    if not _ticket_path(project, ticket_id):
        return HTMLResponse("Ticket introuvable", status_code=404)

    data = await file.read()
    if len(data) > MAX_SPEC_SIZE:
        return HTMLResponse("Fichier trop volumineux (max 10 Mo)", status_code=413)

    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "upload")
    spec_path = fd / f"{ticket_id}-spec-{safe_name}"
    spec_path.write_bytes(data)

    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=spec_uploaded", status_code=303)


@router.get("/{project}/{ticket_id}/spec/{filename}")
async def ticket_spec_download(
    request: Request,
    project: str,
    ticket_id: str,
    filename: str,
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    fd = _feedback_dir(project)
    if not fd:
        return HTMLResponse("Projet introuvable", status_code=404)

    # Safety: only allow files matching the ticket_id-spec- pattern
    if not filename.startswith(f"{ticket_id}-spec-"):
        return HTMLResponse("Accès refusé", status_code=403)

    spec_path = fd / filename
    if not spec_path.exists() or not spec_path.is_file():
        return HTMLResponse("Fichier introuvable", status_code=404)

    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"
    display_name = filename[len(f"{ticket_id}-spec-"):]

    return Response(
        content=spec_path.read_bytes(),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{display_name}"'},
    )


@router.post("/{project}/{ticket_id}/spec/{filename}/delete")
async def ticket_spec_delete(
    request: Request,
    project: str,
    ticket_id: str,
    filename: str,
):
    from app.main import settings
    if redir := _require_auth(request, settings):
        return redir
    fd = _feedback_dir(project)
    if not fd:
        return HTMLResponse("Projet introuvable", status_code=404)

    if not filename.startswith(f"{ticket_id}-spec-"):
        return HTMLResponse("Accès refusé", status_code=403)

    spec_path = fd / filename
    if spec_path.exists() and spec_path.is_file():
        spec_path.unlink()

    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=spec_deleted", status_code=303)
