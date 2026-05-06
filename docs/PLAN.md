# High level steps for project

This document is the execution plan for the Project Management MVP web app. Each phase includes discrete substeps, acceptance criteria, and test validation.

## Part 1: Plan and alignment

- Review the existing repository structure and frontend demo.
- Confirm the MVP scope with the user.
- Create `frontend/AGENTS.md` describing the current frontend codebase.
- Confirm the final AI model choice is a free OpenRouter-compatible model.

Success criteria:
- The plan is detailed and approved by the user.
- `frontend/AGENTS.md` exists and accurately describes current code.
- The model choice is confirmed as free and compatible.

## Part 2: Scaffolding

- Add backend scaffolding in `backend/` using Python FastAPI.
- Add Docker support at the repository root:
  - `Dockerfile` for the full app.
  - optional `docker-compose.yml` if needed for local development.
- Add start/stop scripts in `scripts/` for Windows, macOS, and Linux.
- Add a minimal backend route to serve static files and a sample API endpoint.
- Ensure the frontend can be statically built with `npm run build` from `frontend/`.

Success criteria:
- Docker container builds successfully.
- The container serves a static page at `/`.
- A simple API route returns a working JSON response.
- Scripts can start and stop the app locally.

Tests:
- Build and run Docker container.
- Verify `/` returns HTML and `/api/health` returns JSON.

## Part 3: Static frontend integration

- Configure the backend to serve the built Next.js frontend from `frontend/.next` or `out`.
- Add any needed frontend build scripts or static export settings.
- Confirm the demo Kanban board renders at `/` from the containerized app.

Success criteria:
- The Kanban board loads in production mode via the backend.
- Client-side interactions work in the served app.

Tests:
- Run a browser-based smoke test against `/`.
- Verify the existing Playwright tests can load the page successfully.

## Part 4: Fake user sign in experience

- Add a simple login page and session flow.
- Use hardcoded credentials: `user` and `password`.
- Protect the Kanban route so unauthenticated users must log in.
- Add logout support.

Success criteria:
- Visiting `/` without authentication redirects to login.
- Valid credentials display the Kanban board.
- Logout returns to the login screen.

Tests:
- Login with correct credentials.
- Reject invalid credentials.
- Logout and verify authentication is cleared.

## Part 5: Database modeling

- Define a SQLite schema for users and Kanban board state.
- Store board data as JSON for the MVP, while preserving the ability to extend to fine-grained tables later.
- Document the schema and rationale in `docs/`.
- Include user and board versioning fields as needed.

Success criteria:
- The schema is documented in `docs/`.
- The user agrees to the schema and persistence approach.

Tests:
- Validate the schema by creating the database and verifying the tables exist.
- Confirm the database is created automatically if missing.

## Part 6: Backend API

- Implement authentication endpoints and session handling.
- Implement Kanban CRUD endpoints for the signed-in user:
  - `GET /api/board`
  - `POST /api/board`
  - `PATCH /api/board`
  - `POST /api/board/actions` if needed for structured updates.
- Ensure the API reads from SQLite and writes changes persistently.

Success criteria:
- Backend routes are available and respond correctly.
- Data persists between requests and server restarts.

Tests:
- Backend unit tests for each route.
- End-to-end API tests that exercise login, board load, and board save.

## Part 7: Frontend + Backend integration

- Replace client-only board state with backend-driven state.
- Load the signed-in user board from `GET /api/board`.
- Send updates to the backend on user actions:
  - rename column
  - add card
  - delete card
  - move card
- Keep the UI in sync with persisted state.

Success criteria:
- The board persists changes on refresh.
- User actions are reflected in backend data.

Tests:
- Integration tests that perform login, update board state, refresh, and verify persistence.
- Frontend tests for API failure handling and loading state.

## Part 8: AI connectivity

- Add OpenRouter integration in the backend.
- Store `OPENROUTER_API_KEY` in `.env`.
- Verify a simple AI call returns an expected answer.
- Use a free model such as `openai/gpt-oss-120b:free` or another free OpenRouter-compatible model.

