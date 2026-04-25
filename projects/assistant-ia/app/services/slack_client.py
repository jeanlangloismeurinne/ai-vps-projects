import httpx
from app.config import settings

_SLACK_POST = "https://slack.com/api/chat.postMessage"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}


async def post_message(channel: str, blocks: list, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(
            _SLACK_POST,
            headers=_headers(),
            json={"channel": channel, "blocks": blocks, "text": text},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error')}")


async def post_text(channel: str, text: str, thread_ts: str | None = None) -> str:
    """Envoie un message texte simple. Retourne le timestamp Slack du message."""
    payload: dict = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(_SLACK_POST, headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error')}")
        return data["ts"]
