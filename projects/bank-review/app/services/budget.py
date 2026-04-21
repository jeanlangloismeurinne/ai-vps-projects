"""
Budget aggregation service.
Computes monthly actuals from transactions and compares to budget lines.
"""
from datetime import date, timedelta
from collections import defaultdict
from app.services.database import get_pool


# ── DB helpers ────────────────────────────────────────────────────────────────

async def get_budget_years() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, year_label, start_date, end_date, needs_budget_update FROM budget_years ORDER BY start_date DESC"
    )
    return [dict(r) for r in rows]


async def create_next_budget_year() -> dict | None:
    """
    If the most recent budget_year has no successor, create one covering the next
    calendar year (Jan 1 – Dec 31), copying all budget_lines from the current year
    and flagging the new year as needing a budget review.
    Returns the new year dict, or None if it already exists.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        latest = await conn.fetchrow(
            "SELECT id, year_label, start_date, end_date FROM budget_years ORDER BY end_date DESC LIMIT 1"
        )
        if not latest:
            return None

        # Fiscal year: next day after end_date, same duration as current year
        prev_start = latest["start_date"]
        prev_end   = latest["end_date"]
        duration_days = (prev_end - prev_start).days  # preserve exact duration
        next_start = prev_end + timedelta(days=1)
        next_end   = next_start + timedelta(days=duration_days)
        year_label = f"{next_start.year}-{next_end.year}" if next_start.year != next_end.year else str(next_start.year)

        existing = await conn.fetchval(
            "SELECT id FROM budget_years WHERE start_date = $1", next_start
        )
        if existing:
            return None

        async with conn.transaction():
            new_id = await conn.fetchval(
                """
                INSERT INTO budget_years (year_label, start_date, end_date, needs_budget_update)
                VALUES ($1, $2, $3, TRUE)
                RETURNING id
                """,
                year_label, next_start, next_end,
            )
            await conn.execute(
                """
                INSERT INTO budget_lines (year_id, category, monthly_budget, group_name, sort_order, is_income)
                SELECT $1, category, monthly_budget, group_name, sort_order, is_income
                FROM budget_lines
                WHERE year_id = $2
                ON CONFLICT (year_id, category) DO NOTHING
                """,
                new_id, latest["id"],
            )

        return {"id": new_id, "year_label": year_label, "start_date": str(next_start), "end_date": str(next_end)}


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


async def get_monthly_actuals(
    year_id: int,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, int]]]:
    """
    Returns (actuals, tx_counts).
    actuals: {category: {YYYY-MM: signed_amount}}
    tx_counts: {category: {YYYY-MM: transaction_count}}
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT
            t.category,
            TO_CHAR(t.date_op, 'YYYY-MM') AS month,
            SUM(t.amount)                 AS total,
            COUNT(*)                      AS tx_count
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
    counts: dict[str, dict[str, int]] = defaultdict(dict)
    for r in rows:
        result[r["category"]][r["month"]] = float(r["total"])
        counts[r["category"]][r["month"]] = int(r["tx_count"])
    return dict(result), dict(counts)


# ── Budget view builder ───────────────────────────────────────────────────────

