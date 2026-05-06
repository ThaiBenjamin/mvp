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


# ------------------------------------------------------------ persistence

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
        }
        for card_id, card in cards.items()
        if isinstance(card_id, str) and isinstance(card, dict)
    }

    if not repaired_columns:
        return DEFAULT_BOARD_STATE

    return {"columns": repaired_columns, "cards": repaired_cards}


def load_board_state(user_id: int) -> dict:
    with get_connection() as conn:
        cursor = conn.execute("SELECT state FROM boards WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    if row is None:
        save_board_state(DEFAULT_BOARD_STATE, user_id=user_id)
        return DEFAULT_BOARD_STATE

    try:
        board_state = json.loads(row[0])
    except json.JSONDecodeError:
        board_state = DEFAULT_BOARD_STATE

    repaired = repair_board_state(board_state)
    if repaired != board_state:
        save_board_state(repaired, user_id=user_id)
    return repaired


def save_board_state(state: dict, user_id: int) -> None:
    state_text = json.dumps(state)
    updated_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute("SELECT version FROM boards WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        version = row[0] + 1 if row else 1
        conn.execute(
            """
            INSERT INTO boards (user_id, state, version, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              state = excluded.state,
              version = excluded.version,
              updated_at = excluded.updated_at
            """,
            (user_id, state_text, version, updated_at),
        )
        conn.commit()


# ----------------------------------------------------------------- actions

def _new_card_id() -> str:
    return f"card-{secrets.token_hex(8)}"


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
        new_cards = {**cards, card_id: {"id": card_id, "title": title, "details": details}}
        new_columns = [
            {**c, "cardIds": [*c["cardIds"], card_id]} if c["id"] == column_id else c
            for c in columns
        ]
        return {"columns": new_columns, "cards": new_cards}

    if action == "delete_card":
        card_id = payload["card_id"]
        new_cards = {k: v for k, v in cards.items() if k != card_id}
        new_columns = [
            {**c, "cardIds": [cid for cid in c["cardIds"] if cid != card_id]}
            for c in columns
        ]
        return {"columns": new_columns, "cards": new_cards}

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


class DeleteCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: str


class MoveCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: str
    target_column_id: str
    target_index: int | None = None


class BoardActionRequest(BaseModel):
    action: Literal["rename_column", "add_card", "delete_card", "move_card"]
    payload: dict


# -------------------------------------------------------------- HTTP API

router = APIRouter(prefix="/api", tags=["board"])


@router.get("/board")
async def get_board(user_id: Annotated[int, Depends(require_user)]):
    return load_board_state(user_id=user_id)


@router.post("/board")
async def replace_board(state: dict, user_id: Annotated[int, Depends(require_user)]):
    repaired = repair_board_state(state)
    save_board_state(repaired, user_id=user_id)
    return repaired


@router.post("/board/actions")
async def post_board_action(
    req: BoardActionRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    try:
        if req.action == "rename_column":
            payload = RenameColumnPayload.model_validate(req.payload).model_dump()
        elif req.action == "add_card":
            payload = AddCardPayload.model_validate(req.payload).model_dump(exclude_none=True)
        elif req.action == "delete_card":
            payload = DeleteCardPayload.model_validate(req.payload).model_dump()
        elif req.action == "move_card":
            payload = MoveCardPayload.model_validate(req.payload).model_dump()
        else:  # pragma: no cover -- exhausted by Literal
            raise HTTPException(status_code=400, detail="Unsupported action")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    board = load_board_state(user_id=user_id)
    updated = apply_board_action(board, req.action, payload)
    save_board_state(updated, user_id=user_id)
    return updated
