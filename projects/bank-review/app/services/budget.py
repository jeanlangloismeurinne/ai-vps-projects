"""
Budget aggregation service.
Computes monthly actuals from transactions and compares to budget lines.
"""
from datetime import date
from collections import defaultdict
from app.services.database import get_pool


# ── DB helpers ────────────────────────────────────────────────────────────────

async def get_budget_years() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, year_label, start_date, end_date FROM budget_years ORDER BY start_date DESC"
    )
    return [dict(r) for r in rows]


async def get_budget_lines(year_id: int) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT category, monthly_budget, group_name, sort_order, is_income
        FROM budget_lines
        WHERE year_id = $1
        ORDER BY sort_order
        """,
        year_id,
    )
    return [dict(r) for r in rows]


async def update_budget_line(year_id: int, category: str, monthly_budget: float):
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO budget_lines (year_id, category, monthly_budget, group_name, sort_order)
        VALUES ($1, $2, $3, 'Dépenses variables', 99)
        ON CONFLICT (year_id, category)
        DO UPDATE SET monthly_budget = EXCLUDED.monthly_budget
        """,
        year_id, category, monthly_budget,
    )


async def get_monthly_actuals(year_id: int) -> dict[str, dict[str, float]]:
    """
    Returns {category: {YYYY-MM: amount}} for all transactions in the year.
    Amounts are absolute values (expenses positive, income positive).
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT
            t.category,
            TO_CHAR(t.date_op, 'YYYY-MM') AS month,
            SUM(ABS(t.amount))            AS total
        FROM transactions t
        JOIN budget_years y ON t.date_op BETWEEN y.start_date AND y.end_date
        WHERE y.id = $1
          AND t.category IS NOT NULL
        GROUP BY t.category, TO_CHAR(t.date_op, 'YYYY-MM')
        ORDER BY t.category, month
        """,
        year_id,
    )
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        result[r["category"]][r["month"]] = float(r["total"])
    return dict(result)


# ── Budget view builder ───────────────────────────────────────────────────────

def build_budget_view(
    year: dict,
    lines: list[dict],
    actuals: dict[str, dict[str, float]],
    today: date | None = None,
) -> dict:
    """
    Build the full budget view dict for the template.
    """
    today = today or date.today()
    months = _year_months(year["start_date"], year["end_date"])
    elapsed_months = _elapsed_months(months, today)

    groups: dict[str, list[dict]] = defaultdict(list)

    for line in lines:
        cat = line["category"]
        budget = float(line["monthly_budget"])
        cat_actuals = actuals.get(cat, {})

        monthly = []
        for m in months:
            actual = cat_actuals.get(m, 0.0)
            variance = budget - actual if not line["is_income"] else actual - budget
            monthly.append({
                "month": m,
                "actual": actual,
                "budget": budget,
                "variance": round(variance, 2),
                "is_current": m == today.strftime("%Y-%m"),
                "is_future": m > today.strftime("%Y-%m"),
            })

        ytd_actual = sum(cat_actuals.get(m, 0.0) for m in months[:elapsed_months])
        ytd_budget = budget * elapsed_months
        ytd_variance = (ytd_budget - ytd_actual) if not line["is_income"] else (ytd_actual - ytd_budget)
        avg_actual = (ytd_actual / elapsed_months) if elapsed_months else 0.0

        # Progress ratio for bar (capped at 150%)
        progress = min(150, round(100 * ytd_actual / ytd_budget)) if ytd_budget else 0

        groups[line["group_name"]].append({
            "category":      cat,
            "monthly_budget": budget,
            "is_income":     line["is_income"],
            "monthly":       monthly,
            "ytd_actual":    round(ytd_actual, 2),
            "ytd_budget":    round(ytd_budget, 2),
            "ytd_variance":  round(ytd_variance, 2),
            "avg_actual":    round(avg_actual, 2),
            "progress":      progress,
            "status":        _status(ytd_variance, ytd_budget, line["is_income"]),
        })

    # Group totals
    group_list = []
    for group_name, cats in groups.items():
        g_ytd_actual  = sum(c["ytd_actual"]  for c in cats if not c["is_income"])
        g_ytd_budget  = sum(c["ytd_budget"]  for c in cats if not c["is_income"])
        g_ytd_income  = sum(c["ytd_actual"]  for c in cats if c["is_income"])

        monthly_totals = []
        for i, m in enumerate(months):
            g_actual = sum(c["monthly"][i]["actual"] for c in cats if not c["is_income"])
            g_budget = sum(c["monthly_budget"] for c in cats if not c["is_income"])
            monthly_totals.append({
                "month": m,
                "actual": round(g_actual, 2),
                "budget": round(g_budget, 2),
                "is_current": m == today.strftime("%Y-%m"),
                "is_future": m > today.strftime("%Y-%m"),
            })

        group_list.append({
            "name":          group_name,
            "categories":    cats,
            "ytd_actual":    round(g_ytd_actual, 2),
            "ytd_budget":    round(g_ytd_budget, 2),
            "ytd_variance":  round(g_ytd_budget - g_ytd_actual, 2),
            "monthly":       monthly_totals,
        })

    return {
        "year":            year,
        "months":          months,
        "elapsed_months":  elapsed_months,
        "today":           today.strftime("%Y-%m"),
        "groups":          group_list,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _year_months(start: date, end: date) -> list[str]:
    months = []
    d = date(start.year, start.month, 1)
    while d <= end:
        months.append(d.strftime("%Y-%m"))
        m = d.month + 1
        y = d.year + (1 if m > 12 else 0)
        d = date(y, m % 12 or 12, 1)
    return months


def _elapsed_months(months: list[str], today: date) -> int:
    current = today.strftime("%Y-%m")
    count = sum(1 for m in months if m <= current)
    return max(1, count)


def _status(variance: float, ytd_budget: float, is_income: bool) -> str:
    """green / yellow / red based on variance vs budget."""
    if ytd_budget == 0:
        return "neutral"
    pct = variance / ytd_budget * 100
    if pct >= 0:
        return "green"
    if pct >= -20:
        return "yellow"
    return "red"
