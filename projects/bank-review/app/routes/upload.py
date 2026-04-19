import os
import json
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_env import templates

from app.routes.auth import is_authenticated
from app.services.file_parser import parse_upload, df_to_preview

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "upload.html", {"error": None})


@router.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    allowed = {"xlsx", "xls", "csv"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        return templates.TemplateResponse(
            request, "upload.html",
            {"error": f"Format .{ext} non supporté. Utilisez Excel (.xlsx) ou CSV."},
        )

    content = await file.read()

    try:
        df, warnings = parse_upload(file.filename, content)
    except Exception as e:
        return templates.TemplateResponse(
            request, "upload.html", {"error": f"Erreur de lecture : {e}"}
        )

    preview = df_to_preview(df)

    # Persist parsed data in session for analysis
    request.session["file_name"] = file.filename
    request.session["preview"] = json.dumps(preview)

    # Save raw file for Claude analysis
    dest = os.path.join(UPLOAD_DIR, f"current.{ext}")
    with open(dest, "wb") as f:
        f.write(content)
    request.session["file_path"] = dest

    return templates.TemplateResponse(
        request, "view.html",
        {"file_name": file.filename, "preview": preview, "warnings": warnings},
    )
