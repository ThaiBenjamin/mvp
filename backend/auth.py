"""Session storage, the require_user dependency, and the auth HTTP routes."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import config
from .db import get_connection
from .security import upgrade_password_hash, verify_password


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


# ------------------------------------------------------------------ HTTP API

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/session")
async def session(session_token: Annotated[str | None, Cookie()] = None):
    user_id = session_user_id(session_token)
    if user_id is None:
        return {"authenticated": False, "username": None}
    with get_connection() as conn:
        cursor = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
    return {"authenticated": True, "username": row[0] if row else None}


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

    token = create_session(user_id)
    response = JSONResponse({"authenticated": True, "username": req.username})
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
