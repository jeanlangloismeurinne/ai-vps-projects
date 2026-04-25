import httpx
from app.config import settings

_SLACK_API = "https://slack.com/api/chat.postMessage"


async def post_message(channel: str, blocks: list, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(
            _SLACK_API,
            headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
            json={"channel": channel, "blocks": blocks, "text": text},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error')}")
