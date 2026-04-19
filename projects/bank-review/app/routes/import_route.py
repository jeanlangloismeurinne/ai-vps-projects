import os
import json
from datetime import date, datetime
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.templates_env import templates
from pydantic import BaseModel

from app.routes.auth import is_authenticated
from app.services.importer import run_import_pipeline
from app.services.database import insert_transactions, upsert_account
from app.services.format_checker import check_format, apply_mapping

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    vacation_ranges: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    content = await file.read()

    # Format check — remap columns if needed, block if required cols missing
    fmt = check_format(content)
    if not fmt.can_proceed:
        return templates.TemplateResponse(
            request, "import.html",
            {"error": f"Fichier non reconnu — colonnes obligatoires introuvables : "
                      f"{', '.join(fmt.missing_required)}"}
        )
    if not fmt.is_exact_match:
        content = apply_mapping(content, fmt)

    dest = os.path.join(UPLOAD_DIR, "import_pending.csv")
    with open(dest, "wb") as f:
        f.write(content)

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

    try:
        classified = await run_import_pipeline(dest, periods)
    except Exception as e:
        return templates.TemplateResponse(
            request, "import.html", {"error": f"Erreur pipeline : {e}"}
        )

    serializable = _serialize_rows(classified)
    stats = _compute_stats(serializable)

    return templates.TemplateResponse(
        request, "review.html",
        {
            "rows": serializable,
            "stats": stats,
            "format_warnings": fmt.warnings,
            "format_summary": fmt.summary() if not fmt.is_exact_match else None,
        }
    )


class ConfirmPayload(BaseModel):
    rows: list[dict]


@router.post("/api/import/confirm")
async def import_confirm(request: Request, payload: ConfirmPayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    try:
        # Upsert accounts found in this batch
        accounts_seen: set[tuple] = set()
        for row in payload.rows:
            num = row.get("account_num")
            label = row.get("account_label")
            if num and (num, label) not in accounts_seen:
                await upsert_account(num, label or "")
                accounts_seen.add((num, label))

        # Prepare rows for DB (restore date types, strip UI-only fields)
        db_rows = []
        for row in payload.rows:
            db_row = {k: v for k, v in row.items() if not k.startswith("_")}
            for date_field in ("date_op", "date_val", "real_date"):
                val = db_row.get(date_field)
                if isinstance(val, str) and val:
                    try:
                        db_row[date_field] = datetime.strptime(val, "%Y-%m-%d").date()
                    except Exception:
                        db_row[date_field] = None
            db_rows.append(db_row)

        nb = await insert_transactions(db_rows)
        return {"added": nb}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def _serialize_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, date):
                r[k] = v.isoformat()
        out.append(r)
    return out


def _compute_stats(rows: list[dict]) -> dict:
    if not rows:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "by_method": {}}
    high   = sum(1 for r in rows if (r.get("confidence") or 0) >= 80)
    medium = sum(1 for r in rows if 50 <= (r.get("confidence") or 0) < 80)
    low    = sum(1 for r in rows if (r.get("confidence") or 0) < 50)
    by_method: dict[str, int] = {}
    for r in rows:
        m = r.get("classification_method", "?")
        by_method[m] = by_method.get(m, 0) + 1
    return {"total": len(rows), "high": high, "medium": medium, "low": low, "by_method": by_method}
