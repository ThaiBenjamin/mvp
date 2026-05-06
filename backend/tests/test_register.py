"""User registration and profile management."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    return TestClient(app)


def test_register_creates_user_and_session(client):
    response = client.post(
        "/api/register",
        json={"username": "alice", "password": "secret123", "display_name": "Alice"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["authenticated"] is True
    assert body["username"] == "alice"
    assert body["displayName"] == "Alice"
    assert "session_token" in response.cookies


def test_register_seeds_initial_board(client):
    client.post(
        "/api/register",
        json={"username": "alice", "password": "secret123"},
    )
    response = client.get("/api/boards")
    assert response.status_code == 200
    boards = response.json()["boards"]
    assert len(boards) == 1
    assert boards[0]["name"] == "My Board"


def test_register_rejects_duplicate_username(client):
    client.post("/api/register", json={"username": "alice", "password": "secret123"})
    second = TestClient(app).post(
        "/api/register",
        json={"username": "alice", "password": "secret456"},
    )
    assert second.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post("/api/register", json={"username": "alice", "password": "short"})
    assert response.status_code == 422


def test_register_rejects_invalid_username_chars(client):
    response = client.post(
        "/api/register",
        json={"username": "bad name!", "password": "secret123"},
    )
    assert response.status_code == 422


def test_register_isolated_board_state():
    """Each user gets their own boards and chat history."""
    a = TestClient(app)
    a.post("/api/register", json={"username": "alice", "password": "secret123"})
    b = TestClient(app)
    b.post("/api/register", json={"username": "bob", "password": "secret123"})

    a_boards = a.get("/api/boards").json()["boards"]
    b_boards = b.get("/api/boards").json()["boards"]
    assert a_boards[0]["id"] != b_boards[0]["id"]


def test_me_returns_current_user(client):
    client.post("/api/register", json={"username": "alice", "password": "secret123", "display_name": "Alice"})
    response = client.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["displayName"] == "Alice"


def test_update_profile_changes_display_name(client):
    client.post("/api/register", json={"username": "alice", "password": "secret123"})
    response = client.patch("/api/me", json={"display_name": "Alice Smith"})
    assert response.status_code == 200
    assert response.json()["displayName"] == "Alice Smith"


def test_update_profile_changes_password_lets_user_log_in(client):
    client.post("/api/register", json={"username": "alice", "password": "secret123"})
    client.patch("/api/me", json={"password": "new_secret"})
    client.post("/api/logout")
    response = client.post("/api/login", json={"username": "alice", "password": "new_secret"})
    assert response.status_code == 200


def test_update_profile_requires_at_least_one_field(client):
    client.post("/api/register", json={"username": "alice", "password": "secret123"})
    response = client.patch("/api/me", json={})
    assert response.status_code == 422
