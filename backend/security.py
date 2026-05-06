"""Password hashing primitives. Bcrypt with SHA-256 legacy fallback."""
from __future__ import annotations

import hashlib

import bcrypt

from .db import get_connection


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False
    # Legacy SHA-256 hashes from before the bcrypt migration.
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash


def upgrade_password_hash(user_id: int, password: str) -> None:
    new_hash = hash_password(password)
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
