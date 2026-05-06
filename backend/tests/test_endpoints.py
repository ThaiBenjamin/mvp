"""End-to-end HTTP tests for the legacy single-board endpoints (no live AI)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.boards import first_board_id
from backend.chat import append_chat_message
from backend.main import app

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/login", json={"username": "user", "password": "password"})
    return c


def test_board_action_validates_action(client):
    response = client.post("/api/board/actions", json={"action": "frobnicate", "payload": {}})
    assert response.status_code == 422


def test_board_action_validates_payload(client):
    response = client.post("/api/board/actions", json={"action": "rename_column", "payload": {}})
    assert response.status_code == 422


def test_rename_column_round_trip(client):
    response = client.post("/api/board/actions", json={
        "action": "rename_column",
        "payload": {"column_id": "col-backlog", "title": "Inbox"},
    })
    assert response.status_code == 200
    body = response.json()
    backlog = next(c for c in body["columns"] if c["id"] == "col-backlog")
    assert backlog["title"] == "Inbox"


def test_add_then_delete_card(client):
    response = client.post("/api/board/actions", json={
        "action": "add_card",
        "payload": {"column_id": "col-backlog", "title": "New", "details": "details"},
    })
    body = response.json()
    new_id = next(cid for cid in body["columns"][0]["cardIds"] if cid not in ("card-1", "card-2"))
    assert new_id.startswith("card-")
    assert body["cards"][new_id]["title"] == "New"
    assert body["cards"][new_id]["priority"] == "medium"
    assert body["cards"][new_id]["dueDate"] is None

    response = client.post("/api/board/actions", json={
        "action": "delete_card",
        "payload": {"card_id": new_id},
    })
    assert new_id not in response.json()["cards"]


def test_move_card_into_empty_column_persists(client):
    # Empty col-discovery first.
    client.post("/api/board/actions", json={
        "action": "move_card",
        "payload": {"card_id": "card-3", "target_column_id": "col-backlog", "target_index": 0},
    })
    # Move card-1 into the now-empty discovery column.
    response = client.post("/api/board/actions", json={
        "action": "move_card",
        "payload": {"card_id": "card-1", "target_column_id": "col-discovery", "target_index": 0},
    })
    body = response.json()
    discovery = next(c for c in body["columns"] if c["id"] == "col-discovery")
    assert discovery["cardIds"] == ["card-1"]


def test_chat_history_starts_empty(client):
    response = client.get("/api/chat/history")
    assert response.json() == {"messages": []}


def test_chat_reset_clears_history(client):
    user_id = 1
    board_id = first_board_id(user_id)
    append_chat_message(user_id, board_id, "user", "hi")
    append_chat_message(user_id, board_id, "assistant", "hello")
    response = client.post("/api/chat/reset")
    assert response.json() == {"messages": []}
    assert client.get("/api/chat/history").json() == {"messages": []}