def build_budget_view(
    year: dict,
    lines: list[dict],
    actuals: dict[str, dict[str, float]],
    tx_counts: dict[str, dict[str, int]] | None = None,
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

        cat_counts = (tx_counts or {}).get(cat, {})
        monthly = []
        for m in months:
            actual = cat_actuals.get(m, 0.0)
            # actual is signed: negative = expense, positive = income/refund
            # variance > 0 means "good" in both cases
            variance = budget + actual if not line["is_income"] else actual - budget
            monthly.append({
                "month": m,
                "actual": actual,
                "budget": budget,
                "variance": round(variance, 2),
                "is_current": m == today.strftime("%Y-%m"),
                "is_future": m > today.strftime("%Y-%m"),
                "has_tx": cat_counts.get(m, 0) > 0,
            })

        ytd_actual = sum(cat_actuals.get(m, 0.0) for m in months[:elapsed_months])
        ytd_budget = budget * elapsed_months
        ytd_variance = (ytd_budget + ytd_actual) if not line["is_income"] else (ytd_actual - ytd_budget)
        avg_actual = (ytd_actual / elapsed_months) if elapsed_months else 0.0

        progress = round(100 * abs(ytd_actual) / ytd_budget) if ytd_budget else 0

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
            "ytd_variance":  round(g_ytd_budget + g_ytd_actual, 2),
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


# ── Transaction drill-down ────────────────────────────────────────────────────

async def get_transactions_by_cell(category: str, month: str) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, date_op, real_date, label, label_clean, amount,
               bank_category, category, confidence, classification_method, precision_note
        FROM transactions
        WHERE category = $1 AND TO_CHAR(date_op, 'YYYY-MM') = $2
        ORDER BY date_op DESC
        """,
        category, month,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["date_op"] = str(d["date_op"])
        d["real_date"] = str(d["real_date"]) if d["real_date"] else None
        d["amount"] = float(d["amount"])
        result.append(d)
    return result


async def recategorize_transaction(tx_id: int, new_category: str):
    pool = await get_pool()
    await pool.execute(
        "UPDATE transactions SET category = $1 WHERE id = $2",
        new_category, tx_id,
    )


# ── Category management ───────────────────────────────────────────────────────

async def get_all_categories_for_year(year_id: int) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, category, monthly_budget, group_name, sort_order, is_income
        FROM budget_lines
        WHERE year_id = $1
        ORDER BY sort_order, group_name, category
        """,
        year_id,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["monthly_budget"] = float(d["monthly_budget"])
        result.append(d)
    return result


async def add_budget_category(
    year_id: int, category: str, group_name: str,
    monthly_budget: float, is_income: bool, sort_order: int,
) -> int | None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO categories (name) VALUES ($1) ON CONFLICT DO NOTHING",
        category,
    )
    row = await pool.fetchrow(
        """
        INSERT INTO budget_lines (year_id, category, monthly_budget, group_name, sort_order, is_income)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (year_id, category) DO NOTHING
        RETURNING id
        """,
        year_id, category, monthly_budget, group_name, sort_order, is_income,
    )
    return row["id"] if row else None


async def update_budget_category(
    line_id: int, group_name: str, monthly_budget: float,
    is_income: bool, sort_order: int,
):
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE budget_lines
        SET group_name = $1, monthly_budget = $2, is_income = $3, sort_order = $4
        WHERE id = $5
        """,
        group_name, monthly_budget, is_income, sort_order, line_id,
    )


async def rename_budget_category(line_id: int, new_name: str):
    """
    Rename a category for a specific year only.
    - Only this year's budget_line is renamed.
    - Only transactions within this year's date range are updated.
    - Other years and their transactions are untouched.
    - The old name is kept in the categories table (other years may still use it).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT bl.category, by_.start_date, by_.end_date
            FROM budget_lines bl
            JOIN budget_years by_ ON bl.year_id = by_.id
            WHERE bl.id = $1
            """,
            line_id,
        )
        if not row or row["category"] == new_name:
            return
        old_name = row["category"]
        start_date = row["start_date"]
        end_date = row["end_date"]
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO categories (name) VALUES ($1) ON CONFLICT DO NOTHING", new_name
            )
            # Only rename this specific budget line
            await conn.execute(
                "UPDATE budget_lines SET category = $1 WHERE id = $2", new_name, line_id
            )
            # Only rename transactions within this year's date range
            await conn.execute(
                "UPDATE transactions SET category = $1 WHERE category = $2 AND date_op BETWEEN $3 AND $4",
                new_name, old_name, start_date, end_date,
            )


async def get_uncovered_count(year_id: int) -> int:
    """Count transactions in this year whose category has no matching budget_line."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT COUNT(*) AS cnt
        FROM transactions t
        JOIN budget_years y ON t.date_op BETWEEN y.start_date AND y.end_date
        WHERE y.id = $1
          AND t.category IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM budget_lines bl WHERE bl.year_id = y.id AND bl.category = t.category
          )
        """,
        year_id,
    )
    return int(row["cnt"]) if row else 0


async def delete_budget_category(line_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM budget_lines WHERE id = $1", line_id)


async def dismiss_budget_update_flag(year_id: int):
    pool = await get_pool()
    await pool.execute(
        "UPDATE budget_years SET needs_budget_update = FALSE WHERE id = $1",
        year_id,
    )


async def get_month_transactions(year_id: int, month: str) -> list[dict]:
    """All transactions for a given YYYY-MM within the year's date range."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT t.id, t.date_op, t.real_date, t.label, t.label_clean, t.amount,
               t.bank_category, t.category, t.confidence, t.classification_method, t.precision_note
        FROM transactions t
        JOIN budget_years y ON t.date_op BETWEEN y.start_date AND y.end_date
        WHERE y.id = $1 AND TO_CHAR(t.date_op, 'YYYY-MM') = $2
        ORDER BY t.date_op, t.category
        """,
        year_id, month,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["date_op"] = str(d["date_op"])
        d["real_date"] = str(d["real_date"]) if d["real_date"] else None
        d["amount"] = float(d["amount"])
        result.append(d)
    return result


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
