import os
import re
import time
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response

PROJECTS_BASE = Path(os.environ.get("PROJECTS_DIR", "/projects"))
MAX_SPEC_SIZE = 10 * 1024 * 1024  # 10 MB

TYPE_EMOJI  = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
TYPE_LABEL  = {"bug": "Bug", "feature": "Feature", "suggestion": "Suggestion", "error": "Erreur JS"}
STATUS_LABEL = {"open": "Ouvert", "blocked": "Bloqué", "closed": "Fermé"}

PRIORITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
PRIORITY_LABEL = {"critical": "Critique", "high": "Haute", "medium": "Moyenne", "low": "Basse"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PRIORITY_COLOR = {"critical": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#6b7280"}

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


def _parse_questions(body: str) -> list[dict]:
    section = re.search(r"### Questions avant implémentation\n\n([\s\S]*?)(?:\n###|\Z)", body)
    if not section:
        return []
    text = section.group(1)
    pairs = []
    for m in re.finditer(r"\*\*Q(\d+)\*\* : ([^\n]+)\n\*\*R\1\*\* : ([^\n]+)", text):
        answer = m.group(3).strip()
        pairs.append({
            "num": int(m.group(1)),
            "question": m.group(2).strip(),
            "answer": answer,
            "pending": answer == "*(en attente)*",
        })
    return pairs


def _apply_answers(body: str, answers: dict) -> str:
    for num, text in answers.items():
        if text.strip():
            body = re.sub(
                rf"\*\*R{num}\*\* : \*\(en attente\)\*",
                f"**R{num}** : {text.strip()}",
                body,
            )
    return body


def _parse_ticket(filepath: Path) -> dict:
    raw = filepath.read_text()
    fm, body = _parse_frontmatter(raw)
    fm["body"] = body
    fm["file"] = filepath.name
    fm.setdefault("id", filepath.stem.split("-")[0])
    desc_m = re.search(r"### Description\n\n([\s\S]*?)(?:\n###|\Z)", body)
    fm["description"] = desc_m.group(1).strip()[:150] if desc_m else ""
    fm["questions"] = _parse_questions(body)
    fm["pending_count"] = sum(1 for q in fm["questions"] if q["pending"])
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
    return sorted(tickets, key=lambda t: PRIORITY_ORDER.get(t.get("priority"), 4))


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

        def _count(files):
            open_c = blocked_c = closed_c = 0
            for f in files:
                txt = f.read_text()
                if "status: open" in txt:
                    open_c += 1
                elif "status: blocked" in txt:
                    blocked_c += 1
                else:
                    closed_c += 1
            return open_c, blocked_c, closed_c

        root_md = list(fd.glob("*.md"))
        if root_md:
            o, b, c = _count(root_md)
            projects.append({"name": p.name, "open": o, "blocked": b, "closed": c, "total": len(root_md)})

        for sub in sorted(fd.iterdir()):
            if not sub.is_dir():
                continue
            sub_md = list(sub.glob("*.md"))
            if not sub_md:
                continue
            o, b, c = _count(sub_md)
            projects.append({"name": f"{p.name}~{sub.name}", "open": o, "blocked": b, "closed": c, "total": len(sub_md)})

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

    open_t   = [t for t in tickets if t.get("status") == "open"]
    blocked_t = [t for t in tickets if t.get("status") == "blocked"]
    closed_t = [t for t in tickets if t.get("status") == "closed"]

    def fmt_date(iso):
        try:
            return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return "?"

    def rows(items):
        if not items:
            return "_Aucun_\n"
        header = "| ID | Date | Priorité | Description |\n|---|---|---|---|\n"
        r = []
        for t in items:
            desc = (t.get("description") or "").replace("|", "\\|")[:80]
            prio = t.get("priority", "")
            r.append(f"| `{t.get('id','')}` | {fmt_date(t.get('date',''))} | {prio} | {desc} |")
        return header + "\n".join(r) + "\n"

    def cnt(lst, typ):
        return sum(1 for t in lst if t.get("type") == typ)

    md = [
        f"# TICKETS — {project}",
        "",
        f"> Généré automatiquement le {datetime.now().strftime('%d/%m/%Y %H:%M')}. **Lire au début de chaque session.**",
        "",
        "## Résumé",
        "",
        "| Type | Ouverts | Bloqués | Fermés |",
        "|---|---|---|---|",
        f"| 🐛 Bugs | {cnt(open_t,'bug')} | {cnt(blocked_t,'bug')} | {cnt(closed_t,'bug')} |",
        f"| 🔴 Erreurs | {cnt(open_t,'error')} | {cnt(blocked_t,'error')} | {cnt(closed_t,'error')} |",
        f"| ✨ Features | {cnt(open_t,'feature')} | {cnt(blocked_t,'feature')} | {cnt(closed_t,'feature')} |",
        f"| 💡 Suggestions | {cnt(open_t,'suggestion')} | {cnt(blocked_t,'suggestion')} | {cnt(closed_t,'suggestion')} |",
        "",
    ]
    for label, items in [
        ("## 🔓 Ouverts", sorted(open_t, key=lambda t: PRIORITY_ORDER.get(t.get("priority"), 4))),
        ("## ⏸ Bloqués (en attente de réponses)", blocked_t),
        (f"## ✅ Fermés ({len(closed_t)})", closed_t),
    ]:
        if items:
            md += [label, "", rows(items)]
    if not tickets:
        md += ["_Aucun ticket pour l'instant._", ""]

    base = PROJECTS_BASE / project.split("~")[0] if "~" in project else PROJECTS_BASE / project
    (base / "TICKETS.md").write_text("\n".join(md))


def _create_ticket(
    project: str, type_: str, message: str, url: str,
    priority: str = "medium", milestone: str = "", needs_clarification: bool = False,
) -> str:
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

    fm_lines = [
        "---",
        f"id: {ticket_id}",
        f"type: {type_}",
        "status: open",
        f"priority: {priority}",
        f"date: {datetime.now().isoformat()}",
        f"project: {project.split('~')[0]}",
        f"url: {url}",
    ]
    if milestone:
        fm_lines.append(f"milestone: {milestone}")
    if needs_clarification:
        fm_lines.append("needs_clarification: true")
    fm_lines.append("---")

    body_lines = [
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

    (fd / filename).write_text("\n".join(fm_lines + body_lines))
    _regenerate_tickets_md(project)
    return str(ticket_id)


def _generate_session_brief(
    project: str,
    scope: str,
    roadmap_items: str,
    preactions: str,
    ticket_ids: list[str],
    context: str,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Session Brief — {project} — {today}", ""]

    if scope.strip():
        lines += ["## Scope", scope.strip(), ""]

    if roadmap_items.strip():
        lines += ["## Roadmap — définition (avant implémentation)"]
        for line in roadmap_items.strip().split("\n"):
            lines.append(f"- [ ] {line.lstrip('- ')}")
        lines.append("")

    if preactions.strip():
        lines += ["## Pré-actions (specs à générer)"]
        for line in preactions.strip().split("\n"):
            lines.append(f"- [ ] {line.lstrip('- ')}")
        lines.append("")

    if ticket_ids:
        fd = _feedback_dir(project)
        lines.append("## Tickets à traiter")
        for tid in ticket_ids:
            path = _ticket_path(project, tid)
            if path:
                t = _parse_ticket(path)
                prio = t.get("priority", "medium")
                type_ = t.get("type", "")
                desc = (t.get("description") or "")[:80]
                lines.append(f"- [ ] #{tid} — {type_} — {desc} (priority: {prio})")
            else:
                lines.append(f"- [ ] #{tid}")
        lines.append("")

    if context.strip():
        lines += ["## Contexte additionnel", context.strip(), ""]

    lines += ["## Résumé de session", "*(Claude Code remplit cette section à la fin)*", ""]
    return "\n".join(lines)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _base(title: str, body: str, breadcrumbs: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Hub</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh;font-size:14px}}
  a{{color:inherit;text-decoration:none}}
  header{{padding:1rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
  .logo{{color:#888;font-size:.9rem}}
  .logo a:hover{{color:#e8e8ea}}
  .sep{{color:#444}}
  .breadcrumb{{font-size:.9rem;color:#888}}
  .breadcrumb .current{{color:#e8e8ea;font-weight:600}}
  .container{{max-width:960px;margin:0 auto;padding:2rem 1.5rem}}
  .btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
        border:none;cursor:pointer;font-size:.85rem;font-weight:500;transition:opacity .15s;white-space:nowrap}}
  .btn:hover{{opacity:.85}}
  .btn-primary{{background:#4f6ef7;color:#fff}}
  .btn-secondary{{background:#1e2130;color:#e8e8ea;border:1px solid #2a2d3a}}
  .btn-danger{{background:#dc2626;color:#fff}}
  .btn-success{{background:#2da862;color:#fff}}
  .btn-sm{{padding:.3rem .65rem;font-size:.78rem}}
  .tag{{display:inline-block;padding:.2rem .55rem;border-radius:20px;font-size:.75rem;font-weight:600;white-space:nowrap}}
  .tag-open{{background:rgba(245,158,11,.15);color:#f59e0b}}
  .tag-blocked{{background:rgba(239,68,68,.15);color:#ef4444}}
  .tag-closed{{background:rgba(45,168,98,.15);color:#2da862}}
  .tag-bug{{background:rgba(220,38,38,.12);color:#f87171}}
  .tag-feature{{background:rgba(139,92,246,.12);color:#a78bfa}}
  .tag-suggestion{{background:rgba(59,130,246,.12);color:#60a5fa}}
  .tag-error{{background:rgba(220,38,38,.12);color:#f87171}}
  .tag-critical{{background:rgba(220,38,38,.12);color:#dc2626}}
  .tag-high{{background:rgba(234,88,12,.12);color:#ea580c}}
  .tag-medium{{background:rgba(202,138,4,.12);color:#ca8a04}}
  .tag-low{{background:rgba(107,114,128,.12);color:#9ca3af}}
  .filter-row{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}}
  .filter-btn{{padding:.3rem .75rem;border-radius:20px;font-size:.78rem;border:1px solid #2a2d3a;
               background:#1a1d27;color:#888;cursor:pointer;transition:all .15s;text-decoration:none;display:inline-block}}
  .filter-btn.active{{background:#4f6ef7;color:#fff;border-color:#4f6ef7}}
  .filter-btn:hover:not(.active){{border-color:#4f6ef7;color:#e8e8ea}}
  .page-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;gap:.75rem}}
  .page-title{{font-size:1.2rem;font-weight:700}}
  .card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:.9rem 1.1rem;
          margin-bottom:.6rem;transition:border-color .15s;position:relative}}
  .card:hover{{border-color:#4f6ef7}}
  .card-row{{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}}
  .card-meta{{font-size:.72rem;color:#555;white-space:nowrap;margin-left:auto}}
  .card-desc{{color:#bbb;font-size:.82rem;margin-top:.35rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .card-milestone{{font-size:.72rem;color:#666;margin-top:.2rem}}
  .card-check{{position:absolute;right:1rem;top:50%;transform:translateY(-50%);width:16px;height:16px;cursor:pointer;accent-color:#4f6ef7}}
  label{{display:block;font-size:.75rem;color:#888;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.04em}}
  input[type=text],input[type=url],select,textarea{{width:100%;background:#0f1117;border:1px solid #2a2d3a;
    border-radius:8px;padding:.65rem .9rem;color:#e8e8ea;font-size:.9rem;outline:none;font-family:inherit}}
  input:focus,select:focus,textarea:focus{{border-color:#4f6ef7}}
  select option{{background:#1a1d27}}
  textarea{{resize:vertical;font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.6}}
  .form-group{{margin-bottom:1.1rem}}
  .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
  .form-row-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem}}
  .section{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1.2rem;margin-bottom:1.1rem}}
  .section-title{{font-size:.78rem;font-weight:600;color:#888;margin-bottom:.9rem;
                  text-transform:uppercase;letter-spacing:.06em}}
  .spec-list{{display:flex;flex-direction:column;gap:.4rem;margin-bottom:.9rem}}
  .spec-item{{display:flex;align-items:center;gap:.6rem;padding:.45rem .75rem;
              background:#0f1117;border-radius:8px;border:1px solid #2a2d3a}}
  .spec-name{{flex:1;font-size:.82rem;color:#bbb}}
  .empty{{color:#555;font-size:.82rem;font-style:italic;padding:.4rem 0}}
  .project-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}}
  .project-card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:14px;padding:1.1rem 1.4rem;
                 transition:border-color .2s,transform .15s}}
  .project-card:hover{{border-color:#4f6ef7;transform:translateY(-2px)}}
  .project-name{{font-size:1rem;font-weight:600;margin-bottom:.5rem}}
  .project-counts{{display:flex;gap:.6rem;flex-wrap:wrap}}
  .count-open{{font-size:.8rem;color:#f59e0b;font-weight:600}}
  .count-blocked{{font-size:.8rem;color:#ef4444;font-weight:600}}
  .count-closed{{font-size:.8rem;color:#555}}
  .alert{{padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.85rem}}
  .alert-success{{background:rgba(45,168,98,.12);border:1px solid rgba(45,168,98,.3);color:#2da862}}
  .alert-error{{background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);color:#f87171}}
  .alert-info{{background:rgba(79,110,247,.12);border:1px solid rgba(79,110,247,.3);color:#818cf8}}
  .divider{{border:none;border-top:1px solid #1e2130;margin:1.25rem 0}}
  .qa-box{{background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:1rem;margin-bottom:.75rem}}
  .qa-question{{font-size:.85rem;color:#e8e8ea;margin-bottom:.5rem;font-weight:500}}
  .qa-answer{{font-size:.82rem;color:#2da862;margin-top:.3rem}}
  .brief-bar{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:10px;padding:.75rem 1rem;
              margin-bottom:1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
  .brief-count{{font-size:.85rem;color:#888}}
  .brief-count strong{{color:#4f6ef7}}
  .checkbox-label{{display:flex;align-items:center;gap:.5rem;cursor:pointer;font-size:.82rem;color:#888}}
  .checkbox-label input{{width:auto;accent-color:#4f6ef7}}
  pre{{background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:1rem;
       font-size:.78rem;line-height:1.6;overflow-x:auto;white-space:pre-wrap;color:#bbb}}
  @media(max-width:600px){{.form-row,.form-row-3{{grid-template-columns:1fr}}.project-grid{{grid-template-columns:1fr}}}}
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
    return f'<span class="tag tag-{_e(type_)}">{TYPE_EMOJI.get(type_,"📝")} {_e(TYPE_LABEL.get(type_, type_))}</span>'


def _status_tag(status: str) -> str:
    return f'<span class="tag tag-{_e(status)}">{_e(STATUS_LABEL.get(status, status))}</span>'


def _priority_tag(priority: str) -> str:
    if not priority:
        return ""
    return f'<span class="tag tag-{_e(priority)}">{PRIORITY_EMOJI.get(priority,"")} {_e(PRIORITY_LABEL.get(priority, priority))}</span>'


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except Exception:
        return iso


# ── Page: projects list ────────────────────────────────────────────────────────

def _page_projects(projects: list) -> str:
    if not projects:
        cards = '<p class="empty">Aucun projet avec des tickets trouvé.</p>'
    else:
        cards = '<div class="project-grid">'
        for p in projects:
            display = _e(p["name"].replace("~", " / "))
            blocked_html = f' <span class="count-blocked">· {p["blocked"]} bloqué{"s" if p["blocked"]!=1 else ""}</span>' if p["blocked"] else ""
            roadmap_link = f'/roadmap/{_e(p["name"])}'
            cards += f"""
      <a href="/tickets/{_e(p['name'])}" class="project-card" style="display:block">
        <div class="project-name">{display}</div>
        <div class="project-counts">
          <span class="count-open">{p['open']} ouvert{"s" if p['open']!=1 else ""}</span>
          {blocked_html}
          <span class="count-closed">· {p['closed']} fermé{"s" if p['closed']!=1 else ""}</span>
        </div>
        <div style="margin-top:.5rem;font-size:.72rem;color:#444">→ Roadmap</div>
      </a>"""
        cards += "</div>"

    body = f"""
<div class="page-header">
  <div class="page-title">🎫 Gestion des tickets</div>
</div>
{cards}"""
    return _base("Tickets", body)


# ── Page: ticket list ──────────────────────────────────────────────────────────

def _page_ticket_list(project: str, tickets: list, status_f: str, type_f: str, priority_f: str, milestone_f: str) -> str:
    def furl(s=None, t=None, p=None, m=None):
        s = s if s is not None else status_f
        t = t if t is not None else type_f
        p = p if p is not None else priority_f
        m = m if m is not None else milestone_f
        params = [x for x in [
            f"status={s}" if s != "all" else "",
            f"type={t}" if t != "all" else "",
            f"priority={p}" if p != "all" else "",
            f"milestone={m}" if m else "",
        ] if x]
        base = f"/tickets/{project}"
        return base + ("?" + "&".join(params) if params else "")

    def fbtn(label, active, **kw):
        cls = "filter-btn active" if active else "filter-btn"
        return f'<a href="{furl(**kw)}" class="{cls}">{label}</a>'

    filtered = tickets
    if status_f != "all":
        filtered = [t for t in filtered if t.get("status") == status_f]
    if type_f != "all":
        filtered = [t for t in filtered if t.get("type") == type_f]
    if priority_f != "all":
        filtered = [t for t in filtered if t.get("priority") == priority_f]
    if milestone_f:
        filtered = [t for t in filtered if t.get("milestone") == milestone_f]

    n_open    = sum(1 for t in tickets if t.get("status") == "open")
    n_blocked = sum(1 for t in tickets if t.get("status") == "blocked")
    n_closed  = sum(1 for t in tickets if t.get("status") == "closed")

    status_btns = (
        fbtn(f"Tout ({len(tickets)})", status_f == "all", s="all", t=type_f, p=priority_f, m=milestone_f) +
        fbtn(f"Ouverts ({n_open})", status_f == "open", s="open", t=type_f, p=priority_f, m=milestone_f) +
        fbtn(f"⏸ Bloqués ({n_blocked})", status_f == "blocked", s="blocked", t=type_f, p=priority_f, m=milestone_f) +
        fbtn(f"Fermés ({n_closed})", status_f == "closed", s="closed", t=type_f, p=priority_f, m=milestone_f)
    )

    type_counts = {}
    for t in tickets:
        type_counts[t.get("type", "")] = type_counts.get(t.get("type", ""), 0) + 1
    type_btns = fbtn(f"Tous ({len(tickets)})", type_f == "all", t="all", s=status_f, p=priority_f, m=milestone_f)
    for tp in ["bug", "feature", "suggestion", "error"]:
        if tp in type_counts:
            type_btns += fbtn(f"{TYPE_EMOJI[tp]} {TYPE_LABEL[tp]} ({type_counts[tp]})", type_f == tp, t=tp, s=status_f, p=priority_f, m=milestone_f)

    prio_counts = {}
    for t in tickets:
        prio_counts[t.get("priority", "")] = prio_counts.get(t.get("priority", ""), 0) + 1
    prio_btns = fbtn("Toutes priorités", priority_f == "all", p="all", s=status_f, t=type_f, m=milestone_f)
    for pr in ["critical", "high", "medium", "low"]:
        if pr in prio_counts:
            prio_btns += fbtn(f"{PRIORITY_EMOJI[pr]} {PRIORITY_LABEL[pr]} ({prio_counts[pr]})", priority_f == pr, p=pr, s=status_f, t=type_f, m=milestone_f)

    milestones = sorted({t.get("milestone", "") for t in tickets if t.get("milestone")})
    ms_btns = ""
    if milestones:
        ms_btns = fbtn("Tous milestones", milestone_f == "", p=priority_f, s=status_f, t=type_f, m="")
        for ms in milestones:
            ms_btns += fbtn(ms, milestone_f == ms, p=priority_f, s=status_f, t=type_f, m=ms)

    blocked_with_pending = [t for t in filtered if t.get("status") == "blocked" and t.get("pending_count", 0) > 0]
    blocked_alert = ""
    if blocked_with_pending:
        blocked_alert = f'<div class="alert alert-info">⏸ {len(blocked_with_pending)} ticket{"s" if len(blocked_with_pending)>1 else ""} en attente de tes réponses — <a href="{furl(s="blocked")}" style="color:#818cf8;text-decoration:underline">voir les questions</a></div>'

    cards = ""
    if not filtered:
        cards = '<p class="empty">Aucun ticket pour ce filtre.</p>'
    else:
        for t in filtered:
            tid   = t.get("id", "")
            type_ = t.get("type", "")
            status = t.get("status", "open")
            prio  = t.get("priority", "")
            desc  = _e(t.get("description", "")[:100])
            date  = _fmt_date(t.get("date", ""))
            ms    = t.get("milestone", "")
            pending = t.get("pending_count", 0)
            pending_html = f' <span class="tag tag-blocked">⏸ {pending} question{"s" if pending>1 else ""}</span>' if pending else ""
            ms_html = f'<div class="card-milestone">🏁 {_e(ms)}</div>' if ms else ""
            cards += f"""
<div class="card" style="padding-right:2.5rem">
  <input type="checkbox" class="card-check brief-cb" name="t" value="{_e(tid)}">
  <a href="/tickets/{_e(project)}/{_e(tid)}/edit" class="card-link" style="display:block">
    <div class="card-row">
      {_type_tag(type_)}{_status_tag(status)}{pending_html}{_priority_tag(prio)}
      <span class="card-meta">{_e(date)}</span>
    </div>
    {"" if not desc else f'<div class="card-desc">{desc}</div>'}
    {ms_html}
  </a>
</div>"""

    display = project.replace("~", " / ")
    breadcrumbs = f'<span class="sep">/</span> <span class="breadcrumb current">{_e(display)}</span>'

    body = f"""
{blocked_alert}
<form method="GET" action="/tickets/{_e(project)}/brief" id="brief-form">
<div class="page-header">
  <div class="page-title">{_e(display)}</div>
  <div style="display:flex;gap:.5rem;flex-wrap:wrap">
    <a href="/roadmap/{_e(project)}" class="btn btn-secondary">🗺 Roadmap</a>
    <a href="/tickets/{_e(project)}/new" class="btn btn-primary">+ Nouveau ticket</a>
  </div>
</div>
<div class="brief-bar">
  <span class="brief-count">📋 <strong id="brief-n">0</strong> ticket(s) sélectionné(s)</span>
  <button type="submit" class="btn btn-secondary btn-sm" id="brief-btn" disabled>Construire le brief →</button>
  <label class="checkbox-label" style="margin-left:auto">
    <input type="checkbox" id="select-all"> Tout sélectionner
  </label>
</div>
<div class="filter-row">{status_btns}</div>
<div class="filter-row">{type_btns}</div>
<div class="filter-row">{prio_btns}</div>
{"" if not ms_btns else f'<div class="filter-row">{ms_btns}</div>'}
{cards}
</form>
<script>
const cbs = () => document.querySelectorAll('.brief-cb');
const btn = document.getElementById('brief-btn');
const counter = document.getElementById('brief-n');
const all = document.getElementById('select-all');
function update() {{
  const n = [...cbs()].filter(c=>c.checked).length;
  counter.textContent = n;
  btn.disabled = n === 0;
}}
document.addEventListener('change', e => {{
  if (e.target.classList.contains('brief-cb')) update();
  if (e.target.id === 'select-all') {{
    cbs().forEach(c => c.checked = e.target.checked);
    update();
  }}
}});
</script>"""
    return _base(display, body, breadcrumbs)


# ── Page: new ticket ───────────────────────────────────────────────────────────

def _page_new(project: str, error: str = "") -> str:
    display = project.replace("~", " / ")
    err_html = f'<div class="alert alert-error">{_e(error)}</div>' if error else ""
    type_opts = "".join(f'<option value="{k}">{v} {TYPE_LABEL[k]}</option>' for k, v in TYPE_EMOJI.items())
    prio_opts = "".join(
        f'<option value="{k}" {"selected" if k=="medium" else ""}>{PRIORITY_EMOJI[k]} {PRIORITY_LABEL[k]}</option>'
        for k in PRIORITY_ORDER
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
    <div class="form-row-3">
      <div class="form-group">
        <label>Type</label>
        <select name="type">{type_opts}</select>
      </div>
      <div class="form-group">
        <label>Priorité</label>
        <select name="priority">{prio_opts}</select>
      </div>
      <div class="form-group">
        <label>Milestone (optionnel)</label>
        <input type="text" name="milestone" placeholder="ex: V2-budget">
      </div>
    </div>
    <div class="form-group">
      <label>URL (optionnel)</label>
      <input type="url" name="url" placeholder="https://...">
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea name="message" rows="7" placeholder="Décrivez le bug, la feature ou la suggestion..."></textarea>
    </div>
    <div class="form-group" style="display:flex;align-items:center;gap:.75rem">
      <input type="checkbox" name="needs_clarification" value="1" id="nc" style="width:auto;accent-color:#4f6ef7">
      <label for="nc" style="text-transform:none;letter-spacing:0;color:#bbb;font-size:.85rem;margin-bottom:0">
        Clarification nécessaire avant implémentation (Claude posera des questions)
      </label>
    </div>
    <button type="submit" class="btn btn-primary">Créer le ticket</button>
  </div>
</form>"""
    return _base("Nouveau ticket", body, breadcrumbs)


# ── Page: edit ticket ──────────────────────────────────────────────────────────

def _page_edit(project: str, ticket: dict, specs: list, flash: str = "") -> str:
    tid     = ticket.get("id", "")
    type_   = ticket.get("type", "bug")
    status  = ticket.get("status", "open")
    prio    = ticket.get("priority", "medium")
    ms      = ticket.get("milestone", "")
    nc      = ticket.get("needs_clarification", "") == "true"
    body_md = ticket.get("body", "")
    questions = ticket.get("questions", [])
    pending   = [q for q in questions if q["pending"]]

    flash_map = {
        "saved": ("✓ Ticket sauvegardé.", "alert-success"),
        "spec_uploaded": ("✓ Fichier attaché.", "alert-success"),
        "spec_deleted": ("✓ Fichier supprimé.", "alert-success"),
        "answers_saved": ("✓ Réponses enregistrées.", "alert-success"),
    }
    flash_html = ""
    if flash in flash_map:
        msg, cls = flash_map[flash]
        flash_html = f'<div class="alert {cls}">{msg}</div>'

    type_opts = "".join(f'<option value="{k}" {"selected" if k==type_ else ""}>{TYPE_EMOJI[k]} {TYPE_LABEL[k]}</option>' for k in TYPE_EMOJI)
    prio_opts = "".join(f'<option value="{k}" {"selected" if k==prio else ""}>{PRIORITY_EMOJI[k]} {PRIORITY_LABEL[k]}</option>' for k in PRIORITY_ORDER)
    status_opts = "".join(f'<option value="{s}" {"selected" if s==status else ""}>{STATUS_LABEL[s]}</option>' for s in ["open", "blocked", "closed"])

    qa_html = ""
    if questions:
        qa_items = ""
        answered = []
        for q in questions:
            if q["pending"]:
                qa_items += f"""
<div class="qa-box">
  <div class="qa-question">❓ Q{q['num']} : {_e(q['question'])}</div>
  <div class="form-group" style="margin:0.5rem 0 0">
    <input type="text" name="r{q['num']}" placeholder="Ta réponse...">
  </div>
</div>"""
            else:
                answered.append(f"<div class='qa-box'><div class='qa-question'>Q{q['num']} : {_e(q['question'])}</div><div class='qa-answer'>✓ {_e(q['answer'])}</div></div>")

        all_pending = all(q["pending"] for q in questions)
        section_title = "⏸ Questions en attente de réponse" if pending else "✅ Questions répondues"
        save_btn = '<button type="submit" class="btn btn-success">Enregistrer les réponses</button>' if pending else ""
        qa_html = f"""
<div class="section">
  <div class="section-title">{section_title}</div>
  {"".join(answered)}
  <form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/answers">
    {qa_items}
    {save_btn}
  </form>
</div>"""

    specs_html = ""
    if specs:
        items = "".join(f"""
<div class="spec-item">
  <span class="spec-name">📎 {_e(s[len(f"{tid}-spec-"):])}</span>
  <a href="/tickets/{_e(project)}/{_e(tid)}/spec/{_e(s)}" class="btn btn-secondary btn-sm">↓</a>
  <form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/spec/{_e(s)}/delete" style="margin:0">
    <button type="submit" class="btn btn-danger btn-sm">✕</button>
  </form>
</div>""" for s in specs)
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
  <div style="display:flex;align-items:center;gap:.6rem;flex-wrap:wrap">
    <div class="page-title">#{_e(str(tid))}</div>
    {_type_tag(type_)}{_status_tag(status)}{_priority_tag(prio)}
  </div>
  <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>

{qa_html}

<form method="POST" action="/tickets/{_e(project)}/{_e(tid)}/edit">
  <div class="section">
    <div class="section-title">Métadonnées</div>
    <div class="form-row-3">
      <div class="form-group">
        <label>Type</label>
        <select name="type">{type_opts}</select>
      </div>
      <div class="form-group">
        <label>Priorité</label>
        <select name="priority">{prio_opts}</select>
      </div>
      <div class="form-group">
        <label>Statut</label>
        <select name="status">{status_opts}</select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Milestone</label>
        <input type="text" name="milestone" value="{_e(ms)}" placeholder="ex: V2-budget">
      </div>
      <div class="form-group" style="display:flex;align-items:flex-end;padding-bottom:.65rem">
        <label class="checkbox-label" style="text-transform:none;letter-spacing:0;color:#bbb;font-size:.85rem;margin-bottom:0;display:flex;align-items:center;gap:.5rem">
          <input type="checkbox" name="needs_clarification" value="1" {"checked" if nc else ""} style="width:auto;accent-color:#4f6ef7">
          Clarification nécessaire
        </label>
      </div>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Contenu (Markdown)</div>
    <div class="form-group">
      <textarea name="body" rows="16">{_e(body_md)}</textarea>
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
      <div class="form-group" style="margin:0">
        <label>Joindre un fichier (max 10 Mo)</label>
        <input type="file" name="file">
      </div>
      <div><button type="submit" class="btn btn-secondary">📎 Uploader</button></div>
    </div>
  </form>
</div>"""
    return _base(f"#{tid}", body, breadcrumbs)


# ── Page: brief builder ────────────────────────────────────────────────────────

def _page_brief(project: str, selected_ids: list[str], current_brief: str) -> str:
    display = project.replace("~", " / ")

    selected_tickets = []
    for tid in selected_ids:
        path = _ticket_path(project, tid)
        if path:
            selected_tickets.append(_parse_ticket(path))
    selected_tickets.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority"), 4))

    tickets_html = ""
    hidden_inputs = ""
    if selected_tickets:
        for t in selected_tickets:
            tid  = t.get("id", "")
            desc = _e(t.get("description", "")[:80])
            prio = t.get("priority", "")
            status = t.get("status", "open")
            tickets_html += f"""
<div class="card" style="margin-bottom:.4rem">
  <div class="card-row">
    {_type_tag(t.get("type",""))}{_status_tag(status)}{_priority_tag(prio)}
    <span class="card-meta">#{_e(str(tid))}</span>
  </div>
  {"" if not desc else f'<div class="card-desc">{desc}</div>'}
</div>"""
            hidden_inputs += f'<input type="hidden" name="t" value="{_e(str(tid))}">'
    else:
        tickets_html = '<p class="empty">Aucun ticket sélectionné. <a href="/tickets/{}" style="color:#4f6ef7">← Retour à la liste</a></p>'.format(_e(project))

    current_brief_html = ""
    if current_brief:
        current_brief_html = f"""
<div class="section">
  <div class="section-title">SESSION_BRIEF.md actuel</div>
  <pre>{_e(current_brief)}</pre>
</div>"""

    breadcrumbs = (
        f'<span class="sep">/</span> <a href="/tickets/{_e(project)}" class="breadcrumb">{_e(display)}</a>'
        f' <span class="sep">/</span> <span class="breadcrumb current">Brief</span>'
    )
    body = f"""
<div class="page-header">
  <div class="page-title">📋 Session Brief — {_e(display)}</div>
  <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>

{current_brief_html}

<form method="POST" action="/tickets/{_e(project)}/brief/generate">
  {hidden_inputs}

  <div class="section">
    <div class="section-title">Tickets sélectionnés ({len(selected_tickets)})</div>
    {tickets_html}
  </div>

  <div class="section">
    <div class="section-title">Scope / Contraintes</div>
    <div class="form-group">
      <label>Milestone actif, modules hors-scope...</label>
      <textarea name="scope" rows="3" placeholder="ex: Milestone actif : V2-budget&#10;Ne pas toucher : module import"></textarea>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Roadmap — définition (optionnel)</div>
    <div class="form-group">
      <label>Instructions pour Claude (une par ligne)</label>
      <textarea name="roadmap_items" rows="4" placeholder="ex: Analyser les tickets ouverts et générer une vision V2 dans roadmap/V2-budget.md"></textarea>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Pré-actions — specs à générer (optionnel)</div>
    <div class="form-group">
      <label>Une par ligne — Claude génèrera le fichier spec correspondant</label>
      <textarea name="preactions" rows="3" placeholder="ex: Générer spec pour : refonte UX page budget → attacher au ticket #1780688"></textarea>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Contexte additionnel (optionnel)</div>
    <div class="form-group">
      <textarea name="context" rows="3" placeholder="ex: Préférer CSS-only pour les animations. Pas de nouvelle dépendance npm."></textarea>
    </div>
  </div>

  <button type="submit" class="btn btn-primary">⚡ Générer SESSION_BRIEF.md</button>
</form>"""
    return _base("Brief", body, breadcrumbs)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _require_auth(request: Request, settings):
    from app.auth import get_session, redirect_to_login
    if not get_session(request, settings.SESSION_SECRET):
        return redirect_to_login(str(request.url.path))
    return None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def tickets_index(request: Request):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_projects(_list_projects()))


@router.get("/{project}", response_class=HTMLResponse)
async def ticket_list(
    request: Request, project: str,
    status: str = "all", type: str = "all",
    priority: str = "all", milestone: str = "",
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if _feedback_dir(project) is None:
        return HTMLResponse(f"Projet introuvable : {_e(project)}", status_code=404)
    tickets = _list_tickets(project)
    return HTMLResponse(_page_ticket_list(project, tickets, status, type, priority, milestone))


@router.get("/{project}/new", response_class=HTMLResponse)
async def ticket_new_get(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if _feedback_dir(project) is None:
        return HTMLResponse(f"Projet introuvable : {_e(project)}", status_code=404)
    return HTMLResponse(_page_new(project))


@router.post("/{project}/new")
async def ticket_new_post(
    request: Request, project: str,
    type: str = Form(...), message: str = Form(default=""),
    url: str = Form(default=""), priority: str = Form(default="medium"),
    milestone: str = Form(default=""), needs_clarification: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if type not in TYPE_EMOJI:
        return HTMLResponse(_page_new(project, "Type invalide."), status_code=400)
    if not message.strip() and type != "error":
        return HTMLResponse(_page_new(project, "La description est obligatoire."), status_code=400)
    tid = _create_ticket(
        project, type, message.strip(), url.strip(),
        priority=priority if priority in PRIORITY_ORDER else "medium",
        milestone=milestone.strip(),
        needs_clarification=bool(needs_clarification),
    )
    return RedirectResponse(f"/tickets/{project}/{tid}/edit?flash=saved", status_code=303)


@router.get("/{project}/brief", response_class=HTMLResponse)
async def ticket_brief_get(request: Request, project: str, t: list[str] = Query(default=[])):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if _feedback_dir(project) is None:
        return HTMLResponse(f"Projet introuvable : {_e(project)}", status_code=404)
    proj_dir = PROJECTS_BASE / project.split("~")[0]
    brief_path = proj_dir / "SESSION_BRIEF.md"
    current = brief_path.read_text() if brief_path.exists() else ""
    return HTMLResponse(_page_brief(project, t, current))


@router.post("/{project}/brief/generate")
async def ticket_brief_generate(
    request: Request, project: str,
    t: list[str] = Form(default=[]),
    scope: str = Form(default=""),
    roadmap_items: str = Form(default=""),
    preactions: str = Form(default=""),
    context: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    proj_dir = PROJECTS_BASE / project.split("~")[0]
    content = _generate_session_brief(project, scope, roadmap_items, preactions, t, context)
    (proj_dir / "SESSION_BRIEF.md").write_text(content)
    return RedirectResponse(f"/tickets/{project}/brief", status_code=303)


@router.get("/{project}/{ticket_id}/edit", response_class=HTMLResponse)
async def ticket_edit_get(request: Request, project: str, ticket_id: str, flash: str = ""):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _ticket_path(project, ticket_id)
    if not path:
        return HTMLResponse(f"Ticket introuvable : {_e(ticket_id)}", status_code=404)
    ticket = _parse_ticket(path)
    specs  = _list_specs(project, ticket_id)
    return HTMLResponse(_page_edit(project, ticket, specs, flash))


@router.post("/{project}/{ticket_id}/edit")
async def ticket_edit_post(
    request: Request, project: str, ticket_id: str,
    type: str = Form(...), status: str = Form(...),
    priority: str = Form(default="medium"), milestone: str = Form(default=""),
    needs_clarification: str = Form(default=""), body: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _ticket_path(project, ticket_id)
    if not path:
        return HTMLResponse(f"Ticket introuvable : {_e(ticket_id)}", status_code=404)

    raw = path.read_text()
    fm, _ = _parse_frontmatter(raw)

    fm["type"]     = type if type in TYPE_EMOJI else fm.get("type", "bug")
    fm["priority"] = priority if priority in PRIORITY_ORDER else fm.get("priority", "medium")
    fm["milestone"] = milestone.strip() or ""
    if not fm["milestone"] and "milestone" in fm:
        del fm["milestone"]

    if needs_clarification:
        fm["needs_clarification"] = "true"
    elif "needs_clarification" in fm:
        del fm["needs_clarification"]

    prev = fm.get("status", "open")
    fm["status"] = status if status in ("open", "blocked", "closed") else prev
    if status == "closed" and prev != "closed":
        fm["closed_at"] = datetime.now(timezone.utc).isoformat()
    elif status != "closed" and "closed_at" in fm:
        del fm["closed_at"]

    path.write_text(_build_file(fm, body.strip()))
    _regenerate_tickets_md(project)
    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=saved", status_code=303)


@router.post("/{project}/{ticket_id}/answers")
async def ticket_answers_post(request: Request, project: str, ticket_id: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _ticket_path(project, ticket_id)
    if not path:
        return HTMLResponse(f"Ticket introuvable : {_e(ticket_id)}", status_code=404)

    form = await request.form()
    answers = {k[1:]: v for k, v in form.items() if k.startswith("r") and k[1:].isdigit() and v.strip()}

    raw = path.read_text()
    fm, body = _parse_frontmatter(raw)
    body = _apply_answers(body, answers)

    questions = _parse_questions(body)
    all_answered = questions and all(not q["pending"] for q in questions)
    if all_answered and fm.get("status") == "blocked":
        fm["status"] = "open"

    path.write_text(_build_file(fm, body))
    _regenerate_tickets_md(project)
    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=answers_saved", status_code=303)


@router.post("/{project}/{ticket_id}/spec")
async def ticket_spec_upload(request: Request, project: str, ticket_id: str, file: UploadFile = File(...)):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    fd = _feedback_dir(project)
    if not fd or not _ticket_path(project, ticket_id):
        return HTMLResponse("Introuvable", status_code=404)
    data = await file.read()
    if len(data) > MAX_SPEC_SIZE:
        return HTMLResponse("Fichier trop volumineux (max 10 Mo)", status_code=413)
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "upload")
    (fd / f"{ticket_id}-spec-{safe}").write_bytes(data)
    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=spec_uploaded", status_code=303)


@router.get("/{project}/{ticket_id}/spec/{filename}")
async def ticket_spec_download(request: Request, project: str, ticket_id: str, filename: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    fd = _feedback_dir(project)
    if not fd or not filename.startswith(f"{ticket_id}-spec-"):
        return HTMLResponse("Accès refusé", status_code=403)
    p = fd / filename
    if not p.exists():
        return HTMLResponse("Introuvable", status_code=404)
    mime, _ = mimetypes.guess_type(filename)
    display = filename[len(f"{ticket_id}-spec-"):]
    return Response(content=p.read_bytes(), media_type=mime or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{display}"'})


@router.post("/{project}/{ticket_id}/spec/{filename}/delete")
async def ticket_spec_delete(request: Request, project: str, ticket_id: str, filename: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    fd = _feedback_dir(project)
    if fd and filename.startswith(f"{ticket_id}-spec-"):
        p = fd / filename
        if p.exists():
            p.unlink()
    return RedirectResponse(f"/tickets/{project}/{ticket_id}/edit?flash=spec_deleted", status_code=303)
