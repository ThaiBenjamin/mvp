from pathlib import Path
import json

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
STATIC_DIR = BASE_DIR.parent / "frontend" / "out"
STATE_FILE = BASE_DIR / "board.json"

VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_COOKIE_NAME = "session_token"
SESSION_COOKIE_VALUE = "demo-session"

DEFAULT_BOARD_STATE = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}

app = FastAPI(title="PM MVP Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_board_state():
    if not STATE_FILE.exists():
        save_board_state(DEFAULT_BOARD_STATE)
    try:
        with STATE_FILE.open("r", encoding="utf-8") as board_file:
            return json.load(board_file)
    except (json.JSONDecodeError, OSError):
        save_board_state(DEFAULT_BOARD_STATE)
        return DEFAULT_BOARD_STATE


def save_board_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as board_file:
        json.dump(state, board_file, indent=2)


def require_authenticated(request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if session_cookie != SESSION_COOKIE_VALUE:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "message": "backend is healthy"})

@app.get("/api/session")
async def session(request: Request):
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    authenticated = session_cookie == SESSION_COOKIE_VALUE
    return JSONResponse({"authenticated": authenticated, "username": VALID_USERNAME if authenticated else None})

@app.get("/api/board")
async def get_board(request: Request):
    require_authenticated(request)
    return JSONResponse(load_board_state())

@app.post("/api/board")
async def update_board(request: Request):
    require_authenticated(request)
    board_state = await request.json()
    save_board_state(board_state)
    return JSONResponse(board_state)

@app.post("/api/login")
async def login(request: Request, response: Response):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")

    if username != VALID_USERNAME or password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response_payload = JSONResponse({"authenticated": True, "username": username})
    response_payload.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=SESSION_COOKIE_VALUE,
        httponly=True,
        max_age=3600,
        path="/",
        samesite="lax",
    )

    return response_payload

@app.post("/api/logout")
async def logout():
    response_payload = JSONResponse({"authenticated": False})
    response_payload.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response_payload

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
