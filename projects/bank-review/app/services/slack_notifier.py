import os
import logging
import httpx

logger = logging.getLogger(__name__)

_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
_CHANNEL = os.getenv("SLACK_FEEDBACK_CHANNEL", "")

TYPE_EMOJI = {"bug": "🐛", "feature": "✨", "suggestion": "💡", "error": "🔴"}


async def _post(text: str, blocks: list | None = None) -> None:
    if not _TOKEN or not _CHANNEL:
        return
    payload: dict = {"channel": _CHANNEL, "text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {_TOKEN}"},
                json=payload,
                timeout=5.0,
            )
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)


async def notify_new_feedback(ticket_type: str, message: str, url: str) -> None:
    """Notifie #feedback-{service} qu'un nouveau ticket vient d'être créé."""
    emoji = TYPE_EMOJI.get(ticket_type, "📝")
    text = f"{emoji} *Nouveau feedback bank-review* — `{ticket_type}`\n{message[:300]}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"URL : `{url}`"}]},
    ]
    await _post(text, blocks)
