import httpx
from app.config import settings


async def import_file(filename: str, content: bytes, mime_type: str) -> dict:
    """Upload a file to bank-review /api/import/direct and return the result."""
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{settings.BANK_REVIEW_BASE_URL}/api/import/direct",
            headers={"X-Internal-Api-Key": settings.BANK_REVIEW_API_KEY},
            files={"file": (filename, content, mime_type)},
        )
        resp.raise_for_status()
        return resp.json()
