# Project Management MVP

A Kanban board with an AI sidebar that moves the cards itself, through the same validated
code path the buttons use.

## The idea

Kanban is a good interface for reading work and a tedious one for changing it. Clearing a
column means deleting cards one at a time. Moving a batch to the next stage means dragging
each one. Renaming a card means finding it, opening it, editing it, saving it. None of it is
hard, and all of it is clicking.

So the premise was to give the board a second interface: say "move everything in review to
done" and have it happen. That's a different problem from a chat sidebar that summarizes
your board, because the model's output stops being text somebody reads and starts being an
instruction something executes. The interesting engineering isn't getting the model to
answer. It's deciding what happens when the answer is wrong.

## How that stays safe

`apply_board_action` is a pure function — board in, new board out, never mutating its input.
The REST endpoint behind the buttons calls it. The AI path calls it too, once per action the
model proposed, after each one has been checked against the ids that actually exist. Nothing
about the reducer knows which caller it has.

That's what makes the assistant safe to wire up directly. It isn't trusted, it's funnelled.
The model's job ends at proposing a list of actions; whether any of them is legal is decided
by code that was already there for the buttons.

Validation is per action, not per batch. A move needs a card id that exists and a target
column that exists. A rename needs a real column and a non-empty title. A delete needs a
card actually on the board. Anything that fails is skipped rather than corrected or guessed
at, and the loop keeps going, so one hallucinated id can't cost you the other nine edits.

The parser is deliberately forgiving too. The request asks for a JSON object, but a cheap
model doesn't always comply, so the parser strips code fences, skips leading prose to the
first brace, and decodes non-strictly so literal newlines inside strings don't kill the
turn. If what comes back still has no message, the turn fails loudly rather than
half-applying.

## What's in it

Drag-and-drop cards across customizable columns with `@dnd-kit`, multiple boards per
account, session-based login with bcrypt hashing, and the AI sidebar. Tests run at three
levels: Vitest on the frontend, Playwright end to end, pytest on the backend.

## Stack

| Layer | What |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Drag and drop | `@dnd-kit/core`, `@dnd-kit/sortable` |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | SQLite, created on first run |
| Auth | Session cookies and bcrypt |
| AI | OpenRouter, configurable model |
| Testing | Vitest, Playwright, pytest |
| Deployment | Docker, docker-compose |

The frontend is a static Next.js export served by the same FastAPI process that owns the
API, so the whole app is one container on one port. I kept the architecture deliberately
small — one SQLite file, one JSON blob per board — so the work went into finishing features
rather than provisioning infrastructure.

## Running it

You'll need Docker and Docker Compose, or Node 20+ and Python 3.12+ with `uv`.

### With Docker

```bash
git clone https://github.com/ThaiBenjamin/mvp.git
cd mvp

echo "OPENROUTER_API_KEY=your_key_here" > .env

scripts/start.ps1    # Windows
./scripts/start.sh   # Linux / macOS
```

The app runs at http://localhost:8000. Default credentials are `user` / `password`.

### Without Docker

```bash
cd backend
uv sync
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Tests

```bash
cd frontend && npm run test:unit
cd frontend && npm run test:e2e   # needs a running server
cd backend && pytest
```
