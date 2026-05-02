# Backend Agent Documentation

## Purpose

The backend is scaffolded as a FastAPI service for the Project Management MVP.
It currently serves a static HTML confirmation page and provides a health endpoint.

## Structure

- `backend/pyproject.toml`
  - Defines the backend project metadata and dependencies.
  - Dependencies: `fastapi`, `uvicorn[standard]`, `python-dotenv`.

- `backend/main.py`
  - Creates the FastAPI application.
  - Mounts a static file directory at `/static`.
  - Exposes `/api/health` for a JSON health check.
  - Serves `backend/static/index.html` at `/`.

- `backend/static/index.html`
  - Simple static HTML page used to verify the backend is serving content.

## Docker support

- `Dockerfile`
  - Builds the frontend with Node.js.
  - Installs Python dependencies using `uv`.
  - Launches FastAPI with `uvicorn`.

- `docker-compose.yml`
  - Defines a single `app` service.
  - Exposes port `8000`.
  - Reads environment variables from `.env`.

## Scripts

- `scripts/start.sh` / `scripts/stop.sh`
  - Start and stop the Docker service on macOS/Linux.

- `scripts/start.ps1` / `scripts/stop.ps1`
  - Start and stop the Docker service on Windows.

## Notes

- This is the scaffolding phase only.
- The static frontend is currently a placeholder; frontend integration will come in the next phase.
