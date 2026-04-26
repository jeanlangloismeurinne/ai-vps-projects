from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime, timezone
import re, time, os

from app.services import slack_notifier

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

TICKETS_DIR = Path(__file__).parent.parent.parent / "feedback-tickets"
TICKETS_MD = Path(__file__).parent.parent.parent / "TICKETS.md"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
TYPE_LABEL = {"bug": "Bug", "feature": "Feature", "suggestion": "Suggestion", "error": "Erreur JS"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", text[:40].lower()))


def _save_ticket(data: dict) -> tuple[str, int]:
    TICKETS_DIR.mkdir(exist_ok=True)
    ticket_id = int(time.time() * 1000)
    slug = _slug(data.get("message") or data.get("description") or "no-message")
    filename = f"{ticket_id}-{data['type']}-{slug}.md"

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    emoji = TYPE_EMOJI.get(data["type"], "📝")
    label = TYPE_LABEL.get(data["type"], data["type"])
    text = data.get("message") or data.get("description") or "_Aucune description_"

    lines = [
        "---",
        f"id: {ticket_id}",
        f"type: {data['type']}",
        "status: open",
        f"date: {datetime.now().isoformat()}",
        "project: bank-review",
        f"url: {data.get('url', '')}",
        "---",
        "",
        f"## {emoji} {label}",
        "",
        f"**Date** : {date_str}",
        f"**URL** : `{data.get('url', 'N/A')}`",
        "",
        "### Description",
        "",
        text,
        "",
    ]
    if data.get("stack"):
        lines += ["### Stack trace", "", "```", data["stack"], "```", ""]
    if data.get("userAgent"):
        lines += ["### Contexte", "", f"- **User-Agent** : {data['userAgent']}", ""]

    (TICKETS_DIR / filename).write_text("\n".join(lines))
    _regenerate_tickets_md()
    return filename, ticket_id


def _regenerate_tickets_md():
    if not TICKETS_DIR.exists():
        return
    files = sorted(TICKETS_DIR.glob("*.md"), reverse=True)
    tickets = []
    for f in files:
        raw = f.read_text()
        fm = {}
        m = re.search(r"^---\n([\s\S]*?)\n---", raw)
        if m:
            for line in m.group(1).split("\n"):
                if ": " in line:
                    k, _, v = line.partition(": ")
                    fm[k.strip()] = v.strip()
        desc_m = re.search(r"### Description\n\n([\s\S]*?)(?:\n###|\Z)", raw)
        fm["description"] = (desc_m.group(1).strip()[:120] if desc_m else "")
        tickets.append(fm)

    open_t = [t for t in tickets if t.get("status") == "open"]
    closed_t = [t for t in tickets if t.get("status") != "open"]

    def rows(items):
        if not items:
            return "_Aucun_\n"
        header = "| ID | Date | URL | Description |\n|---|---|---|---|\n"
        r = []
        for t in items:
            try:
                d = datetime.fromisoformat(t.get("date", "")).strftime("%d/%m/%Y %H:%M")
            except Exception:
                d = "?"
            desc = t.get("description", "").replace("|", "\\|")[:80]
            r.append(f"| `{t.get('id','')}` | {d} | `{t.get('url','')[:50]}` | {desc} |")
        return header + "\n".join(r) + "\n"

    def count(type_): return sum(1 for t in open_t if t.get("type") == type_)
    def count_c(type_): return sum(1 for t in closed_t if t.get("type") == type_)

    bugs = [t for t in open_t if t.get("type") in ("bug", "error")]
    features = [t for t in open_t if t.get("type") == "feature"]
    suggestions = [t for t in open_t if t.get("type") == "suggestion"]

    md = [
        "# TICKETS — Feedback bank-review",
        "",
        f"> Généré automatiquement le {datetime.now().strftime('%d/%m/%Y %H:%M')}. **Lire au début de chaque session.**",
        "",
        "## Résumé",
        "",
        "| Type | Ouverts | Fermés |",
        "|---|---|---|",
        f"| 🐛 Bugs | {count('bug')} | {count_c('bug')} |",
        f"| 🔴 Erreurs JS | {count('error')} | {count_c('error')} |",
        f"| ✨ Features | {count('feature')} | {count_c('feature')} |",
        f"| 💡 Suggestions | {count('suggestion')} | {count_c('suggestion')} |",
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

    TICKETS_MD.write_text("\n".join(md))


def _parse_ticket(path: Path) -> dict:
    raw = path.read_text()
    fm: dict = {}
    m = re.search(r"^---\n([\s\S]*?)\n---", raw)
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
    desc_m = re.search(r"### Description\n\n([\s\S]*?)(?:\n###|\Z)", raw)
    fm["description"] = desc_m.group(1).strip()[:120] if desc_m else ""
    fm["_path"] = path
    return fm


def _find_ticket(ticket_id: str) -> Path | None:
    if not TICKETS_DIR.exists():
        return None
    for f in TICKETS_DIR.glob(f"{ticket_id}-*.md"):
        return f
    return None


@router.post("")
async def post_feedback(request: Request):
    data = await request.json()
    valid_types = {"bug", "feature", "suggestion", "error"}
    if data.get("type") not in valid_types:
        return JSONResponse({"error": "Invalid type"}, status_code=400)
    if not data.get("message") and data.get("type") != "error":
        return JSONResponse({"error": "Message required"}, status_code=400)

    filename, _ = _save_ticket(data)
    await slack_notifier.notify_new_feedback(
        data["type"],
        data.get("message") or data.get("description") or "",
        data.get("url", ""),
    )
    return {"ok": True, "file": filename}


@router.post("/{ticket_id}/close")
async def close_ticket(ticket_id: str, x_internal_api_key: str = Header(default="")):
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    path = _find_ticket(ticket_id)
    if not path:
        return JSONResponse({"error": "Ticket not found"}, status_code=404)

    raw = path.read_text()
    ticket = _parse_ticket(path)
    if ticket.get("status") == "closed":
        return JSONResponse({"error": "Already closed"}, status_code=409)

    closed_at = datetime.now(timezone.utc).isoformat()
    updated = raw.replace("status: open", f"status: closed\nclosed_at: {closed_at}", 1)
    path.write_text(updated)
    _regenerate_tickets_md()
    return {"ok": True, "ticket_id": ticket_id}


@router.get("/closed-since")
async def closed_since(
    since: str,
    x_internal_api_key: str = Header(default=""),
):
    """Retourne les tickets fermés depuis `since` (ISO 8601). Protégé par X-Internal-Api-Key."""
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return JSONResponse({"error": "Invalid since format (use ISO 8601)"}, status_code=400)

    results = []
    if TICKETS_DIR.exists():
        for f in sorted(TICKETS_DIR.glob("*.md"), reverse=True):
            t = _parse_ticket(f)
            if t.get("status") != "closed":
                continue
            closed_at_str = t.get("closed_at", "")
            if not closed_at_str:
                continue
            try:
                closed_at_dt = datetime.fromisoformat(closed_at_str)
                if closed_at_dt.tzinfo is None:
                    closed_at_dt = closed_at_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if closed_at_dt >= since_dt:
                results.append({
                    "id": t.get("id", ""),
                    "type": t.get("type", ""),
                    "description": t.get("description", ""),
                    "closed_at": closed_at_str,
                    "url": t.get("url", ""),
                })

    return {"tickets": results}
