# Code Review — Project Management MVP

Reviewed at commit `c3f99e3` (post stages 8–10). Scope: full repo. Findings are
ordered by severity. Each item names the location and a concrete action.

The MVP works end-to-end (auth → board CRUD → AI chat). The issues below are
real, but most are polish or hardening rather than blockers. Items marked
**Critical** should be fixed before any non-local deployment.

---

## Critical

### C1. `backend/pm.db` is tracked in git
- **Location**: `backend/pm.db` (in `git ls-files`)
- **Problem**: The SQLite database file is in version control. It changes on
  every server run, so every commit accidentally captures whoever's local
  state — including session tokens (real secrets) and personal cards. It also
  caused the test pollution we saw during stage 7 testing.
- **Action**:
  1. `git rm --cached backend/pm.db`
  2. Add `backend/pm.db` (and `*.db`) to `.gitignore`.
  3. Commit. The DB will auto-recreate on next backend startup via
     `ensure_database()`.

### C2. `backend/board.json` is a stale leaked snapshot
- **Location**: `backend/board.json` (101 lines)
- **Problem**: A snapshot of someone's local board (titles like
  "Backlog Updated", "Persistent test card", "Persistence card 1777763300605")
  is committed. Nothing in the codebase reads it — `DEFAULT_BOARD_STATE`
  in `main.py` is the source of truth.
- **Action**: `git rm backend/board.json` and add `*.json` (selectively) or
  just delete and don't add it back.

### C3. `OPENROUTER_API_KEY` is exposed in conversation history
- **Location**: `.env` (gitignored, good) — but the key was visible in our
  earlier session output.
- **Problem**: The key has been observed by anyone with chat access. Even
  though `.env` itself is not tracked, treat it as compromised.
- **Action**: Rotate the OpenRouter key now and replace `.env`. Document in
  `AGENTS.md` that the key must come from local env, not be pasted into chat
  or repo.

### C4. Passwords stored as unsalted SHA-256
- **Location**: `backend/main.py:99-100` (`hash_password`)
- **Problem**: `hashlib.sha256` with no salt is trivially rainbow-tableable.
  The MVP only seeds one user, but `users.password_hash` is the schema for
  every future user. This is a footgun the moment someone adds registration.
- **Action**: Switch to a password-hashing primitive: `passlib[bcrypt]` or
  `argon2-cffi`. Update the seeding path and `find_user`/login comparison.
  This is one focused change in `main.py` and `pyproject.toml`.

### C5. `repair_board_state` silently resurrects default cards/columns
- **Location**: `backend/main.py:207-270`
- **Problem**: On every `load_board_state` call, the helper re-adds any
  default column or card that's missing. If a user deletes `card-1`
  ("Align roadmap themes"), it reappears on the next load. This contradicts
  the delete operation and confused testing.
- **Action**: Reduce the helper to *structural* repair only (ensure
  `columns`/`cards` are dicts/lists with the right shape). Do not re-inject
  default data. If a user empties their board, that's their choice.

---

## High

### H1. `apply_board_action` mutates input dict in two places
- **Location**: `backend/main.py:399-475`
- **Problem**: `add_card` does `board["cards"][card_id] = ...` (mutation),
  then returns a board with a new `columns` array. The caller can't reason
  about whether the input was mutated. `apply_ai_board_update` chains calls
  expecting "return the new board," so a mutation that's also returned
  happens to work, but the contract is unclear.
- **Action**: Make every branch return a fresh dict (`{**board, "cards":
  {...}, "columns": [...]}`). Or, alternatively, copy the input once at the
  top and mutate that copy — and document the choice.

### H2. No input validation at API boundaries (no Pydantic models)
- **Location**: All endpoints in `backend/main.py`
- **Problem**: Endpoints `await request.json()` and index into the dict
  (`payload["card_id"]`). A request missing a required field raises a
  `KeyError` and returns 500 instead of 422. FastAPI's main strength —
  Pydantic validation — is unused.
- **Action**: Define `LoginRequest`, `BoardActionRequest` (with a tagged
  union over actions), `ChatRequest`, etc. Replace `await request.json()`
  with typed parameters: `async def board_actions(req: BoardActionRequest, ...)`.
  This also fixes H1's edge cases for free.

### H3. Backend has zero automated tests
- **Location**: `backend/`
- **Problem**: The most logic-heavy area (auth, board mutation, AI parsing
  / validation in `apply_ai_board_update`) has no tests. The bug we found
  in `move_card` for same-column moves would have been caught instantly.
