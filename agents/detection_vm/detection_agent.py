"""
Detection VM Agent
------------------
NEW file. Does not modify analyzer.py or router.py — it only imports
and calls the functions that already exist in those files.

Exposes the Detection VM's scanning logic over HTTP so the central
FastAPI dashboard (running on the host) can trigger scans on demand.

Run with:
    uvicorn detection_agent:app --host 0.0.0.0 --port 8002
"""
import os
import json
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# --- Unmodified existing scripts, just imported ---
from analyzer import analyze_file, Verdict
from router import route_file

app = FastAPI(title="Detection VM Agent")

# Shared secret so only the dashboard can call this agent.
# Set the same value in the dashboard's .env as DETECTION_AGENT_API_KEY.
API_KEY = os.getenv("AGENT_API_KEY", "CHANGE_ME_SHARED_SECRET")

# Folder this agent scans for /scan-directory calls (matches detector_watchdog.py's WATCH_DIR).
WATCH_DIR = os.getenv("WATCH_DIR", "/mnt/prod/Prod_Files")

# Since router.py's safe_move() copies (not moves) files, a file left in WATCH_DIR
# would get re-scanned and re-copied every cycle unless we remember what we already
# processed. This is new bookkeeping added here, in the agent — analyzer.py and
# router.py themselves are still untouched.
SEEN_FILES_PATH = os.getenv("SEEN_FILES_PATH", "./seen_files.json")


def load_seen_files() -> set:
    if os.path.exists(SEEN_FILES_PATH):
        with open(SEEN_FILES_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_files(seen: set):
    with open(SEEN_FILES_PATH, "w") as f:
        json.dump(list(seen), f)


def check_auth(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid agent API key")


class ScanRequest(BaseModel):
    path: str          # full path to the file on this VM, e.g. /mnt/prod/Prod_Files/file1.txt
    auto_route: bool = True  # if True, also copies file to backup_inbox / quarantine like the watchdog does


@app.get("/health")
def health():
    return {"status": "ONLINE", "vm": "Detection"}


@app.post("/scan")
def scan(req: ScanRequest, x_api_key: str = Header(...)):
    check_auth(x_api_key)

    if not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail=f"File not found: {req.path}")

    verdict: Verdict = analyze_file(req.path)

    if req.auto_route:
        route_file(req.path, verdict)

    return {
        "path": req.path,
        "verdict": verdict.name,
        "routed": req.auto_route,
    }


@app.post("/scan-directory")
def scan_directory(force_rescan: bool = False, x_api_key: str = Header(...)):
    """
    Scans every file currently in WATCH_DIR that hasn't been processed before.
    Meant to be called on a timer by the dashboard's scheduler instead of
    relying on a folder-watcher running on this VM.

    force_rescan=True re-checks every file regardless of scan history
    (useful for testing, or if you edit files in place).
    """
    check_auth(x_api_key)

    if not os.path.isdir(WATCH_DIR):
        raise HTTPException(status_code=404, detail=f"Watch directory not found: {WATCH_DIR}")

    seen = set() if force_rescan else load_seen_files()
    results = []

    for root, dirs, files in os.walk(WATCH_DIR):
        for name in files:
            full_path = os.path.join(root, name)
            if full_path in seen:
                continue

            verdict: Verdict = analyze_file(full_path)
            route_file(full_path, verdict)

            results.append({"path": full_path, "verdict": verdict.name})
            seen.add(full_path)

    save_seen_files(seen)

    return {
        "watch_dir": WATCH_DIR,
        "files_scanned": len(results),
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("detection_agent:app", host="0.0.0.0", port=8002)
