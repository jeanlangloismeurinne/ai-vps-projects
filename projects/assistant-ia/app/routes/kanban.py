import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from app.routes.auth import require_auth
from app.services import kanban as kanban_svc
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_auth)])

_PUBLIC = Path(__file__).parent.parent.parent / "public" / "kanban"


# ─── Models ──────────────────────────────────────────────────────────────────

class BoardCreate(BaseModel):
    name: str
    is_default: bool = False

class ColumnCreate(BaseModel):
    name: str
    position: int = 0

class CardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class CardMove(BaseModel):
    column_id: str
    position: int

class GroupingCreate(BaseModel):
    name: str
    group_by: str


# ─── Web interface ────────────────────────────────────────────────────────────

@router.get("/kanban", response_class=HTMLResponse)
async def kanban_page():
    return FileResponse(_PUBLIC / "index.html")


# ─── Boards ──────────────────────────────────────────────────────────────────

@router.get("/api/boards")
async def get_boards():
    boards = await kanban_svc.list_boards()
    return [dict(b) for b in boards]


@router.post("/api/boards", status_code=201)
async def post_board(body: BoardCreate):
    board = await kanban_svc.create_board(body.name, body.is_default)
    return dict(board)


# ─── Columns ─────────────────────────────────────────────────────────────────

@router.get("/api/boards/{board_id}/columns")
async def get_columns(board_id: str):
    cols = await kanban_svc.list_columns(board_id)
    return [dict(c) for c in cols]


@router.post("/api/boards/{board_id}/columns", status_code=201)
async def post_column(board_id: str, body: ColumnCreate):
    col = await kanban_svc.create_column(board_id, body.name, body.position)
    return dict(col)


# ─── Cards ───────────────────────────────────────────────────────────────────

@router.get("/api/columns/{column_id}/cards")
async def get_cards(column_id: str):
    cards = await kanban_svc.list_cards(column_id)
    return [dict(c) for c in cards]


@router.post("/api/columns/{column_id}/cards", status_code=201)
async def post_card(column_id: str, body: CardCreate):
    card = await kanban_svc.create_card(column_id, body.title, body.description, body.due_date)
    return dict(card)


@router.get("/api/cards/{card_id}")
async def get_card(card_id: str):
    card = await kanban_svc.get_card(card_id)
    if not card:
        raise HTTPException(404)
    return dict(card)


@router.put("/api/cards/{card_id}")
async def put_card(card_id: str, body: CardUpdate):
    card = await kanban_svc.update_card(card_id, **body.model_dump(exclude_none=True))
    if not card:
        raise HTTPException(404)
    return dict(card)


@router.put("/api/cards/{card_id}/move")
async def move_card(card_id: str, body: CardMove):
    card = await kanban_svc.move_card(card_id, body.column_id, body.position)
    if not card:
        raise HTTPException(404)
    return dict(card)


@router.delete("/api/cards/{card_id}", status_code=204)
async def delete_card(card_id: str):
    deleted = await kanban_svc.delete_card(card_id)
    if not deleted:
        raise HTTPException(404)


# ─── Groupings ───────────────────────────────────────────────────────────────

@router.get("/api/boards/{board_id}/groupings")
async def get_groupings(board_id: str):
    gs = await kanban_svc.list_groupings(board_id)
    return [dict(g) for g in gs]


@router.post("/api/boards/{board_id}/groupings", status_code=201)
async def post_grouping(board_id: str, body: GroupingCreate):
    g = await kanban_svc.create_grouping(board_id, body.name, body.group_by)
    return dict(g)


@router.put("/api/groupings/{grouping_id}/activate")
async def activate_grouping(grouping_id: str):
    from app.db import get_pool
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT board_id FROM grouping_configs WHERE id = $1", grouping_id
    )
    if not row:
        raise HTTPException(404)
    result = await kanban_svc.activate_grouping(grouping_id, str(row["board_id"]))
    return dict(result)
