import httpx
from app.config import settings


async def import_file(
    filename: str, content: bytes, mime_type: str, vacation_ranges: str = ""
) -> dict:
    """Upload a file to bank-review /api/import/direct and return the result.

    `vacation_ranges` (optionnel) : JSON `[["YYYY-MM-DD","YYYY-MM-DD"], ...]` transmis au
    classifieur, comme les périodes de vacances de l'import web.
    """
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{settings.BANK_REVIEW_BASE_URL}/api/import/direct",
            headers={"X-Internal-Api-Key": settings.BANK_REVIEW_API_KEY},
            files={"file": (filename, content, mime_type)},
            data={"vacation_ranges": vacation_ranges},
        )
        resp.raise_for_status()
        return resp.json()
