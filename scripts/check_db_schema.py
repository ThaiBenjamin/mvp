import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "backend" / "pm.db"
EXPECTED_TABLES = {"users", "boards"}

if not DB_FILE.exists():
    raise SystemExit(f"Database not found: {DB_FILE}")

with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

missing = EXPECTED_TABLES - tables
if missing:
    raise SystemExit(f"Missing tables: {missing}")

print("Database schema check passed.")
print("Found tables:", tables)
