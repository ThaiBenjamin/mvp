FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/pyproject.toml
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-dotenv httpx

COPY backend/ backend/
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
