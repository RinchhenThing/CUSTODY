import sqlite3
import os
from datetime import datetime

# Local database path to prevent permission errors
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rel_path TEXT NOT NULL,
            version INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def insert_file(rel_path, version, sha256, size):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO files (rel_path, version, sha256, size, created_at) VALUES (?,?,?,?,?)",
        (rel_path, version, sha256, size, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_latest_version(rel_path):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM files WHERE rel_path=?", (rel_path,))
    row = cur.fetchone()
    conn.close()
    latest = row[0]
    return latest if latest is not None else 0

def list_files(limit=100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, rel_path, version, sha256, size, created_at FROM files ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
