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
    dismiss_budget_update_flag, get_uncovered_count, get_month_transactions,
    get_uncovered_transactions, get_category_year_transactions,
)
from app.services.database import (
    get_classification_rules, create_classification_rule,
    delete_classification_rule, check_rule_conflict, apply_rule_to_year,
    get_classifier_rules_all, get_classifier_rules_for_settings,
    create_classifier_rule_new, update_classifier_rule_fields,
    delete_classifier_rule_new, reorder_classifier_rules,
    apply_classifier_rule_to_year, check_rule_conflict_new,
    get_classifier_snapshots, create_classifier_snapshot,
    restore_classifier_snapshot,
)

router = APIRouter()


def _annotate_with_rules(txs: list[dict], rules: list[dict]) -> None:
    """Annotate each transaction with matched rule info (multi-keyword aware)."""
    for tx in txs:
        lc = (tx.get("label_clean") or tx.get("label") or "").upper()
        matched = None
        for rule in rules:
            keywords = [k.upper() for k in rule.get("keywords", [])]
            if not keywords:
                continue
            if rule.get("match_mode") == "AND":
                if all(k in lc for k in keywords):
                    matched = rule
                    break
            else:
                if any(k in lc for k in keywords):
                    matched = rule
                    break
        tx["_matched_rule_category"] = matched["category"] if matched else None
        tx["_matched_rule_id"] = matched["id"] if matched else None


@router.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request, year_id: int = Query(default=None)):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    years = await get_budget_years()
    if not years:
        return templates.TemplateResponse(request, "budget.html", {"years": [], "view": None, "uncovered_count": 0})

    from datetime import date as _date
    today_str = _date.today().isoformat()
    default = next(
        (y for y in years if str(y["start_date"]) <= today_str <= str(y["end_date"])),
        years[0]
    )
    selected = next((y for y in years if y["id"] == year_id), default)
    lines = await get_budget_lines(selected["id"])
    actuals, tx_counts = await get_monthly_actuals(selected["id"])
    view = build_budget_view(selected, lines, actuals, tx_counts)
    uncovered = await get_uncovered_count(selected["id"])

    for y in years:
        y["start_date"] = str(y["start_date"])
        y["end_date"] = str(y["end_date"])
    view["year"]["start_date"] = str(view["year"]["start_date"])
    view["year"]["end_date"] = str(view["year"]["end_date"])

    return templates.TemplateResponse(request, "budget.html", {
        "years": years,
        "selected_year_id": selected["id"],
        "view": view,
        "uncovered_count": uncovered,
    })


@router.get("/budget/month", response_class=HTMLResponse)
async def budget_month_page(
    request: Request,
    year_id: int = Query(...),
    month: str = Query(...),
    sort: str = Query(default="date"),
):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    years = await get_budget_years()
    year = next((y for y in years if y["id"] == year_id), None)
    if not year:
        return RedirectResponse("/budget", status_code=302)

    txs = await get_month_transactions(year_id, month)
    lines = await get_budget_lines(year_id)
    categories = [l["category"] for l in lines]  # ordered by sort_order

    rules = await get_classifier_rules_all()
    _annotate_with_rules(txs, rules)

    total_expenses = sum(t["amount"] for t in txs if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txs if t["amount"] > 0)

    return templates.TemplateResponse(request, "month.html", {
        "year": year,
        "year_id": year_id,
        "month": month,
        "sort": sort,
        "txs": txs,
        "categories": categories,
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income + total_expenses, 2),
    })


@router.get("/budget/uncovered", response_class=HTMLResponse)
async def budget_uncovered_page(
    request: Request,
    year_id: int = Query(...),
    sort: str = Query(default="date"),
):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    years = await get_budget_years()
    year = next((y for y in years if y["id"] == year_id), None)
    if not year:
        return RedirectResponse("/budget", status_code=302)

    txs = await get_uncovered_transactions(year_id)
    lines = await get_budget_lines(year_id)
    categories = [l["category"] for l in lines]

    rules = await get_classifier_rules_all()
    _annotate_with_rules(txs, rules)

    total_expenses = sum(t["amount"] for t in txs if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txs if t["amount"] > 0)

    return templates.TemplateResponse(request, "month.html", {
        "year": year,
        "year_id": year_id,
        "month": f"Non couvertes — {year['year_label']}",
        "sort": sort,
        "txs": txs,
        "categories": categories,
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income + total_expenses, 2),
    })


@router.get("/budget/ytd", response_class=HTMLResponse)
async def budget_ytd_page(
    request: Request,
    year_id: int = Query(...),
    category: str = Query(...),
    sort: str = Query(default="date"),
):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    years = await get_budget_years()
    year = next((y for y in years if y["id"] == year_id), None)
    if not year:
        return RedirectResponse("/budget", status_code=302)

    txs = await get_category_year_transactions(year_id, category)
    lines = await get_budget_lines(year_id)
    categories = [l["category"] for l in lines]

    rules = await get_classifier_rules_all()
    _annotate_with_rules(txs, rules)

    total_expenses = sum(t["amount"] for t in txs if t["amount"] < 0)
    total_income = sum(t["amount"] for t in txs if t["amount"] > 0)

    return templates.TemplateResponse(request, "month.html", {
        "year": year,
        "year_id": year_id,
        "month": f"{category} — {year['year_label']}",
        "sort": sort,
        "txs": txs,
        "categories": categories,
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income + total_expenses, 2),
    })


