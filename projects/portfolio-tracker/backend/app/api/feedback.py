import re
import time
import os
import logging
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime, timezone

from app.notifications.slack_notifier import SlackNotifier

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)

TICKETS_DIR = Path("/app/feedback-tickets")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
TYPE_LABEL = {"bug": "Bug", "feature": "Feature", "suggestion": "Suggestion", "error": "Erreur JS"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", text[:40].lower()))


def _save_ticket(data: dict) -> str:
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
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
        "project: portfolio-tracker",
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
    return filename


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
    fm["_path"] = str(path)
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
    if data.get("type") not in {"bug", "feature", "suggestion", "error"}:
        return JSONResponse({"error": "Invalid type"}, status_code=400)
    if not data.get("message") and data.get("type") != "error":
        return JSONResponse({"error": "Message required"}, status_code=400)

    filename = _save_ticket(data)

    try:
        notifier = SlackNotifier()
        emoji = TYPE_EMOJI.get(data["type"], "📝")
        label = TYPE_LABEL.get(data["type"], data["type"])
        text = data.get("message") or data.get("description") or ""
        await notifier.send_message(
            f"{emoji} *Nouveau feedback portfolio-tracker* — `{label}`\n"
            f"{text[:300]}\n<{data.get('url', '')}>"
        )
    except Exception as e:
        logger.warning("Slack notify failed: %s", e)

    return {"ok": True, "file": filename}


@router.post("/{ticket_id}/close")
async def close_ticket(ticket_id: str, x_internal_api_key: str = Header(default="")):
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    path = _find_ticket(ticket_id)
    if not path:
        return JSONResponse({"error": "Ticket not found"}, status_code=404)
    raw = path.read_text()
    t = _parse_ticket(path)
    if t.get("status") == "closed":
        return JSONResponse({"error": "Already closed"}, status_code=409)
    closed_at = datetime.now(timezone.utc).isoformat()
    path.write_text(raw.replace("status: open", f"status: closed\nclosed_at: {closed_at}", 1))
    return {"ok": True}


@router.get("/closed-since")
async def closed_since(since: str, x_internal_api_key: str = Header(default="")):
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return JSONResponse({"error": "Invalid since format"}, status_code=400)

    results = []
    if TICKETS_DIR.exists():
        for f in sorted(TICKETS_DIR.glob("*.md"), reverse=True):
            t = _parse_ticket(f)
            if t.get("status") != "closed":
                continue
            try:
                closed_at_dt = datetime.fromisoformat(t.get("closed_at", ""))
                if closed_at_dt.tzinfo is None:
                    closed_at_dt = closed_at_dt.replace(tzinfo=timezone.utc)
                if closed_at_dt >= since_dt:
                    results.append({"id": t.get("id"), "type": t.get("type"),
                                    "description": t.get("description"), "closed_at": t.get("closed_at"),
                                    "url": t.get("url")})
            except Exception:
                continue
    return {"tickets": results}
