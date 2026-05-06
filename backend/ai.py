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

The user has one Kanban board with fixed columns and freely titled cards. You can chat with the user and you may optionally modify the board.

You ALWAYS respond with a single JSON object on its own (no surrounding prose, no markdown fences) shaped like:
{"message": string, "boardUpdate": null | {"actions": [...]}}

`boardUpdate.actions` is an array applied in order. Each action is one of:
- {"type": "rename_column", "column_id": "<id>", "title": "<new title>"}
- {"type": "add_card", "column_id": "<id>", "title": "<title>", "details": "<details>"}
- {"type": "delete_card", "card_id": "<id>"}
- {"type": "move_card", "card_id": "<id>", "target_column_id": "<id>", "target_index": <int>}

Rules:
- Use existing column ids and card ids from the supplied board state. Do not invent ids.
- For new cards, omit the card id; the server will assign one.
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


def apply_ai_board_update(board: dict, board_update: dict | None) -> tuple[dict, bool]:
    """Validate and apply an AI-suggested board update. Drops invalid actions."""
    if not isinstance(board_update, dict):
        return board, False
    actions = board_update.get("actions")
    if not isinstance(actions, list) or not actions:
        return board, False

    valid_column_ids = {c["id"] for c in board["columns"]}
    changed = False

    for action in actions:
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        try:
            if action_type == "rename_column":
                column_id = action.get("column_id")
                title = action.get("title")
                if column_id in valid_column_ids and isinstance(title, str) and title.strip():
                    board = apply_board_action(board, "rename_column", {"column_id": column_id, "title": title.strip()})
                    changed = True
            elif action_type == "add_card":
                column_id = action.get("column_id")
                title = action.get("title")
                details = action.get("details", "No details yet.")
                if column_id in valid_column_ids and isinstance(title, str) and title.strip():
                    board = apply_board_action(board, "add_card", {
                        "column_id": column_id,
                        "title": title.strip(),
                        "details": details if isinstance(details, str) else "No details yet.",
                    })
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
        except HTTPException as exc:
            logger.warning("AI action %r rejected: %s", action_type, exc.detail)
            continue

    return board, changed
