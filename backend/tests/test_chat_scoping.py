"""Chat history is scoped to a specific board."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.boards import first_board_id
from backend.chat import append_chat_message, load_chat_history
from backend.main import app

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/login", json={"username": "user", "password": "password"})
    return c


def test_history_partitioned_by_board(client):
    user_id = 1
    first_id = first_board_id(user_id)
    second = client.post("/api/boards", json={"name": "Second"}).json()

    append_chat_message(user_id, first_id, "user", "first board hello")
    append_chat_message(user_id, second["id"], "user", "second board hello")

    first_msgs = load_chat_history(user_id, first_id)
    second_msgs = load_chat_history(user_id, second["id"])
    assert [m["content"] for m in first_msgs] == ["first board hello"]
    assert [m["content"] for m in second_msgs] == ["second board hello"]


def test_history_endpoint_returns_first_board_when_unspecified(client):
    user_id = 1
    first_id = first_board_id(user_id)
    second = client.post("/api/boards", json={"name": "Second"}).json()

    append_chat_message(user_id, first_id, "user", "first")
    append_chat_message(user_id, second["id"], "user", "second")

    response = client.get("/api/chat/history")
    assert [m["content"] for m in response.json()["messages"]] == ["first"]


def test_history_endpoint_filters_by_board_id(client):
    user_id = 1
    first_id = first_board_id(user_id)
    second = client.post("/api/boards", json={"name": "Second"}).json()

    append_chat_message(user_id, first_id, "user", "first")
    append_chat_message(user_id, second["id"], "user", "second")

    response = client.get(f"/api/chat/history?board_id={second['id']}")
    assert [m["content"] for m in response.json()["messages"]] == ["second"]


def test_chat_reset_only_clears_target_board(client):
    user_id = 1
    first_id = first_board_id(user_id)
    second = client.post("/api/boards", json={"name": "Second"}).json()

    append_chat_message(user_id, first_id, "user", "first")
    append_chat_message(user_id, second["id"], "user", "second")

    client.post(f"/api/chat/reset?board_id={second['id']}")

    assert [m["content"] for m in load_chat_history(user_id, first_id)] == ["first"]
    assert load_chat_history(user_id, second["id"]) == []


def test_chat_reset_unknown_board_404s(client):
    response = client.post("/api/chat/reset?board_id=9999")
    assert response.status_code == 404
