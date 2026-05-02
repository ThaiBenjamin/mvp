import http.client
import http.cookies
import json

BASE_URL = "localhost"
PORT = 8000

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("POST", "/api/login", json.dumps({"username": "user", "password": "password"}), {"Content-Type": "application/json"})
res = conn.getresponse()
print("LOGIN", res.status, res.reason)
cookie = res.getheader("Set-Cookie")
print("SET-COOKIE", cookie)
body = res.read().decode()
print(body)

if not cookie:
    raise SystemExit("Login failed: no cookie")

jar = http.cookies.SimpleCookie()
jar.load(cookie)
cookie_header = "; ".join(f"{m.key}={m.value}" for m in jar.values())

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/board", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("BOARD-GET", res.status, res.reason)
initial_board = json.loads(res.read().decode())
print("initial columns", [c["title"] for c in initial_board["columns"]])

# mutate the first column title and add a marker card
initial_board["columns"][0]["title"] = "Backlog Updated"
new_card_id = "card-test-persistence"
initial_board["cards"][new_card_id] = {
    "id": new_card_id,
    "title": "Persistent test card",
    "details": "This card should persist after logout and login.",
}
initial_board["columns"][0]["cardIds"].append(new_card_id)

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request(
    "POST",
    "/api/board",
    json.dumps(initial_board),
    {"Content-Type": "application/json", "Cookie": cookie_header},
)
res = conn.getresponse()
print("BOARD-POST", res.status, res.reason)
print(res.read().decode())

# logout and login again to verify persistence
conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("POST", "/api/logout", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("LOGOUT", res.status, res.reason)
res.read()

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("POST", "/api/login", json.dumps({"username": "user", "password": "password"}), {"Content-Type": "application/json"})
res = conn.getresponse()
print("RELOGIN", res.status, res.reason)
cookie = res.getheader("Set-Cookie")
print("SET-COOKIE-2", cookie)
jar = http.cookies.SimpleCookie()
jar.load(cookie)
cookie_header = "; ".join(f"{m.key}={m.value}" for m in jar.values())
res.read()

conn = http.client.HTTPConnection(BASE_URL, PORT)
conn.request("GET", "/api/board", headers={"Cookie": cookie_header})
res = conn.getresponse()
print("BOARD-GET-2", res.status, res.reason)
board_after = json.loads(res.read().decode())
print("restored title", board_after["columns"][0]["title"])
print("restored has new card", new_card_id in board_after["cards"])
