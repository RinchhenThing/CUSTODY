"""
Backup VM Agent
----------------
NEW file. Does not modify backup_db.py, backup_ingest.py, or restore.py —
it only imports and calls the functions that already exist in those files.

Exposes storage/versioning/restore logic over HTTP so the central
FastAPI dashboard (running on the host) can trigger ingest and restores
on demand instead of relying only on the background watch loop.

Run with:
    uvicorn backup_agent:app --host 0.0.0.0 --port 8003
"""
import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# --- Unmodified existing scripts, just imported ---
from backup_db import list_files, get_latest_version, init_db
from backup_ingest import store_file
from restore import restore_file

app = FastAPI(title="Backup VM Agent")

API_KEY = os.getenv("AGENT_API_KEY", "CHANGE_ME_SHARED_SECRET")


def check_auth(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent API key")


class StoreRequest(BaseModel):
    src_path: str  # full path to a file already sitting in the backup inbox


class RestoreRequest(BaseModel):
    rel_path: str
    version: int
    destination_path: str | None = None  # optional override; restore.py has its own default


@app.on_event("startup")
def ensure_db():
    init_db()  # safe no-op if tables already exist


@app.get("/health")
def health():
    return {"status": "ONLINE", "vm": "Backup"}


@app.get("/versions")
def versions(limit: int = 100, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    return list_files(limit=limit)


@app.get("/latest-version")
def latest_version(rel_path: str, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    return {"rel_path": rel_path, "latest_version": get_latest_version(rel_path)}


@app.post("/store")
def store(req: StoreRequest, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    if not os.path.exists(req.src_path):
        raise HTTPException(status_code=404, detail=f"File not found: {req.src_path}")
    store_file(req.src_path)
    return {"status": "STORED", "src_path": req.src_path}


@app.post("/restore")
def restore(req: RestoreRequest, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    try:
        dest = restore_file(req.rel_path, req.version)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # covers both "no DB record" and "hash mismatch / tampering"
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ONLINE", "restored_to": dest}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backup_agent:app", host="0.0.0.0", port=8003)
