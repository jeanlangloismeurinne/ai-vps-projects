from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.templates_env import templates
from pydantic import BaseModel

from app.routes.auth import is_authenticated
from app.services.budget import (
    get_budget_years, get_budget_lines, get_monthly_actuals,
    build_budget_view, update_budget_line,
    get_transactions_by_cell, recategorize_transaction,
    get_all_categories_for_year, add_budget_category,
    update_budget_category, rename_budget_category, delete_budget_category,
    dismiss_budget_update_flag,
)

router = APIRouter()


@router.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request, year_id: int = Query(default=None)):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    years = await get_budget_years()
    if not years:
        return templates.TemplateResponse(request, "budget.html", {"years": [], "view": None})

    from datetime import date as _date
    today_str = _date.today().isoformat()
    default = next(
        (y for y in years if str(y["start_date"]) <= today_str <= str(y["end_date"])),
        years[0]
    )
    selected = next((y for y in years if y["id"] == year_id), default)
    lines = await get_budget_lines(selected["id"])
    actuals = await get_monthly_actuals(selected["id"])
    view = build_budget_view(selected, lines, actuals)

    # Serialize dates for template
    for y in years:
        y["start_date"] = str(y["start_date"])
        y["end_date"] = str(y["end_date"])
    view["year"]["start_date"] = str(view["year"]["start_date"])
    view["year"]["end_date"] = str(view["year"]["end_date"])

    return templates.TemplateResponse(request, "budget.html", {
        "years": years,
        "selected_year_id": selected["id"],
        "view": view,
    })


class BudgetUpdate(BaseModel):
    year_id: int
    category: str
    monthly_budget: float


@router.post("/api/budget/update")
async def budget_update(request: Request, payload: BudgetUpdate):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await update_budget_line(payload.year_id, payload.category, payload.monthly_budget)
    return {"ok": True}


class RecategorizePayload(BaseModel):
    category: str


class CategoryAddPayload(BaseModel):
    year_id: int
    category: str
    group_name: str
    monthly_budget: float = 0
    is_income: bool = False
    sort_order: int = 99


class CategoryUpdatePayload(BaseModel):
    category: str
    group_name: str
    monthly_budget: float = 0
    is_income: bool = False
    sort_order: int = 99


@router.get("/api/transactions/by-cell")
async def api_transactions_by_cell(
    request: Request,
    category: str = Query(...),
    month: str = Query(...),
):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    rows = await get_transactions_by_cell(category, month)
    return rows


@router.post("/api/transactions/{tx_id}/recategorize")
async def api_recategorize(request: Request, tx_id: int, payload: RecategorizePayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await recategorize_transaction(tx_id, payload.category)
    return {"ok": True}


@router.get("/api/budget/year-categories")
async def api_year_categories(request: Request, year_id: int = Query(...)):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    cats = await get_all_categories_for_year(year_id)
    return cats


@router.post("/api/budget/category")
async def api_add_category(request: Request, payload: CategoryAddPayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    line_id = await add_budget_category(
        payload.year_id, payload.category, payload.group_name,
        payload.monthly_budget, payload.is_income, payload.sort_order,
    )
    return {"ok": True, "id": line_id}


@router.put("/api/budget/category/{line_id}")
async def api_update_category(request: Request, line_id: int, payload: CategoryUpdatePayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await rename_budget_category(line_id, payload.category)
    await update_budget_category(
        line_id, payload.group_name, payload.monthly_budget,
        payload.is_income, payload.sort_order,
    )
    return {"ok": True}


@router.delete("/api/budget/category/{line_id}")
async def api_delete_category(request: Request, line_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await delete_budget_category(line_id)
    return {"ok": True}


@router.post("/api/budget/year/{year_id}/dismiss-update")
async def api_dismiss_update(request: Request, year_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await dismiss_budget_update_flag(year_id)
    return {"ok": True}
