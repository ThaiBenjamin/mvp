"""Board state persistence, action application, and the board HTTP routes."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .auth import require_user
from .db import DEFAULT_BOARD_STATE, get_connection

VALID_PRIORITIES = {"low", "medium", "high"}


# ------------------------------------------------------------ persistence

def _normalize_priority(value) -> str:
    if isinstance(value, str) and value.lower() in VALID_PRIORITIES:
        return value.lower()
    return "medium"


def _normalize_due_date(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    # Accept either YYYY-MM-DD or full ISO-8601; just enforce parseability.
    try:
        # Python's fromisoformat is permissive enough for our needs.
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError:
        return None


def repair_board_state(board_state: dict) -> dict:
    """Structural repair only; never resurrects deleted defaults."""
    if not isinstance(board_state, dict):
        return DEFAULT_BOARD_STATE

    columns = board_state.get("columns")
    cards = board_state.get("cards")
    if not isinstance(columns, list) or not isinstance(cards, dict):
        return DEFAULT_BOARD_STATE

    repaired_columns: list[dict] = []
    seen_ids: set[str] = set()
    for column in columns:
        if not isinstance(column, dict):
            continue
        column_id = column.get("id")
        if not isinstance(column_id, str) or column_id in seen_ids:
            continue
        seen_ids.add(column_id)
        card_ids = column.get("cardIds")
        title = column.get("title")
        repaired_columns.append({
            "id": column_id,
            "title": title if isinstance(title, str) else column_id,
            "cardIds": [cid for cid in card_ids if isinstance(cid, str)] if isinstance(card_ids, list) else [],
        })

    repaired_cards = {
        card_id: {
            "id": card_id,
            "title": card.get("title", "") if isinstance(card.get("title"), str) else "",
            "details": card.get("details", "") if isinstance(card.get("details"), str) else "",
            "priority": _normalize_priority(card.get("priority")),
            "dueDate": _normalize_due_date(card.get("dueDate")),
        }
        for card_id, card in cards.items()
        if isinstance(card_id, str) and isinstance(card, dict)
    }

    if not repaired_columns:
        return DEFAULT_BOARD_STATE

    return {"columns": repaired_columns, "cards": repaired_cards}


# -------- multi-board persistence

def list_boards(user_id: int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, name, position, archived, version, updated_at
              FROM boards
             WHERE user_id = ?
             ORDER BY position ASC, id ASC
            """,
            (user_id,),
        )
        return [
            {
                "id": row[0],
                "name": row[1],
                "position": row[2],
                "archived": bool(row[3]),
                "version": row[4],
                "updatedAt": row[5],
            }
            for row in cursor.fetchall()
        ]


def get_board_record(board_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, name, position, archived, version, updated_at, state FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "position": row[2],
            "archived": bool(row[3]),
            "version": row[4],
            "updatedAt": row[5],
            "state_text": row[6],
        }