- **Action**: Add `pytest` + `httpx`-based tests for: login/session, each
  `apply_board_action` branch (especially `move_card` cross-column,
  same-column, invalid inputs), `apply_ai_board_update` (drops invalid
  ids, validates types, idempotency), `parse_ai_response` (fence stripping,
  bad JSON, missing `message`).

### H4. AI error responses leak upstream details
- **Location**: `backend/main.py:655-657`
- **Problem**: On OpenRouter failure, the response includes
  `f"OpenRouter error: {response.status_code} {response.text[:300]}"`.
  That can include rate-limit URLs, internal error IDs, or partial
  prompts.
- **Action**: Log the full upstream response server-side; return a
  generic `"AI service unavailable"` to clients. Same for
  `parse_ai_response` JSON errors.

### H5. AI prompt sends the full board on every turn
- **Location**: `backend/main.py:769-780`
- **Problem**: The system message includes `json.dumps(board_state)`. As
  the board grows the prompt grows, and the model sees the entire board
  every turn — so column/card ids leak across the conversation history
  in token cost terms. For an MVP it's fine; for any real use this needs
  to be bounded.
- **Action**: Either (a) move the board into a single system message that
  isn't replayed in history (already done — but `history` from
  `load_chat_history` mixes user/assistant text without the prior board
  snapshots, so we're OK on context but still send the full board each
  turn), or (b) summarize/compress the board for the AI.

### H6. `DragOverEvent` mutates board state without reference equality
  guard for trivial moves
- **Location**: `frontend/src/components/KanbanBoard.tsx:197-243`
- **Problem**: `handleDragOver` calls `setBoard((prev) => ...)` repeatedly
  during a drag (every pointer move that crosses a column boundary).
  React will short-circuit on `Object.is`, but the new object is fresh
  each call — so re-renders fire even when nothing changed. With our drag
  helper running 8 mouse-move steps per drag, that's 8 re-renders.
- **Action**: Inside the updater, return `prev` if the move is a no-op
  (same column already, no insert position change). Return new state
  only when something actually changes.

### H7. `useEffect` ignores `dragSourceColumnRef.current` on unmount
- **Location**: `frontend/src/components/KanbanBoard.tsx:185-195`
- **Problem**: If the user starts a drag, then unmounts the component
  (e.g., logs out), refs aren't cleared. Minor — refs go away with the
  component. No action required, just noted.

### H8. Frontend has no API client; every component re-implements fetch
- **Location**: `KanbanBoard.tsx`, `AuthApp.tsx`, `AiChat.tsx`
- **Problem**: Each component has its own `fetch("/api/...")` with
  near-identical error handling. Adding a new endpoint means duplicating
  the same try/catch shape. Type drift between client and server is
  silent.
- **Action**: Add a thin `frontend/src/lib/api.ts`:
  ```ts
  export const api = {
    getBoard: () => json<BoardData>("/api/board"),
    postAction: (a: BoardAction) => json<BoardData>("/api/board/actions", { method: "POST", body: a }),
    chat: (msg: string) => json<ChatResponse>("/api/chat", { method: "POST", body: { message: msg } }),
    ...
  };
  ```
  Move the response/error shapes to a shared types file.

---

## Medium

### M1. Stale `AGENTS.md` files
- **Location**: `backend/AGENTS.md`, `frontend/AGENTS.md`, `scripts/AGENTS.md`
- **Problem**: They describe earlier scaffolding stages.
  `backend/AGENTS.md` claims "this is the scaffolding phase only" and that
  `backend/static/index.html` exists (it doesn't — that's a leftover note).
  `frontend/AGENTS.md` claims "no backend persistence yet."
  `scripts/AGENTS.md` is a single sentence: "This folder will contain
  start and stop scripts."
