# Database Schema for PM MVP

This project uses SQLite for MVP persistence in `backend/pm.db`.
The schema stores user credentials and the serialized Kanban board state as JSON.

## Tables

### `users`
- `id` INTEGER PRIMARY KEY
- `username` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `created_at` TEXT NOT NULL DEFAULT (datetime('now'))

### `boards`
- `id` INTEGER PRIMARY KEY
- `user_id` INTEGER NOT NULL UNIQUE
- `state` TEXT NOT NULL
- `version` INTEGER NOT NULL DEFAULT 1
- `updated_at` TEXT NOT NULL DEFAULT (datetime('now'))
- `FOREIGN KEY(user_id)` REFERENCES `users(id)` ON DELETE CASCADE

## Rationale

- Storing the board state as JSON keeps the MVP implementation simple.
- A dedicated SQLite file enables durable persistence and automatic creation.
- The schema is designed to support future extension:
  - `users` can be expanded with auth fields and profiles.
  - `boards` can be normalized later into card/column tables.
- `version` and `updated_at` fields provide a lightweight versioning mechanism
  for board updates.

## Startup behavior

- The backend creates `backend/pm.db` automatically on startup if it does not exist.
- A default user is seeded with the credentials `user` / `password`.
- The default Kanban board state is inserted for that user if no board row exists.
