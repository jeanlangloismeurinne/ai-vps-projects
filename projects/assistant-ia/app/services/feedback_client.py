"""Client HTTP générique pour interroger le endpoint closed-since d'un service."""
import logging
import httpx

logger = logging.getLogger(__name__)


async def get_closed_since(svc: dict, since: str) -> list[dict]:
    """
    Appelle GET {base_url}{closed_since_path}?since={since}.
    Retourne la liste des tickets fermés ou [] en cas d'erreur.
    """
    url = svc["base_url"].rstrip("/") + svc["closed_since_path"]
    api_key = svc.get("api_key", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"since": since},
                headers={"X-Internal-Api-Key": api_key} if api_key else {},
                timeout=10.0,
            )
        if resp.status_code == 200:
            return resp.json().get("tickets", [])
        logger.warning("feedback_client: %s returned %s", url, resp.status_code)
    except Exception as exc:
        logger.error("feedback_client error for %s: %s", url, exc)
    return []
