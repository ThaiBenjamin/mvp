"""Chat history persistence and the chat HTTP routes (incl. AI health check)."""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config
from .ai import (
    SYSTEM_PROMPT,
    apply_ai_board_update,
    call_openrouter,
    parse_ai_response,
)
from .auth import require_user
from .boards import (
    first_board_id,
    load_board_state,
    require_board,
    save_board_state,
)
from .db import get_connection


# ----------------------------------------------------------------- DB ops

def load_chat_history(user_id: int, board_id: int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT role, content FROM chat_messages
             WHERE user_id = ? AND board_id = ?
             ORDER BY id ASC
            """,
            (user_id, board_id),
        )
        return [{"role": role, "content": content} for role, content in cursor.fetchall()]


def append_chat_message(user_id: int, board_id: int, role: str, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, board_id, role, content) VALUES (?, ?, ?, ?)",
            (user_id, board_id, role, content),
        )
        conn.commit()


def clear_chat_history(user_id: int, board_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND board_id = ?",
            (user_id, board_id),
        )
        conn.commit()


# -------------------------------------------------------------- requests

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    board_id: int | None = None


# -------------------------------------------------------------- HTTP API

router = APIRouter(prefix="/api", tags=["chat"])


def _resolve_board_id(user_id: int, board_id: int | None) -> int:
    if board_id is None:
        return first_board_id(user_id)
    require_board(board_id, user_id)
    return board_id


@router.get("/chat/history")
async def chat_history(
    user_id: Annotated[int, Depends(require_user)],
    board_id: int | None = None,
):
    resolved = _resolve_board_id(user_id, board_id)
    return {"messages": load_chat_history(user_id, resolved)}


@router.post("/chat/reset")
async def chat_reset(
    user_id: Annotated[int, Depends(require_user)],
    board_id: int | None = None,
):
    resolved = _resolve_board_id(user_id, board_id)
    clear_chat_history(user_id, resolved)
    return {"messages": []}


@router.post("/chat")
async def chat(req: ChatRequest, user_id: Annotated[int, Depends(require_user)]):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    board_id = _resolve_board_id(user_id, req.board_id)
    board_state = load_board_state(board_id=board_id, user_id=user_id)
    history = load_chat_history(user_id, board_id)[-config.CHAT_HISTORY_LIMIT:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Current board state JSON:\n{json.dumps(board_state)}"},
        *history,
        {"role": "user", "content": user_message},
    ]

    raw = await call_openrouter(messages)
    parsed = parse_ai_response(raw)

    updated_board, changed = apply_ai_board_update(board_state, parsed.get("boardUpdate"))
    if changed:
        save_board_state(updated_board, board_id=board_id, user_id=user_id)

    append_chat_message(user_id, board_id, "user", user_message)
    append_chat_message(user_id, board_id, "assistant", parsed["message"])

    return {
        "message": parsed["message"],
        "boardUpdated": changed,
        "board": updated_board if changed else None,
        "boardId": board_id,
    }


@router.get("/ai/health")
async def ai_health():
    if not config.OPENROUTER_API_KEY:
        return JSONResponse(
            {"ok": False, "reason": "OPENROUTER_API_KEY is not configured"},
            status_code=503,
        )
    try:
        raw = await call_openrouter([
            {"role": "system", "content": "Reply with the exact JSON {\"message\": \"4\", \"boardUpdate\": null}"},
            {"role": "user", "content": "What is 2+2?"},
        ])
    except HTTPException as exc:
        return JSONResponse({"ok": False, "reason": exc.detail}, status_code=exc.status_code)
    return {"ok": True, "raw": raw}
