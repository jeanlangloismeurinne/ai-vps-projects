import os
import uuid
import json
from datetime import date, datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.templates_env import templates
from pydantic import BaseModel

from app.routes.auth import is_authenticated
from app.services.importer import run_import_pipeline
from app.services.database import (
    insert_transactions, upsert_account,
    get_classification_rules,
    create_import_session, get_import_sessions, link_transactions_to_session,
    get_session_with_transactions,
)
from app.services.format_checker import check_format, apply_mapping
from app.services.budget import (
    get_budget_years, create_next_budget_year, get_budget_lines, get_all_categories_for_year,
)

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _year_categories_for_date(years: list[dict], max_date_str: str | None) -> list[str]:
    """Return sorted category names from the budget year that contains max_date."""
    if not max_date_str or not years:
        return []
    matching = next(
        (y for y in years if str(y["start_date"]) <= max_date_str <= str(y["end_date"])),
        years[0],
    )
    return matching.get("_categories", [])


@router.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)
    sessions = await get_import_sessions(limit=20)
    return templates.TemplateResponse(request, "import.html", {"error": None, "sessions": sessions})


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

    fmt = check_format(content)
    if not fmt.can_proceed:
        sessions = await get_import_sessions(limit=20)
        return templates.TemplateResponse(
            request, "import.html",
            {"error": f"Fichier non reconnu — colonnes obligatoires introuvables : "
                      f"{', '.join(fmt.missing_required)}", "sessions": sessions}
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
            sessions = await get_import_sessions(limit=20)
            return templates.TemplateResponse(
                request, "import.html",
                {"error": f"Dates de vacances invalides : {e}", "sessions": sessions}
            )

    try:
        classified = await run_import_pipeline(dest, periods)
    except Exception as e:
        sessions = await get_import_sessions(limit=20)
        return templates.TemplateResponse(
            request, "import.html", {"error": f"Erreur pipeline : {e}", "sessions": sessions}
        )

    # Determine year and fetch its categories for review dropdowns
    dates = [r["date_op"] for r in classified if isinstance(r.get("date_op"), date)]
    max_date_str = max((str(d)[:10] for d in dates), default=None)
    years = await get_budget_years()
    categories = []
    if max_date_str and years:
        matching_year = next(
            (y for y in years if str(y["start_date"]) <= max_date_str <= str(y["end_date"])),
            years[0],
        )
        lines = await get_budget_lines(matching_year["id"])
        categories = sorted([l["category"] for l in lines])

    # Load rules to show badges on rows that already have a matching rule
    rules = await get_classification_rules()
    rules_upper = [(r["keyword"].upper(), r["category"], r["id"]) for r in rules]

    serializable = sorted(_serialize_rows(classified), key=lambda r: r.get("confidence") or 0)

    # Annotate each row with matched rule info
    for row in serializable:
        lc = (row.get("label_clean") or row.get("label") or "").upper()
        matched = next(((cat, rid) for kw, cat, rid in rules_upper if kw in lc), None)
        row["_matched_rule_category"] = matched[0] if matched else None
        row["_matched_rule_id"] = matched[1] if matched else None

    stats = _compute_stats(serializable)

    return templates.TemplateResponse(
        request, "review.html",
        {
            "rows": serializable,
            "stats": stats,
            "categories": categories,
            "filename": file.filename,
            "format_warnings": fmt.warnings,
            "format_summary": fmt.summary() if not fmt.is_exact_match else None,
        }
    )


class ConfirmPayload(BaseModel):
    rows: list[dict]
    filename: str | None = None


@router.post("/api/import/confirm")
async def import_confirm(request: Request, payload: ConfirmPayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    try:
        accounts_seen: set[tuple] = set()
        for row in payload.rows:
            num = row.get("account_num")
            label = row.get("account_label")
            if num and (num, label) not in accounts_seen:
                await upsert_account(num, label or "")
                accounts_seen.add((num, label))

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

        # Create import session and link inserted transactions
        dates = [r["date_op"] for r in db_rows if isinstance(r.get("date_op"), date)]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        years = await get_budget_years()
        year_id_for_session = None
        if date_max and years:
            max_str = str(date_max)
            year_id_for_session = next(
                (y["id"] for y in years if str(y["start_date"]) <= max_str <= str(y["end_date"])),
                None,
            )

        session_id = await create_import_session(
            payload.filename, nb, date_min, date_max, year_id_for_session
        )
        dedup_keys = [r["dedup_key"] for r in db_rows if r.get("dedup_key")]
        await link_transactions_to_session(dedup_keys, session_id)

        # Auto-create next budget year if needed
        new_year = None
        if date_max and years:
            latest_end = years[0]["end_date"]
            if isinstance(latest_end, str):
                latest_end = date.fromisoformat(latest_end)
            if date_max > latest_end:
                new_year = await create_next_budget_year()

        return {"added": nb, "new_year": new_year, "session_id": session_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/import/history/{session_id}", response_class=HTMLResponse)
async def import_history(request: Request, session_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    session, txs = await get_session_with_transactions(session_id)
    if not session:
        return HTMLResponse("Import introuvable.", status_code=404)

    # Fetch categories for this session's year
    categories = []
    if session.get("year_id"):
        lines = await get_all_categories_for_year(session["year_id"])
        categories = sorted([l["category"] for l in lines])

    # Annotate with rule badges
    rules = await get_classification_rules()
    rules_upper = [(r["keyword"].upper(), r["category"], r["id"]) for r in rules]
    for tx in txs:
        lc = (tx.get("label_clean") or tx.get("label") or "").upper()
        matched = next(((cat, rid) for kw, cat, rid in rules_upper if kw in lc), None)
        tx["_matched_rule_category"] = matched[0] if matched else None
        tx["_matched_rule_id"] = matched[1] if matched else None

    stats = _compute_stats_from_txs(txs)

    return templates.TemplateResponse(request, "history.html", {
        "session": session,
        "rows": txs,
        "stats": stats,
        "categories": categories,
    })


def _require_internal_api_key(x_internal_api_key: str = Header(default="")):
    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected or x_internal_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/api/import/direct")
async def import_direct(
    request: Request,
    file: UploadFile = File(...),
    _: None = Depends(_require_internal_api_key),
):
    """Endpoint machine-to-machine : import complet en une seule requête, sans étape de review."""

    content = await file.read()

    fmt = check_format(content)
    if not fmt.can_proceed:
        return JSONResponse(
            {"error": f"Format non reconnu : {', '.join(fmt.missing_required)}"},
            status_code=400,
        )
    if not fmt.is_exact_match:
        content = apply_mapping(content, fmt)

    tmp_name = f"import_direct_{uuid.uuid4().hex}.csv"
    dest = os.path.join(UPLOAD_DIR, tmp_name)
    try:
        with open(dest, "wb") as f:
            f.write(content)

        classified = await run_import_pipeline(dest, [])
    except Exception as e:
        return JSONResponse({"error": f"Erreur pipeline : {e}"}, status_code=500)
    finally:
        if os.path.exists(dest):
            os.remove(dest)

    rows = _serialize_rows(classified)

    try:
        accounts_seen: set[tuple] = set()
        for row in rows:
            num = row.get("account_num")
            label = row.get("account_label")
            if num and (num, label) not in accounts_seen:
                await upsert_account(num, label or "")
                accounts_seen.add((num, label))

        db_rows = []
        for row in rows:
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

        dates = [r["date_op"] for r in db_rows if isinstance(r.get("date_op"), date)]
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        years = await get_budget_years()
        year_id_for_session = None
        if date_max and years:
            max_str = str(date_max)
            year_id_for_session = next(
                (y["id"] for y in years if str(y["start_date"]) <= max_str <= str(y["end_date"])),
                None,
            )

        session_id = await create_import_session(
            file.filename, nb, date_min, date_max, year_id_for_session
        )
        dedup_keys = [r["dedup_key"] for r in db_rows if r.get("dedup_key")]
        await link_transactions_to_session(dedup_keys, session_id)

        new_year = None
        if date_max and years:
            latest_end = years[0]["end_date"]
            if isinstance(latest_end, str):
                latest_end = date.fromisoformat(latest_end)
            if date_max > latest_end:
                new_year = await create_next_budget_year()

        return {
            "session_id": session_id,
            "added": nb,
            "date_min": str(date_min) if date_min else None,
            "date_max": str(date_max) if date_max else None,
            "year_id": year_id_for_session,
            "new_year": new_year,
        }
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


def _compute_stats_from_txs(txs: list[dict]) -> dict:
    """Same as _compute_stats but for DB-fetched transactions (confidence can be None)."""
    return _compute_stats(txs)
