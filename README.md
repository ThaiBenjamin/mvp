# 🗂️ Project Management MVP

A full-stack Kanban-style project management web app with an AI chat assistant that can create, move, and delete cards on your behalf.

![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)

---

## ✨ Features

- **Kanban Board** — Drag-and-drop cards across customizable columns using `@dnd-kit`
- **Multiple Boards** — Create and switch between separate project boards
- **AI Chat Sidebar** — Chat with an LLM (via OpenRouter) that can add, move, rename, and delete cards on your behalf
- **User Authentication** — Secure session-based login with bcrypt password hashing
- **Fully Tested** — Unit tests (Vitest), end-to-end tests (Playwright), and backend tests (pytest)
- **Docker Deployment** — Single-container deployment via multi-stage Docker build

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Drag & Drop | `@dnd-kit/core`, `@dnd-kit/sortable` |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | SQLite (auto-created on first run) |
| Auth | Session cookies + bcrypt |
| AI | OpenRouter API (configurable model) |
| Testing | Vitest, Playwright, pytest |
| Deployment | Docker, docker-compose |

---

## 🚀 Setup & Running

### Prerequisites
- Docker & Docker Compose, **or** Node.js 20+ and Python 3.12+ with `uv`

### Option A — Docker (recommended)

```bash
git clone https://github.com/ThaiBenjamin/mvp.git
cd mvp

# Create .env with your OpenRouter key
echo "OPENROUTER_API_KEY=your_key_here" > .env

# Start (Windows)
scripts/start.ps1

# Start (Linux/Mac)
./scripts/start.sh
```

The app runs at **http://localhost:8000**. Default credentials: `user` / `password`.

### Option B — Local development

```bash
# Backend
cd backend
uv sync
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # runs at http://localhost:3000
```

### Running Tests

```bash
# Frontend unit tests
cd frontend && npm run test:unit

# Frontend e2e tests (requires running server)
cd frontend && npm run test:e2e

# Backend tests
cd backend && pytest
```

---

## 🧠 What I Built and Why

I built this as a full-stack portfolio project to practice shipping a production-quality web app from scratch — not just a tutorial clone, but something with real architecture decisions.

The goal was to integrate every layer of a modern stack: a statically-exported Next.js frontend, a FastAPI Python backend, SQLite persistence, Docker containerization, and an AI chat interface that actually modifies state. The AI sidebar was the most interesting part — instead of just answering questions, it understands board context and issues structured actions (`add_card`, `move_card`, `delete_card`) that the backend processes.

I deliberately kept the architecture simple: one SQLite file, one Docker container, one JSON blob per board. The constraint forced me to focus on feature completeness and code quality rather than over-engineering infrastructure.
