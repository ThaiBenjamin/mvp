"""SQLite connection helper, schema bootstrap, and the default board state."""
from __future__ import annotations

import json
import sqlite3

from . import config

DEFAULT_BOARD_STATE: dict = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {"id": "card-1", "title": "Align roadmap themes", "details": "Draft quarterly themes with impact statements and metrics.", "priority": "medium", "dueDate": None},
        "card-2": {"id": "card-2", "title": "Gather customer signals", "details": "Review support tags, sales notes, and churn feedback.", "priority": "medium", "dueDate": None},
        "card-3": {"id": "card-3", "title": "Prototype analytics view", "details": "Sketch initial dashboard layout and key drill-downs.", "priority": "high", "dueDate": None},
        "card-4": {"id": "card-4", "title": "Refine status language", "details": "Standardize column labels and tone across the board.", "priority": "medium", "dueDate": None},
        "card-5": {"id": "card-5", "title": "Design card layout", "details": "Add hierarchy and spacing for scanning dense lists.", "priority": "low", "dueDate": None},
        "card-6": {"id": "card-6", "title": "QA micro-interactions", "details": "Verify hover, focus, and loading states.", "priority": "medium", "dueDate": None},
        "card-7": {"id": "card-7", "title": "Ship marketing page", "details": "Final copy approved and asset pack delivered.", "priority": "high", "dueDate": None},
        "card-8": {"id": "card-8", "title": "Close onboarding sprint", "details": "Document release notes and share internally.", "priority": "low", "dueDate": None},
    },
}


def get_connection() -> sqlite3.Connection:
    """Open a fresh SQLite connection. Caller is responsible for closing."""
    config.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _migrate_boards_table(conn: sqlite3.Connection) -> None:
    """Migrate legacy boards table (UNIQUE user_id, no name) to multi-board form."""
    cursor = conn.execute("PRAGMA table_info(boards)")
    rows = cursor.fetchall()
    if not rows:
        return
    has_name = any(r[1] == "name" for r in rows)
    if has_name:
        return

    # Legacy schema: user_id UNIQUE, no name/position. Rebuild and migrate data.
    conn.execute("ALTER TABLE boards RENAME TO boards_legacy")
    conn.execute(
        """
        CREATE TABLE boards (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO boards (id, user_id, name, state, position, archived, version, updated_at)
        SELECT id, user_id, 'My Board', state, 0, 0, version, updated_at FROM boards_legacy
        """
    )
    conn.execute("DROP TABLE boards_legacy")
    conn.commit()


def _migrate_chat_messages_for_board(conn: sqlite3.Connection) -> None:
    """Add board_id column to chat_messages and backfill from user's first board."""
    if _column_exists(conn, "chat_messages", "board_id"):
        return
    conn.execute("ALTER TABLE chat_messages ADD COLUMN board_id INTEGER")
    # Backfill: associate existing chat with that user's first board.
    conn.execute(
        """
        UPDATE chat_messages
           SET board_id = (
             SELECT b.id FROM boards b
              WHERE b.user_id = chat_messages.user_id
              ORDER BY b.id ASC LIMIT 1
           )
         WHERE board_id IS NULL
        """
    )
    conn.commit()


def ensure_database() -> None:
    """Create tables if missing and seed the default user/board (idempotent)."""
    # Local import keeps db.py dependency-light; security only needed at seed time.
    from .security import hash_password

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                state TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id);
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                board_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_board_id ON chat_messages(board_id);
            """
        )
        conn.commit()

        _migrate_boards_table(conn)
        _migrate_chat_messages_for_board(conn)

        if not _column_exists(conn, "users", "display_name"):
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            conn.commit()

        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (config.SEED_USERNAME,))
        row = cursor.fetchone()
        if row is None:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (config.SEED_USERNAME, hash_password(config.SEED_PASSWORD), "Demo User"),
            )
            user_id = cursor.lastrowid
            conn.commit()
        else:
            user_id = row[0]

        cursor = conn.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is None:
            conn.execute(
                "INSERT INTO boards (user_id, name, state, position) VALUES (?, ?, ?, 0)",
                (user_id, "My Board", json.dumps(DEFAULT_BOARD_STATE)),
            )
            conn.commit()