@router.get("/budget/settings", response_class=HTMLResponse)
async def budget_settings(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/", status_code=302)

    rules = await get_classifier_rules_for_settings()
    snapshots = await get_classifier_snapshots(limit=20)
    years = await get_budget_years()
    categories = []
    current_year_id = None
    if years:
        from datetime import date as _date
        today_str = _date.today().isoformat()
        current_year = next(
            (y for y in years if str(y["start_date"]) <= today_str <= str(y["end_date"])),
            years[0],
        )
        lines = await get_budget_lines(current_year["id"])
        categories = sorted([l["category"] for l in lines])
        current_year_id = current_year["id"]

    return templates.TemplateResponse(request, "settings.html", {
        "rules": rules,
        "categories": categories,
        "snapshots": snapshots,
        "current_year_id": current_year_id,
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


class RulePayload(BaseModel):
    keyword: str
    category: str
    year_id: int | None = None


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


# ── Legacy rules API (kept for ⚡ modal — now creates stage-0 rules) ──────────

@router.get("/api/rules")
async def api_get_rules(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    rules = await get_classifier_rules_all()
    return rules


@router.post("/api/rules")
async def api_create_rule(request: Request, payload: RulePayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    if not payload.keyword.strip() or not payload.category.strip():
        return JSONResponse({"error": "Mot-clé et catégorie requis."}, status_code=400)
    rule_id = await create_classifier_rule_new(
        stage=0, keywords=[payload.keyword.strip()],
        match_mode="OR", category=payload.category.strip(), source="auto",
    )
    applied = 0
    if payload.year_id:
        applied = await apply_classifier_rule_to_year(rule_id, payload.year_id)
    return {"ok": True, "id": rule_id, "applied": applied}


@router.get("/api/rules/check")
async def api_check_rule(
    request: Request,
    keyword: str = Query(...),
    category: str = Query(...),
):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    conflict = await check_rule_conflict_new(keyword, category)
    return {"conflict": conflict is not None, "existing": conflict}


# ── Classifier rules API (new system) ────────────────────────────────────────

class ClassifierRulePayload(BaseModel):
    stage: int = 2
    keywords: list[str]
    match_mode: str = "OR"
    category: str
    source: str = "user"
    year_id: int | None = None


class ClassifierRuleUpdate(BaseModel):
    stage: int | None = None
    sort_order: int | None = None
    keywords: list[str] | None = None
    match_mode: str | None = None
    category: str | None = None
    is_active: bool | None = None


class ReorderItem(BaseModel):
    id: int
    stage: int
    sort_order: int


@router.get("/api/classifier/rules")
async def api_get_classifier_rules(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    return await get_classifier_rules_for_settings()


@router.post("/api/classifier/rules")
async def api_create_classifier_rule(request: Request, payload: ClassifierRulePayload):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    if not payload.keywords or not payload.category.strip():
        return JSONResponse({"error": "Mots-clés et catégorie requis."}, status_code=400)
    rule_id = await create_classifier_rule_new(
        stage=payload.stage, keywords=payload.keywords,
        match_mode=payload.match_mode, category=payload.category,
        source=payload.source, year_id=payload.year_id,
    )
    return {"ok": True, "id": rule_id}


@router.put("/api/classifier/rules/reorder")
async def api_reorder_classifier_rules(request: Request, items: list[ReorderItem]):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await reorder_classifier_rules([i.dict() for i in items])
    return {"ok": True}


@router.put("/api/classifier/rules/{rule_id}")
async def api_update_classifier_rule(request: Request, rule_id: int, payload: ClassifierRuleUpdate):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    fields = {k: v for k, v in payload.dict().items() if v is not None}
    await update_classifier_rule_fields(rule_id, fields)
    return {"ok": True}


@router.delete("/api/classifier/rules/{rule_id}")
async def api_delete_classifier_rule(request: Request, rule_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await delete_classifier_rule_new(rule_id)
    return {"ok": True}


@router.get("/api/classifier/snapshots")
async def api_get_snapshots(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    return await get_classifier_snapshots()


@router.post("/api/classifier/snapshots")
async def api_create_snapshot(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    body = await request.json()
    snap_id = await create_classifier_snapshot(body.get("label", "Manuel"))
    return {"ok": True, "id": snap_id}


@router.post("/api/classifier/snapshots/{snapshot_id}/restore")
async def api_restore_snapshot(request: Request, snapshot_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Non authentifié."}, status_code=401)
    await create_classifier_snapshot("avant-restauration")
    await restore_classifier_snapshot(snapshot_id)
    return {"ok": True}
