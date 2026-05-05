# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Project Management MVP web app: Next.js frontend + Python FastAPI backend, served together from a single Docker container. Features: authentication, Kanban board with drag-and-drop, AI chat sidebar that can manipulate cards via OpenRouter.

## Commands

### Frontend (`frontend/`)
```
npm install          # install dependencies
npm run dev          # dev server on port 3000
npm run build        # static export to frontend/out/
npm run lint         # ESLint
npm run test:unit    # Vitest unit tests
npm run test:e2e     # Playwright e2e tests (requires running server on port 3000)
npm run test:all     # unit + e2e
```

### Backend (`backend/`)
```
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Uses `uv` as the Python package manager (Python 3.12+).

### Full stack
```
scripts/start.ps1    # Windows: start Docker container
scripts/stop.ps1     # Windows: stop Docker container
docker-compose up    # or directly via Docker
```

The Dockerfile does a multi-stage build: Node 20 Alpine builds `frontend/out/`, then Python 3.12 slim runs FastAPI which serves the static files at `/` and the API at `/api/*`.

## Architecture

**Single-file backend** — all FastAPI logic lives in `backend/main.py`: DB initialization, session auth middleware, board CRUD, AI chat endpoint. SQLite DB (`backend/pm.db`) is auto-created on first run with a default `user`/`password` account.

**Board state** is stored as a single JSON blob in `boards.state` (TEXT column). Mutations go through `POST /api/board/actions` with action types: `rename_column`, `add_card`, `delete_card`, `move_card`. A `PATCH /api/board` endpoint also accepts partial state updates.

**Frontend** is a static Next.js export (`output: "export"` in `next.config.ts`). It cannot use SSR features. Path alias `@/*` maps to `src/*`.

**Frontend state** — `src/lib/kanban.ts` contains board state logic. Components live in `src/components/`: `AuthApp`, `KanbanBoard`, `KanbanCard`, and AI chat components. Drag-and-drop uses `@dnd-kit`.

**AI chat** calls OpenRouter with model `openai/gpt-oss-120b:free`. The `OPENROUTER_API_KEY` is read from `.env` at the project root.

## Coding Standards

- Keep it simple — no over-engineering, no unnecessary defensive programming, no extra features.
- No emojis anywhere.
- Use latest idiomatic library versions and patterns.
- When debugging: identify root cause with evidence before fixing. Do not guess.
- Color scheme: Yellow `#ecad0a` (accents), Blue `#209dd7` (links/key sections), Purple `#753991` (submit buttons), Navy `#032147` (headings), Gray `#888888` (labels).
- Review `docs/PLAN.md` for the current development stage and acceptance criteria before starting new work.
