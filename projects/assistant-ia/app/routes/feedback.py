"""
Endpoint feedback pour les services hébergés dans assistant-ia (journal, kanban, etc.).
Même pattern que bank-review : stockage Markdown + notification Slack.
"""
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime, timezone
import re, time, os, logging

from app.services import slack_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["feedback"])

_PROJECT_ROOT = Path(__file__).parent.parent.parent
INTERNAL_API_KEY = os.getenv("ASSISTANT_INTERNAL_API_KEY", "")

_VALID_PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VALID_TYPES = {"bug", "feature", "suggestion", "error"}

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}
TYPE_LABEL = {"bug": "Bug", "feature": "Feature", "suggestion": "Suggestion", "error": "Erreur JS"}


def _tickets_dir(project: str) -> Path:
    d = _PROJECT_ROOT / "feedback-tickets" / project
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", text[:40].lower()))


def _save_ticket(project: str, data: dict) -> str:
    ticket_id = int(time.time() * 1000)
    slug = _slug(data.get("message") or "no-message")
    filename = f"{ticket_id}-{data['type']}-{slug}.md"

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    emoji = TYPE_EMOJI.get(data["type"], "📝")
    label = TYPE_LABEL.get(data["type"], data["type"])
    text = data.get("message") or "_Aucune description_"

    lines = [
        "---",
        f"id: {ticket_id}",
        f"type: {data['type']}",
        "status: open",
        f"date: {datetime.now().isoformat()}",
        f"project: {project}",
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
    (_tickets_dir(project) / filename).write_text("\n".join(lines))
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
    return fm


def _find_ticket(project: str, ticket_id: str) -> Path | None:
    d = _tickets_dir(project)
    for f in d.glob(f"{ticket_id}-*.md"):
        return f
    return None


@router.post("/{project}")
async def post_feedback(project: str, request: Request):
    if not _VALID_PROJECT_RE.match(project):
        return JSONResponse({"error": f"Invalid project name '{project}'"}, status_code=400)

    data = await request.json()
    if data.get("type") not in VALID_TYPES:
        return JSONResponse({"error": "Invalid type"}, status_code=400)
    if not data.get("message") and data.get("type") != "error":
        return JSONResponse({"error": "Message required"}, status_code=400)

    filename = _save_ticket(project, data)

    channel = settings.FEEDBACK_CHANNEL_ID or settings.FEATURES_AI_CHANNEL_ID
    emoji = TYPE_EMOJI.get(data["type"], "📝")
    text = f"{emoji} *Nouveau feedback {project}* — `{data['type']}`\n{(data.get('message') or '')[:300]}"
    try:
        await slack_client.post_message(
            channel=channel,
            text=text,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": text}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"URL : `{data.get('url', '')}`"}]},
            ],
        )
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)

    return {"ok": True, "file": filename}


@router.post("/{project}/{ticket_id}/close")
async def close_ticket(project: str, ticket_id: str, x_internal_api_key: str = Header(default="")):
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not _VALID_PROJECT_RE.match(project):
        return JSONResponse({"error": f"Invalid project name '{project}'"}, status_code=400)

    path = _find_ticket(project, ticket_id)
    if not path:
        return JSONResponse({"error": "Ticket not found"}, status_code=404)

    raw = path.read_text()
    t = _parse_ticket(path)
    if t.get("status") == "closed":
        return JSONResponse({"error": "Already closed"}, status_code=409)

    closed_at = datetime.now(timezone.utc).isoformat()
    updated = raw.replace("status: open", f"status: closed\nclosed_at: {closed_at}", 1)
    path.write_text(updated)
    return {"ok": True, "ticket_id": ticket_id}


@router.get("/{project}/closed-since")
async def closed_since(
    project: str,
    since: str,
    x_internal_api_key: str = Header(default=""),
):
    if INTERNAL_API_KEY and x_internal_api_key != INTERNAL_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not _VALID_PROJECT_RE.match(project):
        return JSONResponse({"error": f"Invalid project name '{project}'"}, status_code=400)

    try:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return JSONResponse({"error": "Invalid since format (use ISO 8601)"}, status_code=400)

    results = []
    d = _tickets_dir(project)
    for f in sorted(d.glob("*.md"), reverse=True):
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
