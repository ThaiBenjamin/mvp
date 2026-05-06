"""repair_board_state must NOT resurrect deleted defaults (C5)."""
from __future__ import annotations

import pytest

from backend.boards import repair_board_state
from backend.db import DEFAULT_BOARD_STATE

pytestmark = pytest.mark.usefixtures("fresh_db")


def test_repair_keeps_user_deletions():
    """A user-deleted card-1 must stay deleted across repair."""
    state = {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-2"]},
            {"id": "col-discovery", "title": "Discovery", "cardIds": []},
        ],
        "cards": {
            "card-2": {"id": "card-2", "title": "kept", "details": "x"},
        },
    }
    out = repair_board_state(state)
    assert "card-1" not in out["cards"]
    backlog = next(c for c in out["columns"] if c["id"] == "col-backlog")
    assert "card-1" not in backlog["cardIds"]


def test_repair_falls_back_when_columns_invalid():
    out = repair_board_state({"columns": "wrong", "cards": {}})
    assert out == DEFAULT_BOARD_STATE


def test_repair_strips_non_string_card_ids():
    state = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["c1", 42, None, "c2"]}],
        "cards": {"c1": {"id": "c1", "title": "x", "details": "y"}},
    }
    out = repair_board_state(state)
    assert out["columns"][0]["cardIds"] == ["c1", "c2"]


def test_repair_dedupes_columns():
    state = {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": []},
            {"id": "col-a", "title": "duplicate", "cardIds": []},
        ],
        "cards": {},
    }
    out = repair_board_state(state)
    assert len(out["columns"]) == 1
