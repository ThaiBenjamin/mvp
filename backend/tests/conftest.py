"""Shared pytest fixtures: each test gets a fresh on-disk SQLite DB.

We override config.DB_FILE to a tmp path so tests are isolated from each
other and from the developer's local DB. ensure_database() is then called
to create the schema and seed the default user/board against the new path.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Point the backend at a fresh SQLite file and seed the schema."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from backend import config
    monkeypatch.setattr(config, "DB_FILE", tmp_path / "pm.db")
    from backend.db import ensure_database
    ensure_database()
    yield
