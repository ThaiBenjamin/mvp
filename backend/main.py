from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "frontend" / "out"
DB_FILE = BASE_DIR / "pm.db"

load_dotenv(BASE_DIR.parent / ".env")

VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_COOKIE_NAME = "session_token"
SESSION_COOKIE_MAX_AGE = 3600

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b:free"
CHAT_HISTORY_LIMIT = 20

DEFAULT_BOARD_STATE = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}

app = FastAPI(title="PM MVP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                state TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()

        cursor.execute("SELECT id FROM users WHERE username = ?", (VALID_USERNAME,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (VALID_USERNAME, hash_password(VALID_PASSWORD)),
            )
            conn.commit()
            user_id = cursor.lastrowid
        else:
            user_id = row[0]

        cursor.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO boards (user_id, state) VALUES (?, ?)",
                (user_id, json.dumps(DEFAULT_BOARD_STATE)),
            )
            conn.commit()


ensure_database()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
        conn.commit()
    return token


def delete_session(token: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def find_user(username: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        )
        return cursor.fetchone()


def repair_board_state(board_state: dict) -> dict:
    if not isinstance(board_state, dict):
        return DEFAULT_BOARD_STATE

    columns = board_state.get("columns")
    cards = board_state.get("cards")
    if not isinstance(columns, list) or not isinstance(cards, dict):
        return DEFAULT_BOARD_STATE

    default_columns_by_id = {col["id"]: col for col in DEFAULT_BOARD_STATE["columns"]}
    repaired_columns = []
    seen_ids = set()

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_id = column.get("id")
        if not isinstance(column_id, str):
            continue
        seen_ids.add(column_id)
        card_ids = column.get("cardIds")
        repaired_columns.append(
            {
                "id": column_id,
                "title": column.get(
                    "title",
                    default_columns_by_id.get(column_id, {}).get("title", column_id),
                ),
                "cardIds": card_ids if isinstance(card_ids, list) else [],
            }
        )

    for default_column in DEFAULT_BOARD_STATE["columns"]:
        if default_column["id"] not in seen_ids:
            repaired_columns.append(
                {
                    "id": default_column["id"],
                    "title": default_column["title"],
                    "cardIds": [
                        card_id
                        for card_id in default_column["cardIds"]
                        if card_id not in [
                            cid
                            for column in repaired_columns
                            for cid in column["cardIds"]
                        ]
                    ],
                }
            )

    repaired_cards = {
        card_id: card
        for card_id, card in cards.items()
        if isinstance(card_id, str) and isinstance(card, dict)
    }

    for card_id, card in DEFAULT_BOARD_STATE["cards"].items():
        if card_id not in repaired_cards:
            repaired_cards[card_id] = card

    if not repaired_columns or not repaired_cards:
        return DEFAULT_BOARD_STATE

    return {"columns": repaired_columns, "cards": repaired_cards}


def merge_board_patch(board_state: dict, patch_data: dict) -> dict:
    merged = {**board_state}

    def merge_columns(existing_columns, patch_columns):
        patch_by_id = {
            patch["id"]: patch
            for patch in patch_columns
            if isinstance(patch, dict) and isinstance(patch.get("id"), str)
        }
        merged_columns = []
        existing_ids = [
            column["id"]
            for column in existing_columns
            if isinstance(column, dict) and isinstance(column.get("id"), str)
        ]

        for column in existing_columns:
            if not isinstance(column, dict) or not isinstance(column.get("id"), str):
                continue
            column_id = column["id"]
            if column_id in patch_by_id:
                patch = patch_by_id[column_id]
                merged_column = {**column, **patch}
                if "cardIds" in patch and not isinstance(patch["cardIds"], list):
                    merged_column["cardIds"] = column.get("cardIds", [])
                merged_columns.append(merged_column)
            else:
                merged_columns.append(column)

        for patch_id, patch in patch_by_id.items():
            if patch_id not in existing_ids:
                base = default_columns_by_id.get(
                    patch_id,
                    {"id": patch_id, "title": patch.get("title", patch_id), "cardIds": []},
                )
                merged_column = {**base, **patch}
                merged_columns.append(merged_column)

        return merged_columns

    default_columns_by_id = {col["id"]: col for col in DEFAULT_BOARD_STATE["columns"]}

    for key, value in patch_data.items():
        if key == "columns" and isinstance(value, list):
            merged["columns"] = merge_columns(board_state.get("columns", []), value)
        elif key == "cards" and isinstance(value, dict):
            merged["cards"] = {**board_state.get("cards", {}), **value}
        else:
            merged[key] = value

    return merged


def load_board_state(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT state FROM boards WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            try:
                board_state = json.loads(row[0])
            except json.JSONDecodeError:
                board_state = DEFAULT_BOARD_STATE

            repaired = repair_board_state(board_state)
            if repaired != board_state:
                save_board_state(repaired, user_id=user_id)
            return repaired

    save_board_state(DEFAULT_BOARD_STATE, user_id=user_id)
    return DEFAULT_BOARD_STATE


def save_board_state(state: dict, user_id: int):
    state_text = json.dumps(state)
    updated_at = datetime.utcnow().isoformat() + "Z"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version FROM boards WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        version = row[0] + 1 if row else 1
        cursor.execute(
            """
            INSERT INTO boards (user_id, state, version, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              state = excluded.state,
              version = excluded.version,
              updated_at = excluded.updated_at
            """,
            (user_id, state_text, version, updated_at),
        )
        conn.commit()


def require_authenticated(request: Request):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?",
            (session_token,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user_id, expires_at = row
        if datetime.fromisoformat(expires_at) < datetime.utcnow():
            cursor.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
            conn.commit()
            raise HTTPException(status_code=401, detail="Unauthorized")

    return user_id


def apply_board_action(board: dict, action: str, payload: dict) -> dict:
    if action == "rename_column":
        column_id = payload["column_id"]
        title = payload["title"]
        board["columns"] = [
            {**column, "title": title} if column["id"] == column_id else column
            for column in board["columns"]
        ]
        return board

    if action == "add_card":
        card_id = payload.get("card_id") or secrets.token_hex(8)
        column_id = payload["column_id"]
        title = payload["title"]
        details = payload.get("details", "No details yet.")
        board["cards"][card_id] = {"id": card_id, "title": title, "details": details}
        board["columns"] = [
            {
                **column,
                "cardIds": column["cardIds"] + [card_id] if column["id"] == column_id else column["cardIds"],
            }
            for column in board["columns"]
        ]
        return board

    if action == "delete_card":
        card_id = payload["card_id"]
        board["cards"] = {k: v for k, v in board["cards"].items() if k != card_id}
        board["columns"] = [
            {**column, "cardIds": [cid for cid in column["cardIds"] if cid != card_id]}
            for column in board["columns"]
        ]
        return board

    if action == "move_card":
        card_id = payload["card_id"]
        target_column_id = payload["target_column_id"]
        target_index = payload.get("target_index")

        source_column = next(
            (column for column in board["columns"] if card_id in column["cardIds"]),
            None,
        )
        target_column = next(
            (column for column in board["columns"] if column["id"] == target_column_id),
            None,
        )

        if not source_column or not target_column:
            raise HTTPException(status_code=400, detail="Invalid column or card id")

        if source_column["id"] == target_column_id:
            reordered = [cid for cid in source_column["cardIds"] if cid != card_id]
            if target_index is None or target_index < 0 or target_index > len(reordered):
                reordered.append(card_id)
            else:
                reordered.insert(target_index, card_id)
            board["columns"] = [
                {**column, "cardIds": reordered} if column["id"] == source_column["id"] else column
                for column in board["columns"]
            ]
            return board

        new_source_card_ids = [cid for cid in source_column["cardIds"] if cid != card_id]
        new_target_card_ids = target_column["cardIds"][:]
        if target_index is None or target_index < 0 or target_index > len(new_target_card_ids):
            new_target_card_ids.append(card_id)
        else:
            new_target_card_ids.insert(target_index, card_id)

        board["columns"] = [
            {**column, "cardIds": new_source_card_ids} if column["id"] == source_column["id"] else
            {**column, "cardIds": new_target_card_ids} if column["id"] == target_column_id else
            column
            for column in board["columns"]
        ]
        return board

    raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "message": "backend is healthy"})


@app.get("/api/session")
async def session(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return JSONResponse({"authenticated": False, "username": None})

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?",
            (token,),
        )
        row = cursor.fetchone()
        if not row:
            return JSONResponse({"authenticated": False, "username": None})

        user_id, expires_at = row
        if datetime.fromisoformat(expires_at) < datetime.utcnow():
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return JSONResponse({"authenticated": False, "username": None})

        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        return JSONResponse(
            {"authenticated": True, "username": user_row[0] if user_row else None}
        )


@app.get("/api/board")
async def get_board(request: Request):
    user_id = require_authenticated(request)
    return JSONResponse(load_board_state(user_id=user_id))


@app.post("/api/board")
async def update_board(request: Request):
    user_id = require_authenticated(request)
    board_state = await request.json()
    save_board_state(board_state, user_id=user_id)
    return JSONResponse(board_state)


@app.patch("/api/board")
async def patch_board(request: Request):
    user_id = require_authenticated(request)
    patch_data = await request.json()
    board_state = load_board_state(user_id=user_id)
    updated_state = merge_board_patch(board_state, patch_data)
    save_board_state(updated_state, user_id=user_id)
    return JSONResponse(updated_state)


@app.post("/api/board/actions")
async def board_actions(request: Request):
    user_id = require_authenticated(request)
    payload = await request.json()
    action = payload.get("action")
    data = payload.get("payload", {})
    if not action:
        raise HTTPException(status_code=400, detail="Action is required")

    board_state = load_board_state(user_id=user_id)
    updated = apply_board_action(board_state, action, data)
    save_board_state(updated, user_id=user_id)
    return JSONResponse(updated)


@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")

    user = find_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id, password_hash = user
    if password_hash != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_session(user_id)
    response_payload = JSONResponse({"authenticated": True, "username": username})
    response_payload.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
    )
    return response_payload


@app.post("/api/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    response_payload = JSONResponse({"authenticated": False})
    response_payload.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response_payload


SYSTEM_PROMPT = """You are a project management assistant embedded in a Kanban app.

The user has one Kanban board with fixed columns and freely titled cards. You can chat with the user and you may optionally modify the board.

You ALWAYS respond with a single JSON object on its own (no surrounding prose, no markdown fences) shaped like:
{"message": string, "boardUpdate": null | {"actions": [...]}}

`boardUpdate.actions` is an array applied in order. Each action is one of:
- {"type": "rename_column", "column_id": "<id>", "title": "<new title>"}
- {"type": "add_card", "column_id": "<id>", "title": "<title>", "details": "<details>"}
- {"type": "delete_card", "card_id": "<id>"}
- {"type": "move_card", "card_id": "<id>", "target_column_id": "<id>", "target_index": <int>}

Rules:
- Use existing column ids and card ids from the supplied board state. Do not invent ids.
- For new cards, omit the card id; the server will assign one.
- Set boardUpdate to null when the user is just asking a question with no requested change.
- Keep `message` short, friendly, and explain what you changed (if anything).
- Output MUST be valid JSON. No code fences."""


def load_chat_history(user_id: int) -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id ASC",
            (user_id,),
        )
        return [{"role": role, "content": content} for role, content in cursor.fetchall()]


def append_chat_message(user_id: int, role: str, content: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.commit()


def clear_chat_history(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        conn.commit()


async def call_openrouter(messages: list[dict]) -> str:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=body)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"OpenRouter error: {response.status_code} {response.text[:300]}",
            )
        data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected OpenRouter response: {exc}")


def parse_ai_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        # Strip markdown fences if the model ignores instructions.
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {exc}")

    if not isinstance(parsed, dict) or "message" not in parsed:
        raise HTTPException(status_code=502, detail="AI response missing 'message'")

    parsed.setdefault("boardUpdate", None)
    return parsed


def apply_ai_board_update(board: dict, board_update: dict | None) -> tuple[dict, bool]:
    if not board_update or not isinstance(board_update, dict):
        return board, False

    actions = board_update.get("actions")
    if not isinstance(actions, list) or not actions:
        return board, False

    valid_column_ids = {col["id"] for col in board["columns"]}
    changed = False

    for action in actions:
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        if action_type == "rename_column":
            column_id = action.get("column_id")
            title = action.get("title")
            if column_id in valid_column_ids and isinstance(title, str) and title.strip():
                board = apply_board_action(
                    board, "rename_column", {"column_id": column_id, "title": title.strip()}
                )
                changed = True
        elif action_type == "add_card":
            column_id = action.get("column_id")
            title = action.get("title")
            details = action.get("details", "No details yet.")
            if column_id in valid_column_ids and isinstance(title, str) and title.strip():
                board = apply_board_action(
                    board,
                    "add_card",
                    {"column_id": column_id, "title": title.strip(), "details": details},
                )
                changed = True
        elif action_type == "delete_card":
            card_id = action.get("card_id")
            if isinstance(card_id, str) and card_id in board["cards"]:
                board = apply_board_action(board, "delete_card", {"card_id": card_id})
                changed = True
        elif action_type == "move_card":
            card_id = action.get("card_id")
            target_column_id = action.get("target_column_id")
            target_index = action.get("target_index")
            if (
                isinstance(card_id, str)
                and card_id in board["cards"]
                and target_column_id in valid_column_ids
            ):
                board = apply_board_action(
                    board,
                    "move_card",
                    {
                        "card_id": card_id,
                        "target_column_id": target_column_id,
                        "target_index": target_index,
                    },
                )
                changed = True

    return board, changed


@app.get("/api/chat/history")
async def chat_history(request: Request):
    user_id = require_authenticated(request)
    return JSONResponse({"messages": load_chat_history(user_id)})


@app.post("/api/chat/reset")
async def chat_reset(request: Request):
    user_id = require_authenticated(request)
    clear_chat_history(user_id)
    return JSONResponse({"messages": []})


@app.post("/api/chat")
async def chat(request: Request):
    user_id = require_authenticated(request)
    body = await request.json()
    user_message = (body.get("message") or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    board_state = load_board_state(user_id=user_id)
    history = load_chat_history(user_id)[-CHAT_HISTORY_LIMIT:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Current board state JSON:\n{json.dumps(board_state)}",
        },
        *history,
        {"role": "user", "content": user_message},
    ]

    raw = await call_openrouter(messages)
    parsed = parse_ai_response(raw)

    updated_board, changed = apply_ai_board_update(board_state, parsed.get("boardUpdate"))
    if changed:
        save_board_state(updated_board, user_id=user_id)

    append_chat_message(user_id, "user", user_message)
    append_chat_message(user_id, "assistant", parsed["message"])

    return JSONResponse(
        {
            "message": parsed["message"],
            "boardUpdated": changed,
            "board": updated_board if changed else None,
        }
    )


@app.get("/api/ai/health")
async def ai_health():
    if not OPENROUTER_API_KEY:
        return JSONResponse({"ok": False, "reason": "missing OPENROUTER_API_KEY"}, status_code=500)
    try:
        raw = await call_openrouter(
            [
                {"role": "system", "content": "Reply with the exact JSON {\"message\": \"4\", \"boardUpdate\": null}"},
                {"role": "user", "content": "What is 2+2?"},
            ]
        )
    except HTTPException as exc:
        return JSONResponse({"ok": False, "reason": exc.detail}, status_code=exc.status_code)
    return JSONResponse({"ok": True, "raw": raw})


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