def require_board(board_id: int, user_id: int) -> dict:
    record = get_board_record(board_id, user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return record


def load_board_state(board_id: int, user_id: int) -> dict:
    record = require_board(board_id, user_id)
    try:
        board_state = json.loads(record["state_text"])
    except json.JSONDecodeError:
        board_state = DEFAULT_BOARD_STATE
    repaired = repair_board_state(board_state)
    if repaired != board_state:
        save_board_state(repaired, board_id=board_id, user_id=user_id)
    return repaired


def save_board_state(state: dict, board_id: int, user_id: int) -> None:
    state_text = json.dumps(state)
    updated_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute("SELECT version FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Board not found")
        version = row[0] + 1
        conn.execute(
            "UPDATE boards SET state = ?, version = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (state_text, version, updated_at, board_id, user_id),
        )
        conn.commit()


def create_board(user_id: int, name: str, state: dict | None = None) -> dict:
    if state is None:
        state = {"columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": []},
            {"id": "col-in-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ], "cards": {}}
    repaired = repair_board_state(state)
    state_text = json.dumps(repaired)
    with get_connection() as conn:
        cursor = conn.execute("SELECT COALESCE(MAX(position), -1) FROM boards WHERE user_id = ?", (user_id,))
        next_pos = cursor.fetchone()[0] + 1
        cursor = conn.execute(
            "INSERT INTO boards (user_id, name, state, position) VALUES (?, ?, ?, ?)",
            (user_id, name, state_text, next_pos),
        )
        board_id = cursor.lastrowid
        conn.commit()
    record = require_board(board_id, user_id)
    return {
        "id": record["id"],
        "name": record["name"],
        "position": record["position"],
        "archived": record["archived"],
        "version": record["version"],
        "updatedAt": record["updatedAt"],
    }


def rename_board(board_id: int, user_id: int, name: str) -> dict:
    require_board(board_id, user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE boards SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (name, datetime.now(timezone.utc).isoformat(), board_id, user_id),
        )
        conn.commit()
    record = require_board(board_id, user_id)
    return {
        "id": record["id"],
        "name": record["name"],
        "position": record["position"],
        "archived": record["archived"],
        "version": record["version"],
        "updatedAt": record["updatedAt"],
    }


def delete_board(board_id: int, user_id: int) -> None:
    require_board(board_id, user_id)
    with get_connection() as conn:
        # Refuse to delete the user's only board so they always have one.
        cursor = conn.execute("SELECT COUNT(*) FROM boards WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete your only board")
        conn.execute("DELETE FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
        conn.commit()


# ----------------------------------------------------------------- actions

def _new_card_id() -> str:
    return f"card-{secrets.token_hex(8)}"


def _new_column_id() -> str:
    return f"col-{secrets.token_hex(6)}"


def apply_board_action(board: dict, action: str, payload: dict) -> dict:
    """Pure: returns a new board, never mutates the input."""
    columns = board["columns"]
    cards = board["cards"]
    column_ids = {c["id"] for c in columns}

    if action == "rename_column":
        column_id = payload["column_id"]
        title = payload["title"]
        if column_id not in column_ids:
            raise HTTPException(status_code=400, detail="Unknown column")
        new_columns = [
            {**c, "title": title} if c["id"] == column_id else c
            for c in columns
        ]
        return {"columns": new_columns, "cards": cards}

    if action == "add_card":
        column_id = payload["column_id"]
        if column_id not in column_ids:
            raise HTTPException(status_code=400, detail="Unknown column")
        card_id = payload.get("card_id") or _new_card_id()
        title = payload["title"]
        details = payload.get("details", "No details yet.")
        priority = _normalize_priority(payload.get("priority"))
        due_date = _normalize_due_date(payload.get("dueDate"))
        new_cards = {
            **cards,
            card_id: {
                "id": card_id,
                "title": title,
                "details": details,
                "priority": priority,
                "dueDate": due_date,
            },
        }
        new_columns = [
            {**c, "cardIds": [*c["cardIds"], card_id]} if c["id"] == column_id else c
            for c in columns
        ]
        return {"columns": new_columns, "cards": new_cards}

    if action == "update_card":
        card_id = payload["card_id"]
        if card_id not in cards:
            raise HTTPException(status_code=400, detail="Unknown card")
        existing = cards[card_id]
        title = payload.get("title", existing.get("title"))
        details = payload.get("details", existing.get("details"))
        priority = (
            _normalize_priority(payload["priority"])
            if "priority" in payload else existing.get("priority", "medium")
        )
        due_date = (
            _normalize_due_date(payload["dueDate"])
            if "dueDate" in payload else existing.get("dueDate")
        )
        new_cards = {
            **cards,
            card_id: {
                **existing,
                "id": card_id,
                "title": title,
                "details": details,
                "priority": priority,
                "dueDate": due_date,
            },
        }
        return {"columns": columns, "cards": new_cards}

    if action == "delete_card":
        card_id = payload["card_id"]
        new_cards = {k: v for k, v in cards.items() if k != card_id}
        new_columns = [
            {**c, "cardIds": [cid for cid in c["cardIds"] if cid != card_id]}
            for c in columns
        ]
        return {"columns": new_columns, "cards": new_cards}

    if action == "add_column":
        title = payload["title"]
        column_id = payload.get("column_id") or _new_column_id()
        if column_id in column_ids:
            raise HTTPException(status_code=400, detail="Column id already exists")
        new_columns = [*columns, {"id": column_id, "title": title, "cardIds": []}]
        return {"columns": new_columns, "cards": cards}

    if action == "delete_column":
        column_id = payload["column_id"]
        if column_id not in column_ids:
            raise HTTPException(status_code=400, detail="Unknown column")
        if len(columns) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the only column")
        target = next(c for c in columns if c["id"] == column_id)
        if target["cardIds"]:
            raise HTTPException(status_code=400, detail="Column must be empty before deletion")
        new_columns = [c for c in columns if c["id"] != column_id]
        return {"columns": new_columns, "cards": cards}

    if action == "move_column":
        column_id = payload["column_id"]
        target_index = payload["target_index"]
        if column_id not in column_ids:
            raise HTTPException(status_code=400, detail="Unknown column")
        without = [c for c in columns if c["id"] != column_id]
        target = next(c for c in columns if c["id"] == column_id)
        if target_index < 0 or target_index > len(without):
            target_index = len(without)
        new_columns = [*without[:target_index], target, *without[target_index:]]
        return {"columns": new_columns, "cards": cards}

    if action == "move_card":
        card_id = payload["card_id"]
        target_column_id = payload["target_column_id"]
        target_index = payload.get("target_index")

        source_column = next((c for c in columns if card_id in c["cardIds"]), None)
        target_column = next((c for c in columns if c["id"] == target_column_id), None)
        if source_column is None or target_column is None:
            raise HTTPException(status_code=400, detail="Invalid column or card id")

        if source_column["id"] == target_column_id:
            reordered = [cid for cid in source_column["cardIds"] if cid != card_id]
            if target_index is None or target_index < 0 or target_index > len(reordered):
                reordered.append(card_id)
            else:
                reordered.insert(target_index, card_id)
            new_columns = [
                {**c, "cardIds": reordered} if c["id"] == source_column["id"] else c
                for c in columns
            ]
            return {"columns": new_columns, "cards": cards}

        new_source = [cid for cid in source_column["cardIds"] if cid != card_id]
        new_target = list(target_column["cardIds"])
        if target_index is None or target_index < 0 or target_index > len(new_target):
            new_target.append(card_id)
        else:
            new_target.insert(target_index, card_id)

        new_columns = []
        for c in columns:
            if c["id"] == source_column["id"]:
                new_columns.append({**c, "cardIds": new_source})
            elif c["id"] == target_column_id:
                new_columns.append({**c, "cardIds": new_target})
            else:
                new_columns.append(c)
        return {"columns": new_columns, "cards": cards}

    raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")


# ---------------------------------------------------------- request models

class RenameColumnPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    column_id: str
    title: str = Field(min_length=1, max_length=120)


class AddCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    column_id: str
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="No details yet.", max_length=2000)
    card_id: str | None = None
    priority: str | None = None
    dueDate: str | None = None


class UpdateCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: str
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=2000)
    priority: str | None = None
    dueDate: str | None = None


class DeleteCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: str


class MoveCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: str
    target_column_id: str
    target_index: int | None = None


class AddColumnPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=120)
    column_id: str | None = None


class DeleteColumnPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    column_id: str


class MoveColumnPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    column_id: str
    target_index: int


class BoardActionRequest(BaseModel):
    action: Literal[
        "rename_column",
        "add_card",
        "update_card",
        "delete_card",
        "move_card",
        "add_column",
        "delete_column",
        "move_column",
    ]
    payload: dict


class CreateBoardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RenameBoardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


# -------------------------------------------------------------- HTTP API

router = APIRouter(prefix="/api", tags=["board"])


@router.get("/boards")
async def get_boards(user_id: Annotated[int, Depends(require_user)]):
    return {"boards": list_boards(user_id)}


@router.post("/boards", status_code=201)
async def post_board(
    req: CreateBoardRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    return create_board(user_id, req.name.strip())


@router.patch("/boards/{board_id}")
async def patch_board(
    board_id: int,
    req: RenameBoardRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    return rename_board(board_id, user_id, req.name.strip())


@router.delete("/boards/{board_id}", status_code=204)
async def remove_board(
    board_id: int,
    user_id: Annotated[int, Depends(require_user)],
):
    delete_board(board_id, user_id)
    return None


@router.get("/boards/{board_id}")
async def get_board_state(
    board_id: int,
    user_id: Annotated[int, Depends(require_user)],
):
    state = load_board_state(board_id=board_id, user_id=user_id)
    record = require_board(board_id, user_id)
    return {
        "id": record["id"],
        "name": record["name"],
        "position": record["position"],
        "version": record["version"],
        "updatedAt": record["updatedAt"],
        **state,
    }


@router.post("/boards/{board_id}/state")
async def replace_board_state(
    board_id: int,
    state: dict,
    user_id: Annotated[int, Depends(require_user)],
):
    require_board(board_id, user_id)
    repaired = repair_board_state(state)
    save_board_state(repaired, board_id=board_id, user_id=user_id)
    return repaired


@router.post("/boards/{board_id}/actions")
async def post_board_action(
    board_id: int,
    req: BoardActionRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    payload = _validate_action_payload(req.action, req.payload)
    board = load_board_state(board_id=board_id, user_id=user_id)
    updated = apply_board_action(board, req.action, payload)
    save_board_state(updated, board_id=board_id, user_id=user_id)
    return updated


def _validate_action_payload(action: str, payload: dict) -> dict:
    try:
        if action == "rename_column":
            return RenameColumnPayload.model_validate(payload).model_dump()
        if action == "add_card":
            return AddCardPayload.model_validate(payload).model_dump(exclude_none=True)
        if action == "update_card":
            return UpdateCardPayload.model_validate(payload).model_dump(exclude_unset=True)
        if action == "delete_card":
            return DeleteCardPayload.model_validate(payload).model_dump()
        if action == "move_card":
            return MoveCardPayload.model_validate(payload).model_dump()
        if action == "add_column":
            return AddColumnPayload.model_validate(payload).model_dump(exclude_none=True)
        if action == "delete_column":
            return DeleteColumnPayload.model_validate(payload).model_dump()
        if action == "move_column":
            return MoveColumnPayload.model_validate(payload).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    raise HTTPException(status_code=400, detail="Unsupported action")


# -------- Legacy single-board compatibility (resolves to user's first board)

def first_board_id(user_id: int) -> int:
    boards = list_boards(user_id)
    if not boards:
        raise HTTPException(status_code=404, detail="No board exists for this user")
    return boards[0]["id"]


@router.get("/board")
async def get_board_legacy(user_id: Annotated[int, Depends(require_user)]):
    board_id = first_board_id(user_id)
    return load_board_state(board_id=board_id, user_id=user_id)


@router.post("/board")
async def replace_board_legacy(state: dict, user_id: Annotated[int, Depends(require_user)]):
    board_id = first_board_id(user_id)
    repaired = repair_board_state(state)
    save_board_state(repaired, board_id=board_id, user_id=user_id)
    return repaired


@router.post("/board/actions")
async def post_board_action_legacy(
    req: BoardActionRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    board_id = first_board_id(user_id)
    payload = _validate_action_payload(req.action, req.payload)
    board = load_board_state(board_id=board_id, user_id=user_id)
    updated = apply_board_action(board, req.action, payload)
    save_board_state(updated, board_id=board_id, user_id=user_id)
    return updated
