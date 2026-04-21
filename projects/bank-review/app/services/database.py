"""
PostgreSQL access layer via asyncpg.
Connection string from env: DATABASE_URL
Default for local dev: postgresql://bank:bank_secure_pwd@localhost:5432/db_bank
In Docker (Coolify): postgresql://bank:bank_secure_pwd@shared-postgres:5432/db_bank
"""
import asyncpg
import os
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


def _dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://bank:bank_secure_pwd@localhost:5432/db_bank",
    )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=5)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ── Deduplication ─────────────────────────────────────────────────────────────

async def get_existing_dedup_keys() -> set[str]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT dedup_key FROM transactions")
    return {r["dedup_key"] for r in rows}


# ── Accounts ──────────────────────────────────────────────────────────────────

async def upsert_account(account_num: str, account_label: str):
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO accounts (account_num, account_label)
        VALUES ($1, $2)
        ON CONFLICT (account_num) DO UPDATE SET account_label = EXCLUDED.account_label
        """,
        account_num, account_label,
    )


# ── Transactions ──────────────────────────────────────────────────────────────

async def insert_transactions(rows: list[dict]) -> int:
    """Bulk insert, skipping duplicates. Returns number of rows actually inserted."""
    if not rows:
        return 0
    pool = await get_pool()

    inserted = 0
    async with pool.acquire() as conn:
        for row in rows:
            try:
                await conn.execute(
                    """
                    INSERT INTO transactions (
                        date_op, date_val, real_date,
                        label, label_clean, amount, currency,
                        account_num, account_balance,
                        bank_category, bank_category_parent, supplier, comment,
                        category, confidence, classification_method,
                        precision_note, source, dedup_key
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                        $14,$15,$16,$17,$18,$19
                    )
                    ON CONFLICT (dedup_key) DO NOTHING
                    """,
                    row["date_op"], row.get("date_val"), row.get("real_date"),
                    row["label"], row.get("label_clean"), row["amount"], row.get("currency", "EUR"),
                    row.get("account_num"), row.get("account_balance"),
                    row.get("bank_category"), row.get("bank_category_parent"),
                    row.get("supplier"), row.get("comment"),
                    row.get("category"), row.get("confidence"),
                    row.get("classification_method"),
                    row.get("precision_note"), row.get("source", "export"),
                    row["dedup_key"],
                )
                inserted += 1
            except asyncpg.ForeignKeyViolationError:
                # Category not in table yet — insert as non catégorisé
                row["category"] = "Non catégorisé"
                await conn.execute(
                    """
                    INSERT INTO transactions (
                        date_op, date_val, real_date,
                        label, label_clean, amount, currency,
                        account_num, account_balance,
                        bank_category, bank_category_parent, supplier, comment,
                        category, confidence, classification_method,
                        precision_note, source, dedup_key
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                        $14,$15,$16,$17,$18,$19
                    )
                    ON CONFLICT (dedup_key) DO NOTHING
                    """,
                    row["date_op"], row.get("date_val"), row.get("real_date"),
                    row["label"], row.get("label_clean"), row["amount"], row.get("currency", "EUR"),
                    row.get("account_num"), row.get("account_balance"),
                    row.get("bank_category"), row.get("bank_category_parent"),
                    row.get("supplier"), row.get("comment"),
                    "Non catégorisé", row.get("confidence"),
                    row.get("classification_method"),
                    row.get("precision_note"), row.get("source", "export"),
                    row["dedup_key"],
                )
                inserted += 1
    return inserted


# ── Classification rules ──────────────────────────────────────────────────────

async def get_classification_rules() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, keyword, category, created_at FROM classification_rules ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


async def create_classification_rule(keyword: str, category: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO classification_rules (keyword, category) VALUES ($1, $2) RETURNING id",
        keyword.strip(), category.strip(),
    )
    return row["id"]


async def delete_classification_rule(rule_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM classification_rules WHERE id = $1", rule_id)


async def check_rule_conflict(keyword: str, category: str) -> dict | None:
    """Return the first rule whose keyword matches and points to a different category."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, keyword, category FROM classification_rules WHERE lower(keyword) = lower($1) AND lower(category) != lower($2) LIMIT 1",
        keyword.strip(), category.strip(),
    )
    return dict(row) if row else None


# ── Import sessions ───────────────────────────────────────────────────────────

async def create_import_session(
    filename: str | None,
    row_count: int,
    date_min,
    date_max,
    year_id: int | None,
) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO import_sessions (filename, row_count, date_min, date_max, year_id)
        VALUES ($1, $2, $3, $4, $5) RETURNING id
        """,
        filename, row_count, date_min, date_max, year_id,
    )
    return row["id"]


async def get_import_sessions(limit: int = 20) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, created_at, filename, row_count, date_min, date_max, year_id
        FROM import_sessions
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["created_at"] = d["created_at"].isoformat() if d["created_at"] else None
        d["date_min"] = str(d["date_min"]) if d["date_min"] else None
        d["date_max"] = str(d["date_max"]) if d["date_max"] else None
        result.append(d)
    return result


async def link_transactions_to_session(dedup_keys: list[str], session_id: int):
    if not dedup_keys:
        return
    pool = await get_pool()
    await pool.execute(
        "UPDATE transactions SET import_session_id = $1 WHERE dedup_key = ANY($2) AND import_session_id IS NULL",
        session_id, dedup_keys,
    )


async def get_session_with_transactions(session_id: int) -> tuple[dict | None, list[dict]]:
    pool = await get_pool()
    session = await pool.fetchrow(
        "SELECT id, created_at, filename, row_count, date_min, date_max, year_id FROM import_sessions WHERE id = $1",
        session_id,
    )
    if not session:
        return None, []
    session_dict = dict(session)
    session_dict["created_at"] = session_dict["created_at"].isoformat() if session_dict["created_at"] else None
    session_dict["date_min"] = str(session_dict["date_min"]) if session_dict["date_min"] else None
    session_dict["date_max"] = str(session_dict["date_max"]) if session_dict["date_max"] else None

    rows = await pool.fetch(
        """
        SELECT id, date_op, real_date, label, label_clean, amount,
               bank_category, category, confidence, classification_method, precision_note
        FROM transactions
        WHERE import_session_id = $1
        ORDER BY date_op DESC, id DESC
        """,
        session_id,
    )
    txs = []
    for r in rows:
        d = dict(r)
        d["date_op"] = str(d["date_op"])
        d["real_date"] = str(d["real_date"]) if d["real_date"] else None
        d["amount"] = float(d["amount"])
        txs.append(d)
    return session_dict, txs


# ── History for classifier ────────────────────────────────────────────────────

async def get_classified_history(limit: int = 500) -> list[dict]:
    """Return recent classified transactions for building the history index."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT label_clean, label, category
        FROM transactions
        WHERE category IS NOT NULL
          AND source IN ('historical', 'export')
        ORDER BY date_op DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]
