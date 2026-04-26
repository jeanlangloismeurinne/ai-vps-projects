"""Client HTTP générique pour interroger le endpoint /api/feedback/closed-since d'un service."""
import logging
import httpx

logger = logging.getLogger(__name__)


async def get_closed_since(base_url: str, since: str, api_key: str) -> list[dict]:
    """
    Appelle GET {base_url}/api/feedback/closed-since?since={since}.
    Retourne la liste des tickets fermés ou [] en cas d'erreur.
    """
    url = f"{base_url.rstrip('/')}/api/feedback/closed-since"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"since": since},
                headers={"X-Internal-Api-Key": api_key},
                timeout=10.0,
            )
        if resp.status_code == 200:
            return resp.json().get("tickets", [])
        logger.warning("feedback_client: %s returned %s", url, resp.status_code)
    except Exception as exc:
        logger.error("feedback_client error for %s: %s", base_url, exc)
    return []
