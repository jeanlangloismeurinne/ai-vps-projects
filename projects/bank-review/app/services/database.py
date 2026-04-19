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
