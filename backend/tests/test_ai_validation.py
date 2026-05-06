"""Tests for the AI response parser and the structured-update validator."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.ai import apply_ai_board_update, parse_ai_response

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def board():
    return {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["c1"]},
            {"id": "col-b", "title": "B", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "One", "details": "x"},
        },
    }


# -------- parse_ai_response

def test_parse_plain_json():
    out = parse_ai_response('{"message": "hi", "boardUpdate": null}')
    assert out["message"] == "hi"
    assert out["boardUpdate"] is None


def test_parse_strips_markdown_fences():
    out = parse_ai_response('```json\n{"message": "hi"}\n```')
    assert out["message"] == "hi"
    assert out["boardUpdate"] is None  # default-filled


def test_parse_invalid_json_raises_502():
    with pytest.raises(HTTPException) as exc:
        parse_ai_response("not json")
    assert exc.value.status_code == 502


def test_parse_missing_message_raises_502():
    with pytest.raises(HTTPException) as exc:
        parse_ai_response('{"boardUpdate": null}')
    assert exc.value.status_code == 502


def test_parse_non_string_message_raises_502():
    with pytest.raises(HTTPException) as exc:
        parse_ai_response('{"message": 42}')
    assert exc.value.status_code == 502


# -------- apply_ai_board_update

def test_apply_ai_no_update_returns_unchanged(board):
    out, changed = apply_ai_board_update(board, None)
    assert out is board
    assert changed is False


def test_apply_ai_invalid_actions_dropped(board):
    out, changed = apply_ai_board_update(board, {"actions": [
        {"type": "rename_column", "column_id": "ghost", "title": "x"},
        {"type": "add_card", "column_id": "ghost", "title": "x"},
        {"type": "delete_card", "card_id": "ghost"},
        {"type": "move_card", "card_id": "ghost", "target_column_id": "col-a"},
        {"type": "unknown"},
        "not a dict",
    ]})
    assert changed is False
    assert out == board


def test_apply_ai_valid_add_card(board):
    out, changed = apply_ai_board_update(board, {"actions": [
        {"type": "add_card", "column_id": "col-b", "title": "AI added", "details": "ok"},
    ]})
    assert changed is True
    new_card = next(iter(out["columns"][1]["cardIds"]))
    assert out["cards"][new_card]["title"] == "AI added"


def test_apply_ai_rejects_invalid_title(board):
    out, changed = apply_ai_board_update(board, {"actions": [
        {"type": "rename_column", "column_id": "col-a", "title": "   "},
    ]})
    assert changed is False
    assert out == board


def test_apply_ai_chained_actions(board):
    out, changed = apply_ai_board_update(board, {"actions": [
        {"type": "move_card", "card_id": "c1", "target_column_id": "col-b", "target_index": 0},
        {"type": "rename_column", "column_id": "col-b", "title": "Done"},
    ]})
    assert changed is True
    assert out["columns"][1]["cardIds"] == ["c1"]
    assert out["columns"][1]["title"] == "Done"
