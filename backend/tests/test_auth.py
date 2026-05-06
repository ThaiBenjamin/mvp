"""Login + session flow with bcrypt password hashing (C4)."""
from __future__ import annotations

import bcrypt
import pytest
from fastapi.testclient import TestClient

from backend.db import get_connection
from backend.main import app
from backend.security import hash_password, verify_password

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture
def client():
    return TestClient(app)


def test_password_hash_uses_bcrypt():
    h = hash_password("password")
    assert h.startswith("$2")
    assert verify_password("password", h)
    assert not verify_password("wrong", h)


def test_legacy_sha256_hash_still_verifies():
    """Login-time upgrade path: stored SHA-256 still verifies for now."""
    import hashlib
    legacy = hashlib.sha256(b"password").hexdigest()
    assert verify_password("password", legacy)


def test_login_success_sets_cookie(client):
    response = client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert "session_token" in response.cookies


def test_login_wrong_password_returns_401(client):
    response = client.post("/api/login", json={"username": "user", "password": "wrong"})
    assert response.status_code == 401


def test_login_missing_field_returns_422(client):
    response = client.post("/api/login", json={"username": "user"})
    assert response.status_code == 422


def test_logged_in_user_can_load_board(client):
    client.post("/api/login", json={"username": "user", "password": "password"})
    response = client.get("/api/board")
    assert response.status_code == 200
    assert "columns" in response.json()


def test_logged_out_user_cannot_load_board(client):
    response = client.get("/api/board")
    assert response.status_code == 401


def test_legacy_sha256_login_upgrades_hash():
    """A user seeded with SHA-256 should have their hash upgraded on first login."""
    import hashlib
    legacy = hashlib.sha256(b"password").hexdigest()
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = 'user'", (legacy,))
        conn.commit()

    client = TestClient(app)
    response = client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200

    with get_connection() as conn:
        cursor = conn.execute("SELECT password_hash FROM users WHERE username = 'user'")
        new_hash = cursor.fetchone()[0]
    assert new_hash.startswith("$2")
    assert bcrypt.checkpw(b"password", new_hash.encode())