Success criteria:
- AI connectivity is verified with a simple `2+2` or equivalent prompt.
- The backend can successfully call OpenRouter and parse the response.

Tests:
- Backend test for OpenRouter connectivity using a mocked or real request.
- Validate the response format and successful handling of errors.

## Part 9: Structured AI board updates

- Extend the backend AI prompt to include the current Kanban board JSON and user question.
- Maintain conversation history for the session.
- Define a structured output format with:
  - `message`: text response for the user
  - `boardUpdate`: optional Kanban state modification
- Validate and apply board updates from AI responses.

Success criteria:
- The AI can return structured JSON that includes a board update.
- The backend safely applies valid updates to the persisted board.

Tests:
- Unit tests for parsing structured responses.
- End-to-end tests that send a sample question and verify board update application.

## Part 10: AI chat UI

- Add a sidebar chat panel to the UI.
- Allow users to send messages and see AI responses.
- Display AI responses and any board updates in the interface.
- Refresh the Kanban board automatically when the AI updates it.

Success criteria:
- Users can chat with AI from the app.
- AI responses display clearly and board updates are visible.
- The board refreshes after AI-driven changes.

Tests:
- End-to-end tests for the chat flow.
- Verify board updates from AI are applied and shown in the UI.

## Part 11: User management

- Add `POST /api/register` for self-service signup with bcrypt-hashed passwords.
- Add `GET /api/me` and `PATCH /api/me` for profile reads + display-name and
  password changes.
- Each new user is seeded with a default `My Board` so the first sign-in lands
  on a usable board.

Success criteria:
- Two distinct users can register and only see their own boards and chat.
- Profile updates persist across logout/login.

Tests:
- `backend/tests/test_register.py` covers happy path, duplicate username,
  invalid username characters, short password, board isolation across users,
  and profile updates.

## Part 12: Multiple boards per user

- Migrate `boards` to drop the `UNIQUE(user_id)` constraint and add `name`,
  `position`, `archived` columns. Existing rows become "My Board" at position 0.
- Add `GET/POST /api/boards`, `PATCH/DELETE /api/boards/{id}`,
  `GET /api/boards/{id}` and `POST /api/boards/{id}/actions`.
- Refuse to delete a user's only board so the UI always has one to render.
- Frontend gains a sidebar (`BoardWorkspace` + `BoardSidebar`) that switches
  between boards and remembers the active board in `localStorage`.

Success criteria:
- A user can create, rename, switch between, and delete boards.
- Card/column actions only mutate the targeted board's state.

Tests:
- `backend/tests/test_multiboard.py`: list/create/rename/delete, scoping,
  cross-user isolation, 404 for unknown ids.
- `frontend/src/components/BoardSidebar.test.tsx`.

## Part 13: Richer cards and columns

- Add `priority` (low/medium/high) and `dueDate` fields to each card; the
  `repair_board_state` normalizer fills sensible defaults for legacy data.
- New board actions: `update_card`, `add_column`, `delete_column` (refuses
  non-empty columns), and `move_column`.
- Frontend `KanbanCard` shows priority + due-date pills with overdue styling;
  `CardEditModal` allows editing all fields.
- AI prompt + validator extended to accept the new action types.

Success criteria:
- Users can edit any card field and reorder/add/delete columns.
- The AI assistant can drive the new actions.

Tests:
- `backend/tests/test_card_columns.py` and additions to
  `test_ai_validation.py`.
- `frontend/src/components/CardEditModal.test.tsx`.

## Part 14: Per-board AI chat

- `chat_messages` gains a `board_id` column so each board has its own
  assistant conversation.
- `GET /api/chat/history` and `POST /api/chat/reset` accept an optional
  `board_id` query parameter; `POST /api/chat` accepts it in the body.
- The frontend `AiChat` re-fetches when the active board changes.

Success criteria:
- Switching boards shows the chat history for that board only.
- Resetting chat for one board does not clear another's.

Tests:
- `backend/tests/test_chat_scoping.py`.

## Notes

- Keep the implementation minimal and avoid over-engineering.
- Prioritize a clean MVP flow over extra features.
- Use evidence-based debugging: identify root cause before applying fixes.
