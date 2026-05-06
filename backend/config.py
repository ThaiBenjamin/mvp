"""Centralized configuration: paths, env-derived values, constants."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "frontend" / "out"

load_dotenv(BASE_DIR.parent / ".env")

# DB location is overridable so tests can point at a tmp path.
DB_FILE: Path = Path(os.getenv("PM_DB_FILE", str(BASE_DIR / "pm.db")))

# Bootstrap credentials; the seeded user can be relogged with these.
SEED_USERNAME = "user"
SEED_PASSWORD = "password"

SESSION_COOKIE_NAME = "session_token"
SESSION_COOKIE_MAX_AGE = 3600
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b:free"
CHAT_HISTORY_LIMIT = 20
