"""Session storage, the require_user dependency, and the auth HTTP routes."""
from __future__ import annotations

import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config
from .db import DEFAULT_BOARD_STATE, get_connection
from .security import hash_password, upgrade_password_hash, verify_password


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")


# -------------------------------------------------------------- DB operations

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (_now_utc() + timedelta(seconds=config.SESSION_COOKIE_MAX_AGE)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
        conn.commit()
    return token


def delete_session(token: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def find_user(username: str):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        )
        return cursor.fetchone()


def fetch_user(user_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, username, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "displayName": row[2], "createdAt": row[3]}


def session_user_id(token: str | None) -> int | None:
    if not token:
        return None
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?",
            (token,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        user_id, expires_at = row
        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            return None
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < _now_utc():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return user_id


def require_user(session_token: Annotated[str | None, Cookie()] = None) -> int:
    user_id = session_user_id(session_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user_id


def register_user(username: str, password: str, display_name: str | None) -> int:
    """Create a user + seed default board. Raises 409 on duplicate username."""
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-32 chars: letters, digits, '.', '-', '_'",
        )
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    password_hash = hash_password(password)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username, password_hash, display_name or username),
            )
            user_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO boards (user_id, name, state, position) VALUES (?, ?, ?, 0)",
                (user_id, "My Board", json.dumps(DEFAULT_BOARD_STATE)),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")
    return user_id


# ------------------------------------------------------------------ HTTP API

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=256)
    display_name: str | None = Field(default=None, max_length=64)


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, min_length=6, max_length=256)


router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/session")
async def session(session_token: Annotated[str | None, Cookie()] = None):
    user_id = session_user_id(session_token)
    if user_id is None:
        return {"authenticated": False, "username": None}
    user = fetch_user(user_id)
    if user is None:
        return {"authenticated": False, "username": None}
    return {
        "authenticated": True,
        "username": user["username"],
        "displayName": user["displayName"],
    }


@router.post("/register", status_code=201)
async def register(req: RegisterRequest):
    user_id = register_user(req.username.strip(), req.password, req.display_name)
    token = create_session(user_id)
    response = JSONResponse(
        {"authenticated": True, "username": req.username, "displayName": req.display_name or req.username},
        status_code=201,
    )
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=config.SESSION_COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
        secure=config.SESSION_COOKIE_SECURE,
    )
    return response


@router.post("/login")
async def login(req: LoginRequest):
    user = find_user(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, password_hash = user
    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not password_hash.startswith("$2"):
        upgrade_password_hash(user_id, req.password)

    record = fetch_user(user_id)
    token = create_session(user_id)
    response = JSONResponse(
        {
            "authenticated": True,
            "username": req.username,
            "displayName": record["displayName"] if record else req.username,
        }
    )
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=config.SESSION_COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
        secure=config.SESSION_COOKIE_SECURE,
    )
    return response


@router.post("/logout")
async def logout(session_token: Annotated[str | None, Cookie()] = None):
    if session_token:
        delete_session(session_token)
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/me")
async def me(user_id: Annotated[int, Depends(require_user)]):
    user = fetch_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me")
async def update_profile(
    req: UpdateProfileRequest,
    user_id: Annotated[int, Depends(require_user)],
):
    if req.display_name is None and req.password is None:
        raise HTTPException(status_code=422, detail="At least one field must be supplied")
    with get_connection() as conn:
        if req.display_name is not None:
            conn.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (req.display_name, user_id),
            )
        if req.password is not None:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(req.password), user_id),
            )
        conn.commit()
    return fetch_user(user_id)
