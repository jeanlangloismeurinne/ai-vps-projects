import asyncpg
import json
from datetime import datetime
from app.db import get_pool


# ─── Boards ──────────────────────────────────────────────────────────────────

async def list_boards() -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch("SELECT * FROM boards ORDER BY is_default DESC, name")


async def create_board(name: str, is_default: bool = False) -> asyncpg.Record:
    pool = await get_pool()
    if is_default:
        await pool.execute("UPDATE boards SET is_default = false")
    return await pool.fetchrow(
        "INSERT INTO boards (name, is_default) VALUES ($1, $2) RETURNING *",
        name, is_default,
    )


async def get_default_board() -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM boards WHERE is_default = true LIMIT 1")


# ─── Columns ─────────────────────────────────────────────────────────────────

async def list_columns(board_id: str) -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM columns WHERE board_id = $1 ORDER BY position, name",
        board_id,
    )


async def create_column(board_id: str, name: str, position: int = 0) -> asyncpg.Record:
    pool = await get_pool()
    return await pool.fetchrow(
        "INSERT INTO columns (board_id, name, position) VALUES ($1, $2, $3) RETURNING *",
        board_id, name, position,
    )


async def get_column(column_id: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM columns WHERE id = $1", column_id)


async def get_column_by_name(board_id: str, name: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM columns WHERE board_id = $1 AND lower(name) = lower($2)",
        board_id, name,
    )


# ─── Cards ───────────────────────────────────────────────────────────────────

async def list_cards(column_id: str) -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM cards WHERE column_id = $1 ORDER BY position, created_at",
        column_id,
    )


async def list_cards_due_between(start: datetime, end: datetime) -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT c.*, col.name AS column_name FROM cards c "
        "JOIN columns col ON col.id = c.column_id "
        "WHERE c.due_date >= $1 AND c.due_date < $2 ORDER BY c.due_date",
        start, end,
    )


async def create_card(
    column_id: str,
    title: str,
    description: str | None = None,
    due_date: datetime | None = None,
) -> asyncpg.Record:
    pool = await get_pool()
    pos = await pool.fetchval(
        "SELECT COALESCE(MAX(position), -1) + 1 FROM cards WHERE column_id = $1", column_id
    )
    return await pool.fetchrow(
        "INSERT INTO cards (column_id, title, description, due_date, position) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING *",
        column_id, title, description, due_date, pos,
    )


async def get_card(card_id: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow("SELECT * FROM cards WHERE id = $1", card_id)


async def update_card(card_id: str, **fields) -> asyncpg.Record | None:
    if not fields:
        return await get_card(card_id)
    allowed = {"title", "description", "due_date", "column_id", "position"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
    values = list(fields.values())
    pool = await get_pool()
    return await pool.fetchrow(
        f"UPDATE cards SET {set_clause} WHERE id = $1 RETURNING *",
        card_id, *values,
    )


async def move_card(card_id: str, target_column_id: str, target_position: int) -> asyncpg.Record | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            card = await conn.fetchrow("SELECT * FROM cards WHERE id = $1", card_id)
            if not card:
                return None
            # Shift cards in origin column
            await conn.execute(
                "UPDATE cards SET position = position - 1 "
                "WHERE column_id = $1 AND position > $2",
                card["column_id"], card["position"],
            )
            # Make room in target column
            await conn.execute(
                "UPDATE cards SET position = position + 1 "
                "WHERE column_id = $1 AND position >= $2",
                target_column_id, target_position,
            )
            return await conn.fetchrow(
                "UPDATE cards SET column_id = $1, position = $2, updated_at = now() "
                "WHERE id = $3 RETURNING *",
                target_column_id, target_position, card_id,
            )


async def delete_card(card_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM cards WHERE id = $1", card_id)
    return result == "DELETE 1"


async def mark_reminder_sent(card_id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE cards SET reminder_sent_at = now() WHERE id = $1", card_id
    )


async def get_cards_due_now() -> list[asyncpg.Record]:
    """Cartes dont due_date est dans la minute courante et reminder_sent_at IS NULL."""
    pool = await get_pool()
    return await pool.fetch(
        "SELECT c.*, col.name AS column_name, b.name AS board_name "
        "FROM cards c "
        "JOIN columns col ON col.id = c.column_id "
        "JOIN boards b ON b.id = col.board_id "
        "WHERE c.due_date >= date_trunc('minute', now()) "
        "  AND c.due_date < date_trunc('minute', now()) + interval '1 minute' "
        "  AND c.reminder_sent_at IS NULL"
    )


# ─── Grouping configs ─────────────────────────────────────────────────────────

async def list_groupings(board_id: str) -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT * FROM grouping_configs WHERE board_id = $1 ORDER BY name",
        board_id,
    )


async def create_grouping(board_id: str, name: str, group_by: str) -> asyncpg.Record:
    pool = await get_pool()
    return await pool.fetchrow(
        "INSERT INTO grouping_configs (board_id, name, group_by) VALUES ($1, $2, $3) RETURNING *",
        board_id, name, group_by,
    )


async def activate_grouping(grouping_id: str, board_id: str) -> asyncpg.Record | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE grouping_configs SET is_active = false WHERE board_id = $1", board_id
            )
            return await conn.fetchrow(
                "UPDATE grouping_configs SET is_active = true WHERE id = $1 RETURNING *",
                grouping_id,
            )


async def get_active_grouping(board_id: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM grouping_configs WHERE board_id = $1 AND is_active = true",
        board_id,
    )


async def get_grouping_by_name(board_id: str, name: str) -> asyncpg.Record | None:
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM grouping_configs WHERE board_id = $1 AND lower(name) = lower($2)",
        board_id, name,
    )
