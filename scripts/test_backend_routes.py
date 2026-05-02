from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("HEALTH", client.get("/api/health").status_code, client.get("/api/health").json())
resp = client.post("/api/login", json={"username": "user", "password": "password"})
print("LOGIN", resp.status_code, resp.json())
print("COOKIE", resp.cookies)
assert resp.status_code == 200
assert resp.cookies.get("session_token")

cookies = {"session_token": resp.cookies.get("session_token")}
print("SESSION", client.get("/api/session", cookies=cookies).json())
board = client.get("/api/board", cookies=cookies).json()
print("BOARD COLUMNS", [col["title"] for col in board["columns"]])
patch = client.patch(
    "/api/board",
    cookies=cookies,
    json={
        "columns": [
            {
                "id": "col-backlog",
                "title": "Backlog Patched",
                "cardIds": board["columns"][0]["cardIds"],
            }
        ]
    },
)
print("PATCH", patch.status_code, patch.json()["columns"][0]["title"])
action = client.post(
    "/api/board/actions",
    cookies=cookies,
    json={
        "action": "add_card",
        "payload": {
            "column_id": "col-backlog",
            "title": "Action Card",
            "details": "details",
        },
    },
)
print("ACTIONS", action.status_code, any(card["title"] == "Action Card" for card in action.json()["cards"].values()))
logout = client.post("/api/logout", cookies=cookies)
print("LOGOUT", logout.status_code, logout.json())
print("SESSION AFTER LOGOUT", client.get("/api/session", cookies=cookies).json())
