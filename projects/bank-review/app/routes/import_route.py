import os
import json
from datetime import date, datetime
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.routes.auth import is_authenticated
from app.services.importer import run_import_pipeline, append_to_historical

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "uploads"
HISTORY_PATH = os.path.join(UPLOAD_DIR, "2025_comptes_raw_data.xlsx")


@router.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "import.html", {"error": None})


@router.post("/import", response_class=HTMLResponse)
async def import_upload(
    request: Request,
    file: UploadFile = File(...),
    has_vacations: str = Form("no"),
    vacation_ranges: str = Form(""),   # JSON: [["2025-07-14","2025-07-28"], ...]
):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    # Save uploaded CSV
    content = await file.read()
    dest = os.path.join(UPLOAD_DIR, "import_pending.csv")
    with open(dest, "wb") as f:
        f.write(content)

    # Parse vacation periods
    periods: list[tuple[date, date]] = []
    if has_vacations == "yes" and vacation_ranges.strip():
        try:
            raw = json.loads(vacation_ranges)
            for item in raw:
                start = datetime.strptime(item[0], "%Y-%m-%d").date()
                end = datetime.strptime(item[1], "%Y-%m-%d").date()
                periods.append((start, end))
        except Exception as e:
            return templates.TemplateResponse(
                request, "import.html",
                {"error": f"Dates de vacances invalides : {e}"}
            )

    # Run pipeline
    try:
        classified = await run_import_pipeline(HISTORY_PATH, dest, periods)
    except Exception as e:
        return templates.TemplateResponse(
            request, "import.html", {"error": f"Erreur pipeline : {e}"}
        )

    # Store in session for confirmation step
    request.session["classified"] = json.dumps(classified)

    stats = _compute_stats(classified)
    return templates.TemplateResponse(
        request, "review.html",
        {"rows": classified, "stats": stats}
    )


class ConfirmPayload(BaseModel):
    rows: list[dict]   # may include user overrides on "category"


@router.post("/api/import/confirm")
async def import_confirm(request: Request, payload: ConfirmPayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    try:
        nb = append_to_historical(HISTORY_PATH, payload.rows)
        # Clear session state
        request.session.pop("classified", None)
        return {"added": nb}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def _compute_stats(rows: list[dict]) -> dict:
    if not rows:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "by_method": {}}
    high = sum(1 for r in rows if r["confidence"] >= 80)
    medium = sum(1 for r in rows if 50 <= r["confidence"] < 80)
    low = sum(1 for r in rows if r["confidence"] < 50)
    by_method: dict[str, int] = {}
    for r in rows:
        by_method[r["method"]] = by_method.get(r["method"], 0) + 1
    return {"total": len(rows), "high": high, "medium": medium, "low": low, "by_method": by_method}
