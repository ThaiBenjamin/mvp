"""Multiple-board CRUD and per-board scoping."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/api/login", json={"username": "user", "password": "password"})
    return c


def test_list_boards_returns_seeded_board(client):
    response = client.get("/api/boards")
    assert response.status_code == 200
    boards = response.json()["boards"]
    assert len(boards) == 1
    assert boards[0]["name"] == "My Board"
    assert boards[0]["position"] == 0


def test_create_board(client):
    response = client.post("/api/boards", json={"name": "Roadmap"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Roadmap"
    assert body["position"] == 1

    listing = client.get("/api/boards").json()["boards"]
    assert [b["name"] for b in listing] == ["My Board", "Roadmap"]


def test_create_board_validates_name(client):
    response = client.post("/api/boards", json={"name": ""})
    assert response.status_code == 422


def test_rename_board(client):
    boards = client.get("/api/boards").json()["boards"]
    response = client.patch(f"/api/boards/{boards[0]['id']}", json={"name": "Inbox"})
    assert response.status_code == 200
    assert response.json()["name"] == "Inbox"


def test_delete_board_requires_more_than_one(client):
    boards = client.get("/api/boards").json()["boards"]
    response = client.delete(f"/api/boards/{boards[0]['id']}")
    assert response.status_code == 400


def test_delete_board_succeeds_when_other_boards_exist(client):
    extra = client.post("/api/boards", json={"name": "Extra"}).json()
    response = client.delete(f"/api/boards/{extra['id']}")
    assert response.status_code == 204
    listing = client.get("/api/boards").json()["boards"]
    assert all(b["id"] != extra["id"] for b in listing)


def test_get_board_state_returns_full_data(client):
    boards = client.get("/api/boards").json()["boards"]
    response = client.get(f"/api/boards/{boards[0]['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Board"
    assert "columns" in body
    assert "cards" in body


def test_actions_are_scoped_to_board(client):
    second = client.post("/api/boards", json={"name": "Second"}).json()
    boards = client.get("/api/boards").json()["boards"]
    first_id = next(b["id"] for b in boards if b["name"] == "My Board")

    # Add card to second board.
    response = client.post(
        f"/api/boards/{second['id']}/actions",
        json={"action": "add_card", "payload": {"column_id": "col-todo", "title": "Hello"}},
    )
    assert response.status_code == 200

    first_state = client.get(f"/api/boards/{first_id}").json()
    second_state = client.get(f"/api/boards/{second['id']}").json()

    titles_first = {c["title"] for c in first_state["cards"].values()}
    titles_second = {c["title"] for c in second_state["cards"].values()}
    assert "Hello" in titles_second
    assert "Hello" not in titles_first


def test_cannot_access_other_users_board():
    a = TestClient(app)
    a.post("/api/register", json={"username": "alice", "password": "secret123"})
    a_board = a.get("/api/boards").json()["boards"][0]

    b = TestClient(app)
    b.post("/api/register", json={"username": "bob", "password": "secret123"})

    response = b.get(f"/api/boards/{a_board['id']}")
    assert response.status_code == 404


def test_actions_404_on_unknown_board(client):
    response = client.post(
        "/api/boards/9999/actions",
        json={"action": "add_card", "payload": {"column_id": "col-backlog", "title": "x"}},
    )
    assert response.status_code == 404