- **Action**: Either delete them (CLAUDE.md and `docs/PLAN.md` cover
  what's needed) or update each to reflect reality. I lean toward delete:
  the source of truth should be one place.

### M2. Ad-hoc `scripts/check_*.py` and `scripts/test_backend_routes.py`
- **Location**: `scripts/check_api_routes.py`, `check_auth.py`,
  `check_board_persistence.py`, `check_db_schema.py`, `test_backend_routes.py`
- **Problem**: 249 lines of one-off verification scripts that overlap
  with what proper pytest tests should cover. They were probably for
  earlier stage acceptance and are dead.
- **Action**: Convert them to `pytest` tests under `backend/tests/` (see
  H3) or delete. Don't leave a third "kind" of test floating.

### M3. `merge_board_patch` and the `PATCH /api/board` endpoint are dead
- **Location**: `backend/main.py:273-323`, route `@app.patch("/api/board")`
- **Problem**: The frontend uses `POST /api/board/actions` exclusively.
  No client calls PATCH. The 50-line `merge_board_patch` helper exists
  only to serve this unused endpoint.
- **Action**: Delete the PATCH route and `merge_board_patch`. Keep the
  full POST replace endpoint if you want it for AI overwrite scenarios;
  otherwise remove it too.

### M4. `getTargetDetails` and `resolveDragOverColumnId` are dead
  in production but still tested
- **Location**: `frontend/src/components/KanbanBoard.tsx:33-41`, `:93-117`
- **Problem**: Exported and unit-tested in `KanbanBoard.utils.test.ts`,
  but no longer called by the component since the multi-container
  refactor.
- **Action**: Delete both helpers and their tests. The new flow uses
  `findColumnId` + `Array.indexOf` directly inside the handlers, which
  is what the tests should validate (and don't yet).

### M5. CORS is wide open
- **Location**: `backend/main.py:86-91`
- **Problem**: `allow_origins=["*"]` plus `allow_methods=["*"]`. The
  frontend is served from the same origin as the API in this MVP, so
  CORS isn't actually needed. Wide-open CORS combined with cookie auth
  has caused real bugs in adjacent codebases.
- **Action**: Remove the CORS middleware entirely. If you ever need to
  serve the frontend from a different origin, pin
  `allow_origins=[frontend_origin]` and `allow_credentials=True`.

### M6. Session cookie is missing `secure`
- **Location**: `backend/main.py:535-542`
- **Problem**: `set_cookie(httponly=True, samesite="lax", secure=...)`
  doesn't set `secure`. Fine over localhost; not fine if the app ever
  runs behind HTTPS.
- **Action**: Set `secure=True` when not running locally — easiest is to
  read an env var like `SESSION_COOKIE_SECURE` (default false in dev).

### M7. `datetime.utcnow()` is deprecated in Python 3.12+
- **Location**: `backend/main.py:179`, `:329`, `:351`, `:391`, `:468`
- **Problem**: Every call emits a `DeprecationWarning` on Python ≥ 3.12
  and will be removed in a future release.
- **Action**: Replace with `datetime.now(timezone.utc)` (and import
  `timezone`). Same offset semantics, future-proof.

### M8. `KanbanBoard.tsx` is doing too much (470 lines)
- **Location**: `frontend/src/components/KanbanBoard.tsx`
- **Problem**: Holds state, fetch, optimistic update, drag handlers,
  collision detection, chat refresh, and the layout. The collision
  detection + drag flow alone is ~150 lines of logic that has nothing
  to do with rendering.
- **Action**: Extract two pieces:
  1. `frontend/src/lib/dnd.ts` for `buildCollisionDetection` and
     `findColumnId`.
  2. A `useKanbanBoard` hook that owns `board`, `sendBoardAction`,
     drag handlers, and exposes `{ board, handlers }`. The component
     becomes layout + handler wiring.

### M9. `apply_board_action` with `add_card` doesn't validate column
- **Location**: `backend/main.py:409-422`
- **Problem**: If `column_id` doesn't exist, the card is added to
  `board["cards"]` but never linked to a column. The card is orphaned
  and survives `repair_board_state`.
- **Action**: Validate `column_id` exists; raise 400 if not. Same
  pattern as `move_card` already does.

### M10. AI-generated card ids are too short
- **Location**: `backend/main.py:410` — `secrets.token_hex(8)` gives
  16 hex chars.
- **Problem**: Frontend ids look like `card-z7j44fmooyw2wj`; AI-added
  cards look like `b15cc02426ee1a48`. Inconsistent format makes them
  hard to scan, and `token_hex(8)` is 64 bits — fine for an MVP but
  small enough to consider raising.
- **Action**: Standardize: `f"card-{secrets.token_hex(8)}"` matches
  the `card-` prefix convention.

---

## Low

### L1. `frontend/test-results/` and `.claude/` are not gitignored
- **Location**: repo root + `frontend/`
- **Action**: Add to `.gitignore`. They appeared as "untracked" during
  the recent commit.

### L2. `docs/DB_SCHEMA.md` is out of date
- **Location**: `docs/DB_SCHEMA.md`
- **Problem**: Documents `users` and `boards`. Doesn't mention
  `sessions` (added in stage 6) or `chat_messages` (added in stage 9).
- **Action**: Add the two missing tables, with the same Rationale
  block style.

### L3. `docs/PLAN.md` doesn't note completion status
- **Location**: `docs/PLAN.md`
- **Problem**: Reads like all 10 stages are pending. Stages 1–10 are
  done.
- **Action**: Add a "Status" header or per-stage "Done ✓" markers so
  newcomers don't double-implement.

### L4. Duplicate `frontend/README.md`-style descriptions
- **Location**: `frontend/README.md` (4 lines), `frontend/AGENTS.md`
- **Problem**: Two near-identical "what is this folder" docs.
- **Action**: Keep `frontend/README.md` minimal and delete
  `frontend/AGENTS.md` (covered by M1).

### L5. Drag helper lives in the spec file
- **Location**: `frontend/tests/kanban.spec.ts:8-31`
- **Problem**: `dragCardTo` will be useful for future drag tests.
  Right now it's inline at the top of one spec.
- **Action**: When a second drag test is added, move it to
  `frontend/tests/helpers/drag.ts`. Not urgent.

### L6. `AiChat`'s `handleReset` swallows server errors
- **Location**: `frontend/src/components/AiChat.tsx:90-97`
- **Problem**: If `/api/chat/reset` fails, the UI clears anyway. The
  next chat call will replay the old history from the server.
- **Action**: Surface the error in the existing `error` state, only
  clear messages on successful response.

### L7. `KanbanBoard` falls back to `initialData` on load failure
- **Location**: `frontend/src/components/KanbanBoard.tsx:120, 134-137`
- **Problem**: If `/api/board` returns a non-OK status, the user sees
  the demo data and any actions hit the server (which has different
  state). Worse: actions will fail silently or apply to a different
  board.
- **Action**: Render an error state ("Failed to load board, retry?")
  instead of the demo board. The fallback data was useful before
  stage 7; now it's misleading.

### L8. Chat history grows without bound in storage
- **Location**: `backend/main.py:611-628`, `chat_messages` table
- **Problem**: We trim to the last 20 when sending to the AI, but the
  table keeps every message forever. Per-user this is small, but it's
  a slow leak.
- **Action**: Either purge messages older than N days on `chat_reset`,
  or cap the row count per user (delete oldest above 200). Not
  urgent for MVP.

### L9. Magic numbers in layout
- **Location**: `KanbanColumn.tsx`, `KanbanBoard.tsx`, `AiChat.tsx`
- **Problem**: `min-h-[520px]`, `w-[260px]`, `lg:w-[360px]`,
  `h-[calc(100vh-2rem)]` — sprinkled in JSX.
- **Action**: Lift to a `const SIZES = { column: ..., chat: ... }`
  in one place if you ever need to tune them. Pure polish.

### L10. No backend logging
- **Location**: `backend/main.py`
- **Problem**: We log nothing — including AI calls (which we're billed
  for). On any production-ish issue (rate limits, parse errors, slow
  OpenRouter), there's nothing to look at.
- **Action**: Add `logging.basicConfig(level=logging.INFO)` and log
  AI request id, latency, and any error path. Five lines, big payoff.

---

## Suggested action order

If you only have time for a few items, I'd do them in this order:

1. **C1, C2, C3** — git hygiene + key rotation (15 min, prevents
   leaks getting worse)
2. **C5** — fix `repair_board_state` resurrection (this caused real
   confusion; one helper to simplify)
3. **H3** — add backend tests (catches future regressions like the
   `move_card` bug we just fixed)
4. **C4** — switch to bcrypt/argon2 (one focused change before any
   real users exist)
5. **H2** — Pydantic models (refactor that pays for itself in every
   subsequent endpoint)
6. **M3, M4** — delete the dead `PATCH`/`merge_board_patch` and
   `getTargetDetails` helpers (smaller surface area)
7. Everything else as time permits.

## What's already in good shape

Worth calling out the things that don't need fixing:

- `apply_board_action` cleanly separates the four mutation types and
  works for both human and AI callers — that's why H1 is "high" not
  "critical."
- `buildCollisionDetection` is the right pattern (pointer-first +
  drill-down + lastOver fallback). It's the standard dnd-kit kanban
  approach.
- The `dragCardTo` helper is correctly diagnosing a real Playwright
  limitation; the comment explains why.
- Session handling (`sessions` table + cookie + `require_authenticated`
  middleware) is clean and easy to extend.
- The structured AI response contract (`{ message, boardUpdate }`) and
  the `apply_ai_board_update` validator are a sensible safety boundary
  between the model and the database.
- CLAUDE.md (added in this session) accurately reflects the current
  architecture.
