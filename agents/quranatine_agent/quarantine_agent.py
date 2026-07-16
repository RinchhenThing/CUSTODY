"""
Quarantine VM Agent
--------------------
NEW file. There was no existing quarantine script in your uploads (the
Detection VM just copies suspicious files into /mnt/quarantine and stops
there), so this agent owns the quarantine-management logic directly.

Exposes listing / releasing / deleting quarantined files over HTTP so
the central FastAPI dashboard can manage them remotely.

Run with:
    uvicorn quarantine_agent:app --host 0.0.0.0 --port 8004
"""
import os
import shutil
import hashlib
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Quarantine VM Agent")

API_KEY = os.getenv("AGENT_API_KEY", "CHANGE_ME_SHARED_SECRET")
QUARANTINE_DIR = os.getenv("QUARANTINE_DIR", "/mnt/quarantine")


def check_auth(x_api_key: str):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent API key")


def sha256sum(path, blocksize=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            h.update(chunk)
    return h.hexdigest()


class ReleaseRequest(BaseModel):
    filename: str
    destination_path: str  # e.g. back into /mnt/backup_inbox for re-processing


@app.get("/health")
def health():
    return {"status": "ONLINE", "vm": "Quarantine"}


@app.get("/files")
def list_files(x_api_key: str = Header(...)):
    check_auth(x_api_key)
    if not os.path.isdir(QUARANTINE_DIR):
        return []
    results = []
    for name in os.listdir(QUARANTINE_DIR):
        full_path = os.path.join(QUARANTINE_DIR, name)
        if os.path.isfile(full_path):
            results.append({
                "filename": name,
                "size": os.path.getsize(full_path),
                "sha256": sha256sum(full_path),
            })
    return results


@app.post("/release")
def release(req: ReleaseRequest, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    src = os.path.join(QUARANTINE_DIR, req.filename)
    if not os.path.exists(src):
        raise HTTPException(status_code=404, detail=f"File not found in quarantine: {req.filename}")

    os.makedirs(req.destination_path, exist_ok=True)
    dest = os.path.join(req.destination_path, req.filename)
    shutil.move(src, dest)
    return {"status": "RELEASED", "released_to": dest}


@app.delete("/files/{filename}")
def delete_file(filename: str, x_api_key: str = Header(...)):
    check_auth(x_api_key)
    target = os.path.join(QUARANTINE_DIR, filename)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    os.remove(target)
    return {"status": "DELETED", "filename": filename}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("quarantine_agent:app", host="0.0.0.0", port=8004)
