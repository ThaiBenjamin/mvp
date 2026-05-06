"""Unit tests for apply_board_action — the core mutation primitive."""
from __future__ import annotations

import copy

import pytest
from fastapi import HTTPException

from backend.boards import apply_board_action

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def board():
    return {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["c1", "c2"]},
            {"id": "col-b", "title": "B", "cardIds": ["c3"]},
            {"id": "col-empty", "title": "Empty", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "One", "details": "first"},
            "c2": {"id": "c2", "title": "Two", "details": "second"},
            "c3": {"id": "c3", "title": "Three", "details": "third"},
        },
    }


def test_rename_column(board):
    before = copy.deepcopy(board)
    out = apply_board_action(board, "rename_column", {"column_id": "col-a", "title": "Renamed"})
    assert out["columns"][0]["title"] == "Renamed"
    assert board == before  # input must be unchanged


def test_rename_unknown_column_rejected(board):
    with pytest.raises(HTTPException) as exc:
        apply_board_action(board, "rename_column", {"column_id": "col-nope", "title": "x"})
    assert exc.value.status_code == 400


def test_add_card_uses_card_prefix_id(board):
    out = apply_board_action(board, "add_card", {"column_id": "col-empty", "title": "New", "details": "d"})
    new_id = out["columns"][2]["cardIds"][0]
    assert new_id.startswith("card-")
    assert out["cards"][new_id]["title"] == "New"


def test_add_card_unknown_column_rejected(board):
    with pytest.raises(HTTPException) as exc:
        apply_board_action(board, "add_card", {"column_id": "ghost", "title": "x"})
    assert exc.value.status_code == 400


def test_delete_card_removes_from_cards_and_columns(board):
    out = apply_board_action(board, "delete_card", {"card_id": "c1"})
    assert "c1" not in out["cards"]
    assert "c1" not in out["columns"][0]["cardIds"]


def test_move_card_cross_column_at_index(board):
    out = apply_board_action(board, "move_card", {
        "card_id": "c1", "target_column_id": "col-b", "target_index": 0,
    })
    assert out["columns"][0]["cardIds"] == ["c2"]
    assert out["columns"][1]["cardIds"] == ["c1", "c3"]


def test_move_card_to_empty_column(board):
    out = apply_board_action(board, "move_card", {
        "card_id": "c1", "target_column_id": "col-empty", "target_index": 0,
    })
    assert out["columns"][0]["cardIds"] == ["c2"]
    assert out["columns"][2]["cardIds"] == ["c1"]


def test_move_card_same_column_does_not_drop_card(board):
    """Regression: same-column move was deleting the card pre-fix."""
    out = apply_board_action(board, "move_card", {
        "card_id": "c1", "target_column_id": "col-a", "target_index": 1,
    })
    assert out["columns"][0]["cardIds"] == ["c2", "c1"]
    assert "c1" in out["cards"]


def test_move_card_invalid_target_rejected(board):
    with pytest.raises(HTTPException) as exc:
        apply_board_action(board, "move_card", {
            "card_id": "c1", "target_column_id": "ghost",
        })
    assert exc.value.status_code == 400


def test_apply_board_action_does_not_mutate_input(board):
    before = copy.deepcopy(board)
    apply_board_action(board, "add_card", {"column_id": "col-a", "title": "x", "details": "y"})
    apply_board_action(board, "delete_card", {"card_id": "c1"})
    apply_board_action(board, "move_card", {
        "card_id": "c1", "target_column_id": "col-b", "target_index": 0,
    })
    assert board == before


def test_unsupported_action_rejected(board):
    with pytest.raises(HTTPException) as exc:
        apply_board_action(board, "frobnicate", {})
    assert exc.value.status_code == 400
