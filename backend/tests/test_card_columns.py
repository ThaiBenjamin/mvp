"""Tests for the new card update + column add/delete/move actions."""
from __future__ import annotations

import copy

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.boards import apply_board_action
from backend.main import app

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/login", json={"username": "user", "password": "password"})
    return c


@pytest.fixture
def board():
    return {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": ["c1"]},
            {"id": "col-b", "title": "B", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "One", "details": "first", "priority": "low", "dueDate": None},
        },
    }


# ----- update_card unit

def test_update_card_changes_title(board):
    out = apply_board_action(board, "update_card", {"card_id": "c1", "title": "New title"})
    assert out["cards"]["c1"]["title"] == "New title"
    assert out["cards"]["c1"]["details"] == "first"  # unchanged


def test_update_card_changes_priority_and_due_date(board):
    out = apply_board_action(board, "update_card", {
        "card_id": "c1",
        "priority": "high",
        "dueDate": "2026-12-01",
    })
    assert out["cards"]["c1"]["priority"] == "high"
    assert out["cards"]["c1"]["dueDate"] == "2026-12-01"


def test_update_card_invalid_priority_normalized(board):
    out = apply_board_action(board, "update_card", {"card_id": "c1", "priority": "urgent"})
    assert out["cards"]["c1"]["priority"] == "medium"


def test_update_card_invalid_due_date_dropped(board):
    out = apply_board_action(board, "update_card", {"card_id": "c1", "dueDate": "tomorrow"})
    assert out["cards"]["c1"]["dueDate"] is None


def test_update_card_unknown_id_rejected(board):
    with pytest.raises(HTTPException):
        apply_board_action(board, "update_card", {"card_id": "ghost", "title": "x"})


def test_update_card_does_not_mutate_input(board):
    before = copy.deepcopy(board)
    apply_board_action(board, "update_card", {"card_id": "c1", "title": "x"})
    assert board == before


# ----- add_column / delete_column / move_column unit

def test_add_column_appends_with_generated_id(board):
    out = apply_board_action(board, "add_column", {"title": "Backlog"})
    assert len(out["columns"]) == 3
    assert out["columns"][-1]["title"] == "Backlog"
    assert out["columns"][-1]["id"].startswith("col-")
    assert out["columns"][-1]["cardIds"] == []


def test_add_column_uses_explicit_id(board):
    out = apply_board_action(board, "add_column", {"title": "Backlog", "column_id": "col-backlog"})
    assert out["columns"][-1]["id"] == "col-backlog"


def test_add_column_rejects_duplicate_id(board):
    with pytest.raises(HTTPException):
        apply_board_action(board, "add_column", {"title": "Dup", "column_id": "col-a"})


def test_delete_column_only_when_empty(board):
    with pytest.raises(HTTPException) as exc:
        apply_board_action(board, "delete_column", {"column_id": "col-a"})
    assert "empty" in exc.value.detail.lower()


def test_delete_empty_column(board):
    out = apply_board_action(board, "delete_column", {"column_id": "col-b"})
    assert [c["id"] for c in out["columns"]] == ["col-a"]


def test_delete_column_refuses_last_column():
    one_col = {"columns": [{"id": "col-a", "title": "A", "cardIds": []}], "cards": {}}
    with pytest.raises(HTTPException):
        apply_board_action(one_col, "delete_column", {"column_id": "col-a"})


def test_move_column_reorders(board):
    out = apply_board_action(board, "move_column", {"column_id": "col-b", "target_index": 0})
    assert [c["id"] for c in out["columns"]] == ["col-b", "col-a"]


def test_move_column_clamps_index(board):
    out = apply_board_action(board, "move_column", {"column_id": "col-a", "target_index": 99})
    assert [c["id"] for c in out["columns"]] == ["col-b", "col-a"]


# ----- HTTP integration

def test_http_update_card_priority(client):
    boards = client.get("/api/boards").json()["boards"]
    bid = boards[0]["id"]
    response = client.post(
        f"/api/boards/{bid}/actions",
        json={"action": "update_card", "payload": {"card_id": "card-1", "priority": "high"}},
    )
    assert response.status_code == 200
    assert response.json()["cards"]["card-1"]["priority"] == "high"


def test_http_add_card_with_priority(client):
    boards = client.get("/api/boards").json()["boards"]
    bid = boards[0]["id"]
    response = client.post(
        f"/api/boards/{bid}/actions",
        json={
            "action": "add_card",
            "payload": {
                "column_id": "col-backlog",
                "title": "Urgent",
                "priority": "high",
                "dueDate": "2026-06-01",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    new_card = next(c for c in body["cards"].values() if c["title"] == "Urgent")
    assert new_card["priority"] == "high"
    assert new_card["dueDate"] == "2026-06-01"


def test_http_add_and_delete_column(client):
    boards = client.get("/api/boards").json()["boards"]
    bid = boards[0]["id"]
    add = client.post(
        f"/api/boards/{bid}/actions",
        json={"action": "add_column", "payload": {"title": "Frozen"}},
    )
    assert add.status_code == 200
    new_col_id = add.json()["columns"][-1]["id"]
    delete = client.post(
        f"/api/boards/{bid}/actions",
        json={"action": "delete_column", "payload": {"column_id": new_col_id}},
    )
    assert delete.status_code == 200
    assert all(c["id"] != new_col_id for c in delete.json()["columns"])


def test_http_move_column(client):
    boards = client.get("/api/boards").json()["boards"]
    bid = boards[0]["id"]
    response = client.post(
        f"/api/boards/{bid}/actions",
        json={"action": "move_column", "payload": {"column_id": "col-done", "target_index": 0}},
    )
    assert response.status_code == 200
    assert response.json()["columns"][0]["id"] == "col-done"
