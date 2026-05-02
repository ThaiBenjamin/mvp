import http.client
import http.cookies
import json

BASE_URL = "localhost"
PORT = 8000

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/health")
res = conn.getresponse()
print("HEALTH", res.status, res.reason)
print(res.read().decode())

conn = http.client.HTTPConnection(BASE_URL, PORT)
login_body = json.dumps({"username": "user", "password": "password"})
conn.request("POST", "/api/login", login_body, {"Content-Type": "application/json"})
res = conn.getresponse()
print("LOGIN", res.status, res.reason)
cookie = res.getheader("Set-Cookie")
print("SET-COOKIE", cookie)
resp_body = res.read().decode()
print(resp_body)
if res.status != 200 or not cookie:
    raise SystemExit("Login failed")

jar = http.cookies.SimpleCookie()
jar.load(cookie)
cookie_header = "; ".join(f"{m.key}={m.value}" for m in jar.values())

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/session", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("SESSION", res.status, res.reason)
print(res.read().decode())

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/board", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("BOARD GET", res.status, res.reason)
board = json.loads(res.read().decode())
print("columns", [col["title"] for col in board["columns"]])

patch_body = json.dumps({"columns": [{"id": "col-backlog", "title": "Backlog Patched", "cardIds": board["columns"][0]["cardIds"]}]})
conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("PATCH", "/api/board", patch_body, {"Content-Type": "application/json", "Cookie": cookie_header})
res = conn.getresponse()
print("BOARD PATCH", res.status, res.reason)
patched = json.loads(res.read().decode())
print("patched title", patched["columns"][0]["title"])

action_body = json.dumps({
    "action": "add_card",
    "payload": {
        "column_id": "col-backlog",
        "title": "Action Card",
        "details": "Created via action endpoint.",
    },
})
conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("POST", "/api/board/actions", action_body, {"Content-Type": "application/json", "Cookie": cookie_header})
res = conn.getresponse()
print("BOARD ACTIONS", res.status, res.reason)
actioned = json.loads(res.read().decode())
print("action card present", any(card["title"] == "Action Card" for card in actioned["cards"].values()))

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("POST", "/api/logout", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("LOGOUT", res.status, res.reason)
print(res.read().decode())

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/session", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("SESSION AFTER LOGOUT", res.status, res.reason)
print(res.read().decode())
