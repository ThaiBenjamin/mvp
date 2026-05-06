"""OpenRouter client, response parser, and the AI-driven board-update validator."""
from __future__ import annotations

import json
import logging

import httpx
from fastapi import HTTPException

from . import config
from .boards import apply_board_action

logger = logging.getLogger("pm.ai")


SYSTEM_PROMPT = """You are a project management assistant embedded in a Kanban app.

The user has a Kanban board with editable columns and freely titled cards. You may chat and may optionally modify the board.

You ALWAYS respond with a single JSON object on its own (no surrounding prose, no markdown fences) shaped like:
{"message": string, "boardUpdate": null | {"actions": [...]}}

`boardUpdate.actions` is an array applied in order. Each action is one of:
- {"type": "rename_column", "column_id": "<id>", "title": "<new title>"}
- {"type": "add_card", "column_id": "<id>", "title": "<title>", "details": "<details>", "priority": "low|medium|high", "dueDate": "YYYY-MM-DD"}
- {"type": "update_card", "card_id": "<id>", "title": "<new title>", "details": "<new details>", "priority": "low|medium|high", "dueDate": "YYYY-MM-DD"}
- {"type": "delete_card", "card_id": "<id>"}
- {"type": "move_card", "card_id": "<id>", "target_column_id": "<id>", "target_index": <int>}
- {"type": "add_column", "title": "<title>"}
- {"type": "delete_column", "column_id": "<id>"}

Rules:
- Use existing column ids and card ids from the supplied board state. Do not invent ids.
- For new cards or columns, omit the id; the server will assign one.
- Only delete a column when it is empty.
- Set boardUpdate to null when the user is just asking a question with no requested change.
- Keep `message` short, friendly, and explain what you changed (if anything).
- Output MUST be valid JSON. No code fences."""


async def call_openrouter(messages: list[dict]) -> str:
    if not config.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not configured")
        raise HTTPException(status_code=503, detail="AI service unavailable")

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(config.OPENROUTER_URL, headers=headers, json=body)
    except httpx.HTTPError as exc:
        logger.exception("OpenRouter request failed: %s", exc)
        raise HTTPException(status_code=503, detail="AI service unavailable")

    if response.status_code >= 400:
        logger.error("OpenRouter returned %s: %s", response.status_code, response.text[:500])
        raise HTTPException(status_code=502, detail="AI service returned an error")

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.exception("Could not parse OpenRouter response: %s", exc)
        raise HTTPException(status_code=502, detail="AI service returned an error")


def parse_ai_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("AI returned non-JSON response: %s", exc)
        raise HTTPException(status_code=502, detail="AI service returned an invalid response")

    if not isinstance(parsed, dict) or not isinstance(parsed.get("message"), str):
        logger.warning("AI response missing 'message': %r", parsed)
        raise HTTPException(status_code=502, detail="AI service returned an invalid response")

    parsed.setdefault("boardUpdate", None)
    return parsed


def _is_str(value, allow_empty: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    return allow_empty or bool(value.strip())


def apply_ai_board_update(board: dict, board_update: dict | None) -> tuple[dict, bool]:
    """Validate and apply an AI-suggested board update. Drops invalid actions."""
    if not isinstance(board_update, dict):
        return board, False
    actions = board_update.get("actions")
    if not isinstance(actions, list) or not actions:
        return board, False

    changed = False

    for action in actions:
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        valid_column_ids = {c["id"] for c in board["columns"]}
        try:
            if action_type == "rename_column":
                column_id = action.get("column_id")
                title = action.get("title")
                if column_id in valid_column_ids and _is_str(title):
                    board = apply_board_action(board, "rename_column", {
                        "column_id": column_id,
                        "title": title.strip(),
                    })
                    changed = True
            elif action_type == "add_card":
                column_id = action.get("column_id")
                title = action.get("title")
                details = action.get("details", "No details yet.")
                if column_id in valid_column_ids and _is_str(title):
                    payload = {
                        "column_id": column_id,
                        "title": title.strip(),
                        "details": details if isinstance(details, str) else "No details yet.",
                    }
                    if "priority" in action:
                        payload["priority"] = action.get("priority")
                    if "dueDate" in action:
                        payload["dueDate"] = action.get("dueDate")
                    board = apply_board_action(board, "add_card", payload)
                    changed = True
            elif action_type == "update_card":
                card_id = action.get("card_id")
                if isinstance(card_id, str) and card_id in board["cards"]:
                    payload: dict = {"card_id": card_id}
                    if "title" in action and _is_str(action["title"]):
                        payload["title"] = action["title"].strip()
                    if "details" in action and isinstance(action["details"], str):
                        payload["details"] = action["details"]
                    if "priority" in action:
                        payload["priority"] = action["priority"]
                    if "dueDate" in action:
                        payload["dueDate"] = action["dueDate"]
                    if len(payload) > 1:
                        board = apply_board_action(board, "update_card", payload)
                        changed = True
            elif action_type == "delete_card":
                card_id = action.get("card_id")
                if isinstance(card_id, str) and card_id in board["cards"]:
                    board = apply_board_action(board, "delete_card", {"card_id": card_id})
                    changed = True
            elif action_type == "move_card":
                card_id = action.get("card_id")
                target_column_id = action.get("target_column_id")
                target_index = action.get("target_index")
                if (
                    isinstance(card_id, str)
                    and card_id in board["cards"]
                    and target_column_id in valid_column_ids
                ):
                    board = apply_board_action(board, "move_card", {
                        "card_id": card_id,
                        "target_column_id": target_column_id,
                        "target_index": target_index if isinstance(target_index, int) else None,
                    })
                    changed = True
            elif action_type == "add_column":
                title = action.get("title")
                if _is_str(title):
                    board = apply_board_action(board, "add_column", {"title": title.strip()})
                    changed = True
            elif action_type == "delete_column":
                column_id = action.get("column_id")
                if column_id in valid_column_ids:
                    board = apply_board_action(board, "delete_column", {"column_id": column_id})
                    changed = True
        except HTTPException as exc:
            logger.warning("AI action %r rejected: %s", action_type, exc.detail)
            continue

    return board, changed
