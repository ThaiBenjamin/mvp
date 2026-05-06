# Database Schema for PM MVP

This project uses SQLite for MVP persistence in `backend/pm.db`.
The schema stores user credentials, multiple Kanban boards per user, sessions,
and per-board chat history. Board state itself is serialized as JSON inside the
`boards.state` column.

## Tables

### `users`
- `id` INTEGER PRIMARY KEY
- `username` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `display_name` TEXT (added by migration; defaults to username on register)
- `created_at` TEXT NOT NULL DEFAULT (datetime('now'))

### `boards`
- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL — FK to `users(id)` ON DELETE CASCADE
- `name` TEXT NOT NULL
- `state` TEXT NOT NULL — JSON-serialized board state
- `position` INTEGER NOT NULL DEFAULT 0 — sort order for the user's sidebar
- `archived` INTEGER NOT NULL DEFAULT 0
- `version` INTEGER NOT NULL DEFAULT 1
- `updated_at` TEXT NOT NULL DEFAULT (datetime('now'))
- INDEX `idx_boards_user_id` ON `boards(user_id)`

A user may have any number of boards. The single-board legacy schema (which
enforced a `UNIQUE(user_id)` constraint) is migrated automatically at startup:
the column is rebuilt with a `name` of "My Board" and `position = 0`.

### `sessions`
- `token` TEXT PRIMARY KEY
- `user_id` INTEGER NOT NULL — FK to `users(id)` ON DELETE CASCADE
- `expires_at` TEXT NOT NULL
- `created_at` TEXT NOT NULL DEFAULT (datetime('now'))

### `chat_messages`
- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL — FK to `users(id)` ON DELETE CASCADE
- `board_id` INTEGER — FK to `boards(id)` ON DELETE CASCADE (added by migration)
- `role` TEXT NOT NULL — `user` or `assistant`
- `content` TEXT NOT NULL
- `created_at` TEXT NOT NULL DEFAULT (datetime('now'))
- INDEX `idx_chat_messages_user_id`, `idx_chat_messages_board_id`

## Board state JSON shape

```json
{
  "columns": [
    { "id": "col-todo", "title": "To Do", "cardIds": ["card-..."] }
  ],
  "cards": {
    "card-...": {
      "id": "card-...",
      "title": "...",
      "details": "...",
      "priority": "low" | "medium" | "high",
      "dueDate": null | "YYYY-MM-DD"
    }
  }
}
```

## Rationale

- Storing board state as JSON keeps the MVP simple while the schema scales to
  multi-board, multi-user use without normalizing card/column tables.
- `position` enables stable sidebar ordering without an extra link table.
- `version` and `updated_at` provide a lightweight optimistic-versioning hook.
- `chat_messages.board_id` lets the AI assistant maintain a separate
  conversation per board.

## Startup behavior

- The backend creates `backend/pm.db` automatically on startup if missing.
- The schema migration is idempotent and converts legacy single-board rows.
- A default user is seeded with credentials `user` / `password` and a single
  `My Board`. New users register via `POST /api/register` and get the same
  default board template.
