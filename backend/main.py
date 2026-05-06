"""Application entry point: wire routers, mount the SPA, run schema bootstrap."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .auth import router as auth_router
from .boards import router as board_router
from .chat import router as chat_router
from .db import ensure_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Schema bootstrap runs at app startup (not at module import time) so that
    # tests can redirect config.DB_FILE to a tmp path before any DB work.
    ensure_database()
    yield


app = FastAPI(title="PM MVP Backend", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(board_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "backend is healthy"}


app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="frontend")
